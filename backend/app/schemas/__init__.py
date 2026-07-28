from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime, date


# ── Auth ──────────────────────────────────────────────────
class PatientRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8)
    preferred_language: str = "en"


class ClinicianRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8)
    specialty: Optional[str] = None
    hospital: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Onboarding ────────────────────────────────────────────
class OnboardingStep1(BaseModel):
    """Demographics"""
    dob: date
    gender: str
    height_cm: int = Field(..., ge=100, le=250)
    weight_kg: float = Field(..., ge=20, le=300)
    living_situation: str     # alone | family | assisted


class OnboardingStep2(BaseModel):
    """Condition"""
    primary_condition: str
    surgery_type: Optional[str] = None
    discharge_date: date
    chronic_diseases: List[str] = []
    allergies: List[str] = []


class OnboardingStep3(BaseModel):
    """Lifestyle"""
    eating_habits: str
    exercise_frequency: str
    smoking: bool = False
    alcohol: bool = False
    sleep_baseline: float = Field(..., ge=1, le=12)
    mood_baseline: float = Field(..., ge=0, le=10)


class OnboardingStep4(BaseModel):
    """Prescriptions (initial)"""
    prescriptions: List["PrescriptionCreate"]
    emergency_contact: Optional[dict] = None


# ── Daily Log ─────────────────────────────────────────────
class DailyLogCreate(BaseModel):
    log_date: date
    pain_score: Optional[int] = Field(None, ge=0, le=10)
    sleep_score: Optional[int] = Field(None, ge=0, le=10)
    appetite_score: Optional[int] = Field(None, ge=0, le=10)
    mood_score: Optional[int] = Field(None, ge=0, le=10)
    fatigue_score: Optional[int] = Field(None, ge=0, le=10)
    mobility_score: Optional[int] = Field(None, ge=0, le=10)
    swelling_score: Optional[int] = Field(None, ge=0, le=10)
    medicine_adherence: Optional[int] = Field(None, ge=0, le=10)
    note: Optional[str] = Field(None, max_length=1000)
    submission_method: str = "manual"


class DailyLogResponse(BaseModel):
    id: UUID
    patient_id: UUID
    log_date: date
    pain_score: Optional[int]
    sleep_score: Optional[int]
    appetite_score: Optional[int]
    mood_score: Optional[int]
    fatigue_score: Optional[int]
    mobility_score: Optional[int]
    swelling_score: Optional[int]
    medicine_adherence: Optional[int]
    note: Optional[str]
    created_at: datetime
    insight: Optional[str] = None          # AI-generated, if any

    model_config = {"from_attributes": True}


class TrendDataPoint(BaseModel):
    date: date
    actual: Optional[float]
    expected: Optional[float]
    deviation: Optional[float]


class TrendResponse(BaseModel):
    metric: str
    data: List[TrendDataPoint]
    current_level: int   # escalation level


# ── Prescription ──────────────────────────────────────────
class PrescriptionCreate(BaseModel):
    drug_name: str = Field(..., min_length=2, max_length=200)
    generic_name: Optional[str] = None
    dosage: str
    frequency: dict     # {times: ["08:00"], condition: null}
    is_compulsory: bool = True
    total_doses_bought: int = Field(..., ge=1)
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("total_doses_bought")
    @classmethod
    def doses_positive(cls, v):
        if v < 1:
            raise ValueError("doses must be positive")
        return v


class PrescriptionResponse(BaseModel):
    id: UUID
    drug_name: str
    generic_name: Optional[str]
    dosage: str
    frequency: dict
    is_compulsory: bool
    total_doses_bought: int
    doses_remaining: int
    refill_threshold: int
    start_date: date
    end_date: Optional[date]
    notes: Optional[str]
    needs_refill: bool = False

    model_config = {"from_attributes": True}


class DoseLogCreate(BaseModel):
    prescription_id: UUID
    scheduled_time: datetime
    taken: bool
    skip_reason: Optional[str] = None


# ── Food ──────────────────────────────────────────────────
class FoodItem(BaseModel):
    name: str
    quantity: Optional[str] = None
    confidence: Optional[float] = None


class InteractionFlag(BaseModel):
    drug_name: str
    severity: str          # low | moderate
    message: str           # human-friendly, never alarming
    advice: str            # e.g. "1-2 hour gap is ideal"


class FoodScanResponse(BaseModel):
    food_items: List[FoodItem]
    interaction_flags: List[InteractionFlag]
    has_interactions: bool
    recommended_foods: Optional[List[str]] = None


class FoodLogCreate(BaseModel):
    meal_type: str
    food_items: List[FoodItem]
    image_s3_key: Optional[str] = None
    cv_confidence: Optional[float] = None
    interaction_flags: List[InteractionFlag] = []


# ── Escalation / Clinician ────────────────────────────────
class PatientFlagSummary(BaseModel):
    patient_id: UUID
    patient_name: str
    recovery_day: int
    escalation_level: int
    primary_metric: str
    insight: str
    trend_data: List[TrendDataPoint]
    flag_date: date


class EscalationFlagResponse(BaseModel):
    id: UUID
    flag_date: date
    level: int
    metric: str
    expected_value: float
    actual_value: float
    deviation_pct: float
    patient_insight: Optional[str]
    clinician_summary: Optional[str]
    suppressed: bool
    clarified_by_user: bool

    model_config = {"from_attributes": True}


class ClarifyFlag(BaseModel):
    flag_id: UUID
    clarification: str      # patient explains the deviation


# ── Reminder ──────────────────────────────────────────────
class ReminderCreate(BaseModel):
    reminder_type: str      # medicine | water | meal | exercise | checkin
    scheduled_time: str     # "08:00"
    days_of_week: List[int] = [0, 1, 2, 3, 4, 5, 6]
    prescription_id: Optional[UUID] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class ReminderResponse(BaseModel):
    id: UUID
    reminder_type: str
    scheduled_time: str
    days_of_week: List[int]
    is_active: bool
    last_sent: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Voice ─────────────────────────────────────────────────
class VoiceSessionStart(BaseModel):
    language: Optional[str] = None   # auto-detect if null


class VoiceMessageRequest(BaseModel):
    session_id: str
    audio_base64: str                # base64 encoded audio
    language: Optional[str] = None


class VoiceMessageResponse(BaseModel):
    session_id: str
    transcript: str
    bot_text: str
    audio_base64: Optional[str]      # TTS response
    extracted_log: Optional[dict]    # partial DailyLog fields extracted
    log_complete: bool               # true when all fields filled
    detected_language: str


# ── Digital Twin ──────────────────────────────────────────
class TwinStateResponse(BaseModel):
    patient_id: UUID
    recovery_day: int
    expected_ranges: dict           # {metric: {expected, low, high}}
    calibrated: bool
    model_version: str
