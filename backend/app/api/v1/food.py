import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient, FoodLog, Prescription
from app.schemas import FoodScanResponse, FoodLogCreate, FoodItem, InteractionFlag
from app.services.ai_service import AIOrchestrator
from app.utils.s3 import upload_to_s3
from sqlalchemy import select, and_
from datetime import date

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

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large. Max 10MB.")

    # Identify food items via AI
    food_items_raw = await ai.identify_food(image_bytes, file.content_type)
    food_items = [FoodItem(**f) for f in food_items_raw]

    if not food_items:
        return FoodScanResponse(
            food_items=[],
            interaction_flags=[],
            has_interactions=False,
        )

    # Fetch active prescriptions
    rx_result = await db.execute(
        select(Prescription).where(
            and_(Prescription.patient_id == patient.id, Prescription.doses_remaining > 0)
        )
    )
    prescriptions = rx_result.scalars().all()

    # Check interactions
    interactions_raw = await ai.check_drug_food_interactions(
        [f.model_dump() for f in food_items], prescriptions
    )
    interaction_flags = [InteractionFlag(**i) for i in interactions_raw]

    # Optional food recommendations
    recommended = None
    if show_recommendations:
        recommended = _get_recommended_foods(patient.primary_condition)

    # Upload image to S3 async (non-blocking for response)
    s3_key = None
    try:
        s3_key = await upload_to_s3(
            image_bytes,
            bucket="rc-food-images",
            key_prefix=f"patients/{patient.id}/food",
            content_type=file.content_type,
        )
    except Exception:
        pass  # S3 failure should never block the user

    # Save food log
    avg_confidence = (
        sum(f.confidence or 0.8 for f in food_items) / len(food_items) if food_items else None
    )
    food_log = FoodLog(
        patient_id=patient.id,
        meal_type=meal_type,
        food_items=[f.model_dump() for f in food_items],
        image_s3_key=s3_key,
        cv_confidence=avg_confidence,
        interaction_flags=[i.model_dump() for i in interaction_flags],
        caution_shown=len(interaction_flags) > 0,
    )
    db.add(food_log)

    return FoodScanResponse(
        food_items=food_items,
        interaction_flags=interaction_flags,
        has_interactions=len(interaction_flags) > 0,
        recommended_foods=recommended,
    )


@router.post("/log", status_code=201)
async def log_food_manually(
    payload: FoodLogCreate,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
    ai: AIOrchestrator = Depends(get_ai),
):
    # Still check interactions even for manual logs
    rx_result = await db.execute(
        select(Prescription).where(
            and_(Prescription.patient_id == patient.id, Prescription.doses_remaining > 0)
        )
    )
    prescriptions = rx_result.scalars().all()

    interactions_raw = await ai.check_drug_food_interactions(
        [f.model_dump() for f in payload.food_items], prescriptions
    )
    interaction_flags = [InteractionFlag(**i) for i in interactions_raw]

    food_log = FoodLog(
        patient_id=patient.id,
        meal_type=payload.meal_type,
        food_items=[f.model_dump() for f in payload.food_items],
        interaction_flags=[i.model_dump() for i in interaction_flags],
        caution_shown=len(interaction_flags) > 0,
    )
    db.add(food_log)

    return {
        "id": str(food_log.id),
        "interaction_flags": [i.model_dump() for i in interaction_flags],
        "has_interactions": len(interaction_flags) > 0,
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
            "has_interactions": len(l.interaction_flags) > 0,
        }
        for l in logs
    ]


def _get_recommended_foods(condition: Optional[str]) -> List[str]:
    """
    Very basic static recommendations by condition.
    In production, this would be expanded by a dietitian-reviewed DB.
    """
    base = ["Oatmeal", "Lean chicken", "Blueberries", "Broccoli", "Sweet potato", "Greek yoghurt"]
    if not condition:
        return base

    c = condition.lower()
    if "cardiac" in c or "heart" in c:
        return ["Oily fish (salmon)", "Walnuts", "Leafy greens", "Oatmeal", "Berries", "Olive oil"]
    if "appendix" in c or "cholecyst" in c:
        return ["White rice", "Toast", "Bananas", "Boiled chicken", "Scrambled eggs", "Apple sauce"]
    if "knee" in c or "ortho" in c:
        return ["Calcium-rich dairy", "Leafy greens", "Fatty fish", "Turmeric", "Berries", "Nuts"]

    return base
