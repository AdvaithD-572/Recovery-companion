"""
Speech-to-Text (STT) Utility
===========================
Uses Gemini's audio understanding for transcription.
Falls back gracefully if audio processing fails.
"""

from typing import Tuple
from google import genai
from google.genai import types
from app.core.config import settings
from app.core.gemini import client as gemini_client


async def transcribe_audio(audio_bytes: bytes, language_code: str = "en-US") -> Tuple[str, str]:
    """
    Transcribe audio bytes to text using Gemini.
    Returns (transcript, detected_language).
    """
    lang_map = {
        "en": "en-US",
        "hi": "hi-IN",
        "te": "te-IN",
        "ta": "ta-IN",
    }
    full_lang = lang_map.get(language_code, language_code)

    try:
        client = gemini_client()
        
        prompt = f"""Transcribe the speech in this audio clip to text exactly as spoken.
The speaker is communicating in language code: {full_lang}.
Return only the transcribed text, nothing else."""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            ],
        )
        transcript = response.text.strip() if response.text else ""
        return transcript, full_lang
    except Exception:
        return "", full_lang
