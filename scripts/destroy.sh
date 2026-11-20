#!/usr/bin/env bash
# Remove everything the lab created. Safe to run more than once.
# Usage: REGION=us-east-1 ./scripts/destroy.sh
set -uo pipefail

REGION="${REGION:-us-east-1}"
STACK="orders-api"

echo "Deleting the webhook parameter, if present..."
aws ssm delete-parameter --name /orders-api/devops-agent-webhook --region "${REGION}" 2>/dev/null

echo "Deleting the GitHub deploy role stack, if present..."
aws cloudformation delete-stack --stack-name orders-api-github-oidc --region "${REGION}" 2>/dev/null

echo "Deleting the application stack (${STACK})..."
sam delete --stack-name "${STACK}" --region "${REGION}" --no-prompts

if [[ -f .agent-space-id ]]; then
  SPACE_ID="$(cat .agent-space-id)"
  echo "Deleting Agent Space ${SPACE_ID}. Its investigation data cannot be recovered."
  aws devops-agent delete-agent-space --agent-space-id "${SPACE_ID}" --region "${REGION}" \
    && rm -f .agent-space-id
fi

for ROLE in DevOpsAgentRole-AgentSpace DevOpsAgentRole-WebappAdmin; do
  echo "Removing IAM role ${ROLE}..."
  aws iam delete-role-policy --role-name "${ROLE}" --policy-name AllowCreateServiceLinkedRoles 2>/dev/null
  for ARN in $(aws iam list-attached-role-policies --role-name "${ROLE}" \
      --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do
    aws iam detach-role-policy --role-name "${ROLE}" --policy-arn "${ARN}"
  done
  aws iam delete-role --role-name "${ROLE}" 2>/dev/null
done

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
aws budgets delete-budget --account-id "${ACCOUNT_ID}" --budget-name orders-api-lab 2>/dev/null \
  && echo "Deleted budget orders-api-lab"

echo
echo "Check that nothing is left:"
aws cloudformation describe-stacks --stack-name "${STACK}" --region "${REGION}" 2>&1 | grep -q "does not exist" \
  && echo "  stack: gone" || echo "  stack: STILL PRESENT"
aws devops-agent list-agent-spaces --region "${REGION}" --query 'agentSpaces[].name' --output text
echo "  (the list above should not include northwind-orders)"
