# Required public check repair result

## Material Passport

- Date: 2026-10-28. Executed once; official=false, claim_eligible=false.
- Scope: assisted continuation of Astroid-1333, dev-train current-dev20/13.
- Runtime implementation `aaf598c1`; preparation `f73ba6c9`, `0eb1c972`;
  execution checkout `e2a6ff76`.
- Outcome: two new edits, required public 11/11 PASS, isolated task acceptance
  PASS and safety PASS. Allocation CLOSED; no automatic repeat.

## Why this question mattered

The [preceding continuation](2026-10-28-probe-revision-repair-results.md) received
three public regressions and submitted the unchanged candidate while an affordable
repair route remained. The failures were advisory evidence outside the required
check registry. Merely retaining more budget had not made the agent repair them.

The [change](2026-10-28-required-public-checks.md) registers those explicit public
counterexamples as completion obligations with current-diff checks, automatic
post-edit feedback and resource reservations. The [sealed plan](2026-10-28-required-public-check-repair-plan.md)
asks whether the live model revises and passes them, beyond merely blocking finish.
An unresolved stop, failed patch, missing feedback or isolated rejection would not
establish successful repair. The original F0010 case already passed at this saved
checkpoint; this is not a fresh discovery or first repair of F0010.

## Authorized conditions

The user approved manifest
`sha256:0e64d7e62d5648e4904fd9640f026105236eb492002cf31b099e966a78e2eca1`
and `C:/pt/required-public-check-repair-plan-v3/run.ps1` for one execution with
`gpt-5.4-2026-03-05` (xhigh), repository `.env`, and a fresh USD3.38078870 cap.
It ran once, starting at 2026-10-28 12:08:38 UTC, and exited zero.

The source checkpoint, public packet and model stayed fixed. Remaining limits were
eight responses including at most one correction, fourteen ordinary actions, two
accepted edits, context60K, output40K/correction25K, solver1388.349 seconds and
isolated evaluation reserve390 seconds. The former separate post-finish replay
action/time moved into the ordinary required-check budget. No post-finish public
matrix execution occurred; reporting reused its completed receipt.

The first request offered edit/stop with the current source body. Optional
exploration was closed by the protected completion forecast, then reopened after
the first failed edit. This action-space change and check timing prevent treating
the trial as a prompt-only comparison. No private evaluation material, reference
patch or operator repair was supplied to the model.

## Observed repair and feedback

Sequences below refer to the branch journal under the result root.

| Stage | Public evidence | Next action |
| --- | --- | --- |
| First edit, 229 | `_get_relative_base_path` normalizes absolute/real search roots, checks directory boundaries with `commonpath`, and strips the matching normalized root. | Original replay 236 passes. Required matrix 242 still fails three cases. |
| Failure delivery, 245 and 260 | Matrix FAIL and its complete 1999-character output remain bound to the edited diff. Finish is unavailable. | One bounded test search, then a second edit. |
| Second edit, 271 | Both `_spec_from_modpath` call sites return to `spec.find_spec`, bypassing the added namespace fallback. | Original replay 278 passes; matrix 284 passes all 11. |
| Success delivery, 286 | The exact 1044-character matrix output reaches the next input. Base regression is NOT_RUN on this diff, so finish stays closed. | Model requests base regression. |
| Completion, 300-319 | Regression 296 passes; both required checks are current PASS and original cases verified. | Finish is offered, model submits at 311; isolated acceptance and safety PASS at 318, terminal EVALUATOR_PASS at 319. |

The remaining failures after the first edit were `namespace_leaf_explicit`,
`split_leaf_forward` and `split_leaf_reverse`. The second edit's stated hypothesis
was that the namespace fallback manufactured `PY_NAMESPACE` when the explicit path
already pointed inside the namespace directory and normal resolution should raise
`ImportError`. The patch bypasses that fallback and all three then pass. This
supports the local hypothesis within the public cases; no independent ablation
was run. The final patch retains unused fallback helper definitions from the saved
candidate. The submitted artifact was preserved without cleanup or operator edits.

