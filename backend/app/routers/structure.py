"""CRUD for the structural entities: campuses, time slots, subjects,
sections. Reads are open to any logged-in user; writes are admin-only
(operators fill timetables, admins shape the structure).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from ..database import get_db
from .. import models, schemas
from ..auth import require_user, require_admin

router = APIRouter(prefix="/api", tags=["structure"])


# ---------------- campuses ----------------
@router.get("/campuses", response_model=list[schemas.CampusOut])
def list_campuses(db: DbSession = Depends(get_db), _u=Depends(require_user)):
    return db.query(models.Campus).order_by(models.Campus.id).all()


@router.post("/campuses", response_model=schemas.CampusOut)
def create_campus(body: schemas.CampusIn, db: DbSession = Depends(get_db),
                  _a=Depends(require_admin)):
    c = models.Campus(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/campuses/{cid}", response_model=schemas.CampusOut)
def update_campus(cid: int, body: schemas.CampusIn,
                  db: DbSession = Depends(get_db), _a=Depends(require_admin)):
    c = db.get(models.Campus, cid)
    if not c:
        raise HTTPException(404, "Campus not found")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/campuses/{cid}")
def delete_campus(cid: int, db: DbSession = Depends(get_db),
                  _a=Depends(require_admin)):
    c = db.get(models.Campus, cid)
    if not c:
        raise HTTPException(404, "Campus not found")
    db.delete(c)
    db.commit()
    return {"ok": True}


# ---------------- time slots ----------------
@router.get("/time-slots", response_model=list[schemas.TimeSlotOut])
def list_slots(campus_id: int | None = None,
               db: DbSession = Depends(get_db), _u=Depends(require_user)):
    q = db.query(models.TimeSlot)
    if campus_id:
        q = q.filter_by(campus_id=campus_id)
    return q.order_by(models.TimeSlot.campus_id,
                      models.TimeSlot.sort_order).all()


@router.post("/time-slots", response_model=schemas.TimeSlotOut)
def create_slot(body: schemas.TimeSlotIn, db: DbSession = Depends(get_db),
                _a=Depends(require_admin)):
    if body.end_min <= body.start_min:
        raise HTTPException(422, "End time must be after start time")
    s = models.TimeSlot(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/time-slots/{sid}", response_model=schemas.TimeSlotOut)
def update_slot(sid: int, body: schemas.TimeSlotIn,
                db: DbSession = Depends(get_db), _a=Depends(require_admin)):
    s = db.get(models.TimeSlot, sid)
    if not s:
        raise HTTPException(404, "Time slot not found")
    if body.end_min <= body.start_min:
        raise HTTPException(422, "End time must be after start time")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/time-slots/{sid}")
def delete_slot(sid: int, db: DbSession = Depends(get_db),
                _a=Depends(require_admin)):
    s = db.get(models.TimeSlot, sid)
    if not s:
        raise HTTPException(404, "Time slot not found")
    used = db.query(models.TTSession).filter_by(time_slot_id=sid).count()
    if used:
        raise HTTPException(409, f"{used} session(s) use this slot. "
                                 "Clear them first.")
    db.delete(s)
    db.commit()
    return {"ok": True}


# ---------------- subjects ----------------
@router.get("/subjects", response_model=list[schemas.SubjectOut])
def list_subjects(db: DbSession = Depends(get_db), _u=Depends(require_user)):
    return db.query(models.Subject).order_by(models.Subject.id).all()


@router.post("/subjects", response_model=schemas.SubjectOut)
def create_subject(body: schemas.SubjectIn, db: DbSession = Depends(get_db),
                   _a=Depends(require_admin)):
    if db.query(models.Subject).filter_by(code=body.code).first():
        raise HTTPException(409, f"Subject code {body.code} already exists")
    s = models.Subject(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/subjects/{sid}")
def delete_subject(sid: int, db: DbSession = Depends(get_db),
                   _a=Depends(require_admin)):
    s = db.get(models.Subject, sid)
    if not s:
        raise HTTPException(404, "Subject not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


# ---------------- sections ----------------
@router.get("/sections", response_model=list[schemas.SectionOut])
def list_sections(campus_id: int | None = None,
                  db: DbSession = Depends(get_db), _u=Depends(require_user)):
    q = db.query(models.Section)
    if campus_id:
        q = q.filter_by(campus_id=campus_id)
    return q.order_by(models.Section.campus_id,
                      models.Section.sort_order).all()


@router.post("/sections", response_model=schemas.SectionOut)
def create_section(body: schemas.SectionIn, db: DbSession = Depends(get_db),
                   _u=Depends(require_user)):
    dup = db.query(models.Section).filter_by(
        campus_id=body.campus_id, name=body.name).first()
    if dup:
        raise HTTPException(409, f"Section {body.name} already exists "
                                 "on this campus")
    s = models.Section(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/sections/{sid}", response_model=schemas.SectionOut)
def update_section(sid: int, body: schemas.SectionIn,
                   db: DbSession = Depends(get_db), _u=Depends(require_user)):
    s = db.get(models.Section, sid)
    if not s:
        raise HTTPException(404, "Section not found")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/sections/{sid}")
def delete_section(sid: int, db: DbSession = Depends(get_db),
                   _a=Depends(require_admin)):
    s = db.get(models.Section, sid)
    if not s:
        raise HTTPException(404, "Section not found")
    db.delete(s)
    db.commit()
    return {"ok": True}
