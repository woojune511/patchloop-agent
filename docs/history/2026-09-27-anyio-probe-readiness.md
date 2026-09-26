# AnyIO probe readiness: missing dependency, waiting fixture

## Problem and hypothesis

The closed [planning regression](2026-09-27-planning-off-regression.md) had two AnyIO
probes time out before their first stdout. Both used TestRunner; public source showed
a lazy `_pytest.outcomes` import. The prepared probe bundle contained AnyIO's runtime
dependencies, not pytest. Successful registered checks used a separate environment.
Module discovery established absence, but had not reproduced the stalled control flow.

This follow-up used public source/programs and the existing Docker image, with zero
provider calls or private evaluations. It did not resume or amend the paid comparison.
Packet: `C:\pt\analyses\anyio-probe-readiness-20260927-v1`.

## Reproduction and causal evidence

The OFF run NB1's sequence-84 program ran before its edit. It was extracted byte-exact
from `NB1-public-timeline.json` and executed on an independent pristine prepared clone.
Its source hash is `sha256:1cc6b7b63492448220b68be10fd707375891a14b08ece0b9dcd53de3572984e4`.
All three probes retained source snapshot
`sha256:b17f7265ba1ecc580a9844deb06c2dfa291cf9775422af95957edba2c59996d3`.

| Execution | Result | Observation |
| --- | --- | --- |
| Original program, old bundle | timeout; 32.196 s including setup/cleanup | empty stdout/stderr |
| Instrumented program, old bundle | diagnostic stop; 6.102 s | runner task done with `ModuleNotFoundError: _pytest`; no fixture events |
| Original program, corrected bundle | completed; 21.077 s including setup/cleanup | setup, interrupt and teardown observations emitted |

The instrumented variant printed before `next(gen)` and scheduled a one-second
event-loop observer. It retrieved the completed background task's exception and stopped
the loop. The resulting `Event loop stopped before Future completed` exception is an
intentional diagnostic exit, not another task defect. The background task had failed
before consuming the queued fixture coroutine; the caller's future remained incomplete.

The corrected exact program showed `KeyboardInterrupt` leaving the runner task pending.
`post_interrupt` was absent immediately after the interrupt and appeared during fixture
teardown, followed by fixture cleanup. This establishes that the original question could
reveal the base-source defect. The original model did not receive these new observations.
Probe exit success means the diagnostic completed, not that the task was repaired.

Both executions requested the same 30-second probe limit within a 50-second operator
deadline. Copying the larger corrected bundle reduced its effective execution allowance
to 26.134 seconds; it still completed. This is not a perfectly equal-time comparison,
and a longer allowance did not enable the corrected result. Other execution controls
match apart from dependency/profile identities and this recorded deadline reduction.

The ON candidate's probe was not replayed. Its shared missing-import path is consistent
with this mechanism, but a byte-exact ON replay is not part of this evidence. No old
acceptance, safety or NOT_RUN outcome was relabeled.

## Correction

Selecting the full public `test` group failed resolution: its `blockbuster` dependency
requires `forbiddenfruit`, for which the resolver found no usable wheel. The failed
preparation has no descriptor and remains in `test-group/`. Source builds stay disabled.

The generic preparation CLI now accepts repeated `--select-dependency <package-name>`
with `--resolve` and explicit `--group`/`--extra`. It retains runtime requirements and
selected roots, then resolves their transitive dependencies. Unknown names, inapplicable
target declarations and requirement/URL strings fail before resolution. Selection is
recorded in public resolution provenance; omitted selection preserves existing behavior.
The original metadata hash still binds the full public declaration. See the
[preparation contract](../../.agent/prepared-probe-dependencies.md).

The new AnyIO preparation used `--resolve --group test --select-dependency pytest
--source-root src`. Its roots are `idna>=2.8`, `typing_extensions>=4.5`, `pytest>=8.4`.
The original idna 3.20 and typing_extensions 4.16.0 wheel identities stayed identical.
Added wheels: pytest 9.1.1, iniconfig 2.3.0, packaging 26.3, pluggy 1.6.0 and pygments 2.21.0.
No project build, image pull/build, task-source change or private dependency source was used.

New descriptor: `selected-pytest/prepared-probe-dependencies.json` in the packet.
Descriptor hash: `sha256:ae8d0a01dd8c67305ea620a885a75c73344979104f6d067e83dc3aebc79f143e`.
Content hash: `sha256:773bff706bc48be3f9a47b9943ceaa611004d4dee3a3bc44f3232b0225a78063`.
Changed runtime hash: `sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.
Only preparation code changed; the execution wrapper, model tools/prompts and policies
did not. Existing source/dependency descriptors and closed experiment files remain intact.

One operator launcher used unsupported `python -m patchloop`; it exited before preparation
created its output. That receipt is preserved in `selected-preparation.json`; the actual
console entry point's completed preparation is `selected-preparation-cli.json`.

## Validation and limits

Focused dependency tests, including both append-v1 and segmented-v1 mock paths, passed:
33 tests in 59.97 seconds. Both mocks used a selected bundle, mutated, ran a public check,
submitted and reached isolated evaluation; actual model inputs retained public task,
diff and check state. Unknown/invalid selections, default selection, source binding,
offline reuse and preparation failure publication are covered. Ruff passed.

Related dependency, generated-file, environment and provenance regressions passed:
97 tests in 196.75 seconds. Documentation checks passed: five tests. Together with the
focused group these cover 135 distinct tests; the earlier 31-test subset is not added
again. Full regression was not rerun for this preparation-only change.

The three Docker diagnostics used the ordinary network-none, read-only sandbox and
confirmed owned-container cleanup. They exercised the public AnyIO base entry point,
not a hidden correctness test. Final related checks and integrity receipts are recorded
in the packet's `validation.json` and `closure.json`.

The operator request log's auxiliary `dependencies_hash` is null for the larger new
descriptor because it used the source-manifest size cap. The authoritative probe
profile/receipt contains its correct dependency manifest hash, verified against the
descriptor bytes at closure. This is an operator logging limitation, not an unbound
runtime dependency admission; the original journal is retained.

No fresh paid agent run, acceptance comparison, full-suite rerun or general efficacy
claim was made. Earlier whole-suite results do not validate this changed runtime.
The next useful performance observation is whether a fresh agent can select and use
this available lifecycle evidence to revise an incorrect candidate while preserving
ordinary cancellation. No new prompt template is implied by this environment failure.
