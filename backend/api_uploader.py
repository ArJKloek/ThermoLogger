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
from time import monotonic

from backend.error_logger import ErrorLogger

AVERAGE_INTERVAL_SECONDS = 5 * 60
AVERAGE_WINDOW_START_HOUR = 7
AVERAGE_WINDOW_END_HOUR = 17
BACKFILL_BATCH_SIZE = 500


class MeasurementUploader:
    """Send logged temperature readings to the measurements API."""

    def __init__(self, timeout: float = 5.0, on_uploaded=None):
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
        self.on_uploaded = on_uploaded
        self._queue = queue.Queue()
        self._stopping = threading.Event()
        self._thread = None
        self._sums = {}
        self._counts = {}
        self._average_started = None
        self.enabled = bool(self.device_id and self.token)

        if not self.enabled:
            if self.device_id or self.token:
                ErrorLogger.log_warning("API upload disabled: DEVICE_ID and DEVICE_TOKEN are both required")
            return

        self._thread = threading.Thread(target=self._send_pending, daemon=True)
        self._thread.start()
        ErrorLogger.log_info(f"API upload enabled: {self.api_url}/api/v1/measurements")

    @staticmethod
    def _finite_values(readings, settings_manager):
        """Yield (channel, temperature) for enabled channels with finite readings."""
        for channel, value in enumerate(readings):
            if not settings_manager.is_channel_enabled(channel):
                continue
            try:
                temperature = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(temperature):
                yield channel, temperature

    def _build_measurements(self, values, settings_manager, timestamp: datetime, logging_on: bool):
        iso_timestamp = timestamp.astimezone(timezone.utc).isoformat()  # naive = local time
        return [{
            "measurement_id": str(uuid.uuid4()),
            "timestamp": iso_timestamp,
            "sensor": f"rtd{channel}",
            "value": round(temperature, 2),
            "unit": "C",
            "quality": "good",
            "logging_on": logging_on,
            "metadata": {"channel_type": settings_manager.get_channel_type(channel)},
        } for channel, temperature in values]

    @staticmethod
    def _in_average_window(now: datetime) -> bool:
        return now.weekday() < 5 and AVERAGE_WINDOW_START_HOUR <= now.hour < AVERAGE_WINDOW_END_HOUR

    def submit(self, readings, settings_manager, logging_on: bool) -> bool:
        """Upload every reading while logging; otherwise a 5-minute average in the weekday window."""
        if not self._thread:
            return False

        now = datetime.now()
        values = list(self._finite_values(readings, settings_manager))

        if logging_on:
            self._reset_average()
            return self._enqueue(self._build_measurements(values, settings_manager, now, True))

        if not self._in_average_window(now):
            self._reset_average()
            return False

        if self._average_started is None:
            self._average_started = monotonic()
        for channel, temperature in values:
            self._sums[channel] = self._sums.get(channel, 0.0) + temperature
            self._counts[channel] = self._counts.get(channel, 0) + 1

        if monotonic() - self._average_started < AVERAGE_INTERVAL_SECONDS:
            return False

        averages = [(channel, self._sums[channel] / self._counts[channel]) for channel in sorted(self._sums)]
        self._reset_average()
        return self._enqueue(self._build_measurements(averages, settings_manager, now, False))

    def submit_backfill(self, history, settings_manager) -> bool:
        """Upload previously collected (timestamp, readings) entries, e.g. when logging auto-starts."""
        if not self._thread:
            return False

        measurements = []
        for timestamp, readings in history:
            values = self._finite_values(readings, settings_manager)
            measurements.extend(self._build_measurements(values, settings_manager, timestamp, True))

        queued = False
        for start in range(0, len(measurements), BACKFILL_BATCH_SIZE):
            queued = self._enqueue(measurements[start:start + BACKFILL_BATCH_SIZE]) or queued
        return queued

    def _reset_average(self) -> None:
        self._sums.clear()
        self._counts.clear()
        self._average_started = None

    def _enqueue(self, measurements) -> bool:
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
                    if self.on_uploaded:
                        self.on_uploaded(len(batch["measurements"]))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                ErrorLogger.log_error(f"API measurement upload failed: {exc}")
            finally:
                self._queue.task_done()

    def close(self) -> None:
        """Stop accepting work and allow the daemon worker to exit."""
        self._stopping.set()