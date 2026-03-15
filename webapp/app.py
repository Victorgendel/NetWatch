from flask import Flask, jsonify, request
from pathlib import Path
import json
import os

app = Flask(__name__)

REPORT_DIR = Path("/opt/netwatch/reports")

API_TOKEN = os.getenv("NETWATCH_API_TOKEN", "CHANGE_ME")

def auth(req):

    header = req.headers.get("Authorization","")

    if header.replace("Bearer ","") != API_TOKEN:
        return False

    return True

@app.route("/api/v1/latest")

def latest():

    if not auth(request):
        return {"error":"unauthorized"},401

    files = sorted(REPORT_DIR.glob("netwatch-*.json"))

    if not files:
        return {"error":"no reports"},404

    latest = files[-1]

    with open(latest) as f:
        return jsonify(json.load(f))

@app.route("/")

def index():

    return {"status":"netwatch api online"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
