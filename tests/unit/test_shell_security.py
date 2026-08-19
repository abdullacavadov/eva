import pytest

from core.security.command_policy import validate_command


@pytest.mark.parametrize(
    "command",
    [
        "whoami",
        "hostname",
        "ver",
        "ipconfig",
        "ipconfig /all",
        "getmac",
        "tasklist",
        "systeminfo",
        "where python",
    ],
)
def test_allowed_commands(command):
    allowed, reason = validate_command(command)

    assert allowed is True
    assert reason == ""


@pytest.mark.parametrize(
    "command",
    [
        "cmd /c whoami",
        "powershell Get-Process",
        "pwsh Get-Process",
        "python -c \"print(1)\"",
        "wscript test.vbs",
        "cscript test.vbs",
        "mshta test.hta",
        "rundll32 something.dll",
    ],
)
def test_dangerous_executables_are_blocked(command):
    allowed, reason = validate_command(command)

    assert allowed is False
    assert reason


@pytest.mark.parametrize(
    "command",
    [
        "whoami && whoami",
        "whoami || hostname",
        "whoami | findstr user",
        "whoami > output.txt",
        "whoami < input.txt",
        "whoami; hostname",
        "whoami `hostname`",
    ],
)
def test_shell_operators_are_blocked(command):
    allowed, reason = validate_command(command)

    assert allowed is False
    assert "operatoru" in reason


@pytest.mark.parametrize(
    "command",
    [
        "del /f test.txt",
        "erase /f test.txt",
        "format C:",
        "diskpart",
        "shutdown /s",
        "reg delete HKCU\\Software\\Test",
        "remove-item test.txt",
        "set-executionpolicy bypass",
    ],
)
def test_destructive_commands_are_blocked(command):
    allowed, reason = validate_command(command)

    assert allowed is False
    assert reason


def test_unknown_executable_is_blocked():
    allowed, reason = validate_command("notepad")

    assert allowed is False
    assert "icazə yoxdur" in reason


def test_empty_command_is_blocked():
    allowed, reason = validate_command("")

    assert allowed is False


def test_non_string_command_is_blocked():
    allowed, reason = validate_command(None)

    assert allowed is False