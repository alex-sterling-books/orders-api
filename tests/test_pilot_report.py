import importlib.util
import os

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location(
    "pilot_report", os.path.join(HERE, "..", "scripts", "pilot_report.py"))
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)

CFG = {
    "rate_usd_per_agent_second": 0.0083,
    "criteria": {
        "min_reviewed_investigations": 2,
        "min_share_root_cause_correct_or_useful": 0.5,
        "max_share_misleading": 0.5,
        "max_median_minutes_to_useful_hypothesis": 15,
        "max_monthly_cost_usd": 10,
        "max_guardrail_violations": 0,
    },
}


def row(verdict, seconds="100", minutes="5"):
    return {"id": "X", "verdict": verdict, "agent_seconds": seconds,
            "minutes_to_useful_hypothesis": minutes}


def test_chat_rows_count_for_cost_but_not_for_accuracy():
    rows = [row("correct"), row("useful"), row("not_applicable", seconds="1000", minutes="")]
    results = {r[0]: r for r in pr.score(rows, CFG)}
    assert results["Reviewed investigations"][1] == 2
    assert results["Estimated agent cost (USD)"][1].startswith("9.96")


def test_too_few_investigations_fails():
    results = {r[0]: r for r in pr.score([row("correct")], CFG)}
    assert results["Reviewed investigations"][3] is False


def test_guardrail_violation_fails():
    rows = [row("correct"), row("correct")]
    results = {r[0]: r for r in pr.score(rows, CFG, guardrail_violations=1)}
    assert results["Guardrail violations"][3] is False
