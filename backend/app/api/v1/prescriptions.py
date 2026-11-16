"""Prescriptions API Router"""
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, case

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


@router.post("/scan-ocr")
async def scan_prescription_ocr(
    file: UploadFile = File(...),
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """OCR a prescription image and extract medication list."""
    from app.services.ai_service import AIOrchestrator

    from google.genai import types

    if file.content_type not in {"image/jpeg","image/png","image/webp"}:
        raise HTTPException(415,"Upload a JPEG, PNG or WebP image")
    image_bytes = await file.read(10 * 1024 * 1024 + 1)
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413,"Image exceeds 10 MB")
    ai = AIOrchestrator()

    prompt = """Extract all medications from this prescription.
Return ONLY JSON array:
[{"drug_name": "...", "dosage": "...", "frequency": {"times": ["08:00"], "condition": null}, "is_compulsory": true, "duration_days": 7}]
Leave unclear fields empty. Do not guess a dose, time, or duration."""

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

    return [{"drug_name": str(m.get("drug_name") or ""), "dosage": str(m.get("dosage") or ""),
             "requires_review": True} for m in medications if isinstance(m, dict)]


@router.post("/dose-log", status_code=201)
async def log_dose(
    payload: DoseLogCreate,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
    occurred: datetime | None = None,
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

    if rx.is_compulsory:
        from app.care import Entry
        from uuid import uuid5, NAMESPACE_URL
        from sqlalchemy.exc import IntegrityError
        stamp = payload.scheduled_time
        stamp = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
        occurrence = uuid5(NAMESPACE_URL, f"recovery-dose:{rx.id}:{stamp.isoformat()}")
        db.add(Entry(id=occurrence,patient=patient.id,kind="occurrence",actor=str(patient.id),data={}))
        try:
            await db.flush()
        except IntegrityError:
            raise HTTPException(409, "This scheduled dose already has an entry")
    dose_log = DoseLog(
        created_at=datetime.now(timezone.utc),
        prescription_id=payload.prescription_id,
        patient_id=patient.id,
        scheduled_time=payload.scheduled_time,
        taken_at=(occurred or datetime.now(timezone.utc)) if payload.taken else None,
        skipped=not payload.taken,
        skip_reason=payload.skip_reason,
    )
    db.add(dose_log)

    # Decrement remaining doses
    if payload.taken:
        await db.execute(update(Prescription).where(Prescription.id == rx.id).values(
            doses_remaining=case((Prescription.doses_remaining > 0, Prescription.doses_remaining-1),else_=0)))
        await db.refresh(rx)

    return {"status": "ok", "doses_remaining": rx.doses_remaining}
