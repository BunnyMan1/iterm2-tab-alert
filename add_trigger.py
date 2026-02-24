#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Add/update the bell trigger in ALL iTerm2 profiles.
Uses iTermInjectTrigger to set tab color red via escape codes on BEL.

Run once. Restart iTerm2 afterward for changes to take effect.
"""

import plistlib
from pathlib import Path

PLIST_PATH = Path.home() / "Library" / "Preferences" / "com.googlecode.iterm2.plist"

TRIGGER = {
    "action": "iTermInjectTrigger",
    "regex": "\\a",
    "partial": True,
    "parameter": (
        "\\e]6;1;bg;red;brightness;220\\e\\\\"
        "\\e]6;1;bg;green;brightness;40\\e\\\\"
        "\\e]6;1;bg;blue;brightness;40\\e\\\\"
    ),
}

with open(PLIST_PATH, "rb") as f:
    plist = plistlib.load(f)

profiles = plist.get("New Bookmarks", [])
updated = 0

for profile in profiles:
    name = profile.get("Name", "unnamed")
    triggers = profile.get("Triggers", [])

    # Remove any old bell triggers we created
    triggers = [
        t for t in triggers
        if not (t.get("regex") == "\\a" and t.get("action") in ("iTermInjectTrigger", "iTermRPCTrigger"))
    ]

    triggers.append(TRIGGER)
    profile["Triggers"] = triggers
    updated += 1

with open(PLIST_PATH, "wb") as f:
    plistlib.dump(plist, f)

print(f"Trigger added to {updated} profiles.")
print("Restart iTerm2 for changes to take effect.")
