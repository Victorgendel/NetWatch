#!/usr/bin/env python3
"""
NetWatch — Report uploader utility.

Uploads JSON scan reports to a remote API endpoint.
"""

import argparse
import glob
import json
import logging
import os
import sys

import requests
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("netwatch-upload")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def find_reports(directory, pattern="netwatch-*.json"):
    """Find all report files matching the pattern."""
    search = os.path.join(directory, pattern)
    files = sorted(glob.glob(search), reverse=True)
    return files


def upload(filepath, api_cfg):
    """Upload a single report file to the API."""
    with open(filepath, "r") as f:
        data = json.load(f)

    filename = os.path.basename(filepath)
    log.info("Uploading %s to %s", filename, api_cfg["url"])

    resp = requests.post(
        api_cfg["url"],
        json=data,
        timeout=api_cfg.get("timeout", 25),
        verify=api_cfg.get("verify_tls", True),
    )
    resp.raise_for_status()
    log.info("Uploaded %s — status %d", filename, resp.status_code)
    return True


def main():
    parser = argparse.ArgumentParser(description="Upload NetWatch reports to API")
    parser.add_argument("--file", help="Upload a specific report file")
    parser.add_argument("--latest", action="store_true", help="Upload only the latest report")
    parser.add_argument("--all", action="store_true", help="Upload all unsent reports")
    args = parser.parse_args()

    config = load_config()
    api_cfg = config.get("api_upload", {})

    if not api_cfg.get("url"):
        log.error("No API URL configured in config.yaml")
        sys.exit(1)

    if args.file:
        if not os.path.exists(args.file):
            log.error("File not found: %s", args.file)
            sys.exit(1)
        upload(args.file, api_cfg)

    elif args.latest:
        reports = find_reports(REPORTS_DIR)
        if not reports:
            log.info("No reports found")
            return
        upload(reports[0], api_cfg)

    elif args.all:
        reports = find_reports(REPORTS_DIR)
        if not reports:
            log.info("No reports found")
            return
        success = 0
        for rpt in reports:
            try:
                upload(rpt, api_cfg)
                success += 1
            except Exception as exc:
                log.error("Failed to upload %s: %s", os.path.basename(rpt), exc)
        log.info("Uploaded %d/%d reports", success, len(reports))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
