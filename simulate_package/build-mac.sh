#!/bin/bash
# Aktywuj venv (jeśli masz)
# source venv/bin/activate

# Zainstaluj zależności
pip install -r requirements.txt

# Buduj simulate (dostaniesz plik simulate w dist/)
pyinstaller simulate.spec
