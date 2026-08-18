from core.security.command_policy import validate_command

from core.security.command_runner import run_command


def test_safe_command_executes():
    result = run_command("python --version")

    assert "Python" in result


def test_blocked_command_is_not_executed():
    result = run_command("shutdown /s /t 0")

    assert result.startswith("Komanda bloklandı:")


def test_failed_command_reports_failure():
    result = run_command("python -c \"raise SystemExit(7)\"")

    assert "exit code 7" in result


def test_empty_command_is_blocked():
    allowed, reason = validate_command("")

    assert allowed is False
    assert reason


def test_normal_command_is_allowed():
    allowed, reason = validate_command("python --version")

    assert allowed is True
    assert reason == ""


def test_command_chaining_is_blocked():
    allowed, reason = validate_command("python --version && whoami")

    assert allowed is False
    assert "operator" in reason.lower()


def test_pipe_is_blocked():
    allowed, reason = validate_command("whoami | findstr user")

    assert allowed is False


def test_redirection_is_blocked():
    allowed, reason = validate_command("echo hello > test.txt")

    assert allowed is False


def test_shutdown_is_blocked():
    allowed, reason = validate_command("shutdown /s /t 0")

    assert allowed is False


def test_dangerous_delete_is_blocked():
    allowed, reason = validate_command("del /f /q test.txt")

    assert allowed is False


def test_normal_python_command_is_allowed():
    allowed, reason = validate_command("python -m pytest -q")

    assert allowed is True
    assert reason == ""
