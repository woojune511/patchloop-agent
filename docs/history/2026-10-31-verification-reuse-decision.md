# Same-patch verification reuse: selection cues and next-action reasoning

Date: 2026-10-31. Status: CLOSED, implemented and locally validated. Baseline: a1f31888.
All evidence is development-only, official=false and claim-ineligible.

## Problem and evidence

The user requested a general improvement for redundant checks/probes on unchanged
patches. This matters because model decisions, not just test subprocesses, dominate
the observed latency. The closed [integrated 1/4/11 run](2026-10-31-integrated-1411-results.md)
contains three subset selections after a same-diff tests-directory PASS. Their tools
took 11.805931 seconds; associated model decisions took 125.496561 seconds and
USD0.23724. These are associated costs, not demonstrated avoidable savings.

The public-input audit is at
`C:/pt/integrated1411-run-20261031-v1/analysis/verification-overlap.json`, CAS copy hash
`sha256:1b5539f662fd0b8ad18c86c038d921003236358f09cf0beae9b3ab7e76d833d1`.
It links the exact delivered public input artifacts; no private evaluator or
provider reasoning was used in this investigation.

- Before marshmallow's changed-file selection and Astroid's three-file selection,
  full-check PASS and declared `tests` scope were present. Changed files still
  said `discovery_unknown` and supplied an unconditional `run_tests_selection`.
  Astroid's public action basis explicitly cited uncertainty about added-test discovery.
- The other marshmallow selection targeted an unchanged neighboring file. It did
  not have a changed-file discovery warning. The UI cue cannot explain all repeats.
- Astroid's first non-Dict probe failed while printing an exception, then a corrected
  probe explicitly asserted the intended exception and passed. A subsequent probe
  renamed variables and repeated equivalent successful assertions on the same diff.
  Its public basis called the already observed case remaining. Latest stdout, exit
  zero and `current_public_failure=null` were delivered in input `0573c7ef...`.
  Re-running the corrected logging probe was useful; the subsequent equivalent
  case supplied no identified new behavior evidence.

## Explanation and design decision

Missing successful-result delivery is contradicted for these observations. Generic
reuse guidance was already present, so another general exhortation is insufficient.
Two narrower mechanisms are plausible: ambiguous collection wording nudges explicit
selection, and the model fails to compare a proposed case with actual prior output.
Neither causal explanation is established by a single trace. Real discovery omission,
filters, changed setup, partial output or unstable behavior can justify another test;
literal directory arguments alone cannot rule those out.

Keep the bounded evidence projection and registered tools. Make declared scope and
unreported collection separate, and make a file selector an available option rather
than an implied next action. Avoid repeated suggestions after an adequate explicit
file selection. Do not infer collected tests from filenames, PASS counts or directory
scope, and do not add pytest instrumentation solely to eliminate this advisory ambiguity.

Replace the shared reuse sentence with a concrete comparison: before another check
or probe, compare its input/setup/assertion with current-diff observations and name
the additional information in the existing public `basis` when offered. Equivalent successful
cases can be reused; new cases, conditions, assertions, uncertainty and post-edit
checks still warrant action. A renamed program alone is not new information.
`not_assessed` means no host semantic judgment, not a requirement to repeat an observed
case. Required current-diff PASS, uncertainty handling and action recovery stay exact.

This is guidance and navigation, not a semantic duplicate detector, execution cache,
new persistent memory, request field, review round, budget allowance or finish gate.

## Implementation and local validation

Source owners are `patchloop/dev/check_review.py` and `patchloop/dev/repair_guidance.py`;
contracts are `.agent/selected-tests.md` and `.agent/planning-experiment.md`.
Local receipts live outside the repository at `C:/pt/reuse1031/` in hash-chained
`dev-run-v1` JSONL with content-addressed outputs.

- Changed-file selection tests exercise passing explicit selections, literal
  filters, partial nodes, failures/conflicts, stale/unknown currency and nonstandard
  filenames. Directory selection remains unreported collection; no execution credit
  is inferred and no registered tool becomes unavailable.
- Synthetic actual-request tests preserve the earlier probe logging failure and
  latest successful or timed-out observation across ordinary/segmented context.
  Changed patches exclude old successful observations. Current/thin and repair/
  completion delivery retain the same offered tools, budget and workflow gate.
- The first quick suite had 1,302 PASS, 1 SKIP and 6 failures: five bounded-prompt
  checks and the intentionally changed current prompt identity. The shared text had
  grown the system prompt to 8,431 characters. It was compressed back within the
  unchanged 8,000-character contract; memory and request schemas were not expanded.
  Only the current surrounding-prompt identity was updated; frozen identities stay exact.
  Review also qualified `basis` with "if offered" for schemas without that field.
- The corrected focused suite passed 156 cases in 16.620 seconds, including all
  initial quick failures. Quick then passed 1,308 cases with 1 host-symlink SKIP in
  275.98 seconds using four workers, including isolated mock evaluation. No worker
  crashed and the runtime stayed fixed during each check.
- After that quick run, review changed only "Refute material assumptions" to "Test
  material assumptions" and its current prompt digest: an assumption may survive
  testing rather than being required to fail. Final focused/delivery/identity/bound
  validation passed the same 156 cases in 16.788 seconds; Ruff passed again. The
  full prompt is 7,994 characters. Quick was not repeated for this final wording-only
  change. The full repository and Linux suites were not run.
- Reprojection of three saved public inputs preserves gates, tools, budgets and
  required-check verdicts. The two directory rows now show factual selection plus
  unreported collection; the already passing explicit-file row loses its repeat
  suggestion. This does not determine whether the unchanged neighboring-file test
  or equivalent probe would still be chosen by a live model.

The initial failed quick receipt is
`sha256:bc55e1d73190d3ce6ed9647c85e9142137dfa9ddbc007f31697e055959603417`.
The passing quick receipt is
`sha256:6c15d0d785c4bfe5e650101bab3f07c5f8ce6635630dc75117c3195e9b939092`.
The final focused receipt is
`sha256:b6c2e1d2303e66d796b09596a33a8879016182d7e15b49729166c99784f57d0a`.
Final runtime identity:
`sha256:06b0bbc8bd933616c7e40495a87bdaf76207db10f477263d98bbb6ab0cb8e866`.
No result was overwritten or converted into a successful receipt.

## Result and unresolved question

The design preserves unknown collection instead of turning directory PASS into
execution proof. It also preserves meaningful counterexamples instead of blocking
all repeat-looking programs. Local checks can establish projection, delivery,
currency and gate preservation; they cannot establish that a live model will avoid
the next equivalent probe. No paid call, target experiment or new independent
evaluation is performed here. The next integrated development run can measure
repeated decisions, task acceptance, total cost and time together; a separate paid
ablation is not a prerequisite and no allocation is pending.
