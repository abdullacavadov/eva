"""React Settings ekranı üçün təhlükəsiz lokal runtime konfiqurasiya körpüsü."""

from __future__ import annotations

from typing import Any

from app_config import load_app_config, save_app_config


PUBLIC_KEYS = {
    "youtube_channel_handle",
    "voice",
    "sfx_enabled",
    "sfx_volume",
    "proactive_enabled",
    "language",
    "wake_listener_enabled",
    "auto_start",
}
SECRET_KEYS = {"gemini_api_key", "youtube_api_key"}
MASK = "••••"


def _mask_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return f"{MASK}{text[-4:]}"


def _public_settings() -> dict[str, Any]:
    config = load_app_config()
    result = {key: config.get(key) for key in PUBLIC_KEYS}
    for key in SECRET_KEYS:
        result[key] = _mask_secret(config.get(key))
    return result


def _apply_sound_settings(ui, config: dict[str, Any]) -> None:
    sound = getattr(ui, "sound", None)
    if sound is None:
        return
    sound.set_volume(float(config.get("sfx_volume", 20)) / 100.0)
    sound.set_enabled(bool(config.get("sfx_enabled", True)))


def apply_saved_settings(ui) -> None:
    """Yadda saxlanmış runtime parametrlərini UI/runtime yaradıldıqdan sonra tətbiq edir."""
    _apply_sound_settings(ui, load_app_config())


def install_settings_bridge(bridge, ui) -> None:
    """UiBridge-in settings.get/settings.update hadisələrini dəstəkləməsi üçün genişləndirir."""
    original_handle_message = bridge._handle_message

    def handle_message(websocket, raw_message):
        import json

        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8", errors="replace")
        try:
            message = json.loads(raw_message)
        except (TypeError, json.JSONDecodeError):
            return original_handle_message(websocket, raw_message)
        if not isinstance(message, dict):
            return original_handle_message(websocket, raw_message)

        message_type = str(message.get("type") or "")
        if message_type == "settings.get":
            websocket.send(json.dumps({
                "type": "settings.state",
                "settings": _public_settings(),
            }, ensure_ascii=False))
            return

        if message_type == "settings.update":
            requested = message.get("settings")
            if not isinstance(requested, dict):
                websocket.send(json.dumps({
                    "type": "bridge.error",
                    "message": "Settings obyekti tələb olunur.",
                }, ensure_ascii=False))
                return

            updates: dict[str, Any] = {}
            for key in PUBLIC_KEYS:
                if key in requested:
                    updates[key] = requested[key]
            for key in SECRET_KEYS:
                if key in requested:
                    value = str(requested.get(key) or "").strip()
                    if value and not value.startswith(MASK):
                        updates[key] = value

            config = save_app_config(updates)
            _apply_sound_settings(ui, config)
            websocket.send(json.dumps({
                "type": "settings.saved",
                "settings": _public_settings(),
            }, ensure_ascii=False))
            try:
                bridge.emit_activity("Settings yeniləndi", "success")
            except Exception:
                pass
            return

        return original_handle_message(websocket, raw_message)

    bridge._handle_message = handle_message
