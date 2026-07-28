"""Prescriptions API Router"""
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient, Prescription, DoseLog
from app.schemas import PrescriptionCreate, PrescriptionResponse, DoseLogCreate
from datetime import datetime, timezone

router = APIRouter()


@router.get("/", response_model=List[PrescriptionResponse])
async def list_prescriptions(
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Prescription)
        .where(Prescription.patient_id == patient.id)
        .order_by(Prescription.is_compulsory.desc(), Prescription.drug_name)
    )
    prescriptions = result.scalars().all()
    results = []
    for rx in prescriptions:
        rx_dict = {
            "id": rx.id,
            "drug_name": rx.drug_name,
            "generic_name": getattr(rx, "generic_name", None),
            "dosage": rx.dosage,
            "frequency": rx.frequency,
            "is_compulsory": rx.is_compulsory,
            "total_doses_bought": rx.total_doses_bought,
            "doses_remaining": rx.doses_remaining,
            "refill_threshold": rx.refill_threshold,
            "start_date": rx.start_date,
            "end_date": rx.end_date,
            "notes": getattr(rx, "notes", None),
            "needs_refill": rx.doses_remaining <= rx.refill_threshold,
        }
        results.append(PrescriptionResponse.model_validate(rx_dict))
    return results


@router.post("/", response_model=PrescriptionResponse, status_code=201)
async def add_prescription(
    payload: PrescriptionCreate,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    rx = Prescription(
        patient_id=patient.id,
        doses_remaining=payload.total_doses_bought,
        **payload.model_dump(),
    )
    db.add(rx)
    await db.flush()
    return PrescriptionResponse.model_validate(rx)


@router.post("/scan-ocr", response_model=List[PrescriptionResponse])
async def scan_prescription_ocr(
    file: UploadFile = File(...),
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """OCR a prescription image and extract medication list."""
    from app.services.ai_service import AIOrchestrator
    from app.utils.s3 import upload_to_s3

    from google.genai import types

    image_bytes = await file.read()
    ai = AIOrchestrator()

    prompt = """Extract all medications from this prescription.
Return ONLY JSON array:
[{"drug_name": "...", "dosage": "...", "frequency": {"times": ["08:00"], "condition": null}, "is_compulsory": true, "duration_days": 7}]
If dosage unclear, use "as prescribed". If frequency unclear, use {"times": ["08:00"], "condition": null}."""

    response = ai.client.models.generate_content(
        model=ai.model,
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=file.content_type)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=600,
        )
    )

    try:
        import json
        medications = json.loads(response.text.strip())
    except:
        medications = []

    created = []
    from datetime import date, timedelta
    for med in medications:
        duration = med.pop('duration_days', 14)
        rx = Prescription(
            patient_id=patient.id,
            drug_name=med.get('drug_name', 'Unknown'),
            dosage=med.get('dosage', 'As prescribed'),
            frequency=med.get('frequency', {"times": ["08:00"]}),
            is_compulsory=med.get('is_compulsory', True),
            total_doses_bought=duration * len(med.get('frequency', {}).get('times', ['08:00'])),
            doses_remaining=duration * len(med.get('frequency', {}).get('times', ['08:00'])),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=duration),
        )
        db.add(rx)
        await db.flush()
        created.append(PrescriptionResponse.model_validate(rx))

    return created


@router.post("/dose-log", status_code=201)
async def log_dose(
    payload: DoseLogCreate,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    # Verify prescription belongs to patient
    result = await db.execute(
        select(Prescription).where(
            and_(Prescription.id == payload.prescription_id, Prescription.patient_id == patient.id)
        )
    )
    rx = result.scalar_one_or_none()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    dose_log = DoseLog(
        prescription_id=payload.prescription_id,
        patient_id=patient.id,
        scheduled_time=payload.scheduled_time,
        taken_at=datetime.now(timezone.utc) if payload.taken else None,
        skipped=not payload.taken,
        skip_reason=payload.skip_reason,
    )
    db.add(dose_log)

    # Decrement remaining doses
    if payload.taken and rx.doses_remaining > 0:
        rx.doses_remaining -= 1

    return {"status": "ok", "doses_remaining": rx.doses_remaining}
