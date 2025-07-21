@echo off
rem ---------------------------------------------------------------------------
rem Build script for tiko‑play on Windows
rem 1. Create .venv with Python 3.11 only if it does not yet exist
rem 2. Activate the venv
rem 3. Install requirements
rem 4. Run PyInstaller to produce tiko‑play.exe (windowless, per tiko‑play.spec)
rem ---------------------------------------------------------------------------

:: 0) Pick the Python 3.11 command once
set "PY_CMD=python3.11"

%PY_CMD% -V >nul 2>&1 || (
    echo [ERROR] Python 3.11 not found. Install it or change python command in PY_CMD.
    exit /b 1
)

:: 1) Create venv only when missing
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment .venv with Python 3.11 ...
    %PY_CMD% -m venv .venv
)

:: 2) Activate venv (call ensures the batch continues in the same shell)
call ".venv\Scripts\activate.bat"

:: 3) Install/upgrade dependencies inside the venv
python -m pip install --upgrade pip wheel
pip install -r requirements.txt

:: 4) Build the executable
pyinstaller tiko-play.spec
