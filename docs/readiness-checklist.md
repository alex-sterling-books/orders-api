# Context readiness checklist: Orders API

Run this before an incident, after any change to connections, skills, or
instructions, and at least once a month. Record the date and who ran it.

Date: ____________  Run by: ____________  Agent Space: northwind-orders

## Part 1: Connections

| Check | Where | Pass when | Result |
| --- | --- | --- | --- |
| AWS account associated as monitor | Console, Agent Space, Capabilities | Test account listed | |
| GitHub repository connected | Console, Capabilities, Pipeline | `orders-api` listed | |
| Release review triggers off for the lab | Code Review and Automated Testing | Both boxes cleared for `orders-api` | |
| Runbook skill imported and Active | Web app, Knowledge, Skills | `orders-5xx-investigation` is Active | |
| Global instructions saved | Web app, Agents, Agent definition | AGENTS.md content shown | |
| Directive about promotions saved | Web app, Knowledge, Memories, directives | Memory present | |

## Part 2: What the agent knows (Summary report and Topology)

| The agent should know | Pass when | Result |
| --- | --- | --- |
| The request path | API Gateway route to `orders-submit` alias `live` to the `orders` table | |
| The dependency | `orders-submit` can call `inventory-reserve` | |
| The alarm | `OrdersApi-5xx-High` is linked to the API | |
| The log groups | `/aws/lambda/orders-submit` and `/aws/lambda/inventory-reserve` | |
| The repository | `orders-api` maps to both functions and the table | |
| The pipeline | GitHub Actions `deploy` workflow to the `production` environment | |

## Part 3: Dry run in chat (score each 2 = correct and sourced, 1 = partial, 0 = wrong or missing)

| Question to ask the agent | Expected answer | Score |
| --- | --- | --- |
| What is the request path for POST /orders? | API Gateway, `orders-submit` (`live`), DynamoDB `orders` | |
| What was the most recent production deployment, and what changed? | The latest `deploy` run and its commit | |
| Which alarm covers failed orders, and what is its threshold? | `OrdersApi-5xx-High`, above 2 percent in 3 of 5 minutes | |
| Which log groups would you query for a failed order? | The two Lambda log groups | |
| Which skill applies if OrdersApi-5xx-High fires? | `orders-5xx-investigation` | |
| Is anything expected to cause traffic bursts? | Promotion emails on the hour, burst 15 to 25 minutes later | |

Total: ____ / 12. Ready when every row in Parts 1 and 2 passes and the
dry run scores 10 or more with no zeros.

## Gaps found and fixes

| Gap | Fix | Owner | Done |
| --- | --- | --- | --- |
| | | | |
