"""reminders.py"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient, Reminder
from app.schemas import ReminderCreate, ReminderResponse

router = APIRouter()


@router.get("/", response_model=List[ReminderResponse])
async def list_reminders(
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder)
        .where(Reminder.patient_id == patient.id)
        .order_by(Reminder.reminder_type, Reminder.scheduled_time)
    )
    return [ReminderResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    payload: ReminderCreate,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(patient_id=patient.id, **payload.model_dump())
    db.add(reminder)
    await db.flush()
    return ReminderResponse.model_validate(reminder)


@router.patch("/{reminder_id}/toggle")
async def toggle_reminder(
    reminder_id: UUID,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(
            and_(Reminder.id == reminder_id, Reminder.patient_id == patient.id)
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder.is_active = not reminder.is_active
    return {"is_active": reminder.is_active}


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    reminder_id: UUID,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(
            and_(Reminder.id == reminder_id, Reminder.patient_id == patient.id)
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await db.delete(reminder)


@router.patch("/{reminder_id}")
async def set_active(reminder_id: UUID, payload: dict, patient=Depends(get_current_patient),db=Depends(get_db)):
    if type(payload.get("is_active")) is not bool:
        raise HTTPException(422, "is_active must be true or false")
    reminder=await db.scalar(select(Reminder).where(Reminder.id==reminder_id,Reminder.patient_id==patient.id))
    if not reminder:
        raise HTTPException(404,"Reminder unavailable")
    reminder.is_active=payload["is_active"]
    return {"is_active":reminder.is_active}
