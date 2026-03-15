# NetWatch — Operations Guide

Day-to-day operations, testing, and troubleshooting.

---

## Running Scans

### Full scan (manual)

```bash
cd /opt/netwatch
python3 netvuln_scan.py
```

### Single-host test

```bash
cd /opt/netwatch
python3 single_host_test.py --host 203.0.113.10
```

> Single-host results are saved to `reports-test/` and do **not** appear in the API.

---

## Email

### Test SMTP connectivity

```bash
cd /opt/netwatch
python3 test_mail.py
```

### Email flow

1. `netvuln_scan.py` builds a plain-text email with scan results
2. Connects to the SMTP server configured in `config.yaml`
3. Issues STARTTLS
4. Authenticates with LOGIN
5. Sends the alert
6. Logs success/failure to `netwatch.log`

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

### systemd journal

```bash
journalctl -u netwatch.service -f
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

The API only returns files matching `netwatch-*.json` from the `reports/` directory, so test results never leak into production data.

---

## API Usage

All requests require:

```
Authorization: Bearer <TOKEN>
```

### Get latest report

```bash
curl -s "http://localhost:5000/api/v1/latest" \
  -H "Authorization: Bearer <TOKEN>"
```

### Health check

```bash
curl -s "http://localhost:5000/"
```

---

## Upload Reports

To upload all reports to a remote API:

```bash
cd /opt/netwatch
python3 upload_reports.py
```

> The upload URL is configured in `upload_reports.py` — update it before use.

---

## Troubleshooting

### Service fails with exit code 203/EXEC

**Causes:**
- `ExecStart` points to a non-existing Python path
- Wrong script filename
- Missing execute permissions

**Fix:**

```bash
# Verify the Python path exists
ls -la /usr/bin/python3

# Verify the script exists
ls -la /opt/netwatch/netvuln_scan.py

# Check the ExecStart line in the service file
cat /etc/systemd/system/netwatch.service
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

1. Run `python3 test_mail.py` and check output
2. Verify SMTP settings in `config.yaml`
3. Check the mail server queue
4. Check recipient Spam / Junk folder
5. Check mail server logs

### API returns wrong or stale report

- Verify the API reads from `/opt/netwatch/reports/`
- Verify file naming matches `netwatch-*.json`
- Check that `NETWATCH_API_TOKEN` is set correctly

### masscan permission denied

masscan requires root privileges:

```bash
sudo python3 /opt/netwatch/netvuln_scan.py
```

Or run via the systemd service which runs as root.
