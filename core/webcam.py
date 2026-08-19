"""Webcam capture and latest-frame streaming for EVA."""

import threading
import time


class WebcamStreamer:
    """Continuously capture the latest JPEG frame from the default webcam."""

    JPEG_QUALITY = 72
    MAX_DIM = 640
    WARMUP = 6

    def __init__(self):
        self._latest: bytes | None = None
        self._lock = threading.Lock()
        self._active = False
        self._thread: threading.Thread | None = None

    @property
    def is_active(self) -> bool:
        return self._active

    def get_latest_frame(self) -> bytes | None:
        """Return the most recent frame in a thread-safe way."""
        with self._lock:
            return self._latest

    def start(self) -> str:
        with self._lock:
            if self._active:
                return "already_active"
            self._active = True
            self._latest = None

        thread = threading.Thread(target=self._run, daemon=True)
        self._thread = thread
        thread.start()
        return "ok"

    def stop(self) -> None:
        with self._lock:
            self._active = False
            self._latest = None

    def _run(self) -> None:
        try:
            import cv2
        except ImportError:
            print("[Webcam] opencv-python yüklü deyil.")
            with self._lock:
                self._active = False
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Webcam] Kamera açılmadı.")
            with self._lock:
                self._active = False
            return

        for _ in range(self.WARMUP):
            cap.read()

        enc_params = [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY]

        try:
            while True:
                with self._lock:
                    if not self._active:
                        break

                ret, frame = cap.read()
                if not ret:
                    break

                height, width = frame.shape[:2]
                if max(height, width) > self.MAX_DIM:
                    scale = self.MAX_DIM / max(height, width)
                    frame = cv2.resize(
                        frame,
                        (int(width * scale), int(height * scale)),
                    )

                frame = cv2.flip(frame, 1)
                ok, buffer = cv2.imencode(".jpg", frame, enc_params)
                if ok:
                    with self._lock:
                        self._latest = buffer.tobytes()

                time.sleep(0.03)
        finally:
            cap.release()
            with self._lock:
                self._active = False
                self._latest = None
            print("[Webcam] Kamera serbest bırakıldı.")
