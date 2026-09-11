"""Core runtime configuration used by EVA."""

import json
import os
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
# 480 samples @ 16 kHz = 30 ms. WebRTC VAD/APM üçün keçərli realtime frame ölçüsüdür.
CHUNK_SIZE = 480
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


def _estimate_tokens(text: str) -> int:
    """UTF-8 mətn üçün yalnız audit məqsədli təxmini token sayı verir.

    Bu, Gemini tokenizer deyil. Şəbəkə çağırışı etmədən ölçü trendini izləmək
    üçün konservativ 4 simvol/token heuristikasından istifadə edir.
    """
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def _log_live_context_metrics(kwargs: dict):
    """Live config payload ölçülərini debug üçün ölçür; davranışı dəyişmir."""
    enabled = str(os.getenv("EVA_CONTEXT_METRICS", "true")).strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return

    system_instruction = str(kwargs.get("system_instruction") or "")
    tools = kwargs.get("tools") or []
    try:
        tools_text = json.dumps(tools, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        tools_text = str(tools)

    memory_chars = 0
    memory_marker = "[İSTİFADƏÇİ HAQQINDA MƏLUMATLAR]"
    memory_start = system_instruction.find(memory_marker)
    if memory_start >= 0:
        memory_end = system_instruction.find("\n\nSən EVA", memory_start)
        if memory_end < 0:
            memory_end = len(system_instruction)
        memory_chars = len(system_instruction[memory_start:memory_end])

    system_bytes = len(system_instruction.encode("utf-8"))
    tools_bytes = len(tools_text.encode("utf-8"))
    total_bytes = system_bytes + tools_bytes
    system_tokens = _estimate_tokens(system_instruction)
    memory_tokens = _estimate_tokens(system_instruction[memory_start:memory_end]) if memory_start >= 0 else 0
    tools_tokens = _estimate_tokens(tools_text)
    total_tokens = system_tokens + tools_tokens
    tool_count = sum(
        len(item.get("function_declarations") or [])
        for item in tools
        if isinstance(item, dict)
    )

    tool_metrics = []
    for group in tools:
        if not isinstance(group, dict):
            continue
        for declaration in group.get("function_declarations") or []:
            try:
                declaration_text = json.dumps(
                    declaration,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            except (TypeError, ValueError):
                declaration_text = str(declaration)
            tool_metrics.append(
                (
                    str(declaration.get("name") or "unknown")
                    if isinstance(declaration, dict)
                    else "unknown",
                    len(declaration_text.encode("utf-8")),
                    _estimate_tokens(declaration_text),
                )
            )

    tool_metrics.sort(key=lambda item: item[1], reverse=True)
    top_tools = ", ".join(
        f"{name}={size}B/~{tokens}t"
        for name, size, tokens in tool_metrics[:10]
    )

    print(
        "[CONTEXT] "
        f"system={len(system_instruction)} chars/{system_bytes} bytes/~{system_tokens} tokens | "
        f"memory={memory_chars} chars/~{memory_tokens} tokens | "
        f"tools={tool_count} declarations/{tools_bytes} bytes/~{tools_tokens} tokens | "
        f"total={total_bytes} bytes/~{total_tokens} tokens"
    )
    if top_tools:
        print(f"[CONTEXT-TOOLS] top10: {top_tools}")


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
        _log_live_context_metrics(kwargs)
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
