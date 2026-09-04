"""
Sistem bilgisi — Windows üçün psutil + subprocess (cmd/PowerShell)
"""

import re
import subprocess
import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def sys_info(query: str) -> str:
    query = query.lower().strip()
    results = []

    # Explicit internal control syntax must reach its strict parser first.
    # Otherwise the natural-language parser can mistake "volume_set:..."
    # for a normal volume query and import the Windows-only pycaw backend.
    if query.startswith("volume_set:"):
        results.append(_desktop_control("set_volume", _parse_level(query, "volume_set:")))
        return "\n".join(r for r in results if r)
    if query.startswith("brightness_set:"):
        results.append(_desktop_control("set_brightness", _parse_level(query, "brightness_set:")))
        return "\n".join(r for r in results if r)

    # Natural-language desktop control commands must be parsed before the
    # generic system-info routing. Gemini commonly passes the whole user
    # phrase here (for example: "səs səviyyəsini 50-yə endir").
    control_result = _parse_desktop_control_query(query)
    if control_result is not None:
        return control_result

    if query in ("battery", "pil", "all"):
        results.append(_battery())
    if query in ("cpu", "işləmci", "all"):
        results.append(_cpu())
    if query in ("ram", "bellek", "memory", "all"):
        results.append(_ram())
    if query in ("disk", "depolama", "all"):
        results.append(_disk())
    if query in ("time", "saat", "zaman", "all"):
        now = datetime.datetime.now()
        results.append(f"Saat: {now.strftime('%H:%M:%S')}")
    if query in ("date", "tarih", "all"):
        now = datetime.datetime.now()
        results.append(f"Tarix: {now.strftime('%d %B %Y, %A')}")
    if query in ("network", "ağ", "wifi", "all"):
        results.append(_network())

    if query in ("volume", "səs", "ses", "volume_get"):
        results.append(_desktop_control("get_volume"))
    elif query in ("volume_up", "səs artır", "sesi artır", "səsi artır"):
        results.append(_desktop_control("adjust_volume", 10))
    elif query in ("volume_down", "səs azalt", "sesi azalt", "səsi azalt"):
        results.append(_desktop_control("adjust_volume", -10))
    if query in ("brightness", "parlaqlıq", "parlaqliq", "brightness_get"):
        results.append(_desktop_control("get_brightness"))
    elif query in ("brightness_up", "parlaqlığı artır", "parlaqliqi artır"):
        results.append(_desktop_control("adjust_brightness", 10))
    elif query in ("brightness_down", "parlaqlığı azalt", "parlaqliqi azalt"):
        results.append(_desktop_control("adjust_brightness", -10))

    if not results:
        results.append(f"Bilinməyən sorğu: {query}. battery/cpu/ram/disk/time/date/network/all istifadə edin.")

    return "\n".join(r for r in results if r)


def _parse_desktop_control_query(query: str) -> str | None:
    """Extract explicit volume/brightness commands from natural language."""
    q = re.sub(r"\s+", " ", str(query or "").strip().casefold())

    volume_words = r"(?:səs|ses|volume|səs səviyyəsi|ses səviyyəsi)"
    brightness_words = r"(?:ekran parlaqlığı|ekran parlaxlığı|parlaqlıq|parlaqliq|brightness)"

    value_match = re.search(r"(?<!\d)(100|[0-9]{1,2})(?:\s*%|\s*(?:ə|e|a|i)?\s*(?:faiz|percent|prosent))?", q)
    value = int(value_match.group(1)) if value_match else None
    if value is not None:
        value = max(0, min(100, value))

    if re.search(volume_words, q):
        if value is not None and re.search(r"(?:təyin et|teyin et|et|endir|endirm|qoy|qoyun|saxla|saxlayın|faiz|%)", q):
            return _desktop_control("set_volume", value)
        if re.search(r"(?:artır|artir|qaldır|qaldir|yüksəlt|yukselt|increase|up)", q):
            return _desktop_control("adjust_volume", 10)
        if re.search(r"(?:azalt|azal|endir|aşağı sal|asagi sal|decrease|down)", q):
            return _desktop_control("adjust_volume", -10)
        return _desktop_control("get_volume")

    if re.search(brightness_words, q):
        if value is not None and re.search(r"(?:təyin et|teyin et|et|endir|endirm|qoy|qoyun|saxla|saxlayın|faiz|%)", q):
            return _desktop_control("set_brightness", value)
        if re.search(r"(?:artır|artir|qaldır|qaldir|yüksəlt|yukselt|increase|up)", q):
            return _desktop_control("adjust_brightness", 10)
        if re.search(r"(?:azalt|azal|endir|aşağı sal|asagi sal|decrease|down)", q):
            return _desktop_control("adjust_brightness", -10)
        return _desktop_control("get_brightness")

    return None


