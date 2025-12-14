@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ===============================
echo   TikoPlay - Windows Build
echo ===============================

REM ---- Sprawdzenie Pythona ----
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python nie jest dostepny w PATH
    pause
    exit /b 1
)

REM ---- Virtualenv ----
if not exist venv (
    echo [INFO] Tworzenie virtualenv...
    python -m venv venv
)

echo [INFO] Aktywacja virtualenv
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo [ERROR] Nie mozna aktywowac virtualenv
    pause
    exit /b 1
)

REM ---- Instalacja zaleznosci ----
echo [INFO] Instalacja zaleznosci
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

if errorlevel 1 (
    echo [ERROR] Blad instalacji zaleznosci
    pause
    exit /b 1
)

REM ---- Czyszczenie poprzedniego builda ----
if exist build (
    echo [INFO] Usuwanie katalogu build
    rmdir /s /q build
)

if exist dist (
    echo [INFO] Usuwanie katalogu dist
    rmdir /s /q dist
)

REM ---- Build ----
echo [INFO] Budowanie aplikacji (PyInstaller)
pyinstaller build.spec

if errorlevel 1 (
    echo [ERROR] Build nieudany
    pause
    exit /b 1
)

REM ---- Sukces ----
echo.
echo ===============================
echo   BUILD ZAKONCZONY SUKCESEM
echo ===============================
echo.
echo Wynik znajduje sie w katalogu:
echo   dist\TikoPlay\
echo.

pause
