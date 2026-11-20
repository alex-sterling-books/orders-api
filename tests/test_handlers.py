"""Local unit tests. No AWS calls: DynamoDB is replaced with a fake."""
import importlib
import json
import os
import sys
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeTable:
    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)


def load_orders_submit():
    os.environ["ORDERS_TABLE"] = "orders"
    os.environ["APP_VERSION"] = "1.8.0"
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    sys.path.insert(0, os.path.join(ROOT, "src", "orders_submit"))
    os.environ.setdefault("INVENTORY_FUNCTION", "inventory-reserve")
    fake = FakeTable()
    with mock.patch("boto3.resource") as res, mock.patch("boto3.client") as cli:
        res.return_value.Table.return_value = fake
        # Later versions call inventory-reserve; answer as if stock is reserved.
        payload = mock.Mock()
        payload.read.return_value = b'{"reserved": true, "delay_ms": 250}'
        cli.return_value.invoke.return_value = {"Payload": payload}
        sys.modules.pop("app", None)
        mod = importlib.import_module("app")
    sys.path.pop(0)
    return mod, fake


def test_valid_order_returns_201():
    mod, fake = load_orders_submit()
    out = mod.handler({"body": json.dumps({"sku": "NW-1001", "quantity": 2})}, None)
    assert out["statusCode"] == 201
    assert json.loads(out["body"])["version"] == os.environ["APP_VERSION"]
    assert fake.items[0]["quantity"] == 2


def test_bad_quantity_returns_400():
    mod, _ = load_orders_submit()
    out = mod.handler({"body": json.dumps({"sku": "NW-1001", "quantity": 0})}, None)
    assert out["statusCode"] == 400


def test_bad_json_returns_400():
    mod, _ = load_orders_submit()
    assert mod.handler({"body": "{not json"}, None)["statusCode"] == 400


def test_inventory_stub_slow_path():
    sys.path.insert(0, os.path.join(ROOT, "src", "inventory_reserve"))
    sys.modules.pop("app", None)
    stub = importlib.import_module("app")
    sys.path.pop(0)
    os.environ.update(BASE_LATENCY_MS="0", SLOW_RATE="1.0", SLOW_LATENCY_MS="5")
    out = stub.handler({"sku": "NW-1001", "quantity": 1}, None)
    assert out == {"reserved": True, "delay_ms": 5}


def _load(module_dir, env):
    os.environ.update(env)
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    sys.path.insert(0, os.path.join(ROOT, *module_dir))
    sys.modules.pop("app", None)
    with mock.patch("boto3.resource") as res, mock.patch("boto3.client") as cli:
        fake = FakeTable()
        res.return_value.Table.return_value = fake
        mod = importlib.import_module("app")
    sys.path.pop(0)
    return mod, fake


def test_signature_matches_documented_scheme():
    import base64, hashlib, hmac
    mod, _ = _load(["src", "alarm_to_agent"], {})
    ts, body = "2026-12-08T14:13:30.000Z", '{"a":1}'
    expected = base64.b64encode(hmac.new(b"s3cret", f"{ts}:{body}".encode(), hashlib.sha256).digest()).decode()
    assert mod.sign("s3cret", ts, body) == expected


def test_alarm_payload_fields():
    mod, _ = _load(["src", "alarm_to_agent"], {})
    p = mod.build_payload({"AlarmName": "OrdersApi-5xx-High", "NewStateValue": "ALARM",
                           "StateChangeTime": "2026-12-08T14:13:00.000+0000",
                           "NewStateReason": "Threshold Crossed", "Region": "US East (N. Virginia)",
                           "AWSAccountId": "111122223333", "AlarmDescription": "5xx above 2 percent"})
    assert p["eventType"] == "incident" and p["action"] == "created" and p["priority"] == "HIGH"
    assert p["incidentId"] == "OrdersApi-5xx-High-2026-12-08T14:13:00.000+0000"
    assert "Threshold Crossed" in p["description"]
    ok = mod.build_payload({"AlarmName": "x", "NewStateValue": "OK", "StateChangeTime": "t"})
    assert ok["action"] == "resolved"


