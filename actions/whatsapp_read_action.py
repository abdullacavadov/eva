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


def read_whatsapp_messages() -> dict:
    bridge = _bridge()
    seen_file = os.getenv("EVA_WHATSAPP_SEEN_FILE") or str(DEFAULT_SEEN_FILE)
    try:
        bridge.connect()
        return read_visible_whatsapp_messages(bridge, seen_file)
    finally:
        bridge.close()
