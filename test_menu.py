#!/usr/bin/env python3
"""Simple PyQt6 menu test program for Raspberry Pi."""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QLabel, QMenuBar, QMenu, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction


class TestMenuWindow(QMainWindow):
    """Test window with menu."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("PyQt6 Menu Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Add label
        self.label = QLabel("Menu Test - Click on the menu items above")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Create menu bar
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)  # Critical for Linux/Raspberry Pi
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Add actions to File menu
        new_action = QAction("New", self)
        new_action.setStatusTip("Create new file")
        new_action.triggered.connect(lambda: self.on_menu_click("New"))
        file_menu.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.setStatusTip("Open file")
        open_action.triggered.connect(lambda: self.on_menu_click("Open"))
        file_menu.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setStatusTip("Save file")
        save_action.triggered.connect(lambda: self.on_menu_click("Save"))
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Logging menu
        logging_menu = menubar.addMenu("Logging")
        
        start_action = QAction("Start", self)
        start_action.triggered.connect(lambda: self.on_menu_click("Start Logging"))
        logging_menu.addAction(start_action)
        
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(lambda: self.on_menu_click("Stop Logging"))
        logging_menu.addAction(stop_action)
        
        logging_menu.addSeparator()
        
        # Time interval submenu
        interval_menu = QMenu("Time Interval", self)
        
        interval_5s = QAction("5 seconds", self)
        interval_5s.setCheckable(True)
        interval_5s.setChecked(True)
        interval_5s.triggered.connect(lambda: self.on_interval_change("5 seconds"))
        interval_menu.addAction(interval_5s)
        
        interval_20s = QAction("20 seconds", self)
        interval_20s.setCheckable(True)
        interval_20s.triggered.connect(lambda: self.on_interval_change("20 seconds"))
        interval_menu.addAction(interval_20s)
        
        interval_60s = QAction("1 minute", self)
        interval_60s.setCheckable(True)
        interval_60s.triggered.connect(lambda: self.on_interval_change("1 minute"))
        interval_menu.addAction(interval_60s)
        
        logging_menu.addMenu(interval_menu)
        
        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        
        config_action = QAction("Configuration", self)
        config_action.triggered.connect(lambda: self.on_menu_click("Configuration"))
        settings_menu.addAction(config_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
        print("[MENU] Menu bar created and configured")
        print(f"[MENU] Native menu bar: {menubar.isNativeMenuBar()}")
        print(f"[MENU] Menu bar visible: {menubar.isVisible()}")
    
    def on_menu_click(self, action_name):
        """Handle menu clicks."""
        message = f"Menu clicked: {action_name}"
        print(message)
        self.label.setText(message)
        self.statusBar().showMessage(message, 3000)
    
    def on_interval_change(self, interval):
        """Handle interval changes."""
        message = f"Interval changed to: {interval}"
        print(message)
        self.label.setText(message)
        self.statusBar().showMessage(message, 3000)
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(self, "About", 
                         "PyQt6 Menu Test\n\nThis is a test program to verify "
                         "that menus work correctly on Raspberry Pi with PyQt6.")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    print("=" * 60)
    print("PyQt6 Menu Test Program")
    print("=" * 60)
    print(f"Qt version: {app.instance().applicationVersion()}")
    print(f"Platform: {app.platformName()}")
    print("=" * 60)
    
    window = TestMenuWindow()
    window.show()
    
    print("\nWindow displayed. Try clicking on the menu items.")
    print("If you can't see the menu bar, there may be a Qt platform issue.\n")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
