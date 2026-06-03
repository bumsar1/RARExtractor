#!/bin/bash
# RAR Extractor — installer
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== RAR Extractor installer ==="
echo ""

# ── Homebrew ──────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "Installerer Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/homebrew/install/HEAD/install.sh)"
fi

# ── unar ──────────────────────────────────────────────────────────────────────
if ! command -v unar &>/dev/null; then
    echo "Installerer unar..."
    brew install unar
else
    echo "✓ unar allerede installeret"
fi

# ── Python pakker ─────────────────────────────────────────────────────────────
echo "Installerer Python-pakker..."
pip3 install --quiet --break-system-packages tkinterdnd2 2>/dev/null \
    || pip3 install --quiet tkinterdnd2

echo ""
echo "✓ Alle afhængigheder installeret!"
echo ""

# ── macOS .app via Automator ──────────────────────────────────────────────────
APP_PATH="$HOME/Applications/RAR Extractor.app"
HANDLER="$SCRIPT_DIR/rar_extractor.py"

echo "Opretter macOS-app: $APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

cat > "$APP_PATH/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>         <string>RAR Extractor</string>
  <key>CFBundleIdentifier</key>   <string>dk.cadesign.rar-extractor</string>
  <key>CFBundleVersion</key>      <string>1.0</string>
  <key>CFBundlePackageType</key>  <string>APPL</string>
  <key>CFBundleExecutable</key>   <string>launcher</string>
  <key>CFBundleDocumentTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeExtensions</key>
      <array><string>rar</string></array>
      <key>CFBundleTypeName</key> <string>RAR Archive</string>
      <key>CFBundleTypeRole</key> <string>Viewer</string>
    </dict>
  </array>
</dict>
</plist>
PLIST

# Find python3 with tkinter
PYTHON=$(which python3)

cat > "$APP_PATH/Contents/MacOS/launcher" <<LAUNCHER
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"
exec "$PYTHON" "$HANDLER"
LAUNCHER

chmod +x "$APP_PATH/Contents/MacOS/launcher"

echo ""
echo "======================================"
echo " RAR Extractor er installeret!"
echo "======================================"
echo ""
echo " App: ~/Applications/RAR Extractor.app"
echo ""
echo " Brug:"
echo "   • Åbn appen — slip RAR-filer i vinduet"
echo "   • Eller kør direkte:  python3 '$HANDLER'"
echo ""
