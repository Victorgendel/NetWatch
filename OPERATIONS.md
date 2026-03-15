# NetWatch — Operations Guide

Day-to-day operations, testing, and troubleshooting.

---

## Running Scans

### Full scan (manual)

```bash
cd /opt/netwatch
/usr/bin/python3 /opt/netwatch/netvuln_scan.py
```

### Single-host test

```bash
cd /opt/netwatch
./single_host_test.py --host 203.0.113.10
```

> Single-host results are saved to `reports-test/` and do **not** appear in the API.

---

## Email

### Test SMTP connectivity

```bash
cd /opt/netwatch
./test_mail.py
```

### Email flow

1. `netvuln_scan.py` builds an HTML + plain-text message
2. Connects to the SMTP server
3. Issues STARTTLS
4. Authenticates with AUTH LOGIN
5. Sends the alert with all discovered open ports
6. Logs success/failure to `netwatch.log`

### SMTP debugging

Enable verbose SMTP output by setting in the scanner:

```python
smtp.set_debuglevel(1)
```

This shows the full SMTP conversation: EHLO → STARTTLS → AUTH → MAIL FROM → RCPT TO → DATA → Queue accepted.

---

## Service Management

### Restart the scanner service

```bash
systemctl restart netwatch.service
```

### Restart the timer

```bash
systemctl restart netwatch.timer
```

### Check timer status

```bash
systemctl status netwatch.timer
systemctl list-timers --all | grep netwatch
```

### Check service status

```bash
systemctl status netwatch.service
```

---

## Logs

### Scanner log

```bash
tail -f /opt/netwatch/netwatch.log
```

### Scanner errors

```bash
tail -f /opt/netwatch/netwatch.error.log
```

### systemd journal

```bash
journalctl -u netwatch.service -f
```

### API log

```bash
tail -f /var/log/netwatch/webapp.log
```

---

## Reports

### Production reports

- **Location:** `/opt/netwatch/reports/`
- **Naming:** `netwatch-YYYYMMDD-HHMMSS.json`
- Served by the API

### Test reports

- **Location:** `/opt/netwatch/reports-test/`
- **Naming:** `single-test-<ip>-YYYYMMDD-HHMMSS.json`
- **Not** served by the API

The API only returns files matching `netwatch-*.json`, so test results never leak into production data.

---

## API Usage

All requests require:

```
Authorization: Bearer <TOKEN>
```

### Get latest report

```bash
curl -X POST "https://scanner.example.local/api/v1/latest" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"keep": 100}'
```

### Get latest report from today

```bash
curl -X POST "https://scanner.example.local/api/v1/latest?date=today" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"
```

### List reports

```bash
curl -s "https://scanner.example.local/api/v1/scans?date=today" \
  -H "Authorization: Bearer <TOKEN>"
```

### Get specific report

```bash
curl -s "https://scanner.example.local/api/v1/scan/netwatch-20260315-000000.json" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Troubleshooting

### Service fails with exit code 203/EXEC

**Causes:**
- `ExecStart` points to a non-existing Python path
- Wrong venv path
- Wrong script filename
- Missing execute permissions

**Fix:**

```bash
# Verify the Python path exists
ls -la /usr/bin/python3

# Verify the script exists
ls -la /opt/netwatch/netvuln_scan.py

# Use the correct ExecStart
ExecStart=/usr/bin/python3 /opt/netwatch/netvuln_scan.py
```

### Timer is not running

```bash
systemctl status netwatch.timer
systemctl list-timers --all | grep netwatch

# Re-enable if needed
systemctl daemon-reload
systemctl enable --now netwatch.timer
```

### Email does not arrive

1. Run `./test_mail.py` and check output
2. Check SMTP debug output (enable `set_debuglevel(1)`)
3. Check the mail server queue
4. Check recipient Spam / Junk folder
5. Check mail server logs

### API returns wrong or stale report

- Verify the API reads only from `reports/` (not `reports-test/`)
- Verify file naming matches `netwatch-*.json`
- Check that the report directory in `web.env` is correct

### masscan permission denied

masscan requires root privileges:

```bash
sudo /usr/bin/python3 /opt/netwatch/netvuln_scan.py
```

Or run via the systemd service which runs as root.
