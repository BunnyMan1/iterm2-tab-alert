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
import logging
from pathlib import Path

import iterm2
import iterm2.app
import iterm2.connection

LOG_PATH = Path.home() / ".config" / "iterm2-tab-alert" / "daemon.log"
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

RESET_ESCAPE = b"\x1b]6;1;bg;*;default\x07"


async def reset_tab_color(tab):
    for session in tab.sessions:
        await session.async_inject(RESET_ESCAPE)
        change = iterm2.LocalWriteOnlyProfile()
        change.set_use_tab_color(False)
        await session.async_set_profile_properties(change)


async def main(connection):
    periodic_task = None

    async def periodic_reset():
        """Unconditionally reset focused tab's color every 500ms."""
        while True:
            await asyncio.sleep(0.5)
            app_now = await iterm2.async_get_app(connection)
            window = app_now.current_terminal_window
            if window and window.current_tab:
                await reset_tab_color(window.current_tab)

    try:
        periodic_task = asyncio.ensure_future(periodic_reset())

        async with iterm2.FocusMonitor(connection) as monitor:
            while True:
                update = await monitor.async_get_next_update()
                if update.selected_tab_changed:
                    tab_id = update.selected_tab_changed.tab_id
                    app_now = await iterm2.async_get_app(connection)
                    tab = app_now.get_tab_by_id(tab_id)
                    if tab:
                        await reset_tab_color(tab)
    finally:
        if periodic_task:
            periodic_task.cancel()


async def connect_and_run():
    """Connect using async with (context manager), matching async_connect's pattern.

    async_create() uses bare 'await' on the websocket connect coroutine, while
    the working async_connect() uses 'async with'. This replicates the working
    pattern but adds disconnect detection via asyncio.wait.
    """
    connection = iterm2.Connection()
    connection.authenticate(False)

    async with connection._get_connect_coro() as websocket:
        connection.websocket = websocket
        log.info("Connected to iTerm2 API")

        dispatch_task = asyncio.ensure_future(
            connection._async_dispatch_forever(connection, asyncio.get_running_loop())
        )

        main_task = asyncio.create_task(main(connection))

        # Wait for either to finish. When the dispatch task dies
        # (websocket dropped on iTerm2 restart), cancel main and return
        # so the outer loop can reconnect.
        done, pending = await asyncio.wait(
            [main_task, dispatch_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        for task in done:
            try:
                task.result()
            except Exception as e:
                log.info("Task ended: %s", e)

    connection._remove_auth()


async def run_with_reconnect():
    """Manual retry loop that detects mid-session disconnects.

    iterm2.run_forever(retry=True) only retries connection establishment
    failures. Once connected, if iTerm2 restarts, the internal dispatch task
    dies but main() hangs on futures that will never resolve.

    Fix: replicate async_connect's 'async with' websocket pattern (which is
    known to work) but add disconnect detection via asyncio.wait(FIRST_COMPLETED).
    """
    while True:
        try:
            # Clean up global state from previous connection:
            #
            # 1. Connection.helpers is a CLASS-LEVEL list. Old FocusMonitor handlers
            #    from previous connections crash when the new dispatch task invokes
            #    them (they reference the dead connection's App object).
            iterm2.Connection.helpers.clear()

            # 2. Flush disconnect callbacks (normally done in Connection.run()).
            #    This calls invalidate_app() which clears the stale App singleton.
            #    Without this, async_get_app() returns the old App bound to the
            #    dead connection, and all API calls silently go nowhere.
            callbacks = list(iterm2.connection.gDisconnectCallbacks)
            iterm2.connection.gDisconnectCallbacks = []
            for callback in callbacks:
                callback()

            await connect_and_run()

        except (ConnectionRefusedError, OSError) as e:
            log.info("Cannot connect to iTerm2: %s", e)
        except Exception as e:
            log.info("Unexpected error: %s", e)

        log.info("Reconnecting in 5s...")
        await asyncio.sleep(5)


asyncio.run(run_with_reconnect())
