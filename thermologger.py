import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFontDatabase
from PyQt5 import uic

from backend.thermo_worker import ThermoThread
from backend.epaper_display import EpaperDisplay
from backend.thermo_logger import ThermoLogger


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


class MainWindow(QMainWindow):
    """Main application window for Atlas Logger."""
    
    def __init__(self):
        super().__init__()
        self.channel_count = 8
        self.sensors = []
        self.worker = None
        self.epaper = EpaperDisplay()
        self.logger = ThermoLogger()
        self.last_readings = []
        self.epaper_update_timer = QTimer()
        self.epaper_update_timer.timeout.connect(self.update_epaper_display)
        self.epaper_update_timer.start(5000)  # Update e-paper every 5 seconds
        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.on_logging_timer)
        self.logging_interval = 5  # Default 5 seconds
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
        
        # Add sensor widgets to the central widget
        self.setup_sensors()

        # Connect menu actions
        self.connect_logging_controls()

        # Start background reader (uses dummy data when hardware is absent)
        self.start_worker()
    
    def setup_sensors(self):
        """Add multiple sensor widgets to the main window in two columns."""
        # Create a grid layout for the central widget if it doesn't have one
        if not self.centralwidget.layout():
            layout = QGridLayout(self.centralwidget)
            self.centralwidget.setLayout(layout)
        else:
            layout = self.centralwidget.layout()

        # Add sensors in a 2-column grid
        for idx in range(self.channel_count):
            sensor = SensorWidget(f"Thermocouple {idx + 1}")
            row = idx // 2
            col = idx % 2
            layout.addWidget(sensor, row, col)
            self.sensors.append(sensor)

        # Add stretch at the bottom
        stretch_row = self.channel_count // 2 + 1
        layout.setRowStretch(stretch_row, 1)

    def start_worker(self):
        """Start the background reader thread."""
        self.worker = ThermoThread(interval_sec=1.0, channels=self.channel_count)
        self.worker.reading_ready.connect(self.update_readings)
        self.worker.source_changed.connect(self.on_source_changed)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_readings(self, readings):
        self.last_readings = readings
        for idx, value in enumerate(readings):
            if idx < len(self.sensors):
                self.sensors[idx].update_value(value)

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
            self.epaper.display_readings(self.last_readings)

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

    def start_logging(self):
        """Start logging temperature data."""
        self.logger.start_logging()
        self.logging_timer.start(self.logging_interval * 1000)
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(False)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(True)
        if hasattr(self, 'actionReset'):
            self.actionReset.setEnabled(True)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage("Logging started", 3000)

    def stop_logging(self):
        """Stop logging temperature data."""
        self.logging_timer.stop()
        self.logger.stop_logging()
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(True)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(False)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage("Logging stopped", 3000)

    def reset_logging(self):
        """Reset logging (stop and clear current log)."""
        self.logging_timer.stop()
        self.logger.stop_logging()
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(True)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(False)
        if hasattr(self, 'actionReset'):
            self.actionReset.setEnabled(False)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage("Logging reset", 3000)

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
            self.logger.log_reading(self.last_readings)

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
