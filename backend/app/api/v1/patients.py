"""patients.py"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient, Reminder

router = APIRouter()


@router.post("/onboarding/step/{step}")
async def onboarding_step(
    step: int,
    payload: dict,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    from pydantic import ValidationError
    from app.schemas import OnboardingStep1, OnboardingStep2, OnboardingStep3, OnboardingStep4
    schema = {1:OnboardingStep1, 2:OnboardingStep2, 3:OnboardingStep3, 4:OnboardingStep4}.get(step)
    if schema is None:
        raise HTTPException(404, "Unknown discharge step")
    try:
        payload = schema.model_validate(payload).model_dump(mode="json")
    except ValidationError as exc:
        errors = [{"field":".".join(map(str,item["loc"])), "message":item["msg"]} for item in exc.errors(include_input=False,include_context=False)]
        raise HTTPException(422, errors) from None
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
        if not patient.dob or not patient.discharge_date or not patient.primary_condition:
            raise HTTPException(422, "Complete your birth date and discharge details first")
        changed = await db.execute(update(Patient).where(
            Patient.id == patient.id, Patient.onboarding_complete.is_(False)).values(onboarding_complete=True))
        if not changed.rowcount:
            return {"status":"ok","step":4,"onboarding_complete":True}
        from app.care import add_entry
        note = str(payload.get("discharge_instructions") or "").strip()
        if note:
            add_entry(db,patient.id,None,"instructions",patient.id,{"text":note[:4000]})
        from app.models import Prescription
        from app.schemas import PrescriptionCreate
        from pydantic import ValidationError
        try:
            for raw in payload.get("prescriptions", []):
                rx = PrescriptionCreate.model_validate(raw)
                db.add(Prescription(patient_id=patient.id, doses_remaining=rx.total_doses_bought, **rx.model_dump()))
        except ValidationError:
            raise HTTPException(422, "Invalid prescription")
        patient.emergency_contact = payload.get('emergency_contact')
        patient.onboarding_complete = True
        db.add(Reminder(patient_id=patient.id, reminder_type="checkin",
                        scheduled_time="19:00", days_of_week=list(range(7))))

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
