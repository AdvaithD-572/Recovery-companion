from fastapi import HTTPException
from google import genai

from app.core.config import settings


def client():
    key = settings.GEMINI_API_KEY.strip()
    if not key or key in {"your-gemini-api-key", "PASTE_YOUR_GOOGLE_KEY_HERE"}:
        raise HTTPException(503, "Image and language assistance is unavailable. Use manual entry.")
    return genai.Client(api_key=key)
