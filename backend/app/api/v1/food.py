from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient, FoodLog
from app.schemas import FoodScanResponse, FoodLogCreate, FoodItem
from app.services.ai_service import AIOrchestrator
from sqlalchemy import select, and_
from datetime import date, datetime, timezone

router = APIRouter()


def get_ai() -> AIOrchestrator:
    return AIOrchestrator()


@router.post("/scan", response_model=FoodScanResponse)
async def scan_meal(
    file: UploadFile = File(...),
    meal_type: str = Form("meal"),
    show_recommendations: bool = Form(False),
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
    ai: AIOrchestrator = Depends(get_ai),
):
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images accepted")

    image_bytes = await file.read(10 * 1024 * 1024 + 1)
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large. Max 10MB.")

    # Identify food items via AI
    food_items_raw = await ai.identify_food(image_bytes, file.content_type)
    food_items = [FoodItem(**f) for f in food_items_raw]

    if not food_items:
        return FoodScanResponse(
            food_items=[],
            interaction_flags=[],
            has_interactions=None,
        )

    # Image identification produces a draft. Clinic rules evaluate the confirmed diary event.
    return FoodScanResponse(food_items=food_items,interaction_flags=[],has_interactions=None)


@router.post("/log", status_code=201)
async def log_food_manually(
    payload: FoodLogCreate,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    food_log = FoodLog(
        patient_id=patient.id,
        logged_at=datetime.now(timezone.utc),
        meal_type=payload.meal_type,
        food_items=[f.model_dump() for f in payload.food_items],
        interaction_flags=[],
        caution_shown=False,
    )
    db.add(food_log)
    await db.flush()

    return {
        "id": str(food_log.id),
        "interaction_flags": [],
        "has_interactions": None,
        "analysis_status": "not_assessed",
    }


@router.get("/log/today")
async def get_today_food_logs(
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    today_start = datetime.combine(date.today(), datetime.min.time())

    result = await db.execute(
        select(FoodLog).where(
            and_(
                FoodLog.patient_id == patient.id,
                FoodLog.logged_at >= today_start,
            )
        ).order_by(FoodLog.logged_at)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "meal_type": l.meal_type,
            "food_items": l.food_items,
            "logged_at": l.logged_at.isoformat(),
            "interaction_flags": l.interaction_flags,
            "has_interactions": True if l.interaction_flags else None,
            "analysis_status": "historical_flags" if l.interaction_flags else "not_assessed",
        }
        for l in logs
    ]
