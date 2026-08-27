"""Core runtime configuration used by EVA."""

from pathlib import Path

import pyaudio

from app_config import get_app_config_value

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"

# Gemini Live üçün mövcud, sənədləşdirilmiş audio-to-audio model.
LIVE_MODEL = "gemini-3.1-flash-live-preview"

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024


def get_api_key() -> str:
    return str(get_app_config_value("gemini_api_key", "") or "")


def load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "Sən EVA-san — Windows-da çalışan şəxsi AI assistentsən. "
            "Azərbaycan dilində danış. Qısa və aydın cavablar ver. "
            "Tapşırıqları tamamlamaq üçün alətlərdən istifadə et, heç vaxt təqlid etmə."
        )
