"""Check whether Orders API has recovered.

Recovery, as Northwind's runbook defines it:
  1. 5xx rate below 0.5 percent in every one of the last 10 full minutes,
     with traffic in each minute.
  2. A synthetic order returns 201 from the expected version.

Usage:
  python3 scripts/check_recovery.py [--minutes 10] [--threshold 0.5] [--expect-version 1.8.0]
Exit code 0 means recovered, 1 means not yet.
"""
import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request

REGION = "us-east-1"
STACK = "orders-api"


def minute_rates(errors, requests):
    """Pair per-minute sums by timestamp and return [(minute, requests, rate_pct)]."""
    rows = []
    for ts, count in sorted(requests.items()):
        err = errors.get(ts, 0.0)
        rows.append((ts, count, 100.0 * err / count if count else None))
    return rows


def judge(rows, minutes, threshold):
    """Recovered only if we have `minutes` rows, each with traffic and a rate under threshold."""
    recent = rows[-minutes:]
    if len(recent) < minutes:
        return False, f"only {len(recent)} minutes of data"
    for ts, count, rate in recent:
        if not count:
            return False, f"no traffic at {ts}"
        if rate >= threshold:
            return False, f"5xx {rate:.2f}% at {ts}"
    return True, f"5xx under {threshold}% for {minutes} minutes"


def fetch(minutes):
    import boto3
    cfn = boto3.client("cloudformation", region_name=REGION)
    outputs = {o["OutputKey"]: o["OutputValue"] for o in cfn.describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]}
    api_id = cfn.describe_stack_resource(StackName=STACK, LogicalResourceId="OrdersHttpApi")[
        "StackResourceDetail"]["PhysicalResourceId"]
    end = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    start = end - dt.timedelta(minutes=minutes)
    dims = [{"Name": "ApiId", "Value": api_id}, {"Name": "Stage", "Value": "prod"}]

    def q(qid, name):
        return {"Id": qid, "MetricStat": {"Metric": {"Namespace": "AWS/ApiGateway", "MetricName": name,
                                                     "Dimensions": dims}, "Period": 60, "Stat": "Sum"}}

    cw = boto3.client("cloudwatch", region_name=REGION)
    res = cw.get_metric_data(MetricDataQueries=[q("e", "5xx"), q("c", "Count")], StartTime=start, EndTime=end)
    series = {r["Id"]: dict(zip((t.strftime("%H:%M") for t in r["Timestamps"]), r["Values"]))
              for r in res["MetricDataResults"]}
    return outputs["OrdersEndpoint"], series.get("e", {}), series.get("c", {})


def synthetic_order(url):
    req = urllib.request.Request(url, data=json.dumps({"sku": "NW-1001", "quantity": 1}).encode(),
                                 method="POST", headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read() or b"{}").get("version")
    except urllib.error.HTTPError as err:
        return err.code, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--minutes", type=int, default=10)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--expect-version", default="1.8.0")
    a = p.parse_args()

    url, errors, requests = fetch(a.minutes)
    rows = minute_rates(errors, requests)
    for ts, count, rate in rows:
        print(f"{ts} UTC  requests {int(count):5d}  5xx {'n/a' if rate is None else f'{rate:5.2f}%'}")
    ok_rate, why = judge(rows, a.minutes, a.threshold)
    status, version = synthetic_order(url)
    ok_synth = status == 201 and version == a.expect_version
    print(f"Error rate check: {'PASS' if ok_rate else 'FAIL'} ({why})")
    print(f"Synthetic order:  {'PASS' if ok_synth else 'FAIL'} (status {status}, version {version})")
    sys.exit(0 if ok_rate and ok_synth else 1)


if __name__ == "__main__":
    main()
