"""Phase 10.3 media tool declaration coverage."""

import tool_defs

# actions.media performs the capability registration against the existing declaration.
import actions.media  # noqa: F401,E402


def test_play_media_declaration_exposes_creation_capabilities():
    declaration = next(item for item in tool_defs.TOOL_DECLARATIONS if item["name"] == "play_media")

    description = declaration["description"].lower()
    provider_description = declaration["parameters"]["properties"]["provider"]["description"].lower()

    assert "şəkil yaradır" in description
    assert "slideshow" in description
    assert "image" in provider_description
    assert "slideshow" in provider_description


def test_media_creation_provider_values_are_routed_by_existing_action(monkeypatch):
    calls = []

    monkeypatch.setattr(actions.media, "generate_media_image", lambda prompt, filename: calls.append(("image", prompt, filename)) or "generated.png")
    monkeypatch.setattr(actions.media, "create_media_slideshow", lambda images, filename, **kwargs: calls.append(("slideshow", images, filename, kwargs)) or "video.mp4")

    assert actions.media.play_media("a futuristic city", provider="image") == "Şəkil hazırlandı: generated.png"
    assert actions.media.play_media('{"images":["a.png"],"filename":"video.mp4"}', provider="slideshow") == "Video hazırlandı: video.mp4"
    assert calls[0] == ("image", "a futuristic city", "generated.png")
    assert calls[1][0] == "slideshow"
