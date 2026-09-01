"""React Settings ekranı üçün təhlükəsiz lokal runtime konfiqurasiya körpüsü."""

from __future__ import annotations

import json
from typing import Any

from app_config import load_app_config, save_app_config
from integrations.google.auth import (
    disconnect_google,
    get_google_account_email,
    get_google_credentials,
    is_google_connected,
)


PUBLIC_KEYS = {
    "youtube_channel_handle", "voice", "sfx_enabled", "sfx_volume",
    "sfx_startup_enabled", "sfx_listening_enabled", "sfx_thinking_enabled",
    "sfx_success_enabled", "sfx_error_enabled", "sfx_notification_enabled",
    "sfx_startup_volume", "sfx_listening_volume", "sfx_thinking_volume",
    "sfx_success_volume", "sfx_error_volume", "sfx_notification_volume",
    "proactive_enabled", "language", "wake_listener_enabled", "auto_start",
    "user_name", "address_style", "response_length", "humor_level",
    "proactivity_level", "voice_tone", "persona_prompt", "voice_volume",
    "speech_speed", "interrupt_enabled", "auto_duck_music", "fallback_voice",
    "orb_style", "particle_density", "particle_speed", "glow_intensity",
    "orb_listening_color", "orb_speaking_color", "orb_thinking_color",
    "orb_muted_color", "particle_animation_enabled", "glow_enabled",
    "pulse_enabled", "audio_reactive_enabled",
}
SECRET_KEYS = {"gemini_api_key", "youtube_api_key"}
MASK = "••••"


def _mask_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return f"{MASK}{text[-4:]}"


def _google_account() -> dict[str, Any]:
    if not is_google_connected():
        return {"connected": False, "email": None}
    email = None
    try:
        email = get_google_account_email()
    except Exception:
        pass
    return {"connected": True, "email": email}


def _public_settings() -> dict[str, Any]:
    config = load_app_config()
    result = {key: config.get(key) for key in PUBLIC_KEYS}
    for key in SECRET_KEYS:
        result[key] = _mask_secret(config.get(key))
    result["google_account"] = _google_account()
    return result


def _send(websocket, event: dict[str, Any]) -> None:
    websocket.send(json.dumps(event, ensure_ascii=False))


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
    """UiBridge-in settings və Google OAuth hadisələrini dəstəkləməsi üçün genişləndirir."""
    original_handle_message = bridge._handle_message

    def handle_message(websocket, raw_message):
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
            _send(websocket, {"type": "settings.state", "settings": _public_settings()})
            return

        if message_type == "google.connect":
            try:
                credentials = get_google_credentials()
                email = get_google_account_email(credentials)
                _send(websocket, {"type": "google.account", "account": {"connected": True, "email": email}})
                try:
                    bridge.emit_activity("Google hesabı qoşuldu", "success", email)
                except Exception:
                    pass
            except Exception as exc:
                _send(websocket, {"type": "bridge.error", "message": f"Google hesabı qoşula bilmədi: {exc}"})
            return

        if message_type == "google.disconnect":
            try:
                disconnect_google()
                _send(websocket, {"type": "google.account", "account": {"connected": False, "email": None}})
                try:
                    bridge.emit_activity("Google hesabı ayrıldı", "success")
                except Exception:
                    pass
            except Exception as exc:
                _send(websocket, {"type": "bridge.error", "message": str(exc)})
            return

        if message_type == "settings.update":
            requested = message.get("settings")
            if not isinstance(requested, dict):
                _send(websocket, {"type": "bridge.error", "message": "Settings obyekti tələb olunur."})
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
            _send(websocket, {"type": "settings.saved", "settings": _public_settings()})
            try:
                bridge.emit_activity("Settings yeniləndi", "success")
            except Exception:
                pass
            return

        return original_handle_message(websocket, raw_message)

    bridge._handle_message = handle_message
