from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from ..database import get_db
from .. import models, schemas
from ..auth import verify_password, make_token, hash_password, require_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginOut)
def login(body: schemas.LoginIn, db: DbSession = Depends(get_db)):
    user = db.query(models.User).filter_by(username=body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")
    return schemas.LoginOut(token=make_token(user.username, user.role),
                            username=user.username, role=user.role)


@router.post("/users")
def create_user(body: schemas.LoginIn, role: str = "OPERATOR",
                db: DbSession = Depends(get_db),
                _admin=Depends(require_admin)):
    if db.query(models.User).filter_by(username=body.username).first():
        raise HTTPException(409, "Username already exists")
    if role not in ("ADMIN", "OPERATOR"):
        raise HTTPException(422, "Role must be ADMIN or OPERATOR")
    db.add(models.User(username=body.username,
                       password_hash=hash_password(body.password), role=role))
    db.commit()
    return {"ok": True}
