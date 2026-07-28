"""
Trend & Escalation Service
===========================
Analyses daily log patterns against the digital twin baseline.
Determines escalation level without single-day panic.
Multi-day sustained deviation is the ONLY trigger.
"""

from uuid import UUID
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import Patient, DailyLog, DigitalTwin, EscalationFlag
from app.services.twin_service import get_expected_range
from app.services.ai_service import AIOrchestrator


METRICS = ["pain", "fatigue", "appetite", "sleep", "mood"]

# For pain & fatigue: HIGHER actual = WORSE (so deviation is actual > expected)
# For appetite, sleep, mood: LOWER actual = WORSE
INVERTED_METRICS = {"pain", "fatigue"}


def _deviation_score(metric: str, actual: float, expected: float, tolerance: float) -> float:
    """
    Returns a normalised deviation score.
    Positive = worse than expected. Negative = better than expected.
    """
    if metric in INVERTED_METRICS:
        # Higher actual pain is worse
        raw = actual - expected
    else:
        # Lower actual appetite is worse
        raw = expected - actual

    return raw / max(tolerance, 0.1)


def _get_metric_value(log: DailyLog, metric: str) -> Optional[float]:
    return {
        "pain": log.pain_score,
        "fatigue": log.fatigue_score,
        "appetite": log.appetite_score,
        "sleep": log.sleep_score,
        "mood": log.mood_score,
    }.get(metric)


async def analyze_trend(
    db: AsyncSession,
    patient_id: UUID,
    log_id: UUID,
    ai: Optional[AIOrchestrator] = None,
) -> Optional[EscalationFlag]:
    """
    Called async after each daily log submission.
    Returns an EscalationFlag if warranted, else None.
    """
    # Fetch patient + twin
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        return None

    # Fetch digital twin separately
    twin_result = await db.execute(select(DigitalTwin).where(DigitalTwin.patient_id == patient_id))
    twin = twin_result.scalar_one_or_none()
    if not twin:
        return None
    if not patient.discharge_date:
        return None

    today = date.today()
    recovery_day = (today - patient.discharge_date).days + 1

    # Fetch last 7 days of logs
    week_ago = today - timedelta(days=6)
    logs_result = await db.execute(
        select(DailyLog)
        .where(and_(DailyLog.patient_id == patient_id, DailyLog.log_date >= week_ago))
        .order_by(DailyLog.log_date)
    )
    logs = logs_result.scalars().all()

    if len(logs) < 2:
        return None  # Need at least 2 data points

    worst_metric = None
    worst_deviation = 0.0
    worst_actual = 0.0
    worst_expected = 0.0

    for metric in METRICS:
        # Compute deviation for each day we have data
        deviations = []
        for log in logs:
            day_num = (log.log_date - patient.discharge_date).days + 1
            actual = _get_metric_value(log, metric)
            if actual is None:
                continue
            expected_range = get_expected_range(twin, metric, day_num)
            dev = _deviation_score(
                metric, float(actual),
                expected_range["expected"],
                expected_range["tolerance"],
            )
            deviations.append((dev, float(actual), expected_range["expected"]))

        if not deviations:
            continue

        # Rolling averages
        recent_3 = [d[0] for d in deviations[-3:]]
        recent_7 = [d[0] for d in deviations]

        avg_3 = sum(recent_3) / len(recent_3)
        avg_7 = sum(recent_7) / len(recent_7)

        # Weighted combined score
        combined = 0.6 * avg_3 + 0.4 * avg_7

        if combined > worst_deviation:
            worst_deviation = combined
            worst_metric = metric
            worst_actual = deviations[-1][1]
            worst_expected = deviations[-1][2]

    if not worst_metric or worst_deviation <= 0.5:
        return None  # No meaningful deviation

    # Determine escalation level
    if worst_deviation > 3.0 and len(logs) >= 5:
        level = 3
    elif worst_deviation > 2.0 and len(logs) >= 4:
        level = 2
    elif worst_deviation > 1.0 and len(logs) >= 3:
        level = 1
    else:
        return None  # Not sustained enough

    # Check if already flagged for this metric recently (avoid spam)
    recent_flag = await db.execute(
        select(EscalationFlag).where(
            and_(
                EscalationFlag.patient_id == patient_id,
                EscalationFlag.metric == worst_metric,
                EscalationFlag.flag_date >= today - timedelta(days=2),
                EscalationFlag.suppressed == False,
            )
        )
    )
    if recent_flag.scalar_one_or_none():
        return None  # Already flagged recently

    deviation_pct = round((worst_deviation / 3.0) * 100, 1)

    # Generate insights via LLM if available
    patient_insight = None
    clinician_summary = None
    if ai:
        try:
            patient_insight = await ai.generate_patient_insight(
                metric=worst_metric,
                level=level,
                deviation_pct=deviation_pct,
                recovery_day=recovery_day,
                patient=patient,
            )
            clinician_summary = await ai.generate_clinician_summary(
                metric=worst_metric,
                level=level,
                logs=logs,
                twin=twin,
                patient=patient,
            )
        except Exception:
            # Fallback — never block on AI failure
            patient_insight = _fallback_patient_insight(worst_metric, level)
            clinician_summary = _fallback_clinician_summary(worst_metric, level, deviation_pct)

    flag = EscalationFlag(
        patient_id=patient_id,
        flag_date=today,
        level=level,
        metric=worst_metric,
        expected_value=worst_expected,
        actual_value=worst_actual,
        deviation_pct=deviation_pct,
        patient_insight=patient_insight,
        clinician_summary=clinician_summary,
    )
    db.add(flag)
    await db.flush()
    return flag


def _fallback_patient_insight(metric: str, level: int) -> str:
    insights = {
        ("pain", 1): "Your pain has been a little higher than expected the past few days. This can happen — rest well and stay hydrated.",
        ("pain", 2): "We've noticed your pain hasn't been declining as expected. It's worth mentioning to your care team at your next check-in.",
        ("pain", 3): "Your pain pattern over the past several days is something your care team should know about. They may reach out soon.",
        ("fatigue", 1): "Feeling more tired than usual lately is common, especially if sleep has been disrupted. Try to rest when you can.",
        ("fatigue", 2): "Your fatigue has stayed higher than expected for a few days. A quick conversation with your provider would be a good idea.",
        ("fatigue", 3): "Your care team has been notified about your fatigue levels. Please contact your provider if you feel unwell.",
        ("appetite", 1): "Your appetite has been a little lower than we'd hope to see at this point. Small, frequent meals can help.",
        ("appetite", 2): "Your appetite hasn't improved as expected. It's worth a mention to your doctor — not urgent, but worth noting.",
        ("sleep", 1): "Sleep has been a bit disrupted. This often improves as pain settles — try keeping a consistent bedtime.",
        ("sleep", 2): "Your sleep quality has been below what we'd expect for this stage. It's worth discussing with your care team.",
        ("mood", 1): "Recovery can be emotionally tough. How you're feeling matters — reach out to someone you trust if you need to talk.",
        ("mood", 2): "We've noticed your mood has been lower than expected over the past few days. Please don't hesitate to speak to your provider.",
    }
    return insights.get(
        (metric, level),
        f"We've noticed something in your {metric} readings. Your care team has been informed and may follow up."
    )


def _fallback_clinician_summary(metric: str, level: int, deviation_pct: float) -> str:
    return (
        f"Patient showing sustained {metric} deviation ({deviation_pct:.0f}% above expected baseline). "
        f"Escalation level {level}. Multi-day trend analysis triggered this flag. No single-day spike."
    )
