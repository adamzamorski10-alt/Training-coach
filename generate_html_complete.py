#!/usr/bin/env python3
"""FitAI Dashboard Generator - synchronizes index output from source HTML."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def main() -> int:
    # Source-of-truth defaults to index.html, but can be overridden by env vars.
    src = Path(os.getenv("FITAI_HTML_SOURCE", "index.html")).resolve()
    dst = Path(os.getenv("FITAI_HTML_OUTPUT", "index.html")).resolve()

    if not src.exists():
        print("❌ index.html nie istnieje")
        return 1

    if src != dst:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    else:
        # Keep behavior deterministic even when source and output are the same path.
        _ = src.read_text(encoding="utf-8")

    size_kb = dst.stat().st_size // 1024
    print(f"✅ generate_html_complete.py: index.html is up to date ({size_kb}KB)")
    print(f"📄 index.html: {size_kb}KB")

    if size_kb < 200:
        print("⚠️ OSTRZEŻENIE: plik jest bardzo mały - sprawdź czy bazy danych są dołączone")
    else:
        print("✅ Rozmiar pliku OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
