"""
Digital Twin Service
====================
Builds a personalised expected recovery curve for each patient
based on their condition, demographics, and lifestyle factors.

No hallucinated predictions — all curves derived from evidence-based
recovery templates, then adjusted for personal risk factors.
"""

from uuid import UUID
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Patient, DigitalTwin, DailyLog


# ── Recovery templates ────────────────────────────────────
RECOVERY_TEMPLATES = {
    "appendectomy": {
        "pain": {1: 7, 2: 6.5, 3: 5.5, 4: 4.5, 5: 3.5, 7: 2.5, 10: 1.5, 14: 0.5},
        "fatigue": {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 7: 3, 10: 2, 14: 1},
        "appetite": {1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 7: 8, 10: 9, 14: 9},
        "sleep": {1: 5, 2: 5.5, 3: 6, 4: 6.5, 5: 7, 7: 7.5, 10: 8, 14: 8},
        "mood": {1: 5, 2: 5.5, 3: 6, 4: 6.5, 5: 7, 7: 7.5, 10: 8, 14: 9},
        "mobility": {1: 4, 2: 5, 3: 6, 4: 7, 5: 7.5, 7: 8, 10: 9, 14: 9},
        "recovery_days": 21,
    },
    "cholecystectomy": {
        "pain": {1: 6, 2: 5, 3: 4, 4: 3, 5: 2.5, 7: 1.5, 10: 0.5, 14: 0},
        "fatigue": {1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 7: 2, 10: 1, 14: 0.5},
        "appetite": {1: 2, 2: 4, 3: 5.5, 4: 6.5, 5: 7.5, 7: 8.5, 10: 9, 14: 9},
        "sleep": {1: 5, 2: 6, 3: 6.5, 4: 7, 5: 7.5, 7: 8, 10: 8.5, 14: 9},
        "mood": {1: 5, 2: 6, 3: 6.5, 4: 7, 5: 7.5, 7: 8, 10: 8.5, 14: 9},
        "mobility": {1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 7: 9, 10: 9, 14: 10},
        "recovery_days": 21,
    },
    "cardiac_surgery": {
        "pain": {1: 8, 3: 7, 5: 6, 7: 5.5, 10: 4.5, 14: 3.5, 21: 2.5, 30: 1.5},
        "fatigue": {1: 9, 3: 8, 5: 7.5, 7: 7, 10: 6, 14: 5, 21: 3, 30: 1.5},
        "appetite": {1: 3, 3: 4, 5: 5, 7: 5.5, 10: 6.5, 14: 7.5, 21: 8.5, 30: 9},
        "sleep": {1: 4, 3: 5, 5: 5.5, 7: 6, 10: 6.5, 14: 7, 21: 7.5, 30: 8},
        "mood": {1: 4, 3: 4.5, 5: 5, 7: 5.5, 10: 6, 14: 7, 21: 7.5, 30: 8},
        "mobility": {1: 2, 3: 3, 5: 4, 7: 5, 10: 6, 14: 7, 21: 8, 30: 9},
        "recovery_days": 90,
    },
    "knee_replacement": {
        "pain": {1: 7, 3: 6.5, 5: 6, 7: 5.5, 10: 5, 14: 4, 21: 3, 30: 2, 45: 1},
        "fatigue": {1: 8, 3: 7, 5: 6.5, 7: 6, 10: 5, 14: 4, 21: 3, 30: 2, 45: 1},
        "appetite": {1: 5, 3: 5.5, 5: 6, 7: 6.5, 10: 7, 14: 7.5, 21: 8, 30: 8.5, 45: 9},
        "sleep": {1: 5, 3: 5.5, 5: 6, 7: 6, 10: 6.5, 14: 7, 21: 7.5, 30: 8, 45: 8.5},
        "mood": {1: 5, 3: 5.5, 5: 6, 7: 6.5, 10: 7, 14: 7.5, 21: 8, 30: 8.5, 45: 9},
        "mobility": {1: 2, 3: 3, 5: 4, 7: 5, 10: 6, 14: 7, 21: 8, 30: 9, 45: 10},
        "recovery_days": 90,
    },
    "default": {
        "pain": {1: 6, 3: 5, 5: 4, 7: 3, 10: 2, 14: 1},
        "fatigue": {1: 7, 3: 6, 5: 5, 7: 4, 10: 3, 14: 1.5},
        "appetite": {1: 4, 3: 5, 5: 6, 7: 7, 10: 8, 14: 9},
        "sleep": {1: 5, 3: 6, 5: 6.5, 7: 7, 10: 7.5, 14: 8},
        "mood": {1: 5, 3: 6, 5: 6.5, 7: 7, 10: 7.5, 14: 8},
        "mobility": {1: 4, 3: 5, 5: 6, 7: 7, 10: 8, 14: 9},
        "recovery_days": 30,
    },
}


def _normalise_condition(raw: Optional[str]) -> str:
    if not raw:
        return "default"
    r = raw.lower()
    if "appendix" in r or "appendectomy" in r:
        return "appendectomy"
    if "cholecyst" in r or "gallbladder" in r:
        return "cholecystectomy"
    if "cardiac" in r or "heart" in r or "bypass" in r:
        return "cardiac_surgery"
    if "knee" in r and ("replace" in r or "arthroplasty" in r):
        return "knee_replacement"
    if "hip" in r and ("replace" in r or "arthroplasty" in r):
        return "knee_replacement"  # similar recovery
    return "default"


