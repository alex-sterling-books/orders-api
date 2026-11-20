#!/usr/bin/env bash
# Point the orders-submit "live" alias back at the newest published version
# whose APP_VERSION matches TARGET. Dry run unless you pass --execute.
# A human approver's name is required to execute, and is written to the
# alias description so CloudTrail and the console show who approved it.
#
# Usage:
#   ./scripts/rollback.sh                      # dry run, target 1.8.0
#   TARGET=1.8.0 ./scripts/rollback.sh --execute --approved-by "Dana (IC)"
set -euo pipefail

REGION="${REGION:-us-east-1}"
FUNCTION="orders-submit"
ALIAS="live"
TARGET="${TARGET:-1.8.0}"
EXECUTE=false
APPROVER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute) EXECUTE=true; shift ;;
    --approved-by) APPROVER="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

describe() {  # version -> "version timeout app_version"
  aws lambda get-function-configuration --region "$REGION" \
    --function-name "${FUNCTION}:$1" \
    --query "[Version, Timeout, Environment.Variables.APP_VERSION]" --output text
}

CURRENT=$(aws lambda get-alias --region "$REGION" --function-name "$FUNCTION" \
  --name "$ALIAS" --query FunctionVersion --output text)

# Newest numbered version with the target APP_VERSION.
CANDIDATE=""
for V in $(aws lambda list-versions-by-function --region "$REGION" --function-name "$FUNCTION" \
            --query "Versions[?Version!='\$LATEST'].Version" --output text | tr '\t' '\n' | sort -rn); do
  APPV=$(aws lambda get-function-configuration --region "$REGION" --function-name "${FUNCTION}:${V}" \
          --query "Environment.Variables.APP_VERSION" --output text)
  if [[ "$APPV" == "$TARGET" ]]; then CANDIDATE="$V"; break; fi
done

if [[ -z "$CANDIDATE" ]]; then
  echo "No published version of ${FUNCTION} has APP_VERSION ${TARGET}. Stopping." >&2
  exit 1
fi

echo "Pre-checks"
echo "  Alias ${ALIAS} now -> version, timeout, app: $(describe "$CURRENT")"
echo "  Rollback target    -> version, timeout, app: $(describe "$CANDIDATE")"
if [[ "$CURRENT" == "$CANDIDATE" ]]; then
  echo "  The alias already points at the target. Nothing to do."
  exit 0
fi
STATE=$(gh api "repos/{owner}/{repo}/actions/workflows/deploy.yaml" --jq .state 2>/dev/null || echo "unknown")
echo "  Deploy workflow state: ${STATE} (should be disabled_manually before you execute)"

if [[ "$EXECUTE" != true ]]; then
  echo
  echo "Dry run only. To roll back, rerun with --execute --approved-by \"<name and role>\"."
  exit 0
fi

if [[ -z "$APPROVER" ]]; then
  echo "Refusing: --approved-by is required to execute." >&2
  exit 1
fi
if [[ "$STATE" != "disabled_manually" ]]; then
  echo "Refusing: disable the deploy workflow first (gh workflow disable deploy)," >&2
  echo "or the next push to main can redeploy the broken version." >&2
  exit 1
fi

read -r -p "Type ROLLBACK to move ${ALIAS} from version ${CURRENT} to ${CANDIDATE}: " CONFIRM
[[ "$CONFIRM" == "ROLLBACK" ]] || { echo "Not confirmed. Nothing changed."; exit 1; }

STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
aws lambda update-alias --region "$REGION" --function-name "$FUNCTION" --name "$ALIAS" \
  --function-version "$CANDIDATE" \
  --description "Rolled back from v${CURRENT} at ${STAMP}, approved by ${APPROVER}" >/dev/null

echo "${STAMP}  Alias ${ALIAS} now points at version ${CANDIDATE} (approved by ${APPROVER})."
echo "Record this time in your incident timeline, then run: python3 scripts/check_recovery.py"
