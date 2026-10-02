# Review-context experiment feasibility

## Result

Four usable evidence boundaries exist, but a fair runnable comparison is not yet
implemented. Wrote a [draft protocol](../../.agent/review-context-pilot.md) instead
of starting another paid experiment. The user authorized feasibility/design work;
no model call or new task repair occurred.

Validated four source journal chains, each final prepared request's content hash
and its context artifact hash. Each checkpoint precedes the final finish action
and follows a successful registered public check on the exact submitted diff.
All four expose read/search/probe/edit/finish tools and use the selected model.

| Case | Prepared sequence | Public PASS sequence(s) | Remaining original seconds |
| --- | ---: | --- | ---: |
| OpenSandbox | 131 | 111 | 1422.135 |
| Isort | 339 | 337, 338 (action and recheck records) | 281.669 |
| Pyinfra | 142 | 138 | 1330.421 |
| Conan | 140 | 136 | 1491.791 |

Selection is the last candidate before final submission, not the first public
PASS: Conan's earlier candidate was subsequently repaired. Cases are selected from
known outcomes, so findings would be development calibration, not success-rate
estimates. Conan and pyinfra are preservation controls under their stated checks;
pyinfra's original verdict is not relabeled.

## Prior-work overlap and causal limits

The existing candidate_review_repair seam seeds a patch into a fresh context,
optionally with external review. It explicitly inherits no previous check/plan
credit. It does not restore the original repair trajectory. The
[observation panel](2026-09-29-observation-repair-panel-design.md) already used fresh
contexts in both arms to vary delivered evidence. The prior-decision sampler
removed selected retained decisions from response-only contexts; draft review
compared next responses, not final executed patches. The
[guidance comparison](2026-10-01-verification-selection-comparison.md) varied
instructions and did not establish a repair benefit.

Those are relevant precedents, not proof that this exact reviewer/history contrast
has been tested. Novelty remains bounded to this inspected set of records.
Do not claim that fresh context or external advice is a new capability.

Existing checkpoint restoration retains exact histories and budgets, but its
post-edit preparation targets a first-edit/pre-check boundary with one historical
mutation. Isort, pyinfra and Conan have two edits. Reusing it unmodified does not
establish correct post-check restoration. Recursive CAS admission, Docker readiness
and restoration rehearsal were NOT_RUN in this inventory.

The initial two-arm suggestion confounds adding a review with removing history.
The draft uses ordinary continuation, trajectory-context review and fresh-context
review to separate those effects. Isort's remaining time motivates an explicitly
equal replenished continuation budget; it cannot be called an ordinary resume.
Shared cross-role cost/accounting and projected reviewer context still need
implementation and provider-free validation.

## Decision and evidence

The mechanism is plausible and testable, not demonstrated. Proceeding directly to
paid calls would be premature. The draft defines candidate tasks, twelve episodes,
proposed USD 24 aggregate cap, actual-patch outcomes, preservation controls and
stop conditions; all are design proposals, not paid authorization or frozen live
admission. A promising pilot would still not justify adoption from one repeat.

External root: C:/pt/analyses/review-checkpoint-feasibility-20261001-v1.
inventory.json binds source hashes, run IDs, prefixes, candidate hashes and timing.
Six-event hash-chained journal: runs/run_dev_reviewcheckpointinventory.jsonl.
Driver: C:/pt/review_checkpoint_inventory_20261001.py.
This is an operator inventory, never a solving-agent input packet. Source artifacts
remain unchanged; no private evaluator details were read. Documentation layout
and link checks plus whitespace checks passed. Runtime code is unchanged.
