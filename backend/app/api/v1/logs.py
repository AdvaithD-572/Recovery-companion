from uuid import UUID
from datetime import date, timedelta
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient, DailyLog, DigitalTwin
from app.schemas import DailyLogCreate, DailyLogResponse, TrendResponse, TrendDataPoint
from app.services.twin_service import get_expected_range
from app.tasks import analyze_trend_task

router = APIRouter()


@router.post("/daily", response_model=DailyLogResponse)
async def submit_daily_log(
    payload: DailyLogCreate,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    # Prevent duplicate submission for same date
    existing = await db.execute(
        select(DailyLog).where(
            and_(DailyLog.patient_id == patient.id, DailyLog.log_date == payload.log_date)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Log already submitted for this date")

    log = DailyLog(
        patient_id=patient.id,
        **payload.model_dump(),
    )
    db.add(log)
    await db.flush()

    # Queue async trend analysis — don't block the response
    analyze_trend_task.delay(str(patient.id), str(log.id))

    return DailyLogResponse.model_validate(log)


@router.get("/daily", response_model=List[DailyLogResponse])
async def get_daily_logs(
    days: int = Query(7, ge=1, le=90),
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyLog)
        .where(and_(DailyLog.patient_id == patient.id, DailyLog.log_date >= since))
        .order_by(DailyLog.log_date.desc())
    )
    return [DailyLogResponse.model_validate(l) for l in result.scalars().all()]


@router.get("/daily/today")
async def get_today_log(
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailyLog).where(
            and_(DailyLog.patient_id == patient.id, DailyLog.log_date == date.today())
        )
    )
    log = result.scalar_one_or_none()
    if log is None:
        return None
    return DailyLogResponse.model_validate(log)


@router.get("/trends/{metric}", response_model=TrendResponse)
async def get_trends(
    metric: str,
    days: int = Query(14, ge=7, le=90),
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Get trend data for a specific metric."""
    score_attr = f"{metric}_score"
    if not hasattr(DailyLog, score_attr):
        raise HTTPException(status_code=400, detail="Invalid metric")

    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyLog)
        .where(and_(DailyLog.patient_id == patient.id, DailyLog.log_date >= since))
        .order_by(DailyLog.log_date)
    )
    logs = result.scalars().all()

    if not logs:
        return TrendResponse(metric=metric, data=[], current_level=0)

    # Get digital twin
    twin_result = await db.execute(
        select(DigitalTwin).where(DigitalTwin.patient_id == patient.id)
    )
    twin = twin_result.scalar_one_or_none()

    data_points = []
    current_level = 0

    for log in logs:
        actual = getattr(log, score_attr, None)
        day_num = (log.log_date - patient.discharge_date).days + 1 if patient.discharge_date else 1
        expected_range = get_expected_range(twin, metric, day_num) if twin else None

        deviation = None
        if actual is not None and expected_range:
            deviation = round(float(actual) - expected_range["expected"], 2)
            
            # Calculate escalation level based on deviation
            abs_deviation = abs(deviation)
            if abs_deviation > 3:
                current_level = max(current_level, 3)
            elif abs_deviation > 2:
                current_level = max(current_level, 2)
            elif abs_deviation > 1:
                current_level = max(current_level, 1)

        point = TrendDataPoint(
            date=log.log_date,
            actual=float(actual) if actual is not None else None,
            expected=expected_range["expected"] if expected_range else None,
            deviation=deviation,
        )
        data_points.append(point)

    return TrendResponse(metric=metric, data=data_points, current_level=current_level)


@router.patch("/daily/{log_id}/clarify")
async def clarify_log(
    log_id: UUID,
    payload: dict,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Patient adds context to a logged day — can suppress a false escalation flag."""
    note = payload.get("note", "")
    
    result = await db.execute(
        select(DailyLog).where(
            and_(DailyLog.id == log_id, DailyLog.patient_id == patient.id)
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    existing_note = log.note or ""
    log.note = f"{existing_note}\n[Context added]: {note}".strip()

    # Mark related flags as clarified
    from app.models import EscalationFlag
    flags_result = await db.execute(
        select(EscalationFlag).where(
            and_(
                EscalationFlag.patient_id == patient.id,
                EscalationFlag.flag_date == log.log_date,
                EscalationFlag.clarified_by_user == False,
            )
        )
    )
    for flag in flags_result.scalars().all():
        flag.clarified_by_user = True
        flag.user_clarification = note
        flag.suppressed = True

    return {"status": "ok", "message": "Context saved. Thank you for letting us know."}
