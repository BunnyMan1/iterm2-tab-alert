#!/bin/bash
set -euo pipefail

# iTerm2 Tab Color Alert — Installer
# Copies files, adds the trigger, installs the LaunchAgent, and starts the daemon.

INSTALL_DIR="$HOME/.config/iterm2-tab-alert"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
LAUNCH_AGENT_LABEL="com.user.iterm2-tab-alert"
LAUNCH_AGENT_PLIST="$LAUNCH_AGENT_DIR/$LAUNCH_AGENT_LABEL.plist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Preflight checks ---

if [[ "$(uname)" != "Darwin" ]]; then
  echo "Error: This tool only works on macOS with iTerm2."
  exit 1
fi

if ! command -v uv &>/dev/null; then
  echo "Error: 'uv' is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

UV_PATH="$(command -v uv)"

# --- Install files ---

echo "Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"

cp "$SCRIPT_DIR/reset_on_focus.py" "$INSTALL_DIR/reset_on_focus.py"
chmod +x "$INSTALL_DIR/reset_on_focus.py"

# Create wrapper script with resolved uv path
cat > "$INSTALL_DIR/iterm2-tab-alert" <<EOF
#!/bin/bash
exec $UV_PATH run --script $INSTALL_DIR/reset_on_focus.py
EOF
chmod +x "$INSTALL_DIR/iterm2-tab-alert"

echo "Files installed."

# --- Add iTerm2 trigger ---

echo "Adding bell trigger to iTerm2 default profile ..."
cp "$SCRIPT_DIR/add_trigger.py" "$INSTALL_DIR/add_trigger.py"
uv run --script "$INSTALL_DIR/add_trigger.py"

# --- Install LaunchAgent ---

echo "Installing LaunchAgent ..."

# Unload existing agent if present
launchctl unload "$LAUNCH_AGENT_PLIST" 2>/dev/null || true

cat > "$LAUNCH_AGENT_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>iTerm2 Tab Color Alert</string>
    <key>Program</key>
    <string>$INSTALL_DIR/iterm2-tab-alert</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/daemon.log</string>
    <key>ThrottleInterval</key>
    <integer>5</integer>
</dict>
</plist>
EOF

launchctl load "$LAUNCH_AGENT_PLIST"
echo "LaunchAgent loaded."

# --- Done ---

echo ""
echo "========================================="
echo "  Installation complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Open iTerm2 > Settings > General > Magic"
echo "  2. Check 'Enable Python API'"
echo "  3. Restart iTerm2"
echo ""
echo "After restart, any BEL (\\a) on a background tab will turn it red."
echo "Switching to the tab clears the color."
echo ""
echo "Logs: $INSTALL_DIR/daemon.log"
echo "Uninstall: bash $(dirname "$0")/uninstall.sh"
