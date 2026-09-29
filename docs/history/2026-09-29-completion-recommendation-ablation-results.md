# Latest completion recommendation: closed results

Date: 2026-09-29. Live response-only diagnostic, official=false. Follows the
[frozen design](2026-09-29-completion-recommendation-ablation-design.md) and
[decision audit](2026-09-29-observation-decision-audit.md). No runtime change.

## Question and execution

Does removing the latest computed next-action recommendation cause the model to
address a supplied public counterexample after a registered check passes?
A retains the exact B2 turn-two request; B removes only completion_guidance.next_action
and the imperative run-check recommendation from the latest state. Public evidence,
tools, budgets, plan, earlier history, system prompt and encrypted continuation remain
identical. This is not an ablation of all historical completion language.

User authorized NEW USD 4 by saying proceed after the exact approval request.
Collected A1/B1/B2/A2/A3/B3, hf-hub-xet-endpoint-propagation v5 dev-train,
gpt-5.4-2026-03-05 xhigh, 25K output / 60K input ceiling, exact repository .env,
1800-second invocation deadline. Six counts and six completed model responses;
zero SDK retries, corrections, replacements, tool executions or evaluator calls.
Terminal SAMPLES_COLLECTED after 222.620 seconds. All three pairs completed.

## Arm-masked assessment, then reveal

Six public responses were read in shuffled order without arm labels. Frozen rubric
judgments were saved before reading journal labels. This is arm-masked review by
an informed investigator, not a blind or independent quality evaluation.

| Outcome | A: recommendation retained | B: latest recommendation removed |
| --- | ---: | ---: |
| Explicitly retains supplied observed discrepancy | 2/3 | 1/3 |
| Selects targeted discrepancy-resolving action | 1/3 | 1/3 |
| Both (primary outcome) | 1/3 | 1/3 |
| Selects remaining regression check | 2/3 | 2/3 |

Primary paired B wins / A wins / ties: 1 / 1 / 1. All responses completed with
valid tool-batch shapes. Two targeted responses selected a search for HfApi's
`self.endpoint =` constructor assignment; the other four selected
upstream-xet-regression. These are proposed actions, never executed searches/checks.

A1: regression only, no observed discrepancy retained.
B1: explicit ambient-client discrepancy and targeted constructor search.
B2: regression only; repeats the requirement without retaining the observation.
A2: explicit discrepancy and targeted constructor search.
A3: explicitly notes the external diagnostic and missing visible coverage but still
selects the regression check. B3: mentions the ambient-client concern as an untested
assumption rather than the supplied observation; also selects regression.

The strict recognition rubric counts A3 and not B3. If any ambient-client caveat
were counted instead, recognition would tie at 2/3 each; the primary result stays
1/3 each. This sensitivity is reported without changing the prereveal judgments.
A regression choice in a single sampled response does not prove the model would
never return to the discrepancy later. Only the source episode actually continued.

## Interpretation and decision

No selection advantage appeared from removing this latest recommendation. Retain
the runtime unchanged; this small diagnostic does not support adopting the removal.
It does not rule out completion framing effects elsewhere, effects already carried
in history/continuation, or smaller effects this sample cannot detect. Six samples
of one exposed checkpoint are not six tasks or evidence of general performance.

A3 distinguishes a useful remaining question: recognition can coexist with a next
action that does not resolve the recognized discrepancy. B3 also shows an observed
counterexample can be described merely as an untested assumption. Delivery alone
and a stronger reminder are not established solutions. Before another intervention,
use existing cross-task public traces to check where observed counterexamples are
retained, downgraded, explicitly dismissed or left behind after unrelated PASS.
That audit should separate single-step ordering from later abandonment and keep
operator feedback distinct from registered agent observations. Do not automatically
add a hard submission gate or turn model-authored expectations into trusted failures.
No further paid run or budget reuse is authorized.

## Integrity, cost and evidence

Reconstructed frozen source and verified all six dispatched request artifacts against
cell request hashes, including artifact byte hashes. No unrelated state/tool/history
changes. Six provider starts/finishes and input counts reconcile. Completed responses
have known usage; input/cached/output token arithmetic reproduces all ledger costs.

Settled cost USD 0.2693865; unused USD 3.7306135 is closed. Task acceptance and safety
are NOT_RUN because no proposed tool or evaluator ran. No repair-performance claim.

Execution source commit a3bbff9. Plan:
C:/pt/analyses/completion-recommendation-ablation-20260929-v2
Packet: sha256:7d9e7a0fbaf21b48a85d10ee10b21314b34328a73f1a4abb92a23ff56e56c019.
Approval and allocation closure are recorded in the plan's dev-run-v1 journal.
Live result: C:/pt/guidanceablation0929a/result.json;
run_dev_sample_03d5c7782c59463c. Review and settlement:
C:/pt/analyses/completion-recommendation-results-20260929-v1,
masked-grading.json then summary.json, hash-bound in run_dev_guidancegrading.

Preparation passed 48 relevant tests and Ruff. Closing this experiment changes
only documentation: documentation-layout tests and diff checks are rerun. Historical
records, frozen packets and provider outputs remain unchanged; no extra test or
probe execution is needed to turn this response-only diagnostic into a solve claim.
