# Migration Checklist: Error Logging System

## ✅ Pre-Deployment Tasks

- [ ] **Review all changes**
  - [ ] `thermologger.py` - Main app modifications
  - [ ] `backend/thermo_worker.py` - Worker thread logging
  - [ ] `backend/thermo_logger.py` - CSV logging additions
  - [ ] `backend/settings_manager.py` - Settings logging
  - [ ] `backend/error_logger.py` - New logging module

- [ ] **Test basic functionality**
  - [ ] App starts without errors
  - [ ] UI loads correctly
  - [ ] Sensors display values
  - [ ] CSV logging works
  - [ ] Buttons (GPIO and UI) respond

- [ ] **Verify log creation**
  - [ ] `Data/logs/` directory created
  - [ ] `Data/logs/thermologger.log` file created
  - [ ] Log file has expected format
  - [ ] Logs contain startup messages

## 🚀 Deployment Steps

1. **Backup existing installation**
   ```bash
   cp -r . thermologger_backup_2026-02-12
   ```

2. **Copy new files**
   - Copy `backend/error_logger.py` (new file)
   - Copy modified Python files

3. **Create logs directory** (if using old version)
   ```bash
   mkdir -p Data/logs
   chmod 755 Data/logs
   ```

4. **Test the application**
   - Start app: `python thermologger.py`
   - Check for log file creation
   - Verify no console errors
   - Let it run for 1-2 minutes
   - Stop and check log file for errors

5. **Verify log file**
   - [ ] `Data/logs/thermologger.log` exists
   - [ ] Contains startup messages
   - [ ] Has expected format with timestamps
   - [ ] Shows hardware/sensor info

## 📋 Post-Deployment Verification

### Automated Tests (if available)
```bash
# Run existing tests
python -m pytest tests/ -v
```

### Manual Tests

- [ ] **Startup**
  - App starts cleanly
  - Log file created with startup messages
  
- [ ] **Sensor Reading**
  - Sensors display values
  - No error messages in console
  - Log shows reading operations
  
- [ ] **Logging**
  - Start CSV logging
  - Data appears in CSV file
  - Log shows file creation/operations
  
- [ ] **Error Handling**
  - Unplug a sensor (if available)
  - Check log for error messages
  - App continues running
  
- [ ] **Shutdown**
  - App shuts down cleanly
  - Log shows shutdown message
  - Files properly closed

## 🔍 Validation Checklist

### Code Quality
- [ ] No syntax errors in modified files
- [ ] All imports resolve correctly
- [ ] Error logger initializes properly
- [ ] No circular imports

### Functionality
- [ ] Normal operations work (same as before)
- [ ] Logging adds minimal overhead
- [ ] Log file rotates correctly when >5MB
- [ ] Backups are created properly

### User Experience
- [ ] No new console spam
- [ ] Existing functionality unchanged
- [ ] Additional error info available for debugging
- [ ] Documentation complete

## 📊 Performance Check

```python
# Check performance impact (in Python REPL)
import time
from backend.error_logger import ErrorLogger

# Time 1000 log operations
start = time.time()
for i in range(1000):
    ErrorLogger.log_info(f"Test message {i}")
end = time.time()

print(f"1000 log operations: {end - start:.3f}s")
# Expected: < 0.5 seconds
```

## 🔧 Troubleshooting Deployment

### Issue: Permission Denied on Log File
```bash
# Check permissions
ls -la Data/logs/

# Fix if needed
chmod 755 Data/logs/
chmod 644 Data/logs/thermologger.log
```

### Issue: No Log File Created
```bash
# Check directory exists
ls -la Data/

# Create if missing
mkdir -p Data/logs
```

### Issue: Circular Import Error
- Verify no imports of main thermologger.py in backend modules
- Check error_logger.py has no circular dependencies

### Issue: Log File Not Written
- Check write permissions on Data/logs/ directory
- Verify disk space available
- Check for permission errors in console

## 📚 Team Communication

### Inform Users/Testers
- [ ] Explain new logging feature
- [ ] Point to LOGGING_QUICK_REFERENCE.md
- [ ] Explain where to find logs if issues occur
- [ ] Request log file when reporting issues

### Documentation Update
- [ ] Update main README if needed
- [ ] Link to LOGGING.md in project docs
- [ ] Update troubleshooting procedures
- [ ] Train team on log analysis

## ✨ Feature Validation

- [ ] Logs show application lifecycle
- [ ] Hardware events are logged
- [ ] Sensor errors are captured
- [ ] File operations are recorded
- [ ] Settings changes are logged
- [ ] All exceptions include stack traces
- [ ] Log rotation works correctly
- [ ] File cleanup works (old logs deleted)

## 📈 Monitoring First Week

- [ ] Monitor for any unexpected errors
- [ ] Check that logs are being written correctly
- [ ] Verify file rotation works after ~5MB
- [ ] Gather user feedback on visibility
- [ ] Note any issues for follow-up

## 🎓 Team Training

Schedule training on:
- [ ] How to access log files
- [ ] What information appears in logs
- [ ] How to search for specific errors
- [ ] Interpreting common log messages
- [ ] How to share logs for support

### Training Resources
- [LOGGING_QUICK_REFERENCE.md](LOGGING_QUICK_REFERENCE.md) - 2 min
- [LOGGING.md](LOGGING.md) - 5 min
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 10 min

## 🔄 Rollback Plan

If major issues occur:

```bash
# Restore from backup
rm -rf backend/__pycache__
cp -r thermologger_backup_2026-02-12 .
```

## ✅ Sign-Off

- [ ] Code review approved
- [ ] Testing completed successfully
- [ ] Documentation reviewed
- [ ] Team trained
- [ ] Deployment authorized
- [ ] Ready for production

---

## Quick Reference for Common Issues

| Problem | Solution |
|---------|----------|
| App won't start | Check console for import errors, verify error_logger.py exists |
| No log file | Check Data/logs/ permissions, verify write access |
| Logs incomplete | Check disk space, verify file not locked by another process |
| Performance slow | Check if debug logging enabled, consider disabling on production |
| Can't read logs | Check file permissions, try opening with different editor |

---

**Deployment Date**: _______________

**Deployed By**: _______________

**Verified By**: _______________

**Notes**: _______________________________________________

