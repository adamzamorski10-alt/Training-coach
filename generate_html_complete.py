#!/usr/bin/env python3
"""FitAI Dashboard Generator - synchronizes the source HTML into app/index.html."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Source-of-truth defaults to root index.html, output defaults to app/index.html.
    src = Path(os.getenv("FITAI_HTML_SOURCE", "index.html")).resolve()
    dst = Path(os.getenv("FITAI_HTML_OUTPUT", "app/index.html")).resolve()

    if not src.exists():
        print(f"❌ {src.name} nie istnieje")
        return 1

    targets = [dst]
    if dst.name == "index.html":
        alt = dst.with_name("index_new.html")
        if alt.exists():
            targets.append(alt)

    if src != dst:
        dst.parent.mkdir(parents=True, exist_ok=True)
        for target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
    else:
        # Keep behavior deterministic even when source and output are the same path.
        _ = src.read_text(encoding="utf-8")

    size_kb = dst.stat().st_size // 1024
    print(f"✅ generate_html_complete.py: {dst.name} is up to date ({size_kb}KB)")
    print(f"📄 {dst.name}: {size_kb}KB")

    html = dst.read_text(encoding="utf-8")
    required_markers = [
        "todayPrSection",
        "dayTimelinePanel",
        "toggleDayTimeline",
        "openDrillLogWizard",
        "drillWizardModal",
        "exerciseHowToPanel",
        "exerciseDetailModal",
        "openExerciseDetailModal",
        "discordConnectSection",
        "reminderTimeInput",
    ]
    missing = [marker for marker in required_markers if marker not in html]
    if missing:
        print(f"⚠️ Brak sekcji UI: {', '.join(missing)}")
    else:
        print("✅ Sekcje Mój Dzień i Sport: PR + oś czasu + drill modal obecne")

    discord_markers = ["discordConnectSection", "reminderTimeInput", "ptab-discord", "discordConnectCode"]
    missing_discord = [m for m in discord_markers if m not in html]
    if missing_discord:
        print(f"⚠️ Brak sekcji Discord: {', '.join(missing_discord)}")
    else:
        print("✅ Sekcja Discord Przypomnienia: wszystkie markery obecne")

    if size_kb < 200:
        print("⚠️ OSTRZEŻENIE: plik jest bardzo mały - sprawdź czy bazy danych są dołączone")
    else:
        print("✅ Rozmiar pliku OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())