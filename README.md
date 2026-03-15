# NetWatch Scanner

**Automated network exposure scanner built with Masscan and Nmap.**

NetWatch scans configured CIDR ranges, verifies open ports with service detection, generates structured JSON reports, sends email alerts, and exposes results through a protected REST API.

---

## Features

- **Fast discovery** — Masscan-based port scanning across large CIDR ranges
- **Service verification** — Nmap service/version detection (`-sV`)
- **JSON reports** — Timestamped per-scan reports saved to disk
- **Email alerts** — SMTP notifications with STARTTLS when open ports are found
- **AbuseIPDB integration** — Report upload to [AbuseIPDB](https://www.abuseipdb.com/) API for IP reputation tracking
- **Protected API** — Flask REST API with Bearer token authentication
- **systemd automation** — Daily scheduled scans via systemd timer
- **Production / Test separation** — `reports/` for production, `reports-test/` for single-host tests

---

## Project Structure

```
/opt/netwatch/
├── config.yaml              # Runtime configuration (not committed)
├── netvuln_scan.py          # Main full-range scanner
├── single_host_test.py      # Single-host point scanner
├── test_mail.py             # SMTP connectivity tester
├── upload_reports.py        # Report uploader utility
├── reports/                 # Production scan reports
├── reports-test/            # Test scan reports
└── webapp/
    └── app.py               # Flask REST API server
```

### Repository Layout

```
NetWatch/
├── README.md
├── DEPLOYMENT.md
├── OPERATIONS.md
├── config.example.yaml
├── requirements.txt
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
sudo apt install -y python3 python3-pip masscan nmap

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create directories
sudo mkdir -p /opt/netwatch/reports /opt/netwatch/reports-test

# 5. Copy and edit config
sudo cp config.example.yaml /opt/netwatch/config.yaml
sudo nano /opt/netwatch/config.yaml   # set real values

# 6. Copy scripts
sudo cp netvuln_scan.py single_host_test.py test_mail.py upload_reports.py /opt/netwatch/
sudo cp -r webapp /opt/netwatch/

# 7. Run a scan
sudo python3 /opt/netwatch/netvuln_scan.py
```

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for full server setup and **[OPERATIONS.md](OPERATIONS.md)** for day-to-day usage.

---

## How It Works

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌───────────┐
│  config.yaml │────▶│ Masscan  │────▶│  Nmap verify  │────▶│ JSON Report│
└─────────────┘     └──────────┘     └──────────────┘     └─────┬─────┘
                                                                │
                                              ┌─────────────────┼──────────────┐
                                              ▼                 ▼              ▼
                                        ┌──────────┐     ┌──────────┐   ┌────────────┐
                                        │  Email    │     │  Disk    │   │ AbuseIPDB  │
                                        │  Alert    │     │  Store   │   │  API       │
                                        └──────────┘     └──────────┘   └────────────┘
```

1. **Masscan** performs fast port discovery across all configured CIDR ranges
2. **Nmap** verifies each discovered host with service/version detection
3. Results are saved as a timestamped JSON report in `reports/`
4. If open ports are found, an **email notification** is sent via SMTP
5. Reports can be uploaded to **[AbuseIPDB](https://www.abuseipdb.com/)** for IP reputation and abuse tracking
6. The **Web API** serves the latest reports on demand

---

## Web API

The API runs on Flask and requires a Bearer token:

```
Authorization: Bearer <TOKEN>
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/latest` | Get the latest scan report |
| `GET` | `/` | API health check |

The token is set via the `NETWATCH_API_TOKEN` environment variable.

---

## AbuseIPDB Integration

The `upload_reports.py` script uploads scan reports to the [AbuseIPDB API](https://www.abuseipdb.com/). AbuseIPDB is a public database for reporting and checking IP addresses involved in malicious activity (scanning, brute-force, spam, etc.).

**What it does:**
- Reads completed JSON reports from `reports/`
- Sends them via `POST` to the AbuseIPDB API endpoint
- Tracks submission status per report

**Configuration** (in `config.example.yaml`):

```yaml
api_upload:
  enabled: false                            # Set to true to activate
  url: "https://api.abuseipdb.com/api/v2/report"  # AbuseIPDB API endpoint
  timeout: 25
  verify_tls: true
  mark_sent: true
```

> To use AbuseIPDB, [create a free account](https://www.abuseipdb.com/register) and generate an API key. Replace the MOCK URL with the real endpoint and configure your API key.

---

## Configuration

Copy `config.example.yaml` to `/opt/netwatch/config.yaml` and replace MOCK values:

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

- **Never commit** `config.yaml` — it contains real credentials
- **Never commit** report files — they contain scan results
- The API token is stored in an environment variable, not in code
- Use `config.example.yaml` as a safe reference with MOCK values only
- All sensitive values in this repo use `example.local` / `CHANGE_ME` placeholders

---

## License

This project is provided as-is for educational and authorized security testing purposes only.
Use responsibly and only on networks you own or have explicit permission to scan.
