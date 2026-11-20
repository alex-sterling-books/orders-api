"""orders-submit, v1.8.0 (fictional Northwind Supply lab).

Accepts POST /orders, validates the body, and writes the order to DynamoDB.
v1.8.0 does not call inventory-reserve yet. Chapter 4 introduces v1.9.0.
"""
import json
import logging
import os
import time
import uuid

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE"])
VERSION = os.environ.get("APP_VERSION", "unknown")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


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

    order_id = str(uuid.uuid4())
    TABLE.put_item(Item={
        "order_id": order_id,
        "sku": sku,
        "quantity": qty,
        "created_at": int(started),
        "app_version": VERSION,
    })

    logger.info(json.dumps({
        "event": "order_created",
        "order_id": order_id,
        "version": VERSION,
        "duration_ms": round((time.time() - started) * 1000),
    }))
    return _response(201, {"order_id": order_id, "version": VERSION})
