"""
test_exercise_descriptions.py
Testy jednostkowe dla modułu app/exercise_descriptions.py.

Pokrycie:
  (a) znane ćwiczenie ma niepusty how_to
  (b) nieznane ćwiczenie zwraca pusty string ""
  (c) fallback substring działa (np. "Pull-up po jednym kozie" → klucz "pull-up")
  (d) drille – analogiczne trzy przypadki
  (e) wielkość liter nie ma znaczenia (case-insensitive)
"""

import sys
import os

# Dodaj katalog projektu do ścieżki, żeby testy działały bez instalacji pakietu
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pytest

from app.exercise_descriptions import (
    EXERCISE_HOW_TO,
    DRILL_HOW_TO,
    get_how_to,
)


# ---------------------------------------------------------------------------
# Testy EXERCISE_HOW_TO
# ---------------------------------------------------------------------------

class TestExerciseHowTo:
    """Testy dla słownika ćwiczeń siłowych."""

    def test_known_exercise_returns_nonempty_string(self):
        """(a) Znane ćwiczenie ma niepusty how_to."""
        result = get_how_to("martwy ciąg konwencjonalny")
        assert isinstance(result, str)
        assert len(result) > 0, "how_to nie może być pustym stringiem dla znanych ćwiczeń"

    def test_known_exercise_case_insensitive(self):
        """(a) Wyszukiwanie działa niezależnie od wielkości liter."""
        lower = get_how_to("martwy ciąg konwencjonalny")
        upper = get_how_to("Martwy Ciąg Konwencjonalny")
        mixed = get_how_to("MARTWY CIĄG KONWENCJONALNY")
        assert lower == upper == mixed
        assert len(lower) > 0

    def test_unknown_exercise_returns_empty_string(self):
        """(b) Nieznane ćwiczenie zwraca dokładnie pusty string, nie None."""
        result = get_how_to("ćwiczenie_którego_nie_ma_w_słowniku_xyz_999")
        assert result == "", f"Oczekiwano '', otrzymano: {result!r}"

    def test_unknown_exercise_is_not_none(self):
        """(b) Zwracana wartość dla nieznanego ćwiczenia to str, nie None."""
        result = get_how_to("nieistniejące_ćwiczenie")
        assert result is not None
        assert isinstance(result, str)

    def test_substring_fallback_pull_up(self):
        """(c) 'Pull-up po jednym kozie' → klucz 'pull-up' (substring fallback)."""
        result = get_how_to("Pull-up po jednym kozie")
        assert len(result) > 0, (
            "Fallback substring powinien znaleźć opis dla 'pull-up' "
            "w nazwie 'Pull-up po jednym kozie'"
        )

    def test_substring_fallback_plank_variant(self):
        """(c) 'Side plank 30 sekund' → klucz 'plank' (substring fallback)."""
        result = get_how_to("Side plank 30 sekund")
        assert len(result) > 0, "Fallback powinien dopasować 'plank' w nazwie"

    def test_substring_fallback_deadlift_variant(self):
        """(c) 'Martwy ciąg sumo z ketlebellem' → klucz 'martwy ciąg'."""
        result = get_how_to("Martwy ciąg sumo z ketlebellem")
        assert len(result) > 0, "Fallback powinien dopasować 'martwy ciąg' w nazwie"

    def test_substring_fallback_does_not_match_random_word(self):
        """(c) Losowe słowo bez dopasowania wciąż zwraca ''."""
        result = get_how_to("zupełnie_obca_nazwa_której_nie_ma_nigdzie")
        assert result == ""

    def test_exact_match_preferred_over_substring(self):
        """Exact match powinien być zwrócony (nie substring innego klucza)."""
        exact = get_how_to("plank")
        assert exact == EXERCISE_HOW_TO["plank"]

    def test_all_dict_values_are_nonempty_strings(self):
        """Wszystkie wpisy w EXERCISE_HOW_TO są niepustymi stringami."""
        for key, value in EXERCISE_HOW_TO.items():
            assert isinstance(value, str), f"Wartość dla klucza '{key}' nie jest stringiem"
            assert len(value.strip()) > 0, f"Wartość dla klucza '{key}' jest pusta"

    def test_all_dict_keys_are_lowercase(self):
        """Wszystkie klucze w EXERCISE_HOW_TO są lowercase (wymaganie lookup)."""
        for key in EXERCISE_HOW_TO:
            assert key == key.lower(), f"Klucz '{key}' nie jest lowercase"

    @pytest.mark.parametrize("name", [
        "martwy ciąg konwencjonalny",
        "przysiad ze sztangą",
        "wyciskanie sztangi na ławce płaskiej",
        "podciąganie nachwytem",
        "plank",
        "burpees",
        "kettlebell swing",
        "arnold press",
    ])
    def test_core_exercises_have_descriptions(self, name):
        """Podstawowe ćwiczenia mają opisy."""
        result = get_how_to(name)
        assert len(result) > 0, f"Brak opisu dla ćwiczenia: '{name}'"


# ---------------------------------------------------------------------------
# Testy DRILL_HOW_TO
# ---------------------------------------------------------------------------

