# NetWatch Scanner

**Automated network exposure scanner built with Masscan and Nmap.**

NetWatch scans configured CIDR ranges, verifies open ports with service detection, generates structured JSON reports, sends email alerts, and exposes results through a protected REST API.

---

## Features

- **Fast discovery** — Masscan-based port scanning across large CIDR ranges
- **Service verification** — Nmap fingerprinting for product and version identification
- **JSON reports** — Structured per-scan reports with timestamps
- **Email alerts** — SMTP notifications with STARTTLS when open ports are found
- **Protected API** — Flask-based REST API with Bearer token authentication
- **systemd automation** — Daily scheduled scans via systemd timer
- **Production / Test separation** — Isolated report directories prevent test data from polluting production results

---

## Project Structure

```
/opt/netwatch/
├── config.yaml                # Runtime configuration (not committed)
├── netvuln_scan.py            # Main full-range scanner
├── single_host_test.py        # Single-host point scanner
├── test_mail.py               # SMTP connectivity tester
├── upload_reports.py          # Report uploader utility
├── reports/                   # Production scan reports
├── reports-test/              # Test scan reports
└── webapp/
    └── app.py                 # Flask REST API server
```

### Repository layout

```
NetWatch/
├── README.md                  # This file
├── DEPLOYMENT.md              # Full deployment guide
├── OPERATIONS.md              # Operational runbook
├── config.example.yaml        # Sample config with MOCK values
├── requirements.txt           # Python dependencies
├── .gitignore
├── netvuln_scan.py
├── single_host_test.py
├── test_mail.py
├── upload_reports.py
├── webapp/
│   └── app.py
├── systemd/
│   ├── netwatch.service
│   └── netwatch.timer
└── nginx/
    └── netwatch-web.conf
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Victorgendel/NetWatch.git
cd NetWatch

# 2. Install system packages (Ubuntu)
sudo apt update
sudo apt install -y python3 python3-venv python3-pip masscan nmap

# 3. Create virtual environment
python3 -m venv /opt/netwatch-venv
/opt/netwatch-venv/bin/pip install -r requirements.txt

# 4. Copy and edit config
cp config.example.yaml /opt/netwatch/config.yaml
nano /opt/netwatch/config.yaml   # set real values

# 5. Run a scan
/opt/netwatch-venv/bin/python netvuln_scan.py
```

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for full server setup and **[OPERATIONS.md](OPERATIONS.md)** for day-to-day usage.

---

## How It Works

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌───────────┐
│  config.yaml │────▶│ Masscan  │────▶│  Nmap verify  │────▶│ JSON Report│
└─────────────┘     └──────────┘     └──────────────┘     └─────┬─────┘
                                                                │
                                          ┌─────────────────────┼──────────┐
                                          ▼                     ▼          ▼
                                    ┌──────────┐         ┌──────────┐ ┌────────┐
                                    │  Email    │         │  API     │ │ Disk   │
                                    │  Alert    │         │  Upload  │ │ Store  │
                                    └──────────┘         └──────────┘ └────────┘
```

1. **Masscan** performs fast port discovery across all configured CIDR ranges
2. **Nmap** verifies each discovered host:port with service/version detection
3. Results are saved as a timestamped JSON report in `reports/`
4. If open ports match alert rules, an **email notification** is sent
5. The **Web API** serves the latest reports on demand

---

## Web API

All endpoints require a Bearer token:

```
Authorization: Bearer <TOKEN>
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/latest` | Get the latest scan report |
| `POST` | `/api/v1/latest?date=today` | Get the latest report from today |
| `GET` | `/api/v1/scans?date=today` | List available reports |
| `GET` | `/api/v1/scan/<filename>` | Get a specific report by filename |

---

## Configuration

Copy `config.example.yaml` to `config.yaml` and replace MOCK values with real ones:

```yaml
ranges:
  - "203.0.113.0/24"       # Replace with real CIDR ranges

notify:
  email:
    smtp_host: "smtp.example.local"    # Replace with real SMTP
    username: "scanner@example.local"  # Replace with real credentials
    password: "CHANGE_ME"
```

---

## Security Notes

- **Never commit** `config.yaml` — it contains credentials
- **Never commit** report files — they contain scan results
- The API token is stored in `/etc/netwatch/web.env`, not in code
- Use `config.example.yaml` as a safe reference with MOCK values

---

## License

This project is provided as-is for educational and authorized security testing purposes only. Use responsibly and only on networks you own or have explicit permission to scan.
