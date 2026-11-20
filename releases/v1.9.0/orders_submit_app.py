"""orders-submit, v1.9.0 (fictional Northwind Supply lab).

Change from v1.8.0 (PR #214): reserve inventory before writing the order, so
Northwind stops accepting orders for items that are out of stock.
The same PR lowered the function timeout from 10 to 3 seconds in template.yaml.
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
LAMBDA = boto3.client("lambda")
INVENTORY_FUNCTION = os.environ["INVENTORY_FUNCTION"]
VERSION = os.environ.get("APP_VERSION", "unknown")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def reserve_inventory(sku, qty):
    result = LAMBDA.invoke(
        FunctionName=INVENTORY_FUNCTION,
        InvocationType="RequestResponse",
        Payload=json.dumps({"sku": sku, "quantity": qty}).encode(),
    )
    return json.loads(result["Payload"].read() or b"{}")


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
    if not reservation.get("reserved"):
        return _response(409, {"error": "item not available"})

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
        "inventory_delay_ms": reservation.get("delay_ms"),
        "duration_ms": round((time.time() - started) * 1000),
    }))
    return _response(201, {"order_id": order_id, "version": VERSION})
