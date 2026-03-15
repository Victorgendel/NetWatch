#!/usr/bin/env python3
"""
NetWatch — Web API server.

Flask application that exposes scan reports through authenticated endpoints.
All requests require a Bearer token in the Authorization header.

Environment variables (set in /etc/netwatch/web.env):
    NETWATCH_API_TOKEN   — Required bearer token
    NETWATCH_REPORT_DIR  — Path to reports directory
    NETWATCH_MAX_KEEP    — Max reports to retain
    NETWATCH_WEBLOG      — Log file path
"""

import glob
import json
import logging
import os
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request

app = Flask(__name__)

REPORT_DIR = os.environ.get("NETWATCH_REPORT_DIR", "/opt/netwatch/reports")
API_TOKEN = os.environ.get("NETWATCH_API_TOKEN", "")
MAX_KEEP = int(os.environ.get("NETWATCH_MAX_KEEP", "100"))
WEBLOG = os.environ.get("NETWATCH_WEBLOG", "/var/log/netwatch/webapp.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(WEBLOG),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("netwatch-api")


def require_auth(f):
    """Decorator to enforce Bearer token authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != API_TOKEN:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def list_reports(date_filter=None):
    """List report files, optionally filtered by date."""
    pattern = os.path.join(REPORT_DIR, "netwatch-*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if date_filter == "today":
        today = datetime.now().strftime("%Y%m%d")
        files = [f for f in files if today in os.path.basename(f)]

    return files


@app.route("/api/v1/latest", methods=["POST"])
@require_auth
def get_latest():
    """Return the latest scan report."""
    date_filter = request.args.get("date")
    files = list_reports(date_filter)

    if not files:
        return jsonify({"error": "no reports found"}), 404

    with open(files[0], "r") as f:
        data = json.load(f)

    return jsonify(data)


@app.route("/api/v1/scans", methods=["GET"])
@require_auth
def list_scans():
    """Return a list of available report filenames."""
    date_filter = request.args.get("date")
    files = list_reports(date_filter)

    report_list = [os.path.basename(f) for f in files[:MAX_KEEP]]
    return jsonify({"reports": report_list, "count": len(report_list)})


@app.route("/api/v1/scan/<filename>", methods=["GET"])
@require_auth
def get_scan(filename):
    """Return a specific report by filename."""
    if not filename.startswith("netwatch-") or not filename.endswith(".json"):
        return jsonify({"error": "invalid filename"}), 400

    filepath = os.path.join(REPORT_DIR, filename)

    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "invalid filename"}), 400

    if not os.path.exists(filepath):
        return jsonify({"error": "report not found"}), 404

    with open(filepath, "r") as f:
        data = json.load(f)

    return jsonify(data)


if __name__ == "__main__":
    if not API_TOKEN:
        log.error("NETWATCH_API_TOKEN not set — refusing to start")
        raise SystemExit(1)

    log.info("NetWatch API starting — reports from %s", REPORT_DIR)
    app.run(host="127.0.0.1", port=5000, debug=False)
