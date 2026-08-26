"""React UI üçün EVA runtime WebSocket körpüsü."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from typing import Any

from websockets.exceptions import ConnectionClosed
from websockets.sync.server import Server, ServerConnection, serve


class UiBridge:
    """Mövcud desktop EVA runtime-ını lokal React UI-a bağlayır."""

    def __init__(self, ui, tool_executor=None):
        self.ui = ui
        self.host = os.getenv("EVA_UI_WS_HOST", "127.0.0.1")
        self.port = int(os.getenv("EVA_UI_WS_PORT", "8765"))
        self._clients: set[ServerConnection] = set()
        self._clients_lock = threading.Lock()
        self._server: Server | None = None
        self._thread: threading.Thread | None = None
        self._last_state: str | None = None
        self._install_ui_hooks()
        if tool_executor is not None:
            self._install_tool_hook(tool_executor)
        self._start_server()

    def _install_ui_hooks(self) -> None:
        self.ui.emit_event = self.emit  # type: ignore[attr-defined]
        original_set_state = self.ui.set_state

        def set_state(state: str):
            original_set_state(state)
            self.emit("state.changed", state=self._normalize_state(state))

        self.ui.set_state = set_state
        original_write_log = self.ui.write_log

        def write_log(text: str):
            original_write_log(text)
            self._emit_log_event(text)

        self.ui.write_log = write_log

    def _install_tool_hook(self, tool_executor) -> None:
        if getattr(tool_executor, "_eva_ui_bridge_wrapped", False):
            return
        original_execute = tool_executor.execute

        async def execute(fc):
            name = str(getattr(fc, "name", "") or "")
            args = dict(getattr(fc, "args", {}) or {})
            self.emit("tool.started", tool=name, args=args)
            try:
                result = await original_execute(fc)
                response = getattr(result, "response", {}) or {}
                value = response.get("result") if isinstance(response, dict) else str(response)
                text = str(value or "")
                failed = any(marker in text.lower() for marker in ("xəta", "error", "mümkün olmadı", "alınmadı"))
                self.emit("tool.completed", tool=name, success=not failed, result=text[:500])
                return result
            except Exception as exc:
                self.emit("tool.completed", tool=name, success=False, result=str(exc)[:500])
                raise

        tool_executor.execute = execute
        tool_executor._eva_ui_bridge_wrapped = True

    @staticmethod
    def _normalize_state(state: str) -> str:
        return {"SPEAKING": "LISTENING", "INITIALISING": "THINKING"}.get(str(state), str(state))

    def _emit_log_event(self, text: str) -> None:
        clean = str(text or "").strip()
        lower = clean.lower()
        if lower.startswith("siz:") or lower.startswith("you:"):
            detail = clean.split(":", 1)[1].strip()
            self.emit("conversation.user", text=detail)
            self.emit_activity("Komanda qəbul edildi", "user", detail)
        elif lower.startswith("e.v.a:") or lower.startswith("ai:"):
            detail = clean.split(":", 1)[1].strip()
            self.emit("conversation.assistant", text=detail)
            self.emit_activity("EVA cavab verdi", "assistant", detail)
        elif lower.startswith("err:"):
            self.emit_activity("Runtime xətası", "error", clean.split(":", 1)[1].strip())
        elif lower.startswith("sys:"):
            self.emit_activity(clean.split(":", 1)[1].strip(), "system")

    def emit_activity(self, text: str, kind: str = "system", detail: str | None = None) -> None:
        activity: dict[str, Any] = {
            "id": f"activity-{time.time_ns()}",
            "time": time.strftime("%H:%M:%S"),
            "text": text,
            "kind": kind,
        }
        if detail:
            activity["detail"] = detail
        self.emit("activity.created", activity=activity)

    def emit(self, event_type: str, **payload: Any) -> None:
        """Hadisəni bütün WebSocket client-lərinə thread-safe yayımlayır."""
        event = {"type": event_type, **payload}
        if event_type == "state.changed":
            self._last_state = str(payload.get("state") or "") or None
        message = json.dumps(event, ensure_ascii=False)
        with self._clients_lock:
            clients = tuple(self._clients)
        stale: list[ServerConnection] = []
        for client in clients:
            try:
                client.send(message)
            except (ConnectionClosed, OSError):
                stale.append(client)
        if stale:
            with self._clients_lock:
                for client in stale:
                    self._clients.discard(client)

    def _start_server(self) -> None:
        def run():
            try:
                with serve(self._handle_client, self.host, self.port) as server:
                    self._server = server
                    print(f"[E.V.A] 🌐 UI WebSocket: ws://{self.host}:{self.port}")
                    server.serve_forever()
            except OSError as exc:
                print(f"[E.V.A] ⚠️ UI WebSocket başlatılmadı: {exc}")
            finally:
                self._server = None

        self._thread = threading.Thread(target=run, name="eva-ui-ws", daemon=True)
        self._thread.start()

    def _handle_client(self, websocket: ServerConnection) -> None:
        with self._clients_lock:
            self._clients.add(websocket)
        try:
            websocket.send(json.dumps({"type": "connection.ready"}))
            if self._last_state:
                websocket.send(json.dumps({"type": "state.changed", "state": self._last_state}))
            for raw_message in websocket:
                self._handle_message(websocket, raw_message)
        except ConnectionClosed:
            pass
        finally:
            with self._clients_lock:
                self._clients.discard(websocket)

    def _handle_message(self, websocket: ServerConnection, raw_message: str | bytes) -> None:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8", errors="replace")
        try:
            message = json.loads(raw_message)
        except (TypeError, json.JSONDecodeError):
            websocket.send(json.dumps({"type": "bridge.error", "message": "Yanlış JSON mesajı."}, ensure_ascii=False))
            return
        if not isinstance(message, dict):
            websocket.send(json.dumps({"type": "bridge.error", "message": "Mesaj obyekti tələb olunur."}, ensure_ascii=False))
            return
        message_type = str(message.get("type") or "")
        if message_type == "ping":
            websocket.send(json.dumps({"type": "pong"}))
            return
        if message_type != "conversation.send":
            websocket.send(json.dumps({"type": "bridge.error", "message": "Dəstəklənməyən UI hadisəsi."}, ensure_ascii=False))
            return
        text = str(message.get("text") or "").strip()
        if not text:
            return
        callback: Callable[[str], None] | None = getattr(self.ui, "on_text_command", None)
        if callback is None:
            websocket.send(json.dumps({"type": "bridge.error", "message": "EVA text command callback-i hazır deyil."}, ensure_ascii=False))
            return
        try:
            callback(text)
        except Exception as exc:
            websocket.send(json.dumps({"type": "bridge.error", "message": str(exc)}, ensure_ascii=False))
