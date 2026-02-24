#!/bin/bash
set -euo pipefail

# iTerm2 Tab Color Alert — Uninstaller

INSTALL_DIR="$HOME/.config/iterm2-tab-alert"
LAUNCH_AGENT_PLIST="$HOME/Library/LaunchAgents/com.user.iterm2-tab-alert.plist"

echo "Uninstalling iTerm2 Tab Color Alert ..."

# Stop and remove LaunchAgent
if [[ -f "$LAUNCH_AGENT_PLIST" ]]; then
  launchctl unload "$LAUNCH_AGENT_PLIST" 2>/dev/null || true
  rm "$LAUNCH_AGENT_PLIST"
  echo "LaunchAgent removed."
fi

# Kill any running daemon
pkill -f "reset_on_focus.py" 2>/dev/null || true

# Remove installed files
if [[ -d "$INSTALL_DIR" ]]; then
  rm -rf "$INSTALL_DIR"
  echo "Files removed from $INSTALL_DIR"
fi

echo ""
echo "Uninstalled. The iTerm2 trigger remains in your profile."
echo "To remove it: iTerm2 > Settings > Profiles > Advanced > Triggers > Edit"
echo "Delete the trigger with regex '\\a'."
