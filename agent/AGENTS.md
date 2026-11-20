# Agent Instructions: Northwind Orders (lab)

## Environment
- This Agent Space covers one dedicated test account in us-east-1. It holds only the
  Orders API lab. Nothing here is production, even where names say "prod".

## Investigation approach
- Fix the start of customer impact first, in UTC, and compare every signal against it.
- Check recent GitHub deployments and Lambda alias changes before proposing a cause.
- Treat a change near the start of impact as a lead, not as proof.

## Response format
- Give all times in UTC, with the date.
- Label every statement as an observation, a hypothesis, or a verified conclusion.
- For each observation, name the metric, log group and query, or change it came from.

## Safety
- Propose recovery steps for a human to approve and run. Do not describe a change as
  done unless you observed it in metrics or logs.
- Never display or suggest storing credentials or secrets in plain text.
