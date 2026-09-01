# R23 preparation and pre-execution status

Historical audit only. These snapshots preceded the approved R23 invocation on 2026-08-31.
They do not describe current authority and do not permit any build, rehearsal, retry or execution of consumed R23.
Current closure and exact result identities are owned by `docs/current-status.md` and `docs/09-evidence.md`.

## Pre-execution current-status snapshot

# Current status - 2026-08-31

## Current checkpoint

The agent remains a single bounded coding loop. Held-out R16 settled 48/48 for `$27.24465825`; C-minus-A was
`-1/24`, with no causal/general memory claim. Consumed Rapid runs and all historical artifacts are immutable.
Exact identities and preparation history are in `docs/09-evidence.md` and its named archives.

Work Item 70 consumed R20 exactly once: 6/6 settled for `$1.62950550`, both arms reach/submit/success 0/3/0.
Two V24 rows exposed a plan-feedback compatibility confound; cost is completion-censored, not efficiency.
Work Item 71 is complete offline: V25 fixed that compatibility seam with one durable admission retry.
Its zero-call qualification/review and the three-row R21 preparation remain immutable.

R21 then settled 3/3 for `$1.42525890`: no harness/admission failure, initial plan/first mutation in 2/3,
reach/submission/success 1/1/0. V25 failed the 2/3 evaluator-reach floor and is not promoted; R21 cannot retry.
Public diagnosis cannot attribute row 2's hidden failure.

Work Items 74/75 qualified and reviewed V26 `v27/phase-evidence-v36`: dedicated incomplete recovery, compact
feedback, anchored source reads and lifecycle plans. The frozen review records `eligible-not-adopted` as one
non-attributable product package. The separately source-qualified runner-continuity check remains unexecuted.

Work Item 76 adopted R22: V25 control/V26 treatment, three rows each, `$7.20` reserve/`$7.50` cap, unchanged
AnyIO-v5/model/image/no-memory/row budget/evaluator. Candidate-v30 execution is
`sha256:3930c68bdca28e28de1233a374e52f091d03d1dde95414d681c5be4c27c7f62b`.
Its six manifests and two identical no-call rehearsals/qualifications passed; the runner check stayed excluded.

Work Item 77 invoked that approved entry once, then stopped it before batch start: one wrapper image inspect plus
two per row would total 13, exceeding approval for one. No row/event/checkpoint/action/row-start record or result
bundle exists. All six rows are not started; provider/evaluator/visible-check calls and model cost are zero.
Outer Docker preflight/inspect counts are unknown, not zero (image inspect at most one before that boundary).
The approved plan and 3,795-byte stop audit remain unchanged. No R22 result or promotion exists; retry authority is closed.

Work Item 78 implements R23's requested offline image-admission successor. One exact reference/digest inspection
is recorded before dispatch, bound to six admitted manifests and reused only inside that batch. Missing, changed,
copied or foreign-batch authority cannot trigger fallback inspection. Restart cannot recover live authority from
the receipt. V25/V26 agent policies and AnyIO-v5 stay unchanged; exact reverse-delta audits recover the old runner/
contract bytes and all other reviewed policy/evidence bytes match. Candidate-v31 was superseded at zero calls after
mock SQLite cleanup failed; explicit mock-connection closure and GC-disabled cleanup now pass.
Final candidate-v32 execution is `sha256:d9d3818c9d2b80eb8238746c510fd071d808fb734bdc7f3d74837548c967d309`.
Two 15,966-byte rehearsals and two 21,492-byte qualifications are byte-identical; all six row image/provider gates and
actual-start mocks pass. No R23 execution, real Docker observation, provider/evaluator/check call or cost has occurred.

## Evaluator correctness gap

Evaluator-v1 still assigns literal safety PASS. V2 adds typed controls and receipts, but Rapid remains
`official=false`; neither synthetic completion nor one reused public task proves quality or generalization.

## Evidence, retry and authority

Evidence is append-only. Consumed development/Rapid/held-out runs cannot retry, resume, overwrite or transfer approval.
D-142 remains **source-qualified only, unactivated**; its planning disposition is now **deferred**.
No paid, held-out or B/D execution is currently authorized. R11-R21 approvals are consumed; R22's invocation is closed.
An R23 image-attempt marker is also one-use: unavailable identity or interruption requires a new candidate, not retry.

