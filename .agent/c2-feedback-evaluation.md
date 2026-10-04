# C2 public-regression feedback continuation

Status: approved two-row allocation completed and closed; no further work funded.
Public repair 2/2; original acceptance 1 PASS, 1 NOT_RUN after cost exhaustion.
New cost USD 0.9083865. See the [results](../docs/history/2026-10-04-c2-feedback-results.md).
The [fourth-edit choice evaluation](../docs/history/2026-10-04-c2-choice-results.md)
is closed. This was a separate funded continuation, not a reopened run.

## Question and minimal change

Can the agent use a completed public regression failure to repair its candidate
with one additional accepted edit, preserving the issue output? Use the existing
max_accepted_mutations setting at 5. No conditional budget-issuing policy, new
prompt, gate or reviewer is introduced; the selected baseline stays at 4.

Take one continuation from each of the two recently failed candidates. Preserve
the original journal prefix through the failed check's completed tool batch, four
accepted edits, public receipts, native state and all settled usage. Exclude the
terminal record and later operator measurements. The original run has no next
model request: the ordinary runner generates a new input under the five-edit
envelope. This input is frozen offline, then independently recounted before any
approved paid dispatch. It is not a historical request replay.

Ordinary resume still rejects a changed envelope. A fresh external diagnostic
fork records source identity and the 4-to-5 limit change; source files/journals
are immutable. Synthetic repair fixtures never enter the funded seed prefixes.

## Executed paid scope

Registered dev-train task: swebench-lite-dev-sqlfluff-sqlfluff-1733.
Model: gpt-5.4-2026-03-05, xhigh, desired output ceiling 25,000 tokens.
Credential path: C:/Users/geonj/Documents/PatchLoop/.env.
Order: one continuation from live1, then one from live2; no replacement repeats.

| Source | Additional calls | Additional actions | Additional edits | Remaining active seconds at failure | New USD cap |
| --- | ---: | ---: | ---: | ---: | ---: |
| C:/pt/c2cp01/live1 | 21 | 65 | 1 | 544.085 | 0.5849210 |
| C:/pt/c2cp01/live2 | 22 | 64 | 1 | 611.741 | 0.8077385 |

Total new invocation cap: USD 1.3926595. Historical settled costs, USD 2.415079
and USD 2.1922615 respectively, remain bookkeeping and are not billed again.
No old allocation was reopened; a new exact-scope approval authorized these amounts.
The caps are inherited remainders, not a guarantee that all nominal calls can fit.
Per-call cost admission and normal completion reserves remain active.

Source remaining time is an upper bound, not a reset. Copied preparation timing
and ordinary runner preflight/counting/actions consume the existing deadline.
Frozen initial views display 543 and 611 seconds respectively. The prefix, prepared
input and envelope are independently bound in the external manifest.

Zero SDK retries. No automatic resume, replacement, budget transfer, sixth edit,
time extension or post-result changes. Count, transport, billing, cleanup or
identity uncertainty stops the whole allocation. Use existing local images only;
missing environments stop preparation/execution without pull/build.

## Outcomes and limits

On each final candidate, run the existing independent issue-output program and
registered base-regression check, with a separate 120-second operator deadline.
Both must pass on the same diff for public success. Keep the existing required
checks and normal finish path; hidden acceptance runs only if the model submits.
Otherwise acceptance is NOT_RUN. Post-run observations never return to the model.
Record solver time, operator time, all new usage and original acceptance/safety
separately. Patch cleanup is not a success condition.

Success demonstrates correction under failure feedback plus an additional
edit on these exposed candidates. It does not isolate feedback's causal effect,
show better fourth-edit scope judgment, establish general product performance,
or justify a conditional extension policy. This bounded scope is closed;
unused resources do not authorize another experiment.

## Implementation and evidence

External preparation: C:/pt/analyses/c2-feedback-prep-20261004-v1.
prepare.py composes existing prefix/CAS, candidate restoration and runner helpers.
verify.py tests errors and an operator-authored fifth-edit fixture. collect.py
reuses the existing new-usage ledger and collector, with a fresh single-use
allocation and manifest-bound human authorization. That authorization is consumed.
The [preparation report](../docs/history/2026-10-04-c2-feedback-preparation.md)
records the earlier provider-free state. The results report records actual autonomous
repair separately. Execution commit: 89c1ff4ccb06ca30b2436fcbd8f48018b6a46528.
Frozen pre-execution scope bytes: C:/pt/c2fb01/allocation/approved-scope.md.
