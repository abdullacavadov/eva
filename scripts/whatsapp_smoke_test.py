from __future__ import annotations

import argparse
from pathlib import Path

from integrations.whatsapp.web import WhatsAppWebBridge


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only WhatsApp Web DOM smoke test")
    parser.add_argument(
        "--profile",
        default=".eva/whatsapp-profile",
        help="Persistent Chromium profile directory",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without a visible window",
    )
    args = parser.parse_args()

    bridge = WhatsAppWebBridge(user_data_dir=str(Path(args.profile)), headless=args.headless)
    try:
        bridge.connect()
        print("WhatsApp Web opened.")
        print("If a QR code is shown, scan it in the browser. Waiting 20 seconds...")
        bridge._require_page().wait_for_timeout(20_000)

        conversations = bridge.get_visible_conversations()
        messages = bridge.get_visible_messages()

        print(f"Visible conversations: {len(conversations)}")
        for conversation in conversations[:10]:
            print(
                "CONVERSATION | "
                f"id={conversation.conversation_id!r} | "
                f"title={conversation.title!r} | "
                f"last={conversation.last_message!r}"
            )

        print(f"Visible messages in current conversation: {len(messages)}")
        for message in messages[-20:]:
            print(
                "MESSAGE | "
                f"id={message.message_id!r} | "
                f"conversation={message.conversation_id!r} | "
                f"sender={message.sender!r} | "
                f"timestamp={message.timestamp!r} | "
                f"direction={message.direction!r} | "
                f"content={message.content!r}"
            )

        return 0
    finally:
        bridge.close()


if __name__ == "__main__":
    raise SystemExit(main())
