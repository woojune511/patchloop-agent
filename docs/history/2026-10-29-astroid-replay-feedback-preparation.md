# Astroid post-edit helper feedback comparison preparation

Status: local preparation; paid A/B execution is not authorized by this record.
Official=false, claim-ineligible. Material is the exposed dev-train current-dev20/13
task, public source and an ordinary saved agent checkpoint.

## Question and reason

The [two-task pilot](2026-10-29-dev20-followup-pilot-results.md) exposed a completion
gap: Astroid read its caller and observed a wrong file selection before editing,
then submitted after passing the public regression suite without replaying that
helper. The [public diagnosis](2026-10-29-astroid-pilot-path-diagnosis.md) confirmed
that the candidate did not change this behavior. Caller availability and optional
guidance did not establish repair correctness.

Test whether delivering the model's own helper output on the current candidate
changes its next decision and subsequent repair. Alternatives remain that the raw
output is insufficiently discriminating, or that the model receives the result but
still forms a wrong repair hypothesis. A success without a replay would weaken
the necessity of enforced observation. No automatic global replay policy or new
finish gate is being adopted; the earlier
[replay comparison](2026-10-03-probe-recheck-results.md) did not justify one.

## Frozen checkpoint and comparison

Parent `C:/pt/dev20-followup-pilot-run-v1/13`, run
`run_dev_aecd56b8decc47ff`, cut before `model_input_prepared` sequence 214.
Copy sequences 1–213 only. Sequence 218 is a later `turn_started`, not a valid cut.
The checkpoint is after one accepted edit and a passing public regression check,
before the next count, provider dispatch, finish and private evaluation.

- A: ordinary restored completion request and optional replay guidance.
- B: the same checkpoint plus one registered replay of the model-authored helper
  `call_vXtNNRJXLf9EtZbBGTEhdflt` on the current candidate. Collect this once during
  preparation, seal its raw receipt, and reuse it in the funded B continuation.
  Charge its actual active time and one tool action; do not execute it twice.
- Both use gpt-5.4-2026-03-05/xhigh, public-checks-v1, thin, segmented-v1,
  completion-recovery-v1, probe policy none, 60K input and 40K/25K output ceilings.
- Parent consumed 14 responses, 25 actions, one edit and USD1.102459. Remaining
  allowances are six responses, 15 actions, two edits and 2,049 seconds including
  390 seconds reserved for evaluation. B subtracts its one replay and elapsed time.
- Proposed fresh funding is USD3.397541 per arm, USD6.795082 total, one run each.
  This preserves the original effective USD4.50 ceiling; closed historical funds
  are not reopened and unused funds do not enlarge another arm's allowance.

The helper exits zero while printing its result. Do not convert this into a
host-declared task PASS or FAIL. Its current-diff provenance and raw output are
the intervention. Operator root-cause text, trace, separate CLI F0010 observation,
hidden tests, reference patches and evaluator logs remain excluded from repair
requests. Evaluation can occur only after finish and never feeds back to the model.

## Implementation and interpretation

The existing restoration primitive now preserves `verification_policy` when
parent configuration preservation is requested; previously it silently defaulted
public-checks-v1 to reproduction-gated-v1. Both experiment arms use the primitive's
identity projection, avoiding its unrelated observation-removal A mode.

`diagnostics/replay_feedback_checkpoint.py` binds replay reuse to the exact parent,
candidate and helper; ordinary journal batches charge the action and retain recovery
identity. `diagnostics/replay_feedback_comparison.py` audits actual next requests,
rehearses count/dispatch guards without a provider, and seals the live manifest.
Normalization excludes only elapsed-time fields and derived segment identity;
evidence, policies, tool/action/cost limits and dispatch equality remain checked.

Report result delivery, subsequent replay/exploration/edit choice, public checks,
submission, original SWE-bench acceptance, cost and active time separately. A
single selected A/B can support a local mechanism hypothesis, not a solve-rate
or generalization claim. Even B-only acceptance would warrant a broader controlled
test before adoption. Both failing would leave raw-evidence sufficiency and repair
reasoning unresolved. Stop all rows on count, transport, billing, execution or
cleanup uncertainty; zero SDK retries and no automatic resume.

Validation receipts and sealed execution command are added after preparation.
