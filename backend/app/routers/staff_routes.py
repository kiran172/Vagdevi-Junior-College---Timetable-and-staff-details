"""Staff (lecturer + JL) profiles.

Data isolation lives at TWO layers:
1. Response model is chosen by the caller's role: operators get
   StaffOperatorOut, which has no sensitive fields at all.
2. Writes to sensitive fields require admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from ..database import get_db
from .. import models, schemas
from ..auth import require_user, require_admin

router = APIRouter(prefix="/api/staff", tags=["staff"])


def _serialize(staff: models.Staff, role: str):
    cls = schemas.StaffAdminOut if role == "ADMIN" else schemas.StaffOperatorOut
    return cls.model_validate(staff)


@router.get("")
def list_staff(db: DbSession = Depends(get_db),
               user=Depends(require_user)):
    rows = db.query(models.Staff).order_by(models.Staff.role,
                                           models.Staff.code).all()
    return [_serialize(s, user["role"]) for s in rows]


@router.get("/slot-availability")
def slot_availability(slot_id: int, db: DbSession = Depends(get_db),
                      user=Depends(require_user)):
    """Return staff IDs that are blocked for the given slot."""
    rows = db.query(models.StaffAvailability).filter_by(
        time_slot_id=slot_id, available=False).all()
    return {"unavailable_staff_ids": [r.staff_id for r in rows]}


@router.get("/{sid}")
def get_staff(sid: int, db: DbSession = Depends(get_db),
              user=Depends(require_user)):
    s = db.get(models.Staff, sid)
    if not s:
        raise HTTPException(404, "Staff member not found")
    return _serialize(s, user["role"])


def _apply(s: models.Staff, body: schemas.StaffAdminIn, db: DbSession,
           is_admin: bool):
    data = body.model_dump()
    subject_ids = data.pop("subject_ids")
    campus_ids = data.pop("home_campus_ids")
    sensitive = ("salary_discussed", "date_of_interview",
                 "campaign_village_town", "notes_admin")
    for k, v in data.items():
        if k in sensitive and not is_admin:
            continue
        setattr(s, k, v)
    s.subjects = db.query(models.Subject).filter(
        models.Subject.id.in_(subject_ids)).all() if subject_ids else []
    s.home_campuses = db.query(models.Campus).filter(
        models.Campus.id.in_(campus_ids)).all() if campus_ids else []


@router.post("")
def create_staff(body: schemas.StaffAdminIn, db: DbSession = Depends(get_db),
                 user=Depends(require_user)):
    if db.query(models.Staff).filter_by(code=body.code).first():
        raise HTTPException(409, f"Staff code {body.code} already exists")
    s = models.Staff()
    _apply(s, body, db, user["role"] == "ADMIN")
    db.add(s)
    db.commit()
    db.refresh(s)
    return _serialize(s, user["role"])


@router.put("/{sid}")
def update_staff(sid: int, body: schemas.StaffAdminIn,
                 db: DbSession = Depends(get_db), user=Depends(require_user)):
    s = db.get(models.Staff, sid)
    if not s:
        raise HTTPException(404, "Staff member not found")
    dup = db.query(models.Staff).filter(models.Staff.code == body.code,
                                        models.Staff.id != sid).first()
    if dup:
        raise HTTPException(409, f"Staff code {body.code} already exists")
    _apply(s, body, db, user["role"] == "ADMIN")
    db.commit()
    db.refresh(s)
    return _serialize(s, user["role"])


@router.get("/{sid}/availability")
def get_availability(sid: int, db: DbSession = Depends(get_db),
                     user=Depends(require_user)):
    s = db.get(models.Staff, sid)
    if not s:
        raise HTTPException(404, "Staff member not found")
    rows = db.query(models.StaffAvailability).filter_by(staff_id=sid).all()
    unavailable = {r.time_slot_id for r in rows if not r.available}
    return {"slot_ids_unavailable": list(unavailable)}


@router.put("/{sid}/availability")
def set_availability(sid: int, body: schemas.AvailabilityIn,
                     db: DbSession = Depends(get_db),
                     user=Depends(require_user)):
    s = db.get(models.Staff, sid)
    if not s:
        raise HTTPException(404, "Staff member not found")
    db.query(models.StaffAvailability).filter_by(staff_id=sid).delete()
    for slot_id in body.slot_ids_unavailable:
        db.add(models.StaffAvailability(
            staff_id=sid, time_slot_id=slot_id, available=False))
    db.commit()
    return {"ok": True}


@router.delete("/{sid}")
def delete_staff(sid: int, db: DbSession = Depends(get_db),
                 _a=Depends(require_admin)):
    s = db.get(models.Staff, sid)
    if not s:
        raise HTTPException(404, "Staff member not found")
    booked = db.query(models.TTSession).filter_by(staff_id=sid).count()
    if booked:
        raise HTTPException(409, f"{booked} timetable session(s) reference "
                                 "this person. Reassign or clear them first, "
                                 "or mark the profile inactive instead.")
    db.delete(s)
    db.commit()
    return {"ok": True}
