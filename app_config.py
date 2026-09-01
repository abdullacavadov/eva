# Alp Ünlü tərəfindən yapılmışdır — @alppunlu
from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "api_keys.json"


DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "voice": "Charon",
    "youtube_api_key": "",
    "youtube_channel_handle": "",
    "sfx_enabled": True,
    "sfx_volume": 20,
    "sfx_startup_enabled": True,
    "sfx_listening_enabled": True,
    "sfx_thinking_enabled": True,
    "sfx_success_enabled": True,
    "sfx_error_enabled": True,
    "sfx_notification_enabled": True,
    "sfx_startup_volume": 100,
    "sfx_listening_volume": 100,
    "sfx_thinking_volume": 100,
    "sfx_success_volume": 100,
    "sfx_error_volume": 100,
    "sfx_notification_volume": 100,
    "proactive_enabled": True,
    "language": "az-AZ",
    "wake_listener_enabled": True,
    "auto_start": False,
    "user_name": "Abdulla",
    "address_style": "Abdulla",
    "response_length": "normal",
    "humor_level": 30,
    "proactivity_level": 50,
    "voice_tone": "balanced",
    "persona_prompt": "",
    "voice_volume": 100,
    "speech_speed": 1.0,
    "interrupt_enabled": True,
    "auto_duck_music": True,
    "fallback_voice": "",
    "orb_style": "default",
    "particle_density": 100,
    "particle_speed": 100,
    "glow_intensity": 100,
    "orb_listening_color": "0, 255, 136",
    "orb_speaking_color": "68, 136, 255",
    "orb_thinking_color": "255, 204, 0",
    "orb_muted_color": "200, 30, 80",
    "particle_animation_enabled": True,
    "glow_enabled": True,
    "pulse_enabled": True,
    "audio_reactive_enabled": True,
}


def load_app_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            config.update(raw)
    except Exception:
        pass
    return config


def save_app_config(updates: dict) -> dict:
    config = load_app_config()
    for key, value in (updates or {}).items():
        if value is None:
            continue
        config[key] = value
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return config


def get_app_config_value(key: str, default=None):
    return load_app_config().get(key, default)


def has_gemini_api_key() -> bool:
    value = str(get_app_config_value("gemini_api_key", "") or "").strip()
    return bool(value)
