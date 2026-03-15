# NetWatch — Deployment Guide

Complete step-by-step deployment on a fresh Ubuntu server.

---

## Prerequisites

- Ubuntu Server 24.04 LTS (or compatible)
- Root / sudo access
- Outbound SMTP access (port 587)
- Network access to target CIDR ranges

---

## Step 1 — Install System Packages

```bash
apt update
apt install -y python3 python3-venv python3-pip masscan nmap nginx certbot python3-certbot-nginx
```

---

## Step 2 — Create Project Directories

```bash
mkdir -p /opt/netwatch/reports
mkdir -p /opt/netwatch/reports-test
mkdir -p /opt/netwatch/webapp
mkdir -p /var/log/netwatch
mkdir -p /etc/netwatch
```

---

## Step 3 — Copy Project Files

Clone from the repository:

```bash
git clone https://github.com/Victorgendel/NetWatch.git /tmp/netwatch-src
cp /tmp/netwatch-src/netvuln_scan.py /opt/netwatch/
cp /tmp/netwatch-src/single_host_test.py /opt/netwatch/
cp /tmp/netwatch-src/test_mail.py /opt/netwatch/
cp /tmp/netwatch-src/upload_reports.py /opt/netwatch/
cp /tmp/netwatch-src/webapp/app.py /opt/netwatch/webapp/
```

Or transfer files manually:

```bash
scp netvuln_scan.py single_host_test.py test_mail.py upload_reports.py root@server:/opt/netwatch/
scp webapp/app.py root@server:/opt/netwatch/webapp/
```

---

## Step 4 — Install Python Dependencies

```bash
pip install requests pyyaml flask gunicorn
```

Or with a virtual environment:

```bash
python3 -m venv /opt/netwatch-venv
/opt/netwatch-venv/bin/pip install --upgrade pip
/opt/netwatch-venv/bin/pip install requests pyyaml flask gunicorn
```

---

## Step 5 — Create Configuration

Copy the example config and fill in real values:

```bash
cp /tmp/netwatch-src/config.example.yaml /opt/netwatch/config.yaml
nano /opt/netwatch/config.yaml
```

**Required changes:**

| Field | Replace with |
|-------|-------------|
| `ranges` | Real CIDR ranges to scan |
| `smtp_host` | Real SMTP server address |
| `username` | Real SMTP username |
| `password` | Real SMTP password |
| `from_addr` | Real sender email |
| `to_addrs` | Real recipient emails |
| `api_upload.url` | Real API endpoint (if enabled) |

---

## Step 6 — Create systemd Service

```bash
cp /tmp/netwatch-src/systemd/netwatch.service /etc/systemd/system/netwatch.service
```

Or create manually:

```bash
cat > /etc/systemd/system/netwatch.service << 'EOF'
[Unit]
Description=NetWatch full-range scan
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/netwatch
ExecStart=/usr/bin/python3 /opt/netwatch/netvuln_scan.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```

---

## Step 7 — Create systemd Timer

```bash
cp /tmp/netwatch-src/systemd/netwatch.timer /etc/systemd/system/netwatch.timer
```

Or create manually:

```bash
cat > /etc/systemd/system/netwatch.timer << 'EOF'
[Unit]
Description=Run NetWatch scan daily at midnight

[Timer]
OnCalendar=*-*-* 00:00:00
Persistent=true
Unit=netwatch.service

[Install]
WantedBy=timers.target
EOF
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now netwatch.timer
```

Verify:

```bash
systemctl status netwatch.timer
systemctl list-timers --all | grep netwatch
```

---

## Step 8 — Set API Environment Variable

Set the token for the web API:

```bash
export NETWATCH_API_TOKEN="your-secret-token-here"
```

For persistence, add it to a file:

```bash
cat > /etc/netwatch/web.env << 'EOF'
NETWATCH_API_TOKEN="CHANGE_ME"
EOF

chmod 600 /etc/netwatch/web.env
```

---

## Step 9 — Configure NGINX Reverse Proxy

```bash
cp /tmp/netwatch-src/nginx/netwatch-web.conf /etc/nginx/sites-available/netwatch-web
ln -s /etc/nginx/sites-available/netwatch-web /etc/nginx/sites-enabled/netwatch-web
```

Test and reload:

```bash
nginx -t
systemctl restart nginx
```

### Optional: Enable HTTPS with Let's Encrypt

```bash
certbot --nginx -d scanner.example.local
```

---

## Step 10 — Test Full Scan

```bash
cd /opt/netwatch
python3 netvuln_scan.py
```

Check the output:

```bash
ls -la /opt/netwatch/reports/
cat /opt/netwatch/netwatch.log
```

---

## Step 11 — Test Email

```bash
cd /opt/netwatch
python3 test_mail.py
```

---

## Step 12 — Test API

Start the API:

```bash
cd /opt/netwatch
NETWATCH_API_TOKEN="your-token" python3 webapp/app.py
```

Test it:

```bash
curl -s "http://localhost:5000/api/v1/latest" \
  -H "Authorization: Bearer your-token"
```

---

## Verification Checklist

- [ ] System packages installed (python3, masscan, nmap, nginx)
- [ ] Project files in `/opt/netwatch/`
- [ ] Python dependencies installed
- [ ] `config.yaml` created with real values
- [ ] systemd service and timer enabled
- [ ] Timer shows next run in `systemctl list-timers`
- [ ] NGINX configured and running
- [ ] API token set
- [ ] Manual scan produces a JSON report in `reports/`
- [ ] Email alert arrives
- [ ] API responds with latest report
