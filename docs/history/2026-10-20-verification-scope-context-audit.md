# Verification scope in the actual recovery-comparison inputs

The original public task and scope warnings survived all **358 saved model
requests**. This does not establish that the needed verification and the performed
verification were represented as a concrete, durable comparison. B's 202 requests
all carried `original_task_verification=no_bound_reproduction`, with no declared
case. B1 and B5 submitted with an unresolved verification concern still visible.
There is also contradictory concern bookkeeping in B2 and B6.

This is a provider-free follow-up to the
[closed recovery comparison](2026-10-20-recovery-schema-results.md), selected because
repeated public PASS followed by original-caller failure could reflect either lost
requirements/results or a failure to use preserved evidence. No runtime, submission,
grade, spending limit, transition, reference count or earlier artifact was changed.
No provider or evaluator was called.

## Evidence and method

- Source: the twelve `audit-public/{A,B}-r{1..6}-t13.json` files in
  `C:/pt/evidence-comparison38/`, containing the actual dispatched public inputs.
- Original manifest:
  `sha256:35e9de083dbbe2758e2c22f6559225995756a9b3795e3b7f087b2e6a1c9f7347`.
- New evidence: `C:/pt/evidence-comparison38-scope-audit-20261020/audit.py`,
  `audit.json` and `runs/run_dev_scopeaudit38.jsonl`. The JSON records input hashes,
  request counts, selected complete scope snapshots and per-request probe retention.
- Audit artifact:
  `sha256:2b9046bbaa66202e39b6bd4e52e12206bc370514704847c9d8f4e2b3f311d7d6`.
- All source-export hashes were rechecked after reading. Six relevant current
  runtime owners match the frozen B checkout byte for byte. No opaque reasoning
  was decoded, and no private evaluator material was needed.

The audit reconstructs the latest public state using the recorded segmented
format and inventories native/archived exchanges separately. It compares exact
stdout with both exchanges and the `recent_probes` fallback. Counting only
exchanges would incorrectly imply that a lost full record also lost its output.

## What was actually delivered

| Item | Observed delivery | Practical limit |
| --- | --- | --- |
| Public issue, including reproduction steps and expected outcome | Same complete task object in 358/358 requests; one task hash across both arms | Prose is not a checked mapping from the issue to an executed experiment |
| System instruction that suite PASS or another path cannot establish the original behavior | 358/358 requests | It remains an instruction requiring model judgment |
| New B reproduction review | 202/202 B requests | Every review has no bound reproduction and no case items |
| B1/B5 original verification concerns | Both remain `unresolved` in the last input | Submission eligibility does not require resolving them |
| Recent probe output | Latest three probes, with stdout/stderr tails up to 2,000 characters when full results are absent | Complete authored programs and all setup details are not guaranteed by this fallback |
| Exact expected-versus-executed caller/input/setup comparison | Not instantiated by any B declaration | The ordinary probe path leaves this connection to prose and model interpretation |

The relevant owners are `model.py` (scope instructions), `runner.py` (recent probes
and completion guidance), `reproduction.py` (bound cases), and
`verification_observations.py` / `verification_concerns.py` (execution observations
and model-authored concern decisions).

## Full programs can disappear while failure output survives

For B2's original-caller baseline, probe 290, the entire 390-character stdout
including F0010 survives **all 19 subsequent requests**. Its complete program and
native result are absent in 12 of those requests.

- Input 299 has the full exchange.
- Inputs 318 through 397 lack that exchange, but retain the exact stdout in
  `recent_probes`.
- Inputs 415 through 484 restore the complete exchange, including immediately
  before edit 491.
- Inputs 501 through 563 again retain the exact stdout through `recent_probes`.
- Post-edit replay 523's full exchange survives all three later requests, 532,
  548 and 563, with the same original error.

This qualifies the earlier report's “Original F0010 probe body” loss: that was
loss of the full exchange/program, **not loss of the F0010 output from the entire
model input**. It does not change a sealed annotation or grade.

B4's altered-environment Pylint program is absent in 20 of its 21 subsequent
requests, but its entire stdout remains in all 21. B1's stdout remains in all
three subsequent requests, and B5's helper program, result and explicit
`helper_or_unbound_diagnostic` label are present immediately before submission.
These findings establish availability, not attention or correct use.

## Preserved information did not produce a consistent verification state

**B1, final input 500:** the original missing-initializer concern is unresolved.
The helper's ImportError remains visible in recent probe feedback. The review says
there is no bound reproduction. The same input says `submission_ready=true`,
while its accompanying prose explicitly says this means eligibility, not
correctness. The model still submits and acknowledges not running the exact repro.

**B5, final input 291:** the original concern is unresolved, the review says no
bound reproduction, and the complete successful helper result is labelled
diagnostic only. The model still treats the helper result as sufficient for the
original task. Neither the scope warning nor the relevant result had disappeared.

**B2, after replay:** the public program uses `Run(..., do_exit=False)`, prints
F0010, and exits zero. The ordinary observation catalog tracks unsuccessful
executions, not arbitrary semantic failures inside stdout; it therefore has no
failure item for this experiment. `current_public_failure` is null and the new
reproduction review still has no bound case. Those fields do not claim a repair
PASS, but they also do not encode “the original failure persists.” That conclusion
is present in stdout and the model's prose.

At decision 550, B2 sends `operation=dismiss` with the reason that the concern
“remains unresolved” and that suite PASS does not close it. Final input 563 then
has `status=dismissed_by_model` and `unresolved_ids=[]`, while retaining that
contradictory reason. B6 does the same at decisions 381 and 423 with reasons
saying to keep concerns open. These are observed mismatches between model-authored
operations and reasons, not proof of verified resolution. Neither B2 nor B6
submitted, so they do not establish that this mismatch caused a false submission.

The host labels these decisions unverified and accepts a nonempty dismissal
reason; it does not interpret whether the reason contradicts the operation.
Consequently prose, concern status, execution status and submission eligibility
can present different views without a single concrete comparison resolving them.

## Interpretation and decision

The claim that this recurrence was simply caused by the original task or failure
message falling out of context is contradicted by the saved inputs. Complete
experimental setup can still be lost, but B2 had the full baseline at its edit
and B5 had the full helper at submission. Evidence use and scope interpretation
remain independent problems.

The implementation provides preservation and advisory distinctions. It has not
established reliable use of an original-task experiment or consistent semantic
tracking of its outcome. A plausible contributor is that concrete workflow
eligibility is computed automatically while the more important task-to-experiment
mapping remains optional and model-authored. This audit does not isolate that
effect from model capability, prompt complexity, or resource limits.

The next question should concern that mapping and the contradictory concern
operations, using these existing decision points before another paid run. More
source retention or another generic PASS warning is not justified by this evidence
alone. No new gate, mandatory probe, prompt or runtime change is adopted here.

Validation: the read-only audit completed; source hashes and frozen-owner equality
passed. Ruff passed for its script. Documentation checks cover this report's
current-document/index links: 5 passed. The first documentation check found the
current status/index over their byte limits; their entries were shortened and
the unchanged limits then passed. Full solver tests, mock smoke, new probe
execution and new paid comparisons are NOT_RUN because no runtime behavior changed.
