# Game day: rehearse the revised Orders API response

Test account only. Announce the game day before you start, so nobody mistakes
it for a real incident. Times UTC.

## Goal
Find out whether the follow-ups from the 2026-12-08 postmortem change the next
response. Measure, do not assume.

## Roles
- Facilitator: runs the scenario and the clock. Does not help the responders.
- On-call engineer: responds as if it were real, using runbook version 2.
- Incident commander: approves recovery.
- Observer: records times in the scorecard below.

## Scenario (the facilitator keeps this hidden from the responders)
Deploy the v1.9.0 failure from a game-day branch, bypassing the release check on
purpose, because the point is to rehearse the response, not the prevention:

    git switch -c game-day-<date>
    python3 scripts/apply-v1.9.0.py
    make deploy            # from a laptop; the pipeline would block this change

Start steady traffic first (2 requests per second). Add the promotion burst
13 minutes after the new version starts serving.

## Before you start: check that prevention works
On a separate branch, open a pull request with the v1.9.0 change. The release
check in CI must fail. If it passes, stop and fix action item 1 first.

## Scorecard

| Measure | Baseline (2026-12-08) | Target | Game day result |
| --- | --- | --- | --- |
| Impact began to first alarm | 4 min | 3 min or less (`OrdersSubmit-Timeouts`) | |
| Impact began to page acknowledged | 9 min | 5 min or less | |
| Agent's first hypothesis names the timeout | No (named throttling) | Yes | |
| Impact began to verified root cause | 30 min | 15 min or less | |
| Impact began to mitigation applied | 35 min | 20 min or less | |
| Recovery criteria met, with check_recovery.py | Yes | Yes | |
| Pipeline disabled before rollback | Yes | Yes | |

## After the game day
- Restore the lab: revert the game-day branch's change through the pipeline, or
  run `make destroy`.
- File results next to the postmortem. For every target missed, add one action item.
