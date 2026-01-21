import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QPixmap, QImage, QPainter, QFont
from PyQt5 import uic

# Optional GPIO support for physical buttons (only on Raspberry Pi)
try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from backend.thermo_worker import ThermoThread
from backend.epaper_display import EpaperDisplay
from backend.thermo_logger import ThermoLogger
from backend.settings_manager import SettingsManager
from ui.settings_dialog import SettingsDialog


def load_fonts():
    """Load custom fonts from the fonts directory and system."""
    fonts_dir = Path(__file__).parent / "fonts"
    
    # Try to load fonts from local fonts directory
    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.ttf"):
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id >= 0:
                print(f"Loaded font: {font_file.name}")
            else:
                print(f"Failed to load font: {font_file.name}")
    else:
        print(f"Fonts directory not found at {fonts_dir}")
    
    # Try to load system fonts for Raspberry Pi
    system_font_paths = [
        "/usr/share/fonts/truetype/dejavu/",
        "/usr/share/fonts/truetype/liberation/",
    ]
    
    for font_dir in system_font_paths:
        if Path(font_dir).exists():
            for font_file in Path(font_dir).glob("*.ttf"):
                try:
                    font_id = QFontDatabase.addApplicationFont(str(font_file))
                    if font_id >= 0:
                        print(f"Loaded system font: {font_file.name}")
                except Exception as e:
                    pass


class HardwareButtons:
    """Configure Raspberry Pi GPIO buttons (active-LOW) with light debounce."""

    def __init__(self, callback, pin_map=None, hold_time_ms=200, poll_interval_ms=50, 
                 confirmation_count=2, startup_delay_ms=2000):
        self.callback = callback
        self.pin_map = pin_map or {1: 16, 2: 13, 3: 15, 4: 31}  # BOARD numbering
        self.hold_time_ms = hold_time_ms
        self.poll_interval_ms = poll_interval_ms
        self.confirmation_count = confirmation_count
        self.startup_delay_ms = startup_delay_ms
        
        # Track how long each pin has been held LOW (pressed)
        self.pin_hold_time = {pin: 0 for pin in self.pin_map.values()}
        self.pin_consecutive_low = {pin: 0 for pin in self.pin_map.values()}
        self.pin_pressed_triggered = {pin: False for pin in self.pin_map.values()}
        
        # Startup grace period flag
        self.startup_grace_active = True
        
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available")
        
        self._setup()
        self._start_polling()

    def _setup(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        for button_num, pin in self.pin_map.items():
            # Buttons are active-LOW with pull-up
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # Read initial state
            initial_state = GPIO.input(pin)
            print(f"[GPIO] Button {button_num} on pin {pin}: initial state={initial_state} "
                  f"(0=pressed/LOW, 1=unpressed/HIGH)")

        print(f"[GPIO] Buttons ready on pins {list(self.pin_map.values())}, "
              f"hold_time={self.hold_time_ms}ms, confirmation={self.confirmation_count} polls, "
              f"startup_delay={self.startup_delay_ms}ms")
        print("[GPIO] Using active-LOW button logic (pin goes LOW when pressed)")

    def _start_polling(self):
        """Start polling pins using Qt timer after startup grace period."""
        from PyQt5.QtCore import QTimer
        
        # Start grace period timer first
        self.grace_timer = QTimer()
        self.grace_timer.setSingleShot(True)
        self.grace_timer.timeout.connect(self._end_grace_period)
        self.grace_timer.start(self.startup_delay_ms)
        print(f"[GPIO] Startup grace period active for {self.startup_delay_ms}ms - buttons disabled")
        
        # Start polling timer (but it won't trigger presses during grace period)
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_pins)
        self.poll_timer.start(self.poll_interval_ms)

    def _end_grace_period(self):
        """End the startup grace period and enable button detection."""
        self.startup_grace_active = False
        
        # Sanity check for active-LOW: unpressed should be HIGH. If many are LOW, wiring/noise.
        low_count = 0
        for button_num, pin in self.pin_map.items():
            state = GPIO.input(pin)
            if state == 0:
                low_count += 1
                print(f"[GPIO] WARNING: Button {button_num} (pin {pin}) is LOW at startup - unexpected!")
        
        if low_count >= 3:
            print(f"[GPIO] ERROR: {low_count}/4 pins are LOW at startup - buttons DISABLED due to wiring/noise issue")
            print("[GPIO] Fix: Check wiring or add proper pull-ups")
            self.startup_grace_active = True  # Keep grace period active = buttons stay disabled
            return
        
        # Clear any accumulated state during grace period
        for pin in self.pin_map.values():
            self.pin_hold_time[pin] = 0
            self.pin_consecutive_low[pin] = 0
            self.pin_pressed_triggered[pin] = False
        print("[GPIO] Startup grace period ended - buttons now active")

    def _poll_pins(self):
        """Poll all pins with multi-stage confirmation to filter noise.
        Active-LOW logic: pin is LOW (0) when pressed."""
        # Skip polling during startup grace period
        if self.startup_grace_active:
            return
        
        for button_num, pin in self.pin_map.items():
            pin_state = GPIO.input(pin)
            
            # Active-LOW: Button pressed when pin is LOW (0)
            if pin_state == 0:  # Pin is LOW (button pressed)
                self.pin_consecutive_low[pin] += 1
                self.pin_hold_time[pin] += self.poll_interval_ms
                
                # Stage 1: Require N consecutive LOW readings to confirm button press
                if self.pin_consecutive_low[pin] < self.confirmation_count:
                    continue
                
                # Stage 2: Require minimum hold duration
                if self.pin_hold_time[pin] >= self.hold_time_ms and not self.pin_pressed_triggered[pin]:
                    print(f"[GPIO] Button {button_num} confirmed PRESSED (LOW) for {self.pin_hold_time[pin]}ms "
                          f"(after {self.pin_consecutive_low[pin]} consecutive polls) -> PRESS REGISTERED")
                    self.pin_pressed_triggered[pin] = True
                    try:
                        self.callback(button_num)
                    except Exception as exc:
                        print(f"[GPIO] Button handler error: {exc}")
            else:  # Pin is HIGH (button not pressed)
                if self.pin_hold_time[pin] > 0:
                    held_time = self.pin_hold_time[pin]
                    consecutive = self.pin_consecutive_low[pin]
                    if consecutive < self.confirmation_count:
                        print(f"[GPIO] Button {button_num} noise spike: {held_time}ms, "
                              f"{consecutive} polls (< {self.confirmation_count}) - filtered")
                    elif held_time < self.hold_time_ms:
                        print(f"[GPIO] Button {button_num} released after {held_time}ms (ignored - too brief)")
                
                # Reset counters when pin goes HIGH (button released)
                self.pin_hold_time[pin] = 0
                self.pin_consecutive_low[pin] = 0
                self.pin_pressed_triggered[pin] = False

    def cleanup(self):
        try:
            if hasattr(self, 'poll_timer'):
                self.poll_timer.stop()
            if hasattr(self, 'grace_timer'):
                self.grace_timer.stop()
            GPIO.cleanup()
            print("[GPIO] Cleanup complete")
        except Exception as exc:
            print(f"[GPIO] Cleanup error: {exc}")


