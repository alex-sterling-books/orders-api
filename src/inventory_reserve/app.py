"""inventory-reserve stub (fictional Northwind Supply lab).

Pretends to reserve stock. Latency is set by environment variables so the
lab can be repeated:
  BASE_LATENCY_MS   typical response time
  SLOW_RATE         share of calls (0.0 to 1.0) that take SLOW_LATENCY_MS
  SLOW_LATENCY_MS   response time for slow calls
"""
import json
import logging
import os
import random
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    base_ms = int(os.environ.get("BASE_LATENCY_MS", "250"))
    slow_rate = float(os.environ.get("SLOW_RATE", "0.0"))
    slow_ms = int(os.environ.get("SLOW_LATENCY_MS", "3500"))

    slow = random.random() < slow_rate
    delay_ms = slow_ms if slow else base_ms
    time.sleep(delay_ms / 1000)

    logger.info(json.dumps({
        "event": "inventory_reserved",
        "sku": event.get("sku"),
        "quantity": event.get("quantity"),
        "delay_ms": delay_ms,
        "slow": slow,
    }))
    return {"reserved": True, "delay_ms": delay_ms}
