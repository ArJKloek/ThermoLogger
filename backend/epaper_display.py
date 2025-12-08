"""E-paper display handler for temperature sensor values."""

from __future__ import annotations

import os
import sys
import logging
from typing import List, Optional
from datetime import datetime

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

    def __init__(self, width: int = 800, height: int = 480):
        self.width = width
        self.height = height
        self.epd = None
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self.available = False
        self.last_readings: List[Optional[float]] = []
        self.last_update_time = None
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

            # Load Digital-7 Mono font for e-paper (monospace digital display look)
            font_path_options = [
                "/home/pi/.local/share/fonts/Digital-7-Mono.ttf",  # Raspberry Pi user fonts
                "/usr/local/share/fonts/Digital-7-Mono.ttf",  # System-wide fonts
                "/usr/share/fonts/truetype/Digital-7-Mono.ttf",
                "./fonts/Digital-7-Mono.ttf",  # Local fonts directory
                "fonts/Digital-7-Mono.ttf",
            ]

            font_path = None
            for path in font_path_options:
                if os.path.exists(path):
                    font_path = path
                    logging.info(f"Loaded font from: {font_path}")
                    print(f"[EPAPER] Loaded font from: {font_path}")
                    break

            if font_path:
                self.font_large = ImageFont.truetype(font_path, 48)
                self.font_medium = ImageFont.truetype(font_path, 36)
                self.font_small = ImageFont.truetype(font_path, 24)
            else:
                # Fallback to default font
                logging.warning("Digital-7-Mono font not found, using default font")
                print("[EPAPER] Digital-7-Mono font not found, using default font")
                self.font_large = ImageFont.load_default()
                self.font_medium = ImageFont.load_default()
                self.font_small = ImageFont.load_default()

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

    def display_readings(self, readings: List[float]) -> None:
        """Update only temperature readings with partial refresh (fast update)."""
        print(f"[EPAPER] display_readings called with {len(readings)} readings: {[f'{r:.1f}' for r in readings[:3]]}...")
        print(f"[EPAPER] available={self.available}, initialized={self.initialized}")
        
        if not self.available or not self.epd:
            print(f"[EPAPER] Skipping - available={self.available}, epd={self.epd is not None}")
            return

        try:
            self.last_readings = readings
            self.last_update_time = datetime.now()

            # If not yet initialized, do full init first
            if not self.initialized:
                print("[EPAPER] Not initialized, calling init_display()")
                self.init_display()
                return  # Return after init, next call will do the update

            print(f"[EPAPER] Drawing {len(readings)} temperature readings...")
            
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

            # Display readings in a grid (2 columns)
            for idx, reading in enumerate(readings):
                col = idx % 2
                row = idx // 2

                x_pos = 20 + col * (self.width // 2)
                y_pos_current = self.data_start_y + row * 70

                # Channel label
                label = f"CH {idx + 1}:"
                draw.text((x_pos, y_pos_current), label, font=self.font_medium, fill=0)

                # Temperature value
                if isinstance(reading, float) and not float('nan'):
                    value_text = f"{reading:.1f}°C"
                else:
                    value_text = "-- °C"
                draw.text((x_pos + 150, y_pos_current), value_text, font=self.font_medium, fill=0)

            print("[EPAPER] Calling display_Partial...")
            # Partial refresh the full screen (partial mode was already activated in init_display)
            self.epd.display_Partial(
                self.epd.getbuffer(image),
                0,
                0,
                self.width,
                self.height
            )
            print(f"[EPAPER] Updated display at {timestamp}")

        except Exception as e:
            logging.error(f"Error displaying on e-paper: {e}")
            print(f"[EPAPER ERROR] {e}")
            import traceback
            traceback.print_exc()

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