class SensorWidget(QWidget):
    """Reusable widget for displaying sensor data."""
    
    def __init__(self, sensor_name="Sensor", parent=None):
        super().__init__(parent)
        self.sensor_name = sensor_name
        self.is_unplugged = False
        self.load_ui()
    
    def load_ui(self):
        """Load the sensor UI file."""
        ui_dir = Path(__file__).parent / "ui"
        sensor_ui_file = ui_dir / "sensor.ui"
        
        # Load the sensor.ui file
        if sensor_ui_file.exists():
            try:
                uic.loadUi(str(sensor_ui_file), self)
                # Update the sensor name if there's a label named 'label_name'
                if hasattr(self, 'label_name'):
                    self.label_name.setText(self.sensor_name)
                # Display "C" on the degrees LCD
                if hasattr(self, 'lcdDegrees'):
                    self.lcdDegrees.display("C")
            except Exception as e:
                print(f"Error loading sensor UI: {e}")
        else:
            print(f"Warning: {sensor_ui_file} not found. Please create sensor.ui")
    
    def update_value(self, value):
        """Update the sensor value display."""
        # Update the label_value with the temperature value
        if hasattr(self, 'label_value'):
            if self.is_unplugged:
                self.label_value.setText("-- °C")
                return
            try:
                numeric_value = float(value)
                text = f"{numeric_value:.1f}°C"
            except (TypeError, ValueError):
                text = "-- °C"
            self.label_value.setText(text)

    def set_unplugged(self, unplugged: bool):
        """Visually dim the widget when the channel is unplugged."""
        self.is_unplugged = unplugged
        if hasattr(self, 'label_name'):
            self.label_name.setStyleSheet("color: #888;" if unplugged else "")
        if hasattr(self, 'label_value'):
            self.label_value.setStyleSheet("color: #888;" if unplugged else "")
            if unplugged:
                self.label_value.setText("-- °C")


