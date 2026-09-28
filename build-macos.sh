#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != Darwin ]]; then echo 'Ten build wymaga macOS.' >&2; exit 1; fi
if [[ -z "${PYTHON_BUILD:-}" ]] && ! .venv/bin/python -c 'import sys' >/dev/null 2>&1; then python3 -m venv .venv; fi
build_python="${PYTHON_BUILD:-.venv/bin/python}"
"$build_python" -m pip install -r requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
version=$("$build_python" release_support.py)
"$build_python" -m PyInstaller --noconfirm packaging/macos.spec
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
ditto dist/TikoPlay.app "$staging/TikoPlay.app"
ln -s /Applications "$staging/Applications"
cp docs/INSTALL_MACOS.txt "$staging/INSTALACJA.txt"
image="dist/TikoPlay-${version}-macos-$(uname -m).dmg"
hdiutil create -volname TikoPlay -srcfolder "$staging" -ov -format UDZO "$image"
echo "Gotowe: dist/TikoPlay.app oraz $image (bez podpisu dystrybucyjnego)."
