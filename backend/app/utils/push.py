"""Firebase Cloud Messaging push notifications"""
import firebase_admin
from firebase_admin import credentials, messaging
from app.core.config import settings

_initialized = False

def _init_firebase():
    global _initialized
    if not _initialized and settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        _initialized = True


async def send_push_notification(token: str, title: str, body: str, data: dict = None):
    _init_firebase()
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(priority="normal"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1)
                )
            ),
        )
        messaging.send(message)
    except Exception:
        pass  # Push failure should never affect core functionality


async def send_push_if_needed(db, patient_id, flag):
    from sqlalchemy import select
    from app.models import Patient
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient or not patient.fcm_token:
        return

    if flag.level == 2:
        title = "A note from your recovery tracker"
        body = flag.patient_insight or "Something worth mentioning to your care team."
    elif flag.level == 3:
        title = "Your care team has been notified"
        body = flag.patient_insight or "Your recovery pattern has been flagged for review."
    else:
        return

    await send_push_notification(
        token=patient.fcm_token,
        title=title,
        body=body,
        data={"type": "escalation", "level": str(flag.level), "flag_id": str(flag.id)},
    )


async def send_refill_reminder(patient, prescription):
    if not patient.fcm_token:
        return
    await send_push_notification(
        token=patient.fcm_token,
        title="Time to restock",
        body=f"You have {prescription.doses_remaining} doses of {prescription.drug_name} left.",
        data={"type": "refill", "prescription_id": str(prescription.id)},
    )


async def dispatch_due_reminders(db):
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models import Reminder, Patient

    now = datetime.now(timezone.utc)
    current_time = now.strftime("%H:%M")
    current_dow = now.weekday()

    result = await db.execute(
        select(Reminder).where(
            Reminder.is_active == True,
            Reminder.scheduled_time == current_time,
        )
    )
    reminders = result.scalars().all()

    for reminder in reminders:
        if current_dow not in (reminder.days_of_week or list(range(7))):
            continue

        # Respect quiet hours
        if reminder.quiet_hours_start and reminder.quiet_hours_end:
            if reminder.quiet_hours_start <= current_time <= reminder.quiet_hours_end:
                continue

        patient_result = await db.execute(select(Patient).where(Patient.id == reminder.patient_id))
        patient = patient_result.scalar_one_or_none()
        if not patient or not patient.fcm_token:
            continue

        titles = {
            "medicine": "Time for your medicine",
            "water": "Stay hydrated 💧",
            "meal": "Meal time reminder",
            "exercise": "Gentle movement time",
            "checkin": "Daily check-in ready",
        }
        bodies = {
            "medicine": "Your next dose is ready. Tap to log it.",
            "water": "Have you had a glass of water recently?",
            "meal": "Don't forget to eat — your body needs fuel to heal.",
            "exercise": "A short gentle walk can do wonders today.",
            "checkin": "30 seconds to log how you're feeling.",
        }
        rtype = reminder.reminder_type
        await send_push_notification(
            token=patient.fcm_token,
            title=titles.get(rtype, "Recovery reminder"),
            body=bodies.get(rtype, "Check the app for a reminder."),
            data={"type": rtype},
        )

        reminder.last_sent = now
