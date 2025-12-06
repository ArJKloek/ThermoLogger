from __future__ import annotations

import math
import random
import time
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from perlin_noise import PerlinNoise
    HAS_PERLIN = True
except ImportError:
    HAS_PERLIN = False


class DummySMtc:
    """Synthetic thermocouple reader using Perlin noise for realistic temperature variation."""

    def __init__(self, channels: int = 8):
        self.channels = channels
        self.time_scale = 0.001  # Very slow time scale for extremely smooth variation
        if HAS_PERLIN:
            # Create independent Perlin noise generators for each channel with more octaves for smoothness
            self.noise_generators = [PerlinNoise(octaves=1, seed=ch) for ch in range(channels)]
        else:
            self.noise_generators = None

    def get_temp(self, channel: int) -> float:
        """Return a realistic temperature value using Perlin noise."""
        if channel < 1 or channel > self.channels:
            return float("nan")
        
        ch_idx = channel - 1
        base_temp = 20.0 + ch_idx * 2.0  # Slight offset per channel
        
        if HAS_PERLIN and self.noise_generators:
            # Use Perlin noise for smooth, realistic variations
            noise_val = self.noise_generators[ch_idx](time.time() * self.time_scale)
            temp = base_temp + 10.0 * noise_val
        else:
            # Fallback to very smooth sine wave if perlin_noise not installed
            phase = ch_idx * 0.6
            temp = base_temp + 2.5 * math.sin(time.time() / 15.0 + phase)
        
        return round(temp, 1)


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
        
        noise_source = "Perlin noise" if HAS_PERLIN else "sine wave (fallback)"
        self.source_changed.emit(self.source)
        self.error.emit(f"Using {noise_source} for dummy data")

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
