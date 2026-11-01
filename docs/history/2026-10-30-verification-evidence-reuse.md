# Public verification selection and evidence reuse

Date: 2026-10-30 KST. Provider-free audit and local implementation follow-up.
Baseline: `626349363a5bb73fb244fc3be13b268782313319`.
Implementation runtime: `sha256:e8098f8b558a6bd8a5310e0cb07f70deacc3fe86c41fe3a7dab6bd00368d05d9`.

## Problem and diagnostic decision

The [shared-guidance run](2026-10-30-contract-guidance-3916-results.md) kept
PASS/PASS/FAIL on tasks 3/9/16 while cost and time increased. SQLFluff's five probes
all used adjacent doubled semicolons and a normal control. Public source review
found sibling failure paths and option boundaries unaddressed. This matters both
for repair correctness and repeated model/tool work; probe count is not coverage.

Before adding another tool or forcing more checks, distinguish unavailable source
from failure to use delivered source, and inspect whether already obtained results
remain available. Source omissions would support fixing retrieval. Complete source
delivery weakens that explanation; retained observations would weaken a context-loss
explanation for repetition. Neither source delivery nor output retention proves
model attention or correct semantic judgment.

## What was actually delivered

Public action/context/handoff records of task16, run
`run_dev_97454feee9bb4b5f`, establish:

| Action sequence | Public source delivered before first edit |
| --- | --- |
| 43 | `helpers.py` 1-84: input raw preservation check |
| 63 | `delimited.py` 1-251: complete grammar, sibling returns and option conditions |
| 64 | `dialect_ansi.py` 487-515: caller's Delimited configuration |
| 100 | `grammar_test.py` 560-676: existing trailing/gaps/minimum tests |

At turn106, source bodies were in the public context/latest result and their span
IDs/native action IDs were recorded. The first edit completed at sequence113.
After the edit, sequence201 read the entire updated grammar (1-255); turns260 and
276 retained it. Missing delivery of these branches/options does not explain this
case. The observed repair and cases did not use their full implications; the
model's internal reason for that choice remains unknown.

## A reproducible result-delivery defect

Sequence252 asserted input raw preservation, statement count and the expected
unparsable section. Turn260 delivered that successful observation. After the
selected test at sequence268, a fresh completion segment began at sequence275.
The turn276 canonical public context still contained that probe's bounded output
under `recent_probes`, but `completion_context.project()` omitted the whole field.
Only the latest test survived. The fresh segment contained no older native exchange.

Probe ID, question and exit status remained in `reproduction_review.other_executions`,
with coverage unassessed. Concrete successful output was absent; older failed
observations remained in verification notes. This is loss of observed details,
not complete loss of the probe's existence. Sequence286 then rechecked the same
input pair. The sequence supports fixing information loss, but does not prove
that the loss caused that model choice.

## Change

- Completion now retains existing current-diff, non-historical `recent_probes`
  summaries across intervening actions and fresh segments. The builder already
  limits this list to three and each stdout/stderr tail to 2,000 characters.
  Questions, outputs, failed/partial outcomes and `behavior_verdict=not_assessed`
  remain intact; native result bodies are delivered only once.
- Summary output now includes omitted-character counts and the existing timeout,
  deadline, cleanup and truncation flags. A retained tail is not presented as the
  complete execution output. Programs/full call traces are still omitted; the
  existing action-ID replay already resolves exact programs from the journal.
- Replaced the shared six-line instruction rather than appending a new layer:
  distinguish required outputs, preserved state and success/failure conditions;
  choose a refuting related path/option and a normal control; group cases; identify
  the still-untested condition in the next probe's existing question and reuse
  adequate same-diff observations and observed APIs. General, thin, repair and
  completion routes receive the same instruction. Main prompt is 7,950 characters
  versus 7,935 before. No SQLFluff-specific hint or new schema field is included.

Tools, quotas, admission, submission eligibility, current-diff check requirements,
idempotency, evaluator boundary and budget behavior are unchanged. This is an
existing bounded view correction, not a new memory store, planner or verification
gate. Mutation makes prior observations historical rather than current evidence.

The implementation uses an isolated worktree because a separate mini-SWE run/test
was active in the primary checkout. Its runtime and unrelated uncommitted files
were not modified. No new paid solve, target replay or independent evaluation was
started by this work.
The primary runtime remains `sha256:4fe33c20ca40c4ed53ce58d5efb508bba6825ff1872d3eeed59da918ee2bf374`;
the isolated change is not automatically merged into the separately running setup.

