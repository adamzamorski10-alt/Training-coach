"""
Fitness Calculations — Macros, progressive overload, XP, drill progression
"""

from sqlmodel import Session, select

from app.models import DrillResultDB, ExerciseResultDB, UserDB

# ─── Macros Calculations ──────────────────────────────────────────────────────


def calc_calories(p: dict | UserDB) -> int:
    """Mifflin-St Jeor + TDEE. Accepts both dict and ORM object."""
    if isinstance(p, UserDB):
        p = p.to_profile_dict()
    w, h, a = p.get("weight", 75), p.get("height", 175), p.get("age", 25)
    gender = str(p.get("gender", "")).lower()
    bmr = (
        10 * w
        + 6.25 * h
        - 5 * a
        + (-161 if "kobieta" in gender or "female" in gender else 5)
    )
    freq = str(p.get("frequency", "")).lower()
    for key, mult in [("codziennie", 1.9), ("5-6", 1.725), ("3-4", 1.55), ("1-2", 1.375)]:
        if key in freq:
            break
    else:
        mult = 1.2
    tdee = int(bmr * mult)
    goal = str(p.get("goal", "")).lower()
    # Rozpoznaj zarówno angielskie jak i polskie słowa
    if any(
        x in goal
        for x in ["redukcj", "odchudzani", "schud", "cut", "weight_loss", "fat_loss"]
    ):
        tdee -= 400
    elif any(
        x in goal
        for x in ["masa", "budow", "przyty", "bulk", "muscle", "gain", "build"]
    ):
        tdee += 300
    return tdee


def calc_protein(p: dict | UserDB) -> int:
    """
    Liczy zapotrzebowanie na białko na podstawie wagi, celu i DIETY.
    
    Bazowe (na podstawie goal):
    - buildmass/bulk: 2.0 g/kg
    - weight_loss/cut: 2.2 g/kg
    - default: 1.6 g/kg
    
    Modyfikatory diety (ale z limitem max 2.4 g/kg):
    - High-Protein: +0.2 g/kg (razem max 2.4 g/kg)
    - Low-Carb: +0.1 g/kg (razem max 2.2 g/kg)
    - Balanced/Standard/default: bez zmian
    - Low-Fat: bez zmian (białko jak baseline)
    """
    if isinstance(p, UserDB):
        p = p.to_profile_dict()

    w = p.get("weight", 75)
    goal = str(p.get("goal", "")).lower()
    diet = str(p.get("diet", "")).lower()

    # Ustaw baseline na podstawie goal
    if any(
        x in goal
        for x in ["masa", "budow", "przyty", "bulk", "muscle", "gain", "build"]
    ):
        base_protein_factor = 2.0  # Budowa masy: 2.0 g/kg
    elif any(
        x in goal
        for x in ["redukcj", "odchudzani", "schud", "cut", "weight_loss", "fat_loss"]
    ):
        base_protein_factor = 2.2  # Redukcja: 2.2 g/kg
    else:
        base_protein_factor = 1.6  # Default: 1.6 g/kg

    # Modyfikuj na podstawie diety (ale z rozsądnymi limitami)
    if any(
        x in diet for x in ["high.protein", "high_protein", "high-protein", "wysokobiałk", "high protein"]
    ):
        # High-Protein: +0.2 g/kg, ale max 2.4 g/kg (bezpieczny limit)
        protein_factor = min(base_protein_factor + 0.2, 2.4)
    elif any(
        x in diet for x in ["low.carb", "low_carb", "low-carb", "niskoglowodanow", "low carb"]
    ):
        # Low-Carb: +0.1 g/kg, ale max 2.3 g/kg (pozwala na +0.1 modyfikator)
        protein_factor = min(base_protein_factor + 0.1, 2.3)
    elif any(
        x in diet for x in ["low.fat", "low_fat", "low-fat", "niskotłuszczow", "low fat"]
    ):
        # Low-Fat: bez modyfikacji (standardowe białko)
        protein_factor = base_protein_factor
    else:
        # Balanced/Standard/inne: baseline bez zmian
        protein_factor = base_protein_factor

    return int(w * protein_factor)


# ─── Carb Cycling macros ──────────────────────────────────────────────────────

_HEAVY_MUSCLE_GROUPS = {"nogi", "plecy", "full body", "cardio"}
_REST_KEYWORDS = {"odpoczynek", "rest", "regeneracja"}

