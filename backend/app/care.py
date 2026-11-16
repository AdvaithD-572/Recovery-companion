"""Clinic enrolment, longitudinal reports and clinician-authored attention rules."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, GUID, get_db
from app.core.security import get_current_clinician, get_current_patient
from app.models import Patient, Clinician, DailyLog, DoseLog, Prescription, FoodLog
from app.registry import Clinic

router = APIRouter(prefix="/api/v1/care")
now = lambda: datetime.now(timezone.utc)


class Staff(Base):
    __tablename__ = "care_staff"
    id = Column(GUID(), ForeignKey("clinicians.id"), primary_key=True)
    clinic = Column(String, nullable=False)
    role = Column(String, nullable=False)


class Invite(Base):
    __tablename__ = "care_invites"
    digest = Column(String, primary_key=True)
    clinic = Column(String, nullable=False)
    email = Column(String, nullable=False)
    expires = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(DateTime(timezone=True))


class Link(Base):
    __tablename__ = "care_links"
    patient = Column(GUID(), ForeignKey("patients.id"), primary_key=True)
    clinic = Column(String, nullable=False, index=True)


class Entry(Base):
    __tablename__ = "care_records"
    id = Column(GUID(), primary_key=True, default=uuid4)
    patient = Column(GUID(), ForeignKey("patients.id"), nullable=False, index=True)
    clinic = Column(String)
    kind = Column(String, nullable=False)
    at = Column(DateTime(timezone=True), default=now, nullable=False)
    actor = Column(String, nullable=False)
    data = Column(JSON, nullable=False)


async def membership(user: Clinician = Depends(get_current_clinician), db: AsyncSession = Depends(get_db)):
    staff = await db.get(Staff, user.id)
    if not staff:
        raise HTTPException(403, "No active clinic membership")
    if not await db.scalar(select(Clinic.id).where(Clinic.scope == staff.clinic,
                           Clinic.deleted_at.is_(None)).with_for_update(read=True)):
        raise HTTPException(403, "Clinic unavailable")
    return staff


async def clinic_name(db, scope):
    return await db.scalar(select(Clinic.name).where(Clinic.scope == scope)) if scope else None


async def linked(pid, staff, db):
    link = await db.get(Link, pid)
    if not link or link.clinic != staff.clinic:
        raise HTTPException(404, "Patient unavailable")
    return await db.get(Patient, pid)


class Destination(BaseModel):
    email: EmailStr


class Code(BaseModel):
    code: str = Field(min_length=16, max_length=120)


class Note(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class Checkup(Note):
    request_id: UUID


class Rule(BaseModel):
    event: Literal["skipped", "food"]
    match: str = Field(min_length=1, max_length=200)
    severity: Literal["Needs review", "Critical"]
    reason: str = Field(min_length=1, max_length=500)


@router.post("/invitations")
async def invite(body: Destination, staff=Depends(membership), db=Depends(get_db)):
    code = token_urlsafe(24)
    db.add(Invite(digest=sha256(code.encode()).hexdigest(), email=body.email.lower(),
                  clinic=staff.clinic, expires=now() + timedelta(hours=24)))
    return {"code": code, "clinic": await clinic_name(db, staff.clinic)}


async def valid_invite(body, patient, db):
    query = select(Invite).where(Invite.digest == sha256(body.code.encode()).hexdigest(),
        Invite.email == patient.email.lower(), Invite.consumed.is_(None), Invite.expires > now())
    invitation = await db.scalar(query)
    if not invitation:
        raise HTTPException(404, "Invitation unavailable")
    if not await db.scalar(select(Clinic.id).where(Clinic.scope == invitation.clinic,
                           Clinic.deleted_at.is_(None)).with_for_update(read=True)):
        raise HTTPException(404, "Invitation unavailable")
    return invitation


@router.post("/invitation/preview")
async def preview(body: Code, patient=Depends(get_current_patient), db=Depends(get_db)):
    invitation = await valid_invite(body, patient, db)
    return {"clinic": await clinic_name(db, invitation.clinic)}


@router.post("/link")
async def connect(body: Code, patient=Depends(get_current_patient), db=Depends(get_db)):
    invitation = await valid_invite(body, patient, db)
    if await db.get(Link, patient.id):
        raise HTTPException(409, "Disconnect the current clinic first")
    consumed = await db.execute(update(Invite).where(Invite.digest == invitation.digest,
        Invite.consumed.is_(None)).values(consumed=now()))
    if consumed.rowcount != 1:
        raise HTTPException(409, "Invitation already used")
    db.add(Link(patient=patient.id, clinic=invitation.clinic))
    add_entry(db,patient.id,invitation.clinic,"sharing_granted",patient.id,{})
    return {"clinic": await clinic_name(db, invitation.clinic)}


@router.delete("/link")
async def disconnect(patient=Depends(get_current_patient), db=Depends(get_db)):
    link = await db.get(Link, patient.id)
    if link:
        add_entry(db,patient.id,link.clinic,"sharing_revoked",patient.id,{})
        await db.delete(link)
    return {"disconnected": True}


@router.get("/patients")
async def roster(staff=Depends(membership), db=Depends(get_db)):
    patients = (await db.scalars(select(Patient).join(Link, Patient.id == Link.patient)
        .where(Link.clinic == staff.clinic).order_by(Patient.full_name))).all()
    return {"clinic": await clinic_name(db, staff.clinic), "role": staff.role, "patients": [
        {"id": p.id, "name": p.full_name, "dob": p.dob, "condition": p.primary_condition} for p in patients]}


def add_entry(db, pid, clinic, kind, actor, data, **kw):
    row = Entry(patient=pid, clinic=clinic, kind=kind, actor=str(actor), data=data, **kw)
    db.add(row)
    return row


@router.post("/instructions")
async def instructions(body: Note, patient=Depends(get_current_patient), db=Depends(get_db)):
    add_entry(db, patient.id, None, "instructions", patient.id, {"text": body.text})
    return {"saved": True}


@router.post("/observations/{kind}/{record_id}/notes")
async def observation_note(kind: Literal["check-in","food","taken","skipped"], record_id: UUID,
                           body: Note, patient=Depends(get_current_patient), db=Depends(get_db)):
    model = {"check-in": DailyLog, "food": FoodLog, "taken": DoseLog, "skipped": DoseLog}[kind]
    row = await db.get(model, record_id)
    if not row or row.patient_id != patient.id:
        raise HTTPException(404, "Diary entry unavailable")
    actual = ("skipped" if row.skipped else "taken") if isinstance(row, DoseLog) else kind
    if actual != kind:
        raise HTTPException(404, "Diary entry unavailable")
    event_time = (row.log_date if kind == "check-in" else row.logged_at if kind == "food"
                  else row.taken_at or row.scheduled_time)
    add_entry(db, patient.id, None, "patient_note", patient.id,
              {"text":body.text, "target":str(record_id), "type":kind, "event_at":event_time.isoformat()})
    return {"saved":True}


@router.post("/patients/{pid}/rules")
async def new_rule(pid: UUID, body: Rule, staff=Depends(membership), db=Depends(get_db)):
    await linked(pid, staff, db)
    if staff.role != "clinician":
        raise HTTPException(403, "Clinician required")
    add_entry(db, pid, staff.clinic, "rule", staff.id, body.model_dump())
    return {"saved": True}


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def timeline(patient, clinic, db, since_visit):
    records = (await db.scalars(select(Entry).where(Entry.patient == patient.id,
        Entry.kind.in_(["visit", "rule", "instructions","receipt","attendance","amendment","patient_note"])).order_by(Entry.at, Entry.id))).all()
    visible = [r for r in records if r.clinic in (None, clinic)]
    visits = [r for r in visible if r.kind == "visit"]
    start = utc(visits[-1].at) if visits and since_visit else None
    lower = start or (datetime.combine(patient.discharge_date, datetime.min.time(), timezone.utc) if patient.discharge_date else None)
    end = now()
    events = []
    def event(at, category, detail, names=(), precision="time", received=None, record_id=None):
        stamp = utc(at)
        before_window = lower and (stamp.date() < lower.date() if precision == "day" else stamp < lower)
        if precision == "day" and start and stamp.date() == start.date() and received and utc(received) < start:
            return
        late = bool(before_window and start and received and utc(received) >= start)
        if stamp > end or (before_window and not late):
            return
        matches = [r for r in visible if r.kind == "rule" and utc(r.at) <= stamp
            and r.data["event"] == category and r.data["match"].strip().casefold() in names]
        # A newer directive for the same item replaces the earlier severity from that time onward.
        active = {r.data["match"].strip().casefold(): r for r in matches}
        best = max(active.values(), key=lambda r: (r.data["severity"] == "Critical", r.at), default=None)
        events.append({"id": record_id, "at": stamp.isoformat() if precision == "time" else stamp.date().isoformat(),
            "late": late, "type": category, "detail": detail, "status": best.data["severity"] if best else
            ("Unable to assess" if category in ("skipped", "food") else "Recorded"),
            "reason": best.data["reason"] if best else "", "rule": str(best.id) if best else None})
    async def rows(model):
        return (await db.scalars(select(model).where(model.patient_id == patient.id))).all()
    meds = {r.id:r for r in await rows(Prescription)}
    for row in await rows(DoseLog):
        med = meds.get(row.prescription_id)
        if med:
            event(row.taken_at or row.scheduled_time, "skipped" if row.skipped else "taken",
                f"{med.drug_name} · {med.dosage}" + (f" · {row.skip_reason}" if row.skip_reason else ""),
                [med.drug_name.strip().casefold()], received=row.created_at, record_id=row.id)
    meals_received = {r.id:r.at for r in records if r.kind == "receipt"}
    for meal in await rows(FoodLog):
        names = [x["name"] for x in meal.food_items]
        event(meal.logged_at, "food", meal.meal_type + " · " + ", ".join(names), [s.strip().casefold() for s in names], received=meals_received.get(meal.id), record_id=meal.id)
    for log in await rows(DailyLog):
        scores = [f"{k} {getattr(log,k+'_score')}/10" for k in ("pain","sleep","appetite","mood","fatigue","mobility","swelling") if getattr(log,k+'_score') is not None]
        event(datetime.combine(log.log_date, datetime.min.time()), "check-in", " · ".join(scores+[log.note or ""]).strip(" ·"), precision="day",received=log.created_at,record_id=log.id)
    for record in visible:
        if record.kind in ("attendance","amendment"):
            event(record.at,record.kind,record.data["text"])
        elif record.kind == "patient_note":
            event(record.at, "Patient correction",
                  f"{record.data['type']} · {record.data['event_at']} · {record.data['text']}")
    return {"name": patient.full_name, "id": patient.id, "dob": patient.dob, "condition": patient.primary_condition,
        "height_cm":patient.height_cm, "weight_kg":patient.weight_kg, "chronic_diseases":patient.chronic_diseases,
        "procedure":patient.surgery_type, "allergies":patient.allergies, "discharged":patient.discharge_date,
        "from":start or patient.discharge_date, "as_of":end, "clinic":await clinic_name(db, clinic),
        "medicines":[{"name":m.drug_name,"dose":m.dosage,"schedule":m.frequency,"compulsory":m.is_compulsory,"notes":m.notes,"start_date":m.start_date,"end_date":m.end_date,"remaining":m.doses_remaining} for m in meds.values()],
        "instructions":[r.data["text"] for r in visible if r.kind=="instructions"],
        "visits":[{"at":r.at,"note":r.data["text"],"id":r.id} for r in visits],
        "events":sorted(events,key=lambda e:e["at"],reverse=True)}


@router.get("/me")
async def records(patient=Depends(get_current_patient), db=Depends(get_db)):
    link=await db.get(Link,patient.id)
    result=await timeline(patient,link.clinic if link else None,db,False)
    history=(await db.scalars(select(Entry).where(Entry.patient==patient.id,Entry.kind.in_(["visit","amendment"])).order_by(Entry.at))).all()
    scopes = {r.clinic for r in history if r.clinic}
    labels = dict((await db.execute(select(Clinic.scope, Clinic.name).where(Clinic.scope.in_(scopes)))).all())
    result["visits"]=[{"at":r.at,"note":r.data["text"],"id":r.id,"clinic":labels.get(r.clinic),"kind":r.kind} for r in history]
    return result


@router.post("/patients/{pid}/reports")
async def report(pid: UUID, staff=Depends(membership), db=Depends(get_db)):
    patient=await linked(pid,staff,db)
    data=jsonable_encoder(await timeline(patient,staff.clinic,db,True))
    snapshot=add_entry(db,pid,staff.clinic,"report",staff.id,data)
    await db.flush()
    return {"id":snapshot.id,"report":data}


@router.get("/patients/{pid}/reports")
async def report_history(pid: UUID, staff=Depends(membership), db=Depends(get_db)):
    await linked(pid, staff, db)
    saved = (await db.execute(select(Entry.id, Entry.at).where(
        Entry.patient == pid, Entry.clinic == staff.clinic, Entry.kind == "report"
    ).order_by(Entry.at.desc()))).all()
    return [{"id": row.id, "at": row.at} for row in saved]


@router.get("/reports/{rid}")
async def reprint(rid: UUID, staff=Depends(membership), db=Depends(get_db)):
    row=await db.get(Entry,rid)
    if not row or row.kind!="report" or row.clinic!=staff.clinic:
        raise HTTPException(404,"Report unavailable")
    await linked(row.patient,staff,db)
    add_entry(db,row.patient,staff.clinic,"report_read",staff.id,{"report":str(row.id)})
    return {"id":row.id,"report":row.data}


@router.post("/reports/{rid}/print")
async def print_report(rid: UUID, staff=Depends(membership), db=Depends(get_db)):
    record = await db.get(Entry, rid)
    if not record or record.kind != "report" or record.clinic != staff.clinic:
        raise HTTPException(404, "Report unavailable")
    await linked(record.patient, staff, db)
    add_entry(db, record.patient, staff.clinic, "print_requested", staff.id, {"report":str(rid)})
    return {"authorized": True}


@router.post("/patients/{pid}/visits")
async def close_visit(pid: UUID, body: Checkup, staff=Depends(membership), db=Depends(get_db)):
    await linked(pid,staff,db)
    if staff.role!="clinician":
        raise HTTPException(403,"Clinician required")
    clinic, actor = staff.clinic, staff.id
    prior = await db.get(Entry, body.request_id)
    if not prior:
        try:
            async with db.begin_nested():
                add_entry(db, pid, clinic, "visit", actor, {"text":body.text}, id=body.request_id)
                await db.flush()
        except IntegrityError:
            prior = await db.get(Entry, body.request_id)
            if not prior:
                raise
    if prior and (prior.patient != pid or prior.clinic != clinic or prior.actor != str(actor)
                  or prior.kind != "visit" or prior.data.get("text") != body.text):
        raise HTTPException(409, "Request identifier conflict")
    return {"id":body.request_id}



class SyncEvent(BaseModel):
    id: UUID
    kind: Literal["daily", "meal", "dose"]
    occurred: datetime
    payload: dict


@router.post("/sync")
async def sync(body: SyncEvent, patient=Depends(get_current_patient), db=Depends(get_db)):
    from app.schemas import DailyLogCreate, FoodLogCreate, DoseLogCreate
    from app.api.v1.logs import submit_daily_log
    from app.api.v1.prescriptions import log_dose
    from pydantic import ValidationError
    if body.occurred.tzinfo is None:
        raise HTTPException(422, "Timestamp needs a timezone")
    patient_id = patient.id
    signature = body.model_dump(mode="json")
    prior = await db.get(Entry, body.id)
    if prior:
        if prior.patient != patient.id or prior.kind != "receipt" or prior.data != signature:
            raise HTTPException(409, "Event identifier conflict")
        return {"saved": True}
    add_entry(db, patient.id, None, "receipt", patient.id, signature, id=body.id)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        prior = await db.get(Entry, body.id)
        if prior and prior.patient == patient_id and prior.kind == "receipt" and prior.data == signature:
            return {"saved": True}
        raise HTTPException(409, "Event identifier conflict")
    try:
        if body.kind == "daily":
            await submit_daily_log(DailyLogCreate.model_validate(body.payload),patient,db)
        elif body.kind == "dose":
            await log_dose(DoseLogCreate.model_validate(body.payload),patient,db,occurred=body.occurred)
        else:
            meal = FoodLogCreate.model_validate(body.payload)
            db.add(FoodLog(id=body.id,patient_id=patient.id, logged_at=body.occurred, meal_type=meal.meal_type,
                food_items=[item.model_dump() for item in meal.food_items], interaction_flags=[]))
    except ValidationError:
        raise HTTPException(422, "Invalid diary entry")
    return {"saved": True}


@router.post("/patients/{pid}/attendance")
async def attendance(pid: UUID, staff=Depends(membership), db=Depends(get_db)):
    await linked(pid,staff,db)
    add_entry(db,pid,staff.clinic,"attendance",staff.id,{"text":"Arrived for follow-up"})
    return {"recorded":True}


@router.post("/visits/{vid}/amendments")
async def amendment(vid: UUID, note: Note, staff=Depends(membership), db=Depends(get_db)):
    visit=await db.get(Entry,vid)
    if not visit or visit.kind!="visit" or visit.clinic!=staff.clinic:
        raise HTTPException(404,"Visit unavailable")
    await linked(visit.patient,staff,db)
    if staff.role!="clinician":
        raise HTTPException(403,"Clinician required")
    add_entry(db,visit.patient,staff.clinic,"amendment",staff.id,{"visit_id":str(vid),"text":note.text})
    return {"saved":True}