class PlotWindow(QWidget):
    """Separate window for displaying temperature plot."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Temperature Plot - Last Hour")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create matplotlib figure and canvas
        self.fig = Figure(figsize=(8, 6))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        
        self.ax.set_title("Last Hour Temperatures")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("°C")
        self.fig.autofmt_xdate()
        
    def update_plot(self, history, channel_count, settings_manager):
        """Update the plot with current history data."""
        if not history:
            return
            
        cutoff = datetime.now() - timedelta(hours=1)
        times = []
        values = []
        
        # Filter history for last hour
        for ts, vals in history:
            if ts >= cutoff:
                times.append(ts)
                values.append(vals)
        
        if not times:
            return
        
        self.ax.clear()
        self.ax.set_title("Last Hour Temperatures")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("°C")
        
        enabled_indices = [i for i in range(channel_count) if settings_manager.is_channel_enabled(i)]
        
        # Line styles
        linestyles = ['-', ':', '--', '-.', (0, (3, 1, 1, 1, 1, 1))]
        
        # Build series per enabled channel
        for si, idx in enumerate(enabled_indices):
            series = [row[idx] for row in values if idx < len(row)]
            style = linestyles[si % len(linestyles)]
            self.ax.plot(times, series, label=f"CH{idx + 1}", linestyle=style, linewidth=1.5)
        
        if enabled_indices:
            self.ax.legend(loc="upper left")
        
        # Format time axis
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
        
        self.ax.grid(True, alpha=0.3)
        self.fig.autofmt_xdate(rotation=0, ha='center')
        self.canvas.draw()


class EpaperPreviewWindow(QWidget):
    """Preview window showing what's displayed on the e-paper."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("E-Paper Display Preview")
        self.setGeometry(150, 150, 800, 480)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Label to show the preview image
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: white; border: 2px solid black;")
        layout.addWidget(self.preview_label)
        
    def update_preview(self, image):
        """Update the preview with a PIL Image."""
        if image:
            # Convert PIL Image to QPixmap
            # PIL image is mode "1" (1-bit), convert to RGB for display
            rgb_image = image.convert("RGB")
            data = rgb_image.tobytes("raw", "RGB")
            qimage = QImage(data, rgb_image.width, rgb_image.height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)
            self.preview_label.setPixmap(pixmap)


