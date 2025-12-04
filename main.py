import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6 import uic


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
        # Update the doubleSpinBox with the temperature value
        if hasattr(self, 'doubleSpinBox'):
            self.doubleSpinBox.setValue(value)


class MainWindow(QMainWindow):
    """Main application window for Atlas Logger."""
    
    def __init__(self):
        super().__init__()
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
    
    def setup_sensors(self):
        """Add multiple sensor widgets to the main window."""
        # Create a layout for the central widget if it doesn't have one
        if not self.centralwidget.layout():
            layout = QVBoxLayout(self.centralwidget)
            self.centralwidget.setLayout(layout)
        
        # Get the layout
        layout = self.centralwidget.layout()
        
        # Add three temperature sensors
        self.sensor1 = SensorWidget("Temperature Sensor 1")
        self.sensor2 = SensorWidget("Temperature Sensor 2")
        self.sensor3 = SensorWidget("Temperature Sensor 3")
        
        layout.addWidget(self.sensor1)
        layout.addWidget(self.sensor2)
        layout.addWidget(self.sensor3)
        layout.addStretch()
        
        # Example: Update sensor values (you can connect this to real data)
        self.sensor1.update_value(22.5)
        self.sensor2.update_value(102.1)
        self.sensor3.update_value(121.8)
        
        

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