_DAY_TYPE_LABELS: dict[str, str] = {
    "heavy": "Dzień Wysokich Węglowodanów (Ciężki Trening)",
    "moderate": "Dzień Umiarkowany (Trening Ogólny)",
    "rest": "Dzień Odpoczynku / Niskich Węglowodanów",
}


def day_type(day_name: str, focus: str) -> str:
    """Returns 'heavy', 'moderate', or 'rest' for carb cycling logic."""
    lower = day_name.lower()
    if any(k in lower for k in _REST_KEYWORDS):
        return "rest"
    if focus in _HEAVY_MUSCLE_GROUPS:
        return "heavy"
    return "moderate"


def calc_daily_macros(base_calories: int, day_type_key: str) -> dict:
    """
    Carb Cycling:
      heavy  → +200 kcal, 50% carbs / 30% protein / 20% fat
      moderate → base, 40% / 30% / 30%
      rest   → -200 kcal, 20% carbs / 35% protein / 45% fat (higher fat)
    """
    adjustments = {"heavy": 200, "moderate": 0, "rest": -200}
    macros_pct = {
        "heavy": {"carbs": 0.50, "protein": 0.30, "fat": 0.20},
        "moderate": {"carbs": 0.40, "protein": 0.30, "fat": 0.30},
        "rest": {"carbs": 0.20, "protein": 0.35, "fat": 0.45},
    }
    kcal = base_calories + adjustments.get(day_type_key, 0)
    pct = macros_pct.get(day_type_key, macros_pct["moderate"])
    return {
        "kcal": kcal,
        "carbs_g": round(kcal * pct["carbs"] / 4),
        "protein_g": round(kcal * pct["protein"] / 4),
        "fat_g": round(kcal * pct["fat"] / 9),
        "day_type": day_type_key,
    }


def day_type_label(day_type_key: str) -> str:
    """Zwraca czytelną po polsku etykietę dla day_type w promptach AI."""
    return _DAY_TYPE_LABELS.get(day_type_key, day_type_key)


# ─── Progressive Overload / RPE helpers ───────────────────────────────────────

_RPE_LOW_THRESHOLD = 6  # ≤6 → too easy → increase load
_RPE_HIGH_THRESHOLD = 9  # ≥9 → too hard → decrease or keep
_WEIGHT_INCREMENT_KG = 2.5
_REPS_INCREMENT = 1


def suggest_progression(
    exercise_name: str,
    recent_results: list[ExerciseResultDB],
) -> dict:
    """
    Analyzes last 3 sessions for a given exercise and returns a progression suggestion.
    Returns: {"suggested_weight_kg": float, "suggested_reps": int, "reason": str}
    """
    if not recent_results:
        return {"suggested_weight_kg": None, "suggested_reps": None, "reason": "brak historii"}

    last = recent_results[0]
    avg_rpe = sum(r.rpe for r in recent_results[:3]) / min(len(recent_results), 3)

    if avg_rpe <= _RPE_LOW_THRESHOLD:
        # Zbyt łatwo – zwiększamy ciężar
        suggested_weight = round(last.weight_kg + _WEIGHT_INCREMENT_KG, 1)
        suggested_reps = last.reps
        reason = (
            f"Średnie RPE={avg_rpe:.1f} (≤{_RPE_LOW_THRESHOLD}) → "
            f"sugerowane +{_WEIGHT_INCREMENT_KG}kg"
        )
    elif avg_rpe >= _RPE_HIGH_THRESHOLD:
        # Na granicy możliwości – utrzymaj lub zredukuj, dodaj powtórzenie zamiast ciężaru
        suggested_weight = last.weight_kg
        suggested_reps = last.reps + _REPS_INCREMENT
        reason = (
            f"Średnie RPE={avg_rpe:.1f} (≥{_RPE_HIGH_THRESHOLD}) → "
            f"utrzymaj ciężar, dodaj powtórzenie"
        )
    else:
        # Dobry zakres RPE 7-8 – stopniowo zwiększaj powtórzenia
        suggested_weight = last.weight_kg
        suggested_reps = last.reps + _REPS_INCREMENT
        reason = (
            f"Średnie RPE={avg_rpe:.1f} (7-8) → "
            f"dodaj powtórzenie, ciężar bez zmiany"
        )

    return {
        "suggested_weight_kg": suggested_weight,
        "suggested_reps": suggested_reps,
        "reason": reason,
        "last_session": last.to_dict(),
        "sessions_analyzed": len(recent_results[:3]),
    }


# ─── XP / Leveling system ─────────────────────────────────────────────────────

