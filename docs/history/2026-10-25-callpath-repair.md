# Original-call diagnosis before another repair

Status: implemented and locally validated. official=false, claim-ineligible.

## Problem and decision

The [preceding investigation](2026-10-25-judgment-callpath-analysis.md) found that
consistent F0010 judgments and delivered changed-line feedback still led to four
ineffective mutations. Changed branches were not on the failing call's path;
initialization/control hits were misleading, and the added helper assertion also
passed on the base. This matters to correctness and bounded-resource use: more
edits to an unexecuted branch cannot test the proposed original-call repair.

Selected intervention: observe a bounded failing-call path before another edit,
bind the next hypothesis revision to that evidence, and provide optional identical
selected tests on before/after source. More output budget or repeating the same
regression was not selected. A complete path may still reveal that a hypothesis
is wrong, a necessary caller is unmeasured, or the selected test has an invalid
expectation; none is converted into repair success.

## Implementation

- A host-bound collector scopes simple input/line/return/exception observations to
  one original invocation and focus frame. Separate output framing preserves the
  diagnostic oracle. Unknown never means an unexecuted branch.
- A receipt-derived diagnosis state activates only for same-condition acquired
  original failure plus still-current unobserved implementation changes. It binds
  the previous prediction, failure, candidate and watched hashes. One preparation
  read and one actual diagnosis are available; malformed requests have one
  correction. The next mutation's existing causal_revision receives the completed
  diagnosis link. Incomplete/exhausted work returns verification incomplete.
- Optional `run_tests.comparison` builds two isolated snapshots with identical
  selected tests. `before_mutation` refers to an implementation preimage, even
  when tests were added later. PASS/PASS, assertion fail-to-pass, setup/collection
  failure and body errors are distinct. Original requirement credit remains false.
- Forecasts include diagnosis once and protect preparation/request correction.
  Comparison reserves two child executions. Exact finished receipts are reused;
  missing outcomes after durable start stop without redispatch. No output, cost,
  edit, action or wall limit was raised. Current prompt remains below 8,000 chars.
  If only a single selected execution fits, the schema exposes only null comparison
  before inference; it does not advertise a comparison that would force a late stop.

Source contract: [repair-path](../../.agent/repair-path.md). Baseline source:
`2d7e335615864c4d4e5e919e4dfbad07791e58ae`. External plan and hash-chained journal:
`C:/pt/callpath-repair-local-v1/plan.json`,
`C:/pt/callpath-repair-local-v1/runs/run_dev_callpathlocal.jsonl`.

## Validation and limits

Final current-source validation:

| Check | Result | Recorded wall time |
| --- | --- | --- |
| `@tests/call-path-repair.txt` | 54 PASS | 64.191 seconds |
| `@tests/quick.txt` | 318 PASS, including isolated mock evaluation | 67.612 seconds |
| Ruff, `patchloop tests docker/probe_runner.py` | PASS | recorded in external journal |
| Documentation bounds/links and diff whitespace | PASS | included in quick and closeout |

The two final test groups used separate short external basetemps and ran in
parallel. Focused validation stays below two minutes. Earlier affected snapshot
checks passed 28 tests in 5.945 seconds, preserving frozen branches and existing
prompt-size limits. The first quick pass exposed stale current prompt assertions
and an oversized guide; wording/expectations were corrected without raising limits.
The full regression was not run. No separate duplicate mock smoke was run. Tests
use synthetic public source/local fixtures with no provider calls or real containers.

During implementation, a source-binding typo was found to reach the dispatch
uncertainty handler before any execution. Source-aware validation now runs during
preflight, so a wrong function/line remains a correctable rejected request. The
first integration fixture also had different local import-path initialization
with tracing enabled; the fixture now fixes its launch condition rather than
weakening production call-identity comparison. Neither failure is repair evidence.

Final review also found that unrelated initialization events could consume the
focused trace allowance before the caller was reached. Only focus-subtree events
now consume that allowance; initialization still reaches existing LineTrace, and
exceeding the focus allowance remains unknown. A low-limit control covers both
cases. Resource review caught a schema/admission mismatch: an unaffordable pair
could be advertised while only one execution fit. Dynamic null-only comparison
selection resolves that before the model call and preserves ordinary testing.

This supports local observation/state/comparison/recovery mechanics only. It does
not establish live-model uptake, Astroid repair, causal repair gain, independent
acceptance, Docker isolation or generalization. Prior reports and closed paid
allocations remain unchanged. The next unresolved question is whether a fresh
bounded live solve uses caller evidence to produce an original-call repair and a
valid discriminating test; such a run needs its own exact authorized scope.
