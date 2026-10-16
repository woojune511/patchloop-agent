# Submission assessment comparison proposal

Date: 2026-10-16. Proposed scope only; provider and evaluator execution NOT_RUN.
No spending approval, runnable manifest or live-readiness claim is established.
This is a separate allocation from the older revision and OpenSandbox comparisons.

## Question and alternatives

Does requiring an agent submission assessment after public PASS produce useful
additional verification or repair, and improve independent acceptance under the
same resources? The observed problem is public PASS followed by failed independent
acceptance despite remaining tools and resources. The intervention is the complete
submission-judgment change: schema, prompt and completion guidance together.

Alternatives matter: assessment may become a ceremonial sentence; extra actions
may test the wrong behavior; or resource exhaustion may prevent useful follow-up.
An assessment string or more tool calls alone is not improvement evidence. The
agent may also improve its initial patch before PASS because the changed contract
is visible from the start; distinguish that from repair after PASS.

## Proposed targets

Use these exact checked-in dev-train public inputs, in index order. All four had
current-diff public PASS, registered/native FAIL agreement, safety PASS, confirmed
cleanup and known billing in corrected dev20. The earlier complete portfolio panel
also recorded public PASS and agreeing FAIL for all four.

| Index | Exact public input | Task | Publicly observed verification gap | Historical USD |
| --- | --- | --- | --- | ---: |
| 7 | `tasks/dev-train/current-dev20/7/public.yaml` | pydicom-1139 | Added tests still left the task unresolved; tests alone are not evidence of correctness | 0.16163415 |
| 10 | `tasks/dev-train/current-dev20/10/public.yaml` | pydicom-901 | Broad regression PASS without directly checking the reported logging behavior | 0.20759940 |
| 13 | `tasks/dev-train/current-dev20/13/public.yaml` | astroid-1333 | Pre-edit probes were not repeated on the changed entry point | 0.57627510 |
| 19 | `tasks/dev-train/current-dev20/19/public.yaml` | sqlfluff-1763 | Regression PASS without directly checking the reported failure path | 0.38271660 |

Selection evidence: [corrected results](../docs/history/2026-10-06-corrected-dev20-results.md),
[public trace review](../docs/history/2026-10-06-agent-trace-comparison.md),
`C:/pt/cd20p06c/result.json`,
`C:/pt/analyses/current-dev20-corrected-20261006/comparison.json`, and
`examples/portfolio-dev20/results.json`. The corrected run IDs, in roster order:
`run_dev_91cde4ad4ec44e45`, `run_dev_b78da4b49dc0426f`,
`run_dev_4973e7b5f39a4978`, `run_dev_85f0a06d652047c1`.

Prefer these over pvlib-1707, which passed the newer panel; astroid-1268, whose
public expected output is ambiguous; and heavily repeated SQLFluff-1517/1733
diagnostics. All selected tasks remain development-exposed, not held-out examples.
Historical failures select the roster; they do not replace fresh A measurements.
Do not deliver this protocol, past outcomes, selection notes, hidden tests or
reference patches to the coding agent. Use only the original public task context.

## Arms and common conditions

- A: `7d483d239236df9a27f7542064ea6f46ec168396`, immediately before the change.
- B: `a18976699ed16533516b4347df935e0dea51d161`, required finish assessment and
  review guidance. Compare this fixed revision, not a moving working tree.
- Both: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 tokens, standard
  tier/global endpoint, credential file `C:/Users/geonj/Documents/PatchLoop/.env`.
  Mini is selected for this panel to match the historical failures and control
  cost; the project's general full-model baseline is unchanged.
- Both: current agent policy; segmented-v1; result-or-size-v1; brief-v1; 24,000
  retained source characters; ordinary probes and selected tests available;
  probe-policy none; probe-recheck none; repair-recheck true; protected-v1;
  per-call-v1. Additive test permissions are those of the unchanged task packages.
- Each fresh solve: 40 model calls, 100 actions, four accepted edits, 1,800 seconds,
  including the existing 330-second evaluation reservation. No seeded patch,
  earlier conversation, shared notes or previous solution is supplied.
- Four tasks x two arms x two repetitions = 16 fresh solves, eight per arm.
  Run four waves A1, B1, B2, A2, with two workers and fixed roster order per wave.
  Every row uses an independent task workspace, interpreter, journal and ledger.
  Repetitions are stochastic samples; no fixed seed is claimed.

Keep task bytes, prepared source/dependencies, existing pinned images and evaluator
identities identical across arms. Runtime source differences are limited to the
submission-assessment commit; its mock/test/documentation migrations are not extra
solver interventions. No task-specific prompt or forced probe is introduced.

## Cost ceiling

