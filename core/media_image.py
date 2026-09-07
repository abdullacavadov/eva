"""EVA üçün Gemini əsaslı şəkil yaratma mühərriki."""

from __future__ import annotations

from pathlib import Path

from google import genai

from core.config import get_api_key

DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image"


def _validate_output_path(output_path: str | Path) -> Path:
    path = Path(output_path).expanduser()
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Şəkil çıxışı yalnız PNG, JPEG və ya WebP ola bilər.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def generate_image(
    prompt: str,
    output_path: str | Path,
    *,
    model: str = DEFAULT_IMAGE_MODEL,
    aspect_ratio: str = "16:9",
    image_size: str = "1K",
) -> str:
    """Gemini ilə şəkil yaradır və lokal fayla yazır.

    Şəbəkə/API əməliyyatı yalnız bu funksiyada edilir; video kompozisiyası
    bundan asılı deyil və ayrıca test edilə bilər.
    """
    clean_prompt = str(prompt or "").strip()
    if not clean_prompt:
        raise ValueError("Şəkil prompt-u boş ola bilməz.")

    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Gemini API açarı konfiqurasiya edilməyib.")

    destination = _validate_output_path(output_path)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[clean_prompt],
        config={
            "response_modalities": ["TEXT", "IMAGE"],
            "image_config": {
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
            },
        },
    )

    for part in getattr(response, "parts", []) or []:
        if getattr(part, "inline_data", None) is None:
            continue
        image = part.as_image()
        image.save(destination)
        return str(destination)

    raise RuntimeError("Gemini şəkil çıxışı qaytarmadı.")
