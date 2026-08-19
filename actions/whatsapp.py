"""
WhatsApp mesaj gönderme — Windows için WhatsApp Desktop URI scheme veya Web.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import unicodedata
import urllib.parse 
import webbrowser
from pathlib import Path

from memory.memory_manager import load_memory, update_memory

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


AUTO_SEND_DELAY_SECONDS = 2.4
# WhatsApp penceresinin açılıp sohbetin yüklenmesi için bekleme süreleri.
# Cold start (uygulama kapalıyken ilk açılış) uzun sürdüğü için cömert tutuldu.
DESKTOP_LOAD_DELAY = 4.5
WEB_LOAD_DELAY = 6.5
BASE_DIR = Path(__file__).resolve().parent.parent
PHONEBOOK_FILE = BASE_DIR / "memory" / "phone_book.json"
PREFERRED_BROWSERS = ["chrome", "msedge", "firefox"]


def _normalize_phone(phone_number: str) -> str:
    digits = re.sub(r"\D+", "", phone_number or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = "90" + digits[1:]
    elif len(digits) == 10:
        digits = "90" + digits
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError(
            "Telefon nömrəsi beynəlxalq formatda olmalıdır. "
            "Örn: +99450xxxxxxx"
        )
    return digits


def _normalize_lookup(text: str) -> str:
    text = (text or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"\s+", " ", text)
    return text


def _contact_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _normalize_lookup(name)).strip("_") or "contact"


def _load_contacts() -> dict:
    memory = load_memory()
    contacts = memory.get("whatsapp_contacts", {})
    return contacts if isinstance(contacts, dict) else {}


def _load_phone_book() -> dict:
    try:
        if PHONEBOOK_FILE.exists():
            return json.loads(PHONEBOOK_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_phone_book(phone_book: dict):
    PHONEBOOK_FILE.parent.mkdir(parents=True, exist_ok=True)
    PHONEBOOK_FILE.write_text(
        json.dumps(phone_book, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _contact_candidates() -> list[dict]:
    candidates = []
    for source_name, source in (("whatsapp", _load_contacts()), ("phone_book", _load_phone_book())):
        if not isinstance(source, dict):
            continue
        for key, entry in source.items():
            if not isinstance(entry, dict):
                continue
            item = dict(entry)
            item.setdefault("display_name", key)
            item["_source"] = source_name
            item["_key"] = key
            candidates.append(item)
    return candidates


def _match_score(needle: str, candidate: str) -> int:
    candidate_norm = _normalize_lookup(candidate)
    if not candidate_norm:
        return 0
    if candidate_norm == needle:
        return 300
    if candidate_norm.startswith(needle) or needle.startswith(candidate_norm):
        return 220
    if needle in candidate_norm:
        return 160
    needle_parts = needle.split()
    if needle_parts and all(part in candidate_norm for part in needle_parts):
        return 120
    return 0


def _find_contact(recipient_name: str) -> dict | None:
    needle = _normalize_lookup(recipient_name)
    if not needle:
        return None

    best_match = None
    best_score = 0
    for entry in _contact_candidates():
        names = [entry.get("display_name", ""), entry.get("_key", "")]
        aliases = entry.get("aliases", [])
        if isinstance(aliases, list):
            names.extend(str(alias) for alias in aliases)
        elif aliases:
            names.append(str(aliases))

        for name in names:
            score = _match_score(needle, name)
            if score > best_score:
                best_score = score
                best_match = entry

    return best_match


def save_whatsapp_contact(display_name: str, phone_number: str, aliases: str = "") -> str:
    if not display_name or not display_name.strip():
        return "Kişi adı boş olamaz."

    try:
        normalized_phone = _normalize_phone(phone_number)
    except ValueError as exc:
        return str(exc)

    alias_list = []
    if aliases and aliases.strip():
        alias_list = [part.strip() for part in aliases.split(",") if part.strip()]

    key = _contact_key(display_name)
    update_memory(
        {
            "whatsapp_contacts": {
                key: {
                    "value": f"+{normalized_phone}",
                    "display_name": display_name.strip(),
                    "aliases": alias_list,
                }
            }
        }
    )

    if alias_list:
        return f"{display_name.strip()} WhatsApp kontaktlarında Saxlanıldı. Ləqəblər: {', '.join(alias_list)}"
    return f"{display_name.strip()} WhatsApp kontaktlarında Saxlanıldı."


def _copy_to_clipboard(text: str) -> None:
    if HAS_PYPERCLIP:
        pyperclip.copy(text)
        return
    # PowerShell fallback
    safe = text.replace("'", "`'")
    subprocess.run(
        ["powershell", "-Command", f"Set-Clipboard -Value '{safe}'"],
        check=True, timeout=5,
    )


def _open_url(url: str) -> None:
    webbrowser.open(url)


def _open_whatsapp_desktop_via_scheme(phone_number: str, message: str, include_text: bool = True) -> tuple[bool, str]:
    if include_text and message.strip():
        url = f"whatsapp://send?phone={phone_number}&text={urllib.parse.quote(message.strip())}"
    else:
        url = f"whatsapp://send?phone={phone_number}"
    try:
        # os.startfile protokol şemasını cmd penceresi açmadan güvenilir başlatır
        os.startfile(url)  # type: ignore[attr-defined]
    except Exception:
        try:
            subprocess.run(["cmd", "/c", "start", "", url], timeout=10)
        except Exception as exc:
            return False, f"WhatsApp Desktop açılmadı: {exc}"
    return True, "WhatsApp Desktop açıldı."


def _open_whatsapp_web(phone_number: str, message: str, include_text: bool = True) -> tuple[bool, str]:
    if include_text and message.strip():
        url = f"https://web.whatsapp.com/send?phone={phone_number}&text={urllib.parse.quote(message.strip())}"
    else:
        url = f"https://web.whatsapp.com/send?phone={phone_number}"
    try:
        _open_url(url)
    except Exception as exc:
        return False, f"WhatsApp Web açılmadı: {exc}"
    return True, "web tarayıcı"


def _focus_whatsapp_window() -> None:
    """WhatsApp Desktop pəncərəsini önə gətirməyə çalışır (best-effort, pygetwindow)."""
    try:
        import pygetwindow as gw  # pyautogui ile birlikte gelir
    except Exception:
        return
    try:
        for win in gw.getAllWindows():
            if "whatsapp" in (win.title or "").lower():
                try:
                    if win.isMinimized:
                        win.restore()
                except Exception:
                    pass
                try:
                    win.activate()
                except Exception:
                    pass
                break
    except Exception:
        pass


def _type_and_send(message: str, load_delay: float) -> tuple[bool, str]:
    """
    Söhbət açıldıqdan sonra mesajı mesaj qutusuna yazıb göndərir.

    Mövcud draftın üstünə əlavə etməmək üçün əvvəlcə Ctrl+A edilir.
    """
    if not HAS_PYAUTOGUI:
        return False, "pyautogui quraşdırılmayıb — avtomatik göndəriş alınmadı."

    try:
        time.sleep(load_delay)
        _focus_whatsapp_window()
        time.sleep(0.6)

        _copy_to_clipboard(message.strip())
        time.sleep(0.3)

        # Mövcud draftı seç və əvəz et.
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)

        pyautogui.press("enter")

        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def send_whatsapp_message(
    message: str,
    phone_number: str = "",
    recipient_name: str = "",
    send_now: bool = False,
    app_target: str = "auto",
) -> str:
    if not message or not message.strip():
        return "Mesaj boş ola bilməz."

    app_target = (app_target or "auto").strip().lower()
    if app_target not in {"auto", "desktop", "web"}:
        app_target = "auto"

    normalized_phone = ""
    if phone_number and phone_number.strip():
        try:
            normalized_phone = _normalize_phone(phone_number)
        except ValueError as exc:
            return str(exc)

    resolved_name = recipient_name.strip() if recipient_name else ""
    contact = _find_contact(resolved_name) if resolved_name else None

    if contact and not normalized_phone:
        stored_phone = (
            contact.get("value")
            or contact.get("phone_number")
            or contact.get("phone")
            or contact.get("number")
            or ""
        )

        try:
            normalized_phone = _normalize_phone(str(stored_phone).strip())
        except ValueError:
            normalized_phone = ""

        resolved_name = (
            str(contact.get("display_name", resolved_name)).strip()
            or resolved_name
        )
        contact_source = contact.get("_source", "")
    else:
        contact_source = ""

    if app_target in {"auto", "desktop"}:
        if normalized_phone:
            source_note = " (kontaktdan tapııldı)" if contact_source == "phone_book" else ""
            label = resolved_name or f"+{normalized_phone}"
            # send_now + pyautogui varsa: metni biz panodan yazıp göndereceğiz,
            # bu yüzden URL'ye 'text' koyma (çift metin olmasın). Aksi halde URL ile ön-doldur.
            include_text = not (send_now and HAS_PYAUTOGUI)
            ok, detail = _open_whatsapp_desktop_via_scheme(
                normalized_phone, message, include_text=include_text
            )
            if ok:
                if not send_now:
                    return f"WhatsApp Desktop içində {label}{source_note} üçün qaralama mesaj açıldı."
                ok_send, send_detail = _type_and_send(message, DESKTOP_LOAD_DELAY)
                if ok_send:
                    return f"WhatsApp Desktop üzərindən {label}{source_note} nəfərə mesaj göndərildi."
                return (
                    f"WhatsApp Desktop söhbəti açıldı, amma avtomatik göndərim alınmadı: {send_detail}. "
                    "Mesaj qutusuna gəlib Enter'a basmaq kifayətdir."
                )
            if app_target == "desktop":
                return f"WhatsApp Desktop açılarxən xəta baş verdi: {detail}"

    if not normalized_phone:
        if resolved_name:
            return (
                f"'{resolved_name}' üçün qeyd olunmuş bir telefon nömrəsi tapılmadı. "
                "İstəsən, əvvəlcə həmin şəxsi nömrəsi ilə yadda saxla."
            )
        return "WhatsApp mesajı üçün kontakt adı və ya telefon nömrəsi tələb olunur."

    source_note = " (kontaklardan tapıldı)" if contact_source == "phone_book" else ""
    label = resolved_name or f"+{normalized_phone}"

    # Web'de metni URL ön-doldurması güvenilir taşır; gönderim için sadece Enter gerekir.
    ok, detail = _open_whatsapp_web(normalized_phone, message, include_text=True)
    if not ok:
        return detail

    if not send_now:
        return (
            f"WhatsApp Web {label}{source_note} üçün brauzerdə açıldı. "
            "Göndərmək üçün Enter'a bas."
        )

    if not HAS_PYAUTOGUI:
        return (
            f"WhatsApp Web {label}{source_note} üçün açıldı və mesaj hazırdır. "
            "Avtomatik göndərim üçün pyautogui lazımdır; Enter'a basaraq göndərə bilərsən."
        )

    try:
        time.sleep(WEB_LOAD_DELAY)   # sayfa + sohbet yüklensin (giriş yapılmış olmalı)
        pyautogui.press("enter")
        return f"WhatsApp Web üzərindən {label}{source_note} şəxsə mesaj göndərildi."
    except Exception as exc:
        return (
            f"WhatsApp Web açıldı, amma, avtomatik göndərim baş tutmadı: {exc}. "
            "Enter'a basaraq göndərə bilərsən."
        )


# ── vCard (.vcf) rehber içe aktarma ──────────────────────────────────────────
# macOS sürümüyle aynı: telefon rehberini (.vcf) toplu olarak kalıcı belleğe alır.

def _unfold_vcf_lines(text: str) -> list[str]:
    unfolded = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r\n")
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def import_phone_book_from_vcf(vcf_path: str) -> str:
    source = Path(vcf_path).expanduser()
    if not source.exists():
        return f"Rehber dosyası bulunamadı: {source}"

    try:
        text = source.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return f"Rehber dosyası okunamadı: {exc}"

    entries = {}
    current_lines = []
    imported = 0
    skipped = 0

    def _flush_card(lines: list[str]):
        nonlocal imported, skipped
        if not lines:
            return
        display_name = ""
        aliases = []
        numbers = []
        for line in lines:
            upper = line.upper()
            if upper.startswith("FN:"):
                display_name = line.split(":", 1)[1].strip()
            elif upper.startswith("N:") and not display_name:
                parts = [part.strip() for part in line.split(":", 1)[1].split(";") if part.strip()]
                if parts:
                    display_name = " ".join(reversed(parts[:2])).strip()
            elif "TEL" in upper and ":" in line:
                number = line.split(":", 1)[1].strip()
                if number:
                    numbers.append(number)

        if not display_name or not numbers:
            skipped += 1
            return

        normalized_numbers = []
        for raw_number in numbers:
            try:
                normalized_numbers.append("+" + _normalize_phone(raw_number))
            except ValueError:
                continue
        if not normalized_numbers:
            skipped += 1
            return

        if " " in display_name:
            aliases.extend(part for part in display_name.split() if len(part) > 1)
        key = _contact_key(display_name)
        entries[key] = {
            "display_name": display_name,
            "value": normalized_numbers[0],
            "numbers": normalized_numbers,
            "aliases": sorted({alias for alias in aliases if _normalize_lookup(alias) != _normalize_lookup(display_name)}),
            "source": "vcf_import",
        }
        imported += 1

    for line in _unfold_vcf_lines(text):
        if line.upper() == "BEGIN:VCARD":
            current_lines = []
        elif line.upper() == "END:VCARD":
            _flush_card(current_lines)
            current_lines = []
        else:
            current_lines.append(line)

    phone_book = _load_phone_book()
    phone_book.update(entries)
    _save_phone_book(phone_book)
    return f"{imported} rehber kişisi içe aktarıldı, {skipped} kayıt atlandı."
