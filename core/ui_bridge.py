"""React UI üçün EVA runtime WebSocket körpüsü."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from typing import Any

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed


class UiBridge:
    """EVA runtime hadisələrini lokal React UI-a çatdırır."""

    def __init__(self, on_command: Callable[[str], None]):
        self.host = os.getenv("EVA_UI_WS_HOST", "127.0.0.1")
        self.port = int(os.getenv("EVA_UI_WS_PORT", "8765"))
        self.on_command = on_command
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: Server | None = None
        self._clients: set[ServerConnection] = set()
        self._last_state: str | None = None

    async def start(self) -> None:
        """WebSocket server-i EVA-nın əsas asyncio loop-unda başladır."""
        if self._server is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._server = await serve(self._handle_client, self.host, self.port)
        print(f"[E.V.A] 🌐 UI WebSocket: ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """UI WebSocket server-ini təhlükəsiz bağlayır."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._clients.clear()
        self._loop = None

    def emit(self, event_type: str, **payload: Any) -> None:
        """Hadisəni WebSocket client-lərinə qeyri-bloklayıcı göndərir."""
        event = {"type": event_type, **payload}
        if event_type == "state.changed":
            self._last_state = str(payload.get("state") or "") or None
        if not self._loop or self._server is None:
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._broadcast(event))
        )

    async def _broadcast(self, event: dict[str, Any]) -> None:
        if not self._clients:
            return
        message = json.dumps(event, ensure_ascii=False)
        stale: list[ServerConnection] = []
        for client in tuple(self._clients):
            try:
                await client.send(message)
            except ConnectionClosed:
                stale.append(client)
        for client in stale:
            self._clients.discard(client)

    async def _handle_client(self, websocket: ServerConnection) -> None:
        self._clients.add(websocket)
        try:
            await websocket.send(json.dumps({"type": "connection.ready"}))
            if self._last_state:
                await websocket.send(json.dumps({"type": "state.changed", "state": self._last_state}))
            async for raw_message in websocket:
                await self._handle_message(websocket, raw_message)
        except ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)

    async def _handle_message(self, websocket: ServerConnection, raw_message: str | bytes) -> None:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8", errors="replace")
        try:
            message = json.loads(raw_message)
        except (TypeError, json.JSONDecodeError):
            await websocket.send(json.dumps({"type": "bridge.error", "message": "Yanlış JSON mesajı."}, ensure_ascii=False))
            return

        if not isinstance(message, dict):
            await websocket.send(json.dumps({"type": "bridge.error", "message": "Mesaj obyekti tələb olunur."}, ensure_ascii=False))
            return

        message_type = str(message.get("type") or "")
        if message_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
            return

        if message_type != "conversation.send":
            await websocket.send(json.dumps({"type": "bridge.error", "message": "Dəstəklənməyən UI hadisəsi."}, ensure_ascii=False))
            return

        text = str(message.get("text") or "").strip()
        if not text:
            return
        try:
            self.on_command(text)
        except Exception as exc:
            await websocket.send(json.dumps({"type": "bridge.error", "message": str(exc)}, ensure_ascii=False))
