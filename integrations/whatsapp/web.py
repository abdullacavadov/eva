from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import time
from typing import TYPE_CHECKING, Any
from urllib.request import urlopen

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page


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
    unread_count: int = 0


class WhatsAppWebBridge:
    """Read-only adapter for data currently rendered by WhatsApp Web."""

    def __init__(self, user_data_dir: str, headless: bool = False, cdp_url: str | None = None) -> None:
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.cdp_url = cdp_url or os.getenv("EVA_WHATSAPP_CDP_URL")
        self._playwright = None
        self._browser: Browser | None = None
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

        self._browser = self._connect_cdp_with_retry(cdp_url)
        contexts = self._browser.contexts
        if not contexts:
            raise RuntimeError("WhatsApp Chrome-da browser context tapılmadı.")
        self._context = contexts[0]
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
            self._print_dom_diagnostics()
            raise RuntimeError("WhatsApp Web UI render timeout.") from exc

    def _print_dom_diagnostics(self) -> None:
        page = self._require_page()
        print(f"[WhatsApp] URL: {page.url}")
        print(f"[WhatsApp] Title: {page.title()!r}")
        selectors = (
            '[data-testid="cell-frame-container"]',
            '[data-testid="chat-list"]',
            '[data-testid="conversation-header"]',
            '[contenteditable="true"]',
            '[role="listitem"]',
        )
        for selector in selectors:
            try:
                print(f"[WhatsApp] {selector}: {page.locator(selector).count()}")
            except Exception as exc:
                print(f"[WhatsApp] {selector}: diagnostic error: {exc}")

        try:
            snapshot = page.locator("body").inner_text(timeout=3000)
            print("[WhatsApp] BODY TEXT BEGIN")
            print(snapshot[:5000])
            print("[WhatsApp] BODY TEXT END")
        except Exception as exc:
            print(f"[WhatsApp] body diagnostic error: {exc}")

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

    def _connect_cdp_with_retry(self, cdp_url: str) -> Browser:
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
        items = page.locator('[data-testid="cell-frame-container"]')
        if not items.count():
            self._print_dom_diagnostics()
            return conversations

        for item in items.all():
            raw_title = self._text(item, '[data-testid="cell-frame-title"]')
            if not raw_title:
                continue

            title, unread_count = self._parse_conversation_title(raw_title)
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
                    unread_count=unread_count,
                )
            )

        return conversations

    @staticmethod
    def _parse_conversation_title(raw_title: str) -> tuple[str, int]:
        text = (raw_title or "").strip()
        match = re.match(r"^\s*(?:Непрочитанные сообщения|Unread messages):\s*(\d+)\s*\n+(.+?)\s*$", text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(2).strip(), int(match.group(1))

        match = re.match(r"^\s*(\d+)\s+непрочитанное(?:\s+сообщение|\s+сообщения|\s+сообщений)?\s*\n+(.+?)\s*$", text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(2).strip(), int(match.group(1))

        return text, 0

    def get_visible_messages(self) -> list[WhatsAppVisibleMessage]:
        page = self._require_page()
        conversation_id = self._current_conversation_id(page)
        if not conversation_id:
            return []

        messages: list[WhatsAppVisibleMessage] = []
        for index, item in enumerate(page.locator('[data-testid="msg-container"]').all()):
            message_id = item.get_attribute("data-id") or ""
            content = self._text(item, '[data-testid="selectable-text"]')
            sender = self._text(item, '[data-testid="author"]')
            timestamp = self._text(item, '[data-testid="msg-meta"]')
            direction = self._message_direction(item)

            if self._is_emoji_only(content):
                content = "Emoji mesajı"
            elif not content:
                content = self._message_media_label(item)

            if not message_id:
                message_id = f"{conversation_id}:dom-{index}:{sender}:{timestamp}:{direction}"

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

        return self._sort_messages(messages)

    @staticmethod
    def _message_direction(item: Any) -> str:
        if item.locator('[data-testid="msg-outgoing"]').count():
            return "outgoing"

        try:
            markers = item.evaluate(
                """el => {
                    const values = [];
                    for (let node = el; node && node !== document.body; node = node.parentElement) {
                        values.push(node.getAttribute('data-testid') || '');
                        values.push(node.getAttribute('data-icon') || '');
                        values.push(node.className && typeof node.className === 'string' ? node.className : '');
                        if (values.length > 60) break;
                    }
                    return values.join(' ');
                }"""
            )
        except Exception:
            markers = ""

        if re.search(r"(?:^|[\s_-])message-out(?:[\s_-]|$)", str(markers)):
            return "outgoing"
        if re.search(r"(?:^|[\s_-])message-in(?:[\s_-]|$)", str(markers)):
            return "incoming"
        return "incoming"

    @staticmethod
    def _message_media_label(item: Any) -> str:
        if item.locator('[data-testid="ptt-status"]').count() or item.locator('audio').count():
            return "Səsli mesaj"
        if item.locator('video').count():
            return "Video mesajı"
        if item.locator('img').count():
            return "Şəkil mesajı"
        if item.locator('[data-testid="addon-bubble-container"]').count():
            return "Media mesajı"
        return ""

    @staticmethod
    def _is_emoji_only(content: str) -> bool:
        text = content.strip()
        if not text:
            return False
        emoji_ranges = (
            (0x1F000, 0x1FAFF),
            (0x2600, 0x27BF),
            (0x2300, 0x23FF),
        )
        meaningful = [char for char in text if not char.isspace() and char not in "\uFE0F\u200D"]
        return bool(meaningful) and all(
            any(start <= ord(char) <= end for start, end in emoji_ranges)
            for char in meaningful
        )

    @staticmethod
    def _sort_messages(messages: list[WhatsAppVisibleMessage]) -> list[WhatsAppVisibleMessage]:
        def key(message: WhatsAppVisibleMessage) -> tuple[int, int]:
            match = re.search(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", message.timestamp)
            if not match:
                return (1, 0)
            hour, minute = int(match.group(1)), int(match.group(2))
            return (0, hour * 60 + minute)

        return [
            message
            for _, message in sorted(
                enumerate(messages),
                key=lambda pair: (*key(pair[1]), pair[0]),
            )
        ]

    def close(self) -> None:
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

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
