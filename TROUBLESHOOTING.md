# ThermoLogger Error Logging - Troubleshooting Guide

## Quick Start

When the application crashes or behaves unexpectedly:

1. **Locate the log file**: `Data/logs/thermologger.log`
2. **Open it with a text editor** (Notepad, VS Code, etc.)
3. **Look for ERROR or CRITICAL** messages
4. **Check timestamps** to find when issues occurred

## Understanding Log Messages

### Example 1: Successful Startup
```
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:831] - ================================================================================
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:832] - ThermoLogger application started
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:833] - ================================================================================
2026-02-12 10:15:31 - ThermoLogger - INFO - [thermologger.py:426] - UI file loaded successfully
2026-02-12 10:15:31 - ThermoLogger - INFO - [thermologger.py:434] - UI layouts and sensors configured
2026-02-12 10:15:31 - ThermoLogger - INFO - [thermologger.py:441] - Logging controls connected
2026-02-12 10:15:32 - ThermoLogger - INFO - [thermologger.py:451] - Worker thread started successfully
```
✅ **Good sign**: Application started without errors

### Example 2: Hardware Fallback
```
2026-02-12 10:15:32 - ThermoLogger - WARNING - [thermo_worker.py:72] - Hardware initialization failed, falling back to dummy mode: Device not found
2026-02-12 10:15:32 - ThermoLogger - INFO - [thermo_worker.py:146] - Temperature reading thread started, source: dummy
2026-02-12 10:15:32 - ThermoLogger - INFO - [thermo_worker.py:150] - Using sine wave (fallback) for dummy data
```
ℹ️ **Expected on non-Raspberry Pi systems**: Using simulated data instead of real sensors

### Example 3: Channel Reading Error
```
2026-02-12 10:16:45 - ThermoLogger - WARNING - [thermo_worker.py:171] - [READING] Channel 3 failed: Connection timeout
2026-02-12 10:16:50 - ThermoLogger - WARNING - [thermo_worker.py:171] - [READING] Channel 3 failed: Connection timeout
```
⚠️ **Action needed**: 
- Check physical connection to Channel 3
- Verify sensor is properly inserted
- Check if multiple channels fail (may indicate hardware issue)

### Example 4: Channel Disconnect/Reconnect
```
2026-02-12 10:20:15 - ThermoLogger - INFO - [thermo_worker.py:123] - [HARDWARE] Channel 2: disconnected - CH2
2026-02-12 10:20:30 - ThermoLogger - INFO - [thermo_worker.py:120] - [HARDWARE] Channel 2: connected - CH2
```
ℹ️ **Information**: Sensor was unplugged and reconnected

### Example 5: File Write Error
```
2026-02-12 10:25:00 - ThermoLogger - ERROR - [thermo_logger.py:76] - [LOGGING] Error logging reading: Permission denied
```
❌ **Action needed**:
- Check disk space in `Data/` folder
- Verify write permissions for the directory
- Close other applications that may be accessing the log file

### Example 6: Settings Error
```
2026-02-12 10:30:15 - ThermoLogger - ERROR - [settings_manager.py:35] - [SETTINGS] Error loading settings: Expecting value: line 1 column 1 (char 0)
2026-02-12 10:30:15 - ThermoLogger - INFO - [settings_manager.py:24] - [SETTINGS] Settings file not found at settings.json, using defaults
```
⚠️ **Issue**: Settings file is corrupted, using defaults
- Delete or fix `settings.json` to reset to defaults

## Common Issues and Solutions

### Issue 1: "UI file not found"
```
2026-02-12 10:15:30 - ThermoLogger - CRITICAL - [thermologger.py:416] - UI file not found at .../ui/main.ui
```

**Solution**:
- Verify `ui/main.ui` file exists in the project directory
- Check the file hasn't been accidentally deleted
- Verify project structure is intact

### Issue 2: Multiple Channel Failures
```
2026-02-12 10:16:45 - ThermoLogger - WARNING - [thermo_worker.py:171] - [READING] Channel 1 failed: Connection timeout
2026-02-12 10:16:45 - ThermoLogger - WARNING - [thermo_worker.py:171] - [READING] Channel 2 failed: Connection timeout
2026-02-12 10:16:45 - ThermoLogger - WARNING - [thermo_worker.py:171] - [READING] Channel 3 failed: Connection timeout
2026-02-12 10:16:45 - ThermoLogger - WARNING - [thermo_worker.py:171] - [READING] Channel 4 failed: Connection timeout
```

**Solution**:
- Check main hardware connection (USB/RS485)
- Verify device drivers are installed
- Check if another application is using the device
- Restart the application

### Issue 3: Logging Won't Start
```
2026-02-12 10:35:00 - ThermoLogger - ERROR - [thermo_logger.py:68] - [LOGGING] Error starting logging: Permission denied
```

