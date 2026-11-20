"""Release check: does the orders-submit timeout cover its dependency calls?

Follow-up from the 2026-12-08 incident (postmortem action item 1). Runs in CI
before deploy. It fails when the function timeout is shorter than the time the
function may need to wait for the dependencies it calls synchronously.

Rule:
  For each dependency the code calls, the wait is the client timeout set in
  code (read_timeout=...), or the dependency's worst case if no client timeout
  is set. Required = (own_work_ms + sum of waits) x safety_factor.
  The check fails if the function timeout is below Required.

Usage: python3 scripts/check_release.py   (from the repository root)
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def function_timeout_s(template_text):
    m = re.search(r"OrdersSubmitTimeout:\s*\n\s*Type: Number\s*\n\s*Default: (\d+)", template_text)
    if not m:
        raise ValueError("Could not find the OrdersSubmitTimeout default in template.yaml")
    return int(m.group(1))


def dependency_waits(code_text, budgets):
    """Return {dependency: (wait_ms, how)} for dependencies the code calls."""
    waits = {}
    calls_inventory = "INVENTORY_FUNCTION" in code_text and ".invoke(" in code_text
    if calls_inventory:
        dep = budgets["dependencies"]["inventory-reserve"]
        m = re.search(r"read_timeout\s*=\s*([0-9.]+)", code_text)
        if m:
            waits["inventory-reserve"] = (float(m.group(1)) * 1000, "client timeout in code")
        else:
            waits["inventory-reserve"] = (dep["worst_case_ms"], "no client timeout; worst case from budget")
    return waits


def evaluate(template_text, code_text, budgets):
    timeout_ms = function_timeout_s(template_text) * 1000
    waits = dependency_waits(code_text, budgets)
    required = (budgets["own_work_ms"] + sum(w for w, _ in waits.values())) * budgets["safety_factor"]
    return timeout_ms, waits, required, timeout_ms >= required


def main():
    budgets = json.loads((ROOT / "config/latency-budgets.json").read_text())
    template = (ROOT / "template.yaml").read_text()
    code = (ROOT / "src/orders_submit/app.py").read_text()
    timeout_ms, waits, required, ok = evaluate(template, code, budgets)

    print(f"orders-submit timeout: {timeout_ms:.0f} ms")
    for dep, (wait, how) in waits.items():
        print(f"  waits on {dep}: up to {wait:.0f} ms ({how})")
    if not waits:
        print("  no synchronous dependency calls found")
    print(f"required with safety factor: {required:.0f} ms")
    if ok:
        print("PASS: the timeout covers the function's own work and its dependency waits.")
        return 0
    print("FAIL: the function can time out while waiting on a dependency.")
    print("Fix: set a client timeout on the dependency call, raise the function timeout,")
    print("or update config/latency-budgets.json with reviewed numbers.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
