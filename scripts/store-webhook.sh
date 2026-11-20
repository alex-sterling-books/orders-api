#!/usr/bin/env bash
# Store the Agent Space webhook URL and HMAC secret in SSM Parameter Store as
# one SecureString. Prompts for both values so they never appear in your shell
# history, a file, or the repository.
# Usage: REGION=us-east-1 ./scripts/store-webhook.sh
set -euo pipefail
REGION="${REGION:-us-east-1}"
NAME="/orders-api/devops-agent-webhook"

read -r -p "Webhook URL: " URL
read -r -s -p "Webhook secret (input hidden): " SECRET; echo

VALUE=$(python3 -c 'import json,sys; print(json.dumps({"url": sys.argv[1], "secret": sys.argv[2]}))' "$URL" "$SECRET")
aws ssm put-parameter --region "$REGION" --name "$NAME" --type SecureString \
  --value "$VALUE" --overwrite >/dev/null
unset SECRET VALUE
echo "Stored ${NAME} as a SecureString in ${REGION}."
