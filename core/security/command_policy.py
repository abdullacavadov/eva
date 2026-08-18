from __future__ import annotations

import re


# Açıq şəkildə qadağan edilən command pattern-ləri.
BLOCKED_PATTERNS = [
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
]


# Shell injection / command chaining operatorləri.
BLOCKED_OPERATORS = [
    ";",
    "&&",
    "||",
    "|",
    ">",
    "<",
    "`",
]


def validate_command(command: str) -> tuple[bool, str]:
    """
    Command-ı icra etməzdən əvvəl təhlükəsizlik baxımından yoxlayır.

    Returns:
        (True, "") təhlükəsizdirsə.
        (False, səbəb) bloklanmalıdırsa.
    """
    if not isinstance(command, str):
        return False, "Komanda mətn formatında olmalıdır."

    command = command.strip()

    if not command:
        return False, "Boş komanda icra edilə bilməz."

    for operator in BLOCKED_OPERATORS:
        if operator in command:
            return False, f"Təhlükəli shell operatoru bloklandı: {operator}"

    normalized = command.lower()

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return False, "Təhlükəli sistem əmri bloklandı."

    return True, ""
