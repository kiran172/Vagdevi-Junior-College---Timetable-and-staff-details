"""Timetable grid + session booking.

Every booking goes through clash validation inside one transaction.
On a clash the API answers 409 with a human-readable explanation of
exactly what collided, so the frontend can show it in the cell.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession, joinedload
from ..database import get_db
from .. import models, schemas, clash
from ..auth import require_user, require_admin

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


def _session_out(s: models.TTSession) -> dict:
    return {
        "id": s.id, "time_slot_id": s.time_slot_id,
        "subject_id": s.subject_id, "staff_id": s.staff_id,
        "is_study_hour": s.is_study_hour, "half": s.half,
        "locked": s.locked,
        "section_ids": [x.id for x in s.sections],
        "subject_code": s.subject.code if s.subject else None,
        "staff_code": s.staff.code if s.staff else None,
    }


@router.get("")
def get_grid(campus_id: int, db: DbSession = Depends(get_db),
             _u=Depends(require_user)):
    campus = db.get(models.Campus, campus_id)
    if not campus:
        raise HTTPException(404, "Campus not found")
    slots = sorted(campus.time_slots, key=lambda s: s.sort_order)
    sections = sorted(campus.sections, key=lambda s: s.sort_order)
    slot_ids = [s.id for s in slots]
    sessions = (db.query(models.TTSession)
                  .options(joinedload(models.TTSession.sections),
                           joinedload(models.TTSession.subject),
                           joinedload(models.TTSession.staff))
                  .filter(models.TTSession.time_slot_id.in_(slot_ids))
                  .all()) if slot_ids else []
    cells: dict = {}
    for s in sessions:
        out = _session_out(s)
        for sec_id in out["section_ids"]:
            cells.setdefault(str(sec_id), {}) \
                 .setdefault(str(s.time_slot_id), []).append(out)
    return {
        "campus": {"id": campus.id, "name": campus.name},
        "slots": [schemas.TimeSlotOut.model_validate(s) for s in slots],
        "sections": [schemas.SectionOut.model_validate(s) for s in sections],
        "cells": cells,
    }


def validate_and_create(db: DbSession, body: schemas.SessionIn,
                        locked: bool = False) -> models.TTSession:
    """Shared by manual booking and auto-assign commit. Raises HTTPException
    409 with details on any clash. Does NOT commit (caller controls txn)."""
    slot = db.get(models.TimeSlot, body.time_slot_id)
    if not slot:
        raise HTTPException(404, "Time slot not found")
    if slot.kind != "PERIOD":
        raise HTTPException(422, f"{slot.label} is a {slot.kind.lower()}, "
                                 "not a teaching period")
    if not body.section_ids:
        raise HTTPException(422, "Pick at least one section")
    if body.half not in ("FULL", "A", "B"):
        raise HTTPException(422, "half must be FULL, A or B")
    if not body.is_study_hour and not body.subject_id:
        raise HTTPException(422, "Pick a subject (or mark as study hour)")

    if body.staff_id:
        conflict = clash.find_staff_clash(db, body.staff_id, slot, body.half)
        if conflict:
            who = db.get(models.Staff, body.staff_id)
            raise HTTPException(409, f"Clash: {who.code} is already taking "
                                     f"{clash.describe(db, conflict)}")
    for sec_id in body.section_ids:
        conflict = clash.find_section_clash(db, sec_id, slot, body.half)
        if conflict:
            sec = db.get(models.Section, sec_id)
            raise HTTPException(409, f"Clash: section {sec.name} already has "
                                     f"{clash.describe(db, conflict)}")

    sess = models.TTSession(time_slot_id=slot.id, subject_id=body.subject_id,
                            staff_id=body.staff_id,
                            is_study_hour=body.is_study_hour,
                            half=body.half, locked=locked or body.locked)
    sess.sections = db.query(models.Section).filter(
        models.Section.id.in_(body.section_ids)).all()
    db.add(sess)
    return sess


@router.post("/sessions")
def create_session(body: schemas.SessionIn, db: DbSession = Depends(get_db),
                   _u=Depends(require_user)):
    # Manual bookings are locked by default so auto-assign respects them.
    sess = validate_and_create(db, body, locked=True)
    db.commit()
    db.refresh(sess)
    return _session_out(sess)


@router.delete("/sessions/{sid}")
def delete_session(sid: int, db: DbSession = Depends(get_db),
                   _u=Depends(require_user)):
    s = db.get(models.TTSession, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.put("/sessions/{sid}/lock")
def toggle_lock(sid: int, locked: bool, db: DbSession = Depends(get_db),
                _u=Depends(require_user)):
    s = db.get(models.TTSession, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    s.locked = locked
    db.commit()
    return {"ok": True, "locked": s.locked}


@router.post("/clear")
def clear_campus(campus_id: int, include_locked: bool = False,
                 db: DbSession = Depends(get_db), _a=Depends(require_admin)):
    slot_ids = [s.id for s in db.query(models.TimeSlot)
                                .filter_by(campus_id=campus_id).all()]
    q = db.query(models.TTSession).filter(
        models.TTSession.time_slot_id.in_(slot_ids))
    if not include_locked:
        q = q.filter(models.TTSession.locked.is_(False))
    n = 0
    for s in q.all():
        db.delete(s)
        n += 1
    db.commit()
    return {"deleted": n}
