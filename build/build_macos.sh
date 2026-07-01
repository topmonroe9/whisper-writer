#!/usr/bin/env bash
#
# Build the WhisperWriter macOS .app bundle.
#
# Usage:
#   bash build/build_macos.sh           # build dist/WhisperWriter.app
#   bash build/build_macos.sh --zip     # also produce a distributable .zip
#
# Run this on the Mac itself (Apple Silicon or Intel) inside the project venv.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ASSETS="$PROJECT_ROOT/assets"
SRC_PNG="$ASSETS/ww-logo.png"
ICNS="$ASSETS/ww-logo.icns"
APP="$PROJECT_ROOT/dist/WhisperWriter.app"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: this script must be run on macOS." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Generate the .icns icon from ww-logo.png (requires sips + iconutil, both
#    part of macOS). Skipped automatically if the source PNG is missing.
# ---------------------------------------------------------------------------
if [[ -f "$SRC_PNG" ]]; then
    echo "==> Generating icon: $ICNS"
    ICONSET="$(mktemp -d)/WhisperWriter.iconset"
    mkdir -p "$ICONSET"
    for size in 16 32 64 128 256 512; do
        sips -z "$size" "$size" "$SRC_PNG" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
        double=$((size * 2))
        sips -z "$double" "$double" "$SRC_PNG" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
    done
    iconutil -c icns "$ICONSET" -o "$ICNS"
    rm -rf "$(dirname "$ICONSET")"
else
    echo "==> ww-logo.png not found; building without a custom icon"
fi

# ---------------------------------------------------------------------------
# 2. Run PyInstaller against the macOS spec.
# ---------------------------------------------------------------------------
echo "==> Running PyInstaller"
cd "$PROJECT_ROOT"
python -m PyInstaller --clean \
    --distpath "$PROJECT_ROOT/dist" \
    --workpath "$PROJECT_ROOT/build/pyinstaller_work" \
    "$SCRIPT_DIR/whisperwriter_macos.spec"

if [[ ! -d "$APP" ]]; then
    echo "Error: build did not produce $APP" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 3. Ad-hoc code sign. On Apple Silicon, binaries must be signed (even ad-hoc)
#    to run, and a stable signature keeps the macOS privacy permissions
#    (Accessibility / Input Monitoring / Microphone) from resetting on rebuild.
#    For distribution to other machines you still need a Developer ID identity
#    plus notarization — replace "-" below with your identity.
# ---------------------------------------------------------------------------
echo "==> Ad-hoc code signing"
codesign --force --deep --sign - "$APP"

echo "==> Build complete: $APP"

# ---------------------------------------------------------------------------
# 4. Optional zip for distribution (preserves macOS metadata via ditto).
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--zip" ]]; then
    VERSION="$(python - <<'PY'
import re, pathlib
text = pathlib.Path("pyproject.toml").read_text()
m = re.search(r'^version\s*=\s*["\']([^"\']+)', text, re.M)
print(m.group(1) if m else "0.0.0")
PY
)"
    ARCH="$(uname -m)"
    ZIP="$PROJECT_ROOT/dist/WhisperWriter-v${VERSION}-macos-${ARCH}.zip"
    echo "==> Creating $ZIP"
    ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
    echo "==> Archive ready: $ZIP"
fi
