@echo off
TITLE FitAI v3.5 - Emergency Repair
chcp 65001 >nul

echo ======================================================
echo           FitAI - TRYB NAPRAWCZY v3.5
echo ======================================================
echo.

:: 1. Wymuszenie instalacji bibliotek (raz a dobrze)
echo [1/3] Instalowanie/Aktualizacja bibliotek...
python -m pip install groq google-generativeai fastapi uvicorn sqlmodel python-dotenv pyjwt cryptography slowapi

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ BŁĄD: Instalacja nie powiodła się. 
    echo Spróbuj uruchomić ten plik jako Administrator.
    pause
    exit /b
)

:: 2. Uruchamianie serwera
echo.
echo [2/3] Uruchamianie API...
:: Używamy 'start' bez /B, żeby otworzyło się w nowym oknie i było widać błędy
start "FitAI_Server" cmd /k "python -m uvicorn fitai_api:app --host 0.0.0.0 --port 8000"

echo ⏳ Czekam 5 sekund na start serwera...
timeout /t 5 >nul

:: 3. Otwieranie strony
echo [3/3] Otwieranie przeglądarki...
start index.html

echo.
echo ✅ Jeśli wszystko poszło dobrze, serwer działa w drugim oknie.
echo Jeśli tamto okno jest czerwone lub ma błędy - skopiuj je tutaj.
echo.
pause