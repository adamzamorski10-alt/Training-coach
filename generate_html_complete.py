#!/usr/bin/env python3
"""FitAI Dashboard Generator - synchronizes the source HTML into app/index.html."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def main() -> int:
    # Source-of-truth defaults to root index.html, output defaults to app/index.html.
    src = Path(os.getenv("FITAI_HTML_SOURCE", "index.html")).resolve()
    dst = Path(os.getenv("FITAI_HTML_OUTPUT", "app/index.html")).resolve()

    if not src.exists():
        print(f"❌ {src.name} nie istnieje")
        return 1

    if src != dst:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    else:
        # Keep behavior deterministic even when source and output are the same path.
        _ = src.read_text(encoding="utf-8")

    size_kb = dst.stat().st_size // 1024
    print(f"✅ generate_html_complete.py: {dst.name} is up to date ({size_kb}KB)")
    print(f"📄 {dst.name}: {size_kb}KB")

    if size_kb < 200:
        print("⚠️ OSTRZEŻENIE: plik jest bardzo mały - sprawdź czy bazy danych są dołączone")
    else:
        print("✅ Rozmiar pliku OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
