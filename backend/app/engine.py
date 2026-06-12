"""Auto-Assign engine.

Improvements over a naive greedy loop:
- Most-constrained-first: sections with the heaviest demand are placed
  before lightly loaded ones, so they don't find every lecturer exhausted.
- Subject spreading: at each slot we place the subject with the most
  remaining demand, which naturally interleaves subjects across the day.
- Half-period pairing: 1.5-period demands leave a half, which gets paired
  with another half (the ENG/SAN split-cell pattern).
- Locked sessions and other-campus bookings are treated as fixed busy time.
- Output is a DRAFT (proposal), nothing is written. Commit is a separate,
  transactional endpoint. Unfilled demand is reported, never silent.
- Remaining empty period slots become Study Hours, supervised by the
  least-loaded available JL (JL allocation).

This is deliberately not a full constraint solver: for a college of this
size most-constrained-first greedy fills cleanly, and when it can't, the
unfilled report tells the operator exactly what to fix (usually: not
enough lecturers for one subject).
"""
from collections import defaultdict
from sqlalchemy.orm import Session as DbSession
from . import models
from .clash import times_overlap, halves_conflict


class _Busy:
    """In-memory availability tracker for one engine run."""

    def __init__(self):
        # key -> list of (start_min, end_min, slot_id, half)
        self.map = defaultdict(list)
        self.load = defaultdict(int)  # staff_id -> booked halves (for balancing)

    def is_free(self, key, slot, half):
        for (s, e, slot_id, h) in self.map[key]:
            if times_overlap(s, e, slot.start_min, slot.end_min):
                if halves_conflict(half, h, slot_id == slot.id):
                    return False
        return True

    def book(self, key, slot, half):
        self.map[key].append((slot.start_min, slot.end_min, slot.id, half))


