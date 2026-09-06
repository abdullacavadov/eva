"""Core runtime configuration used by EVA."""

from pathlib import Path

import pyaudio
from google.genai import types as genai_types

from app_config import get_app_config_value

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"

LIVE_MODEL = "models/gemini-3.1-flash-live-preview"
LIVE_THINKING_LEVEL = "minimal"

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
# 512 samples @ 16 kHz = 32 ms. Smaller realtime chunks reduce the amount of
# audio EVA must buffer before Gemini receives it, improving turn latency.
CHUNK_SIZE = 512
# 480 samples @ 24 kHz = 20 ms. Keep playback buffering aligned with the
# realtime audio cadence to reduce output jitter.
PLAYBACK_CHUNK_SIZE = 480

# EVA-nın əsas danışıq dili Azərbaycan dilidir. İstifadəçi Azərbaycan və türk
# dilini qarışdıra bildiyi üçün ASR-ə hər iki dili açıq şəkildə hint edirik.
# İngilis dili texniki terminlər və command adları üçün üçüncü fallback-dir.
LIVE_INPUT_TRANSCRIPTION_LANGUAGE_CODES = ["az-AZ", "tr-TR", "en-US"]

# Səsdən mətnə çevrilən istifadəçi mesajı UI-da göstərildiyi üçün SMART rejimi
# filler, təkrar və yarımçıq ifadələri təmizləyərək daha oxunaqlı transcript verir.
LIVE_INPUT_TRANSCRIPTION_MODE = "SMART"

_LiveConnectConfig = genai_types.LiveConnectConfig


class _EVALiveConnectConfig(_LiveConnectConfig):
    """EVA üçün realtime input transcription parametrlərini mərkəzləşdirir."""

    def __init__(self, *args, **kwargs):
        transcription = kwargs.get("input_audio_transcription")
        if isinstance(transcription, dict):
            transcription = dict(transcription)
            transcription.setdefault(
                "language_codes",
                list(LIVE_INPUT_TRANSCRIPTION_LANGUAGE_CODES),
            )
            transcription.setdefault("mode", LIVE_INPUT_TRANSCRIPTION_MODE)
            kwargs["input_audio_transcription"] = transcription
        kwargs.setdefault(
            "thinking_config",
            {"thinking_level": LIVE_THINKING_LEVEL},
        )
        super().__init__(*args, **kwargs)


genai_types.LiveConnectConfig = _EVALiveConnectConfig


def get_api_key() -> str:
    return str(get_app_config_value("gemini_api_key", "") or "")


def load_system_prompt() -> str:
    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        prompt = (
            "Sən EVA-san — Windows-da çalışan şəxsi AI assistentsən. "
            "Azərbaycan dilində danış. Qısa və aydın cavablar ver. "
            "Tapşırıqları tamamlamaq üçün alətlərdən istifadə et, heç vaxt təqlid etmə."
        )

    user_name = str(get_app_config_value("user_name", "Abdulla") or "Abdulla").strip()
    address_style = str(get_app_config_value("address_style", user_name) or user_name).strip()
    response_length = str(get_app_config_value("response_length", "normal") or "normal").strip().lower()
    humor_level = max(0, min(100, int(get_app_config_value("humor_level", 30) or 0)))
    proactivity_level = max(0, min(100, int(get_app_config_value("proactivity_level", 50) or 0)))
    voice_tone = str(get_app_config_value("voice_tone", "balanced") or "balanced").strip()
    persona_prompt = str(get_app_config_value("persona_prompt", "") or "").strip()

    length_rules = {
        "short": "Cavabları mümkün qədər qısa və birbaşa saxla.",
        "detailed": "Lazım olduqda ətraflı izah ver, amma lazımsız uzatma.",
        "normal": "Normal uzunluqda, konkret və kontekstə uyğun cavablar ver.",
    }
    humor = "Yalnız uyğun olduqda yüngül yumor istifadə et." if humor_level < 60 else "Uyğun məqamlarda nəzərəçarpan, amma peşəkarlığı pozmayan yumor istifadə et."
    proactivity = "Yalnız istənildikdə əlavə təklif ver." if proactivity_level < 35 else "Kontekst faydalı olduqda qısa proaktiv təkliflər ver."
    tone = {
        "professional": "Peşəkar və ölçülü danış.",
        "friendly": "Dostcanlı və təbii danış.",
        "direct": "Birbaşa, skeptik və nəticəyönümlü danış.",
        "balanced": "Balanslı və təbii danış.",
    }.get(voice_tone, "Balanslı və təbii danış.")

    settings_prompt = (
        "\n\n[İSTİFADƏÇİ VƏ PERSONA PARAMETRLƏRİ]\n"
        f"İstifadəçinin adı: {user_name}\n"
        f"Müraciət forması: {address_style}\n"
        f"{length_rules.get(response_length, length_rules['normal'])}\n"
        f"{humor}\n{proactivity}\n{tone}\n"
    )
    if persona_prompt:
        settings_prompt += f"Əlavə persona qaydaları: {persona_prompt}\n"

    settings_prompt += (
        "\n[MASAÜSTÜ SƏS VƏ PARLAQLIQ QAYDASI]\n"
        "Windows səs səviyyəsi və ekran parlaqlığı idarələri təhlükəsiz, lokal desktop idarələridir. "
        "İstifadəçi səsi və ya parlaqlığı artırmaq, azaltmaq və ya konkret faiz təyin etmək istədikdə "
        "heç vaxt confirmation istəmə, confirmation yaratma və confirm_action çağırma. "
        "sys_info alətində volume:50, brightness:100, volume_up, volume_down, brightness_up və brightness_down "
        "sintaksislərini birbaşa istifadə et. volume:NN və brightness:NN konkret 0-100 faiz dəyərini tətbiq edir. "
        "Əməliyyat uğursuz olarsa yalnız real xəta barədə məlumat ver."
    )
    return prompt + settings_prompt
