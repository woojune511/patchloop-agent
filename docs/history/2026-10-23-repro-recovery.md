# Reproduction error recovery and completion funding

Material Passport: academic-research-suite / experiment-agent run; 2026-10-23.
Verification status: locally validated; composed full regression coverage. All evidence is official=false;
no paid provider, real Docker, held-out evaluation or repair-quality claim.

## Problem and decision

The [saved-run diagnosis](2026-10-23-repro-budget.md) found two rejected quote requests
counted as original attempts, action and annotation errors sharing a native result,
and an unchecked final edit after per-call admission spent verification money.
The obligation survived, but that did not produce recovery or completion. These
mechanisms matter because failed request construction can consume bounded acquisition
without executing the caller, and source exploration can leave no affordable check.

Implement three separable corrections. Keep opt-in acquisition and cost defaults
unchanged until live evidence justifies adoption. A simpler explanation remains
possible: the model may still choose the wrong caller, arguments or oracle after
correcting the request; the original trace did not establish those bindings.

Baseline HEAD: `4cbc1171c6e8141c907d2c2e9f6e1d97d79a518b`; prior implementation:
`119f08796e9690227fb67cde4567dd70ccdbf362`. Local protocol was frozen before the
integrated comparisons in `C:/pt/repro-recovery23-local`, journal
`run_dev_reprorecovery23local`; protocol SHA256
`ab0deff689d4f75482c3770e7b09eb6840d4abef48fc2149acc7984f470b7b95`.

## Implementation

Fresh native tool outputs carry the primary action result. Optional note and plan
receipts remain in `working_notes.last_update_result` and
`working_plan.last_update_result`, with current note IDs/lifecycle in their existing
state fields. Annotation rejection is nonblocking. Legacy native outputs remain
byte-preserved; their exact receipt-reference handling is retained.

`probe-stages-v1` records request acceptance/rejection, dispatch start and backend
return separately. `request_errors` is not `original_attempts`. The latter counts
durable dispatch starts, including an uncertain start; `original_execution_results`
counts confirmed returns. The dedicated acquisition phase permits two dispatches
and six total investigation actions, with a separate two-request-error limit for
original or unclassified requests. Helper request errors do not consume that limit.
One rejected request leaves both dispatch slots; two request errors release with
zero execution evidence. Release permits ordinary work, including later eligible
probes; it does not waive the original obligation. Healthy
unchanged-base failure alone acquires original evidence. Setup errors, helper PASS,
release and independent acceptance cannot create it.

Durable backend returns resume postprocessing without another execution. A dispatch
without a durable result stops with recovery uncertainty; a fresh backend exception
also stops immediately. Legacy unknown attempts reserve slots without being relabeled
as confirmed executions. Original journals and action/input identities remain intact.

Opt-in `completion-minimum-v1` requires segmented-v1. Existing model/tool slot
forecasts run first. Financial admission then removes actions whose successful minimum
successors cannot be funded and reserves the largest successor among the offered tools.
Each future call uses the existing conservative 60K uncached-input/128-output floor.
Actual input is still counted immediately before dispatch; ready finish can use exact
counting without a future reserve. Automatic rechecks and case replays retain their
tool slots. Protected slot forecasts are explicitly separate from recovery money.
Legacy per-call and completion-reserve contracts/defaults are unchanged.

Simply enabling the older reserve policy is not equivalent. With four funded calls
but ample real model/tool slots, its protected-recovery intersection offers only
edit/stop in the controlled state. The new policy also permits one affordable
investigation while reserving the successful successor. That local distinction is
why a new opt-in policy was added instead of changing the old contract.

The 128-token floor cannot guarantee a valid response, useful reasoning, successful
check/replay, further repair or submission. Failure triggers a new honest resource
assessment. This policy reserves the successful minimum path, not speculative recovery.

## Local controls

Use deterministic public CSV/probe fixtures and a pure state grid. No live model is
sampled. Compare the same scripted successful path, 40 model calls, 100 actions,
four edits and virtual USD 0.30 cap. Charge each synthetic response its entire output
ceiling and count every input at 60K. These are virtual charges, not API spending.

| Control | Observation |
| --- | --- |
| Wrong quote then corrected original request | Rejection: 1 request error, 0 dispatches; correction executes once and acquires the fixture failure. |
| Two malformed requests | 2 request errors, 0 dispatches; `request_error_limit`, unverified. |
| One request error then two executed setup failures | Both dispatch slots remain usable; no original evidence is acquired. |
| Interrupted dispatch vs durable return | Unknown dispatch stops; saved return resumes with zero duplicate backend execution. |
| Action failure/success plus note or plan rejection | Primary result remains independent across append/native-window/segmented and restart/handoff. |
| Per-call virtual funding | Output ceilings `[25000, 21666]`, virtual USD 0.299997; cost stop before check/finish. |
| Minimum-successor virtual funding | `[16154, 128, 128, 128]`, virtual USD 0.254421; required check and finish/submission reached within cap. |
| Too little funding or current original refutation | Honest cost stop; no ready-finish escape or verification upgrade. |

