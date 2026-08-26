"""EVA dashboard üçün lokal HTTP data bridge."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from actions.calendar import get_calendar_events
from actions.email import search_emails
from actions.reminder_memory import get_reminders as get_memory_reminders
from actions.reminders import get_reminders as get_tasks
from actions.weather import get_weather_summary

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency fallback
    psutil = None

HOST = os.getenv("EVA_DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("EVA_DASHBOARD_PORT", "8765"))


def _safe_count(result: dict[str, Any]) -> int | None:
    if not isinstance(result, dict) or result.get("status") == "error":
        return None
    count = result.get("count")
    if isinstance(count, int):
        return count
    data = result.get("data")
    return len(data) if isinstance(data, list) else None


def _calendar_today() -> dict[str, Any]:
    return get_calendar_events("today", limit=50)


def _dashboard_payload() -> dict[str, Any]:
    calendar = _calendar_today()
    tasks = get_tasks("today", limit=100)
    reminders = get_memory_reminders("today", limit=100, include_completed=False)
    unread = search_emails("is:unread", limit=1)
    weather = get_weather_summary("Baku")

    system: dict[str, Any] = {
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": None,
        "network": None,
    }
    if psutil is not None:
        try:
            system["cpu_percent"] = round(psutil.cpu_percent(interval=0.15), 1)
        except Exception:
            pass
        try:
            system["memory_percent"] = round(psutil.virtual_memory().percent, 1)
        except Exception:
            pass
        try:
            system["disk_percent"] = round(psutil.disk_usage("C:\\").percent, 1)
        except Exception:
            pass
        try:
            system["network"] = "ONLAYN" if psutil.net_if_stats() else "OFFLAYN"
        except Exception:
            pass

    events = calendar.get("data") or []
    context_items = [
        {
            "id": str(item.get("id", "")),
            "title": item.get("title", "(Adsız tədbir)"),
            "subtitle": str(item.get("start", ""))[:16].replace("T", " · "),
            "source": "Təqvim",
        }
        for item in events[:6]
    ]

    return {
        "ok": True,
        "overview": {
            "calendar_events": _safe_count(calendar),
            "tasks_today": _safe_count(tasks),
            "reminders": _safe_count(reminders),
            "unread_messages": _safe_count(unread),
        },
        "weather": weather,
        "system": system,
        "context": {
            "source": "Google Calendar",
            "title": "Aktiv kontekst",
            "items": context_items,
        },
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/dashboard":
            try:
                self._send_json(200, _dashboard_payload())
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if self.path == "/api/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"ok": False, "error": "Endpoint tapılmadı."})

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve() -> None:
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"[EVA] Dashboard API: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
