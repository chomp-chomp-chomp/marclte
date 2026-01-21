# Building MarcliteMac Installer

This guide explains how to build a distributable Mac installer (.dmg) for MarcliteMac.

## Requirements

- **macOS** (Big Sur 12.0 or later)
- **Xcode** (14.0 or later) with Command Line Tools
- **Python 3.8+**
- **Git**

### Install Xcode Command Line Tools

```bash
xcode-select --install
```

Verify installation:
```bash
xcodebuild -version
```

## Quick Start

### Option 1: Simple Build Script (Recommended for Unsigned Apps)

```bash
cd build
./build_installer_simple.sh
```

This creates:
- `build/output/MarcliteMac.app` - The application bundle
- `build/output/MarcliteMac-Installer.dmg` - The installer disk image

### Option 2: Full Build Script (With Archive)

```bash
cd build
./build_installer.sh
```

This uses Xcode's archive and export process, which is better for signed/notarized apps.

## Build Process Steps

Both scripts perform these steps:

1. **Clean previous builds** - Removes old build artifacts
2. **Build Python CLI** - Uses PyInstaller to create a standalone `marclite` binary
3. **Build Mac app** - Compiles the SwiftUI app with xcodebuild
4. **Bundle CLI** - Copies the CLI binary into the app at `Contents/Resources/bin/marclite`
5. **Create DMG** - Packages everything into a disk image for distribution

## Output

After a successful build, you'll find:

```
build/output/
├── MarcliteMac.app                  # Application bundle (ready to use)
├── MarcliteMac-Installer.dmg        # Distributable installer
├── cli/
│   └── marclite                     # Standalone CLI binary
└── DerivedData/                     # Xcode build artifacts
```

## Installing the App

### From DMG (End Users)

1. Double-click `MarcliteMac-Installer.dmg`
2. Drag `MarcliteMac.app` to the Applications folder
3. Launch from Applications or Spotlight

### For Testing (Developers)

You can run the app directly from the build directory:

```bash
open build/output/MarcliteMac.app
```

## Troubleshooting

### "Cannot be opened because the developer cannot be verified"

If you see this error when opening the app, it's because the app isn't code-signed. To allow it:

**macOS Ventura and later:**
```bash
xattr -cr build/output/MarcliteMac.app
```

Then right-click the app, hold Option, and select "Open".

**Via System Settings:**
1. Try to open the app (it will fail)
2. Go to System Settings → Privacy & Security
3. Click "Open Anyway" next to the blocked app message

### Build Fails: "xcodebuild: command not found"

Install Xcode Command Line Tools:
```bash
xcode-select --install
```

### Build Fails: Python/PyInstaller Issues

Ensure Python 3.8+ is installed:
```bash
python3 --version
```

Clean the Python virtual environment:
```bash
cd engine
rm -rf .venv
```

Then run the build script again.

### App Doesn't Find the CLI Binary

Verify the CLI is bundled correctly:
```bash
ls -la build/output/MarcliteMac.app/Contents/Resources/bin/marclite
```

The file should exist and be executable.

### DMG Creation Fails

Make sure you have enough disk space and no existing DMG is mounted:
```bash
hdiutil detach /Volumes/MarcliteMac 2>/dev/null || true
rm -f build/output/MarcliteMac-Installer.dmg
```

Then run the build script again.

## Code Signing & Notarization (Optional)

For public distribution, you should code-sign and notarize your app:

1. **Enroll in Apple Developer Program** ($99/year)
2. **Get a Developer ID Application certificate**
3. **Modify the build script** to use your signing identity:
   ```bash
   CODE_SIGN_IDENTITY="Developer ID Application: Your Name (TEAM_ID)"
   CODE_SIGNING_REQUIRED=YES
   CODE_SIGNING_ALLOWED=YES
   ```
4. **Notarize the app** with Apple:
   ```bash
   xcrun notarytool submit MarcliteMac-Installer.dmg \
     --apple-id "your@email.com" \
     --team-id "TEAM_ID" \
     --password "app-specific-password" \
     --wait
   ```
5. **Staple the notarization**:
   ```bash
   xcrun stapler staple build/output/MarcliteMac-Installer.dmg
   ```

## Distribution

Once built, you can distribute `MarcliteMac-Installer.dmg` via:
- Direct download from your website
- GitHub Releases
- Mac App Store (requires additional setup)

## Continuous Integration

For automated builds (GitHub Actions, etc.), see the example workflow:

```yaml
name: Build Mac App
on: [push]
jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Build Installer
        run: |
          cd build
          ./build_installer_simple.sh
      - name: Upload DMG
        uses: actions/upload-artifact@v3
        with:
          name: MarcliteMac-Installer
          path: build/output/MarcliteMac-Installer.dmg
```

## Development Workflow

For development (without creating a DMG each time):

1. Build the CLI:
   ```bash
   ./build/package_mac.sh
   ```

2. Open and run in Xcode:
   ```bash
   open macapp/MarcliteMac/MarcliteMac.xcodeproj
   ```

3. Click Run (⌘R) to test

## Clean Build

To completely clean all build artifacts:

```bash
rm -rf build/output
rm -rf engine/.venv
rm -rf engine/dist
rm -rf engine/build
```

## Getting Help

- Check the [main README](../README.md) for development setup
- Review Swift code in `macapp/MarcliteMac/MarcliteMac/`
- Review Python code in `engine/marclite/`
