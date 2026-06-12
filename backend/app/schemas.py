"""Pydantic DTOs.

The data-isolation rule lives here: StaffOperatorOut simply does not have
the sensitive fields, so they can never leak to an operator response, even
if a future query accidentally selects them.
"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    username: str
    role: str


# ---------- campuses & slots ----------
class CampusIn(BaseModel):
    name: str
    location: str = ""


class CampusOut(ORM):
    id: int
    name: str
    location: str


class TimeSlotIn(BaseModel):
    campus_id: int
    label: str
    start_min: int
    end_min: int
    sort_order: int
    kind: str = "PERIOD"


class TimeSlotOut(ORM):
    id: int
    campus_id: int
    label: str
    start_min: int
    end_min: int
    sort_order: int
    kind: str


# ---------- subjects ----------
class SubjectIn(BaseModel):
    code: str
    name: str


class SubjectOut(ORM):
    id: int
    code: str
    name: str


# ---------- staff (the DTO split) ----------
class StaffBaseIn(BaseModel):
    name: str
    code: str
    phone_number: str = ""
    role: str = "LECTURER"
    employment: str = "FULL_TIME"
    home_campus_id: Optional[int] = None
    active: bool = True
    subject_ids: List[int] = []


class StaffAdminIn(StaffBaseIn):
    salary_discussed: Optional[float] = None
    date_of_interview: Optional[str] = None
    campaign_village_town: Optional[str] = None
    notes_admin: Optional[str] = None


class StaffOperatorOut(ORM):
    """What an operator is allowed to see. No salary, no interview data."""
    id: int
    name: str
    code: str
    phone_number: str
    role: str
    employment: str
    home_campus_id: Optional[int]
    active: bool
    subjects: List[SubjectOut] = []


class StaffAdminOut(StaffOperatorOut):
    salary_discussed: Optional[float]
    date_of_interview: Optional[str]
    campaign_village_town: Optional[str]
    notes_admin: Optional[str]


# ---------- sections ----------
class SectionIn(BaseModel):
    campus_id: int
    name: str
    stream: str = ""
    sort_order: int = 0


class SectionOut(ORM):
    id: int
    campus_id: int
    name: str
    stream: str
    sort_order: int


# ---------- requirements ----------
class RequirementIn(BaseModel):
    section_id: int
    subject_id: int
    halves_per_day: int
    preferred_staff_id: Optional[int] = None


class RequirementOut(ORM):
    id: int
    section_id: int
    subject_id: int
    halves_per_day: int
    preferred_staff_id: Optional[int]


# ---------- timetable sessions ----------
class SessionIn(BaseModel):
    time_slot_id: int
    section_ids: List[int]
    subject_id: Optional[int] = None
    staff_id: Optional[int] = None
    is_study_hour: bool = False
    half: str = "FULL"
    locked: bool = False


class SessionOut(ORM):
    id: int
    time_slot_id: int
    subject_id: Optional[int]
    staff_id: Optional[int]
    is_study_hour: bool
    half: str
    locked: bool
    section_ids: List[int] = []


# ---------- auto-assign ----------
class AutoAssignRequest(BaseModel):
    campus_id: int
    clear_existing: bool = True


class ProposalItem(BaseModel):
    time_slot_id: int
    section_ids: List[int]
    subject_id: Optional[int] = None
    staff_id: Optional[int] = None
    is_study_hour: bool = False
    half: str = "FULL"


class AutoAssignPreview(BaseModel):
    proposal: List[ProposalItem]
    unfilled: List[str]
    stats: dict


class AutoAssignCommit(BaseModel):
    campus_id: int
    clear_existing: bool = True
    proposal: List[ProposalItem]
