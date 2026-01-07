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
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import io

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
        self.unplugged_channels: List[int] = []  # Channels with 0.00 mV (unplugged)
        self.unplugged_icon = None  # Cached unplugged icon image
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
        self.status_message: Optional[str] = None  # Custom status line for events (paused/reset)
        self.flash_ticks: int = 0  # Remaining flash cycles for channel highlight
        self.flash_phase: bool = False  # Toggle state for flashing effect

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
            # Load unplugged icon if not already loaded
            if self.unplugged_icon is None:
                self._load_unplugged_icon()
            
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

    def set_logging_status(self, is_logging: bool, last_log_time=None, message: Optional[str] = None):
        """Set the logging status to display on screen."""
        self.logging_active = is_logging
        if last_log_time:
            self.last_log_time = last_log_time
        # Store a short custom message (e.g., "Logging paused" / "Logging reset")
        self.status_message = message

    def set_history(self, history):
        """Set history deque for plotting (expects list of (datetime, readings))."""
        self.history = list(history) if history else []

    def start_flash_channels(self, cycles: int = 6):
        """Start a short flashing effect on channel labels during checks."""
        self.flash_ticks = max(0, cycles)
        self.flash_phase = False

    def stop_flash_channels(self):
        """Stop flashing and clear state."""
        self.flash_ticks = 0
        self.flash_phase = False

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
        """Draw matplotlib plot of last hour for enabled channels (excluding unplugged)."""
        if not self.history or not enabled_indices:
            return None

        # Filter out unplugged channels from the plot
        plot_indices = [idx for idx in enabled_indices if (idx + 1) not in self.unplugged_channels]
        
        if not plot_indices:
            return None

        cutoff = datetime.now() - timedelta(hours=1)
        series_times = []
        series_values = [[] for _ in plot_indices]

        for ts, vals in self.history:
            if ts >= cutoff:
                series_times.append(ts)
                for si, ch in enumerate(plot_indices):
                    if ch < len(vals):
                        v = vals[ch]
                        if isinstance(v, (int, float)):
                            v = max(0, min(150, v))
                        series_values[si].append(v)
                    else:
                        series_values[si].append(float("nan"))

        if not series_times:
            return None

        # Dynamic temp scale: +5°C above max, -5°C below min, rounded to nearest 5
        flat_vals = [v for series in series_values for v in series if isinstance(v, (int, float)) and not math.isnan(v)]
        if not flat_vals:
            return None
        
        data_min = min(flat_vals)
        data_max = max(flat_vals)
        # Round to nearest 5: floor(min-5) to nearest 5, ceil(max+5) to nearest 5
        vmin = int(math.floor((data_min - 5) / 5) * 5)
        vmax = int(math.ceil((data_max + 5) / 5) * 5)
        # Clamp to reasonable temperature range
        vmin = max(0, vmin)
        vmax = min(150, vmax)

        # Create matplotlib figure with fixed subplot positioning
        dpi = 100
        fig = Figure(figsize=(w/dpi, h/dpi), dpi=dpi, facecolor='white')
        ax = fig.add_subplot(111)
        
        # Line styles for each channel
        linestyles = ['-', ':', '--', '-.', (0, (3, 1, 1, 1, 1, 1))]
        
        # Plot each enabled channel (excluding unplugged)
        for si, ch_idx in enumerate(plot_indices):
            style = linestyles[si % len(linestyles)]
            ax.plot(series_times, series_values[si], 
                   linestyle=style, 
                   color='black', 
                   linewidth=1.5,
                   label=f'CH{ch_idx + 1}')
        
        # Configure axes
        ax.set_ylim(vmin, vmax)
        
        # Fix x-axis to exactly 1 hour: (now - 1 hour) to now
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        ax.set_xlim(one_hour_ago, now)
        
        ax.set_ylabel('Temperature (°C)', fontsize=8)
        ax.set_xlabel('Time', fontsize=8)
        ax.tick_params(axis='both', labelsize=7)
        
        # Set y-axis ticks every 5 degrees
        import numpy as np
        y_ticks = np.arange(vmin, vmax + 1, 5)
        ax.set_yticks(y_ticks)
        
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Format time axis to show clock times (HH:MM)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
        fig.autofmt_xdate(rotation=0, ha='center')
        
        # Use subplots_adjust for consistent positioning instead of tight_layout
        fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.15)
        
        # Render to PIL Image
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, facecolor='white', edgecolor='none')
        buf.seek(0)
        plot_img = Image.open(buf).convert('1')
        plt.close(fig)
        
        return plot_img, x, y

    def set_unplugged_channels(self, unplugged: List[int]) -> None:
        """Set the list of unplugged channels to display."""
        self.unplugged_channels = unplugged
        # Load unplugged icon if not already loaded
        if self.unplugged_icon is None:
            self._load_unplugged_icon()

    def _load_unplugged_icon(self) -> None:
        """Load and cache the unplugged icon image (resized to 30x30)."""
        try:
            # Get project root
            project_root = Path(__file__).parent.parent
            icon_paths = [
                project_root / "ui" / "unplugged.png",
                Path.home() / "ThermoLogger" / "ui" / "unplugged.png",
                "/home/pi/ThermoLogger/ui/unplugged.png",
            ]
            
            icon_path = None
            for path in icon_paths:
                if Path(path).exists():
                    icon_path = path
                    break
            
            if icon_path:
                img = Image.open(str(icon_path))
                # Convert to 1-bit first for e-paper compatibility
                img = img.convert("1")
                # Resize to 30x24 pixels without stretching
                img.thumbnail((30, 24), Image.Resampling.LANCZOS)
                # Store as 1-bit
                self.unplugged_icon = img
                logging.info(f"Loaded unplugged icon from: {icon_path}")
                print(f"[EPAPER] Loaded unplugged icon: {icon_path}")
            else:
                logging.warning("Unplugged icon not found")
                print("[EPAPER] Warning: unplugged.png not found")
        except Exception as e:
            logging.warning(f"Failed to load unplugged icon: {e}")
            print(f"[EPAPER] Warning: Failed to load unplugged icon: {e}")

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

            # Draw logging status or custom message (paused/reset/etc.)
            status_text = self.status_message or ("Logging: ON" if self.logging_active else "Logging: OFF")
            draw.text((250, 65), status_text, font=self.font_small, fill=0)

            # Show last log time when active, or when paused message is shown (helps indicate file not reset)
            show_last_log = self.logging_active or (self.status_message and "paused" in self.status_message.lower())
            if show_last_log and self.last_log_time:
                log_time_text = f"Last log: {self.last_log_time.strftime('%H:%M:%S')}"
                draw.text((450, 65), log_time_text, font=self.font_small, fill=0)

            # Determine enabled channels
            if self.settings_manager:
                enabled_indices = [i for i in range(len(readings)) if self.settings_manager.is_channel_enabled(i)]
            else:
                enabled_indices = list(range(len(readings)))

            enabled_count = len(enabled_indices)
            font_medium, font_unit, font_tc, font_digital = self._select_fonts(enabled_count)

            # Layout split: left for values, right for plot (50/50 split)
            left_width = int(self.width * 0.5)
            right_available = self.width - left_width - 10
            right_width = right_available  # Plot takes full available space
            # Align plot to the right edge
            plot_x = self.width - right_width - 10
            # Plot height is full available height
            plot_height = self.height - self.data_start_y - 10

            # Compute vertical spacing to fit all enabled channels in one column
            available_height = self.height - self.data_start_y - 10
            row_spacing = max(40, min(70, available_height // max(1, enabled_count)))

            # Display readings in a single column on the left
            linestyle_symbols = {0: '━', 1: '···', 2: '- -', 3: '-·-', 4: '--··'}
            for display_idx, idx in enumerate(enabled_indices):
                reading = readings[idx]
                x_pos = 20
                y_pos_current = self.data_start_y + display_idx * row_spacing

                label = f"CH {idx + 1}:"
                # Flash effect: invert label on alternating phases
                if self.flash_ticks > 0 and self.flash_phase:
                    label_bbox = draw.textbbox((x_pos, y_pos_current), label, font=font_medium)
                    draw.rectangle(label_bbox, fill=0)
                    draw.text((x_pos, y_pos_current), label, font=font_medium, fill=255)
                else:
                    draw.text((x_pos, y_pos_current), label, font=font_medium, fill=0)

                # Compute label width to place the unplugged icon just to the right
                label_bbox = draw.textbbox((x_pos, y_pos_current), label, font=font_medium)
                label_width = label_bbox[2] - label_bbox[0]

                # Add unplugged icon or line style indicator below channel label
                if self.flash_ticks == 0:
                    if (idx + 1) in self.unplugged_channels:
                        if self.unplugged_icon:
                            try:
                                icon_w, icon_h = self.unplugged_icon.size
                                icon_x = x_pos + label_width + 6  # small gap after text
                                # Vertically center icon relative to label text
                                label_height = label_bbox[3] - label_bbox[1]
                                icon_y = y_pos_current + max(0, (label_height - icon_h) // 2)
                                image.paste(self.unplugged_icon, (icon_x, icon_y))
                            except Exception as e:
                                print(f"[EPAPER] Error pasting icon: {e}")
                    else:
                        style_indicator = linestyle_symbols.get(display_idx % 5, '━')
                        draw.text((x_pos, y_pos_current + 25), style_indicator, font=self.font_small, fill=0)

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

            # Plot last hour on the right using matplotlib
            plot_result = self._draw_plot(draw, enabled_indices, plot_x, self.data_start_y, right_width, plot_height)
            if plot_result:
                plot_img, px, py = plot_result
                image.paste(plot_img, (px, py))

            # Partial refresh: when flashing, limit region to the channel area for speed
            region_x = 0
            region_y = max(0, self.data_start_y - 10)
            region_w = max(10, left_width)
            region_h = max(10, self.height - region_y - 5)

            if self.flash_ticks > 0:
                x, y, w, h = region_x, region_y, region_w, region_h
            else:
                x, y, w, h = 0, 0, self.width, self.height

            # Partial refresh the chosen region (partial mode was already activated in init_display)
            self.epd.display_Partial(
                self.epd.getbuffer(image),
                x,
                y,
                w,
                h
            )

            # Step flashing state
            if self.flash_ticks > 0:
                self.flash_phase = not self.flash_phase
                self.flash_ticks -= 1
            
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

