from actions import open_app


def test_open_app_never_uses_shell_for_unresolved_app(monkeypatch):
    calls = []

    monkeypatch.setattr(open_app.shutil, "which", lambda _: None)

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        raise FileNotFoundError("not found")

    monkeypatch.setattr(open_app.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        open_app.os,
        "startfile",
        lambda _: (_ for _ in ()).throw(OSError("not found")),
        raising=False,
    )

    result = open_app.open_app('example" & whoami & "')

    assert calls == [(['example" & whoami & "'], {"shell": False})]
    assert "açılamadı" in result


def test_open_app_uses_allowlisted_executable_path_without_shell(monkeypatch):
    calls = []

    monkeypatch.setattr(open_app.shutil, "which", lambda _: r"C:\Apps\Example.exe")
    monkeypatch.setattr(
        open_app.subprocess,
        "Popen",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )

    assert open_app.open_app("example") == "example açıldı."
    assert calls == [([r"C:\Apps\Example.exe"], {"shell": False})]


def test_open_app_does_not_fallback_to_shell_start(monkeypatch):
    popen_calls = []
    run_calls = []

    monkeypatch.setattr(open_app.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        open_app.subprocess,
        "Popen",
        lambda command, **kwargs: popen_calls.append((command, kwargs)) or (_ for _ in ()).throw(FileNotFoundError()),
    )
    monkeypatch.setattr(
        open_app.subprocess,
        "run",
        lambda *args, **kwargs: run_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        open_app.os,
        "startfile",
        lambda _: (_ for _ in ()).throw(OSError("not found")),
        raising=False,
    )

    open_app.open_app("unknown-app")

    assert run_calls == []
    assert popen_calls == [(["unknown-app"], {"shell": False})]


def test_open_app_does_not_expose_exception_details(monkeypatch):
    secret = r"C:\Users\abdulla\private\launcher-error.exe"

    monkeypatch.setattr(open_app.shutil, "which", lambda _: secret)
    monkeypatch.setattr(
        open_app.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError(secret)),
    )

    result = open_app("example")

    assert secret not in result
    assert result == "'example' açılamadı."
