"""
Text-to-Speech (TTS) Utility
===========================
Returns None so that the Flutter app uses its built-in on-device TTS (flutter_tts).
The voice bot text response is still sent via bot_text in the JSON response.
"""

from typing import Optional


async def synthesize_speech(text: str, language_code: str = "en") -> Optional[bytes]:
    """
    Returns None — the Flutter app handles TTS on-device using flutter_tts.
    This keeps the voice bot free and avoids requiring Google Cloud credentials.
    """
    return None
