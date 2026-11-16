from typing import List
from uuid import UUID
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import get_current_clinician
from app.models import Clinician, Patient, EscalationFlag, DailyLog, DigitalTwin
from app.schemas import PatientFlagSummary, TrendDataPoint, EscalationFlagResponse

from app.care import Link, Staff

router = APIRouter()


@router.get("/flags", response_model=List[PatientFlagSummary])
async def get_flagged_patients(
    min_level: int = Query(1, ge=1, le=3),
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns only patients with active escalation flags.
    Clinician sees NO raw log data — only AI-summarised insights.
    """
    # Flags from last 7 days, not suppressed
    since = date.today() - timedelta(days=7)

    flags_result = await db.execute(
        select(EscalationFlag)
        .join(Patient, Patient.id == EscalationFlag.patient_id)
        .where(
            and_(
                Patient.id.in_(select(Link.patient).join(Staff, Staff.clinic == Link.clinic).where(Staff.id == clinician.id, Staff.role == "clinician")),
                EscalationFlag.level >= min_level,
                EscalationFlag.flag_date >= since,
                EscalationFlag.suppressed == False,
                EscalationFlag.clinician_reviewed == False,
            )
        )
        .order_by(EscalationFlag.level.desc(), EscalationFlag.flag_date.desc())
    )
    flags = flags_result.scalars().all()

    result = []
    for flag in flags:
        patient_result = await db.execute(select(Patient).where(Patient.id == flag.patient_id))
        patient = patient_result.scalar_one_or_none()
        if not patient:
            continue

        recovery_day = (date.today() - patient.discharge_date).days + 1 if patient.discharge_date else 0

        # Get 7-day trend for the flagged metric
        logs_result = await db.execute(
            select(DailyLog)
            .where(and_(
                DailyLog.patient_id == patient.id,
                DailyLog.log_date >= date.today() - timedelta(days=7),
            ))
            .order_by(DailyLog.log_date)
        )
        logs = logs_result.scalars().all()

        twin_result = await db.execute(select(DigitalTwin).where(DigitalTwin.patient_id == patient.id))
        twin = twin_result.scalar_one_or_none()

        from app.services.twin_service import get_expected_range
        score_attr = f"{flag.metric}_score"
        trend = []
        for log in logs:
            actual = getattr(log, score_attr, None)
            if patient.discharge_date:
                day_num = (log.log_date - patient.discharge_date).days + 1
                er = get_expected_range(twin, flag.metric, day_num) if twin else None
            else:
                er = None
            trend.append(TrendDataPoint(
                date=log.log_date,
                actual=float(actual) if actual is not None else None,
                expected=er["expected"] if er else None,
                deviation=None,
            ))

        result.append(PatientFlagSummary(
            patient_id=patient.id,
            patient_name=patient.full_name,
            recovery_day=recovery_day,
            escalation_level=flag.level,
            primary_metric=flag.metric,
            insight=flag.clinician_summary or f"Sustained {flag.metric} deviation detected.",
            trend_data=trend,
            flag_date=flag.flag_date,
        ))

    return result


@router.patch("/flags/{flag_id}/reviewed")
async def mark_reviewed(
    flag_id: UUID,
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EscalationFlag).join(Patient).where(EscalationFlag.id == flag_id, Patient.id.in_(select(Link.patient).join(Staff, Staff.clinic == Link.clinic).where(Staff.id == clinician.id, Staff.role == "clinician"))))
    flag = result.scalar_one_or_none()
    if flag:
        flag.clinician_reviewed = True
    return {"status": "ok"}


@router.get("/patients")
async def list_patients(
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """All patients assigned to this clinician — high-level only, no raw logs."""
    result = await db.execute(
        select(Patient).where(Patient.id.in_(select(Link.patient).join(Staff, Staff.clinic == Link.clinic).where(Staff.id == clinician.id, Staff.role == "clinician")))
    )
    patients = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "name": p.full_name,
            "condition": p.primary_condition,
            "discharge_date": p.discharge_date.isoformat() if p.discharge_date else None,
            "recovery_day": (date.today() - p.discharge_date).days + 1 if p.discharge_date else None,
            "onboarding_complete": p.onboarding_complete,
        }
        for p in patients
    ]
