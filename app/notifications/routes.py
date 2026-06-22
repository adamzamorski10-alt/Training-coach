"""
FitAI Notifications — Router

Endpointy REST dla integracji konta FitAI z Discordem oraz ustawień
codziennych przypomnień o treningu wysyłanych przez DM.

Prefiksy:
  POST  /api/discord/connect-code       — generuje kod parujący (ważny 10 min)
  GET   /api/discord/status             — status połączenia + ustawienia przypomnień
  POST  /api/discord/reminder-settings  — zapisuje godzinę i flagę przypomnień
  POST  /api/discord/disconnect         — rozłącza konto Discord
"""

import asyncio
import json
import logging
import random
import re
import string
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user   # ← ten sam Depends co w app/plan/routes.py itp.
from app.config import CRON_SECRET
from app.database import get_session, engine
from app.models import UserDB

logger = logging.getLogger(__name__)

_TZ_WARSAW = ZoneInfo("Europe/Warsaw")

router = APIRouter(prefix="/api/discord", tags=["discord"])

# ─── Stałe ────────────────────────────────────────────────────────────────────

_CODE_ALPHABET = string.ascii_uppercase + string.digits   # A-Z + 0-9
_CODE_CHARS = 4
_CODE_TTL_MINUTES = 10
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")                  # "HH:MM"


# ─── Schematy żądań / odpowiedzi ──────────────────────────────────────────────

class ConnectCodeResponse(BaseModel):
    code: str
    expires_at: str          # ISO 8601 UTC


class DiscordStatusResponse(BaseModel):
    connected: bool
    discord_user_id: str | None
    reminder_enabled: bool
    reminder_time: str | None


class ReminderSettingsRequest(BaseModel):
    reminder_time: str       # "HH:MM"
    reminder_enabled: bool


class ReminderSettingsResponse(BaseModel):
    reminder_time: str
    reminder_enabled: bool


class DisconnectResponse(BaseModel):
    disconnected: bool


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _generate_connect_code() -> str:
    """Zwraca kod w formacie 'FIT-XXXX' (4 losowe znaki A-Z0-9)."""
    suffix = "".join(random.choices(_CODE_ALPHABET, k=_CODE_CHARS))
    return f"FIT-{suffix}"


def _validate_hhmm(value: str) -> None:
    """Rzuca HTTPException 422 jeśli format godziny jest nieprawidłowy."""
    if not _TIME_RE.match(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nieprawidłowy format godziny — wymagany 'HH:MM', np. '18:00'.",
        )
    hour, minute = int(value[:2]), int(value[3:])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Godzina '{value}' jest poza dopuszczalnym zakresem (00:00–23:59).",
        )


def _get_user_or_404(current_user: UserDB, session: Session) -> UserDB:
    """Odświeża użytkownika z bazy — na wypadek gdyby obiekt był detached."""
    user = session.get(UserDB, current_user.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono konta użytkownika.",
        )
    return user


# ─── Endpointy ────────────────────────────────────────────────────────────────

@router.post(
    "/connect-code",
    response_model=ConnectCodeResponse,
    summary="Generuj kod parujący z Discordem",
)
def generate_connect_code(
    current_user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConnectCodeResponse:
    """
    Generuje jednorazowy kod parujący (np. 'FIT-7K2M') ważny 10 minut.
    Użytkownik wpisuje go w kanale Discorda, bot weryfikuje i łączy konta.
    Każde wywołanie nadpisuje poprzedni kod (można odświeżyć).
    """
    user = _get_user_or_404(current_user, session)

    code = _generate_connect_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_CODE_TTL_MINUTES)

    # Zapisz naive datetime (SQLite nie przechowuje strefy) — UTC przez konwencję
    user.discord_connect_code = code
    user.discord_connect_code_expires_at = expires_at.replace(tzinfo=None)
    user.updated_at = datetime.now()

    session.add(user)
    session.commit()

    return ConnectCodeResponse(
        code=code,
        expires_at=expires_at.isoformat(),
    )


