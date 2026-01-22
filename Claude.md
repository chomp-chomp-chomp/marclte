# Claude.md - AI Assistant Context

## Project Overview

**MarcliteMac** is a MARC file processing toolkit that provides counting, splitting, merging, and converting capabilities through a native macOS SwiftUI application backed by a bundled Python CLI engine.

## Architecture

This is a **hybrid application** with two main components:

1. **Python CLI Engine** (`engine/`): Core MARC processing logic
   - Package: `marclite`
   - Built with PyInstaller into a standalone binary
   - Handles all MARC parsing and conversions
   - Outputs JSONL events for progress streaming

2. **macOS SwiftUI App** (`macapp/`): Native UI frontend
   - Shells out to the bundled CLI binary
   - Provides native macOS user interface
   - Located at: `MarcliteMac.app/Contents/Resources/bin/marclite`

## Repository Structure

```
marclte/
├── engine/          # Python package and CLI
│   ├── marclite/    # Python source code
│   ├── tests/       # Python tests
│   └── setup.py     # Python package configuration
├── macapp/          # SwiftUI macOS application
│   └── MarcliteMac/ # Xcode project
├── build/           # Build and packaging scripts
│   ├── package_mac.sh           # Bundles CLI into app
│   ├── build_installer_simple.sh # Creates DMG installer
│   └── BUILD.md     # Detailed build instructions
└── .github/         # CI/CD workflows
```

## Key Files to Know

- `engine/marclite/cli.py` - CLI entry point
- `engine/setup.py` - Python package configuration
- `macapp/MarcliteMac/MarcliteMac.xcodeproj` - Xcode project
- `build/package_mac.sh` - Packaging helper script
- `build/build_installer_simple.sh` - DMG creation script

## Development Workflow

### Python Engine Development

```bash
cd engine
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest  # Run tests
```

### Building the CLI Binary

```bash
cd engine
pip install pyinstaller
pyinstaller --name marclite --onefile marclite/cli.py --distpath dist
```

### macOS App Development

Open `macapp/MarcliteMac/MarcliteMac.xcodeproj` in Xcode and build/run.

### Full Build Process

```bash
./build/package_mac.sh              # Build CLI + bundle into app
cd build && ./build_installer_simple.sh  # Create distributable DMG
```

## CI/CD

- GitHub Actions automatically builds the installer on every push
- Download DMG from Actions tab or Releases (for tagged versions)

## Common Tasks

### Making Python Changes
1. Modify code in `engine/marclite/`
2. Run tests with `pytest`
3. Rebuild CLI binary if needed
4. Update app bundle if testing integration

### Making UI Changes
1. Open Xcode project
2. Modify SwiftUI code
3. Build and run in Xcode

### Creating a Release
1. Ensure all tests pass
2. Run `build/build_installer_simple.sh`
3. Test the generated DMG
4. Tag the release in git

## Important Notes

- The CLI is bundled as a standalone binary inside the macOS app
- App expects CLI at: `MarcliteMac.app/Contents/Resources/bin/marclite`
- JSONL streaming is used for CLI → App communication
- Never use `git commit --amend` or force push to main/master
- Always develop on feature branches (prefix: `claude/`)

## Requirements

- macOS with Xcode installed (for app development)
- Python 3.7+ (for engine development)
- PyInstaller (for creating standalone binary)

## Troubleshooting

See `build/BUILD.md` for detailed build instructions, troubleshooting, and code-signing information.
