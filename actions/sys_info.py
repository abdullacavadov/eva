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
    if query.startswith("volume_set:"):
        return _desktop_control("set_volume", _parse_level(query, "volume_set:"))
    if query.startswith("brightness_set:"):
        return _desktop_control("set_brightness", _parse_level(query, "brightness_set:"))
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
        results.append(f"Saat: {datetime.datetime.now().strftime('%H:%M:%S')}")
    if query in ("date", "tarih", "all"):
        results.append(f"Tarix: {datetime.datetime.now().strftime('%d %B %Y, %A')}")
    if query in ("network", "ağ", "wifi", "all"):
        results.append(_network())
    if query in ("volume", "səs", "ses", "volume_get"):
        results.append(_desktop_control("get_volume"))
    elif query in ("volume_up", "səs artır", "sesi artır", "səsi artır"):
        results.append(_desktop_control("adjust_volume", 10))
    elif query in ("volume_down", "səs azalt", "səsi azalt", "sesi azalt"):
        results.append(_desktop_control("adjust_volume", -10))
    elif query.startswith("volume_set:"):
        results.append(_desktop_control("set_volume", _parse_level(query, "volume_set:")))
    if query in ("brightness", "parlaqlıq", "parlaqliq", "brightness_get"):
        results.append(_desktop_control("get_brightness"))
    elif query in ("brightness_up", "parlaqlığı artır", "parlaqliqi artır"):
        results.append(_desktop_control("adjust_brightness", 10))
    elif query in ("brightness_down", "parlaqlığı azalt", "parlaqliqi azalt"):
        results.append(_desktop_control("adjust_brightness", -10))
    elif query.startswith("brightness_set:"):
        results.append(_desktop_control("set_brightness", _parse_level(query, "brightness_set:")))
    if not results:
        results.append(f"Bilinməyən sorğu: {query}. battery/cpu/ram/disk/time/date/network/all istifadə edin.")
    return "\n".join(r for r in results if r)


def _parse_desktop_control_query(query: str) -> str | None:
    q = re.sub(r"\s+", " ", str(query or "").strip().casefold())
    if q.startswith("volume:"):
        return _desktop_control("set_volume", _parse_level(q, "volume:"))
    if q.startswith("brightness:"):
        return _desktop_control("set_brightness", _parse_level(q, "brightness:"))
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
    from actions.desktop_controls import adjust_brightness, adjust_volume, get_brightness, get_volume, set_brightness, set_volume
    operations = {
        "get_volume": get_volume,
        "adjust_volume": lambda: adjust_volume(value or 0),
        "set_volume": lambda: set_volume(value or 0),
        "get_brightness": get_brightness,
        "adjust_brightness": lambda: adjust_brightness(value or 0),
        "set_brightness": lambda: set_brightness(value or 0),
    }
    return operations[operation]()


def _battery() -> str:
    if HAS_PSUTIL:
        bat = psutil.sensors_battery()
        if bat:
            return f"Pil: %{bat.percent:.0f} — {'Şarj olur' if bat.power_plugged else 'Pildə'}"
    return "Pil məlumatı alınmadı."


def _cpu() -> str:
    if HAS_PSUTIL:
        usage = psutil.cpu_percent(interval=0.5); count = psutil.cpu_count(logical=True); freq = psutil.cpu_freq()
        return f"CPU: %{usage:.1f} istifadə — {count} nüvə{f', {freq.current:.0f} MHz' if freq else ''}"
    return "CPU məlumatı alınmadı."


def _ram() -> str:
    if HAS_PSUTIL:
        vm = psutil.virtual_memory(); return f"RAM: {vm.used / (1024 ** 3):.1f}GB / {vm.total / (1024 ** 3):.1f}GB istifadədə (%{vm.percent:.0f})"
    return "RAM məlumatı alınmadı."


def _disk() -> str:
    if HAS_PSUTIL:
        du = psutil.disk_usage("C:\\"); return f"Disk (C:): {du.used / (1024 ** 3):.1f}GB istifadə edildi, {du.free / (1024 ** 3):.1f}GB boş (cəmi {du.total / (1024 ** 3):.1f}GB)"
    return "Disk məlumatı alınmadı."


def _network() -> str:
    try:
        out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True, timeout=5, stderr=subprocess.DEVNULL, encoding="utf-8", errors="replace")
        for line in out.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[-1].strip()
                if ssid: return f"WiFi: {ssid} bağlı"
    except Exception: pass
    try:
        out = subprocess.check_output(["ipconfig"], text=True, timeout=5, encoding="utf-8", errors="replace")
        for line in out.splitlines():
            if "IPv4" in line:
                ip = line.split(":", 1)[-1].strip()
                if ip and not ip.startswith("169."): return f"Ağ: IP {ip}"
    except Exception: pass
    return "Ağ bağlantısı tapılmadı."
