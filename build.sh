#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
case "$(uname -s)" in
 Darwin) exec bash build-macos.sh ;;
 MINGW*|MSYS*) exec cmd.exe /c build-windows.bat ;;
 *) echo 'Paczki wydania sa przeznaczone dla Windows i macOS.' >&2; exit 1 ;;
esac
