#!/usr/bin/env bash
# Create the Northwind Agent Space and its two IAM roles from the CLI.
# Follows the AWS DevOps Agent CLI onboarding guide (checked 2026-11-20).
# Usage: REGION=us-east-1 ./scripts/create-agent-space.sh
set -euo pipefail

REGION="${REGION:-us-east-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
SPACE_NAME="northwind-orders"
AGENT_ROLE="DevOpsAgentRole-AgentSpace"
OPERATOR_ROLE="DevOpsAgentRole-WebappAdmin"
WORK="$(mktemp -d)"

echo "Account: ${ACCOUNT_ID}  Region: ${REGION}"

# 1. Agent Space role: what the agent uses to read your resources.
cat > "${WORK}/agent-trust.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "aidevops.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "${ACCOUNT_ID}"},
      "ArnLike": {"aws:SourceArn": "arn:aws:aidevops:${REGION}:${ACCOUNT_ID}:agentspace/*"}
    }
  }]
}
EOF
aws iam create-role --role-name "${AGENT_ROLE}" \
  --assume-role-policy-document "file://${WORK}/agent-trust.json" >/dev/null
aws iam attach-role-policy --role-name "${AGENT_ROLE}" \
  --policy-arn arn:aws:iam::aws:policy/AIDevOpsAgentAccessPolicy

cat > "${WORK}/agent-slr.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCreateServiceLinkedRoles",
    "Effect": "Allow",
    "Action": ["iam:CreateServiceLinkedRole"],
    "Resource": ["arn:aws:iam::${ACCOUNT_ID}:role/aws-service-role/resource-explorer-2.amazonaws.com/AWSServiceRoleForResourceExplorer"]
  }]
}
EOF
aws iam put-role-policy --role-name "${AGENT_ROLE}" \
  --policy-name AllowCreateServiceLinkedRoles \
  --policy-document "file://${WORK}/agent-slr.json"

# 2. Operator role: what the web app uses on behalf of responders.
cat > "${WORK}/operator-trust.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "aidevops.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"],
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "${ACCOUNT_ID}"},
      "ArnLike": {"aws:SourceArn": "arn:aws:aidevops:${REGION}:${ACCOUNT_ID}:agentspace/*"}
    }
  }]
}
EOF
aws iam create-role --role-name "${OPERATOR_ROLE}" \
  --assume-role-policy-document "file://${WORK}/operator-trust.json" >/dev/null
aws iam attach-role-policy --role-name "${OPERATOR_ROLE}" \
  --policy-arn arn:aws:iam::aws:policy/AIDevOpsOperatorAppAccessPolicy

# IAM changes can take a few seconds to propagate.
sleep 10

# 3. The Agent Space itself.
SPACE_ID="$(aws devops-agent create-agent-space \
  --name "${SPACE_NAME}" \
  --description "Northwind Orders API lab (fictional)" \
  --region "${REGION}" \
  --query 'agentSpace.agentSpaceId' --output text)"
echo "Agent Space ID: ${SPACE_ID}"

# 4. Associate this account as the monitoring account.
aws devops-agent associate-service \
  --agent-space-id "${SPACE_ID}" \
  --service-id aws \
  --configuration "{\"aws\": {\"assumableRoleArn\": \"arn:aws:iam::${ACCOUNT_ID}:role/${AGENT_ROLE}\", \"accountId\": \"${ACCOUNT_ID}\", \"accountType\": \"monitor\"}}" \
  --region "${REGION}" >/dev/null

# 5. Turn on the operator web app with IAM sign-in.
aws devops-agent enable-operator-app \
  --agent-space-id "${SPACE_ID}" \
  --auth-flow iam \
  --operator-app-role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${OPERATOR_ROLE}" \
  --region "${REGION}" >/dev/null

echo "${SPACE_ID}" > .agent-space-id
echo "Done. Saved the Agent Space ID to .agent-space-id"
rm -rf "${WORK}"
