from __future__ import annotations

import re
import shlex


ALLOWED_COMMANDS = {
    "whoami",
    "hostname",
    "ver",
    "ipconfig",
    "getmac",
    "tasklist",
    "systeminfo",
    "where",
}

# Shell injection / command chaining operatorləri.
BLOCKED_OPERATORS = (
    ";",
    "&&",
    "||",
    "|",
    ">",
    "<",
    "`",
)

BLOCKED_EXECUTABLES = {
    "cmd",
    "cmd.exe",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "python",
    "python.exe",
    "python3",
    "python3.exe",
    "wscript",
    "wscript.exe",
    "cscript",
    "cscript.exe",
    "mshta",
    "mshta.exe",
    "rundll32",
    "rundll32.exe",
}




def validate_command(command: str) -> tuple[bool, str]:
    """
    Command-ı icra etməzdən əvvəl təhlükəsizlik baxımından yoxlayır.

    Yalnız əvvəlcədən müəyyən edilmiş təhlükəsiz executable-lara icazə verilir.
    """

    if not isinstance(command, str):
        return False, "Komanda mətn formatında olmalıdır."

    command = command.strip()

    if not command:
        return False, "Boş komanda icra edilə bilməz."

    for operator in BLOCKED_OPERATORS:
        if operator in command:
            return False, f"Təhlükəli shell operatoru bloklandı: {operator}"

    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        return False, "Komanda sintaksisi düzgün deyil."

    if not parts:
        return False, "Boş komanda icra edilə bilməz."

    executable = parts[0].strip('"').strip("'").lower()

    if "\\" in executable or "/" in executable:
        executable = executable.rsplit("\\", 1)[-1]
        executable = executable.rsplit("/", 1)[-1]

    if executable in BLOCKED_EXECUTABLES:
        return False, "Təhlükəli executable bloklandı."

    if executable not in ALLOWED_COMMANDS:
        return False, f"Bu executable üçün icazə yoxdur: {executable}"

    normalized = command.lower()

    dangerous_patterns = (
        r"\bformat\b",
        r"\bdiskpart\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\breg\s+delete\b",
        r"\brd\s+/s\b",
        r"\brmdir\s+/s\b",
        r"\bdel\s+/[fqsa-z]*\b",
        r"\berase\s+/[fqsa-z]*\b",
        r"\bremove-item\b",
        r"\bremove-itemproperty\b",
        r"\bset-executionpolicy\b",
    )

    for pattern in dangerous_patterns:
        if re.search(pattern, normalized, re.IGNORECASE):
            return False, "Təhlükəli sistem əmri bloklandı."

    return True, ""
