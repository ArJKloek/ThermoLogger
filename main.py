import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontDatabase
from PyQt6 import uic

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
        self.logger = ThermoLogger()  # Initialize logger
        self.last_readings = []
        self.logging_interval = 5  # Default logging interval in seconds
        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.on_logging_timer)
        self.epaper_update_timer = QTimer()
        self.epaper_update_timer.timeout.connect(self.update_epaper_display)
        self.epaper_update_timer.start(5000)  # Update e-paper every 5 seconds
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
        
        # Add sensor widgets to the central widget
        self.setup_sensors()

        # Start background reader (uses dummy data when hardware is absent)
        self.start_worker()
        
        # Connect logging button signals if they exist
        self.connect_logging_controls()
    
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
        """Connect logging menu action signals from the UI."""
        # Connect Start action
        if hasattr(self, 'actionStart'):
            self.actionStart.triggered.connect(self.on_start_logging)
        
        # Connect Stop action
        if hasattr(self, 'actionStop'):
            self.actionStop.triggered.connect(self.on_stop_logging)
        
        # Connect Reset action
        if hasattr(self, 'actionReset'):
            self.actionReset.triggered.connect(self.on_reset_logging)
        
        # Connect time logging interval actions
        if hasattr(self, 'action5_sec'):
            self.action5_sec.triggered.connect(lambda: self.set_logging_interval(5))
        if hasattr(self, 'action20'):
            self.action20.triggered.connect(lambda: self.set_logging_interval(20))
        if hasattr(self, 'action1_min'):
            self.action1_min.triggered.connect(lambda: self.set_logging_interval(60))

    def set_logging_interval(self, seconds: int):
        """Set the logging interval and update radio button states."""
        self.logging_interval = seconds
        # Uncheck all time logging actions
        if hasattr(self, 'action5_sec'):
            self.action5_sec.setChecked(seconds == 5)
        if hasattr(self, 'action20'):
            self.action20.setChecked(seconds == 20)
        if hasattr(self, 'action1_min'):
            self.action1_min.setChecked(seconds == 60)
        
        message = f"Logging interval set to {seconds} seconds"
        print(message)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(message, 3000)

    def on_logging_timer(self):
        """Called by timer to log reading at set intervals."""
        if self.last_readings and self.logger.is_logging:
            self.logger.log_reading(self.last_readings)

    def on_start_logging(self):
        """Handle start logging menu action."""
        if self.logger.start_logging():
            # Start the logging timer with selected interval
            self.logging_timer.start(self.logging_interval * 1000)  # Convert to milliseconds
            message = f"Logging started: {self.logger.get_log_file_path()} (interval: {self.logging_interval}s)"
            print(message)
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage(message, 5000)
            # Update menu actions state
            if hasattr(self, 'actionStart'):
                self.actionStart.setEnabled(False)
            if hasattr(self, 'actionStop'):
                self.actionStop.setEnabled(True)
            if hasattr(self, 'actionReset'):
                self.actionReset.setEnabled(True)
        else:
            message = "Failed to start logging"
            print(message)
            if hasattr(self, 'statusbar'):
                self.statusbar.showMessage(message, 5000)

    def on_stop_logging(self):
        """Handle stop logging menu action."""
        self.logging_timer.stop()
        self.logger.stop_logging()
        message = "Logging stopped"
        print(message)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(message, 3000)
        # Update menu actions state
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(True)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(False)
        if hasattr(self, 'actionReset'):
            self.actionReset.setEnabled(True)

    def on_reset_logging(self):
        """Handle reset logging menu action."""
        self.logging_timer.stop()
        self.logger.stop_logging()
        message = "Logging reset"
        print(message)
        if hasattr(self, 'statusbar'):
            self.statusbar.showMessage(message, 3000)
        # Reset menu actions state
        if hasattr(self, 'actionStart'):
            self.actionStart.setEnabled(True)
        if hasattr(self, 'actionStop'):
            self.actionStop.setEnabled(False)
        if hasattr(self, 'actionReset'):
            self.actionReset.setEnabled(False)

    def closeEvent(self, event):
        self.logging_timer.stop()
        self.logger.stop_logging()  # Stop logging before closing
        self.epaper_update_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        if self.epaper:
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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
