# Post-Conan milestone review

## Decision

Close the original-task preparation and validation milestone. Retain the current
agent baseline, hidden acceptance requirement and optional probe policy. Select
no further implementation, paid experiment or task from the reviewed evidence.
This is a decision to stop this work sequence, not a claim that repair quality is
sufficient. The most important unresolved product problem remains verification
coverage of preservation and boundary behavior; no supported general intervention
or newly unresolved current-contract defect emerges from these additions.

## What the new evidence changes

| Evidence unit | Classification | What it establishes | Disposition |
| --- | --- | --- | --- |
| jsonschema original live run | Preparation/evaluation defect | Public checks passed but the package had no hidden checks; original terminal remains FAIL | Missing-hidden admission is fixed; do not count this as a demonstrated semantic repair failure |
| jsonschema v2 saved-patch evaluation | Post-run operator validation | Six hidden methods and public/scope/safety checks pass on saved bytes; baseline and wrong-repair controls fail | Useful development evidence, not a second solve or independent held-out trial |
| Conan dependency preparation | Environment support | Initial wheel-only resolution failed; an explicitly reviewed offline-built wheel enabled the existing probe environment | Resolved for this pinned environment; no general build fallback or dependency relaxation |
| Conan live run | Successful original-task repair | Public 28/28, original F2P 1/1 and P2P 21/21, acceptance and safety PASS; USD 0.544468 | Keep baseline; no general success-rate estimate |
| Conan intermediate probe | Agent verification and correction | Public diagnostic failed on the intermediate patch, followed by a second edit | Positive evidence of using optional feedback; no controlled causal benefit measurement |
| Conan final probe replay | Post-run operator validation | The identical two-case probe passes on final submitted bytes | Closes this evidence gap; does not credit the agent with a final probe rerun |

Sources: [jsonschema live result](2026-10-01-jsonschema-live-result.md),
[hidden follow-up](2026-10-01-jsonschema-hidden-evaluation.md),
[Conan preparation failure](2026-10-01-conan-probe-preparation.md),
[environment completion](2026-10-01-conan-probe-ready.md),
[Conan live result](2026-10-01-conan-live-result.md),
[exact probe replay](2026-10-01-conan-final-probe-replay.md).

These units are not interchangeable trials. Do not pool live solves, operator
replays, environment failures, exposed task comparisons or different evaluators
into an aggregate success percentage. Original hidden acceptance is stronger than
public PASS for the frozen oracle, but it does not prove exhaustive correctness.

## Remaining problem and competing explanations

The earlier [development review](2026-09-30-development-review.md) and
[priority review](2026-10-01-failure-priority-review.md) establish public boundary
errors in Pydantic/HF and incomplete inverse preservation in Darts. Conan does
not negate those failures. Their recurrence makes coverage a product concern,
but historical exposed cases do not measure current-baseline failure frequency.

The [Darts closeout](2026-10-01-darts-decision-scope-closeout.md) already tested the
limits of the saved evidence: verification omitted a zero-width case, but the
record cannot distinguish input-generation failure, scope judgment, confidence
or another internal selection process. Prior guidance changes did not fix the
frozen gaps. Reopening the same trace would not discriminate these explanations.

Conan weakens a universal inability-to-use-probes explanation. Its missed final
probe rerun is a verification-process limitation, but the exact replay succeeds.
The audited repair-recheck contract intentionally selects failed registered
checks only. Thus this case supplies neither a broken trigger nor an observed
incorrect final patch that automatic probe replay would have prevented. Generic
model-authored assertions can also fail because of fixture/expectation errors.
A mandatory probe gate would add behavior and cost without demonstrated benefit.

The jsonschema defect has an identified code owner and regression: live admission
in patchloop/dev/runner.py now rejects empty hidden_checks; tests in
tests/test_jsonschema_task.py cover refusal before execution. Nonempty checks do
not guarantee coverage, so baseline/reference/wrong-repair calibration remains
separate. There is no reason to weaken acceptance or treat the count gate as a
semantic-quality certificate.

## When to reopen development

For normal product use, retain the baseline and record failures. Reopen targeted
work when a current run reproduces a contract violation, or provides an explicit
mechanism connecting a proposed change to a missed repair. For example, a valid
public counterexample still failing on the submitted patch could justify checking
whether its evidence reached the agent and whether a bounded exact replay would
have changed submission. First distinguish candidate failure from invalid probe
setup. That is a conditional diagnostic, not a queued experiment or authorization.

Do not select another task merely because Conan finished successfully. A future
measurement campaign needs its own question and frozen sample/resource limits;
it should not be assembled as successive convenient one-task runs. No campaign,
prompt change, memory addition or automated probe requirement is selected here.

## Evidence and validation

Reviewed current authority at main 0254b91c and bounded named historical records;
closed records remain unchanged. The new hash-chained external review is at
C:\pt\analyses\post-conan-review-20261001-v1, run_dev_postconanreview. It binds six
principal review documents and revalidates the Conan live and final-replay journal
chains. Older panel conclusions are taken from their cited reviews, not newly
recomputed from all historical runs. No private test/reference bodies were read.

This change updates documentation only. Documentation layout/link/size and diff
whitespace checks validate it; runtime tests and mock smoke are unnecessary.
No provider calls, credential loads, task execution, Docker operation or paid
allocation occurred. The earlier allocations remain closed.
