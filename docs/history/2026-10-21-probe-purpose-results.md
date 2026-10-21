# Purpose/observation comparison: stopped allocation and separate judgments

## Decision and scope

The approved six-row allocation is **closed after three starts**. A2, A3 and B3
were not started after B2 hit a local continuation error. There was no retry,
resume, replacement or transfer. Known new cost is **USD 1.97877345 / 5.28**;
all 89 generation calls and 96 input counts have settled receipts. Prior
allocations and their bills remain separate. All rows are official=false and
claim-ineligible.

The new interface was offered in all **54 dispatched B requests**, but neither B
run called `run_probe`. No purpose binding, recorded comparison or application of
such a comparison was observed. One B patch was submitted and independently
failed. This incomplete, unequal exposure does **not** estimate an A/B success
difference or establish that purpose-bound probes help or cannot help.

The selected question came from the [five-unbound-probe diagnosis](2026-10-21-reproduction-nonuse.md)
and [purpose/observation implementation](2026-10-21-probe-purpose.md): attaching
original requirements to a selected probe could make execution scope explicit,
while a separate observation channel could avoid treating progress output as a
verdict. The current decision is to preserve the comparison as inconclusive and
address the observed shared continuation defect before another paid comparison.

## Frozen conditions and evidence

- [Specification](../../.agent/plans/probe-purpose-comparison.md).
- Implementation HEAD: `783661c607de0c3e5c3991d364c97246e28099c2`;
  shared product runtime: `5ff8654b4dab0b668986b6a2f643e0b37e5caa68`.
- Canonical manifest:
  `sha256:1dca4ed346628cf4fd8a5cb60d4f87a599f9bdde6f39fc299c922c34878394be`,
  `C:/pt/probe-purpose46/final/manifest.json`.
