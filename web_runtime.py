#!/usr/bin/env python3
"""EVA React runtime launcher without the legacy Tkinter UI."""

import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core.dashboard_api import get_dashboard_data
from core.proactive import ProactiveEngine, ProactiveScheduler
from core.runtime_ui import RuntimeUI
from core.ui_bridge import UiBridge
import core.live_session as live_session_module
from main import JarvisLive

BASE_DIR = Path(__file__).resolve().parent
SFX_DIR = BASE_DIR / "SFX"
_ALLOWED_SFX = {"HUD", "Start", "Think", "Done", "Error"}


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Local dashboard API and React SFX endpoint."""

    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route.startswith("/sfx/"):
            self._serve_sfx(route)
            return
        if route != "/api/dashboard":
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
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return
        except Exception as exc:
            payload = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            try:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return

    def _serve_sfx(self, route: str) -> None:
        name = Path(route.removeprefix("/sfx/")).stem
        if name not in _ALLOWED_SFX:
            self.send_response(404)
            self.end_headers()
            return
        source = SFX_DIR / f"{name}.mp3"
        if not source.is_file():
            self.send_response(404)
            self.end_headers()
            return
        try:
            data = source.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def log_message(self, format, *args):
        return


def _start_dashboard_api() -> ThreadingHTTPServer:
    host = os.getenv("EVA_UI_HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("EVA_UI_HTTP_PORT", "8766"))
    server = ThreadingHTTPServer((host, port), DashboardRequestHandler)
    threading.Thread(target=server.serve_forever, name="eva-dashboard-http", daemon=True).start()
    print(f"[E.V.A] 📊 Dashboard API: http://{host}:{port}/api/dashboard", flush=True)
    return server


def _start_react_frontend() -> subprocess.Popen | None:
    frontend_dir = BASE_DIR / "frontend"
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
    ui = RuntimeUI()
    dashboard_server = _start_dashboard_api()
    frontend_process = _start_react_frontend()

    def runner():
        jarvis = JarvisLive(ui)
        UiBridge(ui, tool_executor=jarvis._tool_executor)

        def on_live_connection_status(status: str, detail: str | None = None):
            if status == "connected":
                ui.set_state("LISTENING")
                ui.write_log("SYS: Gemini Live bağlantısı bərpa edildi.")
                ui.emit_event("connection.ready")
            else:
                reason = detail or "Gemini Live bağlantısı yoxdur."
                ui.set_state("ERROR")
                ui.write_log(f"ERR: Gemini Live bağlantısı yoxdur — {reason}")
                ui.emit_event("bridge.error", message=f"Gemini Live bağlantısı yoxdur — {reason}")

        live_session_module.DEFAULT_CONNECTION_STATUS_CALLBACK = on_live_connection_status

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
            try:
                dashboard_server.shutdown()
            except Exception:
                pass
            if frontend_process and frontend_process.poll() is None:
                try:
                    frontend_process.terminate()
                except Exception:
                    pass

    threading.Thread(target=runner, daemon=True).start()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
