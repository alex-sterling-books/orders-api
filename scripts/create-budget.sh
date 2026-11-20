#!/usr/bin/env bash
# Create a monthly cost budget that emails you at 50, 80, and 100 percent.
# Usage: LIMIT_USD=25 EMAIL=you@example.com ./scripts/create-budget.sh
set -euo pipefail

LIMIT_USD="${LIMIT_USD:-25}"
EMAIL="${EMAIL:?Set EMAIL to the address that should get budget alerts}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

NOTIFS=""
for PCT in 50 80 100; do
  NOTIFS+="{\"Notification\":{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":${PCT},\"ThresholdType\":\"PERCENTAGE\"},\"Subscribers\":[{\"SubscriptionType\":\"EMAIL\",\"Address\":\"${EMAIL}\"}]},"
done
NOTIFS="[${NOTIFS%,}]"

aws budgets create-budget \
  --account-id "${ACCOUNT_ID}" \
  --budget "{\"BudgetName\":\"orders-api-lab\",\"BudgetLimit\":{\"Amount\":\"${LIMIT_USD}\",\"Unit\":\"USD\"},\"TimeUnit\":\"MONTHLY\",\"BudgetType\":\"COST\"}" \
  --notifications-with-subscribers "${NOTIFS}"

echo "Budget orders-api-lab created: ${LIMIT_USD} USD per month, alerts to ${EMAIL}"
