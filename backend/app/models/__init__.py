"""
Recovery Companion - Database Models
Cross-database compatible models supporting PostgreSQL and SQLite
"""
import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Integer, SmallInteger, Boolean, Date, DateTime,
    Text, Numeric, ForeignKey, JSON, ARRAY, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID


class Patient(Base):
    """Patient model representing a user of the recovery companion app."""
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    dob: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    height_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    primary_condition: Mapped[Optional[str]] = mapped_column(String(200))
    surgery_type: Mapped[Optional[str]] = mapped_column(String(200))
    discharge_date: Mapped[Optional[date]] = mapped_column(Date)
    chronic_diseases: Mapped[Optional[List]] = mapped_column(JSON)
    allergies: Mapped[Optional[List]] = mapped_column(JSON)
    eating_habits: Mapped[Optional[str]] = mapped_column(String(100))
    exercise_frequency: Mapped[Optional[str]] = mapped_column(String(50))
    smoking: Mapped[bool] = mapped_column(Boolean, default=False)
    alcohol: Mapped[bool] = mapped_column(Boolean, default=False)
    sleep_baseline: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    mood_baseline: Mapped[Optional[float]] = mapped_column(Numeric(3, 1))
    living_situation: Mapped[Optional[str]] = mapped_column(String(50))
    emergency_contact: Mapped[Optional[Dict]] = mapped_column(JSON)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    fcm_token: Mapped[Optional[str]] = mapped_column(Text)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    clinician_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("clinicians.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="patient", cascade="all, delete-orphan")
    dose_logs: Mapped[List["DoseLog"]] = relationship("DoseLog", back_populates="patient", cascade="all, delete-orphan")
    daily_logs: Mapped[List["DailyLog"]] = relationship("DailyLog", back_populates="patient", cascade="all, delete-orphan")
    food_logs: Mapped[List["FoodLog"]] = relationship("FoodLog", back_populates="patient", cascade="all, delete-orphan")
    digital_twin: Mapped[Optional["DigitalTwin"]] = relationship("DigitalTwin", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    escalation_flags: Mapped[List["EscalationFlag"]] = relationship("EscalationFlag", back_populates="patient", cascade="all, delete-orphan")
    reminders: Mapped[List["Reminder"]] = relationship("Reminder", back_populates="patient", cascade="all, delete-orphan")
    consents: Mapped[List["ConsentLedger"]] = relationship("ConsentLedger", back_populates="patient", cascade="all, delete-orphan")
    clinician: Mapped[Optional["Clinician"]] = relationship("Clinician", back_populates="patients")


class Clinician(Base):
    """Clinician model for healthcare providers."""
    __tablename__ = "clinicians"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[Optional[str]] = mapped_column(String(100))
    hospital: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patients: Mapped[List["Patient"]] = relationship("Patient", back_populates="clinician")


class Prescription(Base):
    """Prescription model for patient's medications."""
    __tablename__ = "prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"))
    drug_name: Mapped[str] = mapped_column(String(200), nullable=False)
    generic_name: Mapped[Optional[str]] = mapped_column(String(200))
    dosage: Mapped[str] = mapped_column(String(50))
    frequency: Mapped[Dict] = mapped_column(JSON, default={"times": ["08:00"]})
    is_compulsory: Mapped[bool] = mapped_column(Boolean, default=True)
    total_doses_bought: Mapped[int] = mapped_column(Integer)
    doses_remaining: Mapped[int] = mapped_column(Integer)
    refill_threshold: Mapped[int] = mapped_column(Integer, default=5)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="prescriptions")
    dose_logs: Mapped[List["DoseLog"]] = relationship("DoseLog", back_populates="prescription", cascade="all, delete-orphan")
    reminders: Mapped[List["Reminder"]] = relationship("Reminder", back_populates="prescription")


class DoseLog(Base):
    """DoseLog model for tracking medication intake."""
    __tablename__ = "dose_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("prescriptions.id"))
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"))
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="dose_logs")
    prescription: Mapped["Prescription"] = relationship("Prescription", back_populates="dose_logs")


class DailyLog(Base):
    """DailyLog model for daily health questionnaire submissions."""
    __tablename__ = "daily_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"))
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    pain_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    sleep_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    appetite_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    mood_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    fatigue_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    mobility_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    swelling_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    medicine_adherence: Mapped[Optional[int]] = mapped_column(SmallInteger)
    note: Mapped[Optional[str]] = mapped_column(Text)
    submission_method: Mapped[str] = mapped_column(String(20), default="manual")
    insight: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="daily_logs")


class FoodLog(Base):
    """FoodLog model for meal tracking."""
    __tablename__ = "food_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"))
    meal_type: Mapped[str] = mapped_column(String(20))
    food_items: Mapped[List] = mapped_column(JSON)
    image_s3_key: Mapped[Optional[str]] = mapped_column(String(500))
    cv_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    interaction_flags: Mapped[List] = mapped_column(JSON, default=list)
    caution_shown: Mapped[bool] = mapped_column(Boolean, default=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="food_logs")


class DigitalTwin(Base):
    """DigitalTwin model for patient's expected recovery curves."""
    __tablename__ = "digital_twins"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"), unique=True)
    expected_pain_curve: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON)
    expected_fatigue_curve: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON)
    expected_appetite_curve: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON)
    expected_mood_curve: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON)
    expected_mobility_curve: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON)
    expected_sleep_curve: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON)
    baseline_bmi: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    baseline_age_group: Mapped[Optional[str]] = mapped_column(String(20))
    baseline_condition: Mapped[Optional[str]] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(20), default="1.0")
    calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="digital_twin")


class EscalationFlag(Base):
    """EscalationFlag model for tracking recovery anomalies."""
    __tablename__ = "escalation_flags"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"))
    flag_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(20))
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_value: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    actual_value: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    deviation_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    patient_insight: Mapped[Optional[str]] = mapped_column(Text)
    clinician_summary: Mapped[Optional[str]] = mapped_column(Text)
    clarified_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    user_clarification: Mapped[Optional[str]] = mapped_column(Text)
    clinician_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="escalation_flags")


class Reminder(Base):
    """Reminder model for patient notifications."""
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"))
    reminder_type: Mapped[str] = mapped_column(String(30))
    scheduled_time: Mapped[str] = mapped_column(String(5))
    days_of_week: Mapped[List] = mapped_column(JSON, default=list)
    prescription_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("prescriptions.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5))
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5))
    last_sent: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="reminders")
    prescription: Mapped[Optional["Prescription"]] = relationship("Prescription", back_populates="reminders")


class ConsentLedger(Base):
    """ConsentLedger for tracking patient consent."""
    __tablename__ = "consent_ledger"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patients.id"))
    consent_type: Mapped[str] = mapped_column(String(80))
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(10), default="1.0")

    patient: Mapped["Patient"] = relationship("Patient", back_populates="consents")
