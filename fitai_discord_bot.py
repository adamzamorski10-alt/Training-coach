"""
FitAI Discord Bot
=================
Wymagania: pip install discord.py anthropic aiohttp python-dotenv
Plik .env: DISCORD_TOKEN=... ANTHROPIC_API_KEY=...

Komendy:
  /fit profil           - Wyświetl lub utwórz profil
  /fit raport           - Złóż dzienny raport
  /fit dieta            - Pobierz plan diety na dziś
  /fit trening          - Pobierz plan treningowy na dziś
  /fit postepy          - Podsumowanie tygodniowe
  /fit cel              - Zmień cel
  /fit pomoc            - Lista komend
"""

import discord
from discord.ext import commands, tasks
import anthropic
import json
import os
import asyncio
from datetime import datetime, date, timedelta, timezone
from dotenv import load_dotenv
from fitai_utils import load_db, save_db, get_user, save_user, calc_calories, calc_protein

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ─── AI helper ────────────────────────────────────────────────────────────────

def ask_claude(system: str, user_msg: str, max_tokens: int = 800) -> str:
    try:
        message = ai_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text
    except Exception as e:
        return f"Błąd AI: {e}"


# ─── Embeds helpers ───────────────────────────────────────────────────────────

def profile_embed(profile: dict, username: str) -> discord.Embed:
    kcal = calc_calories(profile)
    protein = calc_protein(profile)
    embed = discord.Embed(
        title=f"🏋️ Profil FitAI — {profile.get('name', username)}",
        color=0x185FA5,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="📊 Dane podstawowe",
        value=(
            f"Wiek: **{profile.get('age', '?')}** lat\n"
            f"Wzrost: **{profile.get('height', '?')}** cm\n"
            f"Waga: **{profile.get('weight', '?')}** kg\n"
            f"Cel wagowy: **{profile.get('target_weight', '?')}** kg"
        ),
        inline=True,
    )
    embed.add_field(
        name="🎯 Cel i aktywność",
        value=(
            f"Cel: **{profile.get('goal', '?')}**\n"
            f"Aktywność: **{profile.get('frequency', '?')}**\n"
            f"Sporty: {', '.join(profile.get('sports', [])) or '—'}"
        ),
        inline=True,
    )
    embed.add_field(
        name="🥗 Dieta",
        value=(
            f"Preferencje: **{profile.get('diet', '?')}**\n"
            f"Kalorie docelowe: **{kcal} kcal/dzień**\n"
            f"Białko docelowe: **{protein}g/dzień**"
        ),
        inline=False,
    )
    logs = profile.get("logs", [])
    embed.set_footer(text=f"Zalogowanych dni: {len(logs)} | FitAI Bot")
    return embed


# ─── Slash Commands ───────────────────────────────────────────────────────────