@router.get(
    "/status",
    response_model=DiscordStatusResponse,
    summary="Status połączenia z Discordem",
)
def get_discord_status(
    current_user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DiscordStatusResponse:
    """
    Zwraca czy konto Discord jest połączone oraz aktualne ustawienia przypomnień.
    """
    user = _get_user_or_404(current_user, session)

    return DiscordStatusResponse(
        connected=user.discord_user_id is not None,
        discord_user_id=user.discord_user_id,
        reminder_enabled=user.reminder_enabled,
        reminder_time=user.reminder_time,
    )


@router.post(
    "/reminder-settings",
    response_model=ReminderSettingsResponse,
    summary="Zapisz ustawienia przypomnień Discord DM",
)
def update_reminder_settings(
    body: ReminderSettingsRequest,
    current_user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ReminderSettingsResponse:
    """
    Ustawia godzinę codziennego przypomnienia o treningu (format 'HH:MM')
    i włącza/wyłącza przypomnienia.

    Wymaga wcześniejszego połączenia konta Discord — jeśli `reminder_enabled`
    jest True, a `discord_user_id` jest puste, zwraca 409.
    """
    user = _get_user_or_404(current_user, session)

    _validate_hhmm(body.reminder_time)

    if body.reminder_enabled and user.discord_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Nie można włączyć przypomnień — konto Discord nie jest połączone. "
                "Najpierw użyj /api/discord/connect-code."
            ),
        )

    user.reminder_time = body.reminder_time
    user.reminder_enabled = body.reminder_enabled
    user.updated_at = datetime.now()

    session.add(user)
    session.commit()
    session.refresh(user)

    return ReminderSettingsResponse(
        reminder_time=user.reminder_time,
        reminder_enabled=user.reminder_enabled,
    )


