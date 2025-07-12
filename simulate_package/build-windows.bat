@echo off
REM Aktywuj venv (jeśli masz)
REM call venv\Scripts\activate

REM Zainstaluj zależności
pip install -r requirements.txt

REM Buduj simulate.exe bez konsoli
pyinstaller simulate.spec

pause
