"""
auth.py  — Registration + Login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models import Patient, Clinician
from app.schemas import PatientRegister, ClinicianRegister, LoginRequest, TokenResponse, RefreshRequest

router = APIRouter()


@router.post("/patient/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(payload: PatientRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Patient).where(Patient.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    patient = Patient(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        preferred_language=payload.preferred_language,
    )
    db.add(patient)
    await db.flush()

    return TokenResponse(
        access_token=create_access_token(str(patient.id), "patient"),
        refresh_token=create_refresh_token(str(patient.id), "patient"),
        role="patient",
    )


@router.post("/clinician/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_clinician(payload: ClinicianRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Clinician).where(Clinician.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    clinician = Clinician(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        specialty=payload.specialty,
        hospital=payload.hospital,
    )
    db.add(clinician)
    await db.flush()

    return TokenResponse(
        access_token=create_access_token(str(clinician.id), "clinician"),
        refresh_token=create_refresh_token(str(clinician.id), "clinician"),
        role="clinician",
    )


@router.post("/patient/login", response_model=TokenResponse)
async def login_patient(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).where(Patient.email == payload.email))
    patient = result.scalar_one_or_none()
    if not patient or not verify_password(payload.password, patient.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(str(patient.id), "patient"),
        refresh_token=create_refresh_token(str(patient.id), "patient"),
        role="patient",
    )


@router.post("/clinician/login", response_model=TokenResponse)
async def login_clinician(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Clinician).where(Clinician.email == payload.email))
    clinician = result.scalar_one_or_none()
    if not clinician or not verify_password(payload.password, clinician.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(str(clinician.id), "clinician"),
        refresh_token=create_refresh_token(str(clinician.id), "clinician"),
        role="clinician",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest):
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    role = data.get("role", "patient")
    return TokenResponse(
        access_token=create_access_token(data["sub"], role),
        refresh_token=create_refresh_token(data["sub"], role),
        role=role,
    )
