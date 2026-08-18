"""
Basit hava durumu ozeti — uzaktaki bir servis uzerinden calisir.
Alp Ünlü tarafından yapılmıştır — @alppunlu

Varsayilan konum:
- JARVIS_WEATHER_LOCATION env varsa onu kullanir
- yoksa Bakı varsayilir
"""

from __future__ import annotations

import os

import requests


def get_weather_summary(location: str | None = None) -> dict:
    target = (location or "Baku").strip()

    if target.lower() in ("baku", "bakı"):
        latitude = 40.4093
        longitude = 49.8671
        city_name = "Bakı"
    else:
        try:
            geo_response = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": target,
                    "count": 1,
                    "language": "az",
                    "format": "json",
                },
                timeout=10,
            )
            geo_response.raise_for_status()

            results = geo_response.json().get("results") or []

            if not results:
                return {
                    "success": False,
                    "city": target,
                }

            location_data = results[0]

            latitude = location_data["latitude"]
            longitude = location_data["longitude"]
            city_name = location_data.get("name", target)

        except Exception:
            return {
                "success": False,
                "city": target,
            }

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "weather_code,"
                    "surface_pressure,"
                    "wind_speed_10m,"
                    "wind_direction_10m"
                ),
                "wind_speed_unit": "kmh",
                "timezone": "Asia/Baku",
            },
            timeout=10,
        )

        response.raise_for_status()

        current = response.json().get("current", {})

        temperature = current.get("temperature_2m")
        feels_like = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        weather_code = current.get("weather_code")
        pressure = current.get("surface_pressure")
        wind_speed = current.get("wind_speed_10m")
        wind_direction = current.get("wind_direction_10m")

        weather_descriptions = {
            0: "Açıq hava",
            1: "Əsasən açıq hava",
            2: "Qismən buludlu",
            3: "Buludlu",
            45: "Dumanlı",
            48: "Çənli",
            51: "Zəif çiskin",
            53: "Çiskin",
            55: "Güclü çiskin",
            61: "Zəif yağış",
            63: "Yağış",
            65: "Güclü yağış",
            71: "Zəif qar",
            73: "Qar",
            75: "Güclü qar",
            80: "Zəif yağış keçidləri",
            81: "Yağış keçidləri",
            82: "Güclü yağış keçidləri",
            95: "Şimşəkli hava",
            96: "Şimşək və dolu",
            99: "Güclü şimşək və dolu",
        }

        def get_wind_direction(degrees):
            if degrees is None:
                return "--"

            directions = [
                "Şimal",
                "Şimal-Şərq",
                "Şərq",
                "Cənub-Şərq",
                "Cənub",
                "Cənub-Qərb",
                "Qərb",
                "Şimal-Qərb",
            ]

            index = int((degrees + 22.5) / 45) % 8

            return directions[index]

        return {
            "success": True,
            "city": city_name,
            "temperature": temperature,
            "feels_like": feels_like,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": get_wind_direction(wind_direction),
            "weather_code": weather_code,
            "condition": weather_descriptions.get(
                weather_code,
                "Hava şəraiti müəyyən edilmədi"
            ),
        }

    except Exception:
        return {
            "success": False,
            "city": city_name,
        }
