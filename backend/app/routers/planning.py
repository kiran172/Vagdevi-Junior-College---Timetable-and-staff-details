"""Requirements (the workload sheet), auto-assign preview/commit, and
workload summaries.
"""
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from ..database import get_db
from .. import models, schemas
from ..auth import require_user
from ..engine import run_engine
from .timetable import validate_and_create

router = APIRouter(prefix="/api", tags=["planning"])


# ---------------- requirements ----------------
@router.get("/requirements", response_model=list[schemas.RequirementOut])
def list_requirements(campus_id: int | None = None,
                      db: DbSession = Depends(get_db),
                      _u=Depends(require_user)):
    q = db.query(models.Requirement).join(models.Section)
    if campus_id:
        q = q.filter(models.Section.campus_id == campus_id)
    return q.all()


@router.post("/requirements", response_model=schemas.RequirementOut)
def upsert_requirement(body: schemas.RequirementIn,
                       db: DbSession = Depends(get_db),
                       _u=Depends(require_user)):
    if body.halves_per_day < 0:
        raise HTTPException(422, "Periods per day cannot be negative")
    r = db.query(models.Requirement).filter_by(
        section_id=body.section_id, subject_id=body.subject_id).first()
    if body.halves_per_day == 0:
        if r:
            db.delete(r)
            db.commit()
        return schemas.RequirementOut(id=0, section_id=body.section_id,
                                      subject_id=body.subject_id,
                                      halves_per_day=0,
                                      preferred_staff_id=None)
    if not r:
        r = models.Requirement(section_id=body.section_id,
                               subject_id=body.subject_id)
        db.add(r)
    r.halves_per_day = body.halves_per_day
    r.preferred_staff_id = body.preferred_staff_id
    db.commit()
    db.refresh(r)
    return r


# ---------------- auto-assign ----------------
@router.post("/autoassign/preview", response_model=schemas.AutoAssignPreview)
def preview(body: schemas.AutoAssignRequest, db: DbSession = Depends(get_db),
            _u=Depends(require_user)):
    try:
        proposal, unfilled, stats = run_engine(db, body.campus_id,
                                               body.clear_existing)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"proposal": proposal, "unfilled": unfilled, "stats": stats}


@router.post("/autoassign/commit")
def commit(body: schemas.AutoAssignCommit, db: DbSession = Depends(get_db),
           _u=Depends(require_user)):
    """Writes the previewed proposal in ONE transaction. If anything in it
    clashes (e.g. another operator booked something between preview and
    commit), the whole thing rolls back untouched and you get a 409."""
    slot_ids = [s.id for s in db.query(models.TimeSlot)
                                .filter_by(campus_id=body.campus_id).all()]
    if body.clear_existing:
        q = (db.query(models.TTSession)
               .filter(models.TTSession.time_slot_id.in_(slot_ids))
               .filter(models.TTSession.locked.is_(False)))
        for s in q.all():
            db.delete(s)
        db.flush()
    try:
        for item in body.proposal:
            validate_and_create(db, schemas.SessionIn(**item.model_dump()),
                                locked=False)
            db.flush()
    except HTTPException as e:
        db.rollback()
        raise HTTPException(409, f"Commit rolled back, nothing changed. "
                                 f"Reason: {e.detail}. Run preview again.")
    db.commit()
    return {"ok": True, "created": len(body.proposal)}


# ---------------- workload summaries ----------------
@router.get("/workload/staff")
def staff_workload(db: DbSession = Depends(get_db), _u=Depends(require_user)):
    """Periods per lecturer per subject across ALL campuses (halves -> 0.5)."""
    rows = db.query(models.TTSession).filter(
        models.TTSession.staff_id.isnot(None)).all()
    agg = defaultdict(lambda: defaultdict(float))
    for s in rows:
        key = s.staff_id
        weight = 0.5 if s.half in ("A", "B") else 1.0
        label = s.subject.code if s.subject else "SH"
        agg[key][label] += weight
    out = []
    for st in db.query(models.Staff).filter_by(active=True).all():
        per_subject = dict(agg.get(st.id, {}))
        out.append({"staff_id": st.id, "code": st.code, "name": st.name,
                    "role": st.role, "per_subject": per_subject,
                    "total": sum(per_subject.values())})
    out.sort(key=lambda x: -x["total"])
    return out


@router.get("/workload/sections")
def section_workload(campus_id: int, db: DbSession = Depends(get_db),
                     _u=Depends(require_user)):
    """The image-3 sheet, computed live: periods per section per subject,
    requirement vs actually scheduled."""
    sections = (db.query(models.Section)
                  .filter_by(campus_id=campus_id)
                  .order_by(models.Section.sort_order).all())
    subjects = db.query(models.Subject).order_by(models.Subject.id).all()
    reqs = (db.query(models.Requirement).join(models.Section)
              .filter(models.Section.campus_id == campus_id).all())
    req_map = {(r.section_id, r.subject_id): r.halves_per_day / 2 for r in reqs}

    slot_ids = [s.id for s in db.query(models.TimeSlot)
                                .filter_by(campus_id=campus_id).all()]
    sessions = (db.query(models.TTSession)
                  .filter(models.TTSession.time_slot_id.in_(slot_ids))
                  .all()) if slot_ids else []
    actual = defaultdict(float)
    sh_actual = defaultdict(float)
    for s in sessions:
        weight = 0.5 if s.half in ("A", "B") else 1.0
        for sec in s.sections:
            if s.is_study_hour:
                sh_actual[sec.id] += weight
            elif s.subject_id:
                actual[(sec.id, s.subject_id)] += weight
    rows = []
    for sec in sections:
        cells = {}
        for subj in subjects:
            r = req_map.get((sec.id, subj.id), 0)
            a = actual.get((sec.id, subj.id), 0)
            if r or a:
                cells[subj.code] = {"required": r, "scheduled": a}
        rows.append({"section_id": sec.id, "section": sec.name,
                     "cells": cells, "study_hours": sh_actual.get(sec.id, 0),
                     "total_required": sum(c["required"] for c in cells.values()),
                     "total_scheduled": sum(c["scheduled"] for c in cells.values())})
    return {"subjects": [s.code for s in subjects], "rows": rows}
