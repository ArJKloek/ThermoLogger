# Developer Guide: Adding Logging to New Code

## Quick Start

To add logging to any Python file in ThermoLogger:

### 1. Import the Logger
```python
from backend.error_logger import ErrorLogger
```

### 2. Log Events
```python
# Simple messages
ErrorLogger.log_info("Operation started")
ErrorLogger.log_warning("Something might be wrong")

# With errors
try:
    risky_operation()
except Exception as e:
    ErrorLogger.log_error("Operation failed", e)

# Critical failures
ErrorLogger.log_critical("System cannot continue", e)
```

## Common Logging Scenarios

### Scenario 1: File Operations
```python
try:
    file_handle = open("data.csv", "w")
    file_handle.write(data)
    ErrorLogger.log_info(f"Data written to {file_path}")
except FileNotFoundError:
    ErrorLogger.log_error("File path not found", e)
except IOError as e:
    ErrorLogger.log_error("Cannot write to file", e)
finally:
    if file_handle:
        file_handle.close()
```

### Scenario 2: Hardware Communication
```python
def read_sensor(channel):
    try:
        value = device.read(channel)
        if value is None:
            ErrorLogger.log_reading_error(channel, "Null value returned")
            return None
        return value
    except TimeoutError as e:
        ErrorLogger.log_reading_error(channel, f"Read timeout: {e}")
        return float("nan")
    except Exception as e:
        ErrorLogger.log_error(f"Sensor read error on CH{channel}", e)
        return float("nan")
```

### Scenario 3: Hardware Events
```python
def on_channel_detected(channel):
    ErrorLogger.log_hardware_event(channel, "detected", "Device connected")
    
def on_channel_lost(channel):
    ErrorLogger.log_hardware_event(channel, "disconnected", "Communication lost")
```

### Scenario 4: GPIO/Button Events
```python
def on_button_pressed(button_num):
    ErrorLogger.log_gpio_event(button_num, "pressed", f"at {datetime.now()}")
    
def on_button_released(button_num):
    ErrorLogger.log_gpio_event(button_num, "released", f"duration 200ms")
```

### Scenario 5: Communication Errors
```python
def send_command(command):
    try:
        device.send(command)
    except ConnectionError as e:
        ErrorLogger.log_communication_error(f"Failed to send '{command}'", e)
        return False
    except Exception as e:
        ErrorLogger.log_communication_error(f"Unexpected error sending command", e)
        return False
    return True
```

## Available Methods

### General Purpose
```python
ErrorLogger.log_debug(message)        # DEBUG level
ErrorLogger.log_info(message)         # INFO level
ErrorLogger.log_warning(message)      # WARNING level
ErrorLogger.log_error(message, exc)   # ERROR level with exception
ErrorLogger.log_critical(message, exc) # CRITICAL level with exception
```

### Specialized
```python
ErrorLogger.log_hardware_event(channel, status, details)
ErrorLogger.log_reading_error(channel, error_msg)
ErrorLogger.log_gpio_event(button_num, event, details)
ErrorLogger.log_communication_error(message, exception)
```

## Logging Best Practices

### ✅ DO

```python
# Be specific
ErrorLogger.log_error("Failed to write to CSV: Permission denied", e)

# Include context
ErrorLogger.log_reading_error(3, "Timeout after 5 seconds")

# Log both success and failure
ErrorLogger.log_info("Settings saved successfully")
ErrorLogger.log_error("Failed to save settings", e)

# Use appropriate levels
ErrorLogger.log_info("Device initialized")      # Normal flow
ErrorLogger.log_warning("Fallback to dummy")    # Degraded operation
ErrorLogger.log_error("Cannot read channel", e) # Operation failed
```

### ❌ DON'T

```python
# Vague messages
ErrorLogger.log_error("Something went wrong", e)

# Missing exceptions
ErrorLogger.log_error("Failed to connect")  # Better to pass exception

# Excessive logging
for i in range(1000):
    ErrorLogger.log_debug(f"Loop iteration {i}")  # Too much!

# Logging unformatted data
ErrorLogger.log_info(large_data_structure)  # Hard to read
```

## Integration Examples

### In a Thread
```python
from backend.error_logger import ErrorLogger

class MyThread(QThread):
    def __init__(self):
        super().__init__()
        ErrorLogger.log_info("MyThread initialized")
    
    def run(self):
        try:
            ErrorLogger.log_info("MyThread started")
            self.do_work()
        except Exception as e:
            ErrorLogger.log_error("MyThread encountered error", e)
        finally:
            ErrorLogger.log_info("MyThread finished")
    
    def do_work(self):
        # Your work here
        pass
```

