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

# Hər allowlisted executable üçün yalnız zərərsiz, gözlənilən arqumentlərə icazə verilir.
# Digər executable-larda arqument qəbul edilmir.
ALLOWED_ARGUMENTS = {
    "whoami": set(),
    "hostname": set(),
    "ver": set(),
    "ipconfig": {"/all"},
    "getmac": set(),
    "tasklist": set(),
    "systeminfo": set(),
}

_SAFE_WHERE_TARGET = re.compile(r"^[A-Za-z0-9_.-]+(?:\.exe)?$", re.IGNORECASE)


def validate_command(command: str) -> tuple[bool, str]:
    """
    Command-ı icra etməzdən əvvəl təhlükəsizlik baxımından yoxlayır.

    Yalnız əvvəlcədən müəyyən edilmiş təhlükəsiz executable-lara və onların
    məhdud, read-only arqumentlərinə icazə verilir.
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

    args = [part.strip('"').strip("'") for part in parts[1:]]

    if executable == "where":
        if len(args) != 1 or not _SAFE_WHERE_TARGET.fullmatch(args[0]):
            return False, "where üçün yalnız sadə executable adı icazəlidir."
    else:
        allowed_args = ALLOWED_ARGUMENTS[executable]
        if args and any(arg.lower() not in {item.lower() for item in allowed_args} for arg in args):
            return False, f"Bu executable üçün arqumentə icazə yoxdur: {executable}"
        if len(args) > len(allowed_args):
            return False, f"Bu executable üçün arqument sayı icazə veriləndən çoxdur: {executable}"

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
