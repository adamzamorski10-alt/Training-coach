"""
Auth Dependencies — FastAPI Depends for route protection
"""

import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.auth.jwt_utils import decode_token
from app.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.database import engine
from app.models import UserDB

_bearer_scheme = HTTPBearer(auto_error=False)


def _rate_limit_key(request: Request) -> str:
    """Use Bearer sub (user UUID) if present, otherwise fall back to client IP."""
    from slowapi.util import get_remote_address
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},   # key only — expiry checked elsewhere
            )
            return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> UserDB:
    """
    FastAPI Dependency — wyciąga użytkownika z Bearer tokena.

    Użycie w endpointach:
        @app.get("/app/profile")
        def profile(user: UserDB = Depends(get_current_user)):
            return user.to_profile_dict()
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak tokena autoryzacji",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)

    # Odrzuć refresh tokeny użyte jako access token.
    # type == None = stare tokeny bez pola (kompatybilność wsteczna) — OK.
    token_type = payload.get("type")
    if token_type is not None and token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy typ tokenu — użyj access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]   # UUID string
    with Session(engine) as session:
        user = session.get(UserDB, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Użytkownik z tokena nie istnieje",
        )
    return user


def get_current_pro_user(user: UserDB = Depends(get_current_user)) -> UserDB:
    """Dependency — wymaga planu PRO."""
    if user.role not in ("pro_user", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ta funkcja wymaga planu PRO",
        )
    return user


def get_current_admin(user: UserDB = Depends(get_current_user)) -> UserDB:
    """Dependency — wymaga roli admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora",
        )
    return user
