"""React UI üçün EVA runtime WebSocket körpüsü."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from queue import Empty, Queue
from typing import Any

from websockets.exceptions import ConnectionClosed
from websockets.sync.server import Server, ServerConnection, serve


class UiBridge:
    """Mövcud desktop EVA runtime-ını lokal React UI-a bağlayır."""

    _CLIENT_QUEUE_SIZE = 256
    _MAX_HISTORY = 200
    _STOP = object()

    def __init__(self, ui, tool_executor=None):
        self.ui = ui
        self.host = os.getenv("EVA_UI_WS_HOST", "127.0.0.1")
        self.port = int(os.getenv("EVA_UI_WS_PORT", "8765"))
        self._clients: set[ServerConnection] = set()
        self._client_queues: dict[ServerConnection, Queue] = {}
        self._clients_lock = threading.Lock()
        self._server: Server | None = None
        self._thread: threading.Thread | None = None
        self._last_state: str | None = None
        self._conversation_history: list[dict[str, Any]] = []
        self._activity_history: list[dict[str, Any]] = []
        self._last_context: dict[str, Any] | None = None
        self._control_state: dict[str, Any] = {
            "paused": False,
            "camera_active": False,
            "microphone_muted": False,
        }
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

        # Kamera həm UI düyməsindən, həm də EVA-nın toggle_webcam tool-undan
        # dəyişə bilər. Hər iki dəyişiklik eyni WebSocket state-ə yayımlanır.
        original_set_webcam_active = getattr(self.ui, "set_webcam_active", None)
        if callable(original_set_webcam_active):
            def set_webcam_active(active: bool):
                active = bool(active)
                original_set_webcam_active(active)
                self._control_state["camera_active"] = active
                self.emit("control.state", control={"camera_active": active})

            self.ui.set_webcam_active = set_webcam_active

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

    def _queue_message(self, queue: Queue, message: str) -> None:
        try:
            queue.put_nowait(message)
        except Exception:
            try:
                queue.get_nowait()
            except Empty:
                pass
            try:
                queue.put_nowait(message)
            except Exception:
                pass

    def _snapshot(self) -> dict[str, Any]:
        with self._clients_lock:
            return {
                "state": self._last_state,
                "messages": list(self._conversation_history),
                "activities": list(self._activity_history),
                "context": self._last_context,
                "control": dict(self._control_state),
            }

    def emit(self, event_type: str, **payload: Any) -> None:
        """Hadisəni bütün WebSocket client-lərinə runtime-u bloklamadan yayımlayır."""
        event = {"type": event_type, **payload}
        if event_type == "state.changed":
            self._last_state = str(payload.get("state") or "") or None
        elif event_type in {"conversation.user", "conversation.assistant"}:
            self._conversation_history.append(event)
            del self._conversation_history[:-self._MAX_HISTORY]
        elif event_type == "activity.created":
            activity = payload.get("activity")
            if isinstance(activity, dict):
                self._activity_history.append(activity)
                del self._activity_history[:-self._MAX_HISTORY]
        elif event_type == "context.updated":
            context = payload.get("context")
            if isinstance(context, dict):
                self._last_context = context
        elif event_type == "control.state":
            control = payload.get("control")
            if isinstance(control, dict):
                self._control_state.update(control)
        message = json.dumps(event, ensure_ascii=False)
        with self._clients_lock:
            queues = tuple(self._client_queues.values())
        for queue in queues:
            self._queue_message(queue, message)

    def _client_sender(self, websocket: ServerConnection, queue: Queue) -> None:
        while True:
            try:
                message = queue.get()
            except Exception:
                return
            if message is self._STOP:
                return
            try:
                websocket.send(message)
            except (ConnectionClosed, OSError):
                return
            except Exception:
                return

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
        queue: Queue = Queue(maxsize=self._CLIENT_QUEUE_SIZE)
        sender = threading.Thread(
            target=self._client_sender,
            args=(websocket, queue),
            name="eva-ui-ws-sender",
            daemon=True,
        )
        with self._clients_lock:
            self._clients.add(websocket)
            self._client_queues[websocket] = queue
            snapshot = {
                "state": self._last_state,
                "messages": list(self._conversation_history),
                "activities": list(self._activity_history),
                "context": self._last_context,
                "control": dict(self._control_state),
            }
        sender.start()
        self._queue_message(queue, json.dumps({"type": "connection.ready"}))
        self._queue_message(queue, json.dumps({"type": "runtime.snapshot", **snapshot}, ensure_ascii=False))
        try:
            for raw_message in websocket:
                self._handle_message(websocket, raw_message)
        except ConnectionClosed:
            pass
        finally:
            with self._clients_lock:
                self._clients.discard(websocket)
                self._client_queues.pop(websocket, None)
            self._queue_message(queue, self._STOP)

    def _handle_control_command(self, websocket: ServerConnection, command: str) -> None:
        allowed = {"shutdown", "pause", "camera", "microphone"}
        if command not in allowed:
            websocket.send(json.dumps({"type": "bridge.error", "message": "Naməlum idarəetmə əmri."}, ensure_ascii=False))
            return

        callback: Callable[[str], dict[str, Any] | None] | None = getattr(self.ui, "on_control_command", None)
        if callback is None:
            websocket.send(json.dumps({"type": "bridge.error", "message": "EVA control callback-i hazır deyil."}, ensure_ascii=False))
            return

        try:
            control = callback(command) or {}
            if isinstance(control, dict):
                self._control_state.update(control)
            self.emit("control.state", control=dict(self._control_state))
        except Exception as exc:
            websocket.send(json.dumps({"type": "bridge.error", "message": str(exc)}, ensure_ascii=False))

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
        if message_type == "control.command":
            self._handle_control_command(websocket, str(message.get("command") or "").strip().lower())
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
