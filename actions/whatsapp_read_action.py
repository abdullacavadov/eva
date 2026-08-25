"""EVA WhatsApp read actions backed by the existing Web read contract."""

from __future__ import annotations

import os
from pathlib import Path

from actions.whatsapp_read import (
    read_visible_whatsapp_conversations,
    read_visible_whatsapp_messages,
)
from integrations.whatsapp.web import WhatsAppWebBridge

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = BASE_DIR / ".eva" / "whatsapp-profile"
DEFAULT_SEEN_FILE = BASE_DIR / ".eva" / "whatsapp-seen.json"


def _bridge() -> WhatsAppWebBridge:
    profile = os.getenv("EVA_WHATSAPP_PROFILE") or str(DEFAULT_PROFILE)
    return WhatsAppWebBridge(user_data_dir=profile)


def read_whatsapp_conversations() -> dict:
    bridge = _bridge()
    try:
        bridge.connect()
        return read_visible_whatsapp_conversations(bridge)
    finally:
        bridge.close()


def read_whatsapp_messages(conversation: str = "", deduplicate: bool = True) -> dict:
    bridge = _bridge()
    seen_file = os.getenv("EVA_WHATSAPP_SEEN_FILE") or str(DEFAULT_SEEN_FILE)
    try:
        bridge.connect()
        if conversation.strip():
            page = bridge._require_page()
            target = conversation.strip().casefold()
            candidates = bridge.get_visible_conversations()

            exact_matches = [
                item
                for item in candidates
                if item.conversation_id.casefold() == target
                or item.title.casefold() == target
            ]
            if len(exact_matches) == 1:
                match = exact_matches[0]
            elif len(exact_matches) > 1:
                return _ambiguous_conversation_result(conversation, exact_matches)
            else:
                partial_matches = [
                    item
                    for item in candidates
                    if target in item.title.casefold()
                ]
                if not partial_matches:
                    return {
                        "type": "whatsapp_message",
                        "status": "error",
                        "query": {"conversation": conversation},
                        "data": [],
                        "count": 0,
                        "selected": None,
                        "meta": {"error": f"WhatsApp söhbəti tapılmadı: {conversation}"},
                    }
                if len(partial_matches) > 1:
                    return _ambiguous_conversation_result(conversation, partial_matches)
                match = partial_matches[0]

            page.locator('[data-testid="cell-frame-container"]').filter(
                has_text=match.title
            ).first.click()
            page.wait_for_timeout(500)

        return read_visible_whatsapp_messages(bridge, seen_file, deduplicate=deduplicate)
    finally:
        bridge.close()


def _ambiguous_conversation_result(conversation: str, matches: list) -> dict:
    return {
        "type": "whatsapp_message",
        "status": "error",
        "query": {"conversation": conversation},
        "data": [
            {
                "id": f"whatsapp:conversation:{item.conversation_id}",
                "conversation_id": item.conversation_id,
                "title": item.title,
                "contact_name": item.contact_name,
                "contact_phone": item.contact_phone,
                "unread_count": item.unread_count,
            }
            for item in matches
        ],
        "count": len(matches),
        "selected": None,
        "meta": {
            "error": f"Bir neçə WhatsApp söhbəti uyğun gəldi: {conversation}",
            "ambiguous": True,
            "candidates": [item.title for item in matches],
        },
    }
