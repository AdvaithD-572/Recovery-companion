from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import auth, patients, logs, prescriptions, food, clinician, voice, reminders


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Recovery Companion API",
    version="1.0.0",
    description="Post-hospital recovery monitoring platform",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.cors_hosts)

# Routers
app.include_router(auth.router,          prefix="/api/v1/auth",          tags=["auth"])
app.include_router(patients.router,      prefix="/api/v1/patients",      tags=["patients"])
app.include_router(logs.router,          prefix="/api/v1/logs",          tags=["logs"])
app.include_router(prescriptions.router, prefix="/api/v1/prescriptions", tags=["prescriptions"])
app.include_router(food.router,          prefix="/api/v1/food",          tags=["food"])
app.include_router(clinician.router,     prefix="/api/v1/clinician",     tags=["clinician"])
app.include_router(voice.router,         prefix="/api/v1/voice",         tags=["voice"])
app.include_router(reminders.router,     prefix="/api/v1/reminders",     tags=["reminders"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
