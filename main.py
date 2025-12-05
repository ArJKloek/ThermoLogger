import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6 import uic

from thermo_worker import ThermoThread


def load_fonts():
    """Load custom fonts from the fonts directory."""
    fonts_dir = Path(__file__).parent / "fonts"
    
    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.ttf"):
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id >= 0:
                print(f"Loaded font: {font_file.name}")
            else:
                print(f"Failed to load font: {font_file.name}")
    else:
        print(f"Fonts directory not found at {fonts_dir}")


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
                text = f"{numeric_value:.2f}°C"
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

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
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
