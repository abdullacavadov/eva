"""React UI-dan alınan cari geolokasiyanı EVA runtime üçün saxlayır."""

from __future__ import annotations

import threading


_lock = threading.Lock()
_location: dict[str, float] | None = None


def set_current_location(latitude: float, longitude: float) -> None:
    global _location
    with _lock:
        _location = {
            "latitude": float(latitude),
            "longitude": float(longitude),
        }


def get_current_location() -> dict[str, float] | None:
    with _lock:
        return dict(_location) if _location else None
