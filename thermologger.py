import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFontDatabase, QPixmap, QImage, QPainter, QFont
from PyQt5 import uic

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


class SensorWidget(QWidget):
    """Reusable widget for displaying sensor data."""
    
    def __init__(self, sensor_name="Sensor", parent=None):
        super().__init__(parent)
        self.sensor_name = sensor_name
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
            try:
                numeric_value = float(value)
                text = f"{numeric_value:.1f}°C"
            except (TypeError, ValueError):
                text = "-- °C"
            self.label_value.setText(text)


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
    
    def __init__(self):
        super().__init__()
        self.channel_count = 8
        self.sensors = []
        self.worker = None
        self.settings_manager = SettingsManager()
        self.epaper = EpaperDisplay(settings_manager=self.settings_manager)
        self.logger = ThermoLogger(settings_manager=self.settings_manager)
        self.last_readings = []
        self.history = deque(maxlen=3600)  # store last hour at 1 Hz
        self.epaper_update_timer = QTimer()
        self.epaper_update_timer.timeout.connect(self.update_epaper_display)
        self.epaper_update_timer.start(5000)  # Update e-paper every 5 seconds
        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.on_logging_timer)
        self.logging_interval = 5  # Default 5 seconds
        
        # Create e-paper preview window if enabled in settings
        self.preview_window = None
        if self.settings_manager.show_preview:
            self.preview_window = EpaperPreviewWindow()
            self.preview_window.show()
        
        # Create plot window (initially hidden)
        self.plot_window = None
        
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
        print(f"[BUTTON] Virtual button {button_index} pressed")
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(f"Virtual button {button_index} pressed", 1500)
        self.handle_virtual_button(button_index)

    def handle_virtual_button(self, button_index: int):
        """Map virtual button presses to actions; adjust as needed for hardware."""
        if button_index == 1:
            # Toggle start/pause logging
            if self.logger.is_logging:
                self.pause_logging()
            else:
                self.start_logging()
        elif button_index == 2:
            # Reset logging (create new log file) - only when paused/stopped
            if not self.logger.is_logging:
                self.reset_logging()
            else:
                if hasattr(self, 'statusbar'):
                    self.statusbar.showMessage("Stop logging first before resetting", 2000)
        elif button_index == 3:
            # Re-check for attached thermocouples
            self.recheck_thermocouples()
        elif button_index == 4:
            # Reserved for future use
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage("Button 4: Reserved", 1500)

    def start_worker(self):
        """Start the background reader thread."""
        self.worker = ThermoThread(interval_sec=1.0, channels=self.channel_count, settings_manager=self.settings_manager)
        self.worker.reading_ready.connect(self.update_readings)
        self.worker.source_changed.connect(self.on_source_changed)
        self.worker.error.connect(self.on_error)
        self.worker.unplugged_changed.connect(self.on_unplugged_changed)
        self.worker.start()
        
        # Pass unplugged channels to display after worker initialization
        if hasattr(self.worker, 'unplugged_channels'):
            self.epaper.set_unplugged_channels(self.worker.unplugged_channels)

    def on_unplugged_changed(self, unplugged_channels):
        """Handle changes in unplugged channel status."""
        self.epaper.set_unplugged_channels(unplugged_channels)
        print(f"[DISPLAY] Updated unplugged channels: {unplugged_channels}")

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
        if hasattr(self, 'actionSettings'):
            self.actionSettings.triggered.connect(self.show_settings)
        if hasattr(self, 'actionShowPlot'):
            self.actionShowPlot.triggered.connect(self.show_plot_window)

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

    def recheck_thermocouples(self):
        """Manually trigger a thermocouple connection check."""
        if self.worker and hasattr(self.worker, '_check_unplugged_status'):
            print("[BUTTON] Rechecking thermocouple connections...")
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage("Rechecking thermocouples...", 2000)
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