class MainWindow(QMainWindow):
    """Main application window for Atlas Logger."""
    button_pressed = pyqtSignal(int)  # Emitted for both GPIO and on-screen buttons
    
    def __init__(self):
        super().__init__()
        self.channel_count = 8
        self.sensors = []
        self.worker = None
        self.settings_manager = SettingsManager()
        self.epaper = EpaperDisplay(settings_manager=self.settings_manager)
        self.logger = ThermoLogger(settings_manager=self.settings_manager)
        self.last_readings = []
        self.unplugged_channels = []  # 1-based channel numbers reported by worker
        self.history = deque(maxlen=3600)  # store last hour at 1 Hz
        self.epaper_update_timer = QTimer()
        self.epaper_update_timer.timeout.connect(self.update_epaper_display)
        self.epaper_base_interval = 5000  # ms
        self.epaper_update_timer.start(self.epaper_base_interval)  # Update e-paper every 5 seconds
        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.on_logging_timer)
        self.logging_interval = 5  # Default 5 seconds
        self.gpio_buttons = None
        
        # Create e-paper preview window if enabled in settings
        self.preview_window = None
        if self.settings_manager.show_preview:
            self.preview_window = EpaperPreviewWindow()
            self.preview_window.show()
        
        # Create plot window (initially hidden)
        self.plot_window = None
        
        # Route all button events through a signal to keep UI thread-safe
        self.button_pressed.connect(self.handle_virtual_button)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface from the UI file."""
        # Get the path to the UI file
        ui_dir = Path(__file__).parent / "ui"
        ui_file = ui_dir / "main.ui"
        
        # Check if UI file exists
        if not ui_file.exists():
            print(f"Error: UI file not found at {ui_file}")
            sys.exit(1)
        
        # Load the UI file using uic
        try:
            uic.loadUi(str(ui_file), self)
        except Exception as e:
            print(f"Error loading UI file: {e}")
            sys.exit(1)
        
        # Ensure menubar is visible (critical for Raspberry Pi / PyQt6)
        if hasattr(self, 'menubar'):
            self.menubar.setNativeMenuBar(False)
            self.menubar.setVisible(True)
            print(f"[MENU] Menubar configured: visible={self.menubar.isVisible()}")
        
        # Build layouts
        self.setup_layouts()
        self.setup_sensors()

        # Connect menu actions
        self.connect_logging_controls()

        # Wire hardware GPIO buttons (if available)
        self._init_gpio_buttons()

        # Start background reader (uses dummy data when hardware is absent)
        self.start_worker()
    
    def setup_layouts(self):
        """Create main layout with sensors grid."""
        main_layout = QVBoxLayout()
        self.centralwidget.setLayout(main_layout)

        # Sensors grid
        self.sensors_container = QWidget()
        self.sensors_layout = QGridLayout(self.sensors_container)
        main_layout.addWidget(self.sensors_container)

        # Virtual buttons to mimic forthcoming physical buttons on the Pi
        self.buttons_container = QWidget()
        self.buttons_layout = QHBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 8, 0, 0)
        self.buttons_layout.setSpacing(12)

        self.soft_buttons = []
        button_labels = ["Start/Pause", "Reset", "Check TC", "(Reserved)"]
        for idx in range(1, 5):
            button = QPushButton(button_labels[idx - 1])
            button.setObjectName(f"softButton{idx}")
            button.setMinimumHeight(40)
            button.clicked.connect(lambda _, i=idx: self.on_soft_button_pressed(i))
            self.soft_buttons.append(button)
            self.buttons_layout.addWidget(button)

        self.buttons_layout.addStretch()
        main_layout.addWidget(self.buttons_container)

    def setup_sensors(self):
        """Add multiple sensor widgets to the sensors grid - only enabled channels."""
        display_idx = 0
        for idx in range(self.channel_count):
            sensor = SensorWidget(f"Thermocouple {idx + 1}")
            self.sensors.append(sensor)
            
            if self.settings_manager.is_channel_enabled(idx):
                row = display_idx // 2
                col = display_idx % 2
                self.sensors_layout.addWidget(sensor, row, col)
                sensor.show()
                display_idx += 1
            else:
                sensor.hide()

        stretch_row = (display_idx + 1) // 2 + 1
        self.sensors_layout.setRowStretch(stretch_row, 1)

    def on_soft_button_pressed(self, button_index: int):
        """Handle clicks from the virtual hardware buttons."""
        print(f"[BUTTON] Soft button {button_index} clicked (UI)")
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(f"Virtual button {button_index} pressed", 1500)
        self.button_pressed.emit(button_index)

    def handle_virtual_button(self, button_index: int):
        """Map button presses (UI or GPIO) to actions."""
        print(f"[BUTTON] Handle button {button_index} (checking current state...)")
        print(f"[BUTTON]   - is_logging: {self.logger.is_logging}")
        print(f"[BUTTON]   - logging_timer active: {self.logging_timer.isActive()}")
        
        if button_index == 1:
            # Toggle start/pause logging
            print(f"[BUTTON] Button 1: Start/Pause")
            if self.logger.is_logging:
                print(f"[BUTTON]   -> Pausing logging")
                self.pause_logging()
            else:
                print(f"[BUTTON]   -> Starting logging")
                self.start_logging()
        elif button_index == 2:
            # Reset logging (create new log file) - only when paused/stopped
            print(f"[BUTTON] Button 2: Reset")
            if not self.logger.is_logging:
                print(f"[BUTTON]   -> Resetting logging")
                self.reset_logging()
            else:
                print(f"[BUTTON]   -> Reset rejected (logging still active)")
                if hasattr(self, 'statusbar'):
                    self.statusbar.showMessage("Stop logging first before resetting", 2000)
        elif button_index == 3:
            # Re-check for attached thermocouples
            print(f"[BUTTON] Button 3: Check TC")
            self.recheck_thermocouples()
        elif button_index == 4:
            # Reserved for future use
            print(f"[BUTTON] Button 4: Reserved")
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage("Button 4: Reserved", 1500)

    def start_worker(self):
        """Start the background reader thread."""
        self.worker = ThermoThread(interval_sec=1.0, channels=self.channel_count, settings_manager=self.settings_manager)
        self.worker.reading_ready.connect(self.update_readings)
        self.worker.source_changed.connect(self.on_source_changed)
        self.worker.error.connect(self.on_error)
        self.worker.unplugged_changed.connect(self.on_unplugged_changed)
        self.worker.check_complete.connect(self.on_check_complete)
        self.worker.start()
        
        # Pass unplugged channels to display after worker initialization
        if hasattr(self.worker, 'unplugged_channels'):
            self.unplugged_channels = list(self.worker.unplugged_channels)
            self.epaper.set_unplugged_channels(self.unplugged_channels)
            self._update_unplugged_state()

    def on_unplugged_changed(self, unplugged_channels):
        """Handle changes in unplugged channel status."""
        self.unplugged_channels = list(unplugged_channels)
        self.epaper.set_unplugged_channels(self.unplugged_channels)
        self._update_unplugged_state()
        self.epaper.stop_flash_channels()
        self.epaper.set_logging_status(self.logger.is_logging, message=None)
        self.restore_epaper_update_interval()
        print(f"[DISPLAY] Updated unplugged channels: {unplugged_channels}")

    def _update_unplugged_state(self):
        """Refresh UI widgets to reflect unplugged channels."""
        for idx, sensor in enumerate(self.sensors):
            unplugged = (idx + 1) in self.unplugged_channels
            sensor.set_unplugged(unplugged)

    def on_check_complete(self):
        """Called when thermocouple check completes (after flash cycles end)."""
        # Restore logging status on e-paper (removes "Rechecking TC..." message)
        self.epaper.set_logging_status(self.logger.is_logging, message=None)
        self.restore_epaper_update_interval()
        self.update_epaper_display()

    def update_readings(self, readings):
        self.last_readings = readings
        # Store timestamped reading for plotting
        self.history.append((datetime.now(), list(readings)))
        for idx, value in enumerate(readings):
            if idx < len(self.sensors):
                # Only update visible/enabled sensors
                if self.settings_manager.is_channel_enabled(idx):
                    self.sensors[idx].update_value(value)

        # Update plot window if open
        if self.plot_window and self.plot_window.isVisible():
            self.plot_window.update_plot(self.history, self.channel_count, self.settings_manager)

    def on_source_changed(self, source: str):
        message = f"Reading source: {source}"
        print(message)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(message, 3000)

    def on_error(self, message: str):
        print(f"Reader error: {message}")
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(message, 5000)

    def update_epaper_display(self):
        """Update e-paper display with current readings."""
        if self.last_readings:
            self.epaper.set_history(self.history)
            image = self.epaper.display_readings(self.last_readings)
            if image and self.preview_window:
                self.preview_window.update_preview(image)

            # If flashing finished, restore normal epaper cadence
            if self.epaper.flash_ticks == 0 and self.epaper_update_timer.interval() != self.epaper_base_interval:
                self.restore_epaper_update_interval()

    def show_plot_window(self):
        """Open the plot window."""
        if self.plot_window is None:
            self.plot_window = PlotWindow()
        
        self.plot_window.show()
        self.plot_window.raise_()
        self.plot_window.activateWindow()
        
        # Update with current data
        if self.history:
            self.plot_window.update_plot(self.history, self.channel_count, self.settings_manager)

    def connect_logging_controls(self):
        """Connect menu actions to their respective handlers."""
        if hasattr(self, 'actionStart'):
            self.actionStart.triggered.connect(self.start_logging)
        if hasattr(self, 'actionStop'):
            self.actionStop.triggered.connect(self.stop_logging)
        if hasattr(self, 'actionReset'):
            self.actionReset.triggered.connect(self.reset_logging)
        if hasattr(self, 'action5_sec'):
            self.action5_sec.triggered.connect(lambda: self.set_logging_interval(5))
        if hasattr(self, 'action20'):
            self.action20.triggered.connect(lambda: self.set_logging_interval(20))
        if hasattr(self, 'action1_min'):
            self.action1_min.triggered.connect(lambda: self.set_logging_interval(60))
        # Hook the settings menu item to open the configuration dialog
        if hasattr(self, 'actionConfiguration'):
            self.actionConfiguration.triggered.connect(self.open_settings)
        if hasattr(self, 'actionShowPlot'):
            self.actionShowPlot.triggered.connect(self.show_plot_window)

    def _init_gpio_buttons(self):
        """Initialize hardware buttons on Raspberry Pi (if available)."""
        if GPIO is None:
            print("[GPIO] RPi.GPIO not available; hardware buttons disabled")
            return
        try:
            self.gpio_buttons = HardwareButtons(callback=self.on_gpio_button)
            print("[GPIO] Hardware buttons initialized")
        except Exception as exc:
            self.gpio_buttons = None
            print(f"[GPIO] Failed to initialize hardware buttons: {exc}")

    def on_gpio_button(self, button_index: int):
        """GPIO callback wrapper to emit through the Qt signal."""
        print(f"[BUTTON] GPIO button {button_index} -> emitting signal")
        self.button_pressed.emit(button_index)

    def open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.exec_()

    def start_logging(self):
        """Start logging temperature data."""
        self.logger.start_logging()
        self.logging_timer.start(self.logging_interval * 1000)
        self.epaper.set_logging_status(True, message=None)
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(False)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(True)
        if hasattr(self, 'actionReset'):
            self.actionReset.setEnabled(True)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage("Logging started", 3000)

    def pause_logging(self):
        """Pause logging without closing the file."""
        self.logging_timer.stop()
        self.logger.stop_logging()
        self.epaper.set_logging_status(False, message="Logging paused")
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage("Logging paused", 3000)
        print("[LOGGING] Paused")
        # Refresh e-paper immediately to show paused state and last log time
        self.update_epaper_display()

    def stop_logging(self):
        """Stop logging temperature data."""
        self.logging_timer.stop()
        self.logger.stop_logging()
        self.epaper.set_logging_status(False, message="Logging stopped")
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(True)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(False)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage("Logging stopped", 3000)

    def reset_logging(self):
        """Reset logging (stop and prepare for new log file)."""
        self.logging_timer.stop()
        self.logger.stop_logging()
        self.epaper.set_logging_status(False, message="Logging reset")
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(True)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(False)
        if hasattr(self, 'actionReset'):
            self.actionReset.setEnabled(False)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage("Logging reset - new file will be created on start", 3000)
        print("[LOGGING] Reset - new file will be created on next start")

        # Show "reset" briefly, then revert to default OFF status
        QTimer.singleShot(2000, self.clear_epaper_status)
        self.update_epaper_display()

    def clear_epaper_status(self):
        """Clear any temporary e-paper status message (e.g., after reset)."""
        self.epaper.set_logging_status(self.logger.is_logging, message=None)
        self.update_epaper_display()

    def start_fast_epaper_updates(self, interval_ms: int = 400):
        """Temporarily speed up e-paper updates for flashing animations."""
        self.epaper_update_timer.stop()
        self.epaper_update_timer.start(interval_ms)

    def restore_epaper_update_interval(self):
        """Restore the default e-paper update interval."""
        self.epaper_update_timer.stop()
        self.epaper_update_timer.start(self.epaper_base_interval)

    def recheck_thermocouples(self):
        """Manually trigger a thermocouple connection check."""
        if self.worker and hasattr(self.worker, '_check_unplugged_status'):
            print("[BUTTON] Rechecking thermocouple connections...")
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage("Rechecking thermocouples...", 2000)
            # Flash channels on e-paper and hide unplugged icons while checking
            self.epaper.start_flash_channels(cycles=6)
            self.epaper.set_logging_status(self.logger.is_logging, message="Rechecking TC...")
            self.start_fast_epaper_updates()
            self.update_epaper_display()
            # Trigger the check in the worker thread
            self.worker._check_unplugged_status()
        else:
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage("Thermocouple check not available", 2000)

    def set_logging_interval(self, seconds):
        """Set the logging interval."""
        self.logging_interval = seconds
        # Update radio button states
        if hasattr(self, 'action5_sec'):
            self.action5_sec.setChecked(seconds == 5)
        if hasattr(self, 'action20'):
            self.action20.setChecked(seconds == 20)
        if hasattr(self, 'action1_min'):
            self.action1_min.setChecked(seconds == 60)
        # Restart timer if logging is active
        if self.logging_timer.isActive():
            self.logging_timer.stop()
            self.logging_timer.start(self.logging_interval * 1000)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(f"Logging interval set to {seconds}s", 3000)

    def on_logging_timer(self):
        """Called when logging timer fires to log current readings."""
        if self.last_readings:
            from datetime import datetime
            self.logger.log_reading(self.last_readings)
            self.epaper.set_logging_status(True, datetime.now(), message=None)

    def closeEvent(self, event):
        self.logging_timer.stop()
        self.logger.stop_logging()
        self.epaper_update_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        if self.gpio_buttons:
            self.gpio_buttons.cleanup()
        if self.epaper:
            self.epaper.clear()  # Clear the e-paper screen
            self.epaper.sleep()
        super().closeEvent(event)
        

def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Load custom fonts
    load_fonts()
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
