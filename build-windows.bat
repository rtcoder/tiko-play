@echo off
REM Aktywuj venv (jeśli masz)
REM call venv\Scripts\activate

REM Zainstaluj zależności
pip install -r requirements.txt

REM Buduj tiko-play.exe bez konsoli
pyinstaller tiko-play.spec

pause
