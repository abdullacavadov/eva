from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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

    def __init__(self, user_data_dir: str, headless: bool = False) -> None:
        self.user_data_dir = user_data_dir
        self.headless = headless
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

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
        self._context = self._playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            channel="chrome",
            headless=self.headless,
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
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