def test_v190_reserves_inventory_then_writes():
    os.environ.update(ORDERS_TABLE="orders", INVENTORY_FUNCTION="inventory-reserve", APP_VERSION="1.9.0")
    fake = FakeTable()
    sys.path.insert(0, os.path.join(ROOT, "releases", "v1.9.0"))
    sys.modules.pop("orders_submit_app", None)
    with mock.patch("boto3.resource") as res, mock.patch("boto3.client") as cli:
        res.return_value.Table.return_value = fake
        payload = mock.Mock(); payload.read.return_value = b'{"reserved": true, "delay_ms": 250}'
        cli.return_value.invoke.return_value = {"Payload": payload}
        v190 = importlib.import_module("orders_submit_app")
    sys.path.pop(0)
    out = v190.handler({"body": json.dumps({"sku": "NW-1001", "quantity": 1})}, None)
    assert out["statusCode"] == 201 and json.loads(out["body"])["version"] == "1.9.0"
    v190.LAMBDA.invoke.assert_called_once()
    assert fake.items and fake.items[0]["app_version"] == "1.9.0"


def _recovery():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    sys.modules.pop("check_recovery", None)
    mod = importlib.import_module("check_recovery")
    sys.path.pop(0)
    return mod


def test_recovery_passes_when_every_minute_is_clean():
    m = _recovery()
    req = {f"14:{i:02d}": 120.0 for i in range(46, 56)}
    err = {"14:46": 0.0}
    ok, _ = m.judge(m.minute_rates(err, req), 10, 0.5)
    assert ok


def test_recovery_fails_on_one_bad_minute_or_missing_traffic():
    m = _recovery()
    req = {f"14:{i:02d}": 120.0 for i in range(46, 56)}
    ok, why = m.judge(m.minute_rates({"14:50": 2.0}, req), 10, 0.5)
    assert not ok and "14:50" in why
    ok, why = m.judge(m.minute_rates({}, dict(list(req.items())[:7])), 10, 0.5)
    assert not ok and "only 7" in why
    req["14:52"] = 0.0
    ok, why = m.judge(m.minute_rates({}, req), 10, 0.5)
    assert not ok and "no traffic" in why


def _release_check():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    sys.modules.pop("check_release", None)
    mod = importlib.import_module("check_release")
    sys.path.pop(0)
    budgets = json.load(open(os.path.join(ROOT, "config", "latency-budgets.json")))
    return mod, budgets


def _template_with_timeout(seconds):
    t = open(os.path.join(ROOT, "template.yaml")).read()
    import re
    return re.sub(r"(OrdersSubmitTimeout:\s*\n\s*Type: Number\s*\n\s*Default: )\d+", rf"\g<1>{seconds}", t)


def test_release_check_blocks_v190_and_passes_v180_and_v191():
    mod, budgets = _release_check()
    v180 = open(os.path.join(ROOT, "src", "orders_submit", "app.py")).read()
    v190 = open(os.path.join(ROOT, "releases", "v1.9.0", "orders_submit_app.py")).read()
    v191 = open(os.path.join(ROOT, "releases", "v1.9.1", "orders_submit_app.py")).read()
    assert mod.evaluate(_template_with_timeout(10), v180, budgets)[3] is True
    assert mod.evaluate(_template_with_timeout(3), v190, budgets)[3] is False
    assert mod.evaluate(_template_with_timeout(10), v191, budgets)[3] is True
    # v1.9.0's code would also be blocked at 4 seconds, but allowed at 5
    assert mod.evaluate(_template_with_timeout(4), v190, budgets)[3] is False
    assert mod.evaluate(_template_with_timeout(5), v190, budgets)[3] is True


def test_v191_fails_open_on_inventory_timeout():
    from botocore.exceptions import ReadTimeoutError
    os.environ.update(ORDERS_TABLE="orders", INVENTORY_FUNCTION="inventory-reserve", APP_VERSION="1.9.1")
    fake = FakeTable()
    sys.path.insert(0, os.path.join(ROOT, "releases", "v1.9.1"))
    sys.modules.pop("orders_submit_app", None)
    with mock.patch("boto3.resource") as res, mock.patch("boto3.client") as cli:
        res.return_value.Table.return_value = fake
        cli.return_value.invoke.side_effect = ReadTimeoutError(endpoint_url="x")
        v191 = importlib.import_module("orders_submit_app")
    sys.path.pop(0)
    out = v191.handler({"body": json.dumps({"sku": "NW-1001", "quantity": 1})}, None)
    assert out["statusCode"] == 201
    assert fake.items[0]["reservation_status"] == "pending"
