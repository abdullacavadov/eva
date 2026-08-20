from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisibleMessage:
    message_id: str
    conversation_id: str
    sender: str = ""
    sender_phone: str = ""
    content: str = ""
    timestamp: str = ""
    direction: str = "incoming"


@dataclass(frozen=True)
class VisibleConversation:
    conversation_id: str
    title: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    last_message: str = ""
    last_message_timestamp: str = ""


class WhatsAppWebBridge:
    """Read-only Playwright adapter for the currently rendered WhatsApp Web UI."""

    def __init__(self, *, user_data_dir: str | None = None) -> None:
        self.user_data_dir = user_data_dir
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None

    def connect(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright quraşdırılmayıb.") from exc

        self._playwright = sync_playwright().start()
        if self.user_data_dir:
            self._browser = self._playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=False,
            )
            self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=False)
            self._page = self._browser.new_page()

        self._page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded")

    def get_visible_messages(self) -> list[VisibleMessage]:
        """Return only message elements currently rendered by WhatsApp Web.

        DOM selectors are intentionally isolated here because WhatsApp Web's UI is
        not a stable public API and can change independently of EVA's domain layer.
        """
        page = self._require_page()
        elements = page.locator("div.message-in, div.message-out").all()
        messages: list[VisibleMessage] = []

        for element in elements:
            message_id = element.get_attribute("data-id") or ""
            content = self._first_text(element, ["span.selectable-text", "span[dir='auto']"])
            if not message_id or not content:
                continue

            direction = "outgoing" if "message-out" in (element.get_attribute("class") or "") else "incoming"
            conversation_id = self._conversation_id(page)
            if not conversation_id:
                continue

            messages.append(
                VisibleMessage(
                    message_id=message_id,
                    conversation_id=conversation_id,
                    content=content,
                    direction=direction,
                )
            )

        return messages

    def get_visible_conversations(self) -> list[VisibleConversation]:
        """Return conversations currently visible in the chat list."""
        page = self._require_page()
        rows = page.locator("div[role='listitem']").all()
        conversations: list[VisibleConversation] = []

        for row in rows:
            title = self._first_text(row, ["span[title]"])
            if not title:
                continue
            conversations.append(
                VisibleConversation(
                    conversation_id=row.get_attribute("data-id") or title,
                    title=title,
                    contact_name=title,
                )
            )

        return conversations

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None

    def _require_page(self) -> Any:
        if self._page is None:
            raise RuntimeError("WhatsApp Web bridge qoşulmayıb.")
        return self._page

    @staticmethod
    def _first_text(element: Any, selectors: list[str]) -> str:
        for selector in selectors:
            locator = element.locator(selector)
            if locator.count():
                text = locator.first.inner_text().strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _conversation_id(page: Any) -> str:
        header = page.locator("header").first
        return header.get_attribute("data-id") or ""
