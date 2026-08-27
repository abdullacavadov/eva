"""EVA üçün Gemini Live sessiyasının köməkçi idarəedicisi."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager

from google import genai
from google.genai import types


DEFAULT_CONNECTION_STATUS_CALLBACK: Callable[[str, str | None], None] | None = None


class _ResilientLiveSession:
    """Gemini Live bağlantısını runtime-u dayandırmadan yenidən quran proxy."""

    def __init__(self, manager: "LiveSessionManager", config):
        self._manager = manager
        self._config = config
        self._client = None
        self._context = None
        self._session = None
        self._resume_handle: str | None = manager.resume_handle
        self._closed = False
        self._reconnect_lock = asyncio.Lock()

    @property
    def _session_config(self):
        """Mövcud resume handle-ı saxla; Gemini API üçün transparent rejim istifadə etmə."""
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
        if code is None:
            return None
        try:
            return int(code)
        except (TypeError, ValueError):
            return None

    async def _reconnect(self, *, force_fresh: bool = False, reason: str | None = None):
        async with self._reconnect_lock:
            if self._closed:
                raise RuntimeError("Live session bağlanıb.")
            if self._session is not None:
                await self._close_current()
            if force_fresh:
                self._clear_resume_handle()

            self._notify_status("reconnecting", reason)
            delay = 1.0
            while not self._closed:
                try:
                    await self._connect(clear_handle_on_failure=True)
                    self._notify_status("connected", None)
                    print("[E.V.A] 🔁 Gemini Live bağlantısı bərpa edildi.", flush=True)
                    return
                except Exception as exc:
                    self._notify_status("disconnected", str(exc))
                    print(f"[E.V.A] ⚠️ Live reconnect uğursuz oldu: {exc}", flush=True)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2.0, 8.0)
        raise RuntimeError("Live session bağlanıb.")

    async def __aenter__(self):
        await self._connect(clear_handle_on_failure=True)
        self._notify_status("connected", None)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True
        await self._close_current()
        return False

    async def receive(self):
        """Mesajları verir; socket qırılsa eyni runtime daxilində reconnect edir."""
        while not self._closed:
            try:
                session = self._session
                if session is None:
                    await self._reconnect()
                    continue
                async for message in session.receive():
                    update = getattr(message, "session_resumption_update", None)
                    if update is not None:
                        resumable = bool(getattr(update, "resumable", False))
                        handle = getattr(update, "new_handle", None)
                        if resumable and handle:
                            self._resume_handle = str(handle)
                            self._manager.resume_handle = self._resume_handle
                    yield message
                if not self._closed:
                    await self._reconnect(force_fresh=True, reason="Gemini Live bağlantısı bağlandı və bağlandı (1000).")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._closed:
                    raise
                code = self._close_code(exc)
                if code == 1000:
                    self._clear_resume_handle()
                    reason = "Gemini Live bağlantısı normal şəkildə bağlandı (1000); yeni sessiya açılır."
                    self._notify_status("disconnected", reason)
                    await self._reconnect(force_fresh=True, reason=reason)
                    continue
                reason = str(exc)
                self._notify_status("disconnected", reason)
                print(f"[E.V.A] ⚠️ Live receive bağlantısı kəsildi: {exc}", flush=True)
                await self._reconnect(reason=reason)

    async def _call_with_reconnect(self, method_name: str, **kwargs):
        last_error = None
        for _ in range(2):
            try:
                session = self._session
                if session is None:
                    await self._reconnect()
                    session = self._session
                return await getattr(session, method_name)(**kwargs)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                if self._closed:
                    raise
                code = self._close_code(exc)
                if code == 1000:
                    self._clear_resume_handle()
                await self._reconnect(force_fresh=code == 1000, reason=str(exc))
        raise last_error  # type: ignore[misc]

    async def send_realtime_input(self, **kwargs):
        return await self._call_with_reconnect("send_realtime_input", **kwargs)

    async def send_client_content(self, **kwargs):
        return await self._call_with_reconnect("send_client_content", **kwargs)

    async def send_tool_response(self, **kwargs):
        return await self._call_with_reconnect("send_tool_response", **kwargs)


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

    def _set_resume_handle(self, value: str | None) -> None:
        self._resume_handles[self._manager_key] = value
        self._resume_handle = value

    def create_client(self) -> genai.Client:
        """EVA-nın Live API versiyası ilə Gemini client yaradır."""
        return genai.Client(
            api_key=self.api_key,
            http_options={"api_version": "v1alpha"},
        )

    @asynccontextmanager
    async def connect(self, config):
        """Runtime-u dayandırmadan Live socket reconnect edə bilən session verir."""
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
