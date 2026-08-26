#!/usr/bin/env python3
"""EVA runtime-u React UI ilə birlikdə başladan giriş nöqtəsi."""

import asyncio
import os
import threading

from core.proactive import ProactiveEngine, ProactiveScheduler
from core.ui_bridge import UiBridge
from main import JarvisLive
from ui import JarvisUI


def main():
    ui = JarvisUI()
    # React əsas interfeysdir. Mövcud Tk runtime komponentləri yalnız callback,
    # audio/state və event-loop infrastrukturu kimi saxlanılır.
    ui.root.withdraw()
    bridge = None

    def runner():
        nonlocal bridge
        ui.wait_for_api_key()
        ui.root.after(0, ui.root.withdraw)
        jarvis = JarvisLive(ui)
        bridge = UiBridge(ui, tool_executor=jarvis._tool_executor)

        proactive_scheduler = None
        if str(os.getenv("EVA_PROACTIVE_ENABLED", "true")).strip().lower() not in {"0", "false", "no", "off"}:
            proactive_scheduler = ProactiveScheduler(
                ProactiveEngine(),
                jarvis._on_proactive_notification,
                interval=int(os.getenv("EVA_PROACTIVE_INTERVAL", "120")),
            )
            proactive_scheduler.start()
            ui.root.after(0, ui.write_log, "SYS: Proaktiv monitor aktivdir.")

        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Ayrılır...")
        finally:
            if proactive_scheduler:
                proactive_scheduler.stop()
            if bridge and bridge._server:
                bridge._server.shutdown()

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()