The scripted cost fixture deliberately uses synthetic provider/sandbox identity;
submission in that fixture is not independent task acceptance. Standard CLI mock
smoke on the final runtime separately reached `EVALUATOR_PASS`, safety `NOT_RUN`,
`unverified_delivery`: `run_dev_964a39227fc54c6e`, patch
`0528cda528c84257c62049bd27eb57e842c37d9d43761f02d787f40b8bb8755c`.

The first smoke enabled bounded acquisition with the stock mock script, which does
not perform that stage; it ended `PROTOCOL_VIOLATION` before editing. Preserve that
negative result. Acquisition uses dedicated scripted controls; standard smoke uses
its supported path. Initial broader checks also exposed diagnostic adapters that did
not forward the new receipt arguments and a preflight that rejected extension fields.
The runs were stopped, their logs retained, and those interfaces corrected before rerun.

Final runtime SHA256:
`2426912820c5a3d7aef7fed80041e8371e3c566970ac2ba3782d6f979dc05261`.
Its source inventory artifact is
`78f37569cd0562083fddf8473337db87326a2366ca21e7a1a1bd3b026418421d`.
Validation uses Windows/Python 3.14.5; Linux CI remains unexecuted.

| Final local check | Result | Seconds |
| --- | --- | ---: |
| New mechanism tests, four files | 65 PASS | 53.12 |
| Quick selection | 312 PASS | 457.10 |
| Existing diagnostic adapter extensions | 151 PASS | 372.17 |
| Full invocation | 5,741 PASS; 1 FAIL; 20 SKIP | 4,076.46 |
| Unmodified feedback file with short temporary root | 46 PASS | 8.77 |
| Composed coverage of 5,762 collected nodes | 5,742 PASS; 20 SKIP; zero missing or unresolved failures | — |
| Final documentation | 5 PASS | 0.26 |
| Ruff: patchloop, tests, diagnostics | PASS | 0.491 |
| Mock smoke | acceptance PASS; safety NOT_RUN; unverified delivery | 16.713 |

The focused validation remains below two minutes. Expanded suites exceed that
target and ran concurrently; their times are not a performance comparison. The full
suite was restarted with a 90-minute limit after checking the previous 4,137-second
run: the initial 30-minute limit was inadequate. Interrupted logs remain preserved,
and a partial execution is never counted as passing.

The full invocation's one failure occurred before check execution in
`test_diagnostics_precede_delivery_clipping_and_survive_native_restart`: creating
an artifact temporary file failed at a 264-character Windows path, although its
parent directory existed. Re-running the entire unmodified feedback file under
`C:/pt/r23cf`, retaining four workers and the same runtime/source inventory, passed
all 46 tests. No implementation or assertion change was needed. This supports a
temporary-root path-length limitation; it does not claim general long-path support.
The original failing invocation is preserved. Final coverage composes that invocation
and the short-root recheck, rather than claiming a clean full invocation. All 20 skips
remain unexecuted. Coverage artifact SHA256:
`98fc837d66ab37596e337f88bf5cb7498e687ae3f47097481e9453b653ce87ca`.

Retained final JUnit files live at `C:/pt/repro-recovery23-local/`:
`focused-final.xml` SHA256
`63b80b5cb5717eeec96b4c9b6b4ee848786612d518efcb82e42c203bd7dda7f1`, and
`quick-final.xml` SHA256
`90d73da5ac38333f16cd41b13285068c8afb9be3630b30136bec5393c9e45cb2`.
`full-bounded.xml` SHA256
`2818c4b84e511018ff49eca0af6853e828c5b40e5c1255c9ac5954e13e42f95c`;
`recheck-check-feedback.xml` SHA256
`45c26c0a8d617305f0b34cb88a7e9aa4788777c6e9e1e57efd5506d68db77fbf`.
The journal binds commands, frozen source inventories, logs and report artifacts.

## Interpretation and remaining question

These controls test protocol separation, accounting, recovery and monetary reservation.
They do not show that an LLM corrects its original quote/caller/oracle, stops unproductive
exploration sooner, emits a valid request at the output floor, or repairs more tasks.
No policy adoption or fresh paid allocation follows. The next unresolved question is
whether the same public failure can be faithfully bound and replayed in an authorized
bounded live comparison; all previous allocations remain closed.
