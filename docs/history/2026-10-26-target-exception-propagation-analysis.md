# Captured target failure lost before the repair loop

Status: ANALYZED; no runtime change or live rerun.
Date: 2026-10-26. official=false; claim-ineligible.

## Material Passport

- Origin: academic-research-suite / experiment-agent / validate.
- Version: target-exception-propagation-v1.
- Source: closed run `run_dev_b4614e40c1714e81`, its public action/input artifacts,
  current source and focused tests. This follows the [context/classifier audit](2026-10-26-target-failure-context-analysis.md).
- Question: where did the failure stop influencing repair and submission, and why
  did local tests not cover the live form of that failure?
- Scope: static source review, production completion projection over saved events,
  and a scoped read-only test audit. No target execution or provider call.

## Why this problem matters

The request-continuity pilot finally reached original reproduction and an applied
edit, but submitted the first candidate after a known exception. Its public suite
passed 1,231 tests (69 skipped, 15 xfailed); independent acceptance failed. The
exception was available before submission, and further repair capacity remained.
This isolates a reliability bottleneck after the earlier request-construction
failures, rather than providing a reason to increase every resource limit.

## Three different outcomes were conflated

| Layer | Actual saved outcome | Meaning |
| --- | --- | --- |
| Registered tool action | `succeeded` | Execution returned a receipt |
| Selected original call | `raised`, capture `complete`, `FileNotFoundError` | A current target failure was observed |
| Entire authored probe | `failed`, exit 1 | Helper raised after inspecting the captured exception |
| Whole-case comparison | `not_compared`, evidence `UNKNOWN` | Expected observation JSON was not completed |
| Target-failure projection | count 0 | The outer-status guard discarded the selected failure |
| Final workflow | `ready_to_submit`, `unverified_delivery` | Public PASS enabled return without another edit |

`observed_target` catches ordinary exceptions, records the call and returns a
result object. An unexpected exception also marks whole-case observation incomplete;
this correctly prevents equality/success credit. The live helper then inspected
the result's exception and raised `RuntimeError`, causing outer exit 1.

`target_outcome.bound_failure` requires outer `passed/0` before examining selected
calls. The same evidence can therefore be actionable when a helper records null
and returns normally, but not actionable when the helper reports it by raising.
That dependence on later helper behavior is the defect: already captured negative
evidence should not disappear solely because later postprocessing fails.

The final input retained the current call's exception, but the prominent
`current_public_failure` was null and there was no original-failure diagnostic.
The model's final assessment emphasized the intended fix and public PASS, described
the exact original scenario as not freshly rerun, and omitted the observed current
exception. This establishes inadequate evidence use in the final decision; it does
not reveal the model's internal reason or isolate the causal effect of context resets.

## Existing downstream behavior is already present

The actual base/candidate binding, selected inputs/environment and valid complete
capture match. The previous audit isolated the outer-status/exit guard. This
follow-up evaluates `completion_reproduction.review()` over the full saved event
sequence, changing only those two fields in an in-memory diagnostic copy:

| Output | Actual record | Diagnostic copy |
| --- | --- | --- |
| Overall verification | unverified | unverified |
| Whole-case evidence | UNKNOWN | UNKNOWN |
| Target failure count | 0 | 1 |
| Existing original diagnostic | none | available, preparation available |
| Runner's original-failure predicate | false | true |
| Gateway's original-failure finish blocker | false | true |

The runner already switches this condition to `needs_mutation`; the gateway already
rejects finish even with public PASS. No new tool, prompt, submission rule or retry
budget is required to establish that route. The diagnostic copy is not a repaired
runtime, a changed receipt or a live decision replay. Unknown verification remains
unknown; detecting a negative outcome grants no repair-success credit.

## The patch failed a downstream source contract

The submitted `file_build` catches the initial missing initializer and sets
`data=""`, but retains the nonexistent file path. Unlike `string_build`, it does
not populate `module.file_bytes`. Later Pylint tokenization calls `module.stream()`;
`Module._get_stream` opens `module.file` when no bytes are present. The separate
public execution's stack shows that missing-file read and the later crash-report
read of the same missing initializer.

This explains the observed replacement exception. It does not establish that
simply setting `file_bytes` would satisfy all package-discovery/child-analysis
semantics. The next repair must test the actual original caller and its downstream
behavior, rather than conclude that suppressing the first exception repairs the task.

## Why the tests missed it

The existing positive integration test in `tests/test_target_outcome.py:27` runs a
real local exception. Its shared source in `tests/test_probe_purpose.py:22` sends
`observed_target(...).value` directly to `record_observation`. The observer returns
null after capturing the exception, so this helper still exits zero. The synthetic
`raised()` fixtures change only the call trace; the cloned root's outer receipt
also remains passed/0. `ExecutingProbe` accurately reflects subprocess exit status:
the gap is the program/condition combination, not a fake successful backend.

Existing tests cover changed input/environment/binding, duplicate IDs, expected
exceptions, SystemExit, truncated capture, timeout and unknown cleanup. They do
not exercise the positive combination of complete target failure followed by
nonzero helper exit. Setup failure is checked in observation tests but not directly
in this positive-failure promotion path.

The smallest useful regression addition is one real frozen helper that completes
on the baseline but raises after a captured candidate exception. Assert retained
failure, UNKNOWN verification, existing diagnostic/repair routing, finish blocking
despite public PASS, and recovery without duplicate replay. Apply the existing
uncertainty controls to its failed/1 receipt, plus two distinctions: helper failure
before any target call and normal target return followed by helper failure. Neither
should become a target failure. Broad test duplication is unnecessary.

## Decision and unresolved questions

The next implementation should separate trustworthy selected-call failure from
outer helper completion and reuse the existing repair path. Preserve strict
identity/capture/setup/cleanup checks and unverified fallback for genuinely missing
or uncertain evidence. Do not require fixing the helper to exit zero before using
an already complete target exception. Do not classify every nonzero probe as a
target failure or relax success/comparability checks.

Context continuity remains a separate possible contributor. The saved final input
contains the exception; the current finding supports correcting classification
first. Whether a corrected route leads the live model to a good second repair is
unmeasured. A guard change is not task repair or evidence of general improvement.

Reproducible analysis: `C:/pt/target-exception-propagation-analysis-v1/analyze.py`.
Result `analysis.json`, CAS
`sha256:d1aae688da2472cdd1116e96af3ba70f22cbed919ea66d488ac70cf2b7d1e2f0`;
separate append-only `dev-run-v1` journal and source hashes under the same root.
Earlier run/analysis records remain unchanged. Fallacy scan: 11/11 considered;
selected-task bias, one-run variation, observational model behavior and the
difference between offline projection and live repair constrain the conclusion.
