# Pilot charter: AWS DevOps Agent for Orders on-call

> Fictional example from the book. Copy the headings, replace every value.

## Question the pilot answers
Should the Orders on-call rotation use AWS DevOps Agent for every paging alarm,
and should a second team join?

## Scope
- Team: Orders on-call (5 engineers), incident commander rotation (2)
- Service: Orders API in the production account only
- Agent Space: `orders-prod`, separate from the `orders-api-lab` practice space
- Allowed: investigations started by the paging alarms, chat, Review
- Not allowed during the pilot: directed actions (no AIDevOpsAgentActionsPolicy),
  automatic Support case creation, any other team's accounts

## Dates
- Week 1 (2027-01-04): shadow. The agent investigates; responders do not use it
  until after the incident. Every investigation is reviewed.
- Weeks 2 to 4: assist. Responders may use the agent's findings, and must verify
  them with the evidence ledger before acting.
- 2027-02-01: decision meeting.

## Success criteria (set before the pilot, recorded in config/pilot-criteria.json)
| Criterion | Target |
| --- | --- |
| Reviewed investigations | at least 12 |
| Correct or useful | at least 60 percent |
| Misleading | at most 15 percent |
| Median minutes to a useful hypothesis | at most 15 |
| Estimated agent cost for the pilot | at most 400 USD |
| Guardrail violations | 0 |

## People
- Pilot owner: Dana (IC)
- Reviewer each week: the on-call engineer coming off shift, with Jordan (SRE)
- Cost watcher: Priya
- Can stop the pilot at any time: Dana or the Orders engineering manager

## Stop conditions
- Any write to production by the agent, or any attempt blocked by the guardrail
  that nobody can explain
- A responder acting on an unverified agent finding during an incident
- Estimated cost passes 75 percent of the limit before week 3
