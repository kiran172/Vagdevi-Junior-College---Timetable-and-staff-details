"""Smoke test for the whole API. Run: python test_smoke.py"""
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_smoke.db"
if os.path.exists("test_smoke.db"):
    os.remove("test_smoke.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app)
P = 0


def ok(name, cond, extra=""):
    global P
    P += 1
    print(("PASS" if cond else "FAIL"), name, extra)
    assert cond, name


# ---- auth ----
r = c.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
ok("wrong password rejected", r.status_code == 401)
admin = c.post("/api/auth/login",
               json={"username": "admin", "password": "admin123"}).json()
op = c.post("/api/auth/login",
            json={"username": "operator", "password": "operator123"}).json()
A = {"Authorization": f"Bearer {admin['token']}"}
O = {"Authorization": f"Bearer {op['token']}"}
ok("login works", admin["role"] == "ADMIN" and op["role"] == "OPERATOR")
ok("no token = 401", c.get("/api/staff").status_code == 401)

# ---- staff isolation ----
admin_staff = c.get("/api/staff", headers=A).json()
op_staff = c.get("/api/staff", headers=O).json()
ok("admin sees sensitive fields", "salary_discussed" in admin_staff[0])
ok("operator never sees sensitive fields",
   all("salary_discussed" not in s and "campaign_village_town" not in s
       for s in op_staff))

# operator tries to write salary -> silently ignored
ksr = next(s for s in op_staff if s["code"] == "KSR")
body = {**{k: ksr[k] for k in ("name", "code", "phone_number", "role",
                               "employment", "home_campus_id", "active")},
        "subject_ids": [s["id"] for s in ksr["subjects"]],
        "salary_discussed": 999999}
c.put(f"/api/staff/{ksr['id']}", headers=O, json=body)
after = c.get(f"/api/staff/{ksr['id']}", headers=A).json()
ok("operator cannot write salary", after["salary_discussed"] != 999999)

# operator hitting admin-only route
r = c.delete(f"/api/staff/{ksr['id']}", headers=O)
ok("operator blocked from admin delete", r.status_code == 403)

# ---- structure ----
campuses = c.get("/api/campuses", headers=O).json()
ok("4 campuses seeded", len(campuses) == 4)
ac = next(x for x in campuses if x["name"] == "AC Campus")
sar = next(x for x in campuses if "Saraswathi" in x["name"])
subjects = {s["code"]: s for s in c.get("/api/subjects", headers=O).json()}
sections = c.get("/api/sections", headers=O,
                 params={"campus_id": ac["id"]}).json()
ok("AC sections seeded", len(sections) == 8)
slots = c.get("/api/time-slots", headers=O,
              params={"campus_id": ac["id"]}).json()
periods = [s for s in slots if s["kind"] == "PERIOD"]
ok("AC slots seeded", len(slots) == 18 and len(periods) == 14)

vje1 = next(s for s in sections if s["name"] == "VJE1")
vje21 = next(s for s in sections if s["name"] == "VJE21")
slot1 = periods[2]  # 8.00-8.45
staff_by_code = {s["code"]: s for s in op_staff}

# ---- manual booking + clash detection ----
mk = dict(time_slot_id=slot1["id"], section_ids=[vje1["id"]],
          subject_id=subjects["MT1"]["id"],
          staff_id=staff_by_code["KSR"]["id"], half="FULL")
r = c.post("/api/timetable/sessions", headers=O, json=mk)
ok("manual booking works", r.status_code == 200, r.text[:100])
first_id = r.json()["id"]
ok("manual booking auto-locked", r.json()["locked"] is True)

# same lecturer, same slot, different section -> clash
r = c.post("/api/timetable/sessions", headers=O, json={
    **mk, "section_ids": [vje21["id"]]})
ok("lecturer double-book blocked", r.status_code == 409, r.json()["detail"])

# same SECTION, same slot, different lecturer -> clash (the gap fix)
r = c.post("/api/timetable/sessions", headers=O, json={
    **mk, "staff_id": staff_by_code["PVP"]["id"]})
ok("section double-book blocked", r.status_code == 409)

# split period: A + B coexist in another slot
slot2 = periods[3]
r1 = c.post("/api/timetable/sessions", headers=O, json={
    "time_slot_id": slot2["id"], "section_ids": [vje1["id"]],
    "subject_id": subjects["ENG"]["id"],
    "staff_id": staff_by_code["VVLN"]["id"], "half": "A"})
r2 = c.post("/api/timetable/sessions", headers=O, json={
    "time_slot_id": slot2["id"], "section_ids": [vje1["id"]],
    "subject_id": subjects["SAN"]["id"],
    "staff_id": staff_by_code["SAN1"]["id"], "half": "B"})
ok("split period A+B works", r1.status_code == 200 and r2.status_code == 200)
r3 = c.post("/api/timetable/sessions", headers=O, json={
    "time_slot_id": slot2["id"], "section_ids": [vje1["id"]],
    "subject_id": subjects["PHY"]["id"],
    "staff_id": staff_by_code["DEEPAK"]["id"], "half": "FULL"})
ok("FULL over occupied A+B blocked", r3.status_code == 409)

# CROSS-CAMPUS clash: KSR is busy 8.00-8.45 at AC. Saraswathi 8.10-9.00
# overlaps in real time -> must be blocked even though slot ids differ.
sar_slots = c.get("/api/time-slots", headers=O,
                  params={"campus_id": sar["id"]}).json()
sar_810 = next(s for s in sar_slots if s["label"] == "8.10-9.00")
sar_secs = c.get("/api/sections", headers=O,
                 params={"campus_id": sar["id"]}).json()
r = c.post("/api/timetable/sessions", headers=O, json={
    "time_slot_id": sar_810["id"], "section_ids": [sar_secs[0]["id"]],
    "subject_id": subjects["MT1"]["id"],
    "staff_id": staff_by_code["KSR"]["id"], "half": "FULL"})
ok("CROSS-CAMPUS clash blocked", r.status_code == 409, r.json()["detail"])

# combined class (two sections, one session)
slot3 = periods[4]
vjm = next(s for s in sections if s["name"] == "VJM")
r = c.post("/api/timetable/sessions", headers=O, json={
    "time_slot_id": slot3["id"], "section_ids": [vje1["id"], vjm["id"]],
    "subject_id": subjects["PHY"]["id"],
    "staff_id": staff_by_code["DEEPAK"]["id"], "half": "FULL"})
ok("combined class works", r.status_code == 200 and
   len(r.json()["section_ids"]) == 2)

# ---- auto-assign ----
prev = c.post("/api/autoassign/preview", headers=O,
              json={"campus_id": ac["id"], "clear_existing": True}).json()
ok("preview produced proposal", len(prev["proposal"]) > 0,
   str(prev["stats"]))
print("   unfilled:", prev["unfilled"] or "none")

r = c.post("/api/autoassign/commit", headers=O, json={
    "campus_id": ac["id"], "clear_existing": True,
    "proposal": prev["proposal"]})
ok("commit works", r.status_code == 200, r.text[:120])

grid = c.get("/api/timetable", headers=O,
             params={"campus_id": ac["id"]}).json()
booked_cells = sum(len(v) for sec in grid["cells"].values()
                   for v in sec.values())
ok("grid populated after commit", booked_cells > 50, f"cells={booked_cells}")

# locked manual session survived the wipe
found_locked = any(s["id"] == first_id
                   for sec in grid["cells"].values()
                   for v in sec.values() for s in v)
ok("locked manual session survived auto-assign", found_locked)

# requirements actually satisfied? check section workload
wl = c.get("/api/workload/sections", headers=O,
           params={"campus_id": ac["id"]}).json()
vje1_row = next(r for r in wl["rows"] if r["section"] == "VJE1")
ok("VJE1 fully scheduled",
   vje1_row["total_scheduled"] >= vje1_row["total_required"],
   f"req={vje1_row['total_required']} got={vje1_row['total_scheduled']}")

# no lecturer double-booked anywhere (global audit)
from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.clash import times_overlap, halves_conflict  # noqa: E402
db = SessionLocal()
all_sessions = db.query(models.TTSession).all()
by_staff = {}
for s in all_sessions:
    if s.staff_id:
        by_staff.setdefault(s.staff_id, []).append(s)
violations = 0
for sid, lst in by_staff.items():
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            a, b = lst[i], lst[j]
            if times_overlap(a.time_slot.start_min, a.time_slot.end_min,
                             b.time_slot.start_min, b.time_slot.end_min):
                if halves_conflict(a.half, b.half,
                                   a.time_slot_id == b.time_slot_id):
                    violations += 1
ok("global audit: zero lecturer clashes after auto-assign", violations == 0)

# staff workload endpoint
swl = c.get("/api/workload/staff", headers=O).json()
ok("staff workload computed", swl[0]["total"] > 0,
   f"busiest: {swl[0]['code']} = {swl[0]['total']} periods")

# second campus auto-assign must respect first campus bookings
prev2 = c.post("/api/autoassign/preview", headers=O,
               json={"campus_id": sar["id"], "clear_existing": True}).json()
r = c.post("/api/autoassign/commit", headers=O, json={
    "campus_id": sar["id"], "clear_existing": True,
    "proposal": prev2["proposal"]})
ok("second campus commit works", r.status_code == 200, str(prev2["stats"]))
print("   sar unfilled:", len(prev2["unfilled"]), "items")

# re-audit globally after both campuses
db.expire_all()
all_sessions = db.query(models.TTSession).all()
by_staff = {}
for s in all_sessions:
    if s.staff_id:
        by_staff.setdefault(s.staff_id, []).append(s)
violations = 0
for sid, lst in by_staff.items():
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            a, b = lst[i], lst[j]
            if times_overlap(a.time_slot.start_min, a.time_slot.end_min,
                             b.time_slot.start_min, b.time_slot.end_min):
                if halves_conflict(a.half, b.half,
                                   a.time_slot_id == b.time_slot_id):
                    violations += 1
ok("global audit across BOTH campuses: zero clashes", violations == 0)

print(f"\nAll {P} checks passed.")
