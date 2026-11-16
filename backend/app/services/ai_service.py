"""
AI Orchestrator
===============
Single interface for all AI operations:
- LLM (Gemini) for insights, conversation, and safe language
- Food CV + drug interaction checking
- Voice STT/NLP extraction
- All LLM calls are safety-wrapped — never diagnose, never alarm
"""

import base64
import json
import re
from typing import Optional
from uuid import UUID

from google import genai
from google.genai import types
import httpx

from app.core.config import settings
from app.core.gemini import client as gemini_client
from app.models import Patient, DigitalTwin, DailyLog


SYSTEM_PROMPT = """You are a calm, observant recovery assistant for a patient recently discharged from hospital.

Your role:
- Ask gentle, natural questions to fill in their daily health log
- Notice patterns and offer soft, encouraging insights
- Support the patient emotionally without alarming them

Hard rules — you must NEVER:
- Diagnose any symptom or condition
- Suggest medication changes or dosage adjustments
- Use alarming words: "serious", "emergency", "dangerous", "immediately", "critical", "urgent"
- Predict outcomes or prognosis

When something seems off, say exactly this kind of thing:
"That's worth keeping an eye on — and worth mentioning to your care team at your next check-in."

Tone: warm, unhurried, conversational — like a knowledgeable friend.
"""


class AIOrchestrator:
    def __init__(self):
        self.client = gemini_client()
        self.model = settings.GEMINI_MODEL

    async def generate_patient_insight(
        self,
        metric: str,
        level: int,
        deviation_pct: float,
        recovery_day: int,
        patient: Patient,
    ) -> str:
        prompt = f"""
Patient profile summary:
- Condition: {patient.primary_condition}
- Recovery day: {recovery_day}
- Language: {patient.preferred_language}

Situation:
- Metric showing sustained deviation: {metric}
- Escalation level: {level} (1=slight, 2=moderate, 3=significant)
- Deviation from expected baseline: ~{deviation_pct:.0f}%

Generate a SHORT patient-facing insight message (1-2 sentences, max 40 words).
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=120,
            )
        )
        return response.text.strip()

    async def generate_clinician_summary(
        self,
        metric: str,
        level: int,
        logs: list,
        twin: DigitalTwin,
        patient: Patient,
    ) -> str:
        log_summary = "\n".join([
            f"Day {i+1}: {metric}={getattr(l, f'{metric}_score', 'N/A')}"
            for i, l in enumerate(logs[-7:])
        ])

        prompt = f"""
Patient: {patient.full_name}, Day {len(logs)} of recovery, Condition: {patient.primary_condition}
Flagged metric: {metric} at escalation level {level}

Recent log data:
{log_summary}

Write a brief clinician-facing summary (2-3 sentences, clinical tone).
Include: trend description, duration. No recommendations — just facts.
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=150,
            )
        )
        return response.text.strip()

    async def voice_conversation_turn(
        self,
        transcript: str,
        conversation_history: list,
        patient_context: dict,
        partial_log: dict,
    ) -> dict:
        filled = [k for k, v in partial_log.items() if v is not None]
        remaining = [m for m in ["pain", "fatigue", "sleep", "appetite", "mood", "note"] if m not in filled]

        system = SYSTEM_PROMPT + f"""
You are conducting a daily health check-in via voice.
Patient context: {json.dumps(patient_context)}
Fields still needed: {remaining}

After patient message:
1. Acknowledge what they said warmly
2. Ask about the NEXT field naturally

Return JSON:
{{
  "bot_text": "...",
  "extracted": {{"pain_score": null, "fatigue_score": null, "sleep_score": null, "appetite_score": null, "mood_score": null, "note": null}},
  "log_complete": false
}}

Only set log_complete: true when all 5 scores are collected.
"""
        # Collapse conversation history to a single string for simplicity
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history])
        full_prompt = f"History:\n{history_str}\n\nPatient says: {transcript}"

        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
            )
        )
        try:
            return json.loads(response.text.strip())
        except:
            return {"bot_text": "I didn't quite catch that.", "extracted": {}, "log_complete": False}

    async def identify_food(self, image_bytes: bytes, image_mime: str = "image/jpeg") -> list:
        prompt = """Identify the food items in this meal image.
Return ONLY a JSON array: [{"name": "...", "quantity": "...", "confidence": 0.0-1.0}]"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=image_mime)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        try:
            return json.loads(response.text.strip())
        except:
            return []

    async def check_drug_food_interactions(
        self, food_items: list, prescriptions: list
    ) -> list:
        if not food_items or not prescriptions:
            return []

        food_names = [f.get("name", "") for f in food_items]
        drug_names = [p.drug_name for p in prescriptions]

        if settings.DRUGBANK_API_KEY:
            try:
                return await self._drugbank_interaction_check(food_names, drug_names)
            except Exception:
                pass

        prompt = f"""Foods consumed: {', '.join(food_names)}
Current medications: {', '.join(drug_names)}

Check for known food-drug interactions. 
Return ONLY a JSON array of interactions found (empty array if none):
[{{
  "drug_name": "...",
  "severity": "low|moderate",
  "message": "brief, calm, non-alarming patient message",
  "advice": "practical timing advice"
}}]
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        try:
            return json.loads(response.text.strip())
        except:
            return []

    async def _drugbank_interaction_check(self, foods: list, drugs: list) -> list:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.DRUGBANK_BASE_URL}/food_interactions/check",
                json={"drugs": drugs, "foods": foods},
                headers={"Authorization": f"Bearer {settings.DRUGBANK_API_KEY}"},
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "drug_name": i["drug"],
                    "severity": "moderate" if i.get("severity") == "major" else "low",
                    "message": i.get("description", "")[:100],
                    "advice": i.get("management", "")[:80],
                }
                for i in data.get("interactions", [])
            ]