def _parse_level(query: str, prefix: str) -> int:
    try:
        value = int(query.removeprefix(prefix).strip().rstrip("%"))
    except ValueError as exc:
        raise ValueError("Səviyyə 0-100 aralığında tam ədəd olmalıdır.") from exc
    return max(0, min(100, value))


def _desktop_control(operation: str, value: int | None = None) -> str:
    from actions.desktop_controls import (
        adjust_brightness,
        adjust_volume,
        get_brightness,
        get_volume,
        set_brightness,
        set_volume,
    )
    operations = {
        "get_volume": get_volume,
        "adjust_volume": lambda: adjust_volume(value or 0),
        "set_volume": lambda: set_volume(value or 0),
        "get_brightness": get_brightness,
        "adjust_brightness": lambda: adjust_brightness(value or 0),
        "set_brightness": lambda: set_brightness(value or 0),
    }
    handler = operations.get(operation)
    if handler is None:
        raise ValueError(f"Naməlum desktop control: {operation}")
    return handler()


def _battery() -> str:
    if HAS_PSUTIL:
        bat = psutil.sensors_battery()
        if bat:
            status = "Şarj olur" if bat.power_plugged else "Pildə"
            return f"Pil: %{bat.percent:.0f} — {status}"
    try:
        out = subprocess.check_output(
            ["powershell", "-Command", "Get-WmiObject Win32_Battery | Select-Object EstimatedChargeRemaining,BatteryStatus | ConvertTo-Json"],
            text=True, timeout=8, stderr=subprocess.DEVNULL,
        )
        import json
        data = json.loads(out.strip())
        if isinstance(data, list):
            data = data[0]
        pct = data.get("EstimatedChargeRemaining", "?")
        status_code = data.get("BatteryStatus", 0)
        status = "Şarj olur" if status_code in (2, 6, 7, 8, 9) else "Pildə"
        return f"Pil: %{pct} — {status}"
    except Exception:
        pass
    return "Pil məlumatı alınmadı (masaüstü kompüter və ya psutil çatışmır ola bilər)."


def _cpu() -> str:
    if HAS_PSUTIL:
        usage = psutil.cpu_percent(interval=0.5)
        count = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        freq_str = f", {freq.current:.0f} MHz" if freq else ""
        return f"CPU: %{usage:.1f} istifadə — {count} nüvə{freq_str}"
    return "CPU məlumatı alınmadı."


def _ram() -> str:
    if HAS_PSUTIL:
        vm = psutil.virtual_memory()
        total = vm.total / (1024 ** 3)
        used = vm.used / (1024 ** 3)
        pct = vm.percent
        return f"RAM: {used:.1f}GB / {total:.1f}GB istifadədə (%{pct:.0f})"
    return "RAM məlumatı alınmadı."


def _disk() -> str:
    if HAS_PSUTIL:
        du = psutil.disk_usage("C:\\")
        total = du.total / (1024 ** 3)
        used = du.used / (1024 ** 3)
        free = du.free / (1024 ** 3)
        return f"Disk (C:): {used:.1f}GB istifadə edildi, {free:.1f}GB boş (cəmi {total:.1f}GB)"
    try:
        out = subprocess.check_output(["wmic", "logicaldisk", "get", "size,freespace,caption"], text=True, timeout=5)
        lines = [l for l in out.strip().splitlines() if l.strip() and "Caption" not in l]
        if lines:
            return f"Disk: {lines[0].strip()}"
    except Exception:
        pass
    return "Disk məlumatı alınmadı."


def _network() -> str:
    try:
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
            encoding="utf-8", errors="replace",
        )
        for line in out.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[-1].strip()
                if ssid:
                    return f"WiFi: {ssid} bağlı"
    except Exception:
        pass
    try:
        out = subprocess.check_output(["ipconfig"], text=True, timeout=5, encoding="utf-8", errors="replace")
        for line in out.splitlines():
            if "IPv4" in line:
                ip = line.split(":", 1)[-1].strip()
                if ip and not ip.startswith("169."):
                    return f"Ağ: IP {ip}"
    except Exception:
        pass
    return "Ağ bağlantısı tapılmadı."
