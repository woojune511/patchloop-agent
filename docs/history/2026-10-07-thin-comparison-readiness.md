# Current/thin comparison execution readiness

Date: 2026-10-07. Implementation commit: `6440dcfa`.
Runtime content remains
`sha256:3381660b5484eb474efe897157c711b32a8c26f54cbba05ab90ac1c9ec226522`.
This follows the [frozen design and A2 replay](2026-10-07-thin-comparison-preparation.md).
The user authorized completing the execution adapter and provider-free environment
preflight. No paid solve or private SWE-bench evaluation was authorized or performed.

## Problem and implementation

The proposed sixteen-row comparison could not use the generic batch entrypoint
directly: that entrypoint correctly requires distinct task paths within one batch,
while this comparison repeats each task. Existing wave code hardcoded another
comparison, and native prediction metadata hardcoded the mini model.

[thin_comparison.py](../../diagnostics/thin_comparison.py) now prepares, freezes and
executes the exact design through the existing solver and evaluator paths. It uses
four distinct-task waves, at most two workers, separate row roots and assessment
directories, and one USD 64 allocation split into sixteen nontransferable USD 4
caps. Current/brief-v1 and thin/none each solve four tasks twice using the same
full-model baseline. Model, resource, policy, rubric and scheduling choices remain
the prepared design; no quality intervention was added during readiness work.

Before each fresh row and assessment, and at wave boundaries, the driver checks
the frozen code/HEAD, model/tool, task/source/dependency/image and native evaluator
identities. A drift or uncertainty stops new admissions. Calls already admitted
settle; a wave-boundary identity stop preserves completed rows and recorded cost
in a CLOSED result. Settled task-local limits retain their existing separate
classification. The execution lock and fresh roots reject restart or resume.

Native assessment now writes `req.model` in prediction metadata, preserving exact
patch bytes, credential isolation, additive-test projection and grading semantics.
Post-submission public grading binds the frozen program, profile and unchanged
submitted patch. Unsubmitted/native-unavailable rows retain public NOT_RUN; public
output never returns to the solver. The four classifiers retain their calibrated
behavior criteria while rejecting explicit setup failure and uncertain cleanup.

The [operational contract](../../.agent/thin-comparison.md) separates preparation,
manifest freeze, human scope approval and execution. Preparation reads no credential
contents and uses existing images. Freeze binds the final committed HEAD and
immutable evidence. Execution requires the exact manifest hash, model, credential
path, sixteen fresh rows/two repetitions and positive USD 64 cap. No earlier paid
allocation is reused.

## Local validation

| Check | Result | Evidence |
| --- | --- | --- |
| New comparison/classifier tests | 89 PASS, 6.31s | `C:/pt/thtest-receipt01/junit.xml`, `pytest.log` |
| Existing native assessment tests, including full/mini metadata | 26 PASS | Captured tool output, `tests/test_portfolio_dev20.py` |
| Related batch, capability, assessment and preservation tests | 74 PASS, 16.398s | `C:/pt/thcheck01/related.xml` |
| Documentation layout/links | 5 PASS on final documents | `C:/pt/thcheck01/docs-final.xml` |
| Ruff and diff whitespace | PASS | Runtime, tests and changed diagnostics |
| Saved public classifier parity | All eight base/positive observations agree | `C:/pt/thcheck01/saved-calibration.json` |

The new tests use self-contained fixtures, including the real two-worker process
pool across sixteen synthetic rows. They cover permanent stops, settled peer calls,
task-local limits, cap violations, missing authorization/preflight, manifest and
row identity drift, assessment admission, scoped public failures and uncertainty.
No fixture depends on the local historical evidence directories. An initial native
test edit omitted its JSON import; it was corrected before the reported pass.

Both actual CLI mock smokes reached isolated task acceptance PASS, each with four
mock model calls, five actions and one accepted edit. Current run:
`run_dev_58f18e4ddbcc485c`; thin run: `run_dev_83cfe0a520a04867`. State roots are
`C:/pt/thcheck01/smoke-current` and `smoke-thin`; sibling `.json` files preserve
CLI results. Safety remains NOT_RUN, cost zero. Initial CLI syntax attempts exited
before execution; the successful calls used the configured state-root environment.

The validation packet is `C:/pt/thcheck01/validation.json`, file hash
`sha256:3e3a786a7424962d9f97a095ed8f859375e6f6becaffef6304667cde587ef542`.
It binds implementation, runtime and recorded evidence. The full CI suite was not
rerun: this change is confined to diagnostic orchestration and metadata, and the
agent runtime is byte-identical. Relevant suites and both CLI smokes ran instead.
The final documentation check followed that validation packet separately.

## Current environment evidence

Preparation completed in `C:/pt/thready01` in 265.387 seconds between its start
and successful preflight journal events. It used twelve public probes (import,
operation and bug program for each task) and four public selected-test checks.
No OpenAI calls, private SWE-bench evaluation, image pulls/builds or credential
reads occurred. Docker was already running; all images were already installed.

| Task | Import / operation / selected test | Frozen public bug on base |
| --- | --- | --- |
| SQLFluff-1733 | PASS / PASS / PASS | Scoped FAIL, expected bug reproduced |
| SQLFluff-2419 | PASS / PASS / PASS | Scoped FAIL, expected bug reproduced |
| pvlib-1072 | PASS / PASS / PASS | Scoped FAIL, expected bug reproduced |
| pydicom-1694 | PASS / PASS / PASS | Scoped FAIL, expected bug reproduced |

All checks exited normally without timeout, truncation, deadline or cleanup
failure. SQLFluff's plain SELECT/COALESCE and pvlib's naive controls were preserved.
Pydicom preserved the suppression-off ValueError; its failing suppression-on base
does not reach the valid-field preservation observation. Do not report every
pydicom behavior control as passing. The older positive observations remain
separate calibration evidence.

`preparation.json` file hash:
`sha256:7ebb6d1dc04bc24524d9abe03d7c36190ee517f369c1e57d4cec2d618db7538a`;
canonical hash:
`sha256:9f779b3b04648e5e37ed610f14acb0a71bc261ecd8bc0b56f4d358cd0c498666`.
`preflight.json` file hash:
`sha256:a5644d201b492a8a6eff20b4c28672b2aa4efdc83e1451abdaf2a26fcab5af98`.
The case receipts bind exact task, source, dependency, probe/evaluator image and
native harness identities; public program/profile and unchanged source hashes
were checked. Final manifest freeze follows this documentation commit, so its
exact HEAD and returned hash are recorded in `C:/pt/thready01/manifest.json` and
the append-only preparation journal. `C:/pt/thlive01` remains absent.

Independent read-only audit passed 179 JSON/hash checks, including both journal
chains (ten comparison events and twelve canary events), all sixteen requests,
twelve implementation-file bindings and 82 runtime-file bindings. No probes or
tests were rerun by the auditor. It found no material error in these receipts.

## Decision boundary

This work establishes execution readiness only. It produces no new repair success
rate and no evidence that thin improves quality. Current remains the default.
The adapter and current environment preflight are ready. After final manifest
freeze, the remaining gate is exact human funding authorization under AGENTS.md
gate 5. The design's USD 64 proposal alone is not authorization. No paid allocation
has been opened and no next panel is automatic.
