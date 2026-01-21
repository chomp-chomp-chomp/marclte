#!/usr/bin/env bash
# Simplified build script for MarcliteMac (no code signing)
set -euo pipefail

# Directories
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="$ROOT_DIR/engine"
XCODE_PROJECT="$ROOT_DIR/macapp/MarcliteMac/MarcliteMac.xcodeproj"
BUILD_DIR="$ROOT_DIR/build/output"

APP_NAME="MarcliteMac"
DMG_NAME="MarcliteMac-Installer"

echo "=========================================="
echo "Building MarcliteMac (Simple Method)"
echo "=========================================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script must be run on macOS"
    exit 1
fi

# Clean and create build directory
echo -e "\n1. Cleaning build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build Python CLI
echo -e "\n2. Building Python CLI..."
cd "$ENGINE_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip wheel pyinstaller
pip install -e .

pyinstaller --name marclite \
    --onefile \
    -m marclite.cli \
    --distpath "$BUILD_DIR/cli" \
    --clean

echo "✓ CLI built: $BUILD_DIR/cli/marclite"

# Build Mac app
echo -e "\n3. Building Mac app with xcodebuild..."
xcodebuild -project "$XCODE_PROJECT" \
    -scheme "$APP_NAME" \
    -configuration Release \
    -derivedDataPath "$BUILD_DIR/DerivedData" \
    CODE_SIGN_IDENTITY="" \
    CODE_SIGNING_REQUIRED=NO \
    CODE_SIGNING_ALLOWED=NO \
    ONLY_ACTIVE_ARCH=NO

# Find the built app
APP_BUNDLE=$(find "$BUILD_DIR/DerivedData" -name "$APP_NAME.app" -type d | head -n 1)

if [ -z "$APP_BUNDLE" ]; then
    echo "Error: Could not find built app"
    exit 1
fi

# Copy to build directory
cp -R "$APP_BUNDLE" "$BUILD_DIR/"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"

echo "✓ App built: $APP_BUNDLE"

# Bundle CLI into app
echo -e "\n4. Bundling CLI into app..."
BIN_DIR="$APP_BUNDLE/Contents/Resources/bin"
mkdir -p "$BIN_DIR"
cp "$BUILD_DIR/cli/marclite" "$BIN_DIR/marclite"
chmod +x "$BIN_DIR/marclite"

echo "✓ CLI bundled into app"

# Verify the bundle
echo -e "\n5. Verifying bundle..."
if [ -f "$BIN_DIR/marclite" ]; then
    echo "✓ marclite binary present in app bundle"
    ls -lh "$BIN_DIR/marclite"
else
    echo "Error: marclite binary not found in app bundle"
    exit 1
fi

# Create DMG
echo -e "\n6. Creating DMG installer..."
DMG_PATH="$BUILD_DIR/$DMG_NAME.dmg"
DMG_TEMP="$BUILD_DIR/dmg-temp"

mkdir -p "$DMG_TEMP"
cp -R "$APP_BUNDLE" "$DMG_TEMP/"
ln -s /Applications "$DMG_TEMP/Applications"

hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    "$DMG_PATH"

rm -rf "$DMG_TEMP"

echo ""
echo "=========================================="
echo "✓ Build Complete!"
echo "=========================================="
echo ""
echo "Installer: $DMG_PATH"
echo "App bundle: $APP_BUNDLE"
echo ""
echo "To install: Open the DMG and drag MarcliteMac to Applications"
echo ""
