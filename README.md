# ThermoLogger

A professional temperature data logging system for Raspberry Pi with e-Paper display support.

![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)
![Python](https://img.shields.io/badge/python-3.7+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Overview

ThermoLogger is a comprehensive temperature monitoring and logging solution designed for the Raspberry Pi. It features real-time temperature display, CSV data logging, and an e-Paper display for low-power, always-on temperature monitoring.

### Key Features

- ✅ **8-Channel Thermocouple Support** - Monitor up to 8 temperature sensors simultaneously
- ✅ **Multiple Thermocouple Types** - Supports K, J, T, E, N, S, R, B type thermocouples
- ✅ **E-Paper Display** - 7.5" Waveshare display for real-time monitoring
- ✅ **CSV Data Logging** - Automatic timestamped data logging
- ✅ **Interactive Plots** - Real-time and historical temperature graphs
- ✅ **Physical Buttons** - Optional GPIO buttons for hands-free operation
- ✅ **Comprehensive Error Logging** - Full error tracking for troubleshooting
- ✅ **Channel Management** - Enable/disable individual channels
- ✅ **Unplugged Detection** - Automatic detection of disconnected sensors
- ✅ **Dummy Mode** - Run without hardware for testing and development

## Hardware Requirements

### Required Components

1. **Raspberry Pi** (4 Model B recommended, 3B+ minimum)
2. **[Sequent Microsystems 8CH Thermocouple HAT](https://sequentmicrosystems.com/products/eight-thermocouples-daq-8-layer-stackable-hat-for-raspberry-pi)**
   - 8 thermocouple input channels
   - Supports K, J, T, E, N, S, R, B types
   - I2C interface
3. **[Waveshare 7.5" e-Paper Display (V2)](https://www.waveshare.com/7.5inch-e-paper-hat.htm)**
   - 800x480 resolution
   - Black & white display
   - SPI interface

### Optional Components

- 4 momentary push buttons (for physical controls)
- K-Type thermocouples (or your preferred type)
- Raspberry Pi case with cooling

📋 **See [HARDWARE.md](HARDWARE.md) for complete hardware specifications and setup instructions.**

## Software Installation

### 1. System Setup

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade

# Enable SPI and I2C
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
# Navigate to: Interface Options → I2C → Enable
# Reboot when prompted
```

### 2. Install Dependencies

```bash
# System libraries
sudo apt-get install python3-pip python3-pil python3-numpy
sudo apt-get install python3-spidev python3-smbus python3-matplotlib

# Python libraries
pip3 install SM_8THERMO          # Thermocouple HAT library
pip3 install waveshare-epd       # E-Paper display library
pip3 install PyQt5               # GUI framework
pip3 install perlin-noise        # Optional: for realistic dummy data
```

### 3. Clone Repository

```bash
cd ~
git clone https://github.com/ArJKloek/ThermoLogger.git
cd ThermoLogger
```

### 4. Run Application

```bash
python3 thermologger.py
```

## Quick Start

1. **Connect Hardware**: Install HATs on Raspberry Pi GPIO
2. **Connect Thermocouples**: Attach sensors to screw terminals
3. **Configure Types**: Use Settings menu to set thermocouple types
4. **Start Logging**: Click "Start/Pause" or press Button 1
5. **View Data**: Check `Data/temperatures_YYYY-MM-DD.csv`

## Application Interface

### Main Window

- **Temperature Display**: Real-time readings for all 8 channels
- **Status Bar**: Logging status and device information
- **Graphs**: Last hour/2-hour/15-min/30-min temperature plots
- **E-Paper Preview**: Shows what's displayed on physical e-Paper (if enabled)

### Physical Buttons (Optional)

- **Button 1** (GPIO 16 / Pin 36): Start/Pause logging
- **Button 2** (GPIO 13 / Pin 33): Reset display
- **Button 3** (GPIO 15 / Pin 10): Check thermocouples (flashes unplugged channels)
- **Button 4** (GPIO 06 / Pin 26): Cycle graph time range (1h → 2h → 15min → 30min)

**Wiring**: Connect one side of each button to the GPIO pin, and the other side to any Ground (GND) pin. Buttons use active-LOW logic with internal pull-up resistors enabled.

### Menu Options

- **File → Settings**: Configure thermocouple types and channels
- **File → Exit**: Close application
- **Logging → Start/Stop**: Control data logging
- **Logging → Set Interval**: Configure logging frequency (1-3600 seconds)

## Configuration

### Thermocouple Types

Configure thermocouple types in the Settings dialog:

1. Open **File → Settings**
2. Select thermocouple type for each channel (K, J, T, E, N, S, R, B)
3. Enable/disable channels as needed
4. Click **Save**

### Settings File

Settings are stored in `settings.json`:

```json
{
  "channel_types": ["K", "K", "K", "K", "K", "K", "K", "K"],
  "channel_enabled": [true, true, true, true, true, true, true, true],
  "show_preview": true
}
```

## Data Logging

### CSV Format

Temperature data is logged to `Data/temperatures_YYYY-MM-DD.csv`:

```csv
Timestamp,CH1,CH2,CH3,CH4,CH5,CH6,CH7,CH8
12-02-2026 10:15:30,22.5,23.1,21.8,22.9,23.4,22.6,23.0,22.7
12-02-2026 10:15:35,22.6,23.2,21.9,23.0,23.5,22.7,23.1,22.8
```

### Log Location

- **Data Files**: `Data/temperatures_YYYY-MM-DD.csv`
- **Error Logs**: `Data/logs/thermologger.log`
- **Settings**: `settings.json`

### API Upload

ThermoLogger can also send real sensor readings to the measurements API used by `test_post.py`. Copy `api_config.example.json` to `api_config.json` in the project root and fill in the API URL, device ID, and device token:

```json
{
   "api_url": "http://your-api-server:8000",
   "device_id": "your-device-id",
   "device_token": "your-device-token"
}
```

Upload `api_config.json` alongside the application when deploying to the Raspberry Pi, or create/edit it directly in the project root on the Pi. The file is ignored by Git because it contains a secret. Environment variables `API_URL`, `DEVICE_ID`, and `DEVICE_TOKEN`, when set, override the matching file values. Each batch is sent to `/api/v1/measurements` on the selected logging interval; only enabled channels with finite readings are uploaded. If either credential is blank, API upload is disabled and CSV logging continues normally. The device ID and token must also be configured on the API server.

## Error Logging

Comprehensive error logging is built-in to help diagnose issues:

- **Log Location**: `Data/logs/thermologger.log`
- **What's Logged**: Application events, hardware status, sensor errors, file operations
- **Log Rotation**: Automatic rotation at 5MB (5 backups kept)

📋 **See [LOGGING.md](LOGGING.md) for complete logging documentation.**

## Troubleshooting

### Common Issues

**App won't start:**
- Check `Data/logs/thermologger.log` for errors
- Verify Python dependencies installed
- Ensure UI files exist in `ui/` folder

**No sensor readings:**
- Check I2C is enabled: `i2cdetect -y 1`
- Verify HAT is properly seated
- Check thermocouple connections

**E-Paper not updating:**
- Check SPI is enabled: `ls /dev/spi*`
- Verify display cable connections
- Check logs for initialization errors

📋 **See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guide.**

## Documentation

- **[HARDWARE.md](HARDWARE.md)** - Hardware requirements and setup
- **[LOGGING.md](LOGGING.md)** - Error logging system guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[LOGGING_QUICK_REFERENCE.md](LOGGING_QUICK_REFERENCE.md)** - Quick logging reference
- **[MASTER_INDEX.md](MASTER_INDEX.md)** - Complete documentation index

## Development

### Dummy Mode

Run without hardware for testing:

```bash
python3 thermologger.py
```

The application automatically falls back to dummy mode if hardware isn't detected. Synthetic temperature data is generated using Perlin noise (if available) or sine waves.

### Adding Logging to Code

See **[LOGGING_DEVELOPER_GUIDE.md](LOGGING_DEVELOPER_GUIDE.md)** for how to add logging to new code.

## Project Structure

```
ThermoLogger/
├── thermologger.py          # Main application entry point
├── backend/                 # Core functionality modules
│   ├── epaper_display.py    # E-paper display handler
│   ├── thermo_logger.py     # CSV data logging
│   ├── thermo_worker.py     # Temperature reading thread
│   ├── settings_manager.py  # Configuration management
│   └── error_logger.py      # Error logging system
├── ui/                      # UI definition files
│   ├── main.ui              # Main window layout
│   ├── sensor.ui            # Sensor widget layout
│   └── settings_dialog.py   # Settings dialog
├── fonts/                   # Custom fonts
├── Data/                    # Data and logs (created at runtime)
│   ├── temperatures_*.csv   # Temperature data logs
│   └── logs/                # Application error logs
└── smtc/                    # Sequent Microsystems library
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

- **Issues**: https://github.com/ArJKloek/ThermoLogger/issues
- **Sequent Microsystems Support**: https://sequentmicrosystems.com/pages/contact
- **Waveshare Support**: https://www.waveshare.com/contact-us.htm

## Acknowledgments

- **Sequent Microsystems** - For the excellent thermocouple HAT and Python library
- **Waveshare** - For the e-Paper display and drivers
- **PyQt** - For the GUI framework

---

**Made with ❤️ for accurate temperature monitoring**
