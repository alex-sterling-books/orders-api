# Runbook: OrdersApi-5xx-High

Owner: Orders team (fictional Northwind Supply). Last reviewed: 2026-12-10. Version 2 (after the 2026-12-08 incident).

## What this alarm means

More than 2 percent of `POST /orders` requests returned a 5xx status in 3 of
the last 5 one-minute periods. Customers are failing to place some orders.

## First five minutes

1. Acknowledge the page and post in the incident channel with a next-update time.
2. Size impact on the Orders API dashboard: 5xx rate, request count, start time.
3. Set severity from impact. About 1 to 20 percent failing is SEV2. More is SEV1.
4. Open the AWS DevOps Agent investigation. Add anything the agent cannot know.

## What to check

| Check | Where | What it tells you |
| --- | --- | --- |
| When 5xx started, to the minute | API Gateway `5xx` metric for the `prod` stage | The start of impact |
| Recent deploys | `#orders-deploys`, GitHub deployments for `production` | A candidate change |
| `orders-submit` errors and timeouts | Log group `/aws/lambda/orders-submit` | The failure mode |
| Live configuration | `aws lambda get-function-configuration --function-name orders-submit:live` | The timeout and version actually running |
| `orders-submit` Duration, max and p99 | Lambda metrics, or Logs Insights on `REPORT` lines | Whether calls stop at the timeout |
| `inventory-reserve` slow calls | Log group `/aws/lambda/inventory-reserve` | Whether the dependency is slow |
| DynamoDB `ThrottledRequests` on `orders` | DynamoDB metrics | Whether writes are throttled |

## Test before you conclude (added in version 2)

For each suspected cause, compare when it started and stopped with when the
errors started and stopped. A signal that starts after the errors, or ends while
the errors continue, is not the root cause. See `docs/verification-queries.md`.

## Known behavior

- Promotion emails go out on the hour, often on Tuesdays. The traffic burst usually
  arrives 15 to 25 minutes later.

## Recovery options

- Roll back: `./scripts/rollback.sh` (dry run), then disable the deploy workflow
  and run it with `--execute --approved-by "<name and role>"`.
  Needs incident commander approval. Revert the release on main afterward.
- Fix forward: deploy a corrected version through the pipeline. Needs the
  Orders owner and incident commander to agree it is lower risk than rollback.

## Confirm recovery

- 5xx rate below 0.5 percent for 10 minutes.
- A synthetic order returns 201 from the expected version.
- Both checks: `python3 scripts/check_recovery.py --expect-version <version>`.
