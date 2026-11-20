"""Steady traffic, with an optional promotion burst, for the Chapter 4 lab.

Usage:
  python3 scripts/load.py URL --rps 2 --minutes 45
  python3 scripts/load.py URL --rps 20 --minutes 6

The burst stands in for Northwind's promotion traffic. It is sized to exceed
the orders table's 5 write capacity units long enough to use up DynamoDB's
burst capacity, so throttling appears partway through the burst.
Hard limits protect your bill: at most 25 requests per second, 45 minutes,
and 30,000 requests in total. Standard library only.
"""
import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

MAX_RPS, MAX_MINUTES, MAX_TOTAL = 25, 45, 30_000


def send(url, counts, lock):
    data = json.dumps({"sku": "NW-1001", "quantity": 1}).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
    except urllib.error.HTTPError as err:
        code = err.code
    except Exception:  # network errors count separately
        code = "error"
    with lock:
        counts[code] += 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--rps", type=float, default=2)
    p.add_argument("--minutes", type=float, default=20)
    p.add_argument("--burst-at", type=float, help="minutes after start")
    p.add_argument("--burst-rps", type=float, default=20)
    p.add_argument("--burst-minutes", type=float, default=5)
    a = p.parse_args()

    if max(a.rps, a.burst_rps) > MAX_RPS or a.minutes > MAX_MINUTES:
        sys.exit(f"Refusing: limits are {MAX_RPS} requests per second and {MAX_MINUTES} minutes.")

    counts, lock = Counter(), threading.Lock()
    start, sent, last_report = time.time(), 0, 0.0
    with ThreadPoolExecutor(max_workers=64) as pool:
        while (elapsed := (time.time() - start) / 60) < a.minutes and sent < MAX_TOTAL:
            in_burst = a.burst_at is not None and a.burst_at <= elapsed < a.burst_at + a.burst_minutes
            rate = a.burst_rps if in_burst else a.rps
            pool.submit(send, a.url, counts, lock)
            sent += 1
            if elapsed - last_report >= 1:
                last_report = elapsed
                with lock:
                    total = sum(counts.values()) or 1
                    bad = sum(v for k, v in counts.items() if k == "error" or (isinstance(k, int) and k >= 500))
                stamp = time.strftime("%H:%M:%S", time.gmtime())
                print(f"{stamp} UTC  minute {elapsed:4.1f}  rate {rate:4.1f}/s  sent {sent:6d}  5xx {100 * bad / total:5.1f}%")
            time.sleep(1 / rate)
    print("final status counts:", dict(counts))


if __name__ == "__main__":
    main()
