#!/usr/bin/env python3
"""
NetWatch — Single-host point scanner.

Scans a single IP address for open ports using masscan + nmap,
then saves the result to reports-test/ to keep production reports clean.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

sys.path.insert(0, BASE_DIR)
from netvuln_scan import load_config, run_masscan, run_nmap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("netwatch-test")


def main():
    parser = argparse.ArgumentParser(description="NetWatch single-host test scanner")
    parser.add_argument("--host", required=True, help="Target IP address to scan")
    parser.add_argument("--ports", default=None, help="Ports to scan (overrides config)")
    args = parser.parse_args()

    config = load_config()

    ports = args.ports or config["ports"]
    test_dir = config.get("test_reports_dir", os.path.join(BASE_DIR, "reports-test"))
    os.makedirs(test_dir, exist_ok=True)

    target = args.host
    log.info("Starting single-host test for %s", target)

    discovered = run_masscan(
        ranges=[f"{target}/32"],
        ports=ports,
        rate=config.get("masscan_rate", 10000),
        wait=config.get("masscan_wait", 2),
        hard_timeout=config.get("masscan_hard_timeout", 300),
    )

    if not discovered:
        log.info("No open ports found on %s", target)
        return

    results = []
    for ip, port in discovered:
        result = run_nmap(ip, port, config.get("nmap_timeout", 120))
        results.append(result)
        log.info("  %s:%d → %s (%s)", ip, port, result["state"], result["service"])

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = {
        "scan_id": f"single-test-{target}-{timestamp}",
        "timestamp": datetime.now().isoformat(),
        "target": target,
        "ports_scanned": ports,
        "total_findings": len(results),
        "findings": results,
    }

    filename = f"single-test-{target}-{timestamp}.json"
    filepath = os.path.join(test_dir, filename)
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)

    log.info("Test report saved: %s", filepath)
    log.info("Done — %d finding(s)", len(results))


if __name__ == "__main__":
    main()
