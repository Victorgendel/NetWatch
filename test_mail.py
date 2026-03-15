#!/usr/bin/env python3
"""
NetWatch — SMTP connectivity tester.

Verifies SMTP connectivity, STARTTLS, and authentication
using the credentials from config.yaml.
"""

import logging
import os
import smtplib
import sys

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("netwatch-mail-test")


def main():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    email_cfg = config["notify"]["email"]
    host = email_cfg["smtp_host"]
    port = email_cfg["smtp_port"]
    username = email_cfg["username"]
    password = email_cfg["password"]
    from_addr = email_cfg["from_addr"]
    to_addrs = email_cfg["to_addrs"]

    log.info("Testing SMTP connection to %s:%d", host, port)
    log.info("Username: %s", username)
    log.info("From: %s", from_addr)
    log.info("To: %s", ", ".join(to_addrs))

    try:
        smtp = smtplib.SMTP(host, port, timeout=30)
        smtp.set_debuglevel(1)

        log.info("Sending EHLO...")
        smtp.ehlo()

        log.info("Starting TLS...")
        smtp.starttls()
        smtp.ehlo()

        log.info("Authenticating...")
        smtp.login(username, password)

        subject = "NetWatch SMTP Test"
        body = "This is a test message from NetWatch to verify SMTP connectivity."
        message = f"Subject: {subject}\r\nFrom: {from_addr}\r\nTo: {', '.join(to_addrs)}\r\n\r\n{body}"

        log.info("Sending test message...")
        smtp.sendmail(from_addr, to_addrs, message)

        smtp.quit()
        log.info("SMTP test completed successfully — message queued")

    except smtplib.SMTPAuthenticationError as exc:
        log.error("Authentication failed: %s", exc)
        sys.exit(1)
    except smtplib.SMTPException as exc:
        log.error("SMTP error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        log.error("Connection error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
