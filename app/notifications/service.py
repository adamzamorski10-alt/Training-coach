"""
FitAI Notifications — Service layer

Logika biznesowa dla integracji Discord:
  - weryfikacja i konsumpcja kodu parującego
  - pomocnicze operacje na polach discord_* w UserDB
"""

from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlmodel import Session, select

from app.models import UserDB


def consume_connect_code(
    code: str,
    discord_id: str,
    session: Session,
) -> Tuple[bool, Optional[str]]:
    """Weryfikuje kod parujący i przypisuje discord_user_id do konta.

    Wyszukuje użytkownika po `discord_connect_code`, sprawdza czy kod nie wygasł,
    a jeśli wszystko się zgadza — zapisuje `discord_user_id` i czyści kod.

    Args:
        code:       Kod wpisany przez użytkownika na Discordzie, np. "FIT-7K2M".
        discord_id: Snowflake ID konta Discord jako string.
        session:    Aktywna sesja SQLModel/SQLAlchemy.

    Returns:
        (True, display_name)  — gdy kod poprawny i nie wygasł.
        (False, None)         — gdy kod nieznaleziony lub wygasł.
    """
    code_upper = code.strip().upper()

    statement = select(UserDB).where(UserDB.discord_connect_code == code_upper)
    user: Optional[UserDB] = session.exec(statement).first()

    if user is None:
        return False, None

    # Sprawdź wygaśnięcie — porównuj w UTC
    expires_at = user.discord_connect_code_expires_at
    if expires_at is None:
        return False, None

    # Normalizuj strefę czasową: jeśli datetime jest naive, traktuj jako UTC
    now_utc = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now_utc > expires_at:
        # Kod wygasł — wyczyść dla porządku
        user.discord_connect_code = None
        user.discord_connect_code_expires_at = None
        session.add(user)
        session.commit()
        return False, None

    # Kod ważny — zapisz discord_user_id, wyczyść kod parujący
    user.discord_user_id = str(discord_id)
    user.discord_connect_code = None
    user.discord_connect_code_expires_at = None
    user.updated_at = datetime.now()

    session.add(user)
    session.commit()
    session.refresh(user)

    display_name: str = user.nickname or user.name or user.display_name
    return True, display_name
