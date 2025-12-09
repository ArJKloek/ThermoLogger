"""Settings dialog for configuring thermocouple types."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QComboBox, QPushButton, QGroupBox, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt
from backend.settings_manager import SettingsManager


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.channel_combos = []
        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("ThermoLogger Settings")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Thermocouple types group
        tc_group = QGroupBox("Thermocouple Types")
        tc_layout = QGridLayout()
        tc_group.setLayout(tc_layout)

        # Add header
        tc_layout.addWidget(QLabel("<b>Enable</b>"), 0, 0)
        tc_layout.addWidget(QLabel("<b>Channel</b>"), 0, 1)
        tc_layout.addWidget(QLabel("<b>Thermocouple Type</b>"), 0, 2)
        tc_layout.addWidget(QLabel("<b>Temperature Range</b>"), 0, 3)

        # Temperature ranges for each type
        temp_ranges = {
            'K': '-200°C to 1372°C',
            'J': '-210°C to 1200°C',
            'T': '-200°C to 400°C',
            'E': '-200°C to 1000°C',
            'N': '-200°C to 1300°C',
            'S': '0°C to 1768°C',
            'R': '0°C to 1768°C',
            'B': '200°C to 1820°C'
        }

        # Create checkboxes and combo boxes for each channel
        self.channel_checkboxes = []
        for i in range(8):
            # Enable checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.channel_checkboxes.append(checkbox)
            tc_layout.addWidget(checkbox, i + 1, 0, Qt.AlignCenter)
            
            # Channel label
            channel_label = QLabel(f"CH {i + 1}:")
            tc_layout.addWidget(channel_label, i + 1, 1)

            # Type combo box
            combo = QComboBox()
            combo.addItems(SettingsManager.THERMOCOUPLE_TYPES)
            combo.currentTextChanged.connect(lambda text, idx=i: self.update_range_label(idx, text))
            self.channel_combos.append(combo)
            tc_layout.addWidget(combo, i + 1, 2)

            # Temperature range label
            range_label = QLabel(temp_ranges['K'])
            range_label.setObjectName(f"range_label_{i}")
            tc_layout.addWidget(range_label, i + 1, 3)

        layout.addWidget(tc_group)

        # Information label
        info_label = QLabel(
            "<b>Thermocouple Type Information:</b><br>"
            "• <b>Type K:</b> General purpose, most common<br>"
            "• <b>Type J:</b> Iron-constantan, reducing atmospheres<br>"
            "• <b>Type T:</b> Copper-constantan, low temperature<br>"
            "• <b>Type E:</b> Chromel-constantan, highest output<br>"
            "• <b>Type N:</b> High stability, similar to K<br>"
            "• <b>Type S/R:</b> Platinum-based, high accuracy<br>"
            "• <b>Type B:</b> Platinum-rhodium, very high temperature"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(info_label)

        # Display settings group
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        display_group.setLayout(display_layout)
        
        # Show preview checkbox
        self.show_preview_checkbox = QCheckBox("Show E-Paper Preview Window")
        self.show_preview_checkbox.setToolTip("Display a window showing what is being shown on the e-paper display")
        display_layout.addWidget(self.show_preview_checkbox)
        
        layout.addWidget(display_group)

        # Buttons
        button_layout = QHBoxLayout()
        
        # Set all button
        set_all_btn = QPushButton("Set All to Type K")
        set_all_btn.clicked.connect(self.set_all_to_k)
        button_layout.addWidget(set_all_btn)

        button_layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        # Save button
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def update_range_label(self, channel_idx, tc_type):
        """Update the temperature range label when type changes."""
        temp_ranges = {
            'K': '-200°C to 1372°C',
            'J': '-210°C to 1200°C',
            'T': '-200°C to 400°C',
            'E': '-200°C to 1000°C',
            'N': '-200°C to 1300°C',
            'S': '0°C to 1768°C',
            'R': '0°C to 1768°C',
            'B': '200°C to 1820°C'
        }
        range_label = self.findChild(QLabel, f"range_label_{channel_idx}")
        if range_label:
            range_label.setText(temp_ranges.get(tc_type, ''))

    def load_current_settings(self):
        """Load current settings into the dialog."""
        types = self.settings_manager.get_all_channel_types()
        for i, tc_type in enumerate(types):
            if i < len(self.channel_combos):
                index = self.channel_combos[i].findText(tc_type)
                if index >= 0:
                    self.channel_combos[i].setCurrentIndex(index)
            
            # Load channel enabled state
            if i < len(self.channel_checkboxes):
                self.channel_checkboxes[i].setChecked(self.settings_manager.is_channel_enabled(i))
        
        # Load preview window setting
        self.show_preview_checkbox.setChecked(self.settings_manager.show_preview)

    def set_all_to_k(self):
        """Set all channels to Type K."""
        for combo in self.channel_combos:
            combo.setCurrentText('K')

    def save_settings(self):
        """Save the settings and close dialog."""
        types = [combo.currentText() for combo in self.channel_combos]
        enabled = [checkbox.isChecked() for checkbox in self.channel_checkboxes]
        
        self.settings_manager.show_preview = self.show_preview_checkbox.isChecked()
        
        # Save channel types
        if self.settings_manager.set_all_channel_types(types):
            # Save channel enabled states
            for i, is_enabled in enumerate(enabled):
                self.settings_manager.set_channel_enabled(i, is_enabled)
            if self.settings_manager.save_settings():
                QMessageBox.information(self, "Settings Saved", 
                                      "Settings have been saved successfully.\n\nRestart the application for preview window changes to take effect.")
                self.accept()
            else:
                QMessageBox.warning(self, "Save Error", 
                                  "Failed to save settings to file.")
        else:
            QMessageBox.warning(self, "Invalid Settings", 
                              "Invalid thermocouple type configuration.")