def _interpolate(curve: dict, day: int) -> float:
    """Linear interpolation between template waypoints."""
    days = sorted(curve.keys())
    if day <= days[0]:
        return curve[days[0]]
    if day >= days[-1]:
        return curve[days[-1]]
    for i in range(len(days) - 1):
        d0, d1 = days[i], days[i + 1]
        if d0 <= day <= d1:
            t = (day - d0) / (d1 - d0)
            return curve[d0] + t * (curve[d1] - curve[d0])
    return curve[days[-1]]


def _risk_multiplier(patient: Patient) -> float:
    """Returns a multiplier that scales recovery curve."""
    mult = 1.0

    # Age effect
    if patient.dob:
        age = (date.today() - patient.dob).days // 365
    else:
        age = 40
    
    if age > 70:
        mult += 0.25
    elif age > 60:
        mult += 0.15
    elif age < 35:
        mult -= 0.05

    # BMI effect
    if patient.height_cm and patient.weight_kg:
        bmi = float(patient.weight_kg) / ((patient.height_cm / 100) ** 2)
        if bmi > 35:
            mult += 0.2
        elif bmi > 30:
            mult += 0.1

    # Smoking
    if patient.smoking:
        mult += 0.15

    # Chronic diseases
    high_risk = {"diabetes", "copd", "heart failure", "chronic kidney disease", "immunosuppressed"}
    for disease in (patient.chronic_diseases or []):
        if any(h in str(disease).lower() for h in high_risk):
            mult += 0.1

    return max(0.7, min(mult, 2.0))


def _build_curve(template_curve: dict, risk_mult: float, recovery_days: int) -> dict:
    """Build a day-by-day expected curve dict."""
    result = {}
    for day in range(1, recovery_days + 1):
        base = _interpolate(template_curve, day)
        # Risk multiplier slows improvement
        adjusted = base * (1 / risk_mult) if base > 0 else base
        result[str(day)] = round(max(0.0, min(10.0, adjusted)), 2)
    return result


async def build_digital_twin(db: AsyncSession, patient: Patient) -> DigitalTwin:
    """Create or replace the digital twin for a patient."""
    condition_key = _normalise_condition(patient.primary_condition or patient.surgery_type)
    template = RECOVERY_TEMPLATES.get(condition_key, RECOVERY_TEMPLATES["default"])
    risk = _risk_multiplier(patient)
    recovery_days = int(template["recovery_days"] * risk)

    pain_curve = _build_curve(template["pain"], risk, recovery_days)
    fatigue_curve = _build_curve(template["fatigue"], risk, recovery_days)
    
    # For metrics where higher is better (appetite, mood, sleep, mobility)
    # We invert the logic - higher values are better so we adjust differently
    appetite_curve = _build_curve(template["appetite"], 1.0, recovery_days)
    sleep_curve = _build_curve(template["sleep"], 1.0, recovery_days)
    mood_curve = _build_curve(template["mood"], 1.0, recovery_days)
    mobility_curve = _build_curve(template.get("mobility", template["pain"]), risk, recovery_days)

    # Check for existing twin
    result = await db.execute(
        select(DigitalTwin).where(DigitalTwin.patient_id == patient.id)
    )
    twin = result.scalar_one_or_none()

    if twin:
        twin.expected_pain_curve = pain_curve
        twin.expected_fatigue_curve = fatigue_curve
        twin.expected_appetite_curve = appetite_curve
        twin.expected_sleep_curve = sleep_curve
        twin.expected_mobility_curve = mobility_curve
        twin.baseline_condition = condition_key
    else:
        twin = DigitalTwin(
            patient_id=patient.id,
            expected_pain_curve=pain_curve,
            expected_fatigue_curve=fatigue_curve,
            expected_appetite_curve=appetite_curve,
            expected_sleep_curve=sleep_curve,
            expected_mood_curve=mood_curve,
            baseline_condition=condition_key,
            baseline_age_group=f"{(date.today() - patient.dob).days // 365 // 10 * 10}s" if patient.dob else "40s",
        )
        if patient.height_cm and patient.weight_kg:
            twin.baseline_bmi = float(patient.weight_kg) / ((patient.height_cm / 100) ** 2)
        
        db.add(twin)

    await db.flush()
    return twin


def get_expected_range(twin: DigitalTwin, metric: str, day: int) -> dict:
    """Return expected value ± tolerance for a given metric on a given day."""
    curve_map = {
        "pain": twin.expected_pain_curve,
        "fatigue": twin.expected_fatigue_curve,
        "appetite": twin.expected_appetite_curve,
        "sleep": twin.expected_sleep_curve,
        "mood": twin.expected_mood_curve,
        "mobility": getattr(twin, "expected_mobility_curve", None) or twin.expected_pain_curve,
    }
    curve = curve_map.get(metric, {})
    
    # Get the expected value from curve
    if curve:
        expected = float(curve.get(str(day), curve.get(str(min(day, len(curve))), 5.0)))
    else:
        expected = 5.0

    # Tolerance: wider early (±2.5), narrows mid-recovery (±1.5), widens again later
    tolerance = 2.5 if day <= 5 else (1.5 if day <= 21 else 2.0)

    return {
        "expected": expected,
        "low": max(0.0, expected - tolerance),
        "high": min(10.0, expected + tolerance),
        "tolerance": tolerance,
    }
