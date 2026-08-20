from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.whatsapp.web import WhatsAppWebBridge


SELECTOR_PROBES = (
    '[data-testid="cell-frame-container"]',
    '[data-testid="cell-frame-title"]',
    '[data-testid="last-msg"]',
    '[data-testid="last-msg-time"]',
    '[data-testid="msg-container"]',
    '[data-testid="selectable-text"]',
    '[data-testid="msg-meta"]',
    '[data-testid="msg-time"]',
    '[data-testid="conversation-header"]',
    '[data-testid="msg-outgoing"]',
    '[data-testid="chat-list"]',
    '[data-testid="intro"]',
    '[data-testid="qrcode"]',
)


MESSAGE_SELECTOR_CANDIDATES = (
    '[data-testid="msg-container"]',
    '[data-testid="msg-container"] [data-testid="selectable-text"]',
    '[data-testid="msg-container"] [data-testid="msg-meta"]',
    '[data-testid="msg-container"] [data-testid="msg-time"]',
    '[data-id][data-testid="msg-container"]',
    '[data-testid="msg-container"] div[role="row"]',
    '[data-testid="msg-container"] [aria-label]',
)


def print_diagnostics(page) -> None:
    print("\n=== WhatsApp Web diagnostics ===")
    print(f"URL: {page.url}")
    print(f"Title: {page.title()!r}")
    print(f"#app exists: {page.locator('#app').count() > 0}")

    print("Login/session structure:")
    login_probes = (
        "[data-testid='qrcode']",
        "[data-testid='intro']",
        "canvas[aria-label*='QR']",
        "canvas",
        "[contenteditable='true']",
        "[role='application']",
    )
    for selector in login_probes:
        print(f"  {selector}: {page.locator(selector).count()}")

    print("Primary data-testid selector counts:")
    for selector in SELECTOR_PROBES:
        print(f"  {selector}: {page.locator(selector).count()}")

    snapshot = page.locator("body").inner_html()
    max_snapshot_length = 5000
    print("HTML snapshot (first 5000 chars, structure only):")
    print(snapshot[:max_snapshot_length])
    if len(snapshot) > max_snapshot_length:
        print("... [snapshot truncated]")
    print("=== End diagnostics ===\n")


def _message_dom_diagnostics(page) -> dict:
    containers = page.locator('[data-testid="msg-container"]')
    results = []

    for index in range(min(containers.count(), 5)):
        item = containers.nth(index)
        attrs = item.evaluate(
            """el => Object.fromEntries(
                Array.from(el.attributes).map(attr => [attr.name, attr.value])
            )"""
        )
        descendants = item.locator("*")
        tag_names = descendants.evaluate_all(
            """els => Array.from(new Set(els.map(el => el.tagName.toLowerCase())))
                .slice(0, 30)"""
        )
        data_testids = descendants.evaluate_all(
            """els => Array.from(new Set(
                els.map(el => el.getAttribute('data-testid')).filter(Boolean)
            )).slice(0, 30)"""
        )
        results.append(
            {
                "index": index,
                "attributes": attrs,
                "tag_names": tag_names,
                "data_testids": data_testids,
                "descendant_count": descendants.count(),
            }
        )

    selector_counts = {
        selector: page.locator(selector).count()
        for selector in MESSAGE_SELECTOR_CANDIDATES
    }

    return {
        "message_container_count": containers.count(),
        "selector_candidates": selector_counts,
        "sample_elements": results,
    }


def print_message_dom_diagnostics(page, conversations) -> None:
    print("\n=== WhatsApp message DOM diagnostics ===")
    if not conversations:
        print(json.dumps({"status": "no_visible_conversations"}, ensure_ascii=False, indent=2))
        print("=== End message DOM diagnostics ===\n")
        return

    target = page.locator('[data-testid="cell-frame-container"]').first
    target.click()
    page.wait_for_timeout(1500)

    result = _message_dom_diagnostics(page)
    result["status"] = "conversation_opened"
    result["conversation_title_present"] = bool(conversations[0].title)
    result["conversation_header_count"] = page.locator('[data-testid="conversation-header"]').count()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=== End message DOM diagnostics ===\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only WhatsApp Web DOM smoke test")
    parser.add_argument("--profile", default=".eva/whatsapp-profile", help="Persistent Chromium profile directory")
    parser.add_argument("--headless", action="store_true", help="Run Chromium without a visible window")
    args = parser.parse_args()

    bridge = WhatsAppWebBridge(user_data_dir=str(Path(args.profile)), headless=args.headless)
    try:
        bridge.connect()
        page = bridge._require_page()
        print("WhatsApp Web opened.")
        print("If a QR code is shown, scan it in the browser. Waiting 20 seconds...")
        page.wait_for_timeout(20_000)
        print_diagnostics(page)

        conversations = bridge.get_visible_conversations()
        messages = bridge.get_visible_messages()

        print(f"Visible conversations: {len(conversations)}")
        for conversation in conversations[:10]:
            print(
                "CONVERSATION | "
                f"id={conversation.conversation_id!r} | "
                f"title={conversation.title!r} | "
                f"last_message_present={bool(conversation.last_message)}"
            )

        print_message_dom_diagnostics(page, conversations)

        print(f"Visible messages in current conversation: {len(messages)}")
        for message in messages[-20:]:
            print(
                "MESSAGE | "
                f"id_present={bool(message.message_id)} | "
                f"conversation_present={bool(message.conversation_id)} | "
                f"sender_present={bool(message.sender)} | "
                f"timestamp_present={bool(message.timestamp)} | "
                f"direction={message.direction!r} | "
                f"content_present={bool(message.content)}"
            )

        return 0
    finally:
        bridge.close()


if __name__ == "__main__":
    raise SystemExit(main())