## Results kept separate

- Both post-edit original replays match the frozen caller/input/environment
  conditions. Failure and regular-package control cases have `has_f0010=false`
  and `has_w0611=true`, retaining positive target-processing evidence.
- Required public preservation: **11/11 PASS**, including all three regressions.
  The excluded twelfth case, `namespace_root_empty`, already failed on the original
  baseline and remains FAIL; it is not silently counted as repaired.
- Public base regression: **1231 passed, 69 skipped, 15 xfailed**, one warning,
  reported test time8.83 seconds. These are public checks, not hidden test counts.
- Normal finish and patch delivery succeeded; isolated task acceptance **PASS**
  and safety **PASS** are recorded independently.
- Fresh model responses **5**, input counts **5**, accepted edits **2**; all
  responses completed. Fresh actions **9**: two edits, two automatic original
  probes, two matrix checks, one base regression, one search and one finish.
- Fresh settled cost **USD0.90023750**; unused **USD2.48055120** is closed.
  Including inherited accounting, cumulative cost is USD2.01944880.
- New active elapsed time **494.969 seconds**. Maximum input58167/output11715
  tokens; no protocol correction or output-limit exhaustion. No uncertain billing,
  retry, image pull/build or extra target execution was introduced by auditing.

The host status, exact output delivery and action/diff linkage were checked from
actual prepared requests and completed actions, not inferred from the model's
summary. Finish is absent from inputs218/245/260/286 and present at300 only after
all required current checks pass. The search after the first failure yielded no
new source coverage; its contribution to repair is not established.

## Decision and limits

Retain the required-public-check design. In this authorized continuation, the
model received a still-failing result, changed its candidate, passed the public
obligations and reached independent acceptance. This answers the immediate live
uptake question positively; it does not estimate a general repair improvement.

The raw collector's conservative `repair_efficacy=NOT_ESTABLISHED` aggregate is
unchanged. The observed single-candidate success is reported separately from
causal efficacy. Operator-selected public counterexamples and a saved candidate
make this an assisted repair. The issue-to-caller mapping remains model-authored;
frozen-case agreement alone is not complete task correctness. No held-out or
fresh-start gain is established. The next question is performance from the clean
original task without these operator-selected counterexamples under the same
overall budget. That experiment has not been prepared, funded or executed.

## Reproducible evidence

Result root: `C:/pt/required-public-check-repair-run-v1`.

- `result.json`:
  `sha256:db31a30c3f3b1f17c071d04124a861b4442457803d88be8a33510fcd7d9b1196`.
- `repair/runs/run_dev_3e21775752a54cae.jsonl`, 319 hash-chained events; new work
  follows checkpoint212:
  `sha256:0c096ffe61feaf507deb0fbdb920a9bd689344fda2bfca54aa17282f9cd440b4`.
- `public-outcome-audit.json`, read-only artifact audit, no extra model/target call:
  `sha256:b2b2d05170de4060381e6f0fc93ae3d926385956269fbee1cba1af0d020cc226`.
- `independent-outcome-review.json`, independent public-record review PASS:
  `sha256:78f44e89770f67b7c79db41eeec710a387a855bfa128131fc5ef5141ad28dbd9`.
- `submitted.patch`, exact finished artifact, only `astroid/modutils.py`:
  `sha256:9ea8ce64842b278d5fe53f81ef696ac6599930c5105d63789d94713a4dfe99dd`.
- Collector `runs/run_dev_counterexamplerepair.jsonl`: execution result23,
  allocation_closed24, public_outcome_audited25 and independent_outcome_reviewed26.
  Prior plan/results are immutable.

Preparation controls and runtime validation are recorded in the linked plan and
implementation records. This follow-up adds result documentation only; it does
not change runtime behavior or rerun model/target checks. All five focused
documentation checks passed in the result-recording turn.
