"""Webcam capture and latest-frame streaming for EVA."""

import threading
import time

from core.webcam_snapshot import LATEST_FRAME_PATH


class WebcamStreamer:
    """Continuously capture the latest JPEG frame from the default webcam."""

    JPEG_QUALITY = 72
    MAX_DIM = 640
    WARMUP = 6
    SNAPSHOT_INTERVAL = 0.10
    _active_instance: "WebcamStreamer | None" = None
    _instance_lock = threading.Lock()

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

    @classmethod
    def get_active_latest_frame(cls) -> bytes | None:
        """Return the latest frame from the currently active EVA webcam."""
        with cls._instance_lock:
            instance = cls._active_instance
        if instance is None or not instance.is_active:
            return None
        return instance.get_latest_frame()

    def start(self) -> str:
        with self._lock:
            if self._active:
                return "already_active"
            self._active = True
            self._latest = None

        with self._instance_lock:
            self.__class__._active_instance = self

        try:
            LATEST_FRAME_PATH.unlink(missing_ok=True)
        except Exception:
            pass

        thread = threading.Thread(target=self._run, daemon=True)
        self._thread = thread
        thread.start()
        return "ok"

    def stop(self) -> None:
        with self._lock:
            self._active = False
            self._latest = None
        with self._instance_lock:
            if self.__class__._active_instance is self:
                self.__class__._active_instance = None
        try:
            LATEST_FRAME_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    def _run(self) -> None:
        try:
            import cv2
        except ImportError:
            print("[Webcam] opencv-python yüklü deyil.")
            with self._lock:
                self._active = False
            with self._instance_lock:
                if self.__class__._active_instance is self:
                    self.__class__._active_instance = None
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Webcam] Kamera açılmadı.")
            with self._lock:
                self._active = False
            with self._instance_lock:
                if self.__class__._active_instance is self:
                    self.__class__._active_instance = None
            return

        for _ in range(self.WARMUP):
            cap.read()

        enc_params = [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY]
        last_snapshot = 0.0

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
                    jpeg = buffer.tobytes()
                    with self._lock:
                        self._latest = jpeg

                    now = time.monotonic()
                    if now - last_snapshot >= self.SNAPSHOT_INTERVAL:
                        tmp_path = LATEST_FRAME_PATH.with_suffix(".tmp")
                        try:
                            tmp_path.write_bytes(jpeg)
                            tmp_path.replace(LATEST_FRAME_PATH)
                            last_snapshot = now
                        except Exception:
                            try:
                                tmp_path.unlink(missing_ok=True)
                            except Exception:
                                pass

                time.sleep(0.03)
        finally:
            cap.release()
            with self._lock:
                self._active = False
                self._latest = None
            with self._instance_lock:
                if self.__class__._active_instance is self:
                    self.__class__._active_instance = None
            try:
                LATEST_FRAME_PATH.unlink(missing_ok=True)
            except Exception:
                pass
            print("[Webcam] Kamera serbest bırakıldı.")
