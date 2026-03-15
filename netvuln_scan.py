#!/usr/bin/env python3

import json
import yaml
import subprocess
import logging
from pathlib import Path
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

BASE = Path("/opt/netwatch")
CFG_PATH = BASE / "config.yaml"
REPORT_DIR = BASE / "reports"

LOG_FILE = BASE / "netwatch.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def load_cfg():
    with open(CFG_PATH, "r") as f:
        return yaml.safe_load(f)

def run_masscan(ranges, ports, rate):

    cmd = [
        "masscan",
        "-p", ports,
        "--rate", str(rate),
        "-oJ", "/tmp/masscan.json"
    ]

    for r in ranges:
        cmd.append(r)

    subprocess.run(cmd)

def run_nmap(host, ports):

    port_str = ",".join(str(p) for p in ports)

    cmd = [
        "nmap",
        "-sV",
        "-Pn",
        "-p", port_str,
        host,
        "-oX", "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    return result.stdout

def send_email(cfg, text):

    email_cfg = cfg["notify"]["email"]

    msg = MIMEText(text)

    msg["Subject"] = "NetWatch Alert"
    msg["From"] = email_cfg["from_addr"]
    msg["To"] = ",".join(email_cfg["to_addrs"])

    s = smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"])

    s.starttls()
    s.login(email_cfg["username"], email_cfg["password"])
    s.sendmail(msg["From"], email_cfg["to_addrs"], msg.as_string())
    s.quit()

def main():

    cfg = load_cfg()

    ranges = cfg["ranges"]
    ports = cfg["ports"]

    logging.info("Starting masscan")

    run_masscan(ranges, ports, cfg["masscan_rate"])

    report = {
        "scan_started": datetime.utcnow().isoformat(),
        "hosts": []
    }

    report_path = REPORT_DIR / f"netwatch-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logging.info("Report saved: %s", report_path)

if __name__ == "__main__":
    main()
