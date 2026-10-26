# Completion-feedback pilot: proposed fresh solve

Date: 2026-10-26. Status: PREPARED SCOPE; live execution requires a new exact
authorization receipt. official=false; claim-ineligible. All prior paid
allocations remain closed.

## Question and reason for selection

Does the [completion-feedback change](2026-10-26-completion-feedback.md) let the
model turn a captured target exception into a corrected repair, preserve enough
completion output to submit, and reuse already delivered inspection evidence?

The [closed revision pilot](2026-10-26-repair-revision-live.md) spent
USD 1.199996700 in 37 model calls, 39 actions and two accepted edits. Public
regression passed, but the original call raised FileNotFoundError and the model
never submitted. The [budget analysis](2026-10-26-revision-budget-analysis.md)
identified missing failure feedback, repeated inspection and low admitted final
output. These are correctness and completion bottlenecks, not proof that more
budget or any one intervention will produce a correct repair.

The intervention combines bounded selected-call failure feedback, a compact
finalization view with an 8,192-output funding floor, and an advisory connecting
complete first observations to delivered source and recent questions. It is one
descriptive fresh solve on an exposed task, not a causal A/B comparison. Prior
caller construction was stochastic; task, model and resource settings can remain
fixed without making fresh callers byte-identical.

## Implementation and prior local evidence

Implementation commit: `a885f8ea79f3511b62fb0bf219a66b62e6fd04b7`.
Runtime hash:
`sha256:3a7fd37953ffeee6074c53f93ebc315ebe4a77673c9dc40b1645480c9082a1f0`.
Tool surface v61. The immutable request binds the final committed preparation,
runtime, tool surface and source inventory.

At this same runtime hash, core validation passed 98 tests in 35.66 seconds;
Ruff and isolated mock evaluation passed. Quick validation had 415 passes and
one guide-size failure; that guide was shortened and focused docs/contracts
passed nine tests. This is split verification, not a second full clean quick run.
Receipts are in `C:/pt/completion-feedback-v1`.

Offline reprojection recovered the previous target exception while retaining
UNKNOWN whole-case comparison. Compact projection reduced serialized state
bytes, without measuring live input tokens, cost savings or repair gain. The
fixed failure gate would keep that candidate in repair. None of this is a live
Astroid repair result. Preparation reuses these receipts and checks only changed
documentation, frozen requests and existing environment identities.

## Exact proposed invocation

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; preparation checks
  existence and untracked status without reading or printing its contents.
- Repeat **1**, positive invocation-wide cap **USD 1.20**.
- Normal/correction output ceilings **40,000 / 25,000** tokens. Admission may
  reduce normal output. The existing 8,192 finalization floor is funded within
  the same cap; it does not guarantee a useful response or successful finish.
- 40 model calls, 100 actions, four accepted edits, 1,800 active seconds;
  1,920-second operator supervision. Input/context limits are unchanged.
- Segmented-v1, result-or-size-v1, brief-v1, probes/policy none, repair-recheck,
  protected-v1 inspection, bounded-v1 acquisition, completion-recovery-v1.
  The run_probe recommendation and separate first correction reserve remain.
- Same prepared source/dependencies, existing images and frozen public checks
  as the closed revision pilot. At most two post-submission public checks share
  120 seconds and require a settled submission. Isolated evaluation is separate.
- New runtime and fresh state are the intervention. Public task bytes, model,
  dependencies, caps and other request fields remain fixed. No old patch,
  caller, model reasoning or operator diagnosis is seeded into the solver.

The [official pricing table](https://developers.openai.com/api/docs/pricing),
checked on 2026-10-26, lists standard mini input/cached input/output at
USD 0.75 / 0.075 / 4.50 per million tokens. These match the registered runtime
rates. No provider-access or paid input-count request is part of preparation.

Preparation root: `C:/pt/completion-feedback-live-ready-v1`.
Execution root: `C:/pt/completion-feedback-live-v1`.
Workdir: `C:/Users/geonj/Documents/PatchLoop`.

```powershell
uv run --locked --offline python C:/pt/completion-feedback-live-ready-v1/supervisor.py
uv run --locked --offline python C:/pt/completion-feedback-live-ready-v1/assess_submission.py
```

The request includes the full CLI, script hashes and selected identities. The
supervisor requires a matching new authorization receipt, rechecks identities
before dispatch and never resumes or replaces a prior run. Image preflight
does not start containers or acquire images. Provider access remains untested.

## Measurements and decision rules

1. Acquire the unchanged-base original failure and F0010-free control. Record
   actual arguments, cwd, environment, fixture, captured output and issue
   fidelity. F0010-free does not imply no other diagnostics or exit zero.
2. When a qualified unexpected target exception occurs, check its capture,
   current-public-failure delivery, next public hypothesis and patch, diagnostic
   reuse and finish refusal. UNKNOWN stays UNKNOWN; a replacement exception
   must not count as an original-call pass or F0010 repair.
3. If ready_to_submit is reached, record compact-state delivery, fresh segmented
   entry/correction, actual input count and admitted output. Check that remaining
   funds cover the current action plus the applicable finalization successor.
   Distinguish reserved funds, billed usage, finish and no-action exhaustion.
4. After a complete first observation, record delivery of source/question
   references and subsequent inspections, new source coverage, questions and
   first-edit timing. Zero new covered lines alone does not prove an inspection
   was unnecessary. Model uptake requires evidence in public actions or patches.
5. Judge comparable current-diff original-call support and control preservation,
   public regression, submission, frozen public checks, independent acceptance
   and safety separately. A repaired public regression is insufficient by itself.
6. For any absent trigger, record NOT_EXERCISED; do not manufacture a failure or
   seed a patch to exercise a mechanism. First successful repair may legitimately
   skip exception-feedback and correction paths.
7. Record total cost, tokens, time, model/action/edit counts, output ceilings,
   correction/finalization admission, first unmet stage, call IDs and wire hashes.

Delivered evidence followed by another unchanged or wrong repair weakens the
behavioral benefit; continued no-action exhaustion despite funded compact
finalization weakens the completion hypothesis. If the relevant stages are not
reached, their benefit remains unresolved. A fresh caller mismatch, resource
exhaustion or absent trigger limits the conclusion. One exposed-task success
does not establish a general solve-rate gain, and unused budget authorizes no
second run. Report useful mechanical evidence and repair outcome independently.

## Boundaries

Count input immediately before dispatch; zero SDK retries. Count, transport,
billing, cleanup or frozen-source uncertainty stops work. No automatic retry,
resume, replacement, cap increase, Docker Desktop startup or image pull/build.
Public solver context excludes hidden checks, reference patches, evaluator output
and operator analysis. Generated state stays external and hash-chained. Historical
evidence bytes and the user's existing workspace changes remain untouched.
