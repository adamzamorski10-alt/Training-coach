"""
AI Service — LLM integration (Groq, Gemini) with fallbacks
"""

import json
import os
from datetime import datetime
from typing import Optional

from app.config import AI_PROVIDER, GEMINI_API_KEY, GROQ_API_KEY

try:
    import groq as _groq_module
except ImportError:
    _groq_module = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class AIError(str):
    """Marker for AI errors — distinguishes from regular strings."""
    pass


def _get_prompt(template: Optional[str], fallback: str, **kwargs) -> str:
    """
    Bezpieczne renderowanie szablonu promptu.
    Jeśli template jest None → użyj fallback.
    Wszystkie None-wartości w kwargs → zastąp pustym stringiem.
    """
    safe_kwargs = {k: (str(v) if v is not None else "brak") for k, v in kwargs.items()}
    source = template if template is not None else fallback
    try:
        return source.format(**safe_kwargs)
    except KeyError:
        return fallback


def call_groq(system: str, user_msg: str, max_tokens: int = 800) -> str | AIError:
    """Call Groq API."""
    if not _groq_module or not GROQ_API_KEY:
        return AIError("Groq API not available")
    
    try:
        client = _groq_module.Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return AIError(f"Groq error: {exc}")


def call_gemini(system: str, user_msg: str, max_tokens: int = 800) -> str | AIError:
    """Call Gemini API."""
    if not genai or not GEMINI_API_KEY:
        return AIError("Gemini API not available")
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-pro", system_instruction=system)
        response = model.generate_content(user_msg, generation_config={"max_output_tokens": max_tokens})
        return response.text.strip()
    except Exception as exc:
        return AIError(f"Gemini error: {exc}")


def ask_ai(system: str, user_msg: str, max_tokens: int = 800) -> str | AIError:
    """
    Ask LLM with failover logic.
    1. Try configured provider (AI_PROVIDER from env)
    2. Try fallback provider
    3. Return error
    """
    providers = []
    
    if AI_PROVIDER == "groq":
        providers = [call_groq, call_gemini]
    elif AI_PROVIDER == "gemini":
        providers = [call_gemini, call_groq]
    else:
        providers = [call_groq, call_gemini]
    
    for provider_func in providers:
        result = provider_func(system, user_msg, max_tokens)
        if not isinstance(result, AIError):
            return result
    
    # All providers failed
    return AIError("All AI providers failed")


# Fallback responses for when AI is unavailable
def fallback_recovery_tip(mood: Optional[int], energy: Optional[int]) -> str:
    """Fallback recovery tip when AI is unavailable."""
    if mood and mood <= 3:
        return "Nastrój niski — rozważ dodatkowy odpoczynek lub rozmowę z bliską osobą."
    if energy and energy <= 3:
        return "Energia niska — zadbaj o sen i nawodnienie dzisiaj."
    return "Obserwuj swoje samopoczucie i dostosuj intensywność treningu do potrzeb."


def fallback_diet_plan(kcal: int, protein: int) -> str:
    """Fallback diet plan when AI is unavailable."""
    return (
        f"AI niedostępne. Twoje makro na dziś: {kcal} kcal, białko {protein}g. "
        "Skoncentruj się na spożywaniu pełnowartościowych posiłków."
    )


def fallback_workout_plan(user_goal: str) -> str:
    """Fallback workout plan when AI is unavailable."""
    return (
        f"AI niedostępne. Bazując na Twoim celu ({user_goal}), "
        "wykonaj ulubiony trening lub skonsultuj się z trenerem."
    )
