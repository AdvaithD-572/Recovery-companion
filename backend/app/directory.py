"""Station administrator directory and authenticated patient account closure."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.care import Entry, Invite, Link, Staff
from app.core.database import get_db
from app.core.security import (bearer_scheme, create_access_token, decode_token, get_current_patient,
                               hash_password, verify_password)
from app.models import (Clinician, DailyLog, DigitalTwin, DoseLog, EscalationFlag, FoodLog, Patient,
                        Prescription, Reminder)
from app.registry import Administrator, Clinic, ClosedProfile, DirectoryAudit, utcnow
from app.schemas import LoginRequest

router = APIRouter(prefix="/api/v1")


def audit(db, actor, action, target=None):
    db.add(DirectoryAudit(actor=actor, action=action, target=target))


async def administrator(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db=Depends(get_db)):
    claims = decode_token(credentials.credentials)
    if claims.get("type") == "refresh" or claims.get("role") != "administrator":
        raise HTTPException(403, "Station administrator access required")
    account = await db.get(Administrator, UUID(claims["sub"]))
    if not account:
        raise HTTPException(401, "Account unavailable")
    return account


@router.post("/admin/login")
async def login(body: LoginRequest, db=Depends(get_db)):
    account = await db.scalar(select(Administrator).where(Administrator.email == body.email.lower()))
    if not account or not verify_password(body.password, account.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    audit(db, account.id, "administrator_login")
    return {"access_token": create_access_token(str(account.id), "administrator")}


class NewClinic(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    staff_name: str = Field(min_length=2, max_length=120)
    staff_email: EmailStr
    staff_password: str = Field(min_length=12, max_length=72)


@router.post("/admin/clinics", status_code=201)
async def create_clinic(body: NewClinic, admin=Depends(administrator), db=Depends(get_db)):
    name, staff_name = body.name.strip(), body.staff_name.strip()
    if not name or len(staff_name) < 2 or len(body.staff_password.encode()) > 72:
        raise HTTPException(422, "Enter a clinic name, clinician name and password of at most 72 bytes.")
    clinic = Clinic(name=name, scope=str(uuid4()))
    staff = Clinician(full_name=staff_name, email=body.staff_email.lower(),
                      hashed_password=hash_password(body.staff_password))
    db.add_all([clinic, staff])
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(409, "Clinic name or staff email is already in use.")
    db.add(Staff(id=staff.id, clinic=clinic.scope, role="clinician"))
    audit(db, admin.id, "clinic_created", clinic.id)
    return {"id": clinic.id, "name": name}


@router.get("/admin/clinics")
async def list_clinics(admin=Depends(administrator), db=Depends(get_db)):
    clinics = (await db.scalars(select(Clinic).where(Clinic.deleted_at.is_(None))
                                .order_by(Clinic.name))).all()
    audit(db, admin.id, "clinics_listed")
    return [{"id": c.id, "name": c.name} for c in clinics]


@router.delete("/admin/clinics/{cid}", status_code=204)
async def delete_clinic(cid: UUID, admin=Depends(administrator), db=Depends(get_db)):
    clinic = await db.scalar(select(Clinic).where(Clinic.id == cid).with_for_update())
    if not clinic:
        raise HTTPException(404, "Clinic unavailable")
    if clinic.deleted_at is None:
        clinic.deleted_at = utcnow()
        await db.execute(delete(Invite).where(Invite.clinic == clinic.scope))
        await db.execute(delete(Link).where(Link.clinic == clinic.scope))
        accounts = (await db.scalars(select(Clinician).join(Staff, Staff.id == Clinician.id)
                                     .where(Staff.clinic == clinic.scope))).all()
        for account in accounts:
            account.email = "closed:" + str(account.id)
            account.hashed_password = "!"
        await db.execute(delete(Staff).where(Staff.clinic == clinic.scope))
        audit(db, admin.id, "clinic_deleted", cid)
    return Response(status_code=204)


@router.get("/admin/patients")
async def list_patients(offset: int = Query(0, ge=0), q: str = Query("", max_length=200),
                        admin=Depends(administrator), db=Depends(get_db)):
    stmt = (select(Patient, Clinic.name).outerjoin(Link, Link.patient == Patient.id)
            .outerjoin(Clinic, Clinic.scope == Link.clinic)
            .where(~select(ClosedProfile.patient).where(ClosedProfile.patient == Patient.id).exists()))
    if q.strip():
        term = q.strip().lower()
        stmt = stmt.where(func.lower(Patient.full_name).contains(term, autoescape=True) |
                          func.lower(Patient.email).contains(term, autoescape=True))
    rows = (await db.execute(stmt.order_by(Patient.full_name, Patient.id).offset(offset).limit(51))).all()
    audit(db, admin.id, "patient_directory_read")
    return {"patients": [{"id": p.id, "name": p.full_name, "email": p.email, "clinic": clinic}
                         for p, clinic in rows[:50]], "more": len(rows) > 50}


@router.get("/admin/patients/{pid}")
async def profile(pid: UUID, admin=Depends(administrator), db=Depends(get_db)):
    p = await db.get(Patient, pid)
    if not p or await db.get(ClosedProfile, pid):
        raise HTTPException(404, "Patient unavailable")
    clinic = await db.scalar(select(Clinic.name).join(Link, Link.clinic == Clinic.scope).where(Link.patient == pid))
    audit(db, admin.id, "patient_profile_read", pid)
    fields = ("id", "full_name", "email", "dob", "gender", "height_cm", "weight_kg", "primary_condition",
              "surgery_type", "discharge_date", "allergies", "chronic_diseases", "preferred_language",
              "onboarding_complete")
    return {**{field: getattr(p, field) for field in fields}, "clinic": clinic}


class DeleteOwnProfile(BaseModel):
    password: str = Field(min_length=1, max_length=512)


@router.delete("/patients/me", status_code=204)
async def delete_self(body: DeleteOwnProfile, patient=Depends(get_current_patient), db=Depends(get_db)):
    if not verify_password(body.password, patient.hashed_password):
        raise HTTPException(403, "Incorrect password")
    pid = patient.id
    await db.execute(delete(Invite).where(Invite.email == patient.email.lower()))
    await db.execute(delete(Link).where(Link.patient == pid))
    for model in (Reminder, DoseLog, Prescription, DailyLog, FoodLog, DigitalTwin, EscalationFlag):
        await db.execute(delete(model).where(model.patient_id == pid))
    await db.execute(delete(Entry).where(Entry.patient == pid,
                     Entry.kind.in_(["instructions", "patient_note", "receipt"])))
    # Keep the ledger's foreign key and historical signed snapshots. Release the
    # login email and clear all demographic, contact and discharge profile fields.
    for column in Patient.__table__.columns:
        if column.nullable:
            setattr(patient, column.name, None)
    patient.full_name = "Deleted profile"
    patient.email = "closed:" + str(pid)
    patient.hashed_password = "!"
    patient.preferred_language = "en"
    patient.smoking = patient.alcohol = patient.onboarding_complete = False
    db.add(ClosedProfile(patient=pid))
    audit(db, pid, "patient_profile_deleted", pid)
    return Response(status_code=204)
