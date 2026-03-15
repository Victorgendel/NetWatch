#!/usr/bin/env python3

import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import json

OUT_DIR = Path("/opt/netwatch/reports-test")

def run_nmap(host):

    cmd = [
        "nmap",
        "-sV",
        "-Pn",
        "-p-",
        host,
        "-oX",
        "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    return result.stdout

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)

    args = parser.parse_args()

    xml = run_nmap(args.host)

    path = OUT_DIR / f"single-test-{args.host}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"

    with open(path, "w") as f:
        json.dump({"host": args.host, "result": xml}, f, indent=2)

    print("Saved:", path)

if __name__ == "__main__":
    main()
