# MontePy repair preparation: blocked before live execution

Prepared 2026-09-30 on runtime `5c788f653760fed833f017b3f8d1ddec358dd41d`.
This is an operator preparation record and proposed scope, not live authorization.

## Purpose and proposed scope

Exercise the unchanged coding agent on `original-montepy-933`, version 1,
dev-train, base `fbc03d10eb552cf82acc788ef70d120adec8130c`.
The public requirement is to permit setting/deleting `Cell.universe` to clear it
outside a problem, or reset it to universe zero inside a problem. Allowed changes
are `montepy/**`, at most four files/1,000 diff lines, no test or dependency changes.
The task was exposed in the original pilot; a new invocation is not an unseen-task
evaluation or evidence of general improvement. Prior solutions/traces and private
evaluation material must not enter the coding agent's input.

Proposed, currently blocked settings:

- Model `gpt-5.4-2026-03-05`, xhigh, desired output 25,000 tokens.
- Credential file `C:\Users\geonj\Documents\PatchLoop\.env`; existence and Git
  ignore status verified, contents not read during preparation.
- Exactly one fresh invocation, USD 3.00 invocation-wide cap; 40 model calls,
  100 actions, four accepted edits, 1,800 seconds.
- segmented-v1, result-or-size-v1, brief-v1, optional probes with policy none,
  repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Zero SDK retries; stop on count, transport, billing or cleanup uncertainty.
  No automatic repeat, resume, additional funding, image acquisition or policy change.
- Fresh external state root `C:\pt\runs\montepy-next-repair-20260930-v1`.

## Prepared inputs and provider-free evidence

Source descriptor:
`C:\pt\preparations\montepy-next-repair-20260930-v1\prepared-source.json`
with descriptor hash
`sha256:e630635a0cc4676ac36bcf9fdff6d436fcc9809be95fafac01be7ae61a162974`.
Source content hash:
`sha256:d6c13810f2ddcec40d6545a2fbd16ae15da3b099b126a0ee91949d54a5b4b89f`.

Probe descriptor:
`C:\pt\preparations\montepy-next-probes-20260930-v1\prepared-probe-dependencies.json`
with descriptor hash
`sha256:889c338ece550faf87640ed3e1ac44f10206122987ca433bf4cd9d6f4f55d229`.
Resolved only declared runtime dependencies with source root `montepy`; no build hook.

Doctor and task validation passed. Existing images were available:
evaluator `sha256:d79f83f33b0f25749596dd0038adecb80e9b443300200890dca0f6d23488567c`,
probe `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Docker was already running; no start, pull or build was performed.
The normal isolated probe imported MontePy, Cell and Universe successfully.

Evidence root: `C:\pt\analyses\montepy-preparation-20260930-v1`.
Hash-chained journal: `run_dev_montepypreparation`, four events.
Receipts are immutable, content-addressed artifacts referenced by that journal.
The independent workspace remained unchanged. Model calls: zero;
acceptance and safety: NOT_RUN; official=false.

## Observed blocker and next question

The registered public check executed on the unchanged base, collected 44 cases,
and returned exit 1. Its failure section names `TestFill.test_fill_index_setter`:
Hypothesis generated indices `[0, 0, 0]` and width `[1, 1, 9223372036854775808]`;
the fill setter rejected float `1.0`. The saved output is truncated, so do not
claim a complete 43-pass/one-failure summary. Cleanup succeeded.

Public test source uses unbounded integer strategies and computes
`np.array(indices) + np.array(width)` before assigning `fill.max_index`.
Integer-range/dtype promotion is a plausible explanation; dependency-version
behavior or an existing Fill implementation defect are unresolved alternatives.
This failure is not evidence against an agent repair: no agent ran and no patch
was made. Its relationship to the requested universe-nullification repair is unproven.

The [deterministic follow-up](../docs/history/2026-09-30-montepy-index-diagnostic.md)
completed in the existing check environment. NumPy 2.4.5 constructs the exact
width list as float64 before addition; Python integer lists and explicit object
arrays preserve those same values and the original setter accepts them. Six fixed
cases establish this test-input conversion mechanism, not a cross-version regression.

Do not launch the paid proposal yet. The next step is a separately reviewed
development-task revision preserving integer arithmetic in the public property
test, with deterministic boundary controls and original-package preservation.
No such revision was implemented during this diagnostic.
Do not remove the test, constrain random generation, pin another dependency,
rerun until green, or expand the agent's repair scope during preparation.
Revalidate clean tracked runtime/task inputs and descriptor/image identities before
any subsequently authorized live invocation. No second task or paid allocation is opened.
