# Current status

`dev-head` is the only active coding-agent runtime. It is mutable, development-only,
and always records `official=false`. The available commands are `patchloop dev`,
`patchloop doctor`, and `patchloop task validate`; legacy Rapid and provider-backed
claim commands are absent.

## Targets and limits

- focused local validation: under 2 minutes
- default one-row live limit: 1,800 seconds
- 40 model calls, 100 tool actions, and 4 accepted mutations
- one protocol/incomplete correction and at most 4 parallel reads
- `repeat=1` by default, 6 maximum, under one invocation-wide cost cap

## Authority

Mock execution carries no provider authority. One exact live `patchloop dev`
invocation authorizes only its declared `dev-train` task, model, credential file,
repeat count, and positive total cap. It never authorizes an image pull/build,
another task, an automatic retry after uncertainty, or a confirmatory claim run.

Repository policy alone never initiates paid work. The three live observations below
were separately authorized. None authorized an image pull/build, automatic
Docker startup, transport retry, or additional row.

## Evidence state

Ruff, the fast suite, and mock smoke pass. The current context-projection checkpoint
passed 29 tests in 16.45 seconds. The resume checkpoint passes 39 tests in 35.15
seconds. The provenance/safety checkpoint passes 54 tests in 50.43 seconds and
reaches mock `EVALUATOR_PASS` with task acceptance PASS and safety NOT_RUN. The
post-live mutation-encoding checkpoint passes Ruff and 56 tests in 50.92 seconds;
mock smoke reaches the same evaluator boundary through one accepted
`apply_git_diff` mutation. The first live row ran on 2026-09-02:
`loguru-invalid-format-feedback`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
one repetition, and a $1.20 invocation cap. Run `run_dev_e89e940c0715474e`
reached a durable `LIMIT_REACHED` terminal in 141.147 seconds after 39 model
calls and 99 successful read/search actions. It accepted no mutation, submitted
nothing, ran no evaluator, and recorded $0.07907685 of provider cost.

After the local reliability plan, a second separately approved row repeated the
same task, model, reasoning, repetition, and $1.20 cap. Run
`run_dev_9939bd27c5d04819` reached durable `LIMIT_REACHED` after 209.250 active
seconds, 40 model calls, and 92 tool actions, recording $0.25888155. All 39 prior
tool batches were present in the next context and 39 exact requests used the
evidence cache. Unlike the first row, the agent attempted mutation twice, on turns
36 and 39. Both attempts used `*** Begin Patch` wrappers and were rejected because
the runtime required a raw Git diff. It accepted no mutation, submitted nothing,
and ran no evaluator.

After the mutation wire contract was made explicit, a third separately approved
row again used the same task, model, reasoning, repetition, and $1.20 cap. Run
`run_dev_ef58e14b40834f0b` reached durable `LIMIT_REACHED` after 172.780 active
seconds, 40 model calls, and 94 tool actions, recording $0.24390525. On turn 3 the
agent called `apply_git_diff` with the required raw Git-diff prefix, so the renamed
provider tool contract was accepted. The first hunk declared 20 post-image lines
but contained 21, and fail-closed `git apply --check` rejected it at the following
hunk header with `corrupt patch at <stdin>:27`. That exact failure appeared in the
next canonical context. The remaining 37 turns returned to read/search only. No
mutation was accepted, nothing was submitted, and no evaluator ran.

The terminal arrived within 30 minutes, but the operational target still remains
unverified because there was no evaluator summary. See
[Evidence and limitations](evidence.md) for the exact observation and limits.

Historical executables are recoverable at checkpoint `b71ddeee`; immutable
historical artifacts and `docs/archive/` remain preserved. Current checkout
compatibility with those runners is intentionally unsupported.

## Next decision

The first live failure exposed a context-projection defect: successful reads were
selected by lexicographic span hash, so requested source could disappear from the
next stateless request and trigger repeated inspection. The second live row provides
bounded evidence that complete latest-batch projection and exact-request caching now
operate in a live loop. The third row then confirmed that the provider can select
`apply_git_diff` and emit its required raw-diff prefix, but it did not establish
submission reliability: the generated hunk counts were invalid. The exact tool
failure was visible on the next turn, yet it was not retained as an unresolved repair
obligation after later read/search cards displaced it.

The next seam is therefore failed-mutation recovery, not a stronger repeated-read
terminal. Exact-request caching already avoided 31 filesystem rescans in the third
row, while only three diagnostic stagnation cards fired and none blocked execution.
A subsequent change should keep a bounded failed-mutation error and repair target
visible until a corrected mutation succeeds or the run terminates. Repetition
detection remains soft evidence; varied searches should not be treated as proof that
the same mechanism is repeating.

Operational resume uses an immutable envelope, exact contract comparison,
run-lifetime locking, journal-derived counters and cost, durable tool-decision replay,
and mutation reconciliation. Pre-envelope runs remain immutable and non-resumable.
Runtime and task content are byte-bound; the manifest precedes evaluation; task
acceptance and safety remain separate typed axes. No fourth live row is authorized.

A confirmatory lane is not considered until three distinct tasks submit without a
harness/contract terminal and at least two privately pass. That threshold opens a
design review only; it does not support a quality or generalization claim.
