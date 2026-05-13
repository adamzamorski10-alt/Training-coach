"""
FitAI Configuration — Environment, constants, settings
"""

import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fitai.db")

# ─── JWT / Auth ────────────────────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MIN", "10080"))   # 7 dni domyślnie

# ─── Rate Limiting ─────────────────────────────────────────────────────────────
AI_RATE_PER_MINUTE: str = os.getenv("AI_RATE_PER_MINUTE", "10/minute")
AI_RATE_PER_HOUR: str = os.getenv("AI_RATE_PER_HOUR", "50/hour")

# ─── AI Services ──────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")  # "groq" lub "gemini"

# ─── Nutrition Constants ──────────────────────────────────────────────────────
# XP system
_XP_CHECKIN = 10
_XP_WEIGHT_LOGGED = 15
_XP_WORKOUT_LOGGED = 50
_XP_MEAL_LOGGED = 5
_XP_RECOVERY_FILLED = 8
_XP_DRILL_ATTEMPT = 25
_XP_DRILL_COMPLETED = 100

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ─── App Info ──────────────────────────────────────────────────────────────────
APP_VERSION = "2.0.0"
APP_NAME = "FitAI"

# ─── Feature Flags ────────────────────────────────────────────────────────────
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
