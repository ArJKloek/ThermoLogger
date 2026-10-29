"""Send a test batch of measurements to the FastAPI app.

Usage: python test_post.py [--url URL] [--device ID] [--token TOKEN] [--count N]
Env fallbacks: API_URL, DEVICE_ID, DEVICE_TOKEN
The device/token must match an entry in the API's DEVICE_TOKENS.
"""
import argparse
import os
import random
import sys
import uuid
from datetime import datetime, timezone

import requests

parser = argparse.ArgumentParser()
parser.add_argument("--url", default=os.getenv("API_URL", "http://localhost:8000"))
parser.add_argument("--device", default=os.getenv("DEVICE_ID"))
parser.add_argument("--token", default=os.getenv("DEVICE_TOKEN"))
parser.add_argument("--count", type=int, default=3)
args = parser.parse_args()

if not args.device or not args.token:
    sys.exit("Provide --device and --token (or DEVICE_ID / DEVICE_TOKEN)")

headers = {"Authorization": f"Bearer {args.token}"}
endpoint = args.url.rstrip("/") + "/api/v1/measurements"


def show(label, resp):
    print(f"{label}: {resp.status_code} {resp.text}")
    return resp


def make_batch():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "device_id": args.device,
        "measurements": [
            {
                "measurement_id": str(uuid.uuid4()),
                "timestamp": now,
                "sensor": f"rtd{i}",
                "value": round(random.uniform(18, 25), 3),
                "unit": "C",
                "quality": "good",
                "logging_on": i % 2 == 0,
                "metadata": {"test": True},
            }
            for i in range(args.count)
        ],
    }


failures = 0


def expect(label, resp, status):
    global failures
    show(label, resp)
    if resp.status_code != status:
        failures += 1
        print(f"  FAIL: expected {status}")


expect("health", requests.get(args.url.rstrip("/") + "/health", timeout=10), 200)

batch = make_batch()
expect("insert", requests.post(endpoint, json=batch, headers=headers, timeout=10), 200)
expect("duplicate resend", requests.post(endpoint, json=batch, headers=headers, timeout=10), 200)
expect("bad token", requests.post(endpoint, json=batch, headers={"Authorization": "Bearer " + "x" * 40}, timeout=10), 401)

wrong = dict(batch, device_id=args.device + "-other")
expect("wrong device id", requests.post(endpoint, json=wrong, headers=headers, timeout=10), 403)

naive = make_batch()
naive["measurements"][0]["timestamp"] = "2024-01-01T12:00:00"
expect("naive timestamp", requests.post(endpoint, json=naive, headers=headers, timeout=10), 422)

sys.exit(1 if failures else 0)