- Task: dev-train Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml`.
  Model: `gpt-5.4-mini-2026-03-17`, xhigh; project `.env`.
- A: legacy nullable `reproduction` and JSON stdout. B: `purpose` and
  `record_observation`. Verification-state separation ON in both.
- Assigned order A1 B1 B2 A2 A3 B3; USD 0.88/row, 2.64/arm, 5.28 total.
  Transitions, two references, 24k source characters, 60k counted input tokens,
  40 model calls, 100 actions, four accepted edits and 1,800 seconds unchanged.
- Final implementation full suite: **5,503 passed, 20 skipped, zero failed**;
  focused 17, A quick 45, B quick 166 passed, Ruff passed. The prior five stale
  schema snapshot failures and their correction remain in the preparation packet.
  These tests preceded paid execution; they did not cover the compound failure below.
- Fresh standard pricing matched the packet: input/cached/output USD
  0.75/0.075/4.50 per million tokens, checked against
  [official pricing](https://developers.openai.com/api/docs/pricing).

External evidence root is `C:/pt/probe-purpose46/final`; execution state is
`C:/pt/probe-purpose46-live`. Principal receipts are `collection.json`,
`public-annotations.json`, `result.json`, `resource-analysis.json`,
`reconciliation.json`, `public-review/delivery-audit.json` and
`handoff-stop-local-replay.json`. Collection, public audit, assessment and analysis
have separate hash-chained journals under `final/runs/`. Original logs and frozen
files were preserved. Post-run packet validation passed before this report-only
change. The immutable preparation's `paid_authorized=false` is supplemented by
the separate exact human `authorization.json`, not rewritten.

## Outcomes: judgments are separate from acceptance

All six public annotations, including NOT_RUN rows, were sealed before opening
fresh acceptance grades. The schema can reveal the arm; this was not fully blind.
Manual public scope review was checked for identity, quote and receipt provenance;
there was no paid judge. Only the submitted B1 patch was assessed, using two caller
checks and one native evaluation, within the approved 12/6 ceilings.

| Row | Termination | Public judgment | Submitted | Missing-init caller | Init-present control | Native | New USD |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| A1 | COST_CAP_REACHED | NO_CLAIM | No | NOT_RUN | NOT_RUN | NOT_RUN | 0.87999570 |
| B1 | EVALUATOR_FAIL | UNSUPPORTED | Yes | FAIL | PASS | FAIL | 0.50617380 |
| B2 | PROVIDER_CONTINUATION_ERROR | NO_CLAIM | No | NOT_RUN | NOT_RUN | NOT_RUN | 0.59260395 |
| A2, A3, B3 | NOT_RUN | NOT_RUN | No | NOT_RUN | NOT_RUN | NOT_RUN | 0 |

Assigned-denominator J is A 0/3, B 1/3; only B1 made a completion claim, so its
conditional judgment count is 1/1 and A has no claiming-row denominator. This is
not evidence that A judges better: A1 exhausted its cap, B2 aborted, and three
rows never started. Accepted repairs observed are A 0/3 and B 0/3, with only one
assessed submission. Unsubmitted candidates were not evaluated and are not
observed repair failures or correct abstentions. `outcomes_complete=false` and
`favorable_local_signal=false`.

B1's public base regression passed: 1,231 passed, 69 skipped, 15 xfailed. Its
claim that the repair was complete was labeled UNSUPPORTED **before** grades:
the conditional `_spec_from_modpath`/manager argument never connected the actual
Pylint directory call to the edited `PKG_DIRECTORY` plus absent-init branch.
The model then said no remaining public verification would change completion.
The final input still contained the issue, unresolved original-path concern,
`required=UNKNOWN` and registered `requirement_coverage=not_assessed`. Those
fields alone do not determine the judgment; the missing caller/branch argument
does. No original-path counterexample was delivered, so CONTRADICTED was not used.

Independent assessment subsequently found F0010 still present and the child file
not analyzed for missing init; the init-present control analyzed the child and
passed. Native FAIL agreed with the registered isolated acceptance receipt.
Thus the public justification gap and an actually unsuccessful submission were
both observed, through separate evidence.

## Acquisition, delivery and use

| Stage | A: one started of three | B: two started of three |
| --- | --- | --- |
| Probe offered | 33/35 requests | 54/54 requests, new purpose schema |
| Probe attempts / admitted | 2 / 2 | 0 / 0 |
| Probe intent / actual scope | 2 helper diagnostics | No attempts |
| Declared original case / compared result | 0 / 0 | 0 / 0 |
| Faithful original caller execution | 0 | 0 |
| Bound comparison application | 0 | 0 |
| Supported scope reasoning | A1 acknowledged helper limits | No observed application |

None read the Pylint dependency caller source or executed `pylint src/project`.
The public issue supplied that command, but the missing caller connection was
never acquired. All three could inspect internal Astroid source. Search-history
tools were offered but never selected. B has no purpose/observation rejection:
the model did not try that interface, so blocked use is not the explanation for
its zero bindings. Feature availability does not prove model understanding or
that the model judged it unnecessary.

A1's first probe (public event 313) supplied `[src]` to `file_info_from_modpath`,
but called the manager with a context file without the same global search path.
It observed a namespace spec and an import error under differing setup. At event
343 the model explicitly noted this did not test the real failing Pylint path.
Its second probe (473) inserted the root into `sys.path` and compared direct
module-name, directory and file APIs. The directory call raised IsADirectoryError,
which differs from the issue's missing `src/project/__init__.py` error. These are
useful helper observations, not faithful original-caller reproduction. Both used
`reproduction=null`; there was no expectation-bound comparison. A1 edited
`ast_from_file` at event 487 but did not verify or submit that candidate.

B1 repeatedly planned a Pylint regression, then narrowed remaining work to the
registered suite and submission. No additional test was added. B2 remained in
source investigation before its rejected edit batch. Lack of probes is therefore
upstream of the new observation channel, and the comparison cannot measure that
channel's behavior or causal repair effect.

## What disappeared at transitions

The descriptive audit compares actual adjacent dispatched inputs at segment
changes, including their public history. It tracks previously observed source
lines with at least 20 non-whitespace characters and exact full probe bodies.
Counts are textual losses, not necessary-evidence counts; repeated snippets can
remain elsewhere, and differing trajectories are not a paired eviction experiment.

- A1: four transitions; 0, 40, 159, 0 tracked lines become absent. Losses include
  `builder.file_build` and later modutils path/context/spec helpers. Both acquired
  probe bodies remain available through subsequent dispatched inputs.
- B1: two transitions; 61 then 129 tracked lines become absent, mainly builder
  code and 19 manager lines. At completion, current manager lines 101-256 and the
  changed modutils branch remain, along with the original issue and scope warning.
- B2: two dispatched transitions; 220 then 366 tracked lines become absent. The
  latter includes import-spec finder conditions and manager entry points. The
  subsequent over-size correction never dispatches. No completed repair permits
  attributing a repair outcome to these losses.

Loss of internal source remains observable. However, the precise public caller
was never acquired, and B1's coverage distinction survived. Neither fact supports
explaining this panel solely as context eviction or solely as LLM reasoning ability.

## Why B2 stopped: locally reproduced, not repaired in this allocation

The 25th B2 response contained two `replace_text` actions in one batch. The existing
contract allows up to four reads/searches or exactly one other action; neither
edit executed. Event 353 recorded `INVALID_TOOL_BATCH` and prepared the permitted
correction. Input counting succeeded at event 356 with **67,329 tokens**. No
generation was dispatched for that correction.

The unchanged 60k size rule then requested a fresh segment. `segments.start`
treated the rejected decision, which had no matching completed tool batch, as
unfinished and raised `RecoveryError: cannot hand off an unfinished tool batch`.
The outer runner replaced that cause with the generic continuation-error message,
and the frozen collector stopped all remaining rows. Billing and counts remained
known. This was a local correction/size-transition conflict, not an API transport
or unknown-usage failure, and no purpose probe had been invoked.

A read-only replay of the saved journal reproduces that exact guard. The preceding
completed-batch control reaches handoff artifact creation, where the diagnostic
blocks writes. It makes zero provider/count/evaluator calls and leaves the original
journal and runtime unchanged. The guard is shared by both arms; one occurrence in
B does not establish an effect of the new schema.

The next concrete engineering question is how to represent a fully rejected batch
as rejected when carrying its correction across a mandatory size transition,
without representing unexecuted mutations as completed or weakening limits,
idempotency or native-history validation. That fix and any new paid allocation
were not performed here.

## Resource accounting and limits

| Row | Generation / counts | Input / cached tokens | Output / reasoning tokens | Active seconds | Committed segments |
| --- | ---: | ---: | ---: | ---: | ---: |
| A1 | 35 / 38 | 1,343,178 / 830,336 | 96,242 / 82,398 | 796.533 | 5 |
| B1 | 29 / 30 | 1,097,314 / 742,144 | 40,919 / 31,108 | 426.861 | 3 |
| B2 | 25 / 28 | 1,019,479 / 718,976 | 69,623 / 61,023 | 479.659 | 3 |

Usage receipt pricing reconciles exactly: uncached input USD 0.87638625, cached
input 0.17185920, reasoning output 0.78538050 and other output 0.14514750.
A1's last response used its reduced 8,141-token ceiling entirely on reasoning and
ended `max_output_tokens`; the next minimum request could not fit its row cap.
This settled incomplete response is separate from B2's local continuation failure.

Maximum **dispatched** input tokens were A1 58,210, B1 59,103 and B2 58,796.
Larger counted candidates caused transitions or the stop above; they were not
sent for generation. No cap, transition rule, two-reference rule or validation
requirement was relaxed. No additional paid calls, patch evaluations, Docker image
pull/build or post-stop solve was performed. The implementation test receipts do
not imply live-model uptake or repair quality, and this report adds no such claim.
