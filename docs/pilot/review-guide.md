# Reviewing a pilot investigation

Review within two working days, while people still remember the incident.

1. Open the investigation in the web app. Export it as Markdown and attach it
   to the incident record.
2. Write the verified root cause from the incident record, not from the agent.
3. Choose one verdict for the log:
   - `correct`: the agent's root cause matches the verified root cause
   - `useful`: not the root cause, but it moved the responders forward
     (named the right service, found the right change, ruled out a suspect)
   - `misleading`: it pointed responders the wrong way, and following it
     would have cost time
   - `inconclusive`: no root cause offered
   - `not_applicable`: not an incident, for example a chat question
4. Record minutes from impact start to the first hypothesis that was correct
   or useful. Leave it empty for misleading and inconclusive.
5. Record agent-seconds if your usage view shows them. If it does not, record
   the investigation's start and end times and note that the value is an
   estimate.
6. Record whether responders relied on the finding (`human_relied`).
7. If the verdict is not `correct`, submit feedback on the investigation with
   the verified root cause, and note any missing telemetry or access.
