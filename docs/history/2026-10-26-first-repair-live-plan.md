# First-repair observation live pilot: prepared, not executed

Status: PREPARED_LOCAL_ONLY; exact new paid authorization pending. Updated 2026-10-26.
This is a new allocation proposal. All earlier allocations remain closed.

## Question and reason

The [last pilot](2026-10-26-diagnosis-stage-live.md) acquired the original F0010 but
made zero edits. Its ordinary and correction responses ended without a tool call.
The [local intervention](2026-10-26-first-repair.md) adds an optional original-call
premise observation and reduces the first-edit request/context burden.

Can the real model use that observation, make a first repair, and remove F0010 on
the same original call while preserving the healthy control? Local mechanisms do
not answer this. This one fresh solve is descriptive, on an exposed dev-train task;
it cannot isolate the bundled changes or establish general accuracy.

## Proposed frozen scope

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; credential path
  `C:/Users/geonj/Documents/PatchLoop/.env` (contents not inspected during preparation).
- One invocation, repeat 1, cap $1.20; normal output ceiling 40,000 and the existing
  one protocol-correction allowance capped at 25,000.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 active seconds;
  operator supervision bound 1,920 seconds. Input/context bounds unchanged.
- Segmented-v1, result-or-size-v1, brief-v1, probes enabled/policy none,
  repair-recheck, protected-v1 inspection, bounded-v1 reproduction,
  completion-recovery-v1. The run_probe recommendation remains enabled.
- Same prepared source/dependencies, local image digests and two frozen public
  post-submission checks (shared 120 seconds; skipped without a submitted patch).
- Implementation commit `d66234dab2313e5a291234e5445211b0aadd4616`;
  runtime hash `sha256:9c46be3bc3adcc184d3c50a997bbef3aec2687661e00f266ad49649315bf8833`.
  The final request binds the preparation commit and current source inventory.
- Probe profile changes from `9f434d6ac677be33536e49ad2c42afbeba0d8e1b3742204c13ca7263b392e6d7`
  to `11e37dec91e131dae590e7656f2cca44c576798254d37a3a3b70b76d796d2e37` (SHA-256).
  Substituting only the previous call-path wrapper hash reconstructs the old
  profile exactly. Image, isolation and resource settings are unchanged.

Preparation root: `C:/pt/first-repair-live-ready-v1`.
Proposed execution root: `C:/pt/first-repair-live-v1`.
The immutable `request.json`, `command.ps1`, `source-inventory.json`, scripts and
hash-chained preparation journal define the reviewed scope. An authorization
receipt must bind the new request hash before the supervisor dispatches anything.

```powershell
uv run --locked --offline python C:/pt/first-repair-live-ready-v1/supervisor.py
uv run --locked --offline python C:/pt/first-repair-live-ready-v1/assess_submission.py
```

## Measurements and decision

1. Acquire the unchanged-base original failure and a distinct clean control;
   check captured output against the host judgment.
2. Separate observation availability, selection, host construction, rejection,
   dispatch, return, complete collection and delivery to the next model call.
3. Bind frozen caller/control/source/conditions. Report premise predictions as
   matched, contradicted or insufficient. Incomplete collection is not no-entry.
4. Record the first accepted edit and its receipt link. Review its explicit
   hypothesis and source change for use of the observation; a link alone is not
   semantic uptake. Direct supported editing remains allowed.
5. Verify F0010 removal and control preservation on the current diff. Keep
   visible checks, submission, frozen public checks, isolated acceptance and
   safety separate from the observation and from each other.
6. Record actual tokens, cost, actions, time, correction reason and first unmet
   stage. No observation, incomplete evidence, no edit and ineffective edits
   remain valid outcomes. Do not force or seed a mutation to exercise the feature.

The experiment may weaken the proposed explanation if complete useful evidence
arrives but editing still stalls, or if a first repair still fails the original
call. Not reaching observation does not test trace usefulness. A success is one
development example, not a causal estimate or generalization result. Diagnose the
first unmet stage before proposing another intervention; no automatic next run.

## Readiness and boundaries

Read-only preflight verified tracked/clean runtime and task, current runtime hash,
prepared source/dependency identities, Docker availability and existing images,
credential-file existence/untracked status and frozen public-check bytes. No
provider/count calls, containers or image acquisition were needed. Provider access
itself is not tested by this preflight. Final request generation also stubs the
runner to check CLI/request equivalence and checks the collection scripts locally.

Existing validation is reused: final focused/resource controls 154 PASS in 18.68 s,
Ruff PASS; the earlier quick run and its targeted expectation fixes are recorded
separately in the implementation record. No redundant runtime suite rerun.

Count input immediately before dispatch; zero SDK retries. Count, transport,
billing, cleanup or source uncertainty stops execution. No retry, resume,
replacement, limit increase, Docker Desktop launch, evaluator pull/build or
feedback from private evaluation to the solver. State stays outside the repository;
historical bytes and the user's existing AGENTS.md/temp changes are preserved.
All runs remain official=false and claim-ineligible. Live uptake, F0010 repair,
submission, acceptance and safety are NOT_RUN at this preparation stage.
