#!/usr/bin/env python3
"""EVA runtime-u React UI ilə birlikdə başladan vahid giriş nöqtəsi."""

import json
import os
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core.dashboard_api import get_dashboard_data
from core.proactive import ProactiveEngine, ProactiveScheduler
from core.settings_runtime import apply_saved_settings, install_settings_bridge
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
    print(f"[E.V.A] 📊 Dashboard API: http://{host}:{port}/api/dashboard", flush=True)
    return server


def _start_react_frontend() -> subprocess.Popen | None:
    """React development serverini eyni terminal prosesinə qoşur."""
    frontend_dir = Path(__file__).resolve().parent / "frontend"
    if not (frontend_dir / "package.json").exists():
        print("[E.V.A] ⚠️ frontend/package.json tapılmadı; React serveri başladılmadı.", flush=True)
        return None

    npm = "npm.cmd" if os.name == "nt" else "npm"
    print("[E.V.A] ⚛️ React UI başladılır...", flush=True)
    try:
        process = subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1"],
            cwd=str(frontend_dir),
            stdin=None,
            stdout=None,
            stderr=None,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
    except OSError as exc:
        print(f"[E.V.A] ❌ React UI başlatılmadı: {exc}", flush=True)
        return None

    def open_browser():
        time.sleep(2.0)
        url = "http://127.0.0.1:5173"
        print(f"[E.V.A] 🌐 React UI: {url}", flush=True)
        try:
            webbrowser.open(url)
        except Exception as exc:
            print(f"[E.V.A] ⚠️ Browser avtomatik açıla bilmədi: {exc}", flush=True)

    threading.Thread(target=open_browser, name="eva-open-browser", daemon=True).start()
    return process


def main():
    ui = _create_hidden_ui()
    apply_saved_settings(ui)
    dashboard_server = _start_dashboard_api()
    frontend_process = _start_react_frontend()

    # React UI açılışına paralel startup SFX.
    ui.sound.play_startup()
    print(
        f"[E.V.A] 🔊 Startup SFX: enabled={ui.sound._enabled}, "
        f"file={__import__('ui')._START_FILE}, "
        f"exists={__import__('ui')._START_FILE.exists()}",
        flush=True,
    )

    def runner():
        ui.wait_for_api_key()
        ui.root.after(0, ui.root.withdraw)
        jarvis = JarvisLive(ui)

        def handle_control(command: str) -> dict:
            """React idarəetmə panelinin runtime əmrlərini mövcud EVA state-inə bağlayır."""
            command = str(command or "").strip().lower()

            if command == "pause":
                paused = not bool(jarvis._paused)
                jarvis._on_pause_toggle(paused)
                ui.write_log(f"SYS: EVA {'pauza edildi' if paused else 'davam etdirildi'}.")
                return {"paused": paused}

            if command == "camera":
                activate = not jarvis._webcam_streamer.is_active
                if activate:
                    status = jarvis._webcam_streamer.start()
                    active = status in {"ok", "already_active"}
                else:
                    jarvis._webcam_streamer.stop()
                    active = False
                ui.root.after(0, ui.set_webcam_active, active)
                ui.write_log(f"SYS: Kamera {'aktivdir' if active else 'deaktiv edildi'}.")
                return {"camera_active": active}

            if command == "microphone":
                ui.muted = not bool(ui.muted)
                muted = bool(ui.muted)
                ui.write_log(f"SYS: Mikrofon {'səssizdir' if muted else 'aktivdir'}.")
                return {"microphone_muted": muted}

            if command == "shutdown":
                ui.write_log("SYS: EVA bağlanır...")
                jarvis._webcam_streamer.stop()
                jarvis._stop_music()
                ui.root.after(0, ui.root.destroy)
                return {
                    "paused": True,
                    "camera_active": False,
                    "microphone_muted": True,
                }

            raise ValueError("Naməlum idarəetmə əmri.")

        ui.on_control_command = handle_control
        bridge = UiBridge(ui, tool_executor=jarvis._tool_executor)
        install_settings_bridge(bridge, ui)

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
            import asyncio
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Ayrılır...", flush=True)
        except Exception as exc:
            print(f"[E.V.A] ❌ Runtime thread dayandı: {exc}", flush=True)
        finally:
            if proactive_scheduler:
                proactive_scheduler.stop()
            # Dashboard və React UI EVA Live session-dan müstəqildir.
            # Gemini/runtime xətası browser-in məlumat kanalını bağlamamalıdır.

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()
