#!/bin/bash
# Installs the "Claude Usage" plugin for SwiftBar.
# Usage (in Terminal, from this folder):   bash install.sh
set -e
cd "$(dirname "$0")"

PLUGINS="$HOME/SwiftBarPlugins"
PLUGIN="claude_usage.1m.py"

echo "[1/4] SwiftBar..."
if [ ! -d "/Applications/SwiftBar.app" ]; then
  if command -v brew >/dev/null 2>&1; then
    brew install --cask swiftbar
  else
    echo "  SwiftBar is missing. Download it from https://swiftbar.app (or install Homebrew) and run this again."
    exit 1
  fi
else
  echo "  already installed"
fi

echo "[2/4] Pillow (to draw the bars)..."
if /usr/bin/python3 -c "import PIL" 2>/dev/null; then
  echo "  already installed"
else
  /usr/bin/python3 -m pip install --user --quiet pillow || \
    echo "  Could not install Pillow: the plugin will run in text-only mode."
fi

echo "[3/4] Copying the plugin to $PLUGINS..."
mkdir -p "$PLUGINS"
rm -f "$PLUGINS/claude_uso.1m.py"   # old name of the plugin
cp "$PLUGIN" "$PLUGINS/$PLUGIN"
chmod +x "$PLUGINS/$PLUGIN"
xattr -d com.apple.quarantine "$PLUGINS/$PLUGIN" 2>/dev/null || true

echo "[4/4] Configuring and opening SwiftBar..."
osascript -e 'quit app "SwiftBar"' 2>/dev/null || true
defaults write com.ameba.SwiftBar PluginDirectory "$PLUGINS"
sleep 1
open -a SwiftBar

echo
echo "DONE. If macOS asks for Keychain access to \"Claude Code-credentials\","
echo "click \"Always Allow\" (that's where your token comes from)."
echo "To start it at login: SwiftBar menu > Preferences > Launch at login."
