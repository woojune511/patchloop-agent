# Required public counterexamples before completion

Date: 2026-10-28. Development implementation and local mechanism validation only.
No provider-backed run, target Docker execution or new allocation was requested.

## Problem and evidence

The [preceding run](2026-10-28-probe-revision-repair-results.md) resubmitted its
unchanged candidate after receiving three confirmed public regressions. At the
last request, a repair remained offered and its completion path was affordable.
The model acknowledged the failures; 8/11 required public cases passed, isolated
acceptance failed, and safety passed. Its paid allocation is closed.

This was selected because supplying evidence and reserving repair capacity still
allowed successful public finish while a known public regression remained. The
public matrix was an operator feedback packet and a post-submission measurement,
not part of the runtime's required checks. Output/context exhaustion does not
explain that recorded finish. A stronger model or extra funding might change its
choice, but neither resolves the host's inconsistent completion criterion.

## Decision and change

Reuse the registered-check flow instead of adding another model-authored diagnosis
rule. A host-owned supplemental registry freezes the public check definition,
program/expectation/environment identities and source evidence without changing
the original PublicTask or original-call purpose. A complete prior failure on the
measured diff is imported with its own provenance; it is not a new action or cost.
Registration changes/removal on recovery fail validation.

The effective registry drives status, run_check, automatic repair recheck, response/
action/cost/time forecasts and direct finish enforcement. Known FAIL and required
NOT_RUN block finish. Edits require new current-diff evidence, and the same failed
check can run automatically before the next model response. Replay keeps action
and input identities and does not rerun or double-charge a settled child. Stopping
or exhausting resources preserves unresolved checks. Speculative notes stay advisory.

The frozen public path diagnostic uses its prepared probe environment. The host
assesses all 11 required rows; program exit zero is not a PASS. The baseline's one
pre-existing discrepancy stays separate. Invalid/incomplete capture or environment
and execution uncertainty are not semantic success. Raw receipts are artifacts;
bounded failed observations reach the model. The old final-only action/35-second
reservation is removed. Each ordinary execution now reserves its 35-second timeout
plus standard five-second overhead in the shared completion path. Total run limits
remain unchanged. Final reporting reads current evidence without another execution.

The diagnostic schema changes to v2. Previous manifests and approvals are not
reused. Ordinary runs with no supplemental registry preserve their task-only path.

## Validation and remaining question

Focused validation covered 64 distinct controls: the primary 60-test selection
passed in 21.80s; two additional exact cost/time controls passed, and two preparation
audit controls passed in the final 10-test driver selection. Controls include
initial FAIL, post-edit NOT_RUN, unrelated PASS, same-check fresh PASS, exact child
replay (including expired-deadline receipt recovery), immutable registration,
actual next-model input delivery, host matrix assessment and advisory notes.

The exact resource fixture permits repair at USD1.820760000 and 205 seconds;
one nano-dollar or 0.001 second below the corresponding minimum permits only stop.
An additional ten seconds on the supplemental check adds ten seconds to the same
completion reserve. These are fixture boundary results, not live price estimates.

Quick ran once with four workers: 763 PASS and one documentation-size failure in
85.59s. Both scripted isolated mock evaluations passed. The guide exceeded its
16,000-byte limit, so redundant wording was shortened; all five documentation
checks then passed. The preparation review also found that an expected feedback
packet omitted the actual FAIL status and therefore compared against NOT_RUN.
The audit now derives its expected packet from the actual state; both initial and
later request controls pass and reject an offered finish. Ruff and diff whitespace
checks pass. An earlier concurrent owner run's runtime-identity failure passed
its isolated recheck after source was frozen. No full suite or live repair ran.

Local JUnit artifacts (outside the repository):

- `C:/pt/tmp/required-public-owner-all1.xml`
- `C:/pt/tmp/required-check-resources-20261028.xml`
- `C:/pt/tmp/required-check-recovery-20261028-1.xml`
- `C:/pt/tmp/required-counterexample-driver28-final.xml`
- `C:/pt/tmp/required-public-quick1.xml`
- `C:/pt/tmp/required-public-docs1.xml`

This change can establish consistent completion and evidence delivery locally.
It does not establish that a live model makes a correct revision, or that public
case success implies isolated acceptance or held-out generalization. The next
question is whether mandatory feedback leads the model to repair within a newly
authorized fixed budget; lack of a correct repair must remain an incomplete/failing
outcome even when the runtime now refuses premature finish.
