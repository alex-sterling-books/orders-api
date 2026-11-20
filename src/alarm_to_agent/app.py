"""alarm-to-agent: turns a CloudWatch alarm notification into an
AWS DevOps Agent investigation request (fictional Northwind lab).

CloudWatch alarms cannot call an HTTP endpoint, so the alarm notifies an SNS
topic, SNS invokes this function, and this function calls the Agent Space's
HMAC webhook. The webhook URL and secret live in one SecureString parameter in
SSM Parameter Store, never in code or environment variables.

Signing follows the AWS DevOps Agent webhook documentation (checked
2026-11-20): base64(HMAC-SHA256(secret, "<timestamp>:<body>")), sent in the
x-amzn-event-signature header with the timestamp in x-amzn-event-timestamp.
Only title, description, priority, and the incident reference reach the agent,
so everything useful goes into the description.
"""
import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import urllib.request

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PARAM_NAME = os.environ.get("WEBHOOK_PARAMETER", "/orders-api/devops-agent-webhook")
_ssm = boto3.client("ssm")
_config = None


def load_config():
    """Read {"url": ..., "secret": ...} from Parameter Store once per container."""
    global _config
    if _config is None:
        try:
            value = _ssm.get_parameter(Name=PARAM_NAME, WithDecryption=True)["Parameter"]["Value"]
        except _ssm.exceptions.ParameterNotFound:
            return None
        _config = json.loads(value)
    return _config


def sign(secret, timestamp, body):
    digest = hmac.new(secret.encode(), f"{timestamp}:{body}".encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def build_payload(alarm):
    state = alarm.get("NewStateValue")
    changed = alarm.get("StateChangeTime", "")
    name = alarm.get("AlarmName", "unknown-alarm")
    description = (
        f"CloudWatch alarm {name} changed to {state} at {changed} UTC. "
        f"Reason: {alarm.get('NewStateReason', 'not given')} "
        f"Account {alarm.get('AWSAccountId', 'unknown')}, Region {alarm.get('Region', 'unknown')}. "
        f"Alarm description: {alarm.get('AlarmDescription', 'none')}"
    )
    return {
        "eventType": "incident",
        # Unique per state change, so a repeat notification is deduplicated
        # but the next real change starts a new investigation.
        "incidentId": f"{name}-{changed}",
        "action": "created" if state == "ALARM" else "resolved",
        "priority": "HIGH",
        "title": f"{name} is {state}",
        "description": description[:4000],
        "timestamp": changed,
        "service": "orders-api",
    }


def handler(event, context):
    config = load_config()
    if not config:
        logger.warning("Webhook parameter %s not found. Skipping.", PARAM_NAME)
        return {"sent": 0}

    sent = 0
    for record in event.get("Records", []):
        alarm = json.loads(record["Sns"]["Message"])
        if alarm.get("NewStateValue") not in ("ALARM", "OK"):
            continue
        body = json.dumps(build_payload(alarm))
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        request = urllib.request.Request(
            config["url"],
            data=body.encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-amzn-event-timestamp": timestamp,
                "x-amzn-event-signature": sign(config["secret"], timestamp, body),
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            logger.info(json.dumps({
                "event": "webhook_sent",
                "alarm": alarm.get("AlarmName"),
                "state": alarm.get("NewStateValue"),
                "status": response.status,
            }))
        sent += 1
    return {"sent": sent}
