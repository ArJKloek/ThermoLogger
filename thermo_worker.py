from __future__ import annotations

import math
import random
import time
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal


class DummySMtc:
    """Synthetic thermocouple reader used when hardware is unavailable."""

    def __init__(self, channels: int = 8):
        self.channels = channels

    def get_temp(self, channel: int) -> float:
        """Return a plausible temperature value for the requested channel."""
        phase = channel * 0.6
        base = 24.0 + 3.0 * math.sin(time.time() / 5.0 + phase)
        noise = random.uniform(-0.3, 0.3)
        drift = 0.05 * channel
        return round(base + drift + noise, 2)


class ThermoThread(QThread):
    """Background reader that emits temperature readings periodically."""

    reading_ready = pyqtSignal(list)
    source_changed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, interval_sec: float = 1.0, channels: int = 8, parent=None):
        super().__init__(parent)
        self.interval_sec = max(0.1, float(interval_sec))
        self.channels = channels
        self._stop = False
        self._startup_error = ""
        self.device = None
        self.source = "unknown"
        self._init_device()

    def _init_device(self) -> None:
        """Try to use real hardware; fall back to the dummy generator."""
        try:
            import sm_tc

            self.device = sm_tc.SMtc(0)
            self.source = "hardware"
        except Exception as exc:  # pragma: no cover - depends on hardware
            self.device = DummySMtc(self.channels)
            self.source = "dummy"
            self._startup_error = str(exc)

    def run(self) -> None:  # pragma: no cover - involves timing and threads
        if self._startup_error:
            self.error.emit(f"Falling back to dummy: {self._startup_error}")
        self.source_changed.emit(self.source)

        while not self._stop:
            readings: List[float] = []
            for idx in range(self.channels):
                try:
                    readings.append(self.device.get_temp(idx + 1))
                except Exception as exc:
                    self.error.emit(str(exc))
                    readings.append(float("nan"))
            self.reading_ready.emit(readings)
            self.msleep(int(self.interval_sec * 1000))

    def stop(self, timeout_ms: int = 1000) -> None:
        self._stop = True
        self.wait(timeout_ms)
