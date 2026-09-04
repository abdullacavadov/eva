"""EVA nəticələrini ayrıca modal pəncərədə göstərmək üçün UI köməkçisi."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any

from core.result_context import ResultContext


def _display_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def format_result_for_modal(context: ResultContext, selected_item: dict[str, Any] | None = None) -> str:
    """ResultContext-i modal üçün oxunaqlı, deterministik mətnə çevirir."""
    lines = [
        f"MƏNBƏ: {str(context.type or 'NƏTİCƏ').upper()}",
        f"NƏTİCƏ SAYI: {context.count}",
    ]
    if context.query:
        lines.append(f"SORĞU: {_display_value(context.query)}")
    lines.append("")

    data = [selected_item] if selected_item is not None else context.data
    for index, item in enumerate(data, 1):
        lines.append(f"[{index}]")
        if not isinstance(item, dict):
            lines.append(_display_value(item))
            lines.append("")
            continue
        preferred = ("title", "name", "subject", "summary", "display_name", "value", "text", "snippet", "start", "start_iso", "due", "timestamp", "status", "source")
        emitted: set[str] = set()
        for key in preferred:
            if key in item and item[key] not in (None, ""):
                lines.append(f"{key}: {_display_value(item[key])}")
                emitted.add(key)
        for key, value in item.items():
            if key in emitted or value in (None, "") or key == "id":
                continue
            lines.append(f"{key}: {_display_value(value)}")
        lines.append("")
    return "\n".join(lines).strip()


def show_result_modal(root: tk.Misc, context: ResultContext, selected_item: dict[str, Any] | None = None) -> tk.Toplevel:
    """Nəticəni əsas EVA layout-una toxunmadan modal pəncərədə göstərir."""
    window = tk.Toplevel(root)
    window.title("E.V.A — Nəticə")
    window.transient(root)
    window.resizable(True, True)
    window.geometry("760x600")
    window.minsize(560, 420)
    try:
        window.deiconify()
        window.lift()
        window.attributes("-topmost", True)
        window.after(150, lambda: window.attributes("-topmost", False))
        window.focus_force()
        window.grab_set()
    except tk.TclError:
        pass

    bg = "#070b14"
    panel = "#0d1422"
    text = "#d9e6ff"
    accent = "#44aaff"
    muted = "#7f93ad"

    outer = tk.Frame(window, bg=bg, padx=18, pady=16)
    outer.pack(fill="both", expand=True)

    header = tk.Frame(outer, bg=bg)
    header.pack(fill="x", pady=(0, 10))
    tk.Label(header, text="E.V.A", bg=bg, fg=accent, font=("Segoe UI", 14, "bold")).pack(side="left")
    tk.Label(header, text="  Nəticə", bg=bg, fg=text, font=("Segoe UI", 13)).pack(side="left")

    frame = tk.Frame(outer, bg=panel, bd=0, highlightthickness=1, highlightbackground="#1c2b40")
    frame.pack(fill="both", expand=True)

    scrollbar = ttk.Scrollbar(frame, orient="vertical")
    viewer = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set, bg=panel, fg=text, insertbackground=text, relief="flat", borderwidth=0, padx=16, pady=14, font=("Consolas", 10), state="normal")
    scrollbar.config(command=viewer.yview)
    scrollbar.pack(side="right", fill="y")
    viewer.pack(side="left", fill="both", expand=True)
    viewer.insert("1.0", format_result_for_modal(context, selected_item))
    viewer.configure(state="disabled")

    tk.Button(outer, text="Bağla", command=window.destroy, bg="#162236", fg=text, activebackground="#20314b", activeforeground=text, relief="flat", padx=18, pady=7, font=("Segoe UI", 10, "bold")).pack(anchor="e", pady=(12, 0))
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.bind("<Escape>", lambda _event: window.destroy())
    return window
