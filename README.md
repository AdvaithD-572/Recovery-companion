# Recovery Companion

A premium, mobile-first healthcare recovery monitoring application designed for post-hospital discharge patients. The app provides intelligent recovery tracking, prescription management, food logging with drug interaction warnings, and multilingual voice support, all wrapped in a calm, non-alarming UI.

![Platform](https://img.shields.io/badge/Platform-iOS%20%7C%20Android-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)
![Database](https://img.shields.io/badge/Database-PostgreSQL-blue)

## Features

### Patient App
- **Digital Twin** - Personalized recovery curves based on your condition, age, and lifestyle
- **Daily Check-in** - Beautiful slider-based questionnaire (pain, sleep, appetite, mood, fatigue, mobility)
- **Voice Bot** - Multilingual voice check-in (English, Hindi, Telugu, Tamil)
- **Prescription Tracking** - Dose logging with gentle refill reminders
- **Food Logging** - Camera-based meal scanning with drug interaction warnings
- **Recovery Trends** - Visual charts comparing your progress vs expected recovery
- **Smart Reminders** - Medicine, water, meal, and exercise reminders
- **Offline Support** - Queue logs when offline, sync when back online

### Clinician Dashboard
- **Flagged Patients Only** - No spam, only patients needing attention
- **AI Summaries** - Clinician-ready insights without raw data overload
- **Trend Visualization** - See recovery trajectory at a glance

### Design Philosophy
- **Calm** - Never alarming, always supportive
- **Intelligent** - AI-powered insights that feel human
- **Observant** - Noticing patterns without overreaction
- **Non-judgmental** - Supportive language throughout

## Quick Start

### Prerequisites

- **Backend**: Python 3.12+, PostgreSQL 16+, Redis 7+
- **Mobile**: Flutter 3.4+, Dart 3.4+
- **AI Services**:
  - Gemini API key
  - Google Cloud credentials (STT/TTS)
  - Optional: OpenAI API key (Whisper fallback)
  - Optional: DrugBank API key (drug interactions)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the project
cd recovery_companion

# Start all services (API, Database, Redis, Workers)
docker-compose up --build

# Backend runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Option 2: Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload --port 8000
```

#### Mobile Setup

```bash
cd mobile

# Get dependencies
flutter pub get

# Run on connected device/emulator
flutter run
```

## Project Structure

```
recovery_companion/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   │   ├── auth.py      # Authentication
│   │   │   ├── patients.py  # Patient profiles & onboarding
│   │   │   ├── logs.py      # Daily logs & trends
│   │   │   ├── prescriptions.py
│   │   │   ├── food.py      # Food logging & interactions
│   │   │   ├── voice.py     # Voice bot
│   │   │   ├── reminders.py
│   │   │   └── clinician.py # Clinician dashboard
│   │   ├── core/            # Config, DB, security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   │   ├── ai_service.py      # AI orchestrator
│   │   │   ├── twin_service.py     # Digital twin
│   │   │   └── trend_service.py   # Trend analysis
│   │   ├── tasks/           # Celery background tasks
│   │   └── utils/           # STT, TTS, push, S3
│   ├── requirements.txt
│   └── Dockerfile
│
├── mobile/
│   ├── lib/
│   │   ├── core/
│   │   │   ├── theme/      # Beautiful UI theme
│   │   │   ├── router/     # GoRouter navigation
│   │   │   └── di/         # Riverpod providers
│   │   ├── features/
│   │   │   ├── login/
│   │   │   ├── onboarding/
│   │   │   ├── home/
│   │   │   ├── questionnaire/
│   │   │   ├── prescription/
│   │   │   ├── food_log/
│   │   │   ├── trends/
│   │   │   ├── voice_bot/
│   │   │   └── reminders/
│   │   └── shared/
│   │       ├── services/   # API client, auth, offline
│   │       └── widgets/    # Reusable widgets
│   └── pubspec.yaml
│
└── docker-compose.yml
```

## Environment Variables

The real `backend/.env` file is intentionally ignored by Git. Commit `backend/.env.example` only, then create your own local `.env` from it.

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/recovery_companion
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=change-me-to-a-long-random-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Services
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Google Cloud (STT/TTS)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_PROJECT_ID=your-project

# AWS S3
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_FOOD_IMAGES=rc-food-images
S3_BUCKET_PRESCRIPTIONS=rc-prescriptions

# Firebase (Push)
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# Drug Interactions (Optional)
DRUGBANK_API_KEY=...
```

## GitHub Upload Checklist

Before pushing to GitHub, make sure these files are included:

- `README.md`
- `.gitignore`
- `backend/.env.example`
- Source code in `backend/` and `mobile/`
- Dependency files such as `backend/requirements.txt`, `mobile/pubspec.yaml`, and `mobile/pubspec.lock`

Do not commit these:

- `backend/.env`
- API keys, passwords, tokens, or service-account JSON files
- `backend/venv/`
- `mobile/build/`
- Local databases such as `backend/recovery_companion.db`

## API Endpoints

### Authentication
- `POST /api/v1/auth/patient/register` - Patient registration
- `POST /api/v1/auth/patient/login` - Patient login
- `POST /api/v1/auth/clinician/register` - Clinician registration
- `POST /api/v1/auth/clinician/login` - Clinician login
- `POST /api/v1/auth/refresh` - Refresh tokens

### Patients
- `GET /api/v1/patients/me` - Get current patient profile
- `POST /api/v1/patients/onboarding/step/{step}` - Complete onboarding
- `PATCH /api/v1/patients/fcm-token` - Update FCM token

### Daily Logs
- `POST /api/v1/logs/daily` - Submit daily log
- `GET /api/v1/logs/daily` - Get logs (last N days)
- `GET /api/v1/logs/daily/today` - Get today's log
- `GET /api/v1/logs/trends/{metric}` - Get trend data
- `PATCH /api/v1/logs/daily/{log_id}/clarify` - Add context to a log

### Prescriptions
- `GET /api/v1/prescriptions/` - List prescriptions
- `POST /api/v1/prescriptions/` - Add prescription
- `POST /api/v1/prescriptions/scan-ocr` - Scan prescription image
- `POST /api/v1/prescriptions/dose-log` - Log dose taken

### Food
- `POST /api/v1/food/scan` - Scan meal image
- `POST /api/v1/food/log` - Manual food log
- `GET /api/v1/food/log/today` - Today's food logs

### Voice Bot
- `POST /api/v1/voice/session/start` - Start voice session
- `POST /api/v1/voice/session/{id}/message` - Send voice message
- `DELETE /api/v1/voice/session/{id}` - End session

### Reminders
- `GET /api/v1/reminders/` - List reminders
- `POST /api/v1/reminders/` - Create reminder
- `PATCH /api/v1/reminders/{id}/toggle` - Toggle reminder
- `DELETE /api/v1/reminders/{id}` - Delete reminder

### Clinician
- `GET /api/v1/clinician/flags` - Get flagged patients
- `PATCH /api/v1/clinician/flags/{id}/reviewed` - Mark as reviewed
- `GET /api/v1/clinician/patients` - List assigned patients

## Architecture

### Digital Twin
The digital twin creates a personalized expected recovery curve based on:
- Surgery/condition type (appendectomy, cholecystectomy, cardiac, knee replacement, etc.)
- Age group
- BMI
- Lifestyle factors (smoking, chronic diseases)

### Escalation System
- **Level 0**: Normal recovery
- **Level 1**: Slight deviation → In-app insight
- **Level 2**: Sustained deviation → Suggest contacting provider
- **Level 3**: Critical trend → Highlight in clinician dashboard

### AI Safety Rules
- Never diagnose
- Never suggest medication changes
- Never use alarming language
- Always suggest consulting provider if persistent

## Color Palette

The app uses a calming, medical-neutral palette:
- **Sage Green** - Primary brand color (#7CB69D)
- **Soft Blue** - Secondary (#8CB8DE)
- **Muted Lavender** - Accent (#B8A9C9)
- **Warm White** - Background (#FAF8F5)
- **Soft Gray** - Text secondary (#6B7280)

## Supported Languages

- English (en)
- Hindi (hi)
- Telugu (te)
- Tamil (ta)

## License

Private - All rights reserved

## Support

For questions or issues, please contact the development team.
