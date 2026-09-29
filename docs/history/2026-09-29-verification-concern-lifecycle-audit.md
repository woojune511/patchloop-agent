# Verification concern lifecycle audit

Date: 2026-09-29. Provider-free code/test/trace analysis following the
[cross-task audit](2026-09-29-cross-task-evidence-action-audit.md).
No runtime or prompt change; no paid execution or quality claim.

## Actual contract

| Transition | Implemented condition | Limit |
| --- | --- | --- |
| Register | Model emits upsert with null concern_id and nonblank statement, at most 400 characters | No automatic creation from failed checks/probes, external feedback, plans or open_question; no creation evidence required |
| Retain | Separate verification state survives focus changes, source-note expiry, empty updates and restart replay | Three retained items maximum; new entries can evict only currently resolved/dismissed items |
| Update | Existing ID preserves original statement; different statement becomes latest progress_note and clears decision | Repeating original/latest progress is a no-op; null-ID text duplicates are distinct entries, not deduplicated |
| Resolve | Existing ID, nonblank reason, prior completed successful current-diff check or healthy probe | Mechanical currency/execution validation only, not whether the result addresses this concern |
| Dismiss | Existing ID and nonblank reason | No supporting result required and reason validity not assessed; dismissal is not verification |
| Reopen | Retained resolution/dismissal becomes historical on a different diff; changed progress clears decision | An evicted closed concern cannot be reopened in active state; historical journals retain it |
| Finish | Normal scoped-diff and required-check conditions | Unresolved concerns and annotation errors do not block submission |

Integration details matter: only the first non-null memory_update in a tool batch
owns updates; later ones are ignored with feedback. Updates occur before execution,
so a check in that same batch cannot be cited to resolve a concern. Empty arrays
preserve state. Invalid concern annotations do not block the main action; validation
is independent of source-finding validation. The gateway restores journal snapshots
and applies the same turn once, preserving action recovery semantics.

Creation stores original statement and turn identity, not evidence_action_id or a
creation diff. A supplied evidence ID is unused for upsert/dismiss. Thus it is a
model-authored uncertainty, not a structured record attesting that a counterexample
was observed. All projected interpretations remain explicitly unverified.

## Resolution strength and weakness

The cited result must be a prior run_check/run_probe with matching action identity
and nonempty input hash. Both its workspace_diff_hash and output.diff_hash must
match the current candidate. Action status must be succeeded; timeout, deadline
exhaustion and cleanup failure reject resolution. A check requires passed=true;
a probe requires status=passed, integer exit_code=0 and no truncation. Old-diff,
missing, pending, failed or unhealthy evidence cannot resolve the concern.

No automatic transition follows from unrelated PASS or invalid probe output.
However, if the model explicitly cites an unrelated successful current-diff check
and gives a reason, the updater accepts resolution: it cannot establish semantic
coverage. A healthy probe with no useful assertion can likewise satisfy execution
admission. This is intentional advisory semantics, not a verified proof system.
Dismissal admits any nonblank bounded reason, including weak ones. Therefore
resolved/dismissed labels must not be interpreted as harness-certified correctness.

A provider-free direct characterization confirmed: empty updates preserve unresolved;
a successful unrelated regression can be cited for resolved; reason-only dismissal
is accepted. These are synthetic contract examples, not observed misconduct or a
claim that semantic coverage can be solved by another string check.

## What happened in the 45 audited journals

379 public decision turns include 298 non-null memory_update objects: 288 with
empty verification updates and 10 with nonempty updates. Five runs use the feature,
each with one upsert and one resolve. All ten updates are accepted; no dismiss,
capacity rejection, eviction or ignored nonempty update explains the target cases.
Counts include the previously stated historical-prefix/heterogeneous-setting limits;
5/45 is inventory use, not a controlled adoption or efficacy rate.

Using runs: Fromager, pgmpy, Pydantic, Loguru and pyfakefs, one each. Pydantic and
pyfakefs still fail isolated acceptance after their concern is resolved. This does
not prove the cited check failed its promised scope, but demonstrates that resolved
is not equivalent to complete task correctness. Most concerns restate intended
patch behavior and are closed with existing public-check PASS.

The problematic HF observation-repair B1/B2 and toqito follow-up emitted no nonempty
verification updates. Their missing concerns were never registered; they were not
registered then erased by focus change, rejected for capacity, silently dismissed,
or automatically resolved after unrelated PASS. This materially narrows the prior
hypothesis: the immediate gap is registration/use and subsequent judgment, not an
observed failure of concern persistence. Existing focus questions and plans are not
substitutes for the concern list and do not automatically populate it.

## Implications

Preserve the tested retention mechanics. Do not add more durable memory or stricter
submission gates on the assumption that a list was lost. First distinguish three
kinds of evidence: observed candidate mismatch, invalid/unfinished verification
program, and an untested hypothesis. They need different follow-up actions and
must not all become trusted failures.

For a later proposed improvement, the smallest useful requirement is traceability
from an observed question to its explicit disposition. Existing concerns can carry
that discussion, but making an unused list mandatory may only produce bookkeeping
and unrelated-PASS closures. Any structured registration should preserve origin,
candidate identity and observation/action reference where available; a semantic
claim remains model-authored. Resolution must explain the input/behavior correspondence,
and dismissal must remain visibly different from verification. These are design
criteria, not implemented changes or established quality improvements.

The current runtime already asks for such explanations, so simply repeating that
instruction is not a new causal intervention. A next offline diagnostic should test
whether actual discrepancies can be registered with correct provenance and kind,
without classifying setup/compile failures as candidate bugs. Only then consider a
bounded comparison of registration/use; do not bundle new gates or task repair hints.

## Source, validation and evidence

- patchloop/dev/verification_concerns.py: _VerificationUpdate, _effective_status,
  project_verification_concerns, _resolution_evidence, update_verification_concerns.
- patchloop/dev/tools.py: record_working_notes_update, _restore_working_notes,
  verification_concerns, ready_to_submit.
- patchloop/dev/model.py: concern instructions explicitly separate focus, verification,
  dismissal and non-blocking submission.
- patchloop/dev/model_state.py: compaction keeps concern items/status/evidence while
  removing constant explanatory text and turn metadata.

65 existing concern, identity and gateway-flow tests passed, including persistence
through edits/focus/expiry, invalid evidence rejection, capacity, dismissal, restart,
parallel ownership, finish with unresolved concern, and mock isolated evaluation.
No production edits required; documentation-layout tests and diff checks are rerun.

Immutable usage/characterization report:
C:/pt/analyses/verification-lifecycle-audit-20260929-v1/report.json,
with source journal hashes for the five using runs and a dev-run-v1 hash journal.
The 45-run source inventory remains in the prior cross-task audit. Provider calls
and new task executions are zero; existing mock tests are local validation only.
