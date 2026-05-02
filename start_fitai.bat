@echo off
TITLE FitAI v3.0 - Safe Launcher
echo [FitAI] Zamykanie aktywnych procesow backendu...
taskkill /IM uvicorn.exe /F 2>nul

echo [FitAI] Wdraczanie zmian z backendu...
python deploy_backend.py
if %ERRORLEVEL% NEQ 0 (
    echo [BLAD] Wystapil problem z wdrozeniem zmian. Sprawdz bledy Pythona.
    pause
    exit /b
)

echo [FitAI] Uruchamianie API (Port 8000)...
start /B uvicorn fitai_api:app --host 0.0.0.0 --port 8000

echo [FitAI] Otwieranie strony w przegladarce...
start index.html

echo.
echo ======================================================
echo SYSTEM GOTOWY!
echo Twoje zmiany w index.html sa teraz BEZPIECZNE.
echo Backend API dziala na: http://localhost:8000
echo ======================================================