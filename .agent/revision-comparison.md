# Paired agent revision comparison

Preparation only. No provider execution is authorized by this note. The final
external manifest and an exact human spending approval own the live scope.

## Question and selection

Does the accumulated current agent change task acceptance, regressions, settled
cost, or completion time compared with the corrected-dev20 runtime, when tasks,
model, tools and resource allocations are held fixed? This compares a bundle of
changes; it cannot attribute a difference to one feature.

The original low-diagnosis shortlist (1, 3, 9, 15) consisted entirely of previous
successes; task 9 also had recent thin-policy runs. To retain room to observe repair
gains, preparation instead assumes two previous successes and two failures:

| Index | Registered dev-train task | Previous / corrected dev20 |
| --- | --- | --- |
| 1 | Marshmallow-1343 | PASS / PASS |
| 3 | Pvlib-1154 | PASS / PASS |
| 13 | Astroid-1333 | FAIL / FAIL |
| 16 | SQLFluff-1517 | FAIL / FAIL |

All four are development-exposed. Tasks 13 and 16 were briefly diagnosed in the
October 6 trace comparison; they are not unseen tasks. Repeatedly investigated
SQLFluff-1733 is excluded. The roster preference question was unanswered during
preparation; this selection is a disclosed assumption, reviewable before approval.
No task registration, held-out tuning, or task-specific prompt is added.

## Fixed comparison

- A: corrected-dev20 commit `e3aa70804005f110c9f6ed32b0ba792958a56aa3`, runtime
  `sha256:db912ef87f74330ace6285939ecdc124a83e14b1a401022fcb5dfe0c9102ca21`.
- B: current runtime at anchor `b4a24c254eefdde7ba6aa8666f49099e9bd2ab49`,
  `sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.
  The frozen manifest records the final checkout commit, including preparation
  documentation changes; the agent runtime must retain this hash.
- Both: `gpt-5.4-mini-2026-03-17`, xhigh, desired 25,000 output tokens; exact
  credential file `C:/Users/geonj/Documents/PatchLoop/.env`.
- Both: segmented-v1, result-or-size-v1, brief-v1, ordinary probes enabled,
  probe-policy none, probe-recheck none, repair-recheck true, protected-v1,
  per-call-v1. Newer request-only fields are omitted so equivalent defaults apply
  in both versions: current agent policy and 24,000 retained source characters.
- Each fresh solve: 40 model calls, 100 actions, four accepted edits, 1,800 seconds,
  including 330 seconds reserved for evaluation. No seed patch, previous context,
  continuation, or shared working notes.
- Four tasks times two versions times two repetitions: 16 rows. Each row reserves
  USD 1.20; total invocation cap USD 19.20. No transfers or automatic extra runs.
- Four sequential waves: A1, B1, B2, A2. Within each wave, the four tasks run in
  fixed index order with two worker processes. Each wave gets a fresh interpreter
  rooted at its own checkout. Repetitions are stochastic samples, not fixed seeds.

Both arms use the same public/task package bytes, prepared source and dependency
descriptors, existing pinned images, host and locked Python dependencies. The old
checkout's historical text normalization must be reconciled to the original task
bytes while remaining Git-clean; no source or admission bypass is permitted.
Opaque package hashing may bind private assets but never projects their contents
into solver context. Native assessment runs separately after submission.

## Execution and evidence

Preparation root: `C:/pt/revcmp01`; intended live root: `C:/pt/revlive01`.
The external launcher reuses each checkout's existing parallel scheduler and
registered/native assessment. It freezes its own bytes and checks checkout,
runtime, task, environment, descriptor, native harness and request identities.
Provider-free preflight and synthetic stop/accounting tests precede approval.
Both revisions must pass a mock smoke through isolated evaluation; mock safety
remains NOT_RUN. No image is pulled/built and no Docker daemon is started.

Every row has a fresh independent state root. A process-shared admission lock
stops new counts and dispatches on count, transport, billing or cleanup uncertainty.
Already admitted operations settle with retained usage. A stopped or incomplete
wave prevents later waves. The existing scheduler's verified task-local resource
limits remain local; they do not become successful evaluations. No restart,
replacement, retry, resume, or reuse of a closed allocation is allowed.

Report all 16 intended rows with submission, required public checks, registered
acceptance, native acceptance/agreement, safety, infrastructure, cost and elapsed
time separately. An unsubmitted or unevaluated row retains NOT_RUN, never PASS.
Public PASS alone is not task correctness. Historical outcomes explain selection
only and are not substituted for fresh A measurements.

## Decision rules

The primary result is each task's A/B acceptance count out of two, plus total
acceptance out of eight per version. Positive evidence within this panel requires
complete, agreeing assessment of every submitted candidate, settled accounting,
more B acceptances, and no task with fewer B acceptances. A gain with a regression
is a tradeoff to inspect, not an unqualified improvement. Equal acceptance provides
no repair-quality gain; cost and time can still differ. An interrupted panel stays
incomplete; show paired available rows without treating omissions as evaluations.

After execution, inspect public traces for the behavior underlying wins/losses;
do not tune prompts or rerun exposed cases during this allocation. Four selected
tasks and two repetitions do not establish general accuracy or statistical
significance. All runs are official=false and claim-ineligible. There is no
automatic adoption, rollback, larger panel or follow-up spending.
