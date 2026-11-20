---
name: orders-5xx-investigation
description: Investigation procedure for increased 5xx errors on the Northwind
  Orders API (POST /orders) behind API Gateway HTTP API, the orders-submit and
  inventory-reserve Lambda functions, and the orders DynamoDB table. Use this
  skill when the OrdersApi-5xx-High alarm fires, or when investigating failed
  order submissions, orders-submit timeouts or Lambda errors, DynamoDB
  throttling on the orders table, or the OrdersSubmit-Timeouts alarm.
---

# Orders API 5xx investigation

Use this skill for the OrdersApi-5xx-High alarm and for any report of failed
order submissions.

## Step 1: Fix the start of impact

Query the API Gateway `5xx` and `Count` metrics for the `prod` stage at
one-minute resolution. Report the first minute where the 5xx rate exceeded
1 percent, in UTC. Every later step compares against this time.

## Step 2: List changes in the 60 minutes before impact

Check GitHub deployments for the `production` environment of the orders-api
repository, and Lambda version and alias changes for `orders-submit` and
`inventory-reserve`. For each change, report the time and the diff summary,
including configuration changes.

## Step 3: Read the failure mode in logs

Query `/aws/lambda/orders-submit` for the impact window. Summarize the most
common error messages and any exceptions from boto3 or DynamoDB.

## Step 4: Test each hypothesis against timing (added in version 2)

For every candidate cause, report in UTC when that signal started and when it
stopped, next to the start of impact from Step 1. Then answer:
- Did the signal start before or at the start of impact? A signal that starts
  after impact began cannot be the first cause.
- When the signal stopped, did the errors stop? If errors continue at the same
  rate after a suspected cause ends, that cause is not the root cause.
- Outside any traffic burst, does the count of errors per minute match the count
  of the suspected signal per minute?

## Step 5: Check what is actually running (added in version 2)

Read the configuration of the orders-submit live alias (timeout, APP_VERSION)
rather than relying on the diff. Compare the timeout with the latency of every
synchronous dependency call. Max Duration that stops exactly at the timeout
means calls are being cut off.

## Step 6: Report

Separate the output into three labeled lists:
1. Observations: what you saw, with the metric, log query, or change and its UTC time.
2. Hypotheses: proposed causes, each with the evidence for and against it.
3. Verified: only hypotheses that passed Steps 4 and 5. Mark others as rejected,
   contributing, or open.

Recommend a recovery option only for a verified cause, and name the evidence
that would prove the recommendation wrong.
