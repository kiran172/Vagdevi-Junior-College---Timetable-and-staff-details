"""All database tables.

Key design points:
- TimeSlot stores real start/end minutes so clash detection works ACROSS
  campuses even when their period grids differ (AC Campus 8.00-8.45 vs
  Saraswathi 8.10-9.00 still collide for the same lecturer).
- TTSession links to one slot + one lecturer, and to one OR MORE sections
  via SessionSection (combined classes, e.g. VJM merged into VJE1).
- `half` supports split periods: FULL, A (first half), B (second half).
  This is how ENG/SAN or CHE(MNR)/PHY(MMR) share one period.
- `locked` sessions survive auto-assign wipes (manual tweaks are safe).
- Staff sensitive columns (salary_discussed, date_of_interview,
  campaign_village_town) exist here but are stripped for operators in
  schemas.py - never queried separately, just filtered at the DTO layer.
"""
from sqlalchemy import (Column, Integer, String, Boolean, Float, ForeignKey,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from .database import Base


class Campus(Base):
    __tablename__ = "campuses"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    location = Column(String, default="")
    sections = relationship("Section", back_populates="campus",
                            cascade="all, delete-orphan")
    time_slots = relationship("TimeSlot", back_populates="campus",
                              cascade="all, delete-orphan",
                              order_by="TimeSlot.sort_order")


class TimeSlot(Base):
    __tablename__ = "time_slots"
    id = Column(Integer, primary_key=True)
    campus_id = Column(Integer, ForeignKey("campuses.id"), nullable=False)
    label = Column(String, nullable=False)          # "8.00-8.45"
    start_min = Column(Integer, nullable=False)     # minutes from midnight
    end_min = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False)
    kind = Column(String, default="PERIOD")         # PERIOD | BREAK | LUNCH | DINNER
    campus = relationship("Campus", back_populates="time_slots")


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)   # MT1, PHY, SAN...
    name = Column(String, nullable=False)


class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)   # KSR, MNR, DEEPAK...
    phone_number = Column(String, default="")
    role = Column(String, default="LECTURER")            # LECTURER | JL
    employment = Column(String, default="FULL_TIME")     # FULL_TIME | PART_TIME
    active = Column(Boolean, default=True)
    # ---- admin-only fields (hidden from operators at the schema layer) ----
    salary_discussed = Column(Float, nullable=True)
    date_of_interview = Column(String, nullable=True)
    campaign_village_town = Column(String, nullable=True)
    notes_admin = Column(String, nullable=True)

    subjects = relationship("Subject", secondary="staff_subjects")
    home_campuses = relationship("Campus", secondary="staff_campuses")
    availability = relationship("StaffAvailability", cascade="all, delete-orphan")

    @property
    def home_campus_ids(self):
        return [c.id for c in self.home_campuses]


class StaffSubject(Base):
    __tablename__ = "staff_subjects"
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"),
                      primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"),
                        primary_key=True)


class StaffCampus(Base):
    """Many-to-many: a staff member can belong to multiple home campuses."""
    __tablename__ = "staff_campuses"
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"),
                      primary_key=True)
    campus_id = Column(Integer, ForeignKey("campuses.id", ondelete="CASCADE"),
                       primary_key=True)


class StaffAvailability(Base):
    """Per-slot availability override. Absence = available (default open).
    A row with available=False means the staff member is NOT free that slot.
    """
    __tablename__ = "staff_availability"
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"),
                      primary_key=True)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id", ondelete="CASCADE"),
                          primary_key=True)
    available = Column(Boolean, default=True, nullable=False)


class Section(Base):
    __tablename__ = "sections"
    id = Column(Integer, primary_key=True)
    campus_id = Column(Integer, ForeignKey("campuses.id"), nullable=False)
    name = Column(String, nullable=False)        # VJE1, VSE21, GJE2...
    stream = Column(String, default="")          # MAINS | EAMCET | BIPC | CEC...
    sort_order = Column(Integer, default=0)
    campus = relationship("Campus", back_populates="sections")
    __table_args__ = (UniqueConstraint("campus_id", "name"),)


class Requirement(Base):
    """How many periods/day of each subject a section needs (image 3 sheet).
    Stored in HALVES so 1.5 periods = 3 halves, Sanskrit 0.5 = 1 half.
    """
    __tablename__ = "requirements"
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"),
                        nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"),
                        nullable=False)
    halves_per_day = Column(Integer, nullable=False, default=2)
    preferred_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    __table_args__ = (UniqueConstraint("section_id", "subject_id"),)


class TTSession(Base):
    __tablename__ = "timetable_sessions"
    id = Column(Integer, primary_key=True)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    is_study_hour = Column(Boolean, default=False)
    half = Column(String, default="FULL")        # FULL | A | B
    locked = Column(Boolean, default=False)      # locked = survives auto-assign
    time_slot = relationship("TimeSlot")
    subject = relationship("Subject")
    staff = relationship("Staff")
    sections = relationship("Section", secondary="session_sections")


class SessionSection(Base):
    __tablename__ = "session_sections"
    session_id = Column(Integer,
                        ForeignKey("timetable_sessions.id", ondelete="CASCADE"),
                        primary_key=True)
    section_id = Column(Integer,
                        ForeignKey("sections.id", ondelete="CASCADE"),
                        primary_key=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="OPERATOR")    # ADMIN | OPERATOR
