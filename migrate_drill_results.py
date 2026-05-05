"""
migrate_drill_results.py
========================
Migracja tabeli `drill_results` w fitai.db — dodanie kolumn cardio/skills.

Co robi:
  1. Tworzy backup bazy przed jakąkolwiek zmianą (fitai.db.bak_<timestamp>).
  2. Sprawdza, które kolumny już istnieją w tabeli `drill_results`.
  3. Dodaje TYLKO brakujące kolumny za pomocą ALTER TABLE.
  4. Weryfikuje wynik i drukuje raport.

Kolumny docelowe (zgodne z modelem DrillResultDB w fitai_api.py):
  • time_seconds      REAL     nullable  — czas w sekundach (Bieg/Sprint)
  • distance_meters   REAL     nullable  — dystans w metrach (Bieg/Sprint)
  • duration_seconds  INTEGER  nullable  — czas trwania ćwiczenia/meczu [s]
  • weight_kg         REAL     nullable  — obciążenie [kg] (np. weighted drill)

Kompatybilność wsteczna:
  Wszystkie kolumny są NULL-able bez wartości domyślnej, więc istniejące
  rekordy (np. rzuty z success_count/total_attempts) pozostają niezmienione
  — pola cardio będą po prostu NULL dla starych wyników.

Użycie:
  python migrate_drill_results.py
  python migrate_drill_results.py --db /inna/sciezka/fitai.db
  python migrate_drill_results.py --dry-run   # tylko pokaż co by się stało
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# ─── Kolumny do dodania ───────────────────────────────────────────────────────
# Format: (nazwa_kolumny, typ_sql, czy_nullable)
# Wszystkie nullable → istniejące rekordy nie są naruszane.

COLUMNS_TO_ADD: list[tuple[str, str]] = [
    ("time_seconds",     "REAL"),       # czas w sekundach (Bieg/Sprint)
    ("distance_meters",  "REAL"),       # dystans w metrach (Bieg/Sprint)
    ("duration_seconds", "INTEGER"),    # czas trwania ćwiczenia [s]
    ("weight_kg",        "REAL"),       # obciążenie [kg]
]

TABLE_NAME = "drill_results"


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


# ─── Migracja ─────────────────────────────────────────────────────────────────

def run_migration(db_path: Path, dry_run: bool = False) -> None:
    print("=" * 60)
    print("  FitAI — Migracja drill_results (cardio/skills)")
    print("=" * 60)
    print(f"  Baza:    {db_path.resolve()}")
    print(f"  Tabela:  {TABLE_NAME}")
    print(f"  Tryb:    {'DRY-RUN (bez zmian)' if dry_run else 'PRODUKCYJNY'}")
    print()

    if not db_path.exists():
        print(f"❌ BŁĄD: Plik bazy nie istnieje: {db_path}")
        sys.exit(1)

    # Backup
    if not dry_run:
        backup = backup_database(db_path)
        print(f"✅ Backup utworzony: {backup.name}")
    else:
        print("ℹ️  Dry-run: backup pominięty.")
    print()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    try:
        existing = get_existing_columns(cursor, TABLE_NAME)
        print(f"📋 Tabela `{TABLE_NAME}` ma obecnie {len(existing)} kolumn:")
        for col in sorted(existing):
            print(f"     ✓ {col}")
        print()

        # Filtruj: tylko kolumny których naprawdę brakuje
        to_add = [(col, typ) for col, typ in COLUMNS_TO_ADD if col.lower() not in existing]
        already = [col for col, _ in COLUMNS_TO_ADD if col.lower() in existing]

        if already:
            print("  Kolumny już istniejące (pomijam):")
            for col in already:
                print(f"     ⏭️  {col}")
            print()

        if not to_add:
            print("✅ Wszystkie kolumny cardio już istnieją. Migracja nie jest potrzebna.")
            return

        print(f"➕ Do dodania ({len(to_add)} kolumn):")
        for col, typ in to_add:
            print(f"     + {col}  {typ}  NULL")
        print()

        results: list[dict] = []

        for col_name, col_type in to_add:
            # NULL-able → bez DEFAULT, brak wartości = None dla starych rekordów
            sql = f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col_name} {col_type}"
            print(f"  ▶ {sql}")

            if dry_run:
                print(f"    [DRY-RUN] Pominięto.")
                results.append({"col": col_name, "status": "dry-run"})
                continue

            try:
                cursor.execute(sql)
                results.append({"col": col_name, "status": "dodano ✅"})
                print(f"    ✅ Sukces.")
            except sqlite3.OperationalError as exc:
                if "duplicate column name" in str(exc).lower():
                    results.append({"col": col_name, "status": "już istnieje (race) ⚠️"})
                    print(f"    ⚠️  Kolumna już istnieje: {exc}")
                else:
                    results.append({"col": col_name, "status": f"błąd ❌: {exc}"})
                    print(f"    ❌ Błąd: {exc}")
            except Exception as exc:
                results.append({"col": col_name, "status": f"błąd ❌: {exc}"})
                print(f"    ❌ {type(exc).__name__}: {exc}")

        if not dry_run:
            conn.commit()
            print()
            print("💾 Zmiany zatwierdzone (COMMIT).")

        # Weryfikacja
        print()
        print("─" * 60)
        print("  Weryfikacja po migracji:")
        print("─" * 60)
        updated = get_existing_columns(cursor, TABLE_NAME)
        for col, typ in COLUMNS_TO_ADD:
            present = col.lower() in updated
            if dry_run and not present:
                marker = "⏭️  (dry-run — nie dodano)"
            else:
                marker = "✅" if present else "❌ BRAK!"
            print(f"  {marker}  {col}  ({typ}  NULL)")

        # Podsumowanie
        print()
        print("─" * 60)
        print("  Podsumowanie:")
        print("─" * 60)
        for r in results:
            print(f"  {r['col']:22s}  →  {r['status']}")
        print()

        if dry_run:
            print("ℹ️  Dry-run zakończony. Uruchom bez --dry-run, aby zastosować zmiany.")
        else:
            print("🎉 Migracja zakończona pomyślnie!")
            print()
            print("  Następne kroki:")
            print("  1. Zrestartuj serwer: uvicorn fitai_api:app --reload --port 8000")
            print("  2. SQLModel automatycznie użyje nowych kolumn.")
            print("  3. Stare rekordy (rzuty) mają NULL w polach cardio — kompatybilność zachowana.")
            print("  4. Nowe wyniki cardio możesz wysyłać przez POST /app/drill-result")
            print("     z polami: time_seconds, distance_meters, duration_seconds, weight_kg")

    finally:
        conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migracja drill_results — dodanie kolumn cardio/skills",
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
