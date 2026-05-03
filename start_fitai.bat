@echo off
TITLE FitAI v3.0 - Professional Launcher
SETLOCAL EnableDelayedExpansion

:: Ustawienie kodowania znaków na UTF-8 (żeby polskie znaki w konsoli działały)
chcp 65001 >nul

echo ======================================================
echo           FitAI - SYSTEM STARTOWY v3.0
echo ======================================================
echo.

:: 1. Zamykanie starych procesów, aby uniknąć błędu "Port 8000 already in use"
echo [1/5] Porządkowanie procesów...
taskkill /IM uvicorn.exe /F 2>nul
echo ✅ Procesy uporządkowane.

:: 2. Sprawdzanie środowiska Python i bibliotek
echo [2/5] Sprawdzanie bibliotek systemowych...
python -m pip install --upgrade pip >nul
pip install fastapi uvicorn sqlmodel anthropic python-dotenv filelock >nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ BŁĄD: Nie udało się zainstalować wymaganych bibliotek. 
    echo Upewnij się, że masz połączenie z internetem.
    pause
    exit /b
)
echo ✅ Biblioteki są gotowe.

:: 3. Sprawdzanie i wdrożenie zmian z backendu
echo [3/5] Wdrażanie zmian z backendu...
:: Jeśli masz plik deploy_backend.py, uruchomimy go. Jeśli go nie ma - pominiemy bez błędu.
if exist deploy_backend.py (
    python deploy_backend.py
) else (
    echo ℹ️ Pominięto deploy_backend.py (plik nie istnieje).
)

:: 4. Uruchamianie Backend API (FastAPI)
echo [4/5] Uruchamianie serwera API na porcie 8000...
:: Sprawdzamy czy główny plik API istnieje
if not exist fitai_api.py (
    echo ❌ KRYTYCZNY BŁĄD: Nie znaleziono pliku fitai_api.py!
    pause
    exit /b
)

:: Startujemy serwer w tle. Plik fitai.db zostanie stworzony automatycznie przez skrypt python.
start /B uvicorn fitai_api:app --host 0.0.0.0 --port 8000 --log-level info
echo ✅ Serwer API wystartował w tle.

:: Czekamy chwilę, aż serwer się "rozgrzeje" przed otwarciem strony
timeout /t 3 /nobreak >nul

:: 5. Otwieranie interfejsu użytkownika
echo [5/5] Otwieranie panelu sterowania...
if exist index.html (
    start index.html
    echo ✅ Strona index.html została otwarta.
) else (
    echo ⚠️ OSTRZEŻENIE: Nie znaleziono pliku index.html w tym folderze.
)

echo.
echo ======================================================
echo       SYSTEM GOTOWY! MIŁEGO TRENINGU!
echo.
echo  * Twoje zmiany w index.html NIE zostaną usunięte.
echo  * Baza danych: fitai.db (zapisuje Twoje postępy)
echo  * Adres API: http://localhost:8000
echo ======================================================
echo.
echo Nie zamykaj tego okna, jeśli chcesz, aby backend działał.
echo Aby zakończyć, naciśnij Ctrl+C lub zamknij to okno.