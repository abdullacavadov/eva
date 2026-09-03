"""One-shot, argument-bound confirmations for risky EVA actions."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

_PENDING: dict[str, dict[str, Any]] = {}
DEFAULT_TTL_SECONDS = 300


def _fingerprint(action: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"action": action, "payload": payload}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_confirmation(action: str, payload: dict[str, Any], *, ttl: int = DEFAULT_TTL_SECONDS) -> str:
    token = uuid.uuid4().hex
    _PENDING[token] = {
        "action": str(action),
        "payload": dict(payload),
        "fingerprint": _fingerprint(action, payload),
        "expires": time.time() + max(1, int(ttl)),
    }
    return token


def get_confirmation(token: str) -> tuple[str, dict[str, Any]] | None:
    """Return a pending confirmation without consuming it."""
    token = str(token or "").strip()
    record = _PENDING.get(token)
    if record is None:
        return None
    if time.time() > record["expires"]:
        _PENDING.pop(token, None)
        return None
    return str(record["action"]), dict(record["payload"])


def consume_confirmation(token: str, action: str, payload: dict[str, Any]) -> None:
    token = str(token or "").strip()
    record = _PENDING.pop(token, None)
    if record is None:
        raise ValueError("Təsdiq tapılmadı və ya artıq istifadə olunub.")
    if time.time() > record["expires"]:
        raise ValueError("Təsdiqin müddəti bitib; əməliyyatı yenidən hazırla.")
    if record["action"] != action or record["fingerprint"] != _fingerprint(action, payload):
        raise ValueError("Təsdiq başqa əməliyyata aid olduğu üçün rədd edildi.")


def clear_expired() -> None:
    now = time.time()
    for token, record in list(_PENDING.items()):
        if now > record["expires"]:
            _PENDING.pop(token, None)
