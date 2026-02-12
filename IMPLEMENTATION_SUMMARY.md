# Error Logging Implementation Summary

## Overview
A comprehensive error logging system has been added to the ThermoLogger application to help diagnose crashes and errors. All errors and important events are now logged to both console and a rotating log file.

## Files Created

### 1. `backend/error_logger.py` (NEW)
A singleton error logger class that provides:
- **Centralized logging** through a single ErrorLogger instance
- **Rotating file handler** that auto-rotates at 5MB with 5 backup files kept
- **Console output** for real-time monitoring
- **Specialized logging methods** for different event types:
  - `log_debug()`, `log_info()`, `log_warning()`, `log_error()`, `log_critical()`
  - `log_hardware_event()` - For channel connect/disconnect events
  - `log_reading_error()` - For temperature reading failures
  - `log_gpio_event()` - For button press events
  - `log_communication_error()` - For device communication issues

## Files Modified

### 2. `thermologger.py` (MAIN APPLICATION)
**Changes:**
- Added `from backend.error_logger import ErrorLogger` import
- Modified `main()` function to:
  - Initialize ErrorLogger at startup
  - Log application startup/shutdown
  - Wrap window creation in try-catch with error logging
  - Log exit codes and unhandled exceptions
- Added comprehensive error handling around font loading and window creation

### 3. `backend/thermo_worker.py` (TEMPERATURE READING THREAD)
**Changes:**
- Added ErrorLogger import
- Updated `_init_device()` to log:
  - Hardware initialization success/failure
  - Channel type configuration
  - Unplugged channel detection
  - Fallback to dummy mode with error details
- Updated `_check_unplugged_status()` to log:
  - Channel connect/disconnect events
  - Voltage check errors
  - Status check completions
- Updated `run()` to log:
  - Thread startup and data source
  - Specific channel reading failures
  - Noise source for dummy data

### 4. `backend/thermo_logger.py` (CSV LOGGING)
**Changes:**
- Added ErrorLogger import
- Updated `start_logging()` to log:
  - Logging already active warnings
  - CSV file creation/appending
  - Logging start events
  - Error details if logging startup fails
- Updated `log_reading()` to log individual reading errors
- Updated `stop_logging()` to log:
  - Logging stop events
  - File close errors

### 5. `backend/settings_manager.py` (SETTINGS MANAGEMENT)
**Changes:**
- Added ErrorLogger import
- Updated `load_settings()` to log:
  - Missing settings file (uses defaults)
  - Successful settings load
  - Settings loading errors with full exception details
- Updated `save_settings()` to log:
  - Successful settings save
  - Settings save errors with exception details

## Log File Location

All logs are stored in: `Data/logs/thermologger.log`

**Rotation**: When the file exceeds 5MB, it's renamed to `thermologger.log.1`, and a new log file is created. Up to 5 backup files are kept.

## Log Format

Each log entry includes:
```
YYYY-MM-DD HH:MM:SS - ThermoLogger - LEVEL - [filename.py:line_number] - message
```

Example:
```
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:831] - ThermoLogger application started
2026-02-12 10:15:31 - ThermoLogger - INFO - [thermo_worker.py:79] - Initialized hardware SMtc device
2026-02-12 10:15:45 - ThermoLogger - WARNING - [thermo_worker.py:137] - [READING] Channel 3 failed: Connection timeout
2026-02-12 10:16:00 - ThermoLogger - INFO - [thermo_logger.py:50] - [LOGGING] Created new log file
```

## What Gets Logged

### Application Lifecycle
- ✅ Startup and shutdown
- ✅ Font loading status
- ✅ Window creation success/failure
- ✅ Unhandled exceptions

### Hardware & Sensors
- ✅ Hardware device initialization
- ✅ Channel connect/disconnect events
- ✅ Unplugged channels (0.00 mV)
- ✅ Channel configuration updates
- ✅ Hardware check errors

### Temperature Reading
- ✅ Thread startup and data source
- ✅ Individual channel reading failures
- ✅ Sensor type configuration
- ✅ Fallback to dummy mode

### Data Logging
- ✅ CSV file creation
- ✅ Logging start/stop events
- ✅ File write errors
- ✅ Logging state changes

### Settings
- ✅ Settings file load/save
- ✅ Default settings usage
- ✅ Configuration errors
- ✅ Settings validation issues

### GPIO (Buttons)
- ✅ Button press events
- ✅ Pin configuration
- ✅ Startup grace period
- ✅ Debounce activity

## Usage

### Viewing Logs
1. **While running**: Check console output (INFO level and above)
2. **After running**: Check `Data/logs/thermologger.log` file
3. **With text editor**: Open the log file to see all details including DEBUG messages

### Debugging Crashes
1. Reproduce the crash while the app is running
2. Open `Data/logs/thermologger.log`
3. Look for ERROR or CRITICAL level messages
4. Note timestamps and surrounding messages for context
5. Check channel-specific errors if temperature reading issues occur

### Sharing Logs for Support
- The log file `Data/logs/thermologger.log` contains complete error information
- Include the last 50-100 lines when reporting issues
- Timestamps help correlate with observed problems

## Configuration

To modify logging behavior, edit `backend/error_logger.py`:

```python
# Change maximum log file size before rotation
max_bytes=5 * 1024 * 1024  # Default 5MB

# Change console logging level
console_handler.setLevel(logging.INFO)  # Change to DEBUG for more verbosity

# Change file logging level
file_handler.setLevel(logging.DEBUG)  # DEBUG captures everything

# Modify log format
formatter = logging.Formatter("NEW_FORMAT_HERE")
```

## Benefits

✅ **Diagnosis**: Identify exactly what fails and why
✅ **Traceability**: Know exactly when issues occur
✅ **Safety**: All exceptions are caught and logged
✅ **Performance**: Rotating logs don't consume unlimited disk space
✅ **Debugging**: Line numbers and function names in logs
✅ **History**: Keep logs for later analysis

## Testing

The logging system is:
- **Non-intrusive**: Doesn't affect normal operation
- **Defensive**: Handles any exceptions in logging itself
- **Scalable**: Logs grow to 5MB before rotating
- **Complete**: Captures all critical operations
