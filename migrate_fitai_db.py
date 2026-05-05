"""
migrate_fitai_db.py
===================
Jednorazowy skrypt migracji bazy fitai.db.

Co robi:
  1. Tworzy backup bazy przed jakąkolwiek zmianą (fitai.db.bak_<timestamp>).
  2. Sprawdza, które kolumny już istnieją w tabeli `users`.
  3. Dodaje TYLKO brakujące kolumny za pomocą ALTER TABLE.
  4. Weryfikuje wynik i drukuje raport.

Kolumny docelowe:
  • xp_total  INTEGER  DEFAULT 0   — łączne punkty XP (alias/uzupełnienie total_xp)
  • level     INTEGER  DEFAULT 1   — poziom użytkownika (wyliczany z XP)

Uwaga o nazewnictwie:
  SQLModel w fitai_api.py używa pola `total_xp` (kolumna 38 w obecnej schemacie).
  Jeśli Twój model używa TYLKO `total_xp`, kolumna `xp_total` jest dodatkowa i może
  służyć jako przestrzeń robocza albo legacy alias — skrypt doda ją bezpiecznie.
  Jeśli chcesz zamiast tego tylko dodać `level`, ustaw ADD_XP_TOTAL = False poniżej.

Użycie:
  python migrate_fitai_db.py
  python migrate_fitai_db.py --db /inna/sciezka/fitai.db
  python migrate_fitai_db.py --dry-run   # tylko pokaz co by sie stalo
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# ─── Konfiguracja kolumn do dodania ──────────────────────────────────────────
# Każdy wpis: (nazwa_kolumny, typ_sql, wartość_domyślna_sql)
# Kolejność ma znaczenie — SQL wykona je po kolei.

COLUMNS_TO_ADD: list[tuple[str, str, str]] = [
    ("xp_total",  "INTEGER", "0"),
    ("level",     "INTEGER", "1"),
]

# Ustaw False, jeśli nie chcesz dodawać xp_total (bo model używa total_xp)
ADD_XP_TOTAL: bool = True

# ─────────────────────────────────────────────────────────────────────────────


def get_existing_columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    """Zwraca zbiór nazw istniejących kolumn w tabeli (małe litery)."""
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1].lower() for row in cursor.fetchall()}


def backup_database(db_path: Path) -> Path:
    """Tworzy kopię zapasową pliku bazy przed migracją."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".db.bak_{ts}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def run_migration(db_path: Path, dry_run: bool = False) -> None:
    print("=" * 60)
    print("  FitAI — Migracja bazy danych (ALTER TABLE)")
    print("=" * 60)
    print(f"  Baza:    {db_path.resolve()}")
    print(f"  Tryb:    {'DRY-RUN (bez zmian)' if dry_run else 'PRODUKCYJNY'}")
    print()

    # ── Walidacja ścieżki ─────────────────────────────────────────────────────
    if not db_path.exists():
        print(f"❌ BŁĄD: Plik bazy nie istnieje: {db_path}")
        sys.exit(1)

    # ── Backup ────────────────────────────────────────────────────────────────
    if not dry_run:
        backup = backup_database(db_path)
        print(f"✅ Backup utworzony: {backup.name}")
    else:
        print("ℹ️  Dry-run: backup pominięty.")
    print()

    # ── Połączenie z bazą ─────────────────────────────────────────────────────
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")   # bezpieczniejszy zapis
    cursor = conn.cursor()

    try:
        # ── Sprawdź istniejące kolumny ────────────────────────────────────────
        existing = get_existing_columns(cursor, "users")
        print(f"📋 Tabela `users` ma obecnie {len(existing)} kolumn.")
        print()

        # ── Filtruj listę do tych, które faktycznie trzeba dodać ──────────────
        to_add = [
            (col, typ, default)
            for col, typ, default in COLUMNS_TO_ADD
            if (col != "xp_total" or ADD_XP_TOTAL)   # respektuj flagę xp_total
            and col.lower() not in existing
        ]

        already_present = [
            col for col, _, _ in COLUMNS_TO_ADD
            if col.lower() in existing
        ]

        # ── Raport kolumn już istniejących ────────────────────────────────────
        if already_present:
            for col in already_present:
                print(f"  ⏭️  `{col}` — już istnieje, pomijam.")

        if not to_add:
            print()
            print("✅ Wszystkie kolumny już istnieją. Migracja nie jest potrzebna.")
            return

        print()
        print(f"➕ Kolumny do dodania: {[c for c,_,_ in to_add]}")
        print()

        # ── Wykonaj ALTER TABLE ───────────────────────────────────────────────
        results: list[dict] = []

        for col_name, col_type, col_default in to_add:
            sql = (
                f"ALTER TABLE users "
                f"ADD COLUMN {col_name} {col_type} DEFAULT {col_default}"
            )
            print(f"  ▶ SQL: {sql}")

            if dry_run:
                print(f"    [DRY-RUN] Pominięto wykonanie.")
                results.append({"col": col_name, "status": "dry-run"})
                continue

            try:
                cursor.execute(sql)
                results.append({"col": col_name, "status": "dodano ✅"})
                print(f"    ✅ Sukces.")
            except sqlite3.OperationalError as exc:
                # Kolumna mogła pojawić się między sprawdzeniem a wykonaniem
                if "duplicate column name" in str(exc).lower():
                    results.append({"col": col_name, "status": "już istnieje (race) ⚠️"})
                    print(f"    ⚠️  Kolumna już istnieje (concurrent write?): {exc}")
                else:
                    results.append({"col": col_name, "status": f"błąd ❌: {exc}"})
                    print(f"    ❌ Nieoczekiwany błąd OperationalError: {exc}")
                    # Nie przerywaj — spróbuj pozostałe kolumny
            except Exception as exc:
                results.append({"col": col_name, "status": f"błąd ❌: {exc}"})
                print(f"    ❌ Błąd: {type(exc).__name__}: {exc}")

        # ── Commit ────────────────────────────────────────────────────────────
        if not dry_run:
            conn.commit()
            print()
            print("💾 Zmiany zatwierdzone (COMMIT).")

        # ── Weryfikacja po migracji ───────────────────────────────────────────
        print()
        print("─" * 60)
        print("  Weryfikacja po migracji:")
        print("─" * 60)
        updated_cols = get_existing_columns(cursor, "users")
        for col, _, default in COLUMNS_TO_ADD:
            present = col.lower() in updated_cols
            marker = "✅" if present else ("⏭️ (pominięto — dry-run)" if dry_run else "❌ BRAK!")
            print(f"  {marker}  {col} (DEFAULT {default})")

        # ── Podsumowanie ──────────────────────────────────────────────────────
        print()
        print("─" * 60)
        print("  Podsumowanie:")
        print("─" * 60)
        for r in results:
            print(f"  {r['col']:20s}  →  {r['status']}")

        print()
        if dry_run:
            print("ℹ️  Dry-run zakończony. Uruchom bez --dry-run, aby zastosować zmiany.")
        else:
            print("🎉 Migracja zakończona pomyślnie.")
            print()
            print("  Następne kroki:")
            print("  1. Zrestartuj serwer FitAI (uvicorn fitai_api:app ...)")
            print("  2. SQLModel automatycznie użyje nowych kolumn przy starcie.")
            print("  3. Istniejące wiersze mają wartości DEFAULT (xp_total=0, level=1).")

    finally:
        conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migracja fitai.db — bezpieczne dodawanie kolumn ALTER TABLE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db",
        default="fitai.db",
        help="Ścieżka do pliku bazy SQLite (domyślnie: fitai.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pokaż co zostałoby zrobione, bez faktycznych zmian w bazie",
    )
    args = parser.parse_args()

    run_migration(Path(args.db), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
