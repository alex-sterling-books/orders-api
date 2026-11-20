"""Send a few orders and report status codes. Standard library only.

Usage: python3 scripts/smoke_test.py https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/orders [count]
"""
import json
import sys
import urllib.error
import urllib.request
from collections import Counter

MAX_REQUESTS = 50  # hard cap so a typo cannot run up a bill


def send(url):
    data = json.dumps({"sku": "NW-1001", "quantity": 1}).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        return err.code, {}


def main():
    url = sys.argv[1]
    count = min(int(sys.argv[2]) if len(sys.argv) > 2 else 5, MAX_REQUESTS)
    codes = Counter()
    versions = Counter()
    for _ in range(count):
        status, body = send(url)
        codes[status] += 1
        versions[body.get("version", "-")] += 1
    print("status codes:", dict(codes))
    print("versions:    ", dict(versions))
    sys.exit(0 if set(codes) == {201} else 1)


if __name__ == "__main__":
    main()
