#!/bin/bash
# Aktywuj venv (jeśli masz)
# source venv/bin/activate

# Zainstaluj zależności
pip install -r requirements.txt

# Buduj tiko-play (dostaniesz plik tiko-play w dist/)
pyinstaller tiko-play.spec
