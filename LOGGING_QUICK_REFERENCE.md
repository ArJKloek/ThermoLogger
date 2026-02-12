# Error Logging - Quick Reference Card

## Where Are the Logs?
📁 `Data/logs/thermologger.log`

## When Do I Check the Log?
- ⚠️ Program crashes
- 🔴 Sensors not working
- 📊 No data being logged
- ⚙️ Unexpected behavior

## How to Read a Log

### Find the Problem
1. Open `Data/logs/thermologger.log` in any text editor
2. Look for lines with `ERROR` or `CRITICAL`
3. Note the **timestamp** and **error message**
4. Check lines **before the error** for context

### Understand Log Format
```
2026-02-12 10:15:30 - ThermoLogger - WARNING - [file.py:123] - Your message here
   ↑ Date & Time     ↑ Logger Name   ↑ Severity    ↑ Location    ↑ Message
```

## Common Issues

| Issue | Search For | Solution |
|-------|-----------|----------|
| Crash on startup | `CRITICAL` at beginning | Check UI file exists |
| No sensor readings | `[READING].*failed` | Check USB connection |
| No data being saved | `[LOGGING].*Error` | Check folder permissions |
| Channels unplugging | `disconnected` | Check physical connections |
| Settings not saving | `[SETTINGS].*Error` | Run from project folder |

## Quick Search Terms

| What You Want | Search For |
|--------------|-----------|
| Startup info | `started` |
| Errors only | `ERROR` |
| Critical issues | `CRITICAL` |
| Hardware events | `[HARDWARE]` |
| Sensor failures | `[READING]` |
| File operations | `[LOGGING]` |
| Settings issues | `[SETTINGS]` |

## On Windows

**To open the log file:**
```
Start → Run → notepad Data\logs\thermologger.log
```

Or use File Explorer:
- Navigate to the project folder
- Open `Data` → `logs` → `thermologger.log`

## On Linux/Raspberry Pi

**To view the log:**
```bash
cat Data/logs/thermologger.log
```

**To follow in real-time:**
```bash
tail -f Data/logs/thermologger.log
```

**To search for errors:**
```bash
grep ERROR Data/logs/thermologger.log
```

## Log Severity Levels

| Level | Means | Action |
|-------|-------|--------|
| INFO ℹ️ | Normal operation | No action needed |
| WARNING ⚠️ | Potential issue | Monitor situation |
| ERROR ❌ | Operation failed | Investigation needed |
| CRITICAL 🔴 | App-breaking issue | Fix required |

## What Gets Logged

✅ Application startup/shutdown  
✅ Hardware connections/disconnections  
✅ Temperature reading failures  
✅ CSV file operations  
✅ Settings changes  
✅ Button presses  
✅ All exceptions with stack traces  

## Log Rotation

- **File size**: 5MB before rotation
- **Backups kept**: 5 previous logs
- **Location**: All in `Data/logs/`

## Tips for Troubleshooting

1. **Reproduce the issue** while logs are recording
2. **Note the exact time** it happened
3. **Search the log** for that time (or 1-2 seconds before)
4. **Read surrounding lines** for context
5. **Note all ERROR/CRITICAL** messages
6. **Check if pattern repeats** (intermittent vs constant)

## When to Share the Log

Include the last 50-100 lines of the log file when:
- Reporting an issue to developers
- Asking for help on forums
- Requesting technical support

Use: Ctrl+A to select all, Ctrl+C to copy, paste into email/forum

## Log Examples

### ✅ Good - Hardware Found
```
INFO - Initialized hardware SMtc device
INFO - Set CH1 to Type K
```

### ⚠️ OK - Fallback to Dummy
```
WARNING - Hardware initialization failed, falling back to dummy mode
INFO - Using sine wave (fallback) for dummy data
```

### ❌ Problem - Sensor Failure
```
WARNING - [READING] Channel 3 failed: Connection timeout
```

### 🔴 Critical - Can't Start
```
CRITICAL - UI file not found
```

## Configuration

To change logging behavior, edit `backend/error_logger.py`:

```python
# More verbose output
console_handler.setLevel(logging.DEBUG)

# Larger files before rotation
max_bytes = 10 * 1024 * 1024  # 10MB
```

## Still Having Issues?

1. ✅ Check the log file first
2. ✅ Search for ERROR/CRITICAL messages
3. ✅ Review TROUBLESHOOTING.md for solutions
4. ✅ Check LOGGING.md for more details

---

**Remember**: The log file is your best friend for debugging! Always check it first. 📋
