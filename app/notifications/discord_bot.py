"""
FitAI Discord Bot — Nowa integracja (SQLite/SQLAlchemy)

Odpowiedzialność tego modułu:
  - Komenda /fit connect <kod>  — paruje konto FitAI z Discordem
  - send_workout_reminder()     — wysyła DM z przypomnieniem o treningu

Stara logika (profil, raport, dieta, AI-coach itp.) pozostaje
w fitai_discord_bot.py i NIE jest tu przenoszona.

Uruchomienie: bot jest startowany jako asyncio.create_task() przy starcie
FastAPI — patrz app/__init__.py → on_startup / on_shutdown.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from sqlmodel import Session

from app.database import engine
from app.notifications.service import consume_connect_code

logger = logging.getLogger(__name__)

# ─── Intents ──────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
# message_content nie jest potrzebny — używamy tylko slash commands i DM
intents.dm_messages = True


# ─── Bot ──────────────────────────────────────────────────────────────────────

class FitAIBot(discord.Client):
    """Klient Discord z drzewem slash-komend."""

    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        """Synchronizuje drzewo komend przy starcie bota."""
        await self.tree.sync()
        logger.info("[FitAI Bot] Slash commands synced.")

    async def on_ready(self) -> None:
        logger.info(f"[FitAI Bot] Zalogowany jako {self.user} (id={self.user.id})")


bot = FitAIBot()


# ─── /fit connect <kod> ───────────────────────────────────────────────────────

@bot.tree.command(
    name="fit-connect",
    description="Połącz swoje konto FitAI z Discordem podając kod z aplikacji.",
)
@app_commands.describe(kod="Kod wygenerowany w aplikacji FitAI, np. FIT-7K2M")
async def fit_connect(interaction: discord.Interaction, kod: str) -> None:
    """
    Weryfikuje jednorazowy kod parujący i zapisuje discord_user_id przy koncie.
    Używa sesji SQLAlchemy — NIE fitai_utils/DATA_FILE.
    """
    await interaction.response.defer(ephemeral=True)

    discord_id = str(interaction.user.id)

    try:
        with Session(engine) as session:
            success, display_name = consume_connect_code(
                code=kod,
                discord_id=discord_id,
                session=session,
            )
    except Exception as exc:
        logger.error(f"[FitAI Bot] Błąd bazy przy /fit-connect: {exc}", exc_info=True)
        await interaction.followup.send(
            "⚠️ Wystąpił błąd serwera. Spróbuj ponownie za chwilę.",
            ephemeral=True,
        )
        return

    if success:
        embed = discord.Embed(
            title="✅ Konto FitAI połączone!",
            description=(
                f"Hej **{display_name}**! Twoje konto FitAI zostało pomyślnie "
                "połączone z Discordem.\n\n"
                "Będziesz dostawać przypomnienia o treningu tutaj, przez DM. 💪\n"
                "Możesz zmienić godzinę przypomnień w aplikacji FitAI."
            ),
            color=0x1D9E75,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="FitAI — Twój asystent treningowy")
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Nieprawidłowy lub wygasły kod",
            description=(
                "Kod **"
                f"{kod.upper()}"
                "** jest nieprawidłowy lub wygasł (kody są ważne 10 minut).\n\n"
                "Wygeneruj nowy kod w aplikacji FitAI:\n"
                "**Ustawienia → Discord → Połącz konto**"
            ),
            color=0xE74C3C,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="FitAI — Twój asystent treningowy")
        await interaction.followup.send(embed=embed, ephemeral=True)


# ─── Wysyłanie przypomnień przez DM ───────────────────────────────────────────

async def send_workout_reminder(
    discord_user_id: str,
    workout_name: str,
    sport: Optional[str] = None,
) -> bool:
    """Wysyła DM z przypomnieniem o dzisiejszym treningu do podanego użytkownika.

    Args:
        discord_user_id: Snowflake ID użytkownika Discord jako string.
        workout_name:    Nazwa/opis dzisiejszego treningu, np. "Trening siłowy — nogi".
        sport:           Opcjonalny sport, np. "Koszykówka". Wyświetlany w embedzie.

    Returns:
        True  — DM wysłano pomyślnie.
        False — użytkownik zablokował DM, nie znaleziony lub inny błąd.
    """
    if not bot.is_ready():
        logger.warning("[FitAI Bot] send_workout_reminder wywołane przed gotowością bota.")
        return False

    try:
        user = await bot.fetch_user(int(discord_user_id))
    except (discord.NotFound, discord.HTTPException) as exc:
        logger.warning(f"[FitAI Bot] Nie znaleziono użytkownika {discord_user_id}: {exc}")
        return False

    embed = discord.Embed(
        title="🏋️ Przypomnienie o treningu!",
        description=f"Hej! Masz dziś zaplanowany trening — nie zapomnij o nim. 💪",
        color=0x185FA5,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="📋 Trening",
        value=workout_name,
        inline=False,
    )
    if sport:
        embed.add_field(
            name="🏅 Sport",
            value=sport,
            inline=True,
        )
    embed.set_footer(text="FitAI — wyłącz przypomnienia w Ustawieniach → Discord")

    try:
        await user.send(embed=embed)
        logger.info(f"[FitAI Bot] Wysłano przypomnienie do {discord_user_id}.")
        return True
    except discord.Forbidden:
        # User ma zablokowane DM od botów
        logger.warning(f"[FitAI Bot] Użytkownik {discord_user_id} ma zablokowane DM.")
        return False
    except discord.HTTPException as exc:
        logger.error(f"[FitAI Bot] Błąd HTTP przy wysyłaniu DM do {discord_user_id}: {exc}")
        return False
