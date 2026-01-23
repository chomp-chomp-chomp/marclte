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

The repository includes a FastAPI-based HTTP wrapper around the marclite CLI. The web service provides REST endpoints that mirror the CLI commands with identical behavior.

### Local Development

Install dependencies and start the server:

```bash
pip install -r requirements.txt
pip install -e engine
uvicorn web.app:app --reload --host 0.0.0.0 --port 10000
```

The service will be available at `http://localhost:10000`. Visit `http://localhost:10000/docs` for interactive API documentation.

### Endpoints

#### Health Check

```bash
curl http://localhost:10000/health
```

Returns `{"status": "healthy"}`.

#### Count Records

```bash
curl -X POST http://localhost:10000/count \
  -F "input_file=@sample.mrc"
```

Returns a JSONL stream with events:

```
{"event":"start","operation":"count","input":"sample.mrc"}
{"event":"done","operation":"count","input":"sample.mrc","format":"mrc","records":100,"dropped":0,"warnings":[]}
```

#### Convert Format

```bash
curl -X POST http://localhost:10000/convert \
  -F "input_file=@sample.mrc" \
  -F "to=marcxml" \
  --output converted.xml
```

Converts a MARC file to the specified format. Supported formats: `mrc`, `mrk`, `marcxml`.

#### Split File

```bash
curl -X POST http://localhost:10000/split \
  -F "input_file=@sample.mrc" \
  -F "every=50" \
  -F "to=mrc" \
  --output split_output.zip
```

Splits a MARC file into chunks of N records. Returns a zip file containing all output files. The `to` parameter is optional and defaults to the input format.

#### Merge Files

```bash
curl -X POST http://localhost:10000/merge \
  -F "files=@part1.mrc" \
  -F "files=@part2.mrc" \
  -F "files=@part3.mrc" \
  -F "to=mrc" \
  --output merged.mrc
```

Merges multiple MARC files into a single file in the specified format.

### Deployment to Render

The repository includes a `render.yaml` configuration for deployment to Render's free tier.

1. Create a new Web Service on Render
2. Connect your repository
3. Render will automatically detect the configuration and deploy

The service is stateless and uses `/tmp` for ephemeral file storage. Files are automatically cleaned up after each request. The Render free tier includes automatic idle spin-down after 15 minutes of inactivity and a cold start delay when requests resume.

### Implementation Notes

The web service invokes the marclite CLI as a subprocess for each operation. This ensures behavior matches the CLI exactly. All file uploads are saved to temporary directories under `/tmp` and removed immediately after processing. The service does not store files persistently or use a database.

## Web Frontend (GitHub Pages)

A browser-based frontend is provided in the `docs/` directory for easy interaction with the API. The interface is fully customizable with your own branding and color scheme.

### Customizing Branding

Edit `docs/config.js` to customize:

```javascript
const BRANDING = {
  appName: 'Your App Name',
  tagline: 'Your tagline',
  colors: {
    primary: '#2563eb',      // Main brand color
    secondary: '#1e40af',    // Darker shade
    // ... more colors
  },
  logo: 'https://your-site.com/logo.png',     // Optional logo URL
  favicon: 'https://your-site.com/icon.png',  // Optional favicon URL
  footer: '© 2025 Your Company',
  apiEndpoint: 'https://your-app.onrender.com'  // Your Render URL
};
```

### Deploying to GitHub Pages

1. Push the `docs/` directory to your repository
2. Go to your repository Settings on GitHub
3. Navigate to Pages (under Code and automation)
4. Set Source to "Deploy from a branch"
5. Select branch: `main` (or your default branch)
6. Select folder: `/docs`
7. Click Save

Your site will be available at `https://your-username.github.io/marclte/`

### Using a Custom Domain

To use your own domain:

1. In your repository Settings > Pages, enter your custom domain under "Custom domain"
2. Add a `CNAME` file to the `docs/` directory with your domain name
3. Configure your DNS provider with a CNAME record pointing to `your-username.github.io`

Example CNAME file:

```
marclite.yourdomain.com
```

DNS configuration (at your domain provider):

```
Type: CNAME
Name: marclite (or subdomain of your choice)
Value: your-username.github.io
```

After DNS propagates, your site will be available at your custom domain.

### Local Testing

To test the frontend locally:

1. Start the backend API (see Web Service section above)
2. Make sure `apiEndpoint` in `docs/config.js` points to `http://localhost:10000`
3. Open `docs/index.html` in your browser, or use a local server:

```bash
cd docs
python -m http.server 8000
```

Then visit `http://localhost:8000`