class TestDrillHowTo:
    """Testy dla słownika drilli sportowych."""

    def test_known_drill_returns_nonempty_string(self):
        """(a) Znany drill ma niepusty how_to."""
        result = get_how_to("rzuty osobiste", is_drill=True)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_known_drill_case_insensitive(self):
        """(a) Case-insensitive dla drilli."""
        lower = get_how_to("rzuty osobiste", is_drill=True)
        upper = get_how_to("Rzuty Osobiste", is_drill=True)
        assert lower == upper
        assert len(lower) > 0

    def test_unknown_drill_returns_empty_string(self):
        """(b) Nieznany drill zwraca dokładnie ''."""
        result = get_how_to("nieznany_drill_xyz_999", is_drill=True)
        assert result == ""

    def test_unknown_drill_is_not_none(self):
        """(b) Zwracana wartość dla nieznanego drilla to str, nie None."""
        result = get_how_to("nieistniejący_drill", is_drill=True)
        assert result is not None
        assert isinstance(result, str)

    def test_substring_fallback_drill(self):
        """(c) 'Mikan Drill – wersja Power' → klucz 'mikan drill' (substring fallback)."""
        result = get_how_to("Mikan Drill – wersja Power", is_drill=True)
        assert len(result) > 0, "Fallback powinien dopasować 'mikan drill'"

    def test_substring_fallback_defensive_slides(self):
        """(c) 'Defensive Slides (wersja z piłką)' → klucz 'defensive slides'."""
        result = get_how_to("Defensive Slides (wersja z piłką)", is_drill=True)
        assert len(result) > 0

    def test_drill_lookup_does_not_bleed_into_exercise_dict(self):
        """Drill lookup nie zwraca wyników z EXERCISE_HOW_TO."""
        # 'martwy ciąg' jest w EXERCISE_HOW_TO, nie w DRILL_HOW_TO
        result = get_how_to("martwy ciąg konwencjonalny", is_drill=True)
        assert result == "", "Wyszukiwanie drilla nie powinno sięgać do słownika ćwiczeń"

    def test_exercise_lookup_does_not_bleed_into_drill_dict(self):
        """Exercise lookup nie zwraca wyników z DRILL_HOW_TO."""
        # 'rzuty osobiste' jest w DRILL_HOW_TO, nie w EXERCISE_HOW_TO
        result = get_how_to("rzuty osobiste", is_drill=False)
        assert result == "", "Wyszukiwanie ćwiczenia nie powinno sięgać do słownika drilli"

    def test_all_drill_dict_values_are_nonempty_strings(self):
        """Wszystkie wpisy w DRILL_HOW_TO są niepustymi stringami."""
        for key, value in DRILL_HOW_TO.items():
            assert isinstance(value, str), f"Wartość dla klucza '{key}' nie jest stringiem"
            assert len(value.strip()) > 0, f"Wartość dla klucza '{key}' jest pusta"

    def test_all_drill_dict_keys_are_lowercase(self):
        """Wszystkie klucze w DRILL_HOW_TO są lowercase."""
        for key in DRILL_HOW_TO:
            assert key == key.lower(), f"Klucz drilla '{key}' nie jest lowercase"

    @pytest.mark.parametrize("drill_name", [
        "rzuty osobiste",
        "rzuty za 3 punkty",
        "mikan drill",
        "figure-8 dribbling",
        "defensive slides",
    ])
    def test_basketball_drills_have_descriptions(self, drill_name):
        """Podstawowe drille koszykarskie mają opisy."""
        result = get_how_to(drill_name, is_drill=True)
        assert len(result) > 0, f"Brak opisu dla drilla: '{drill_name}'"


# ---------------------------------------------------------------------------
# Testy edge-case / graniczne
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Testy brzegowe dla get_how_to."""

    def test_empty_string_returns_empty(self):
        """Pusta nazwa zwraca ''."""
        assert get_how_to("") == ""
        assert get_how_to("", is_drill=True) == ""

    def test_whitespace_only_returns_empty(self):
        """Sama spacja/tab zwraca ''."""
        assert get_how_to("   ") == ""

    def test_leading_trailing_whitespace_stripped(self):
        """Wiodące/kończące spacje są usuwane przed wyszukiwaniem."""
        result_stripped = get_how_to("martwy ciąg konwencjonalny")
        result_spaces   = get_how_to("  martwy ciąg konwencjonalny  ")
        assert result_stripped == result_spaces
        assert len(result_stripped) > 0

    def test_return_type_is_always_str(self):
        """get_how_to zawsze zwraca str, nigdy None."""
        cases = [
            ("znane ćwiczenie: martwy ciąg konwencjonalny", False),
            ("zupełnie nieznane", False),
            ("rzuty osobiste", True),
            ("zupełnie nieznany drill", True),
        ]
        for name, is_drill in cases:
            result = get_how_to(name, is_drill=is_drill)
            assert isinstance(result, str), (
                f"get_how_to('{name}', is_drill={is_drill}) zwróciło {type(result)}, a nie str"
            )


# ---------------------------------------------------------------------------
# Uruchomienie bezpośrednie
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