@tree.command(name="fit", description="Główna komenda FitAI")
@discord.app_commands.describe(akcja="Akcja: profil | raport | dieta | trening | postepy | pomoc")
async def fit(interaction: discord.Interaction, akcja: str = "pomoc"):
    akcja = akcja.strip().lower()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    profile = get_user(user_id)

    # ── POMOC ──────────────────────────────────────────────────────────────────
    if akcja == "pomoc":
        embed = discord.Embed(title="🤖 FitAI Bot — Komendy", color=0x185FA5)
        embed.add_field(
            name="Dostępne komendy",
            value=(
                "`/fit profil` — Wyświetl swój profil\n"
                "`/fit raport` — Złóż dzienny raport (co jadłeś, co ćwiczyłeś)\n"
                "`/fit dieta` — Plan diety na dziś od AI\n"
                "`/fit trening` — Plan treningowy na dziś od AI\n"
                "`/fit postepy` — Tygodniowe podsumowanie\n"
                "`/fit cel <nowy cel>` — Zmień cel\n"
                "`/fit pomoc` — Ta wiadomość\n\n"
                "🌐 Pełny dashboard: **fitai.twoja-domena.pl**"
            ),
        )
        await interaction.response.send_message(embed=embed)
        return

    # ── PROFIL ─────────────────────────────────────────────────────────────────
    if akcja == "profil":
        if not profile:
            await interaction.response.send_message(
                "❌ Nie masz jeszcze profilu! Użyj `/fit setup` lub załóż profil na stronie **fitai.twoja-domena.pl**.\n\n"
                "Możesz też wypełnić profil tu przez Discord — wpisz `/fit setup`.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(embed=profile_embed(profile, username))
        return

    # ── RAPORT ─────────────────────────────────────────────────────────────────
    if akcja == "raport":
        if not profile:
            await interaction.response.send_message("❌ Najpierw utwórz profil: `/fit setup`", ephemeral=True)
            return

        await interaction.response.send_message(
            "📝 **Dzienny raport FitAI**\n\n"
            "Odpowiedz na poniższe pytania (wyślij jako jedną wiadomość, rozdzielając sekcje `---`):\n\n"
            "**1. Co dziś jadłeś?**\n"
            "**2. Co ćwiczyłeś?**\n"
            "**3. Samopoczucie?**\n"
            "**4. Waga (opcjonalnie)?**\n\n"
            "Przykład:\n"
            "```\n"
            "Owsianka rano, kurczak z ryżem na obiad, sałatka wieczorem\n"
            "---\n"
            "Siłownia 45 min, klatka i triceps\n"
            "---\n"
            "Dobre samopoczucie, trochę zmęczony po treningu\n"
            "---\n"
            "79.5\n"
            "```"
        )

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Upłynął czas oczekiwania na raport.", ephemeral=True)
            return

        parts = [p.strip() for p in msg.content.split("---")]
        food = parts[0] if len(parts) > 0 else ""
        workout = parts[1] if len(parts) > 1 else ""
        mood = parts[2] if len(parts) > 2 else ""
        weight_str = parts[3] if len(parts) > 3 else ""

        log_entry = {
            "date": date.today().isoformat(),
            "food": food,
            "workout": workout,
            "mood": mood,
            "weight": float(weight_str) if weight_str else None,
        }

        if "logs" not in profile:
            profile["logs"] = []
        profile["logs"].append(log_entry)
        if weight_str:
            try:
                profile["weight"] = float(weight_str)
            except ValueError:
                pass
        save_user(user_id, profile)

        thinking_msg = await msg.reply("🤖 Analizuję Twój dzień i przygotowuję plan na jutro...")

        system = (
            "Jesteś osobistym asystentem fitness i diety. Piszesz po polsku. "
            "Analizujesz dzienne raporty i tworzysz konkretny plan na kolejny dzień."
        )
        kcal = calc_calories(profile)
        user_msg = (
            f"Profil: {json.dumps(profile, ensure_ascii=False)}\n\n"
            f"Raport z dziś ({date.today().strftime('%A %d.%m.%Y')}):\n"
            f"- Jedzenie: {food or 'nie podano'}\n"
            f"- Trening: {workout or 'nie podano'}\n"
            f"- Samopoczucie: {mood or 'nie podano'}\n"
            f"- Waga: {weight_str or 'nie podano'} kg\n\n"
            f"Docelowe kalorie: {kcal} kcal\n\n"
            "Krótko (max 300 słów) oceń dzień i podaj plan na jutro (dieta + trening). "
            "Uwzględnij zmęczenie/ból jeśli jest. Bądź konkretny i motywujący."
        )

        ai_response = ask_claude(system, user_msg)

        embed = discord.Embed(
            title="📊 Analiza dnia + Plan na jutro",
            description=ai_response,
            color=0x1D9E75,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"FitAI | {date.today().strftime('%d.%m.%Y')}")
        await thinking_msg.edit(content=None, embed=embed)
        return

    # ── DIETA ──────────────────────────────────────────────────────────────────
    if akcja == "dieta":
        if not profile:
            await interaction.response.send_message("❌ Najpierw utwórz profil: `/fit setup`", ephemeral=True)
            return
        await interaction.response.defer()
        kcal = calc_calories(profile)
        protein = calc_protein(profile)
        system = (
            "Jesteś dietetykiem sportowym. Piszesz po polsku. "
            "Tworzysz konkretne plany posiłków z gramaturą i kaloriami."
        )
        user_msg = (
            f"Profil: {json.dumps(profile, ensure_ascii=False)}\n"
            f"Docelowe kalorie: {kcal} kcal, białko: {protein}g\n\n"
            f"Utwórz plan DIETY NA DZIŚ ({datetime.now().strftime('%A')}) — "
            f"4 posiłki z dokładną gramaturą i kaloriami. "
            f"Dieta: {profile.get('diet', 'brak preferencji')}, "
            f"alergie: {profile.get('allergies', 'brak')}, cel: {profile.get('goal', '?')}. "
            "Na końcu podaj łączne makroskładniki. Max 350 słów."
        )
        ai_response = ask_claude(system, user_msg)
        embed = discord.Embed(
            title=f"🥗 Plan diety na dziś — {kcal} kcal",
            description=ai_response,
            color=0x1D9E75,
        )
        embed.set_footer(text="FitAI | Wygenerowano przez AI")
        await interaction.followup.send(embed=embed)
        return

    # ── TRENING ────────────────────────────────────────────────────────────────
    if akcja == "trening":
        if not profile:
            await interaction.response.send_message("❌ Najpierw utwórz profil: `/fit setup`", ephemeral=True)
            return
        await interaction.response.defer()
        system = (
            "Jesteś trenerem personalnym. Piszesz po polsku. "
            "Tworzysz konkretne plany treningowe z seriami i powtórzeniami."
        )
        recent_workouts = [
            l.get("workout", "")
            for l in profile.get("logs", [])[-7:]
            if l.get("workout")
        ]
        user_msg = (
            f"Profil: {json.dumps(profile, ensure_ascii=False)}\n"
            f"Ostatnie treningi: {'; '.join(recent_workouts) if recent_workouts else 'brak danych'}\n\n"
            f"Utwórz plan TRENINGU NA DZIŚ ({datetime.now().strftime('%A')}) — "
            f"podaj nazwę sesji, 5-6 ćwiczeń z seriami/powtórzeniami i krótkimi wskazówkami. "
            f"Cel: {profile.get('goal', '?')}, sporty: {', '.join(profile.get('sports', [])) or 'ogólne'}. "
            "Unikaj partii mięśniowych zmęczonych z ostatnich dni. Max 300 słów."
        )
        ai_response = ask_claude(system, user_msg)
        embed = discord.Embed(
            title=f"💪 Plan treningowy na dziś",
            description=ai_response,
            color=0x185FA5,
        )
        embed.set_footer(text="FitAI | Wygenerowano przez AI")
        await interaction.followup.send(embed=embed)
        return

    # ── POSTĘPY ────────────────────────────────────────────────────────────────
    if akcja in ("postepy", "postępy"):
        if not profile:
            await interaction.response.send_message("❌ Najpierw utwórz profil: `/fit setup`", ephemeral=True)
            return
        await interaction.response.defer()
        logs = profile.get("logs", [])
        week_logs = logs[-7:] if logs else []

        # Statystyki
        weights = [l["weight"] for l in week_logs if l.get("weight")]
        workouts_done = sum(1 for l in week_logs if l.get("workout") and "brak" not in l["workout"].lower())

        system = "Jesteś analitykiem fitness. Piszesz po polsku. Dajesz motywujące ale realistyczne podsumowania."
        user_msg = (
            f"Profil: {json.dumps(profile, ensure_ascii=False)}\n"
            f"Logi z ostatnich 7 dni: {json.dumps(week_logs, ensure_ascii=False)}\n\n"
            "Podaj krótkie tygodniowe podsumowanie (max 250 słów): "
            "co szło dobrze, co wymaga poprawy, top 3 rekomendacje na następny tydzień."
        )
        ai_response = ask_claude(system, user_msg)

        embed = discord.Embed(
            title="📈 Tygodniowe podsumowanie",
            color=0x7F77DD,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="📊 Statystyki tygodnia",
            value=(
                f"Treningi wykonane: **{workouts_done}/7**\n"
                f"Zalogowane dni: **{len(week_logs)}**\n"
                f"Waga: **{weights[-1]:.1f} kg**" if weights else "Waga: **brak danych**"
            ),
            inline=True,
        )
        embed.add_field(name="🤖 Analiza AI", value=ai_response[:1024], inline=False)
        embed.set_footer(text="FitAI | Analiza tygodniowa")
        await interaction.followup.send(embed=embed)
        return

    # ── SETUP (onboarding przez Discord) ──────────────────────────────────────
    if akcja == "setup":
        if profile:
            await interaction.response.send_message(
                f"✅ Masz już profil! Użyj `/fit profil` aby go zobaczyć.\n"
                f"Aby zresetować profil, napisz `/fit reset`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"👋 Hej **{username}**! Zacznijmy konfigurację Twojego profilu FitAI.\n\n"
            "Proszę odpowiedz na poniższe pytania rozdzielając odpowiedzi znakiem `|`:\n\n"
            "```\n"
            "Imię | Wiek | Wzrost(cm) | Waga(kg) | Waga docelowa(kg) | Płeć\n"
            "```\n"
            "Przykład: `Marek | 28 | 182 | 90 | 80 | mężczyzna`"
        )

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg1 = await bot.wait_for("message", check=check, timeout=120)
            parts = [p.strip() for p in msg1.content.split("|")]

            new_profile = {
                "name": parts[0] if len(parts) > 0 else username,
                "age": int(parts[1]) if len(parts) > 1 else 25,
                "height": int(parts[2]) if len(parts) > 2 else 175,
                "weight": float(parts[3]) if len(parts) > 3 else 75,
                "target_weight": float(parts[4]) if len(parts) > 4 else 70,
                "gender": parts[5].lower() if len(parts) > 5 else "mężczyzna",
                "start_weight": float(parts[3]) if len(parts) > 3 else 75,
                "created_at": datetime.now().isoformat(),
                "logs": [],
            }

            await msg1.reply(
                "Świetnie! Teraz cel:\n"
                "`1` Redukcja tłuszczu | `2` Masa mięśniowa | `3` Kondycja | "
                "`4` Utrzymanie wagi | `5` Zdrowy styl życia"
            )
            msg2 = await bot.wait_for("message", check=check, timeout=60)
            goals = {
                "1": "Redukcja tkanki tłuszczowej",
                "2": "Budowa masy mięśniowej",
                "3": "Poprawa kondycji",
                "4": "Utrzymanie wagi",
                "5": "Zdrowy tryb życia",
            }
            new_profile["goal"] = goals.get(msg2.content.strip(), "Zdrowy tryb życia")

            await msg2.reply(
                "Jak często trenujesz?\n"
                "`1` Nie trenuję | `2` 1-2×/tyg | `3` 3-4×/tyg | `4` 5-6×/tyg | `5` Codziennie"
            )
            msg3 = await bot.wait_for("message", check=check, timeout=60)
            freqs = {
                "1": "sedentaryczny",
                "2": "1-2 razy w tygodniu",
                "3": "3-4 razy w tygodniu",
                "4": "5-6 razy w tygodniu",
                "5": "Codziennie",
            }
            new_profile["frequency"] = freqs.get(msg3.content.strip(), "3-4 razy w tygodniu")

            await msg3.reply("Jakie sporty uprawiasz? (np. `siłownia, bieganie, rower` lub `brak`)")
            msg4 = await bot.wait_for("message", check=check, timeout=60)
            sports_raw = msg4.content.strip()
            new_profile["sports"] = [] if sports_raw.lower() == "brak" else [s.strip() for s in sports_raw.split(",")]

            await msg4.reply(
                "Rodzaj diety? (wpisz numer)\n"
                "`1` Brak preferencji | `2` Wegetariańska | `3` Wegańska | "
                "`4` Ketogeniczna | `5` Śródziemnomorska | `6` High-protein"
            )
            msg5 = await bot.wait_for("message", check=check, timeout=60)
            diets = {
                "1": "Brak preferencji",
                "2": "Wegetariańska",
                "3": "Wegańska",
                "4": "Ketogeniczna",
                "5": "Śródziemnomorska",
                "6": "High-protein",
            }
            new_profile["diet"] = diets.get(msg5.content.strip(), "Brak preferencji")
            new_profile["allergies"] = ""

            save_user(user_id, new_profile)
            await msg5.reply(
                embed=discord.Embed(
                    title="✅ Profil FitAI utworzony!",
                    description=(
                        f"Witaj **{new_profile['name']}**! Twój profil jest gotowy.\n\n"
                        f"• Cel: **{new_profile['goal']}**\n"
                        f"• Kalorie docelowe: **{calc_calories(new_profile)} kcal/dzień**\n"
                        f"• Białko docelowe: **{calc_protein(new_profile)}g/dzień**\n\n"
                        "Użyj `/fit dieta` lub `/fit trening` aby zacząć! 🚀"
                    ),
                    color=0x1D9E75,
                )
            )

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Czas minął. Spróbuj `/fit setup` ponownie.", ephemeral=True)
        return

    # ── RESET ──────────────────────────────────────────────────────────────────
    if akcja == "reset":
        db = load_db()
        if user_id in db:
            del db[user_id]
            save_db(db)
            await interaction.response.send_message("🗑️ Profil został usunięty. Użyj `/fit setup` aby zacząć od nowa.", ephemeral=True)
        else:
            await interaction.response.send_message("Nie masz profilu do usunięcia.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"❓ Nieznana akcja: `{akcja}`. Użyj `/fit pomoc` aby zobaczyć dostępne komendy.", ephemeral=True
    )


# ─── Codzienne przypomnienia ──────────────────────────────────────────────────

@tasks.loop(hours=24)
async def daily_reminder():
    """Wysyła codzienne przypomnienie o raporcie (opcjonalne)."""
    db = load_db()
    today = date.today().isoformat()
    for user_id, profile in db.items():
        logs = profile.get("logs", [])
        has_today_log = any(l.get("date") == today for l in logs)
        reminder_channel = profile.get("reminder_channel_id")
        if not has_today_log and reminder_channel:
            try:
                channel = await bot.fetch_channel(int(reminder_channel))
                user = await bot.fetch_user(int(user_id))
                await channel.send(
                    f"⏰ {user.mention} Pamiętaj o dziennym raporcie! Użyj `/fit raport`"
                )
            except Exception:
                pass


# ─── Bot events ───────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await tree.sync()
    if not daily_reminder.is_running():
        daily_reminder.start()
    print(f"✅ FitAI Bot uruchomiony jako {bot.user}")
    print(f"📁 Baza danych: {DATA_FILE.absolute()}")


bot.run(DISCORD_TOKEN)
