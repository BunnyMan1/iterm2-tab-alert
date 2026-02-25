# iTerm2 Tab Color Alert

Turn iTerm2 tabs red when a background process needs your attention (BEL character), and automatically clear the color when you switch to that tab.

Built for use with [Claude Code](https://claude.ai/claude-code) and other CLI tools that ring the terminal bell when waiting for input.

## How it works

```
Background tab receives BEL (\a)
        │
        ▼
iTerm2 trigger injects escape codes
        │
        ▼
Tab turns red ◄── stays red until you look at it
        │
        ▼
You switch to the tab
        │
        ▼
Daemon detects focus change → resets color
```

**Two components:**

1. **iTerm2 Trigger** — catches the BEL character and injects escape codes to color the tab red
2. **Python Daemon** — monitors tab focus via iTerm2's Python API and resets the color when you switch to a tab. Also clears the focused tab every 500ms (so a BEL on your current tab flashes briefly then clears)

## Requirements

- macOS
- [iTerm2](https://iterm2.com/) 3.5+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)

## Install

```bash
git clone https://github.com/YOUR_USERNAME/iterm2-tab-alert.git
cd iterm2-tab-alert
bash install.sh
```

Then:

1. Open **iTerm2 > Settings > General > Magic**
2. Check **"Enable Python API"**
3. **Restart iTerm2**

## Uninstall

```bash
bash uninstall.sh
```

## Test

Open two iTerm2 tabs. In one tab, run:

```bash
sleep 3 && echo -e "\a"
```

Switch to the other tab immediately. After 3 seconds the first tab should turn red. Switch back to it — the color clears.

## Files

| Installed to | Purpose |
|---|---|
| `~/.config/iterm2-tab-alert/reset_on_focus.py` | Daemon — resets tab color on focus change + periodic cleanup |
| `~/.config/iterm2-tab-alert/add_trigger.py` | Adds the BEL → red trigger to iTerm2's default profile |
| `~/.config/iterm2-tab-alert/iterm2-tab-alert` | Wrapper script (shows proper name in macOS Background Items) |
| `~/Library/LaunchAgents/com.user.iterm2-tab-alert.plist` | Auto-starts daemon on login |

## Troubleshooting

**Tab turns red but never clears:**

Check the daemon is running and connected:

```bash
# Is it running?
launchctl list | grep -i tab

# Check logs
cat ~/.config/iterm2-tab-alert/daemon.log
```

The log should show `Connected to iTerm2 API`. If it shows connection errors, ensure the Python API is enabled in iTerm2 settings.

**"Trigger Function Call Failed" dialog:**

You have an old RPC-based trigger. Re-run `install.sh` to fix it, then restart iTerm2.

**Daemon log is empty:**

The LaunchAgent sets `PYTHONUNBUFFERED=1`. If you modified the plist manually, ensure that environment variable is present.

## Docker / Remote Containers

The BEL character propagates through Docker's PTY to iTerm2, so the trigger works for processes running inside containers. However, if you use **Claude Code hooks** (or similar notification hooks) inside a container, the hook subprocess may not have a controlling terminal — `printf '\a' > /dev/tty` will fail silently.

### Tiered PTY Strategy (Recommended)

Walk the hook subprocess's ancestor process chain to find the nearest process with a PTY-connected stdout. This targets only the exact `docker exec` session that triggered the notification — other sessions' tabs stay unchanged.

**Process chain:** `hook (sh -c) → Claude Code (bun) → zsh → docker exec`

Claude Code's stdout is connected to the PTY (it's a TUI app). The hook subprocess has pipes (Claude Code captures its output), but walking up `$PPID`'s parent chain finds the PTY.

```bash
# Primary: walk ancestor chain to find PTY
# Fallback: broadcast to all PTYs
found=0; p=$PPID
while [ "$p" -gt 1 ] 2>/dev/null; do
  t=$(readlink /proc/$p/fd/1 2>/dev/null)
  case "$t" in /dev/pts/*)
    printf '\a' > "$t" 2>/dev/null; found=1; break;;
  esac
  p=$(awk '{print $4}' /proc/$p/stat 2>/dev/null) || break
done
[ "$found" = 0 ] && for q in /dev/pts/[0-9]*; do printf '\a' > "$q" 2>/dev/null; done
```

Example Claude Code notification hook command (as a one-liner):

```json
{
  "hooks": {
    "Notification": [{
      "matcher": "permission_prompt|idle_prompt|elicitation_dialog",
      "hooks": [{
        "type": "command",
        "command": "found=0; p=$PPID; while [ \"$p\" -gt 1 ] 2>/dev/null; do t=$(readlink /proc/$p/fd/1 2>/dev/null); case \"$t\" in /dev/pts/*) printf '\\a' > \"$t\" 2>/dev/null; found=1; break;; esac; p=$(awk '{print $4}' /proc/$p/stat 2>/dev/null) || break; done; [ \"$found\" = 0 ] && for q in /dev/pts/[0-9]*; do printf '\\a' > \"$q\" 2>/dev/null; done"
      }]
    }]
  }
}
```

### Simple Broadcast (Alternative)

If the ancestor walk doesn't work for your setup (e.g., non-Linux containers without `/proc`), broadcast BEL to all PTYs. This is simpler but turns every session's tab red, not just the one that needs attention.

```bash
for p in /dev/pts/[0-9]*; do printf '\a' > "$p" 2>/dev/null; done
```

## How it's built

- **Trigger detection:** iTerm2's built-in trigger system with `iTermInjectTrigger` action. Injects [proprietary escape codes](https://iterm2.com/documentation-escape-codes.html) to set tab color.
- **Color reset:** iTerm2 Python API (`iterm2` PyPI package) with `FocusMonitor` for tab switch detection and `session.async_inject()` to send the reset escape code `\e]6;1;bg;*;default`.
- **Process management:** macOS LaunchAgent with `KeepAlive` for auto-restart on crash.
- **Dependencies managed by:** [uv](https://docs.astral.sh/uv/) via PEP 723 inline script metadata — no virtualenv setup needed.

## License

MIT