def run_engine(db: DbSession, campus_id: int, clear_existing: bool = True):
    campus = db.get(models.Campus, campus_id)
    if not campus:
        raise ValueError("Campus not found")

    slots = [s for s in campus.time_slots if s.kind == "PERIOD"]
    slots.sort(key=lambda s: s.sort_order)
    sections = sorted(campus.sections, key=lambda s: s.sort_order)
    subjects = {s.id: s for s in db.query(models.Subject).all()}

    staff_all = db.query(models.Staff).filter_by(active=True).all()
    lecturers_by_subject = defaultdict(list)
    jls = []
    for st in staff_all:
        if st.role == "JL":
            jls.append(st)
        for subj in st.subjects:
            lecturers_by_subject[subj.id].append(st)
    # Full-timers first within each subject (stable ordering).
    for lst in lecturers_by_subject.values():
        lst.sort(key=lambda s: (s.employment != "FULL_TIME", s.id))

    staff_busy = _Busy()
    section_busy = _Busy()

    # ---- fixed sessions: everything we are NOT wiping counts as busy ----
    fixed = db.query(models.TTSession).join(models.TimeSlot).all()
    target_slot_ids = {s.id for s in campus.time_slots}
    kept_demand = defaultdict(int)  # (section_id, subject_id) -> halves kept
    for sess in fixed:
        in_target = sess.time_slot_id in target_slot_ids
        wiped = in_target and clear_existing and not sess.locked
        if wiped:
            continue
        h = 1 if sess.half in ("A", "B") else 2
        if sess.staff_id:
            staff_busy.book(sess.staff_id, sess.time_slot, sess.half)
            staff_busy.load[sess.staff_id] += h
        for sec in sess.sections:
            section_busy.book(sec.id, sess.time_slot, sess.half)
            if in_target and sess.subject_id:
                kept_demand[(sec.id, sess.subject_id)] += h

    # ---- demand per section, in halves, minus what kept sessions cover ----
    reqs = (db.query(models.Requirement)
              .join(models.Section)
              .filter(models.Section.campus_id == campus_id).all())
    demand = defaultdict(dict)  # section_id -> {subject_id: halves}
    preferred = {}              # (section_id, subject_id) -> staff_id
    for r in reqs:
        left = r.halves_per_day - kept_demand.get((r.section_id, r.subject_id), 0)
        if left > 0:
            demand[r.section_id][r.subject_id] = left
        if r.preferred_staff_id:
            preferred[(r.section_id, r.subject_id)] = r.preferred_staff_id

    # Most-constrained-first: heaviest total demand placed first.
    ordered_sections = sorted(
        sections, key=lambda s: -sum(demand.get(s.id, {}).values()))

    proposal = []
    unfilled = []

    def pick_lecturer(section_id, subject_id, slot, half):
        pref_id = preferred.get((section_id, subject_id))
        candidates = lecturers_by_subject.get(subject_id, [])
        if pref_id:
            pref = next((c for c in candidates if c.id == pref_id), None)
            if pref and staff_busy.is_free(pref.id, slot, half):
                return pref
        free = [c for c in candidates if staff_busy.is_free(c.id, slot, half)]
        if not free:
            return None
        # Least-loaded among free, full-timers favoured by base ordering.
        free.sort(key=lambda c: (staff_busy.load[c.id],
                                 c.employment != "FULL_TIME"))
        return free[0]

    def place(section, slot, subject_id, staff, half):
        staff_busy.book(staff.id, slot, half)
        staff_busy.load[staff.id] += 1 if half in ("A", "B") else 2
        section_busy.book(section.id, slot, half)
        proposal.append(dict(time_slot_id=slot.id, section_ids=[section.id],
                             subject_id=subject_id, staff_id=staff.id,
                             is_study_hour=False, half=half))

    for section in ordered_sections:
        dem = demand.get(section.id, {})
        for slot in slots:
            if not dem:
                break
            if not section_busy.is_free(section.id, slot, "FULL"):
                continue
            # 1) try a FULL period: subject with most remaining demand >= 2
            fulls = sorted([sid for sid, h in dem.items() if h >= 2],
                           key=lambda sid: -dem[sid])
            placed = False
            for sid in fulls:
                lect = pick_lecturer(section.id, sid, slot, "FULL")
                if lect:
                    place(section, slot, sid, lect, "FULL")
                    dem[sid] -= 2
                    if dem[sid] == 0:
                        del dem[sid]
                    placed = True
                    break
            if placed:
                continue
            # 2) pair two halves in one split period (ENG/SAN pattern)
            half_subjects = sorted([sid for sid, h in dem.items() if h >= 1],
                                   key=lambda sid: -dem[sid])
            pair = []
            for sid in half_subjects:
                which = "A" if not pair else "B"
                lect = pick_lecturer(section.id, sid, slot, which)
                if lect:
                    pair.append((sid, lect, which))
                if len(pair) == 2:
                    break
            if len(pair) == 2:
                for sid, lect, which in pair:
                    place(section, slot, sid, lect, which)
                    dem[sid] -= 1
                    if dem[sid] == 0:
                        del dem[sid]
                continue
            # 3) single stray half: place as half A, leave B as study half?
            # Keep it simple: place the half; the other half stays empty
            # and is visible on the grid for a manual decision.
            if len(pair) == 1:
                sid, lect, which = pair[0]
                place(section, slot, sid, lect, which)
                dem[sid] -= 1
                if dem[sid] == 0:
                    del dem[sid]
        for sid, h in dem.items():
            unfilled.append(
                f"{section.name}: {subjects[sid].code} short by {h/2:g} "
                f"period(s) - no free lecturer")

    # ---- Study Hour fill with JL allocation ----
    sh_count = 0
    for section in ordered_sections:
        for slot in slots:
            if not section_busy.is_free(section.id, slot, "FULL"):
                continue
            free_jls = [j for j in jls if staff_busy.is_free(j.id, slot, "FULL")]
            free_jls.sort(key=lambda j: staff_busy.load[j.id])
            jl = free_jls[0] if free_jls else None
            if jl:
                staff_busy.book(jl.id, slot, "FULL")
                staff_busy.load[jl.id] += 2
            section_busy.book(section.id, slot, "FULL")
            proposal.append(dict(time_slot_id=slot.id,
                                 section_ids=[section.id],
                                 subject_id=None,
                                 staff_id=jl.id if jl else None,
                                 is_study_hour=True, half="FULL"))
            sh_count += 1

    stats = {
        "sections": len(sections),
        "period_slots": len(slots),
        "teaching_sessions": len(proposal) - sh_count,
        "study_hours": sh_count,
        "unfilled_count": len(unfilled),
    }
    return proposal, unfilled, stats