@router.post(
    "/disconnect",
    response_model=DisconnectResponse,
    summary="Rozłącz konto Discord",
)
def disconnect_discord(
    current_user: UserDB = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DisconnectResponse:
    """
    Usuwa powiązanie z kontem Discord i wyłącza przypomnienia DM.
    Czyści: discord_user_id, discord_connect_code, discord_connect_code_expires_at.
    """
    user = _get_user_or_404(current_user, session)

    user.discord_user_id = None
    user.discord_connect_code = None
    user.discord_connect_code_expires_at = None
    user.reminder_enabled = False
    user.updated_at = datetime.now()

    session.add(user)
    session.commit()

    return DisconnectResponse(disconnected=True)


# ─── Cron endpoint — sprawdzanie i wysyłanie przypomnień ──────────────────────

class CheckRemindersResponse(BaseModel):
    checked: int          # ilu userów miało aktywne przypomnienia w tym oknie
    sent: int             # ile DM wysłano pomyślnie
    skipped_rest_day: int # pominięci bo dzień odpoczynku (brak treningu)
    errors: int           # błędy wysyłki (DM zablokowane itp.)
    ts: str               # timestamp wywołania (Europe/Warsaw)


_REMINDER_WINDOW_MINUTES = 2   # tolerancja ±2 min względem reminder_time usera
_MAX_CONCURRENT_DM = 10        # maks. równoległych wywołań Discord API


def _get_today_workout(user: UserDB) -> str | None:
    """Zwraca nazwę dzisiejszego treningu z weekly_plan_json usera lub None (dzień odpoczynku).

    weekly_plan_json to słownik {dzień_tygodnia: opis_treningu}, np.:
      {"Poniedziałek": "Siłownia — klatka i triceps", "Środa": "Bieganie 5km", ...}
    Klucze mogą być polskimi nazwami dni tygodnia lub angielskimi (fallback).
    """
    if not user.weekly_plan_json:
        return None

    try:
        plan: dict = json.loads(user.weekly_plan_json)
    except (json.JSONDecodeError, TypeError):
        return None

    if not plan:
        return None

    today = datetime.now(_TZ_WARSAW)

    # Polskie nazwy dni (isoweekday: 1=Pon … 7=Nie)
    _PL_DAYS = {
        1: "Poniedziałek",
        2: "Wtorek",
        3: "Środa",
        4: "Czwartek",
        5: "Piątek",
        6: "Sobota",
        7: "Niedziela",
    }
    _EN_DAYS = {
        1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
        5: "Friday", 6: "Saturday", 7: "Sunday",
    }

    day_pl = _PL_DAYS[today.isoweekday()]
    day_en = _EN_DAYS[today.isoweekday()]

    workout = plan.get(day_pl) or plan.get(day_en)

    # Pusty string / "odpoczynek" / "rest" traktujemy jako dzień odpoczynku
    if not workout:
        return None
    if workout.strip().lower() in {"odpoczynek", "rest", "dzień odpoczynku", "wolne", "-"}:
        return None

    return workout.strip()


@router.get(
    "/check-reminders",
    response_model=CheckRemindersResponse,
    summary="[CRON] Wyślij zaległe przypomnienia o treningu",
    tags=["cron"],
)
async def check_reminders(
    secret: str = Query(..., description="CRON_SECRET z env"),
) -> CheckRemindersResponse:
    """
    Endpoint wywoływany przez zewnętrzny cron (np. cron-job.org) co 1 minutę.
    NIE wymaga logowania JWT — zabezpieczony parametrem `secret`.

    Logika:
    1. Weryfikuje secret.
    2. Pobiera aktualny czas w strefie Europe/Warsaw.
    3. Wyszukuje userów z aktywnym przypomnieniem w oknie ±{_REMINDER_WINDOW_MINUTES} min.
    4. Pomija tych którym już dziś wysłano (last_reminder_sent_date == today).
    5. Wysyła DM równolegle (max {_MAX_CONCURRENT_DM} jednocześnie).
    6. Aktualizuje last_reminder_sent_date po udanej wysyłce.
    """
    # ── 1. Autoryzacja ────────────────────────────────────────────────────────
    if secret != CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nieprawidłowy secret.",
        )

    # ── 2. Aktualny czas warszawski ───────────────────────────────────────────
    now_warsaw = datetime.now(_TZ_WARSAW)
    today = now_warsaw.date()
    ts_str = now_warsaw.strftime("%Y-%m-%d %H:%M:%S %Z")

    logger.info(f"[FitAI Reminders] Sprawdzam przypomnienia o {ts_str}")

    # ── 3. Pobierz kandydatów z bazy ─────────────────────────────────────────
    # Filtr wstępny: reminder_enabled=True, discord_user_id NOT NULL,
    # last_reminder_sent_date != today (lub NULL).
    # Dopasowanie godziny robimy w Pythonie — SQLite nie ma funkcji STRFTIME
    # z obsługą TZ, a userów z włączonymi przypomnieniami jest zwykle < 1000.
    with Session(engine) as session:
        candidates: list[UserDB] = session.exec(
            select(UserDB).where(
                UserDB.reminder_enabled == True,       # noqa: E712
                UserDB.discord_user_id != None,        # noqa: E711
                UserDB.reminder_time != None,          # noqa: E711
            )
        ).all()

    # ── 4. Filtruj po godzinie i dacie ───────────────────────────────────────
    window = timedelta(minutes=_REMINDER_WINDOW_MINUTES)

    def _in_window(user: UserDB) -> bool:
        """Sprawdza czy reminder_time usera mieści się w aktualnym oknie czasowym."""
        try:
            h, m = int(user.reminder_time[:2]), int(user.reminder_time[3:])
        except (ValueError, TypeError, IndexError):
            return False
        reminder_dt = now_warsaw.replace(hour=h, minute=m, second=0, microsecond=0)
        return abs(now_warsaw - reminder_dt) <= window

    def _not_sent_today(user: UserDB) -> bool:
        return user.last_reminder_sent_date != today

    to_notify = [u for u in candidates if _in_window(u) and _not_sent_today(u)]

    logger.info(
        f"[FitAI Reminders] Kandydaci: {len(candidates)}, "
        f"w oknie czasowym i niewyslani: {len(to_notify)}"
    )

    # ── 5. Wysyłka równoległa z semaforem ────────────────────────────────────
    from app.notifications.discord_bot import send_workout_reminder

    sent = 0
    skipped_rest_day = 0
    errors = 0
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_DM)

    async def _send_one(user: UserDB) -> tuple[str, bool | None]:
        """Zwraca (user_id, True=wysłano | False=błąd | None=pominięto)."""
        workout = _get_today_workout(user)
        if workout is None:
            logger.info(f"[FitAI Reminders] Pominięto {user.id} — dzień odpoczynku.")
            return user.id, None

        async with semaphore:
            try:
                ok = await send_workout_reminder(
                    discord_user_id=user.discord_user_id,
                    workout_name=workout,
                    sport=user.sport_focus,
                )
                if ok:
                    logger.info(f"[FitAI Reminders] ✓ Wysłano DM → {user.discord_user_id}")
                else:
                    logger.warning(f"[FitAI Reminders] ✗ Błąd DM → {user.discord_user_id} (zablokowane?)")
                return user.id, ok
            except Exception as exc:
                logger.error(f"[FitAI Reminders] ✗ Wyjątek dla {user.id}: {exc}", exc_info=True)
                return user.id, False

    results = await asyncio.gather(*[_send_one(u) for u in to_notify])

    # Słownik: user.id → wynik
    result_map: dict[str, bool | None] = dict(results)

    # ── 6. Aktualizuj last_reminder_sent_date dla udanych wysyłek ────────────
    successful_ids = {uid for uid, ok in result_map.items() if ok is True}

    if successful_ids:
        with Session(engine) as session:
            users_to_update = session.exec(
                select(UserDB).where(UserDB.id.in_(successful_ids))
            ).all()
            for u in users_to_update:
                u.last_reminder_sent_date = today
                u.updated_at = datetime.now()
                session.add(u)
            session.commit()

    # ── 7. Zlicz wyniki ───────────────────────────────────────────────────────
    for uid, ok in result_map.items():
        if ok is True:
            sent += 1
        elif ok is None:
            skipped_rest_day += 1
        else:
            errors += 1

    logger.info(
        f"[FitAI Reminders] Gotowe — wysłano: {sent}, "
        f"dzień odpoczynku: {skipped_rest_day}, błędy: {errors}"
    )

    return CheckRemindersResponse(
        checked=len(to_notify),
        sent=sent,
        skipped_rest_day=skipped_rest_day,
        errors=errors,
        ts=ts_str,
    )