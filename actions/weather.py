"""EVA hava məlumatı — cari məkan və soruşulan şəhər üçün Open-Meteo."""
from __future__ import annotations
import requests
from core.location_runtime import get_current_location


def _resolve_location(target: str | None) -> tuple[float, float, str]:
    if target and str(target).strip():
        name = str(target).strip()
        response = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": name, "count": 1, "language": "az", "format": "json"}, timeout=10)
        response.raise_for_status()
        results = response.json().get("results") or []
        if not results:
            raise LookupError(f"Məkan tapılmadı: {name}")
        item = results[0]
        return float(item["latitude"]), float(item["longitude"]), str(item.get("name") or name)
    current = get_current_location()
    if current:
        return current["latitude"], current["longitude"], "Cari məkan"
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data["latitude"]), float(data["longitude"]), str(data.get("city") or data.get("region") or "Cari məkan")
    except Exception:
        return 40.4093, 49.8671, "Bakı"


def get_weather_summary(location: str | None = None) -> dict:
    try:
        latitude, longitude, city_name = _resolve_location(location)
    except Exception:
        return {"success": False, "city": str(location or "Cari məkan")}
    try:
        response = requests.get("https://api.open-meteo.com/v1/forecast", params={"latitude": latitude, "longitude": longitude, "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m", "wind_speed_unit": "kmh", "timezone": "auto"}, timeout=10)
        response.raise_for_status()
        current = response.json().get("current", {})
        code = current.get("weather_code")
        descriptions = {0:"Açıq hava",1:"Əsasən açıq hava",2:"Qismən buludlu",3:"Buludlu",45:"Dumanlı",48:"Çənli",51:"Zəif çiskin",53:"Çiskin",55:"Güclü çiskin",61:"Zəif yağış",63:"Yağış",65:"Güclü yağış",71:"Zəif qar",73:"Qar",75:"Güclü qar",80:"Zəif yağış keçidləri",81:"Yağış keçidləri",82:"Güclü yağış keçidləri",95:"Şimşəkli hava",96:"Şimşək və dolu",99:"Güclü şimşək və dolu"}
        directions = ["Şimal","Şimal-Şərq","Şərq","Cənub-Şərq","Cənub","Cənub-Qərb","Qərb","Şimal-Qərb"]
        degrees = current.get("wind_direction_10m")
        wind_direction = "--" if degrees is None else directions[int((float(degrees) + 22.5) / 45) % 8]
        return {"success": True, "city": city_name, "temperature": current.get("temperature_2m"), "feels_like": current.get("apparent_temperature"), "humidity": current.get("relative_humidity_2m"), "pressure": current.get("surface_pressure"), "wind_speed": current.get("wind_speed_10m"), "wind_direction": wind_direction, "weather_code": code, "condition": descriptions.get(code, "Hava şəraiti müəyyən edilmədi")}
    except Exception:
        return {"success": False, "city": city_name}

try:
    import tool_defs
    for declaration in tool_defs.TOOL_DECLARATIONS:
        if declaration.get("name") == "get_weather":
            declaration["description"] = "Cari hava vəziyyətini alır. Məkan göstərilməzsə istifadəçinin cari geolokasiyasını istifadə edir; istifadəçi şəhər və ya rayon adı deyərsə həmin məkanın havasını alır."
            declaration["parameters"]["properties"]["location"]["description"] = "İstənilən şəhər və ya rayon. Boş saxlanılarsa cari geolokasiya istifadə olunur."
            break
except Exception:
    pass
