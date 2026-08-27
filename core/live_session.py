"""EVA üçün Gemini Live sessiyasının köməkçi idarəedicisi."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager

from google import genai
from google.genai import types


DEFAULT_CONNECTION_STATUS_CALLBACK: Callable[[str, str | None], None] | None = None


class _ResilientLiveSession:
    """Gemini Live socket lifecycle-ını outer runtime-a ötürən nazik proxy."""

    def __init__(self, manager: "LiveSessionManager", config):
        self._manager = manager
        self._config = config
        self._client = None
        self._context = None
        self._session = None
        self._resume_handle: str | None = manager.resume_handle
        self._closed = False

    @property
    def _session_config(self):
        if not self._resume_handle:
            return self._config
        resume = types.SessionResumptionConfig(handle=self._resume_handle)
        if hasattr(self._config, "model_copy"):
            return self._config.model_copy(update={"session_resumption": resume})
        if isinstance(self._config, dict):
            config = dict(self._config)
            config["session_resumption"] = resume
            return config
        return self._config

    def _clear_resume_handle(self) -> None:
        self._resume_handle = None
        self._manager.resume_handle = None

    async def _connect(self, *, clear_handle_on_failure: bool = False):
        if self._closed:
            raise RuntimeError("Live session bağlanıb.")
        try:
            self._client = self._manager.create_client()
            self._context = self._client.aio.live.connect(
                model=self._manager.model,
                config=self._session_config,
            )
            self._session = await self._context.__aenter__()
        except Exception:
            await self._close_current()
            if clear_handle_on_failure and self._resume_handle:
                self._clear_resume_handle()
                self._client = self._manager.create_client()
                self._context = self._client.aio.live.connect(
                    model=self._manager.model,
                    config=self._session_config,
                )
                self._session = await self._context.__aenter__()
            else:
                raise

    async def _close_current(self):
        context = self._context
        self._context = None
        self._session = None
        self._client = None
        if context is not None:
            try:
                await context.__aexit__(None, None, None)
            except Exception:
                pass

    def _notify_status(self, status: str, detail: str | None = None) -> None:
        try:
            self._manager.on_connection_status(status, detail)
        except Exception:
            pass

    @staticmethod
    def _close_code(exc: Exception) -> int | None:
        code = getattr(exc, "code", None)
        try:
            return int(code) if code is not None else None
        except (TypeError, ValueError):
            return None

    async def __aenter__(self):
        await self._connect(clear_handle_on_failure=True)
        self._notify_status("connected")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True
        await self._close_current()
        return False

    @staticmethod
    def _update_resume_handle(manager: "LiveSessionManager", current_handle: str | None, message):
        update = getattr(message, "session_resumption_update", None)
        if update is None:
            return current_handle
        if bool(getattr(update, "resumable", False)):
            handle = getattr(update, "new_handle", None)
            if handle:
                current_handle = str(handle)
                manager.resume_handle = current_handle
        return current_handle

    async def receive(self):
        if self._closed:
            raise RuntimeError("Live session bağlanıb.")
        session = self._session
        if session is None:
            raise RuntimeError("Gemini Live session mövcud deyil.")
        receive_one = getattr(session, "_receive", None)
        if receive_one is None:
            raise RuntimeError("Gemini Live SDK _receive() interfeysini təqdim etmir.")
        try:
            while not self._closed:
                message = await receive_one()
                if message is None:
                    reason = "Gemini Live server bağlantını bağladı."
                    self._notify_status("disconnected", reason)
                    raise RuntimeError(reason)
                self._resume_handle = self._update_resume_handle(
                    self._manager, self._resume_handle, message
                )
                yield message
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if self._closed:
                raise
            code = self._close_code(exc)
            if code == 1000:
                self._clear_resume_handle()
                reason = "Gemini Live bağlantısı normal şəkildə bağlandı (1000)."
            else:
                reason = str(exc)
            self._notify_status("disconnected", reason)
            raise RuntimeError(f"Gemini Live bağlantısı kəsildi: {reason}") from exc

    async def _call(self, method_name: str, **kwargs):
        if self._closed:
            raise RuntimeError("Live session bağlanıb.")
        session = self._session
        if session is None:
            raise RuntimeError("Gemini Live session mövcud deyil.")
        try:
            return await getattr(session, method_name)(**kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if self._closed:
                raise
            code = self._close_code(exc)
            if code == 1000:
                self._clear_resume_handle()
            self._notify_status("disconnected", str(exc))
            raise RuntimeError(f"Gemini Live bağlantısı kəsildi: {exc}") from exc

    async def send_realtime_input(self, **kwargs):
        return await self._call("send_realtime_input", **kwargs)

    async def send_client_content(self, **kwargs):
        # Gemini 3.1 Live-da canlı mətn yeniləmələri realtime input ilə göndərilir.
        text = kwargs.get("text")
        if text is None:
            turns = kwargs.get("turns") or {}
            parts = turns.get("parts") if isinstance(turns, dict) else None
            if parts:
                text = " ".join(
                    str(part.get("text", "")) for part in parts if isinstance(part, dict)
                ).strip()
        if not text:
            return None
        return await self._call("send_realtime_input", text=text)

    async def send_tool_response(self, **kwargs):
        return await self._call("send_tool_response", **kwargs)


class LiveSessionManager:
    """Gemini client yaradılmasını və Live API bağlantısını idarə edir."""

    _resume_handles: dict[str, str | None] = {}

    def __init__(
        self,
        model: str,
        api_key: str,
        on_connection_status: Callable[[str, str | None], None] | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self._manager_key = f"{model}:{api_key}"
        self.resume_handle: str | None = self._resume_handles.get(self._manager_key)
        self.on_connection_status = (
            on_connection_status
            or DEFAULT_CONNECTION_STATUS_CALLBACK
            or (lambda status, detail=None: None)
        )

    def create_client(self) -> genai.Client:
        return genai.Client(
            api_key=self.api_key,
            http_options={"api_version": "v1beta"},
        )

    @asynccontextmanager
    async def connect(self, config):
        # Əvvəlki stability counter səhv olaraq yeni reconnect-ləri bloklayırdı.
        # Real server xətası birbaşa runtime-a ötürülür; reconnect qərarını main.py verir.
        session = _ResilientLiveSession(self, config)
        async with session:
            yield session

    @property
    def resume_handle(self) -> str | None:
        return self._resume_handle

    @resume_handle.setter
    def resume_handle(self, value: str | None) -> None:
        self._resume_handle = value
        if hasattr(self, "_manager_key"):
            self._resume_handles[self._manager_key] = value
