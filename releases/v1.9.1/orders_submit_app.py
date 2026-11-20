"""orders-submit, v1.9.1 (fictional Northwind Supply lab).

The proper fix for the 2026-12-08 incident (postmortem action item 5).
Reserves inventory before writing the order, as v1.9.0 intended, with two
differences:
  1. The inventory call has its own 1-second client timeout and no retries,
     so a slow dependency can never consume the whole function timeout.
  2. If the reservation times out, the order is still accepted and marked
     reservation_status="pending", to be reconciled later. The Orders owner
     chose this (fail open) over rejecting the order, because a lost sale
     costs more than a late stock correction.
The function timeout returns to 10 seconds in template.yaml.
"""
import json
import logging
import os
import time
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ConnectTimeoutError, ReadTimeoutError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE"])
LAMBDA = boto3.client(
    "lambda",
    config=Config(connect_timeout=1, read_timeout=1, retries={"total_max_attempts": 1}),
)
INVENTORY_FUNCTION = os.environ["INVENTORY_FUNCTION"]
VERSION = os.environ.get("APP_VERSION", "unknown")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def reserve_inventory(sku, qty):
    """Return 'reserved', 'unavailable', or 'pending' (timed out)."""
    try:
        result = LAMBDA.invoke(
            FunctionName=INVENTORY_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps({"sku": sku, "quantity": qty}).encode(),
        )
    except (ReadTimeoutError, ConnectTimeoutError):
        return "pending"
    answer = json.loads(result["Payload"].read() or b"{}")
    return "reserved" if answer.get("reserved") else "unavailable"


def handler(event, context):
    started = time.time()
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "body must be JSON"})

    sku = body.get("sku")
    qty = body.get("quantity")
    if not sku or not isinstance(qty, int) or qty < 1:
        return _response(400, {"error": "sku and a positive integer quantity are required"})

    reservation = reserve_inventory(sku, qty)
    if reservation == "unavailable":
        return _response(409, {"error": "item not available"})
    if reservation == "pending":
        logger.warning(json.dumps({"event": "inventory_timeout", "sku": sku, "version": VERSION}))

    order_id = str(uuid.uuid4())
    TABLE.put_item(Item={
        "order_id": order_id,
        "sku": sku,
        "quantity": qty,
        "created_at": int(started),
        "app_version": VERSION,
        "reservation_status": reservation,
    })

    logger.info(json.dumps({
        "event": "order_created",
        "order_id": order_id,
        "version": VERSION,
        "reservation_status": reservation,
        "duration_ms": round((time.time() - started) * 1000),
    }))
    return _response(201, {"order_id": order_id, "version": VERSION})
