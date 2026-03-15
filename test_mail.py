#!/usr/bin/env python3

import yaml
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

CFG = Path("/opt/netwatch/config.yaml")

def load_cfg():
    with open(CFG) as f:
        return yaml.safe_load(f)

def main():

    cfg = load_cfg()
    email_cfg = cfg["notify"]["email"]

    msg = MIMEText("NetWatch SMTP test")

    msg["Subject"] = "NetWatch test"
    msg["From"] = email_cfg["from_addr"]
    msg["To"] = ",".join(email_cfg["to_addrs"])

    smtp = smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"])
    smtp.starttls()

    smtp.login(email_cfg["username"], email_cfg["password"])
    smtp.sendmail(msg["From"], email_cfg["to_addrs"], msg.as_string())

    smtp.quit()

    print("Mail sent")

if __name__ == "__main__":
    main()