### In a Class
```python
class DataProcessor:
    def __init__(self, filename):
        self.filename = filename
        ErrorLogger.log_info(f"DataProcessor created for {filename}")
    
    def process(self):
        try:
            with open(self.filename) as f:
                data = f.read()
            ErrorLogger.log_info(f"Processed {len(data)} bytes")
            return data
        except FileNotFoundError:
            ErrorLogger.log_error(f"File not found: {self.filename}")
            return None
        except Exception as e:
            ErrorLogger.log_error(f"Error processing {self.filename}", e)
            return None
```

### In Event Handlers
```python
def on_button_click(self, button_id):
    try:
        ErrorLogger.log_info(f"Button {button_id} clicked")
        self.handle_button(button_id)
    except Exception as e:
        ErrorLogger.log_error(f"Button handler failed for {button_id}", e)
        # Show error to user
```

## What to Log

### At Component Start
```python
def __init__(self):
    ErrorLogger.log_info(f"Component initialized: {self.__class__.__name__}")
```

### At Component Stop
```python
def cleanup(self):
    ErrorLogger.log_info(f"Component cleaned up: {self.__class__.__name__}")
```

### On Error Conditions
```python
if not device_connected:
    ErrorLogger.log_warning("Device not connected")

if value < expected:
    ErrorLogger.log_warning(f"Value {value} below expected {expected}")
```

### On Configuration Changes
```python
def set_channel_type(self, channel, type_letter):
    ErrorLogger.log_info(f"Channel {channel} type changed to {type_letter}")
```

## Testing Your Logging

### Run and Check Logs
```bash
# Run your modified code
python thermologger.py

# Check that messages appear
cat Data/logs/thermologger.log
grep "Your message" Data/logs/thermologger.log
```

### Test Error Cases
```python
# Force an error to test logging
def test_error_logging():
    try:
        raise ValueError("Test error")
    except Exception as e:
        ErrorLogger.log_error("Test error message", e)

# Run and verify it appears in log
```

## Performance Considerations

- **Logging is fast**: Minimal performance impact
- **Use appropriate levels**: DEBUG on file only, reduces clutter
- **Avoid excessive logging**: Don't log every loop iteration
- **File rotation**: Handles large logs automatically

## Troubleshooting Logging Issues

### If logs not appearing:
1. Check `Data/logs/` directory exists
2. Verify write permissions
3. Check `backend/error_logger.py` initialization
4. Look for import errors

### If logs too verbose:
1. Reduce console_handler level to WARNING
2. Use DEBUG level for detailed info (goes to file only)

### If logs too quiet:
1. Increase console_handler level to DEBUG
2. Check that ErrorLogger is initialized

## Code Review Checklist

Before submitting code, verify:

- ✅ Critical operations have logging
- ✅ All try-except blocks log errors
- ✅ Log messages are clear and specific
- ✅ No sensitive data logged (passwords, tokens)
- ✅ Error messages include context
- ✅ File operations have try-catch logging
- ✅ Hardware events logged appropriately
- ✅ Thread start/stop events logged

## Real-World Examples from ThermoLogger

### Hardware Initialization
```python
# From thermo_worker.py
def _init_device(self):
    try:
        import sm_tc
        self.device = sm_tc.SMtc(0)
        self.source = "hardware"
        ErrorLogger.log_info("Initialized hardware SMtc device")
    except Exception as exc:
        self.device = DummySMtc(self.channels)
        self.source = "dummy"
        self._startup_error = str(exc)
        ErrorLogger.log_warning(
            f"Hardware initialization failed, falling back to dummy mode: {exc}", 
            exc
        )
```

### Temperature Reading
```python
# From thermo_worker.py
for idx in range(self.channels):
    try:
        temp = self.device.get_temp(idx + 1)
        readings.append(temp)
    except Exception as exc:
        error_msg = str(exc)
        self.error.emit(error_msg)
        ErrorLogger.log_reading_error(idx + 1, error_msg)
        readings.append(float("nan"))
```

### CSV Logging
```python
# From thermo_logger.py
try:
    # ... CSV operations ...
    ErrorLogger.log_info("[LOGGING] Started logging to {self.csv_file}")
except Exception as e:
    error_msg = f"Error starting logging: {e}"
    ErrorLogger.log_error(f"[LOGGING] {error_msg}", e)
```

---

**Remember**: Good logging is an investment in debugging ease! 🎯
