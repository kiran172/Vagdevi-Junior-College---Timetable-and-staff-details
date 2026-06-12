"""App entrypoint. Run with:  uvicorn app.main:app --reload"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine, SessionLocal
from .seed import seed_if_empty
from .routers import auth_routes, structure, staff_routes, timetable, planning

app = FastAPI(title="Vagdevi Timetable API", version="1.0.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


init_db()


app.include_router(auth_routes.router)
app.include_router(structure.router)
app.include_router(staff_routes.router)
app.include_router(timetable.router)
app.include_router(planning.router)


@app.get("/api/health")
def health():
    return {"ok": True}
