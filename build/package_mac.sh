#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="$ROOT_DIR/engine"
APP_BUNDLE="$ROOT_DIR/macapp/MarcliteMac/MarcliteMac.app"
BIN_DIR="$APP_BUNDLE/Contents/Resources/bin"

cd "$ENGINE_DIR"
python -m pip install --upgrade pyinstaller
pyinstaller --name marclite --onefile marclite/cli.py --distpath dist

mkdir -p "$BIN_DIR"
cp "$ENGINE_DIR/dist/marclite" "$BIN_DIR/marclite"
chmod +x "$BIN_DIR/marclite"

echo "Bundled marclite into $BIN_DIR"
