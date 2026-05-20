#!/usr/bin/env python3

import requests
import json
from pathlib import Path

REPORTS = Path("/opt/netwatch/reports")

API_URL = "CHANGE_ME"

def main():

    for report in REPORTS.glob("*.json"):

        with open(report) as f:
            data = json.load(f)

        r = requests.post(API_URL, json=data)

        print(report, r.status_code)

if __name__ == "__main__":
    main()
