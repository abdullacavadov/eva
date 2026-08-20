from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import time
from typing import TYPE_CHECKING, Any
from urllib.request import urlopen

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page


@dataclass(frozen=True)
class WhatsAppVisibleMessage:
    message_id: str
    conversation_id: str
    sender: str
    sender_phone: str
    content: str
    timestamp: str
    direction: str


@dataclass(frozen=True)
class WhatsAppVisibleConversation:
    conversation_id: str
    title: str
    contact_name: str
    contact_phone: str
    last_message: str
    last_message_timestamp: str


class WhatsAppWebBridge:
    """Read-only adapter for data currently rendered by WhatsApp Web."""

    def __init__(self, user_data_dir: str, headless: bool = False, cdp_url: str | None = None) -> None:
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.cdp_url = cdp_url or os.getenv("EVA_WHATSAPP_CDP_URL")
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._chrome_process: subprocess.Popen[bytes] | None = None

    def connect(self) -> None:
        if self._page is not None:
            return

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright quraşdırılmayıb. requirements.txt-dən quraşdırın."
            ) from exc

        self._playwright = sync_playwright().start()
        cdp_url = self.cdp_url or "http://127.0.0.1:9222"

        if self.cdp_url is None and not self._cdp_available(cdp_url):
            self._start_eva_chrome(cdp_url)

        self._context = self._connect_cdp_with_retry(cdp_url)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        if self._page.url in ("", "about:blank"):
            self._page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        try:
            self._page.wait_for_function(
                """() => Boolean(
                    document.querySelector('[data-testid="cell-frame-container"]') ||
                    document.querySelector('[data-testid="conversation-header"]') ||
                    document.querySelector('[data-testid="chat-list"]') ||
                    document.querySelector('[contenteditable="true"]')
                )""",
                timeout=120_000,
            )
        except Exception as exc:
            print("[WhatsApp] UI render timeout")
            print(f"[WhatsApp] URL: {self._page.url}")
            print(f"[WhatsApp] Title: {self._page.title()!r}")
            print(f"[WhatsApp] #app: {self._page.locator('#app').count() > 0}")
            for selector in (
                '[data-testid="cell-frame-container"]',
                '[data-testid="conversation-header"]',
                '[data-testid="chat-list"]',
                '[contenteditable="true"]',
            ):
                print(f"[WhatsApp] {selector}: {self._page.locator(selector).count()}")
            raise RuntimeError("WhatsApp Web UI render timeout.") from exc

    def _start_eva_chrome(self, cdp_url: str) -> None:
        port = cdp_url.rsplit(":", 1)[-1]
        chrome = os.getenv("EVA_WHATSAPP_CHROME") or self._find_chrome()
        profile_dir = Path(self.user_data_dir).expanduser().resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)

        args = [
            chrome,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "https://web.whatsapp.com",
        ]
        if self.headless:
            args.insert(1, "--headless=new")

        self._chrome_process = subprocess.Popen(args)

    def _connect_cdp_with_retry(self, cdp_url: str) -> BrowserContext:
        last_exc: Exception | None = None
        for _ in range(60):
            try:
                return self._playwright.chromium.connect_over_cdp(cdp_url)
            except Exception as exc:
                last_exc = exc
                time.sleep(0.5)
        raise RuntimeError(f"WhatsApp Chrome CDP qoşulmadı: {cdp_url}") from last_exc

    @staticmethod
    def _cdp_available(cdp_url: str) -> bool:
        try:
            with urlopen(f"{cdp_url}/json/version", timeout=1) as response:
                return response.status == 200
        except Exception:
            return False

    @staticmethod
    def _find_chrome() -> str:
        candidates = (
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        )
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        raise RuntimeError("Google Chrome tapılmadı. EVA_WHATSAPP_CHROME təyin edin.")

    def get_visible_conversations(self) -> list[WhatsAppVisibleConversation]:
        page = self._require_page()
        conversations: list[WhatsAppVisibleConversation] = []

        for item in page.locator('[data-testid="cell-frame-container"]').all():
            title = self._text(item, '[data-testid="cell-frame-title"]')
            if not title:
                continue

            conversation_id = item.get_attribute("data-id") or title
            last_message = self._text(item, '[data-testid="last-msg"]')
            timestamp = self._text(item, '[data-testid="last-msg-time"]')

            conversations.append(
                WhatsAppVisibleConversation(
                    conversation_id=conversation_id,
                    title=title,
                    contact_name=title,
                    contact_phone="",
                    last_message=last_message,
                    last_message_timestamp=timestamp,
                )
            )

        return conversations

    def get_visible_messages(self) -> list[WhatsAppVisibleMessage]:
        page = self._require_page()
        conversation_id = self._current_conversation_id(page)
        if not conversation_id:
            return []

        messages: list[WhatsAppVisibleMessage] = []
        for item in page.locator('[data-testid="msg-container"]').all():
            message_id = item.get_attribute("data-id") or ""
            content = self._text(item, '[data-testid="selectable-text"]')
            if not content:
                continue

            sender = self._text(item, '[data-testid="msg-meta"]')
            timestamp = self._text(item, '[data-testid="msg-time"]')
            direction = "outgoing" if item.locator('[data-testid="msg-outgoing"]').count() else "incoming"

            if not message_id:
                message_id = f"{conversation_id}:{timestamp}:{sender}:{content}"

            messages.append(
                WhatsAppVisibleMessage(
                    message_id=message_id,
                    conversation_id=conversation_id,
                    sender=sender,
                    sender_phone="",
                    content=content,
                    timestamp=timestamp,
                    direction=direction,
                )
            )

        return messages

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
        self._context = None
        self._page = None
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = None

    def _require_page(self) -> Page:
        if self._page is None:
            raise RuntimeError("WhatsApp Web bridge qoşulmayıb.")
        return self._page

    @staticmethod
    def _text(item: Any, selector: str) -> str:
        locator = item.locator(selector)
        if not locator.count():
            return ""
        return (locator.first.inner_text() or "").strip()

    @staticmethod
    def _current_conversation_id(page: Page) -> str:
        header = page.locator('[data-testid="conversation-header"]')
        if header.count():
            return (header.first.inner_text() or "").strip()
        return ""
