"""
Auth JWT Utilities — Token creation and decoding
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException, status

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_REFRESH_EXPIRE_DAYS, JWT_SECRET_KEY


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Tworzy podpisany token JWT z payloadem użytkownika."""
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),      # subject = primary key w DB (UUID)
        "email": email,
        "role": role,
        "type": "access",
        "exp": exp,
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(8),   # unikalny ID tokena (do blacklistowania)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Token długotrwały — wyłącznie do wymiany na nowy access token."""
    exp = datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": exp,
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Dekoduje i weryfikuje token JWT. Rzuca HTTPException przy błędzie."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token wygasł — zaloguj się ponownie",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Nieprawidłowy token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )