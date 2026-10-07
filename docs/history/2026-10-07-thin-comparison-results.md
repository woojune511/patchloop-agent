# Current/thin comparison results

Date: 2026-10-07. All runs are official=false and claim-ineligible.
Execution HEAD: `6da629ee57acbbcc46d533333af8549fc2b5aee9`.
Runtime hash: `sha256:3381660b5484eb474efe897157c711b32a8c26f54cbba05ab90ac1c9ec226522`.
This closes the [prepared design](2026-10-07-thin-comparison-preparation.md)
and [execution readiness](2026-10-07-thin-comparison-readiness.md).
Those earlier records remain unchanged.

## Question and scope

Recent SQLFluff repair failures persisted despite available source, public probes
and additional verification guidance. This comparison asked whether reducing the
policy/interface bundle could preserve known successes and improve those failures.
The alternative was that repair selection and verification remained the bottleneck;
less narration could also remove useful operating instructions. More probes or
fewer tokens alone were not improvement criteria.

The user's explicit acceptance of the prepared USD 64 proposal authorized sixteen
fresh solves: SQLFluff-1733, SQLFluff-2419, pvlib-1072 and pydicom-1694, twice per
policy. A used current/brief-v1; B used thin/none. Both used
gpt-5.4-2026-03-05, xhigh, 25,000 desired output tokens and the repository `.env`.
The exact credential path is recorded in the manifest; no credential contents are
included in this report. Each row had USD 4, 40 model calls, 100 actions, four
accepted edits and 1,800 active seconds including the evaluation reserve.
Native grading retained its separate 600-second operational timeout.

Four counterbalanced waves ran with at most two distinct tasks concurrently.
Shared source retention, sandbox/tool capabilities, probe and recheck policies,
task/environment identities and grading remained frozen. Existing images only
were used. No retry, resume, replacement, cap transfer or intermediate intervention
occurred. The entire allocation closed after 16/16 attempts, with no global stop.

## Outcomes

| Axis | A: current | B: thin |
| --- | ---: | ---: |
| Attempts | 8 | 8 |
| Submitted | 8 | 7 |
| Registered acceptance PASS / FAIL / NOT_RUN | 6 / 2 / 0 | 6 / 1 / 1 |
| Independent native agreement | 8/8 evaluated | 7/7 evaluated |
| Frozen public behavior PASS / FAIL / NOT_RUN | 6 / 2 / 0 | 6 / 1 / 1 |
| Safety PASS / NOT_RUN | 8 / 0 | 7 / 1 |
| Settled USD | 4.84294700 | 4.87069750 |
| Model calls | 80 | 113 |

| Task | A repeat 1 / 2 | B repeat 1 / 2 |
| --- | --- | --- |
| SQLFluff-1733 | FAIL / FAIL | FAIL / NOT_RUN, unsubmitted |
| SQLFluff-2419 | PASS / PASS | PASS / PASS |
| pvlib-1072 | PASS / PASS | PASS / PASS |
| pydicom-1694 | PASS / PASS | PASS / PASS |

All fifteen submitted patches had complete registered/native agreement, confirmed
assessment cleanup and matching scoped public verdicts. Public PASS remains
evidence for the frozen cases, not an independent definition of task correctness.
The sixteenth row stopped voluntarily before any source inspection or mutation;
its acceptance, public evaluation and safety remain NOT_RUN. It was not silently
excluded or replaced, and NOT_RUN was not converted into a graded FAIL.

Total cost was **USD 9.71364450 of USD 64**, fully settled: 193 model calls,
194 input counts and 288 tool actions. Wall time was 3,783.758 seconds (63m04s),
including parallel execution and assessment. Billing/counting are known. There
were no infrastructure-uncertainty or resource-limit terminal outcomes. Row 8 did
consume all four accepted edit slots; that narrower constraint is discussed below.
Per-arm task times overlap and B includes an early abandoned run, so aggregate
time cannot establish a completion-speed improvement. B did not reduce total cost.

## Public trace and operating-contract findings

Every submitted row ran a required check that passed after its final accepted edit.
Neither arm ran an optional probe or selected test after its final edit. This does
not mean probes were unavailable or unused earlier, nor that required checks had
no value. It leaves the already-observed gap between regression PASS and the
specific requested behavior unresolved. The operator's frozen public grading was
post-submission and was never returned to the solver.

Current's two failed SQLFluff-1733 rows used three and five probes respectively,
then one source edit each. Both still had edit, probe and selected-test tools
available at their final turn. Their termination therefore is not explained by
model/time/edit exhaustion. Across the whole panel, A used eight probes and no
selected tests; B used six probes and one selected test. Counts describe behavior,
not whether the probes asked the right question or established correctness.

Row 8, SQLFluff-1733 thin repeat 1, used four accepted mutations: three source
changes and one test change. Its final turn no longer offered replace_text,
although reads, probes and selected tests remained available. It used 28/40 model
calls and submitted rather than ending in a resource-limit terminal. Edit capacity
was exhausted; whether another edit would have produced a correct repair is
unresolved. Do not describe every row as unconstrained merely because the global
cost cap had room, or infer that a larger edit cap would have solved this case.

In that row, the failing early probe was not a credible task counterexample: after
successful setup it accessed an unavailable `LintedFile.paths` attribute and raised
AttributeError. Later required-check failures were real public L036 fixture string
assertion mismatches (1 failed, 505 passed). Those failures were followed by source
edits; the final recheck passed. A selected-test PASS preceded the last two source
edits. This weakens a blanket explanation that the agent ignores every failed
check: here it corrected regression failures but still submitted a patch that
failed the separately frozen task behavior. No claim about private test semantics
is needed for that distinction.

Row 11, SQLFluff-1733 thin repeat 2 (`run_dev_577f6d56624f4c83`), stopped after
one model call and zero mutations, at USD 0.015871. Its public stop summary said
the offered tools had no mutation/submission action, so it could not repair the
task. Those tools really were absent on the initial turn. The mistaken implication
was that their absence was permanent:

- [Runner tool policy](../../patchloop/dev/runner.py) exposes replace_text after
  current editable source evidence has been delivered; finish additionally needs
  a nonempty scoped patch and required checks passing on that diff.
- [Current prompt](../../patchloop/dev/model.py) explicitly explains that read or
  search can reopen edit availability and temporary tool absence is not a task conflict.
- [Thin prompt/projection](../../patchloop/dev/thin_policy.py) keeps observed-anchor
  requirements but omits that transition explanation and removes the derived
  completion message. Its remaining readiness fields did not prevent this stop.

The same staged admission mechanism applies to both arms. This is a concrete
disclosure weakness consistent with the observed stop, not evidence of disabled
mutation capability or an environment failure. A single stop does not establish
that restoring the sentence causes higher acceptance. Availability-parity tests
verify which tools are offered; they do not prove the model understands when a
temporarily absent tool becomes available.

## Frozen decision and next question

The precommitted decision is **INCONCLUSIVE_NO_ADOPTION**. Both arms preserved all
four successful-control attempts, with no observed paired A-PASS/B-FAIL among
graded pairs. However, no failure task changed A FAIL to B PASS in both repetitions,
and one B attempt has no acceptance verdict. The replicated improvement criterion
was not met even before that incomplete-evaluation qualification.

Keep current as the selected baseline. The panel does not support thinning the
default, increasing context/cost limits, or another adjacent paid prompt comparison.
SQLFluff-2419 now passed both arms; historical mini results used another model and
are not a controlled estimate of a current/full-model or policy improvement.
Four development-exposed tasks and two repetitions do not establish general quality.

The next narrow engineering question is whether the experimental thin interface
can state factual tool prerequisites without restoring advisory narration. A
minimal candidate correction would retain the read-to-edit and check-to-submit
availability contract, with a provider-free projection regression check. It is
not implemented or funded for a rerun by this closeout. Separately, SQLFluff-1733
still calls for a public candidate/verification diagnosis: explain why the submitted
repairs fail the frozen behavior despite required-check PASS before adding another
prompt, mandatory probe gate or resource increase. No new paid run is queued.

## Evidence and validation

- Frozen execution manifest: `C:/pt/thready01/manifest.json`, canonical hash
  `sha256:5f8ab6f02e62c1ce19aa10db95dac086e32d7a5400b3345b8f2ffc91d37f0264`.
- Explicit scope approval: `C:/pt/thready01/authorization.json`, file hash
  `sha256:a69a3a55623b778e18f3d929e4708a9483ea69ecb35457166f3ff3efdea54555`.
- Final result: `C:/pt/thready01/result.json`, file hash
  `sha256:4a4a9b942e34a25053e88f7a5336e8b1ab548925e9bbd907398225a8f73e5a0d`.
- Append-only coordinator journal: `C:/pt/thready01/runs/run_dev_thincomparison.jsonl`;
  solver state and assessment receipts: `C:/pt/thlive01/<row_id>`.
- Outcome summary: `C:/pt/thanalysis01/report02/summary.json`, file hash
  `sha256:9c6655eb1aca730ce57b592872ac0bb937a488ae12376ff6615e0eb1111c279b`.
  Its separate `verification.json` is
  `sha256:70b4d7950da39b7484be997304950da7f8fabb1f9739f2e54bff472e526d9475`.
- Public trace audit: `C:/pt/thtraceaudit01/audit.json`, file hash
  `sha256:be4ae04affe63ac3785ba9711e095e6472d185b45b04b352e074fde36ba8bc53`.
  Narrow public failure review: `C:/pt/thtraceaudit01/public-failure-review.json`,
  `sha256:0108da34f149d439cf36f6e2c6c0b6850871c89757ae383f6ba482b37263f96c`.
- Independent final audit: `C:/pt/thfinalaudit01/audit.json`, file hash
  `sha256:48ead23aa6f316910ee368090b18920733d2665f631a70bc0a83be0b0b8fc573`.
  All 4,065 checks passed across 3,035 journal events, including frozen row
  identities, authorization, count-before-dispatch, settled price arithmetic and
  receipt/patch hashes. No raw reasoning or private test semantics were inspected.

Implementation checks and both mock smokes preceded execution and remain linked
from readiness. This turn live-executed the authorized solves and grading; the
post-run change is documentation only. Runtime/defaults and historical records
are unchanged. User-owned AGENTS.md changes were preserved and excluded from the
closeout commit. No follow-up model calls, probes or evaluations were run to repair
or reinterpret these outcomes.

Closeout documentation layout/link tests passed 5/5, recorded in
`C:/pt/thanalysis01/docs-closeout-final.xml`; whitespace checks passed. The first
documentation check found the current-status page 103 bytes above its existing
limit; its new summary was shortened before the pass. No runtime test or smoke
was rerun for this documentation-only closeout. The public metadata audit first
encountered an incorrect coordinator-path assumption in its external helper;
the corrected helper only read the same immutable inputs and did not rerun tasks.
