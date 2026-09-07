from actions import media


def test_spotify_playback_does_not_use_shell(monkeypatch):
    calls = []

    monkeypatch.setattr(media.webbrowser, "open", lambda url: calls.append(url))
    monkeypatch.setattr(media.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    result = media._play_spotify('test" & whoami & "')

    assert "araması açıldı" in result
    assert calls == ["spotify:search:test%22%20%26%20whoami%20%26%20%22"]


def test_spotify_detection_uses_non_shell_where(monkeypatch):
    calls = []

    monkeypatch.setattr(media.shutil, "which", lambda _: None)

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return type("Completed", (), {"returncode": 1})()

    monkeypatch.setattr(media.subprocess, "run", fake_run)

    assert media._spotify_installed() is False
    assert calls == [((["where", "Spotify"],), {"shell": False, "capture_output": True})]
