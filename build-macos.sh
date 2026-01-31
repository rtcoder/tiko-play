#!/bin/bash
set -e

echo "==============================="
echo "  TikoPlay - macOS Build"
echo "==============================="

# ---- Python check ----
if ! command -v python3 &> /dev/null; then
  echo "[ERROR] python3 nie jest dostepny"
  exit 1
fi

# ---- Virtualenv ----
if [ ! -d "venv" ]; then
  echo "[INFO] Tworzenie virtualenv"
  python3 -m venv venv
fi

echo "[INFO] Aktywacja virtualenv"
source venv/bin/activate

# ---- Zaleznosci ----
echo "[INFO] Instalacja zaleznosci"
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# ---- Czyszczenie ----
echo "[INFO] Czyszczenie poprzednich buildow"
rm -rf build dist

# ---- Build APP ----
echo "[INFO] Budowanie aplikacji (.app)"
pyinstaller build.spec

APP_PATH="dist/TikoPlay.app"
if [ ! -d "$APP_PATH" ]; then
  echo "[ERROR] Nie znaleziono TikoPlay.app"
  exit 1
fi

# ---- Usuniecie quarantine (lokalnie) ----
echo "[INFO] Usuwanie atrybutu quarantine"
xattr -rd com.apple.quarantine "$APP_PATH" || true

# ---- Tworzenie DMG ----
echo "[INFO] Tworzenie DMG"

DMG_NAME="TikoPlay.dmg"
TMP_DMG="TikoPlay-temp.dmg"

hdiutil create "$TMP_DMG" \
  -volname "TikoPlay" \
  -srcfolder "$APP_PATH" \
  -ov -format UDZO

mv "$TMP_DMG" "$DMG_NAME"

echo
echo "==============================="
echo "  BUILD ZAKONCZONY SUKCESEM"
echo "==============================="
echo
echo "Wynik:"
echo "  dist/TikoPlay.app"
echo "  TikoPlay.dmg"
echo
