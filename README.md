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
pyinstaller --name marclite --onefile marclite/cli.py --distpath dist
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

## Building a Distributable Installer

To create a complete Mac installer package (.dmg) for distribution:

```bash
cd build
./build_installer_simple.sh
```

This will:
1. Build the Python CLI as a standalone binary
2. Build the Mac app with xcodebuild
3. Bundle the CLI into the app
4. Create a `.dmg` installer at `build/output/MarcliteMac-Installer.dmg`

**Requirements:** macOS with Xcode installed

For detailed build instructions, troubleshooting, and code-signing information, see [build/BUILD.md](build/BUILD.md).

### Automated Builds

The repository includes a GitHub Actions workflow that automatically builds the installer on every push. Download the DMG from the Actions tab or from Releases (for tagged versions).

## Verifying Integration

1. Build the CLI using the script above.
2. Open the Xcode project and run the app.
3. Use the Run button to execute an operation. Logs should show streamed JSONL events from the CLI.

## Web Service (Render)

The repository includes a FastAPI web service that wraps the marclite CLI for deployment on platforms like Render.

### Local Development

Install dependencies and start the service:

```bash
pip install -r requirements.txt
uvicorn web.app:app --reload --host 0.0.0.0 --port 10000
```

The service will be available at http://localhost:10000

### API Endpoints

#### GET /health

Health check endpoint.

```bash
curl http://localhost:10000/health
```

#### POST /count

Count records in a MARC file. Returns JSONL stream.

```bash
curl -X POST http://localhost:10000/count \
  -F "input_file=@sample.mrc"
```

#### POST /convert

Convert MARC file to specified format. Returns converted file.

```bash
curl -X POST http://localhost:10000/convert \
  -F "input_file=@sample.mrc" \
  -F "to=mrk" \
  -o output.mrk
```

Valid formats: mrc, mrk, marcxml

#### POST /split

Split MARC file into chunks. Returns zip archive.

```bash
curl -X POST http://localhost:10000/split \
  -F "input_file=@sample.mrc" \
  -F "every=100" \
  -F "to=mrc" \
  -o split_output.zip
```

The `to` parameter is optional. If not specified, the format is detected from the input file.

#### POST /merge

Merge multiple MARC files. Returns merged file.

```bash
curl -X POST http://localhost:10000/merge \
  -F "files=@file1.mrc" \
  -F "files=@file2.mrc" \
  -F "to=mrc" \
  -o merged.mrc
```

### Deployment

The included `render.yaml` configures deployment to Render. The service is stateless and uses /tmp for temporary file storage. Files are deleted after each request completes.

The Render free tier may spin down the service after periods of inactivity. Initial requests after idle periods will experience cold start latency.
