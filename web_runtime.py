#!/usr/bin/env python3
"""EVA runtime-u React UI ilə birlikdə başladan giriş nöqtəsi."""

import asyncio
import json
import os
import threading
import tkinter as tk
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core.dashboard_api import get_dashboard_data
from core.proactive import ProactiveEngine, ProactiveScheduler
from core.ui_bridge import UiBridge
from main import JarvisLive
from ui import JarvisUI


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Vite proxy üçün lokal dashboard HTTP endpoint-i."""

    def do_GET(self):
        if self.path.split("?", 1)[0] != "/api/dashboard":
            self.send_response(404)
            self.end_headers()
            return
        try:
            payload = json.dumps(get_dashboard_data(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            payload = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def log_message(self, format, *args):
        return


def _create_hidden_ui() -> JarvisUI:
    """Tk UI-ni runtime infrastrukturu kimi yaradır, pəncərəni göstərmir."""
    original_enter_fullscreen = JarvisUI._enter_fullscreen
    original_deiconify = tk.Wm.deiconify

    def hidden_enter_fullscreen(self):
        return None

    def hidden_deiconify(self):
        return None

    JarvisUI._enter_fullscreen = hidden_enter_fullscreen
    tk.Wm.deiconify = hidden_deiconify
    try:
        ui = JarvisUI()
    finally:
        JarvisUI._enter_fullscreen = original_enter_fullscreen
        tk.Wm.deiconify = original_deiconify

    ui.root.withdraw()
    return ui


def _start_dashboard_api() -> ThreadingHTTPServer:
    host = os.getenv("EVA_UI_HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("EVA_UI_HTTP_PORT", "8766"))
    server = ThreadingHTTPServer((host, port), DashboardRequestHandler)
    threading.Thread(target=server.serve_forever, name="eva-dashboard-http", daemon=True).start()
    print(f"[E.V.A] 📊 Dashboard API: http://{host}:{port}/api/dashboard")
    return server


def main():
    ui = _create_hidden_ui()
    bridge = None
    dashboard_server = _start_dashboard_api()

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
            dashboard_server.shutdown()
            if bridge and bridge._server:
                bridge._server.shutdown()

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()