_XP_THRESHOLDS = [i * 100 for i in range(20)]  # [0, 100, 200, 300, ..., 1900]

_XP_CHECKIN = 10
_XP_MEAL_LOGGED = 5
_XP_WEIGHT_LOGGED = 15
_XP_WORKOUT_LOGGED = 50
_XP_WATER_LOGGED = 5
_XP_STREAK_BONUS = 10


def _xp_to_level(total_xp: int) -> int:
    """Zwraca aktualny poziom na podstawie łącznych punktów XP."""
    level = 1
    for i, threshold in enumerate(_XP_THRESHOLDS):
        if total_xp >= threshold:
            level = i + 1
        else:
            break
    return min(level, len(_XP_THRESHOLDS))


def _xp_to_next_level(total_xp: int) -> dict:
    """Zwraca informacje o postępie do następnego poziomu."""
    level = _xp_to_level(total_xp)
    current_threshold = (
        _XP_THRESHOLDS[level - 1] if level <= len(_XP_THRESHOLDS) else _XP_THRESHOLDS[-1]
    )
    next_threshold = _XP_THRESHOLDS[level] if level < len(_XP_THRESHOLDS) else None
    if next_threshold is None:
        return {
            "level": level,
            "xp": total_xp,
            "next_level_xp": None,
            "progress_pct": 100,
        }
    xp_in_level = total_xp - current_threshold
    xp_needed = next_threshold - current_threshold
    return {
        "level": level,
        "xp": total_xp,
        "next_level_xp": next_threshold,
        "xp_in_level": xp_in_level,
        "xp_needed_for_next": xp_needed - xp_in_level,
        "progress_pct": round(xp_in_level / xp_needed * 100) if xp_needed > 0 else 100,
    }


def award_xp(user: UserDB, points: int, session: Session) -> int:
    """
    Dodaje punkty XP użytkownikowi i commituje zmianę.
    Zwraca nową sumę XP.
    """
    user.total_xp += points
    session.add(user)
    session.commit()
    return user.total_xp


# ─── Drill Progression ─────────────────────────────────────────────────────────

_DRILL_ACCURACY_HIGH = 0.70
_DRILL_RPE_LOW = 5
_DRILL_ATTEMPTS_INCREMENT = 5


def suggest_drill_progression(
    drill_name: str,
    recent_results: list[DrillResultDB],
) -> dict:
    """
    Analizuje historię drilli i sugeruje progresję.
    Zwraca: {suggested_attempts, reason, last_accuracy_pct, sessions_analyzed}
    """
    if not recent_results:
        return {
            "suggested_attempts": None,
            "reason": "brak historii – zacznij od bazowej liczby prób",
            "last_accuracy_pct": None,
            "sessions_analyzed": 0,
        }

    last = recent_results[0]
    analyzed = recent_results[:3]
    avg_accuracy = sum(
        (r.success_count / r.total_attempts) if r.total_attempts else 0 for r in analyzed
    ) / len(analyzed)
    avg_rpe = sum(r.rpe for r in analyzed) / len(analyzed)

    current_attempts = last.total_attempts

    if avg_accuracy >= _DRILL_ACCURACY_HIGH and avg_rpe <= _DRILL_RPE_LOW:
        suggested = current_attempts + _DRILL_ATTEMPTS_INCREMENT
        reason = (
            f"Skuteczność {avg_accuracy:.0%} przy RPE={avg_rpe:.1f} – wyraźnie za łatwe. "
            f"Zwiększ do {suggested} prób lub utrudnij warunki (bliższy obrońca, szybsze tempo)."
        )
    elif avg_accuracy >= _DRILL_ACCURACY_HIGH:
        suggested = current_attempts + _DRILL_ATTEMPTS_INCREMENT
        reason = (
            f"Skuteczność {avg_accuracy:.0%} (≥{_DRILL_ACCURACY_HIGH:.0%}) – dobry moment na progresję. "
            f"Sugerowane: {suggested} prób lub zmiana wariantu drilla."
        )
    else:
        suggested = current_attempts
        reason = (
            f"Skuteczność {avg_accuracy:.0%} – kontynuuj na {current_attempts} próbach "
            f"aż osiągniesz ≥{_DRILL_ACCURACY_HIGH:.0%} przez 2 sesje z rzędu."
        )

    return {
        "suggested_attempts": suggested,
        "reason": reason,
        "last_accuracy_pct": round(avg_accuracy * 100),
        "sessions_analyzed": len(analyzed),
    }
