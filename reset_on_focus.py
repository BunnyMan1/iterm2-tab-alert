#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["iterm2"]
# ///

"""
iTerm2 Tab Color Alert Daemon

Resets tab color to default when user switches to a tab.
Also periodically resets the currently focused tab's color
(handles case where BEL fires on the already-focused tab).

Works with the iTermInjectTrigger that sets tab color red on BEL.

Requires: iTerm2 Python API enabled (Settings > General > Magic > Enable Python API)
"""

import asyncio
import iterm2

RESET_ESCAPE = b"\x1b]6;1;bg;*;default\x07"


async def reset_tab_color(tab):
    for session in tab.sessions:
        await session.async_inject(RESET_ESCAPE)
        change = iterm2.LocalWriteOnlyProfile()
        change.set_use_tab_color(False)
        await session.async_set_profile_properties(change)


async def main(connection):
    print("Connected to iTerm2 API")

    async def periodic_reset():
        """Unconditionally reset focused tab's color every 500ms."""
        while True:
            await asyncio.sleep(0.5)
            try:
                app_now = await iterm2.async_get_app(connection)
                window = app_now.current_terminal_window
                if window and window.current_tab:
                    await reset_tab_color(window.current_tab)
            except Exception as e:
                print(f"periodic_reset error: {e}")

    asyncio.ensure_future(periodic_reset())
    print("Periodic reset started")

    async with iterm2.FocusMonitor(connection) as monitor:
        print("FocusMonitor started")
        while True:
            update = await monitor.async_get_next_update()
            if update.selected_tab_changed:
                tab_id = update.selected_tab_changed.tab_id
                print(f"Tab switched: {tab_id}")
                try:
                    app_now = await iterm2.async_get_app(connection)
                    tab = app_now.get_tab_by_id(tab_id)
                    if tab:
                        await reset_tab_color(tab)
                except Exception as e:
                    print(f"focus_reset error: {e}")


iterm2.run_forever(main, retry=True)
