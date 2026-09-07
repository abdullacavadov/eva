from unittest.mock import patch

import pytest

from core.security.command_policy import validate_command
from core.security.command_runner import run_command


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


@pytest.mark.parametrize(
    "command",
    [
        "ipconfig /release",
        "ipconfig /renew",
        "ipconfig /release6",
        "ipconfig /renew6",
        "systeminfo /s remote-host",
        "tasklist /v",
        "whoami /all",
        "hostname unexpected",
        "ver unexpected",
        "where C:\\Windows\\System32\\cmd.exe",
        "where python cmd",
    ],
)
def test_unapproved_arguments_are_blocked(command):
    allowed, reason = validate_command(command)

    assert allowed is False
    assert reason


def test_where_accepts_simple_executable_name():
    allowed, reason = validate_command("where python.exe")

    assert allowed is True
    assert reason == ""


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


def test_nonzero_exit_does_not_expose_stderr():
    completed = type(
        "CompletedProcessStub",
        (),
        {"returncode": 1, "stdout": "", "stderr": "C:\\Users\\Abdulla\\secret\\missing.txt"},
    )()

    with patch("core.security.command_runner.subprocess.run", return_value=completed):
        result = run_command("whoami")

    assert result == "Komanda uğursuz oldu (exit code 1)."
    assert "Abdulla" not in result
    assert "missing.txt" not in result


def test_exception_does_not_expose_internal_details():
    with patch(
        "core.security.command_runner.subprocess.run",
        side_effect=OSError("C:\\Users\\Abdulla\\private\\runner.exe not found"),
    ):
        result = run_command("whoami")

    assert result == "Xəta: komanda icra edilərkən daxili xəta baş verdi."
    assert "Abdulla" not in result
    assert "runner.exe" not in result


def test_successful_stdout_is_preserved():
    completed = type(
        "CompletedProcessStub",
        (),
        {"returncode": 0, "stdout": "Abdulla\n", "stderr": ""},
    )()

    with patch("core.security.command_runner.subprocess.run", return_value=completed):
        result = run_command("whoami")

    assert result == "Abdulla"
