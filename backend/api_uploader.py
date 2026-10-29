"""Background uploader for ThermoLogger measurements."""

from __future__ import annotations

import json
import math
import os
import queue
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.error_logger import ErrorLogger


class MeasurementUploader:
    """Send logged temperature readings to the measurements API."""

    def __init__(self, timeout: float = 5.0):
        config_path = Path(__file__).resolve().parent.parent / "api_config.json"
        config = {}
        try:
            with config_path.open(encoding="utf-8") as config_file:
                config = json.load(config_file)
            if not isinstance(config, dict):
                raise ValueError("The config root must be a JSON object")
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            ErrorLogger.log_warning(f"Could not read API config {config_path}: {exc}")

        self.api_url = (os.getenv("API_URL") or config.get("api_url") or "http://localhost:8000").rstrip("/")
        self.device_id = os.getenv("DEVICE_ID") or config.get("device_id")
        self.token = os.getenv("DEVICE_TOKEN") or config.get("device_token")
        self.timeout = timeout
        self._queue = queue.Queue()
        self._stopping = threading.Event()
        self._thread = None

        if not self.device_id or not self.token:
            if self.device_id or self.token:
                ErrorLogger.log_warning("API upload disabled: DEVICE_ID and DEVICE_TOKEN are both required")
            return

        self._thread = threading.Thread(target=self._send_pending, daemon=True)
        self._thread.start()
        ErrorLogger.log_info(f"API upload enabled: {self.api_url}/api/v1/measurements")

    def submit(self, readings, settings_manager, logging_on: bool) -> bool:
        """Queue enabled, finite channel readings for upload."""
        if not self._thread:
            return False

        measurements = []
        for channel, value in enumerate(readings):
            if not settings_manager.is_channel_enabled(channel):
                continue
            try:
                temperature = float(value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(temperature):
                continue

            measurements.append({
                "measurement_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sensor": f"rtd{channel}",
                "value": temperature,
                "unit": "C",
                "quality": "good",
                "logging_on": logging_on,
                "metadata": {"channel_type": settings_manager.get_channel_type(channel)},
            })

        if not measurements:
            return False

        batch = {"device_id": self.device_id, "measurements": measurements}
        try:
            self._queue.put_nowait(batch)
            return True
        except queue.Full:
            ErrorLogger.log_warning("API upload skipped: previous measurement batch is still pending")
            return False

    def _send_pending(self) -> None:
        endpoint = f"{self.api_url}/api/v1/measurements"
        while not self._stopping.is_set():
            try:
                batch = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue

            request = urllib.request.Request(
                endpoint,
                data=json.dumps(batch).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    ErrorLogger.log_info(f"API measurement batch accepted: HTTP {response.status}")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                ErrorLogger.log_error(f"API measurement upload failed: {exc}")
            finally:
                self._queue.task_done()

    def close(self) -> None:
        """Stop accepting work and allow the daemon worker to exit."""
        self._stopping.set()