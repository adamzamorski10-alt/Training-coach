@echo off
TITLE FitAI v3.0 Launcher
echo [FitAI] Zamykanie aktywnych procesow...
taskkill /IM uvicorn.exe /F 2>nul

echo [FitAI] Generowanie nowoczesnego interfejsu (v3.0)...
python generate_html_complete.py
if %ERRORLEVEL% NEQ 0 (
    echo [BŁĄD] Nie udalo sie wygenerowac index.html. Sprawdz bledy Pythona powyzej.
    pause
    exit /b
)

echo [FitAI] Uruchamianie backendu API (Port 8000)...
start /B uvicorn fitai_api:app --host 0.0.0.0 --port 8000

echo [FitAI] Otwieranie Dashboardu w przegladarce...
start index.html
echo [FitAI] System gotowy! API: http://localhost:8000. Jesli widzisz stare dane, uzyj Ctrl+F5 w przegladarce.