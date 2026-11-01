# Ordinary caller reads and shared completion reservations

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: authorized implementation and local validation
- Origin Date: 2026-10-28, Asia/Seoul
- Verification Status: local validation with split recheck; no live model run
- Version Label: caller_completion_local_v1
- Scope: dev-head, official=false, claim-ineligible

## Problem and decision

The [caller/reservation investigation](2026-10-28-caller-budget-analysis.md)
found two concrete obstacles in the failed diagnosis-exploration continuation.
Prepared caller dependencies were available to probes but ordinary `run_dev` did
not register their direct read/search scope. Physical completion forecasts and
monetary/time forecasts also reserved different hypothetical recovery paths.
Reads could disappear before the model could investigate file selection or how
the caller consumed the returned AST, despite substantial unused global budget.

This matters because the latest three edits did not satisfy original verification:
two retained F0010, and the third returned an AST that its caller could not consume.
Source availability and a viable exploration choice are requirements, not proof
that another read would produce a correct repair. Misunderstanding the source,
choosing ineffective actions and exhausting mutation capacity remain plausible
independent limitations. The intervention preserves the original validation gate
and all invocation caps; it does not inject the known task solution.

## Implementation

`RunRequest` and `RunEnvelope` now accept explicit `caller_source_roots`. The
ordinary CLI exposes repeatable `--caller-source distribution=directory`, for
example `--caller-source pylint=pylint`. Registration requires enabled probes and
an existing prepared descriptor with an exact caller pin and indexed public Python
files under the selected root. A distribution name is not assumed to be its import
directory. Empty registration keeps the former serialized request shape and
repository-only scope.

The ordinary runner binds this registry to the gateway and its actual counted and
dispatched tool schemas. Existing `read_file` and `search_files` expose the selected
`dependency:<distribution>` scope. Read bodies reach the next model input in their
existing bounded dependency pool. They remain read-only and separate from editable
repository anchors. Roots and prepared identity are bound to recovery; changing
the mapping on resume is rejected. Registration neither imports caller code nor
adds a shell or mutation capability.

For ordinary `completion-recovery-v1` actions, shared path steps now account for
model responses, tool actions, output roles and nominal execution time. Required
completion includes current diagnosis and its unused request correction, any
missing mutation anchor, repair, original replays, fresh required checks and finish.
Automatic replay/check execution consumes actions and time without inventing a
model response. A rejected diagnostic request has no target execution. The
run-wide protocol correction remains separately reserved and cannot renew.

One possible later original failure and one possible public-check failure are
alternative paths, not concatenated stages. A later original failure can require
path diagnosis and its request correction. An automatic check's previous PASS is
not assumed to remain reusable after another edit. These routes preserve each
actual check/replay obligation while avoiding unrelated reservations.

Known-original-failure exploration can use required completion when speculative
future recovery does not fit. The action's compact route metadata reports which
guarantee was retained and why future recovery was released. Response slots, money
and time use the selected path; an older protected physical forecast cannot veto
that choice before path admission. If even required completion cannot fit, reads
remain unavailable. Releasing future recovery means a later failed candidate may
stop incomplete rather than receive another funded revision.

This shared-step calculation applies to ordinary recovery. Acquisition, first
observation, general probes that can add a case, observation/helper correction and
selected-test addition/comparison retain an explicitly labeled conservative adapter.
Other cost policies are
unchanged. No extra response, edit, tool, token, time or money allowance is created.
The nominal time allowance is not a worst-case bound on all setup or filesystem
latency. Admission is not a guarantee of useful model output or repair.

## Evidence and remaining question

Baseline commit: `0f9d0301`. Local evidence is recorded outside the repository at
`C:/pt/caller-completion-local-v1/`, using the hash-chained `dev-run-v1` journal
`run_dev_callercompletionlocal`. Exact commands, artifact hashes, failed attempts
and final results are recorded there. No provider, benchmark target, Docker image
or live isolated evaluator is authorized by this implementation request.

Caller registration and existing source controls passed 39 tests with three
platform-specific skips in 8.384 seconds. A malformed CLI pair exposed an ambiguous
parser in the first attempt; the final parser rejects the extra equals sign.
Budget owner controls passed 97 tests in 7.978 seconds (tool wall time). They cover
host actions without model calls, current checks without duplicate reservation,
missing anchors, future diagnosis/request correction, automatic-check credit,
special adapters and one-unit money/response/action/time boundaries. Initial
expectation changes and intermediate results are retained in the local report.

Pure replay of five saved public snapshots passed without changing their remaining
limits or reading recorded provider token counts as new admission evidence. At
sequences 155, 176 and 193, reads are newly available; 214 remains readable, and
241 remains restricted to diagnosis or stop at the required-completion floor.
At 176 the read uses the required route and releases speculative later recovery.
Original replay, current diagnosis/request correction and the separate protocol
reserve still fit. Special adapters are labeled and excluded from the independent
ordinary-step assertions. These are policy outcomes, not new model actions.

Quick ran once: 698 PASS and six FAIL in 214.86 seconds. Five failures were stale
contract-name expectations; one was the existing current-document byte limit.
After updating the intentional contract expectations and shortening current
guidance, the affected selection passed 35 tests with one remaining 26-byte doc
overrun; a final doc-only recheck passed all five tests. This is split validation,
not one clean quick invocation. Both isolated mock-evaluation smoke cases passed
in quick; mock safety remains NOT_RUN. Ruff and diff checks pass. The full quick
selection was not repeated because only contract assertions and documentation
changed after it. Focused mechanism validation stayed well below two minutes;
the broader quick integration selection took longer.

Reports: `C:/pt/caller-completion-local-v1/validation.json`
(`sha256:48fea7c9afe5b5eaa6b26f6b329db5d76d69243bfc68dc595946bfa500d0170b`)
and `completion-replay.json`
(`sha256:847ffe6ee35bdbf45a3c0937a47be292b5dec29c9ddf60f10e2252a9c425b332`).
Scripted provider input and isolated mock evaluation establish mechanisms only;
they do not show that a real model fixes F0010, performs a fresh solve, or improves
held-out accuracy. The next empirical question is whether explicit caller access
and the visible reservation tradeoff lead to a better repair within the same budget.