## Local evidence and limits

The new regression selection failed before the fix: **12 FAIL / 3 PASS**. It checks
the real model-input assembly for fresh append/segmented requests after probe then
test/read, success/failure/partial retention, native deduplication, changed/unknown
diff exclusion and idempotent projection. The corrected completion-context file
passed **58 tests in 1.05 seconds**.

The expanded selection also exposed four stale probe-observation test contracts.
Read-only baseline execution confirmed **4 FAIL / 13 PASS in 9.27 seconds** on the
unchanged baseline runtime/helpers. Updated the default policy fixture fields,
current generic probe-description expectations and the distinction between raw
historical receipts and current completion evidence. Native receipt equality,
restart/idempotency, historical evidence and no-check-credit assertions remain.
Frozen historical expectations retain their branches. This file then passed
**17 tests in 15.13 seconds**; no production behavior was changed to satisfy it.

Final focused validation: **124 PASS in 84.91 seconds**, below two minutes. The
expanded selection including finalization/recovery controls passed **135 tests in
132.41 seconds** while the quick suite ran concurrently. Changed-file Ruff and
`git diff --check` passed. Documentation: **6 PASS in 0.17 seconds**, HTML 51 unique
IDs and 67 checked links; JavaScript unchanged.

The first quick run had 1,251 PASS / 1 skipped and one expected identity mismatch:
another current tool-surface hash fixture still pinned the old completion contract.
Updated that current expectation; old frozen identities and serialization tests
remain intact. The rerun is recorded separately rather than replacing failed output.
Final quick suite: **1,252 PASS / 1 skipped in 326.05 seconds**, four file-grouped
workers, no failures or worker restarts, including submission and isolated mock
evaluation controls. All captured validation runs kept the same runtime identity.
Full-suite completion, Linux execution and live-model quality/speed remain unverified.

Reprojecting the actual public turn276 state with old/new projection restores
`assertions_passed` and retains the two preceding failed observations unchanged.
All three behavior verdicts remain `not_assessed`; authority, budgets, current
patch, checks, notes and plan are identical. No provider input/reasoning artifact
is needed for this replay. Source journal bytes remain unchanged.

Raw projected state grew from **72,725 to 80,908 characters** (+8,183); the three
probe summaries account for 8,116 characters. This is a character count before
native/state deduplication, not tokens or measured cost. Retention can increase
input cost, so speed or fewer calls cannot be claimed from this local fix.

Improved selection of different input/option boundaries remains a model-behavior
hypothesis. The prompt refinement does not itself establish that behavior. Another
paid run needs a new exact scope; no previous unused allocation is reused. The
independent SQLFluff failure's exact assertion remains unknown.

## Evidence locations

External root: `C:/pt/verification-selection-20261030-v1`.

- `delivery-audit/audit.json` points to public-only audit
  `sha256:fae6b518510bd543673da5c3a43fa7c6e512fddb1ef428b1a617a2b53b008d23`.
- `projection-replay/result.json` points to before/after report
  `sha256:03eb216fa3751aa6cdd0142a5873799de8ff1a05711ea84b5e26775ecee030a0`.
- Source journal byte hash:
  `sha256:b9afe854b272300f9cc50218843e6d7031aab531b43717cf3c297ccb59730c53`.
- Source public context:
  `sha256:4f598d380afc6e44a4d78b6b2adba77e8738547fd109cf0c5ddb7f14c828f4f0`.
- Public handoff that omitted the observations:
  `sha256:d3118c867744989411a8d6d13f57eecfb5e197454adb4dc37fe6ad4f2d99b07d`.
- Focused validation pointer: `validation/focused-core-v2.json`, report
  `sha256:b7a235441deb9a057c2260d843107ad431e83133a7899e190e9e707e14942c4b`.
- Final quick pointer: `validation/quick-v2.json`, report
  `sha256:1c48d4203a2663cf4435f57ad41a12f633881308b5d2ce0e570396f6721d4848`.
- Baseline/candidate stale-test logs: `validation/observation-{baseline,candidate}.txt`,
  journal `run_dev_observationcontracts`; no production fix was hidden in these tests.

Each external result is content-addressed and journaled in append-only `dev-run-v1`.
Private specs, hidden tests, reference patches, evaluator internals and model
reasoning were not inspected. Closed historical records remain unchanged.
