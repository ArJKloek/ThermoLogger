# Error Logging Guide

The ThermoLogger application now includes comprehensive error logging to help diagnose issues and crashes.

## Log Files Location

All logs are stored in the `Data/logs/` directory:
- **Main log file**: `Data/logs/thermologger.log`
- **Backup logs**: `thermologger.log.1`, `thermologger.log.2`, etc. (when file exceeds 5MB)

## What Gets Logged

### Application Events
- Application startup and shutdown
- Font loading status
- Main window initialization

### Hardware Events
- Thermocouple channel connections/disconnections
- Channel unplugging (0.00 mV detected)
- Hardware initialization status
- GPIO button presses and events

### Temperature Reading Errors
- Failed temperature readings per channel
- Communication errors with hardware
- Invalid sensor data

### Logging Operations
- CSV file creation and status
- Logging start/stop events
- File write errors

### System Errors
- All exceptions with full stack traces
- Critical failures
- Device initialization failures

## Log Levels

Logs use standard Python logging levels:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures that may cause crashes

## Accessing Logs

### Console Output
- INFO level and above are printed to console
- DEBUG messages are only in the file

### Log File
- All messages (DEBUG and above) are written to the file
- Includes timestamps, module names, and line numbers
- Format: `YYYY-MM-DD HH:MM:SS - Logger Name - LEVEL - [file.py:line] - Message`

## Troubleshooting

If the program crashes:

1. **Check the log file** for errors before the crash
2. **Look for CRITICAL or ERROR level** messages
3. **Note the timestamps** to correlate with what you were doing
4. **Check hardware events** for connection issues
5. **Review reading errors** for sensor problems

## Example Log Messages

```
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:831] - ThermoLogger application started
2026-02-12 10:15:31 - ThermoLogger - INFO - [thermo_worker.py:79] - Initialized hardware SMtc device
2026-02-12 10:15:32 - ThermoLogger - WARNING - [thermo_worker.py:50] - Hardware initialization failed, falling back to dummy mode: Device not found
2026-02-12 10:15:45 - ThermoLogger - WARNING - [thermo_worker.py:137] - [READING] Channel 3 failed: Connection timeout
2026-02-12 10:16:00 - ThermoLogger - INFO - [thermo_logger.py:50] - [LOGGING] Created new log file: Data/temperatures_2026-02-12.csv
2026-02-12 10:16:15 - ThermoLogger - INFO - [thermologger.py:490] - [GPIO] Button 1: pressed
```

## Log Rotation

The log file automatically rotates when it exceeds 5MB:
- Current log: `thermologger.log`
- Previous logs: `thermologger.log.1`, `thermologger.log.2`, etc.
- Up to 5 backup logs are kept
- Oldest logs are automatically deleted

## Using Logs for Debugging

1. **Reproduce the crash** while monitoring the log
2. **Check timestamps** to identify when the issue occurred
3. **Look for ERROR/CRITICAL messages** with exception details
4. **Review surrounding messages** for context
5. **Check if multiple errors occur** in sequence
6. **Share the log file** with developers if reporting issues

## Disabling/Modifying Logging

To change logging behavior, edit the ErrorLogger class in `backend/error_logger.py`:
- Modify `max_bytes` to change file rotation size
- Modify log handlers to change console output level
- Modify the formatter to change message format
