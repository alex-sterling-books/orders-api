#!/usr/bin/env python3
"""Score a DevOps Agent pilot against criteria the team set before it began.

Usage: python3 scripts/pilot_report.py [docs/pilot/pilot-log.csv] [config/pilot-criteria.json]

The log has one row per agent investigation or chat. A human fills in
`verdict` during review:
  correct         agent's root cause matched the verified root cause
  useful          not the root cause, but it moved the responders forward
  misleading      pointed responders the wrong way
  inconclusive    no root cause offered
  not_applicable  not an incident (for example, a chat question)

Cost is estimated from agent_seconds at the configured rate. Compare it with
your bill: the bill is the record, this is an estimate. Other services the
agent queries (for example, Logs Insights) are billed separately and are not
included here.
"""
import csv
import json
import statistics
import sys

VERDICTS = {"correct", "useful", "misleading", "inconclusive", "not_applicable"}


def load(log_path, criteria_path):
    with open(log_path, newline="") as f:
        rows = list(csv.DictReader(f))
    with open(criteria_path) as f:
        cfg = json.load(f)
    for r in rows:
        if r["verdict"] not in VERDICTS:
            raise SystemExit(f"{r['id']}: unknown verdict {r['verdict']!r}")
    return rows, cfg


def score(rows, cfg, guardrail_violations=0):
    rate = cfg["rate_usd_per_agent_second"]
    c = cfg["criteria"]
    incidents = [r for r in rows if r["verdict"] != "not_applicable"]
    n = len(incidents)
    good = sum(r["verdict"] in ("correct", "useful") for r in incidents)
    misleading = sum(r["verdict"] == "misleading" for r in incidents)
    minutes = [int(r["minutes_to_useful_hypothesis"]) for r in incidents
               if r["minutes_to_useful_hypothesis"]]
    seconds = sum(int(r["agent_seconds"]) for r in rows)
    cost = seconds * rate
    median = statistics.median(minutes) if minutes else None

    results = [
        ("Reviewed investigations", n, f">= {c['min_reviewed_investigations']}",
         n >= c["min_reviewed_investigations"]),
        ("Correct or useful", f"{good}/{n} ({good / n:.0%})" if n else "0/0",
         f">= {c['min_share_root_cause_correct_or_useful']:.0%}",
         n > 0 and good / n >= c["min_share_root_cause_correct_or_useful"]),
        ("Misleading", f"{misleading}/{n} ({misleading / n:.0%})" if n else "0/0",
         f"<= {c['max_share_misleading']:.0%}",
         n > 0 and misleading / n <= c["max_share_misleading"]),
        ("Median minutes to useful hypothesis", median,
         f"<= {c['max_median_minutes_to_useful_hypothesis']}",
         median is not None and median <= c["max_median_minutes_to_useful_hypothesis"]),
        ("Estimated agent cost (USD)", f"{cost:.2f} ({seconds} agent-seconds)",
         f"<= {c['max_monthly_cost_usd']}", cost <= c["max_monthly_cost_usd"]),
        ("Guardrail violations", guardrail_violations,
         f"<= {c['max_guardrail_violations']}",
         guardrail_violations <= c["max_guardrail_violations"]),
    ]
    return results


def main(argv):
    log_path = argv[1] if len(argv) > 1 else "docs/pilot/pilot-log.csv"
    criteria_path = argv[2] if len(argv) > 2 else "config/pilot-criteria.json"
    rows, cfg = load(log_path, criteria_path)
    results = score(rows, cfg)
    print(f"Pilot: {cfg['pilot']}")
    width = max(len(r[0]) for r in results)
    for name, value, target, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {value}  (target {target})")
    passed = all(r[3] for r in results)
    print("ALL CRITERIA MET" if passed else "NOT ALL CRITERIA MET: see FAIL lines")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
