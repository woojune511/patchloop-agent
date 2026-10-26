# Captured failures, compact finalization and bounded completion funding

Status: implemented and locally validated; official=false. No new paid or target
Docker run. Runtime baseline 0e3d8785001d4766634713afb42561b0509523c2;
implementation started from docs-only HEAD 1cb740c4fbdbf4af9610ef7e952e9f9efc28d07a.

## Problem and decision

The [revision pilot](2026-10-26-repair-revision-live.md) observed a replacement
FileNotFoundError, but final public inputs had UNKNOWN and no current failure.
The [budget analysis](2026-10-26-revision-budget-analysis.md) also found large
final contexts, no-action responses under 4,677/4,157 output ceilings, and repeated
inspection after complete original-call observation. These affect repair feedback
and reliable completion, independently of any total-cap increase.

Whole-case UNKNOWN remains correct when the observation is incomplete. The defect
was losing positive evidence that one selected call actually raised. Separate this
fact from equality credit. Larger caps or lower reasoning effort could change a
trajectory, but cannot restore omitted evidence. Repeated reads can answer real
questions; zero new source lines alone does not justify banning inspection.

## Implementation

- Preserve bounded call outcome, capture status, exception and exit code. A
  current unexpected exception becomes `target_failure` only against a qualified
  original root with identical binding and selected-call inputs/environment.
  Global incomplete/UNKNOWN remains visible. Expected exceptions, SystemExit,
  changed conditions and execution uncertainty do not gain this credit.
- Deliver the exception as current failure, route to repair, and block finish
  independently in runner and gateway. Reuse the existing finite diagnostic slot;
  do not reset replay, acquisition or correction accounting. Same-candidate PASS
  cannot erase a captured exception; new candidates require new evidence.
- Use a compact finalization view and a fresh segmented handoff on entry or
  no-action correction. Retain actual patch, public task, check verdicts, original
  outcomes and unresolved notes/plan; omit old source/probe bulk while preserving
  retrieval identifiers and offered tools.
- Within completion-recovery-v1, reserve a finalization output floor of 8,192,
  clipped to the ordinary ceiling. Other ordinary successors keep 128; the first
  correction keeps its separate ceiling. Ready optional continuations fund both
  current and future decisions. Closing finish uses exact counted input. No
  invocation cap, normal/correction ceiling, model/action or mutation limit rises.
  This floor is an engineering allowance, not a measured sufficiency threshold.
- Connect complete current first observations to delivered source ranges, actual
  inspection questions and recent zero-coverage receipts. Keep this advisory;
  introduce no mandatory prose, new tool or fixed exploration ban.

Tool surface v61 and the exact cost contract bind the change on resume. Frozen
observer programs and action/input recovery identities are preserved.

## Evidence

The core selection `tests/completion-feedback.txt` passed **98 tests in 35.66 s**
(37.02 s including startup). It covers real local target exception capture,
current feedback/finish refusal, uncertain/changed/expected cases, bounded replay
recovery, compact source omission, no-action segment recovery, fixed-cap funding,
and independent correction/test-revision reserves. Scripted provider fixtures
exercise request delivery/admission; they do not measure actual model quality.

During development, a test caught the missing completion correction in the full
context builder. It was added before the passing segment/recovery checks. Fixture
expectations were also corrected for qualified exception names, candidate patch
state and the intentionally larger finalization reservation. Earlier observations
are recorded separately; no old experimental artifacts were rewritten.

Offline reprojection of the closed public journal recovers exactly one
`builtins.FileNotFoundError` for `src/project/__init__.py`, with complete selected
capture and same selected-call inputs/environment. Whole-case evidence remains
UNKNOWN. The new runtime would require repair for that candidate.

Separately projecting the legacy ready states at calls 36/37 reduces serialized
public-state bytes from 100,545/100,943 to 44,667/44,428 while preserving patch,
check verdicts and original review. This is a projection measurement, not token
or cost savings, and the corrected failure gate would not put this particular
candidate in finalization. Calls 27/28/30 also produce bounded source/question
reuse packets without reading target files or executing the model.

Evidence root: `C:/pt/completion-feedback-v1`; append-only journal
`run_dev_completionfeedbacklocal`. Public reprojection artifact hash:
`sha256:694d68f9841cd8631d3b158fc2b448ae4fdc933f95a8d4cccb1cd98e2e5247c8`.
Runtime content hash:
`sha256:3a7fd37953ffeee6074c53f93ebc315ebe4a77673c9dc40b1645480c9082a1f0`.

Quick returned **415 PASS / 1 FAIL in 36.29 s**; only the guide's 16KB byte bound
failed. The guide was shortened without raising the bound. Focused documentation
and changed contract pins then passed **9 tests in 0.99 s**. Those extra checks
also found stale pre-existing schema/prompt pins in two older owner tests; their
unchanged schema/prompt source was checked before refreshing current pins. Frozen
historical-arm pins were retained. This is split verification, not one fully
rerun quick invocation. Quick's isolated mock evaluation passed. Ruff passed.
The raw results, including failures, remain in the same validation journal.
No hidden tests, reference patches, evaluator internals or provider reasoning
were used. The user AGENTS.md change and unrelated temporary directory remain
untouched. No dependency/image pull/build or credential access was needed.

## Remaining question

The evidence supports the feedback/projection/admission mechanisms. Actual-model
use, fewer inspections, useful finalization output, F0010 repair and general gains
remain unverified. The next informative measurement is a separately frozen fresh
solve under the same task/model/40K/25K/$1.20 scope; a higher-cap comparison should
follow only if the corrected mechanism still leaves a measured funding bottleneck.
The prior live allocation stays closed; this work does not create a new one.
