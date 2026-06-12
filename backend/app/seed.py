"""Seed the database with data digitized from the college's paper sheets.
Runs once automatically on first boot (only when DB is empty).
Edit freely - this is just a starting point so the app isn't blank.
"""
from sqlalchemy.orm import Session as DbSession
from . import models
from .auth import hash_password


def m(h, mi):  # minutes from midnight
    return h * 60 + mi


def seed_if_empty(db: DbSession):
    if db.query(models.Campus).first():
        return

    # ---------------- campuses ----------------
    ac = models.Campus(name="AC Campus", location="Narasaraopet")
    sar = models.Campus(name="Saraswathi Bhavan", location="Narasaraopet")
    vys = models.Campus(name="Vyshnavi Bhavan (Jr. Boys)", location="Narasaraopet")
    cvr = models.Campus(name="C.V. Raman Bhavan (Sr. Boys)", location="Narasaraopet")
    db.add_all([ac, sar, vys, cvr])
    db.flush()

    # ---------------- time slots ----------------
    # AC Campus grid (from the filled 2026-27 sheet)
    ac_slots = [
        ("6.00-6.45",  m(6, 0),  m(6, 45),  "PERIOD"),
        ("6.45-7.30",  m(6, 45), m(7, 30),  "PERIOD"),
        ("8.00-8.45",  m(8, 0),  m(8, 45),  "PERIOD"),
        ("8.45-9.30",  m(8, 45), m(9, 30),  "PERIOD"),
        ("9.30-10.15", m(9, 30), m(10, 15), "PERIOD"),
        ("10.15-10.30", m(10, 15), m(10, 30), "BREAK"),
        ("10.30-11.15", m(10, 30), m(11, 15), "PERIOD"),
        ("11.15-12.00", m(11, 15), m(12, 0), "PERIOD"),
        ("12.00-12.45", m(12, 0), m(12, 45), "PERIOD"),
        ("12.45-1.30", m(12, 45), m(13, 30), "LUNCH"),
        ("1.30-2.15",  m(13, 30), m(14, 15), "PERIOD"),
        ("2.15-3.00",  m(14, 15), m(15, 0), "PERIOD"),
        ("3.00-3.45",  m(15, 0), m(15, 45), "PERIOD"),
        ("3.45-4.00",  m(15, 45), m(16, 0), "BREAK"),
        ("4.00-5.50",  m(16, 0), m(17, 50), "PERIOD"),
        ("6.00-7.15",  m(18, 0), m(19, 15), "PERIOD"),
        ("7.15-7.45",  m(19, 15), m(19, 45), "DINNER"),
        ("7.45-9.00",  m(19, 45), m(21, 0), "PERIOD"),
    ]
    # Saraswathi / Vyshnavi / CV Raman grid (from the blank sheets)
    sh_slots = [
        ("6.00-6.50",  m(6, 0),  m(6, 50),  "PERIOD"),
        ("6.50-7.40",  m(6, 50), m(7, 40),  "PERIOD"),
        ("7.40-8.10",  m(7, 40), m(8, 10),  "PERIOD"),
        ("8.10-9.00",  m(8, 10), m(9, 0),   "PERIOD"),
        ("9.00-9.50",  m(9, 0),  m(9, 50),  "PERIOD"),
        ("9.50-10.40", m(9, 50), m(10, 40), "PERIOD"),
        ("10.40-10.50", m(10, 40), m(10, 50), "BREAK"),
        ("10.50-11.40", m(10, 50), m(11, 40), "PERIOD"),
        ("11.40-12.30", m(11, 40), m(12, 30), "PERIOD"),
        ("12.30-1.30", m(12, 30), m(13, 30), "LUNCH"),
        ("1.30-2.20",  m(13, 30), m(14, 20), "PERIOD"),
        ("2.20-3.10",  m(14, 20), m(15, 10), "PERIOD"),
        ("3.10-4.00",  m(15, 10), m(16, 0), "PERIOD"),
        ("4.00-4.10",  m(16, 0), m(16, 10), "BREAK"),
        ("4.10-5.00",  m(16, 10), m(17, 0), "PERIOD"),
        ("5.00-5.50",  m(17, 0), m(17, 50), "PERIOD"),
        ("6.00-6.50",  m(18, 0), m(18, 50), "PERIOD"),
        ("6.50-7.40",  m(18, 50), m(19, 40), "PERIOD"),
    ]
    for i, (label, s, e, kind) in enumerate(ac_slots):
        db.add(models.TimeSlot(campus_id=ac.id, label=label, start_min=s,
                               end_min=e, sort_order=i, kind=kind))
    for campus in (sar, vys, cvr):
        for i, (label, s, e, kind) in enumerate(sh_slots):
            db.add(models.TimeSlot(campus_id=campus.id, label=label,
                                   start_min=s, end_min=e, sort_order=i,
                                   kind=kind))

    # ---------------- subjects ----------------
    subj_defs = [("MT1", "Maths T1"), ("MT2", "Maths T2"), ("PHY", "Physics"),
                 ("CHE", "Chemistry"), ("BOT", "Botany"), ("ZOO", "Zoology"),
                 ("ENG", "English"), ("SAN", "Sanskrit"), ("CIV", "Civics"),
                 ("ECO", "Economics"), ("COM", "Commerce")]
    subjects = {}
    for code, name in subj_defs:
        s = models.Subject(code=code, name=name)
        subjects[code] = s
        db.add(s)
    db.flush()

    # ---------------- staff (codes from the filled sheet + Eng list) ------
    def staff(name, code, role, emp, subj_codes, campus=None):
        st = models.Staff(name=name, code=code, role=role, employment=emp,
                          home_campus_id=campus.id if campus else None)
        st.subjects = [subjects[c] for c in subj_codes]
        db.add(st)
        return st

    staff("K.S. Rao", "KSR", "LECTURER", "FULL_TIME", ["MT1", "MT2"], ac)
    staff("P.V. Prasad", "PVP", "LECTURER", "FULL_TIME", ["MT1", "MT2"], ac)
    staff("B.R. Reddy", "BRR", "LECTURER", "FULL_TIME", ["MT1", "MT2"], ac)
    staff("Deepak", "DEEPAK", "LECTURER", "FULL_TIME", ["PHY"], ac)
    staff("M.M. Rao", "MMR", "LECTURER", "FULL_TIME", ["PHY"], ac)
    staff("M.N. Rao", "MNR", "LECTURER", "FULL_TIME", ["CHE"], ac)
    staff("Chakali", "CHKL", "LECTURER", "FULL_TIME", ["CHE"], ac)
    staff("Botany Lecturer", "BTL", "LECTURER", "FULL_TIME", ["BOT"], ac)
    staff("Zoology Lecturer", "ZOL", "LECTURER", "FULL_TIME", ["ZOO"], ac)
    # English allocation from the handwritten note on the workload sheet
    staff("V.V.L.N.", "VVLN", "LECTURER", "FULL_TIME", ["ENG"], sar)
    staff("Prabhakar", "PBK", "LECTURER", "FULL_TIME", ["ENG"], sar)
    staff("Anand", "AND", "LECTURER", "PART_TIME", ["ENG"], sar)
    staff("Aravind", "ARV", "LECTURER", "PART_TIME", ["ENG"], sar)
    staff("R.K. (Vocational)", "RK", "LECTURER", "PART_TIME", ["ENG"], sar)
    staff("Sanskrit Lecturer 1", "SAN1", "LECTURER", "FULL_TIME", ["SAN"], ac)
    staff("Sanskrit Lecturer 2", "SAN2", "LECTURER", "FULL_TIME", ["SAN"], sar)
    staff("Civics Lecturer", "CVL", "LECTURER", "FULL_TIME", ["CIV"], sar)
    staff("Economics Lecturer", "ECL", "LECTURER", "FULL_TIME", ["ECO"], sar)
    staff("Commerce Lecturer", "CML", "LECTURER", "FULL_TIME", ["COM"], sar)
    # Junior Lecturers for study-hour supervision (JL allocation)
    for i in range(1, 7):
        staff(f"Junior Lecturer {i}", f"JL{i}", "JL", "FULL_TIME", [],
              ac if i <= 3 else sar)
    db.flush()

    # ---------------- sections ----------------
    def section(campus, name, stream, order):
        sec = models.Section(campus_id=campus.id, name=name, stream=stream,
                             sort_order=order)
        db.add(sec)
        return sec

    ac_secs = {}
    for i, (n, st) in enumerate([("VJE1", "MAINS"), ("VJE21", "EAMCET"),
                                 ("VJM", "BIPC"), ("VSE1", "MAINS"),
                                 ("VSE21", "EAMCET"), ("VSM", "BIPC"),
                                 ("VJE22", "EAMCET"), ("VSE22", "EAMCET")]):
        ac_secs[n] = section(ac, n, st, i)

    sar_names = ["VJE1", "VJE21", "VJE22", "VJM", "VSM", "VSE1", "VSE21",
                 "VSE22", "VJE3", "VSE3", "GJE1", "GJE2", "GSE1", "GSE2",
                 "BJE1", "BSE1", "BJA", "BSA"]
    sar_secs = {}
    for i, n in enumerate(sar_names):
        stream = "CEC" if n in ("BJA", "BSA") else "MPC"
        sar_secs[n] = section(sar, n, stream, i)
    for i, n in enumerate(["VIJE1", "VIJE2", "VIJE3"]):
        section(vys, n, "MPC", i)
    for i, n in enumerate(["CVSE1", "CVSE2"]):
        section(cvr, n, "MPC", i)
    db.flush()

    # ---------------- requirements (workload sheet, in halves) ----------
    # 2 periods = 4 halves, 1.5 = 3, 1 = 2, 0.5 = 1
    def req(sec, pairs):
        for code, halves in pairs:
            db.add(models.Requirement(section_id=sec.id,
                                      subject_id=subjects[code].id,
                                      halves_per_day=halves))

    mains = [("MT1", 4), ("MT2", 4), ("PHY", 4), ("CHE", 4),
             ("ENG", 2), ("SAN", 1)]
    eamcet = [("MT1", 3), ("MT2", 3), ("PHY", 3), ("CHE", 3),
              ("ENG", 2), ("SAN", 1)]
    bipc = [("BOT", 3), ("ZOO", 3)]
    req(ac_secs["VJE1"], mains)
    req(ac_secs["VSE1"], mains)
    for n in ("VJE21", "VJE22", "VSE21", "VSE22"):
        req(ac_secs[n], eamcet)
    req(ac_secs["VJM"], bipc)
    req(ac_secs["VSM"], bipc)

    std = [("MT1", 3), ("MT2", 3), ("PHY", 2), ("CHE", 2),
           ("ENG", 2), ("SAN", 1)]
    cec = [("CIV", 2), ("ECO", 2), ("COM", 2), ("ENG", 2), ("SAN", 1)]
    for n, sec in sar_secs.items():
        req(sec, cec if n in ("BJA", "BSA") else std)

    # ---------------- users ----------------
    db.add(models.User(username="admin",
                       password_hash=hash_password("admin123"),
                       role="ADMIN"))
    db.add(models.User(username="operator",
                       password_hash=hash_password("operator123"),
                       role="OPERATOR"))
    db.commit()
