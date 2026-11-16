"""
Voice Bot Router
================
Manages multi-turn voice conversations that fill the daily log.
Each session has a UUID. Audio is streamed in base64 chunks.
"""

import base64
import json
import uuid as uuid_module
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.gemini import client as gemini_client
from app.core.database import get_db
from app.core.security import get_current_patient
from app.models import Patient
from app.schemas import VoiceMessageRequest, VoiceMessageResponse, VoiceSessionStart
from app.services.ai_service import AIOrchestrator
from app.utils.stt import transcribe_audio
from app.utils.tts import synthesize_speech

router = APIRouter()
SESSION_TTL = 3600  # 1 hour


@router.get("/localize")
async def localize_questions(
    language: str = "en-US",
    patient: Patient = Depends(get_current_patient),
):
    """
    Return all voice check-in questions translated to the given language using Gemini.
    language: BCP-47 code e.g. en-US, hi-IN, te-IN, ta-IN
    """
    questions = [
        {"field": "pain_score", "text": "How are you feeling today? Tell me about your pain level on a scale of 0 to 10."},
        {"field": "sleep_score", "text": "How was your sleep last night? Give me a number from 0 to 10."},
        {"field": "appetite_score", "text": "How's your appetite today? Rate it from 0 to 10."},
        {"field": "mood_score", "text": "How's your mood? Give me a number from 0 to 10."},
        {"field": "fatigue_score", "text": "How's your energy level today? Rate from 0 to 10."},
        {"field": "mobility_score", "text": "How's your mobility and movement today? Rate from 0 to 10."},
    ]

    if language.startswith("en"):
        return {"language": language, "questions": questions}

    try:
        from google import genai
        from google.genai import types as gtypes
        client = gemini_client()

        questions_text = "\n".join([f"{i+1}. {q['text']}" for i, q in enumerate(questions)])
        prompt = f"""Translate these health check-in questions to the language with BCP-47 code: {language}
Keep the same meaning and warmth. Keep the 0-10 scale instruction clear.
Return ONLY a JSON array of strings, one translated question per item, in the same order.

Questions to translate:
{questions_text}"""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=gtypes.GenerateContentConfig(response_mime_type="application/json"),
        )
        import json
        translated = json.loads(response.text.strip())
        if isinstance(translated, list) and len(translated) == len(questions):
            for i, q in enumerate(questions):
                q["text"] = translated[i]
    except Exception:
        pass  # Fall back to English if translation fails

    return {"language": language, "questions": questions}



async def get_redis():
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


def get_ai() -> AIOrchestrator:
    return AIOrchestrator()


@router.post("/session/start")
async def start_voice_session(
    payload: VoiceSessionStart,
    patient: Patient = Depends(get_current_patient),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Initialise a new voice check-in session."""
    session_id = str(uuid_module.uuid4())
    lang = payload.language or patient.preferred_language or "en"

    session_data = {
        "patient_id": str(patient.id),
        "language": lang,
        "history": [],       # conversation history for LLM
        "partial_log": {     # fields being filled
            "pain_score": None,
            "fatigue_score": None,
            "sleep_score": None,
            "appetite_score": None,
            "mood_score": None,
            "note": None,
        },
        "log_complete": False,
    }

    await redis.setex(f"voice:{session_id}", SESSION_TTL, json.dumps(session_data))

    # Generate opening message
    opening = _get_opening_message(patient.full_name.split()[0], lang)

    return {
        "session_id": session_id,
        "bot_text": opening,
        "language": lang,
    }


@router.post("/session/{session_id}/message", response_model=VoiceMessageResponse)
async def send_voice_message(
    session_id: str,
    payload: VoiceMessageRequest,
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    ai: AIOrchestrator = Depends(get_ai),
):
    # Load session
    raw = await redis.get(f"voice:{session_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Session expired or not found")

    session = json.loads(raw)
    if session["patient_id"] != str(patient.id):
        raise HTTPException(status_code=403, detail="Session does not belong to this patient")

    # Transcribe audio
    audio_bytes = base64.b64decode(payload.audio_base64)
    lang = payload.language or session["language"]

    transcript, detected_lang = await transcribe_audio(audio_bytes, lang)
    if not transcript.strip():
        return VoiceMessageResponse(
            session_id=session_id,
            transcript="",
            bot_text="I didn't catch that — could you say that again?",
            audio_base64=await _tts(
                "I didn't catch that — could you say that again?", detected_lang
            ),
            extracted_log=None,
            log_complete=False,
            detected_language=detected_lang,
        )

    # Update language if auto-detected
    session["language"] = detected_lang

    # Build patient context
    patient_context = {
        "name": patient.full_name.split()[0],
        "condition": patient.primary_condition or "recovery",
        "language": detected_lang,
    }

    # LLM conversation turn
    history = session.get("history", [])
    result = await ai.voice_conversation_turn(
        transcript=transcript,
        conversation_history=history,
        patient_context=patient_context,
        partial_log=session["partial_log"],
    )

    bot_text = result.get("bot_text", "")
    extracted = result.get("extracted", {})
    log_complete = result.get("log_complete", False)

    # Merge extracted values into partial log
    for field, value in extracted.items():
        if value is not None:
            session["partial_log"][field] = value

    # Update conversation history
    history.append({"role": "user", "content": transcript})
    history.append({"role": "assistant", "content": bot_text})
    session["history"] = history[-12:]   # keep last 6 turns (12 messages)
    session["log_complete"] = log_complete

    if log_complete:
        bot_text = "Your draft is ready. Review each value before saving your check-in."

    # Persist session
    await redis.setex(f"voice:{session_id}", SESSION_TTL, json.dumps(session))

    # TTS for bot response
    audio_b64 = await _tts(bot_text, detected_lang)

    return VoiceMessageResponse(
        session_id=session_id,
        transcript=transcript,
        bot_text=bot_text,
        audio_base64=audio_b64,
        extracted_log=session["partial_log"],
        log_complete=log_complete,
        detected_language=detected_lang,
    )


@router.delete("/session/{session_id}")
async def end_voice_session(
    session_id: str,
    patient: Patient = Depends(get_current_patient),
    redis: aioredis.Redis = Depends(get_redis),
):
    stored = await redis.get(f"voice:{session_id}")
    if not stored or json.loads(stored).get("patient_id") != str(patient.id):
        raise HTTPException(404, "Session not found")
    await redis.delete(f"voice:{session_id}")
    return {"status": "session closed"}


async def _tts(text: str, language: str) -> Optional[str]:
    try:
        audio = await synthesize_speech(text, language)
        return base64.b64encode(audio).decode()
    except Exception:
        return None


def _get_opening_message(first_name: str, lang: str) -> str:
    messages = {
        "en": f"Hi {first_name}, it's time for your daily check-in. This should only take a minute. How are you feeling today?",
        "hi": f"नमस्ते {first_name}, आपका दैनिक चेक-इन का समय है। आज आप कैसा महसूस कर रहे हैं?",
        "te": f"హలో {first_name}, మీ రోజువారీ చెక్-ఇన్ సమయం వచ్చింది. నేడు మీరు ఎలా ఉన్నారు?",
        "ta": f"வணக்கம் {first_name}, உங்கள் தினசரி செக்-இன் நேரம் வந்தது. இன்று நீங்கள் எப்படி உணர்கிறீர்கள்?",
    }
    return messages.get(lang, messages["en"])
