"""EVA üçün Gemini Live sessiyasının köməkçi idarəedicisi."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from google import genai
from google.genai import types


class _ResilientLiveSession:
    """Gemini Live bağlantısını tək reconnect lifecycle-ı ilə idarə edən proxy."""

    def __init__(self, manager: "LiveSessionManager", config):
        self._manager = manager
        self._config = config
        self._client = None
        self._context = None
        self._session = None
        self._resume_handle: str | None = manager.resume_handle
        self._closed = False
        self._reconnect_task: asyncio.Task | None = None
        self._reconnect_lock = asyncio.Lock()
        self._reconnect_delay = 1.0

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
                self._resume_handle = None
                self._manager.resume_handle = None
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

    async def _reconnect_impl(self, *, force_fresh: bool = False):
        async with self._reconnect_lock:
            if self._closed:
                raise RuntimeError("Live session bağlanıb.")

            if force_fresh:
                self._resume_handle = None
                self._manager.resume_handle = None

            await self._close_current()

            while not self._closed:
                try:
                    await asyncio.sleep(self._reconnect_delay)
                    await self._connect(clear_handle_on_failure=True)
                    self._reconnect_delay = 1.0
                    print("[E.V.A] 🔁 Gemini Live bağlantısı bərpa edildi.", flush=True)
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    print(f"[E.V.A] ⚠️ Live reconnect uğursuz oldu: {exc}", flush=True)
                    await self._close_current()
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2.0, 8.0)

        raise RuntimeError("Live session bağlanıb.")

    async def _reconnect(self, *, force_fresh: bool = False):
        """Bütün reconnect çağıranları eyni task-ı paylaşır; paralel reconnect yaranmır."""
        if self._closed:
            raise RuntimeError("Live session bağlanıb.")

        task = self._reconnect_task
        if task is None or task.done():
            task = asyncio.create_task(self._reconnect_impl(force_fresh=force_fresh))
            self._reconnect_task = task
        await task

    async def __aenter__(self):
        await self._connect(clear_handle_on_failure=True)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True
        task = self._reconnect_task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._close_current()
        return False

    @staticmethod
    def _is_clean_close(exc: Exception) -> bool:
        """WebSocket 1000 clean close-unu reconnect loopundan ayır."""
        code = getattr(exc, "code", None)
        return code == 1000

    async def receive(self):
        """Mesajları verir; socket qırılsa eyni runtime daxilində tək reconnect edir."""
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
                    await self._reconnect(force_fresh=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._closed:
                    raise
                print(f"[E.V.A] ⚠️ Live receive bağlantısı kəsildi: {exc}", flush=True)
                await self._reconnect(force_fresh=self._is_clean_close(exc))

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
                await self._reconnect(force_fresh=self._is_clean_close(exc))
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

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self._manager_key = f"{model}:{api_key}"
        self.resume_handle: str | None = self._resume_handles.get(self._manager_key)

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
