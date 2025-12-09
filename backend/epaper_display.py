"""E-paper display handler for temperature sensor values."""

from __future__ import annotations

import os
import sys
import logging
import math
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from waveshare_epd import epd7in5_V2
    HAS_EPAPER = True
    print("[EPAPER] Successfully imported waveshare_epd library")
except ImportError as e:
    HAS_EPAPER = False
    print(f"[EPAPER] Failed to import waveshare_epd: {e}")
except Exception as e:
    HAS_EPAPER = False
    print(f"[EPAPER] Error importing waveshare_epd: {e}")


class EpaperDisplay:
    """Handler for 7.5inch e-paper display (waveshare EPD)."""

    def __init__(self, width: int = 800, height: int = 480, settings_manager=None):
        self.width = width
        self.height = height
        self.epd = None
        self.settings_manager = settings_manager
        self.history = []
        # Standard fonts for headers and labels
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self.font_unit = None
        self.font_tc_type = None
        # Keep paths so we can resize dynamically later
        self.font_path_normal = None
        self.font_path_bold = None
        self.font_path_oblique = None
        self.font_path_digital = None
        # Digital-7 Mono fonts for temperature values only
        self.font_digital_large = None
        self.font_digital_medium = None
        self.available = False
        self.last_readings: List[Optional[float]] = []
        self.last_update_time = None
        self.logging_active = False
        self.last_log_time = None
        self.initialized = False
        self.partial_mode_active = False  # Track if we're in partial update mode
        self.data_start_y = 110  # Y position where temperature data starts
        self.data_height = 360  # Height of data region (4 rows * 70 pixels + margin)

        print(f"[EPAPER] EpaperDisplay __init__, HAS_EPAPER={HAS_EPAPER}")
        
        if HAS_EPAPER:
            self._init_epaper()
        else:
            print("[EPAPER] waveshare_epd not available, e-paper display disabled")

    def _init_epaper(self) -> None:
        """Initialize e-paper display and fonts."""
        try:
            print("[EPAPER] Starting initialization...")
            logging.info("Initializing e-paper display...")
            self.epd = epd7in5_V2.EPD()
            print("[EPAPER] EPD object created")
            
            self.epd.init()
            print("[EPAPER] EPD init() called")
            
            self.epd.Clear()
            print("[EPAPER] EPD cleared")

            # Load fonts
            # Standard fonts for headers and labels
            try:
                self.font_path_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                self.font_path_normal = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                self.font_path_oblique = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"

                self.font_large = ImageFont.truetype(self.font_path_bold, 32)
                self.font_medium = ImageFont.truetype(self.font_path_normal, 32)
                self.font_small = ImageFont.truetype(self.font_path_normal, 18)
                self.font_unit = ImageFont.truetype(self.font_path_normal, 20)
                self.font_tc_type = ImageFont.truetype(self.font_path_oblique, 14)
            except:
                # Fallback to default font
                self.font_large = ImageFont.load_default()
                self.font_medium = ImageFont.load_default()
                self.font_small = ImageFont.load_default()
                self.font_unit = ImageFont.load_default()
                self.font_tc_type = ImageFont.load_default()
                self.font_path_bold = None
                self.font_path_normal = None
                self.font_path_oblique = None

            # Load Digital-7 Mono font for temperature values only
            # Get the project root directory (parent of backend/)
            project_root = Path(__file__).parent.parent
            
            font_path_options = [
                project_root / "fonts" / "Digital-7-Mono.ttf",
                project_root / "fonts" / "Digital-7 Mono.ttf",
                project_root / "fonts" / "digital-7-mono.ttf",
                Path.home() / ".local/share/fonts/digital-7-Mono.ttf",  # User fonts (~/.)
                "/home/pi/ThermoLogger/fonts/Digital-7-Mono.ttf",  # Local project fonts on Pi
                "/home/pi/.local/share/fonts/Digital-7-Mono.ttf",  # Raspberry Pi user fonts
                "/usr/local/share/fonts/Digital-7-Mono.ttf",  # System-wide fonts
                "/usr/share/fonts/truetype/Digital-7-Mono.ttf",
            ]

            font_path = None
            for path in font_path_options:
                if Path(path).exists():
                    font_path = str(path)
                    logging.info(f"Loaded Digital-7-Mono font from: {font_path}")
                    print(f"[EPAPER] Loaded Digital-7-Mono font from: {font_path}")
                    break

            if font_path:
                self.font_path_digital = font_path
                self.font_digital_large = ImageFont.truetype(font_path, 72)
                self.font_digital_medium = ImageFont.truetype(font_path, 60)
            else:
                # Fallback to default font for temps too
                logging.warning("Digital-7-Mono font not found, using default font for temperatures")
                print("[EPAPER] Digital-7-Mono font not found, using default font for temperatures")
                self.font_digital_large = ImageFont.load_default()
                self.font_digital_medium = ImageFont.load_default()
                self.font_path_digital = None

            self.available = True
            logging.info("E-paper display initialized successfully")
            print("[EPAPER] Initialization complete - display is available")
        except Exception as e:
            logging.warning(f"E-paper display not available: {e}")
            print(f"[EPAPER ERROR] Initialization failed: {e}")
            self.available = False

    def init_display(self, title: str = "Temperature Logger") -> None:
        """Initialize the display with static header (title, timestamp line, separator)."""
        if not self.available or not self.epd:
            return

        try:
            # Create full image with header
            image = Image.new("1", (self.width, self.height), 255)  # White background
            draw = ImageDraw.Draw(image)

            # Draw title
            draw.text((10, 10), title, font=self.font_large, fill=0)

            # Draw horizontal line
            draw.line((10, 95, self.width - 10, 95), fill=0, width=2)

            # Do a full refresh for initial setup with init_fast (faster than init)
            self.epd.init_fast()
            self.epd.display(self.epd.getbuffer(image))
            
            # Now switch to partial mode for future updates
            self.epd.init_part()
            self.partial_mode_active = True
            self.initialized = True
            logging.info("E-paper display header initialized and switched to partial mode")
            print("[EPAPER] Display initialized, switched to partial update mode")
        except Exception as e:
            logging.error(f"Error initializing e-paper display: {e}")
            print(f"[EPAPER ERROR] {e}")

    def set_logging_status(self, is_logging: bool, last_log_time=None):
        """Set the logging status to display on screen."""
        self.logging_active = is_logging
        if last_log_time:
            self.last_log_time = last_log_time

    def set_history(self, history):
        """Set history deque for plotting (expects list of (datetime, readings))."""
        self.history = list(history) if history else []

    def _make_font(self, path: Optional[str], size: int, fallback) -> ImageFont.FreeTypeFont:
        """Create a font from path if available, otherwise fallback."""
        if path:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
        return fallback

    def _select_fonts(self, enabled_count: int):
        """Select fonts dynamically based on how many channels are displayed."""
        # Default sizes
        medium_size = 32
        unit_size = 20
        tc_size = 14
        digital_size = 60

        if enabled_count > 6:
            medium_size = 24
            unit_size = 16
            tc_size = 11
            digital_size = 42
        elif enabled_count > 4:
            medium_size = 28
            unit_size = 18
            tc_size = 12
            digital_size = 50

        font_medium = self._make_font(self.font_path_normal, medium_size, self.font_medium)
        font_unit = self._make_font(self.font_path_normal, unit_size, self.font_unit)
        font_tc = self._make_font(self.font_path_oblique, tc_size, self.font_tc_type)
        font_digital = self._make_font(self.font_path_digital, digital_size, self.font_digital_medium)

        return font_medium, font_unit, font_tc, font_digital

    def _draw_plot(self, draw: ImageDraw.ImageDraw, enabled_indices: List[int], x: int, y: int, w: int, h: int):
        """Draw simple line plot of last hour for enabled channels with dynamic scale."""
        if not self.history or not enabled_indices:
            return

        cutoff = datetime.now() - timedelta(hours=1)
        series_times = []
        series_values = [[] for _ in enabled_indices]

        for ts, vals in self.history:
            if ts >= cutoff:
                series_times.append(ts)
                for si, ch in enumerate(enabled_indices):
                    if ch < len(vals):
                        # Clamp to [0,150]
                        v = vals[ch]
                        if isinstance(v, (int, float)):
                            v = max(0, min(150, v))
                        series_values[si].append(v)
                    else:
                        series_values[si].append(float("nan"))

        if not series_times:
            return

        vmin, vmax = 0, 150

        # Dynamic time window: use actual data span
        t_min = series_times[0]
        t_max = series_times[-1]
        t_span = (t_max - t_min).total_seconds()
        if t_span < 1:
            t_span = 1

        # Downsample to fit width
        max_points = max(20, w // 2)
        step = max(1, len(series_times) // max_points)
        indices = range(0, len(series_times), step)

        def x_pos(idx):
            return x + int(w * (series_times[idx] - t_min).total_seconds() / t_span)

        def y_pos(val):
            if not isinstance(val, (int, float)) or math.isnan(val):
                return None
            return y + h - int((val - vmin) / (vmax - vmin) * h)

        # Line styles: solid, dashed, dotted, dashdot cycle
        def draw_series(points, style):
            if style == "solid":
                for i in range(1, len(points)):
                    if points[i-1] and points[i]:
                        draw.line([points[i-1], points[i]], fill=0, width=2)
            elif style == "dashed":
                for i in range(1, len(points)):
                    if points[i-1] and points[i] and i % 2 == 0:
                        draw.line([points[i-1], points[i]], fill=0, width=2)
            elif style == "dotted":
                for pt in points:
                    if pt:
                        draw.ellipse([pt[0]-1, pt[1]-1, pt[0]+1, pt[1]+1], fill=0)
            elif style == "dashdot":
                for i in range(1, len(points)):
                    if points[i-1] and points[i]:
                        if i % 4 in (0,1):
                            draw.line([points[i-1], points[i]], fill=0, width=2)
                        else:
                            draw.ellipse([points[i][0]-1, points[i][1]-1, points[i][0]+1, points[i][1]+1], fill=0)

        styles = ["solid", "dashed", "dotted", "dashdot"]

        for si, series in enumerate(series_values):
            pts = []
            for idx in indices:
                if idx >= len(series):
                    break
                xpt = x_pos(idx)
                ypt = y_pos(series[idx])
                pts.append((xpt, ypt) if ypt is not None else None)
            draw_series(pts, styles[si % len(styles)])

        # Axes and labels
        draw.rectangle([x, y, x + w, y + h], outline=0, width=1)

    def display_readings(self, readings: List[float]):
        """Update only temperature readings with partial refresh (fast update).
        Returns the PIL Image that was displayed."""
        if not self.available or not self.epd:
            return None

        try:
            self.last_readings = readings
            self.last_update_time = datetime.now()

            # If not yet initialized, do full init first
            if not self.initialized:
                self.init_display()
                return None  # Return after init, next call will do the update
            
            # Create full image (we need the full canvas for getbuffer)
            image = Image.new("1", (self.width, self.height), 255)  # White background
            draw = ImageDraw.Draw(image)

            # Redraw the title (needed for full image buffer)
            draw.text((10, 10), "Temperature Logger", font=self.font_large, fill=0)

            # Draw horizontal line
            draw.line((10, 95, self.width - 10, 95), fill=0, width=2)

            # Draw timestamp in update region
            timestamp = self.last_update_time.strftime("%H:%M:%S")
            draw.text((10, 65), f"Updated: {timestamp}", font=self.font_small, fill=0)

            # Draw logging status
            if self.logging_active:
                status_text = "Logging: ON"
                draw.text((250, 65), status_text, font=self.font_small, fill=0)
                if self.last_log_time:
                    log_time_text = f"Last log: {self.last_log_time.strftime('%H:%M:%S')}"
                    draw.text((450, 65), log_time_text, font=self.font_small, fill=0)
            else:
                status_text = "Logging: OFF"
                draw.text((250, 65), status_text, font=self.font_small, fill=0)

            # Determine enabled channels
            if self.settings_manager:
                enabled_indices = [i for i in range(len(readings)) if self.settings_manager.is_channel_enabled(i)]
            else:
                enabled_indices = list(range(len(readings)))

            enabled_count = len(enabled_indices)
            font_medium, font_unit, font_tc, font_digital = self._select_fonts(enabled_count)

            # Layout split: left for values, right for plot (50/50 split)
            left_width = int(self.width * 0.5)
            right_x = left_width + 10
            right_available = self.width - right_x - 10
            right_width = int(right_available * 0.8)  # Plot takes 80% of available space

            # Compute vertical spacing to fit all enabled channels in one column
            available_height = self.height - self.data_start_y - 10
            row_spacing = max(40, min(70, available_height // max(1, enabled_count)))

            # Display readings in a single column on the left
            for display_idx, idx in enumerate(enabled_indices):
                reading = readings[idx]
                x_pos = 20
                y_pos_current = self.data_start_y + display_idx * row_spacing

                label = f"CH {idx + 1}:"
                draw.text((x_pos, y_pos_current), label, font=font_medium, fill=0)

                try:
                    temp_val = float(reading)
                    if not math.isnan(temp_val):
                        value_text = f"{temp_val:.1f}"
                        unit_text = "°C"
                    else:
                        value_text = "--"
                        unit_text = "°C"
                except (TypeError, ValueError):
                    value_text = "--"
                    unit_text = "°C"
                
                draw.text((x_pos + 150, y_pos_current), value_text, font=font_digital, fill=0)
                draw.text((x_pos + 320, y_pos_current + 5), unit_text, font=font_unit, fill=0)
                
                if self.settings_manager:
                    tc_type = self.settings_manager.get_channel_type(idx)
                    draw.text((x_pos + 320, y_pos_current + 35), tc_type, font=font_tc, fill=0)

            # Plot last hour on the right
            self._draw_plot(draw, enabled_indices, right_x, 110, right_width, self.height - 120)

            # Partial refresh the full screen (partial mode was already activated in init_display)
            self.epd.display_Partial(
                self.epd.getbuffer(image),
                0,
                0,
                self.width,
                self.height
            )
            
            return image  # Return the image for preview

        except Exception as e:
            logging.error(f"Error displaying on e-paper: {e}")
            print(f"[EPAPER ERROR] {e}")
            import traceback
            traceback.print_exc()
            return None

    def clear(self) -> None:
        """Clear the e-paper display."""
        if self.available and self.epd:
            try:
                self.epd.init()
                self.epd.Clear()
                self.initialized = False
                self.partial_mode_active = False
            except Exception as e:
                logging.error(f"Error clearing e-paper: {e}")

    def sleep(self) -> None:
        """Put e-paper display into sleep mode."""
        if self.available and self.epd:
            try:
                self.epd.sleep()
            except Exception as e:
                logging.error(f"Error putting e-paper to sleep: {e}")

