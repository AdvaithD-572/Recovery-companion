"""patients.py"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient, Reminder
from app.schemas import ReminderCreate, ReminderResponse
from app.services.twin_service import build_digital_twin

router = APIRouter()


@router.post("/onboarding/step/{step}")
async def onboarding_step(
    step: int,
    payload: dict,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    if step == 1:
        patient.dob = date.fromisoformat(payload['dob'])
        patient.gender = payload.get('gender')
        patient.height_cm = payload.get('height_cm')
        patient.weight_kg = payload.get('weight_kg')
        patient.living_situation = payload.get('living_situation')

    elif step == 2:
        patient.primary_condition = payload.get('primary_condition')
        patient.surgery_type = payload.get('surgery_type')
        patient.discharge_date = date.fromisoformat(payload['discharge_date'])
        patient.chronic_diseases = payload.get('chronic_diseases', [])
        patient.allergies = payload.get('allergies', [])

    elif step == 3:
        patient.eating_habits = payload.get('eating_habits')
        patient.exercise_frequency = payload.get('exercise_frequency')
        patient.smoking = payload.get('smoking', False)
        patient.alcohol = payload.get('alcohol', False)
        patient.sleep_baseline = payload.get('sleep_baseline')
        patient.mood_baseline = payload.get('mood_baseline')

    elif step == 4:
        patient.emergency_contact = payload.get('emergency_contact')
        patient.onboarding_complete = True
        await build_digital_twin(db, patient)

        for r in [
            Reminder(patient_id=patient.id, reminder_type="checkin",
                     scheduled_time="19:00", days_of_week=list(range(7))),
            Reminder(patient_id=patient.id, reminder_type="water",
                     scheduled_time="10:00", days_of_week=list(range(7))),
            Reminder(patient_id=patient.id, reminder_type="water",
                     scheduled_time="14:00", days_of_week=list(range(7))),
        ]:
            db.add(r)

    await db.flush()
    return {"status": "ok", "step": step, "onboarding_complete": patient.onboarding_complete}


@router.get("/me")
async def get_me(patient: Patient = Depends(get_current_patient)):
    return {
        "id": str(patient.id),
        "full_name": patient.full_name,
        "email": patient.email,
        "primary_condition": patient.primary_condition,
        "surgery_type": patient.surgery_type,
        "discharge_date": patient.discharge_date.isoformat() if patient.discharge_date else None,
        "recovery_day": (date.today() - patient.discharge_date).days + 1 if patient.discharge_date else None,
        "onboarding_complete": patient.onboarding_complete,
        "preferred_language": patient.preferred_language,
    }


@router.patch("/fcm-token")
async def update_fcm_token(
    data: dict,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    patient.fcm_token = data.get("token")
    return {"status": "ok"}
