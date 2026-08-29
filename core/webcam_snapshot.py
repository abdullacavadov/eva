"""EVA webcam axınının son kadrı üçün paylaşılmış snapshot yolu."""

import tempfile
from pathlib import Path

LATEST_FRAME_PATH = Path(tempfile.gettempdir()) / "eva_webcam_latest.jpg"
