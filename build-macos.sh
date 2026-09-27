#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != Darwin ]]; then echo 'Ten build wymaga macOS.' >&2; exit 1; fi
if ! .venv/bin/python -c 'import sys' >/dev/null 2>&1; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m PyInstaller --noconfirm packaging/macos.spec
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
ditto dist/TikoPlay.app "$staging/TikoPlay.app"
ln -s /Applications "$staging/Applications"
cp docs/INSTALL_MACOS.txt "$staging/INSTALACJA.txt"
hdiutil create -volname TikoPlay -srcfolder "$staging" -ov -format UDZO dist/TikoPlay-2.0.0-test.dmg
echo 'Gotowe: dist/TikoPlay.app oraz dist/TikoPlay-2.0.0-test.dmg (paczka testowa bez podpisu dystrybucyjnego).'
