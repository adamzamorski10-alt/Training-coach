"""
Auth Routes — registration, login, password change, token refresh
"""

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, select

from app.auth import (
    _rate_limit_key,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import engine, get_session
from app.fitness.calculations import calc_calories, calc_protein
from app.models import UserDB
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=_rate_limit_key)


@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterRequest):
    """
    Rejestracja nowego użytkownika — tylko email i hasło.
    Numer użytkownika generowany automatycznie.
    """
    with Session(engine) as session:
        # Sprawdź unikalność e-maila
        existing = session.exec(
            select(UserDB).where(UserDB.email == payload.email.lower().strip())
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Konto z tym e-mailem już istnieje",
            )

        # Generuj unikalny numer użytkownika (atomowo w tej samej sesji)
        max_number_row = session.exec(
            select(UserDB.user_number)
            .where(UserDB.user_number.is_not(None))
            .order_by(UserDB.user_number.desc())
        ).first()
        next_number = (max_number_row or 0) + 1

        user = UserDB(
            user_key=f"native:user:{next_number}",
            email=payload.email.lower().strip(),
            nickname=None,                          # Nick nie jest wymagany
            user_number=next_number,
            hashed_password=hash_password(payload.password),
            name=payload.name or f"Użytkownik#{next_number:04d}",
            age=payload.age or 25,
            height=payload.height or 170.0,
            weight=payload.weight or 70.0,
            start_weight=payload.weight or 70.0,
            target_weight=payload.target_weight or 70.0,
            gender=payload.gender,
            goal=payload.goal,
            frequency=payload.frequency,
            diet=payload.diet,
            is_active=True,
        )
        user.calories_target = calc_calories(user)
        user.protein_target = calc_protein(user)
        session.add(user)
        try:
            session.commit()
            session.refresh(user)
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Konto z tym e-mailem już istnieje",
            )
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Błąd bazy danych: {exc}",
            )

        token = create_access_token(user.id, user.email, user.role)
        return TokenResponse(
            access_token=token,
            user_id=user.id,
            user_number=user.user_number,
            display_name=user.display_name,
            name=user.name,
            role=user.role,
            plan=user.plan,
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute;50/hour")
def login(request: Request, payload: LoginRequest):
    """
    Logowanie email + hasło. Zwraca JWT.
    Endpoint publiczny — nie wymaga tokena.
    """
    with Session(engine) as session:
        user = session.exec(
            select(UserDB).where(UserDB.email == payload.email.lower().strip())
        ).first()

        # Celowo jednolity komunikat błędu — nie ujawniamy czy email istnieje
        _INVALID = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy e-mail lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
        if not user:
            raise _INVALID
        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="To konto używa logowania zewnętrznego (Netlify Identity). "
                "Użyj oryginalnego dostawcy.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Konto zostało zablokowane. Skontaktuj się z pomocą techniczną.",
            )
        if not verify_password(payload.password, user.hashed_password):
            raise _INVALID

        token = create_access_token(user.id, user.email, user.role)
        return TokenResponse(
            access_token=token,
            user_id=user.id,
            user_number=user.user_number,
            display_name=user.display_name,
            name=user.name,
            role=user.role,
            plan=user.plan,
        )


@router.get("/me")
def me(user: UserDB = Depends(get_current_user)):
    """Zwraca profil aktualnie zalogowanego użytkownika."""
    return user.to_profile_dict()


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: UserDB = Depends(get_current_user),
):
    """Zmiana hasła — wymaga podania aktualnego hasła."""
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konto zewnętrzne — zmień hasło u dostawcy identity.",
        )
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Aktualne hasło jest nieprawidłowe",
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nowe hasło musi mieć co najmniej 8 znaków",
        )
    with Session(engine) as session:
        db_user = session.get(UserDB, user.id)
        db_user.hashed_password = hash_password(payload.new_password)
        db_user.updated_at = datetime.now()
        session.add(db_user)
        session.commit()
    return {"status": "ok", "message": "Hasło zostało zmienione"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(user: UserDB = Depends(get_current_user)):
    """
    Odświeżenie tokena — klient wysyła stary (wciąż ważny) token,
    dostaje nowy z przesuniętym `exp`. Bezpieczne zastępstwo refresh tokenów
    dla aplikacji SPA bez backendu sesji.
    """
    token = create_access_token(user.id, user.email, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        user_number=user.user_number,
        display_name=user.display_name,
        name=user.name,
        role=user.role,
        plan=user.plan,
    )


@router.get("/check-nickname")
def check_nickname(nickname: str, session: Session = Depends(get_session)):
    if not nickname or len(nickname.strip()) < 3:
        return {"available": False, "reason": "Za krótki (min. 3 znaki)"}

    normalized = nickname.strip().lower()
    if len(normalized) > 30:
        return {"available": False, "reason": "Za długi (max 30 znaków)"}
    if not re.match(r"^[a-z0-9_\-.]+$", normalized):
        return {"available": False, "reason": "Nieprawidłowe znaki (tylko a-z, 0-9, _ - .)"}

    existing = session.exec(select(UserDB).where(UserDB.nickname == normalized)).first()
    return {
        "available": existing is None,
        "nickname": normalized,
        "reason": None if existing is None else "Ten nick jest już zajęty",
    }


@router.post("/users/{user_id}", deprecated=True)
def create_or_update_user(user_id: str, profile: UserProfile):
    """DEPRECATED — wyłączony od FitAI v2.1. Użyj POST /auth/register."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Ten endpoint jest wyłączony. Użyj POST /auth/register.",
    )