from __future__ import annotations

import subprocess

from core.security.command_policy import validate_command


def run_command(command: str, timeout: int = 30) -> str:
    """
    Təhlükəsizlik yoxlamasından keçən command-ı icra edir.

    shell=True istifadə edilmir.
    """

    allowed, reason = validate_command(command)

    if not allowed:
        return f"Komanda bloklandı: {reason}"

    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return "Xəta: komanda vaxt limitini keçdi."

    except Exception as exc:
        return f"Xəta: {exc}"

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()

    if completed.returncode != 0:
        if stderr:
            return f"Komanda uğursuz oldu (exit code {completed.returncode}): {stderr}"

        return (
            f"Komanda uğursuz oldu "
            f"(exit code {completed.returncode})."
        )

    return stdout or "Komanda uğurla icra edildi."