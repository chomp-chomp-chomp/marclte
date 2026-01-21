# MarcliteMac

MarcliteMac provides a small MarcEdit-lite toolkit for counting, splitting, merging, and converting MARC files through a native macOS SwiftUI app backed by a bundled Python CLI engine.

## Repository Layout

- `engine/`: Python package and CLI (`marclite`) that handles MARC parsing and conversions.
- `macapp/`: SwiftUI macOS application that shells out to the bundled CLI.
- `build/`: helper scripts for packaging.

## Development Setup

### Python engine

```bash
cd engine
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run tests:

```bash
pytest
```

### Build the CLI with PyInstaller

```bash
cd engine
pip install pyinstaller
pyinstaller --name marclite --onefile -m marclite.cli --distpath dist
```

The resulting binary is `engine/dist/marclite`.

## macOS App

Open `macapp/MarcliteMac/MarcliteMac.xcodeproj` in Xcode and build/run.

The app expects the bundled CLI at:

```
MarcliteMac.app/Contents/Resources/bin/marclite
```

## Packaging Script

Run the helper script to build the CLI and place it in the app bundle:

```bash
./build/package_mac.sh
```

The script builds the CLI using PyInstaller and copies it into the app bundle under `Contents/Resources/bin/`.

## Verifying Integration

1. Build the CLI using the script above.
2. Open the Xcode project and run the app.
3. Use the Run button to execute an operation. Logs should show streamed JSONL events from the CLI.
