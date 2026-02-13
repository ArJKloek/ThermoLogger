# ThermoLogger Hardware Requirements

## Overview

The ThermoLogger is designed to run on a Raspberry Pi with specific hardware components for temperature data acquisition and display.

## Required Hardware

### 1. Raspberry Pi
- **Recommended**: Raspberry Pi 4 Model B (2GB RAM or higher)
- **Minimum**: Raspberry Pi 3 Model B+
- **OS**: Raspberry Pi OS (formerly Raspbian)

### 2. Thermocouple Data Acquisition HAT
- **Product**: [Eight Thermocouples DAQ 8-Layer Stackable HAT](https://sequentmicrosystems.com/products/eight-thermocouples-daq-8-layer-stackable-hat-for-raspberry-pi)
- **Manufacturer**: Sequent Microsystems
- **Channels**: 8 thermocouple input channels
- **Supported Types**: K, J, T, E, N, S, R, B type thermocouples
- **Interface**: I2C
- **Stackable**: Yes (up to 8 boards for 64 channels)
- **Library**: `sm_tc` Python library
- **Product Page**: https://sequentmicrosystems.com/products/eight-thermocouples-daq-8-layer-stackable-hat-for-raspberry-pi

**Features:**
- Individual channel configuration for thermocouple types
- Cold junction compensation
- Built-in voltage sensing for unplugged sensor detection
- High accuracy temperature measurement

### 3. E-Paper Display
- **Product**: Waveshare 7.5inch e-Paper HAT (V2)
- **Model**: `epd7in5_V2`
- **Resolution**: 800 x 480 pixels
- **Colors**: Black and White (1-bit)
- **Interface**: SPI
- **Refresh**: Supports partial refresh for fast updates
- **Library**: `waveshare_epd` Python library
- **Product Page**: https://www.waveshare.com/7.5inch-e-paper-hat.htm

**Features:**
- Low power consumption (only during refresh)
- Sunlight readable
- Wide viewing angle
- Image retention when powered off
- Partial refresh capability for dynamic content

## Optional Hardware

### Physical Buttons (GPIO)
The application supports 4 physical buttons connected to the Raspberry Pi GPIO pins:

| Button | Function | GPIO (BCM) | Physical Pin | Ground Pin |
|--------|----------|------------|--------------|------------|
| Button 1 | Start/Pause logging | GPIO 16 | Pin 36 | Pin 39 (GND) |
| Button 2 | Reset display | GPIO 13 | Pin 33 | Pin 34 (GND) |
| Button 3 | Check thermocouples | GPIO 15 | Pin 10 | Pin 9 (GND) |
| Button 4 | Cycle time range | GPIO 31 | Pin 26 | Pin 25 (GND) |

**Configuration:**
- Active-LOW logic (buttons pull pin to ground when pressed)
- Internal pull-up resistors enabled
- BOARD pin numbering scheme used in code
- Any Ground (GND) pin can be used for button common

## Hardware Setup

### 1. Assembly Order
1. **Raspberry Pi**: Start with a clean Raspberry Pi
2. **Thermocouple HAT**: Install the Sequent Microsystems HAT on GPIO pins
3. **E-Paper Display**: 
   - **If using physical buttons**: Connect the Waveshare e-Paper HAT via the provided wired connection (keeps GPIO pins accessible for buttons)
   - **If NOT using buttons**: Install the Waveshare e-Paper HAT directly on top of the Sequent Microsystems HAT

**Note**: The thermocouple HAT uses I2C (pins 3 & 5), while the e-Paper uses SPI (pins 19, 21, 23, 24, 26). They can coexist without conflict. Physical buttons require direct GPIO access.

### 2. Thermocouple Connections
- Connect up to 8 thermocouples to the screw terminals on the HAT
- Observe correct polarity (+ and -)
- Supported thermocouple types can be configured in software

### 3. Power Supply
- **Recommended**: 5V 3A USB-C power supply for Raspberry Pi 4
- **Minimum**: 5V 2.5A for Raspberry Pi 3
- The HATs draw minimal additional power

### 4. GPIO Button Connections (Optional)
If using physical buttons, connect them as follows:

```
Button 1: GPIO 16 (Pin 36) → Ground (Pin 39 or any GND)
Button 2: GPIO 13 (Pin 33) → Ground (Pin 34 or any GND)
Button 3: GPIO 15 (Pin 10) → Ground (Pin 9 or any GND)
Button 4: GPIO 31 (Pin 26) → Ground (Pin 25 or any GND)
```

**Requirements:**
- Use momentary push buttons (normally open)
- No external pull-up resistors needed (internal pull-ups enabled)
- Buttons can share a common ground rail
- Standard tactile switches work well (6mm x 6mm recommended)

**GPIO Pin Reference:**
- Pin numbering uses BOARD scheme (physical pin numbers)
- Raspberry Pi pinout: https://pinout.xyz/
- Avoid pins used by HATs (I2C on pins 3/5, SPI on pins 19/21/23/24/26)

## Software Requirements

### System Libraries
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade

# Install Python dependencies
sudo apt-get install python3-pip python3-pil python3-numpy

# Install SPI and I2C tools
sudo apt-get install python3-spidev python3-smbus

# Install matplotlib for plotting
sudo apt-get install python3-matplotlib
```

### Enable Interfaces
```bash
# Enable SPI and I2C
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
# Navigate to: Interface Options → I2C → Enable
# Reboot when prompted
```

### Python Libraries
```bash
# Install Sequent Microsystems thermocouple library
pip3 install SM_8THERMO

# Install Waveshare e-Paper library
pip3 install waveshare-epd

# Install PyQt5 for GUI
pip3 install PyQt5

# Optional: Install Perlin noise for realistic dummy data
pip3 install perlin-noise
```

## Hardware Verification

### Check I2C Devices
```bash
# List I2C devices (should show thermocouple HAT)
i2cdetect -y 1
```

Expected output: Should show address `0x48` (or your configured address)

### Check SPI
```bash
# Verify SPI is enabled
ls /dev/spi*
```

Expected output: `/dev/spidev0.0` and `/dev/spidev0.1`

### Test Thermocouple HAT
```bash
# Test reading from channel 1
python3 -c "import sm_tc; board = sm_tc.SMtc(0); print(f'CH1: {board.get_temp(1)}°C')"
```

### Test E-Paper Display
The application will automatically detect and initialize the e-Paper display on startup.

## Troubleshooting Hardware

### Thermocouple HAT Not Detected
1. Check I2C is enabled: `sudo raspi-config`
2. Verify HAT is properly seated on GPIO pins
3. Check I2C address: `i2cdetect -y 1`
4. Install/reinstall library: `pip3 install --upgrade SM_8THERMO`

### E-Paper Display Not Working
1. Check SPI is enabled: `ls /dev/spi*`
2. Verify cable connections
3. Install/reinstall library: `pip3 install --upgrade waveshare-epd`
4. Check logs: `Data/logs/thermologger.log`

### Thermocouples Reading 0°C or NaN
- **0.00 mV**: Thermocouple is unplugged
- **NaN**: Communication error or incorrect thermocouple type
- **Solution**: Check connections and thermocouple type configuration

### GPIO Buttons Not Responding
1. Check wiring and connections
2. Verify RPi.GPIO is installed: `pip3 install RPi.GPIO`
3. Check logs for GPIO initialization errors
4. Verify correct pin numbers in code

## Hardware Specifications Summary

| Component | Model | Interface | Resolution/Channels | Power |
|-----------|-------|-----------|---------------------|-------|
| Raspberry Pi | Pi 4 Model B | - | - | 5V 3A |
| Thermocouple HAT | Sequent Microsystems 8CH | I2C | 8 channels | Via GPIO |
| E-Paper Display | Waveshare 7.5" V2 | SPI | 800x480 pixels | Via GPIO |
| Buttons (optional) | Momentary switches | GPIO | 4 buttons | N/A |

## Product Links

- **Sequent Microsystems Thermocouple HAT**: https://sequentmicrosystems.com/products/eight-thermocouples-daq-8-layer-stackable-hat-for-raspberry-pi
- **Waveshare 7.5" e-Paper**: https://www.waveshare.com/7.5inch-e-paper-hat.htm
- **Raspberry Pi 4**: https://www.raspberrypi.com/products/raspberry-pi-4-model-b/

## Cost Estimate

- Raspberry Pi 4 (4GB): ~$55
- Sequent Microsystems 8CH Thermocouple HAT: ~$75
- Waveshare 7.5" e-Paper Display: ~$70
- K-Type Thermocouples (8x): ~$20-40
- Power Supply + SD Card + Case: ~$30
- **Total**: ~$250-280

## Technical Support

- **Sequent Microsystems**: https://sequentmicrosystems.com/pages/contact
- **Waveshare**: https://www.waveshare.com/contact-us.htm
- **ThermoLogger Issues**: https://github.com/ArJKloek/ThermoLogger/issues

---

**Note**: This project can run in "dummy mode" without hardware for development and testing purposes. In dummy mode, synthetic temperature data is generated using Perlin noise or sine waves.
