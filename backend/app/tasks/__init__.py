"""
Celery Tasks
============
All async background jobs: trend analysis, reminders, refill checks.
Each task is idempotent and gracefully handles failures.
"""

import asyncio
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "recovery_companion",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        # Run reminder dispatch every minute
        "dispatch-reminders": {
            "task": "app.tasks.dispatch_reminders",
            "schedule": crontab(minute="*"),
        },
        # Check refill thresholds every morning
        "check-refills": {
            "task": "app.tasks.check_refill_thresholds",
            "schedule": crontab(hour=8, minute=0),
        },
        # Send daily check-in nudge if not submitted by 7pm
        "checkin-nudge": {
            "task": "app.tasks.send_checkin_nudge",
            "schedule": crontab(hour=19, minute=0),
        },
    },
)


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.analyze_trend_task", bind=True, max_retries=3)
def analyze_trend_task(self, patient_id: str, log_id: str):
    """Triggered after every daily log submission."""
    from uuid import UUID
    from app.core.database import AsyncSessionLocal
    from app.services.trend_service import analyze_trend
    from app.services.ai_service import AIOrchestrator
    from app.utils.push import send_push_if_needed

    async def _run():
        async with AsyncSessionLocal() as db:
            flag = await analyze_trend(
                db=db,
                patient_id=UUID(patient_id),
                log_id=UUID(log_id),
                ai=AIOrchestrator(),
            )
            await db.commit()

            if flag and flag.level >= 2:
                await send_push_if_needed(db, UUID(patient_id), flag)

    try:
        _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="app.tasks.dispatch_reminders")
def dispatch_reminders():
    """Check all active reminders and send push notifications as needed."""
    from app.core.database import AsyncSessionLocal
    from app.utils.push import dispatch_due_reminders

    async def _run():
        async with AsyncSessionLocal() as db:
            await dispatch_due_reminders(db)
            await db.commit()

    _run_async(_run())


@celery_app.task(name="app.tasks.check_refill_thresholds")
def check_refill_thresholds():
    """Flag prescriptions with doses_remaining below refill_threshold."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models import Prescription, Patient
    from app.utils.push import send_refill_reminder

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Prescription).where(
                    Prescription.doses_remaining <= Prescription.refill_threshold,
                    Prescription.doses_remaining > 0,
                )
            )
            prescriptions = result.scalars().all()

            for rx in prescriptions:
                patient_result = await db.execute(
                    select(Patient).where(Patient.id == rx.patient_id)
                )
                patient = patient_result.scalar_one_or_none()
                if patient and patient.fcm_token:
                    await send_refill_reminder(patient, rx)
            await db.commit()

    _run_async(_run())


@celery_app.task(name="app.tasks.send_checkin_nudge")
def send_checkin_nudge():
    """Send a gentle push to patients who haven't submitted today's log."""
    from datetime import date
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, and_
    from app.models import Patient, DailyLog
    from app.utils.push import send_push_notification

    async def _run():
        async with AsyncSessionLocal() as db:
            # Get all patients with no log today
            today = date.today()
            patients_result = await db.execute(
                select(Patient).where(Patient.onboarding_complete == True)
            )
            patients = patients_result.scalars().all()

            for patient in patients:
                if not patient.fcm_token:
                    continue

                log_result = await db.execute(
                    select(DailyLog).where(
                        and_(DailyLog.patient_id == patient.id, DailyLog.log_date == today)
                    )
                )
                if log_result.scalar_one_or_none():
                    continue  # Already submitted

                first_name = patient.full_name.split()[0]
                await send_push_notification(
                    token=patient.fcm_token,
                    title="How are you feeling today?",
                    body=f"{first_name}, your evening check-in only takes 30 seconds.",
                    data={"type": "checkin_nudge"},
                )
            await db.commit()

    _run_async(_run())
