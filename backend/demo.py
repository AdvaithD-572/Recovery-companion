"""Launch an isolated synthetic clinic on localhost. Credentials last for one run."""
import asyncio
import os
from pathlib import Path
import secrets
import tempfile
from datetime import date, datetime, timedelta, timezone

import uvicorn


async def seed(password, admin_password):
    from app.main import app
    from app.models import Clinician, Patient, DailyLog, DoseLog, FoodLog, Prescription
    from app.care import Staff, Link, add_entry
    from app.registry import Administrator, Clinic
    from app.core.database import Base, engine, AsyncSessionLocal
    from app.core.security import hash_password
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal.begin() as db:
        secret = hash_password(password)
        doctor = Clinician(full_name="Demo Clinician",email="doctor@example.org",hashed_password=secret)
        patient = Patient(full_name="Mira Sample",email="patient@example.org",hashed_password=secret,
            dob=date(1994,3,12),primary_condition="Post-discharge follow-up",surgery_type="Sample procedure",
            discharge_date=date.today()-timedelta(days=5),allergies=["Not recorded"],onboarding_complete=True)
        db.add_all([doctor,patient])
        await db.flush()
        clinic="Elm Clinic · Demonstration"
        db.add_all([Clinic(name=clinic, scope=clinic), Administrator(email="admin@example.org", hashed_password=hash_password(admin_password))])
        db.add_all([Staff(id=doctor.id,clinic=clinic,role="clinician"),Link(patient=patient.id,clinic=clinic)])
        medication=Prescription(patient_id=patient.id,drug_name="Example medication A",dosage="Recorded demo dose",
            frequency={"times":["09:00"]},total_doses_bought=12,doses_remaining=9,start_date=patient.discharge_date)
        db.add(medication)
        await db.flush()
        time=datetime.now(timezone.utc)
        add_entry(db,patient.id,None,"instructions",patient.id,{"text":"Bring the recovery diary to the next appointment. Synthetic discharge record."})
        add_entry(db,patient.id,clinic,"rule",doctor.id,{"event":"skipped","match":medication.drug_name,
            "severity":"Needs review","reason":"Discuss the reported skip at the next demo visit."},at=time-timedelta(days=5))
        for i,pain in enumerate([5,4,4,2]):
            at=time-timedelta(days=4-i)
            db.add(DailyLog(patient_id=patient.id,log_date=at.date(),pain_score=pain,mobility_score=5+i,sleep_score=6))
            db.add(DoseLog(patient_id=patient.id,prescription_id=medication.id,scheduled_time=at,
                skipped=i==2,taken_at=None if i==2 else at))
        db.add(FoodLog(patient_id=patient.id,meal_type="lunch",food_items=[{"name":"Rice"},{"name":"Vegetables"}],logged_at=time-timedelta(hours=1)))
    await engine.dispose()


if __name__=="__main__":
    with tempfile.TemporaryDirectory(prefix="rc-demo-") as folder:
        os.environ["DATABASE_URL"]="sqlite+aiosqlite:///"+(Path(folder)/"demo.db").as_posix()
        os.environ["GEMINI_API_KEY"]=""
        os.environ["SECRET_KEY"]=secrets.token_urlsafe(48)
        password=secrets.token_urlsafe(15)
        admin_password=secrets.token_urlsafe(18)
        asyncio.run(seed(password, admin_password))
        port=int(os.environ.get("RC_DEMO_PORT","8000"))
        print(f"Synthetic clinic: http://127.0.0.1:{port}/clinic/",flush=True)
        print("Staff: doctor@example.org | Android: patient@example.org",flush=True)
        print("Sample administrator: admin@example.org",flush=True)
        print("Temporary admin password:",admin_password,flush=True)
        print("Temporary demo password:",password,flush=True)
        uvicorn.run("app.main:app",host="127.0.0.1",port=port)
