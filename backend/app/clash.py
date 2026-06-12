"""Clash detection. The single source of truth for "is this booking legal".

Rules:
1. Two slots conflict when their real times overlap (start < other.end and
   other.start < end). Slot IDs are irrelevant: this is what makes
   CROSS-CAMPUS clash prevention work even though each campus has its own
   period grid.
2. Within the SAME slot, half A and half B coexist (split period).
   FULL conflicts with everything in that slot.
3. Across DIFFERENT (but time-overlapping) slots we always conflict,
   halves included: a lecturer physically cannot be in two campuses even
   for half a period.
"""
from sqlalchemy.orm import Session as DbSession
from . import models


def halves_conflict(half_a: str, half_b: str, same_slot: bool) -> bool:
    if not same_slot:
        return True
    if half_a == "FULL" or half_b == "FULL":
        return True
    return half_a == half_b


def times_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    return s1 < e2 and s2 < e1


def find_staff_clash(db: DbSession, staff_id: int, slot: models.TimeSlot,
                     half: str, exclude_ids: set[int] | None = None):
    """Return a conflicting TTSession for this lecturer, or None."""
    if staff_id is None:
        return None
    exclude_ids = exclude_ids or set()
    rows = (db.query(models.TTSession)
              .join(models.TimeSlot)
              .filter(models.TTSession.staff_id == staff_id)
              .filter(times_filter(slot))
              .all())
    for s in rows:
        if s.id in exclude_ids:
            continue
        if halves_conflict(half, s.half, s.time_slot_id == slot.id):
            return s
    return None


def find_section_clash(db: DbSession, section_id: int, slot: models.TimeSlot,
                       half: str, exclude_ids: set[int] | None = None):
    """Return a conflicting TTSession for this section, or None."""
    exclude_ids = exclude_ids or set()
    rows = (db.query(models.TTSession)
              .join(models.TimeSlot)
              .join(models.SessionSection,
                    models.SessionSection.session_id == models.TTSession.id)
              .filter(models.SessionSection.section_id == section_id)
              .filter(times_filter(slot))
              .all())
    for s in rows:
        if s.id in exclude_ids:
            continue
        if halves_conflict(half, s.half, s.time_slot_id == slot.id):
            return s
    return None


def times_filter(slot: models.TimeSlot):
    return (models.TimeSlot.start_min < slot.end_min) & \
           (models.TimeSlot.end_min > slot.start_min)


def describe(db: DbSession, s: models.TTSession) -> str:
    subj = s.subject.code if s.subject else ("SH" if s.is_study_hour else "?")
    who = s.staff.code if s.staff else "-"
    sec = ",".join(x.name for x in s.sections) or "-"
    campus = s.time_slot.campus.name
    return f"{subj} ({who}) for {sec} at {campus} {s.time_slot.label}"
