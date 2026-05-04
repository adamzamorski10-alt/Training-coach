@echo off
TITLE FitAI v3.3 - Stable Launcher
SETLOCAL EnableDelayedExpansion

:: Ustawienie kodowania znaków na UTF-8
chcp 65001 >nul

echo ======================================================
echo           FitAI - SYSTEM STARTOWY v3.3
echo ======================================================
echo.

:: 1. Zamykanie starych procesów
echo [1/4] Porządkowanie procesów...
taskkill /IM uvicorn.exe /F 2>nul
echo ✅ Gotowe.

:: 2. Wdrażanie zmian backendowych (jeśli plik istnieje)
echo [2/4] Wdrażanie zmian...
if exist deploy_backend.py (
    python deploy_backend.py
) else (
    echo ℹ️ Pominięto deploy_backend.py.
)

:: 3. Uruchamianie serwera API
echo [3/4] Uruchamianie serwera API...
if not exist fitai_api.py (
    echo ❌ BŁĄD: Nie znaleziono pliku fitai_api.py!
    pause
    exit /b
)

:: Uruchamiamy serwer w nowym, osobnym oknie, żebyś widział błędy jeśli wystąpią
echo 🚀 Startuję uvicorn...
start "FitAI API Server" cmd /k "python -m uvicorn fitai_api:app --host 0.0.0.0 --port 8000"

:: Czekamy 5 sekund na start bazy danych
echo ⏳ Czekam na utworzenie bazy danych...
timeout /t 5 /nobreak >nul

:: Sprawdzenie czy baza powstała
if exist fitai.db (
    echo ✅ Baza danych fitai.db została znaleziona/utworzona.
) else (
    echo ⚠️ Uwaga: Plik fitai.db jeszcze się nie pojawił. Sprawdź drugie okno konsoli.
)

:: 4. Otwieranie strony WWW
echo [4/4] Otwieranie panelu sterowania...
if exist index.html (
    start index.html
    echo ✅ Aplikacja otwarta w przeglądarce.
)

echo.
echo ======================================================
echo System wystartował. Nie zamykaj okna "FitAI API Server"!
echo ======================================================
pause