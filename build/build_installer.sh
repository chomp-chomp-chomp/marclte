#!/usr/bin/env bash
# Build script to create a distributable Mac installer for MarcliteMac
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directories
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="$ROOT_DIR/engine"
XCODE_PROJECT="$ROOT_DIR/macapp/MarcliteMac/MarcliteMac.xcodeproj"
BUILD_DIR="$ROOT_DIR/build/output"
DERIVED_DATA="$BUILD_DIR/DerivedData"

# App info
APP_NAME="MarcliteMac"
SCHEME="MarcliteMac"
DMG_NAME="MarcliteMac-Installer"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Building MarcliteMac Installer${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script must be run on macOS with Xcode installed${NC}"
    exit 1
fi

# Check if Xcode is installed
if ! command -v xcodebuild &> /dev/null; then
    echo -e "${RED}Error: Xcode command line tools not found. Install with: xcode-select --install${NC}"
    exit 1
fi

# Clean previous builds
echo -e "\n${GREEN}Step 1: Cleaning previous builds...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build Python CLI with PyInstaller
echo -e "\n${GREEN}Step 2: Building Python CLI engine...${NC}"
cd "$ENGINE_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip wheel
pip install -e .
pip install --upgrade pyinstaller

# Build the standalone CLI binary
echo "Building marclite binary with PyInstaller..."
pyinstaller --name marclite \
    --onefile \
    -m marclite.cli \
    --distpath "$BUILD_DIR/cli" \
    --workpath "$BUILD_DIR/pyinstaller-build" \
    --specpath "$BUILD_DIR" \
    --clean

echo -e "${GREEN}✓ CLI binary built: $BUILD_DIR/cli/marclite${NC}"

# Build macOS app with xcodebuild
echo -e "\n${GREEN}Step 3: Building macOS application...${NC}"
xcodebuild clean -project "$XCODE_PROJECT" -scheme "$SCHEME" -configuration Release
xcodebuild archive \
    -project "$XCODE_PROJECT" \
    -scheme "$SCHEME" \
    -configuration Release \
    -archivePath "$BUILD_DIR/$APP_NAME.xcarchive" \
    -derivedDataPath "$DERIVED_DATA" \
    CODE_SIGN_IDENTITY="-" \
    CODE_SIGNING_REQUIRED=NO \
    CODE_SIGNING_ALLOWED=NO

# Export the app
echo -e "\n${GREEN}Step 4: Exporting application bundle...${NC}"
xcodebuild -exportArchive \
    -archivePath "$BUILD_DIR/$APP_NAME.xcarchive" \
    -exportPath "$BUILD_DIR" \
    -exportOptionsPlist "$ROOT_DIR/build/ExportOptions.plist"

APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"

if [ ! -d "$APP_BUNDLE" ]; then
    # If export with plist fails, try copying directly from archive
    echo "Copying app from archive..."
    APP_BUNDLE_SOURCE="$BUILD_DIR/$APP_NAME.xcarchive/Products/Applications/$APP_NAME.app"
    if [ -d "$APP_BUNDLE_SOURCE" ]; then
        cp -R "$APP_BUNDLE_SOURCE" "$BUILD_DIR/"
    else
        echo -e "${RED}Error: Failed to build app bundle${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ App bundle created: $APP_BUNDLE${NC}"

# Bundle the CLI into the app
echo -e "\n${GREEN}Step 5: Bundling CLI into app...${NC}"
BIN_DIR="$APP_BUNDLE/Contents/Resources/bin"
mkdir -p "$BIN_DIR"
cp "$BUILD_DIR/cli/marclite" "$BIN_DIR/marclite"
chmod +x "$BIN_DIR/marclite"

echo -e "${GREEN}✓ CLI bundled into app at: $BIN_DIR/marclite${NC}"

# Create DMG installer
echo -e "\n${GREEN}Step 6: Creating DMG installer...${NC}"
DMG_PATH="$BUILD_DIR/$DMG_NAME.dmg"
DMG_TEMP="$BUILD_DIR/dmg-temp"

# Create temporary DMG directory
mkdir -p "$DMG_TEMP"
cp -R "$APP_BUNDLE" "$DMG_TEMP/"

# Create symbolic link to Applications folder
ln -s /Applications "$DMG_TEMP/Applications"

# Create the DMG
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    "$DMG_PATH"

# Clean up temp directory
rm -rf "$DMG_TEMP"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Build Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nInstaller location:"
echo -e "  ${BLUE}$DMG_PATH${NC}"
echo -e "\nTo install:"
echo -e "  1. Double-click the DMG file"
echo -e "  2. Drag $APP_NAME to the Applications folder"
echo -e "  3. Launch from Applications"
echo -e "\nApp bundle (for testing):"
echo -e "  ${BLUE}$APP_BUNDLE${NC}"
echo ""

# Display file sizes
DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
echo -e "DMG size: ${GREEN}$DMG_SIZE${NC}"
