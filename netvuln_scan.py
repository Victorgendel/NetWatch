#!/usr/bin/env python3
"""
NetWatch — Full-range network exposure scanner.

Reads CIDR ranges from config.yaml, runs masscan for fast port discovery,
verifies results with nmap for service detection, generates JSON reports,
and sends email alerts when open ports are found.
"""

import json
import logging
import os
import smtplib
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
LOG_FILE = os.path.join(BASE_DIR, "netwatch.log")
ERROR_LOG_FILE = os.path.join(BASE_DIR, "netwatch.error.log")

os.makedirs(REPORTS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
error_handler = logging.FileHandler(ERROR_LOG_FILE)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(error_handler)

log = logging.getLogger("netwatch")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def run_masscan(ranges, ports, rate, wait, hard_timeout):
    """Run masscan across all CIDR ranges and return discovered host:port pairs."""
    targets = " ".join(ranges)
    cmd = [
        "masscan", *targets.split(),
        "-p", ports,
        "--rate", str(rate),
        "--wait", str(wait),
        "-oX", "-",
    ]
    log.info("Running masscan: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=hard_timeout,
        )
    except subprocess.TimeoutExpired:
        log.error("Masscan timed out after %d seconds", hard_timeout)
        return []

    if result.returncode not in (0, 1):
        log.error("Masscan failed (rc=%d): %s", result.returncode, result.stderr)
        return []

    discovered = []
    try:
        root = ET.fromstring(f"<root>{result.stdout}</root>")
        for host in root.findall(".//host"):
            addr_el = host.find("address")
            port_el = host.find("ports/port")
            if addr_el is not None and port_el is not None:
                ip = addr_el.get("addr")
                port = int(port_el.get("portid"))
                discovered.append((ip, port))
    except ET.ParseError:
        log.warning("Failed to parse masscan XML output, attempting line parse")
        for line in result.stdout.splitlines():
            if "addr=" in line and "portid=" in line:
                try:
                    ip = line.split('addr="')[1].split('"')[0]
                    port = int(line.split('portid="')[1].split('"')[0])
                    discovered.append((ip, port))
                except (IndexError, ValueError):
                    continue

    log.info("Masscan discovered %d open port(s)", len(discovered))
    return discovered


def run_nmap(ip, port, timeout):
    """Run nmap service detection on a single host:port and return result dict."""
    cmd = [
        "nmap", "-sV", "-Pn",
        "-p", str(port),
        "--open",
        "-oX", "-",
        ip,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        log.warning("Nmap timed out for %s:%d", ip, port)
        return {"host": ip, "port": port, "state": "timeout", "product": "", "service": ""}

    try:
        root = ET.fromstring(result.stdout)
        port_el = root.find(".//port")
        if port_el is not None:
            state = port_el.find("state")
            service = port_el.find("service")
            return {
                "host": ip,
                "port": port,
                "state": state.get("state", "unknown") if state is not None else "unknown",
                "product": service.get("product", "") if service is not None else "",
                "service": service.get("name", "") if service is not None else "",
            }
    except ET.ParseError:
        log.warning("Failed to parse nmap output for %s:%d", ip, port)

    return {"host": ip, "port": port, "state": "unknown", "product": "", "service": ""}


def verify_with_nmap(discovered, workers, timeout):
    """Run nmap verification in parallel for all discovered host:port pairs."""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(run_nmap, ip, port, timeout): (ip, port)
            for ip, port in discovered
        }
        for future in as_completed(futures):
            ip, port = futures[future]
            try:
                result = future.result()
                results.append(result)
                log.info("Verified %s:%d → %s (%s)", ip, port, result["state"], result["service"])
            except Exception as exc:
                log.error("Nmap verification failed for %s:%d: %s", ip, port, exc)
                results.append({"host": ip, "port": port, "state": "error", "product": "", "service": ""})
    return results


def build_report(results, config):
    """Build the JSON report structure."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return {
        "scan_id": f"netwatch-{timestamp}",
        "timestamp": datetime.now().isoformat(),
        "ranges_scanned": config["ranges"],
        "ports_scanned": config["ports"],
        "total_findings": len(results),
        "findings": results,
    }


def save_report(report):
    """Save report to disk and return the file path."""
    filename = f"{report['scan_id']}.json"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    log.info("Report saved: %s", filepath)
    return filepath


def should_alert(results, config):
    """Determine if any findings match alert rules."""
    alert_ports = set(config.get("alert_on", {}).get("ports", []))
    alert_services = set(config.get("alert_on", {}).get("services", []))

    for r in results:
        if r["port"] in alert_ports or r["service"] in alert_services:
            return True
    return False


def build_email_body(report):
    """Build HTML and plain-text email bodies."""
    findings = report["findings"]
    rows_html = ""
    rows_text = ""

    for f in findings:
        rows_html += (
            f"<tr><td>{f['host']}</td><td>{f['port']}</td>"
            f"<td>{f['state']}</td><td>{f['product']}</td>"
            f"<td>{f['service']}</td></tr>\n"
        )
        rows_text += (
            f"  {f['host']}:{f['port']} — {f['state']} — "
            f"{f['product']} ({f['service']})\n"
        )

    html = f"""<html><body>
<h2>NetWatch Alert — {report['scan_id']}</h2>
<p>Scan completed at {report['timestamp']}</p>
<p>Total findings: {report['total_findings']}</p>
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>Host</th><th>Port</th><th>State</th><th>Product</th><th>Service</th></tr>
{rows_html}
</table>
</body></html>"""

    text = (
        f"NetWatch Alert — {report['scan_id']}\n"
        f"Scan completed at {report['timestamp']}\n"
        f"Total findings: {report['total_findings']}\n\n"
        f"{rows_text}"
    )

    return html, text


def send_email(report, config):
    """Send email alert via SMTP with STARTTLS."""
    email_cfg = config["notify"]["email"]
    if not email_cfg.get("enabled", False):
        log.info("Email notifications disabled, skipping")
        return

    html_body, text_body = build_email_body(report)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"NetWatch Alert — {report['scan_id']}"
    msg["From"] = email_cfg["from_addr"]
    msg["To"] = ", ".join(email_cfg["to_addrs"])
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(email_cfg["username"], email_cfg["password"])
            smtp.sendmail(email_cfg["from_addr"], email_cfg["to_addrs"], msg.as_string())
        log.info("Email alert sent to %s", ", ".join(email_cfg["to_addrs"]))
    except Exception as exc:
        log.error("Failed to send email: %s", exc)


def upload_report(filepath, config):
    """Upload report to external API if enabled."""
    import requests

    api_cfg = config.get("api_upload", {})
    if not api_cfg.get("enabled", False):
        return

    with open(filepath, "r") as f:
        data = json.load(f)

    try:
        resp = requests.post(
            api_cfg["url"],
            json=data,
            timeout=api_cfg.get("timeout", 25),
            verify=api_cfg.get("verify_tls", True),
        )
        resp.raise_for_status()
        log.info("Report uploaded to API: %s (status %d)", api_cfg["url"], resp.status_code)
    except Exception as exc:
        log.error("Failed to upload report: %s", exc)


def main():
    log.info("=" * 60)
    log.info("NetWatch scan starting")

    config = load_config()

    discovered = run_masscan(
        ranges=config["ranges"],
        ports=config["ports"],
        rate=config.get("masscan_rate", 10000),
        wait=config.get("masscan_wait", 2),
        hard_timeout=config.get("masscan_hard_timeout", 1800),
    )

    if not discovered:
        log.info("No open ports discovered, scan complete")
        return

    results = verify_with_nmap(
        discovered,
        workers=config.get("nmap_workers", 8),
        timeout=config.get("nmap_timeout", 120),
    )

    report = build_report(results, config)
    filepath = save_report(report)

    if should_alert(results, config):
        send_email(report, config)

    upload_report(filepath, config)

    log.info("NetWatch scan complete — %d finding(s)", len(results))
    log.info("=" * 60)


if __name__ == "__main__":
    main()