## Next gate

Await fresh exact candidate-v32 approval for six R23 rows, `$7.20` reserve/`$7.50` cap and one local-image identity
inspection. No paid plan, live image receipt or result bundle exists. Never reuse R22 or candidate-v31. PDM is retired;
Harbor remains 0/12 local images and pull authority is closed.

## Historical R23 preparation runbook


Use a short, fresh workspace basetemp: the longer `.pytest-wi78-workflow-regression-a` produced 260-character
artifact paths and three Windows file-open failures. The same three tests passed under `.p78w1`, and the full
workflow suite passed 213/213 under `.p78r2`; no agent/test expectation changed.

Final combined regression under `.p78f1`: 407/407 passed; scoped Ruff, formatting of 22 changed files and
`git diff --check` passed.

```powershell
uv run --offline --frozen pytest -o addopts= -q `
  tests/test_batch_image_authority.py tests/test_rapid_public_development_v26.py `
  tests/test_rapid_public_development_v26_qualification.py `
  tests/test_rapid_r22_prestart_stop.py tests/test_documentation_structure.py `
  --basetemp .p23f1
uv run --offline --frozen pytest -o addopts= -q `
  tests/test_workflow_causal_alternative_successor.py `
  tests/test_workflow_causal_plan_projection_successor.py `
  tests/test_workflow_semantic_progress_successor.py `
  tests/test_workflow_self_directed_exploration_successor.py `
  tests/test_workflow_self_directed_exploration_runner.py `
  tests/test_workflow_bounded_request_context_runner.py `
  tests/test_workflow_plan_contract_compatibility_runner.py `
  tests/test_lean_runtime.py tests/test_tool_gateway.py --basetemp .p23r1
uv run --offline --frozen pytest -o addopts= -q `
  tests/test_rapid_batch_driver.py tests/test_rapid_row_continuation.py `
  tests/test_rapid_terminal_state_parity_qualification.py tests/test_rapid_cli.py `
  tests/test_contracts.py tests/test_workflow_r21_reliability_successor.py `
  tests/test_workflow_r21_reliability_runner.py tests/test_anyio_runner_continuity_public_check.py `
  --basetemp .p23b1
```

The R23 mock enters six real `AgentRunner.start` paths and the unchanged settlement driver, with a fake low-level
Docker inspect response and synthetic row terminals. It checks exact command arguments and RepoDigest/config-ID
separation; provider, evaluator, visible checks, network and actual Docker are blocked. Missing, tampered, copied or
foreign-batch receipts, a same-digest foreign image reference, and crash before/after inspect are tested fail closed.
Synthetic completion proves neither agent performance nor local-image availability.

Preparation commands below are no-call only. Do not modify runtime source after creating the candidate; drift requires
a zero-call successor identity, not an overwrite. All builders validate an existing file rather than replacing it.

```powershell
uv run --offline --frozen python scripts/build_rapid_public_development_v32_candidate.py
uv run --offline --frozen python scripts/run_rapid_public_development_v32.py --mode rehearse
uv run --offline --frozen python scripts/run_rapid_public_development_v32.py --mode rehearse
uv run --offline --frozen python scripts/build_rapid_public_development_v26_qualification.py
uv run --offline --frozen python scripts/build_rapid_public_development_v26_qualification.py
```

The rehearsals cover all six shared image/provider gates with `image_identity_observed=false`; qualification separately
runs the actual-start mock twice. Exact identities and byte comparisons are in `docs/09-evidence.md`. Execution
requires fresh exact candidate-v32, six-row `$7.20` reserve/`$7.50` cap approval and the existing key through
`--env-file .env`; rehearsal never loads that file. The sole live inspection writes an exclusive, fsynced attempt
receipt first. An unavailable image, timeout or interruption closes that attempt; do not retry or remove the marker.

Candidate-v31 was superseded at zero calls after qualification mock SQLite cleanup failed; its candidate/receipts
and supersession audit remain immutable. V32 closes only isolated mock connections explicitly. A garbage-collection-
disabled cleanup test and the complete virtual-artifact qualification now run before candidate materialization.
