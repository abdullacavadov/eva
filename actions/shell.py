from __future__ import annotations

from core.security.command_runner import run_command


def shell_run(command: str) -> str:
    return run_command(command)