Propose USD 1.20 per solve and USD 19.20 for the entire invocation, with no transfer,
replacement, retry, resume or automatic extra repetition. This covers all model
usage in the experiment, including reasoning output. Local evaluation uses the
existing Docker images; no paid judge or newly rented compute is included.

[Official standard pricing](https://developers.openai.com/api/docs/pricing), fetched
on 2026-10-16, agrees with the registered mini rates: USD 0.75 input, 0.075 cached
input and 4.50 output per million tokens. Count immediately before dispatch and
reserve uncached input plus bounded output; use zero SDK retries. A 60K input /
25K output call reserves at most USD 0.1575 under these rates. The row cap does not
guarantee 40 maximum-size calls; per-call-v1 may reduce the output ceiling and does
not guarantee a further review call. Record remaining money/time/actions/edits at
the first PASS rather than changing the reservation policy in one arm.

The four historical runs cost USD 1.32822525 in total. Multiplying that observation
by four gives USD 5.312901 for scale only, not a forecast or a smaller spending cap.
The extra review behavior being tested can increase actual cost.

## Measurements

Define first PASS as the first nonempty candidate whose complete set of required
checks has healthy PASS receipts on that exact diff. It is not the first unrelated
test success. Record its diff hash, public evidence and remaining resources.

For each row, report separately:

1. Declared judgment: finish assessment presence and its concise public conclusion.
   This is model-authored information, not proof that useful review occurred.
2. Observable follow-up after first PASS: reads/searches, selected tests/probes,
   required checks, attempted/accepted edits and changed source versus test files.
   No-action finish and resource-limited opportunity remain distinct outcomes.
3. Patch transitions: first-PASS versus final diff, accepted edits between them,
   and fresh required-check PASS on the final diff after any modification.
4. Quality: final registered/native acceptance, agreement, safety and infrastructure
   status, plus settled cost, model calls and elapsed time. More actions without
   better acceptance are not a quality gain.

Preserve the exact first-PASS patch as well as the final candidate. After all 16
solver rows and provider activity are closed, evaluate first-PASS candidates with the same
isolated evaluators, without returning results to any agent. Bound this to at most
one additional candidate per solve (16 additional, 32 candidate identities total
including finals); identical first/final candidates reuse that row's bound receipt.
This lets the report distinguish FAIL-to-PASS late repair, PASS-to-FAIL regression,
and unchanged correctness. These offline jobs do not extend the solver's 1,800
seconds or consume its 330-second reserve. Proposed bounds are two concurrent
candidate jobs, each with 330 seconds for registered replay and 600 seconds for
the existing native subprocess, retaining the frozen command/resource limits and
cleanup stop conditions. Native grading is outside the solver window, including
for final submissions; the 330-second reserve does not cover both graders.
Record offline time separately. Verify snapshot reconstruction and these grading
bounds provider-free before freezing the execution manifest.

## Interpretation and stop rules

Primary comparison: acceptance counts for each task out of two per arm and final
acceptance across eight intended rows per arm. Also show evaluated denominators,
FAIL, ERROR and NOT_RUN separately; missing evaluations are not wrong-answer
verdicts. Secondary results explain whether gains arose before or after first PASS.

A positive result within this panel needs complete known accounting and grading,
more B acceptances, and no task with fewer B acceptances. A gain with a task-level
regression is a tradeoff. Equal acceptance with more work is no correctness gain;
assessment-only output is not observed additional verification. Incomplete exposure
or unavailable grading leaves the corresponding question unresolved. With four
selected tasks and two samples each, do not claim statistical significance, general
accuracy, or improvement on unseen tasks. No automatic adoption or larger run follows.

Freeze before dispatch. Stop further admissions on count, transport, billing or
cleanup uncertainty, unexplained completed evaluator disagreement, or identity drift.
Retain already-admitted usage. Known, reconciled row-cap exhaustion remains local
to that fixed allocation. Do not tune the prompt, change targets, expand budgets,
or inspect hidden failures to author repairs during the comparison.

## Preparation remaining

The task files, saved result metadata and referenced prepared descriptors exist.
Current Docker/image readiness and model access are unverified. No credential
contents, provider calls, task execution or evaluator execution were needed for
this proposal. No previous manifest, ready receipt or spending approval applies.

Before requesting exact execution approval, prepare fresh external roots and a
manifest binding both checkout/runtime hashes, launcher and snapshot observer,
normalized requests, task/public/source/dependency/image identities, opaque private
package/evaluator identity, model/prices, credential path, roster and all caps.
Verify isolated checkout imports, snapshot/hash reconstruction, stop/accounting,
both mock submissions and local evaluator readiness. Preserve existing state and
history; never pull/build evaluator images automatically. Keep official=false and
claim_eligible=false. This note is the target/budget proposal, not that manifest.