**Solution**:
- Verify `Data/` directory exists
- Check folder write permissions
- Ensure no other application is accessing log files
- Free up disk space if drive is full

### Issue 4: Settings Not Persisting
```
2026-02-12 10:40:00 - ThermoLogger - ERROR - [settings_manager.py:62] - [SETTINGS] Error saving settings: No such file or directory
```

**Solution**:
- Verify current working directory when running the app
- Check that the app is run from the project root folder
- Ensure sufficient disk space

### Issue 5: GPIO Button Issues
```
2026-02-12 10:45:00 - ThermoLogger - WARNING - [thermologger.py:445] - GPIO button initialization failed
```

**Solution**:
- This is **expected on non-Raspberry Pi systems** - app continues to work with UI buttons
- On Raspberry Pi, check GPIO pin configuration
- Verify RPi.GPIO library is installed

## Log Analysis Checklist

When troubleshooting, go through these in order:

- [ ] **Check for CRITICAL messages**: These indicate app-breaking failures
- [ ] **Check for ERROR messages**: These indicate operation failures
- [ ] **Check timestamp sequence**: Are errors recurring or one-time?
- [ ] **Look for patterns**: Do multiple channels fail together?
- [ ] **Check application startup**: Find when app started (separator line with ====)
- [ ] **Compare with observed behavior**: Map log messages to what you saw
- [ ] **Look for resource errors**: Permission denied, disk full, memory errors
- [ ] **Check hardware events**: Are channels connecting/disconnecting unexpectedly?

## Getting Help

When reporting issues, include:

1. **Last 100 lines of the log file** (capture from timestamp of the issue)
2. **What you were doing** when it happened
3. **What you expected to happen**
4. **What actually happened**
5. **System information**:
   - Are you on Raspberry Pi or another system?
   - How many sensors connected?
   - What sensor types are configured?

## Log File Examples to Look For

### Good Logging Session Example
```
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:831] - ================================================================================
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:832] - ThermoLogger application started
2026-02-12 10:15:31 - ThermoLogger - INFO - [thermo_worker.py:79] - Initialized hardware SMtc device
2026-02-12 10:15:32 - ThermoLogger - INFO - [thermo_logger.py:50] - [LOGGING] Created new log file: Data/temperatures_2026-02-12.csv
2026-02-12 10:15:32 - ThermoLogger - INFO - [thermo_logger.py:55] - [LOGGING] Started logging to Data/temperatures_2026-02-12.csv
2026-02-12 10:15:35 - ThermoLogger - INFO - [thermologger.py:490] - [GPIO] Button 1: pressed
2026-02-12 10:35:00 - ThermoLogger - INFO - [thermo_logger.py:120] - [LOGGING] Stopped logging
2026-02-12 10:35:05 - ThermoLogger - INFO - [thermologger.py:830] - Application exiting with code: 0
```

### Problematic Logging Session Example
```
2026-02-12 10:15:30 - ThermoLogger - INFO - [thermologger.py:832] - ThermoLogger application started
2026-02-12 10:15:31 - ThermoLogger - ERROR - [thermo_worker.py:50] - Hardware initialization failed, falling back to dummy mode: Cannot open device
2026-02-12 10:15:45 - ThermoLogger - WARNING - [thermo_logger.py:68] - [LOGGING] Error starting logging: Permission denied
2026-02-12 10:15:46 - ThermoLogger - ERROR - [thermo_logger.py:68] - [LOGGING] Error starting logging: Permission denied
2026-02-12 10:15:47 - ThermoLogger - ERROR - [thermo_logger.py:68] - [LOGGING] Error starting logging: Permission denied
```
❌ Multiple attempts to start logging failed - check Data folder permissions

## Log Rotation

The log file automatically manages its size:
- **File**: `Data/logs/thermologger.log` (current)
- **Max size**: 5MB before rotation
- **Backups kept**: 5 previous logs
  - `thermologger.log.1` (most recent backup)
  - `thermologger.log.2`
  - `thermologger.log.3`
  - `thermologger.log.4`
  - `thermologger.log.5` (oldest backup)

Old logs are automatically deleted when new ones are created.

## Advanced Troubleshooting

### Finding Intermittent Issues

1. Enable continuous monitoring by keeping the log file open
2. Use text editor's "follow" or "tail" feature (or command line: `tail -f Data/logs/thermologger.log`)
3. Reproduce the issue
4. Look for patterns in timing and error types

### Comparing Multiple Sessions

1. Save current log: `cp Data/logs/thermologger.log session1.log`
2. Clear current log or restart app for new session
3. Save new log: `cp Data/logs/thermologger.log session2.log`
4. Compare differences to identify what changed

### Log File Location on Different Systems

- **Linux/Raspberry Pi**: `./Data/logs/thermologger.log` (relative to working directory)
- **Windows**: `.\Data\logs\thermologger.log` or full path as shown in app
- **Absolute path**: Shown in initial application startup log
