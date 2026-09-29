# Evidence-only versus surrounding context: provider-free preparation

Date: 2026-09-30. Four paired inputs prepared, no model calls, official=false.
Follows the [negative disposition result](2026-09-30-evidence-disposition-results.md).
Implementation: diagnostics/evidence_context_design.py; contract:
[evidence context design](../../.agent/evidence-context-design.md).

## Duplicate-work check

Two related diagnostics already exist; do not claim context reduction is a new idea.

- Pyfakefs row39 pre-turn32 fresh-state comparison collected four responses. Fresh
  inputs reduced counted tokens, but also changed continuation, repetition, source
  presentation and message structure. It did not isolate a cause or establish a
  better repair. See the immutable [snapshot](2026-09-26-context-split/current-status.md),
  lines 9500-9542 and diagnostics/fresh_state_design.py.
- Pyfakefs row43 model/history factorial collected 16 responses. Both views started
  fresh; removing older state descriptions showed no repeated quality advantage.
  See the same snapshot, lines 7575-7638 and diagnostics/model_state_sampler.py.

Neither evaluated the current HF/AnyIO/tox observations with a common evidence
assessment question. Existing source reconstruction is reused, not a new collector.
All old approvals and artifacts remain closed/unchanged.

## Refined question and limits

Can the same public evidence support a correct applicability/coverage assessment
when separated from the coding workflow's surrounding context? Both A and B are
fresh, non-executing reviewers receiving the same question. A also receives original
instructions/tools as quoted data and selected current workflow state; B does not.
Neither is an exact original-loop control. The comparison would test a bundle of
surrounding context, not isolate a single prompt sentence or an internal model ability.

All four actual source requests already have five messages and zero reasoning items:
system, immutable task, user message, public evidence archive, current state. Thus
this design cannot test removal of encrypted continuation or a long native dialogue.
It also changes the task from acting as a coding agent to assessing evidence in both
arms. Do not compare future reviewer scores directly with old tool-choice scores.

If B improves while A fails, that would support a context-dependent discrepancy for
these views, not prove completion guidance caused it. If both fail, missing evidence,
review wording and interpretation remain competing explanations; intrinsic inability
is not established. If both pass, actual repair/submission ability remains untested.

## Sources and common evidence

| Case | Cutoff | Role in the diagnostic |
| --- | --- | --- |
| C1 | HF endpoint propagation v5, seeded B2 final | Current external mismatch despite registered PASS |
| C2 | HF v5, seeded B1 final | Historical observation after edits; no delivered exact rerun |
| C3 | AnyIO interrupt cleanup v3, N1B final | Historical setup failure distinct from lifecycle evidence |
| C4 | tox cross-section empty substitution v1, TA turn starting at journal sequence 71 | Current missing-default mismatch after a prior import failure |

Three dev-train tasks, four already exposed checkpoints; not a held-out benchmark.
C4 is a positive repair contrast from existing records, not another demonstrated
abandonment. Its saved probe uses direct imports and stubs to exercise current target
code. Preserve those limits. The later operator CLI result and the next agent decision
are outside the cutoff and are not supplied to either view.

Both views contain identical complete public tasks/check definitions, candidate
patches and IDs, public execution/check/probe records, external feedback, historical
evidence archive and materialized observed current source. No new source read is
added. C1 had no retained source bodies; the diagnostic does not fill that gap.

The tox latest-probe entry references the preceding output rather than containing
it. That output and the probe program survive in the historical evidence archive.
Dropping the archive would lose the decisive observation while claiming to shorten
only context. Archive call arguments/results remain intact; only turn_decision prose
moves to A's surrounding context. This includes original model-authored claims, not
new answer hints. Scoring/selection labels are separate from all model-facing views.

Only working_plan, working_notes, completion_guidance, commitment_signal,
action_horizon, remaining_budget and available_tool_names move out of current state.
Registered verification observations inside working_notes also remain in both views.
Every other state field stays common, including mutation results and records that mix
facts with advice. This conservative extraction does not eliminate every framing cue.

## Frozen packet and verification

Current packet: C:/pt/analyses/evidence-context-preparation-20260930-v2/packet.json

Hash: sha256:cf2a1ce2956235f3683db86faaa18273e288caaaf55a80fedb754cd037b83e0c.

V1 is preserved, superseded before any execution: the initial evidence-field allowlist
was widened to retain all state except seven explicitly selected context fields, so
mutation-result facts were not accidentally classified as disposable workflow context.

| Case | A data UTF-8 bytes | B data UTF-8 bytes |
| --- | ---: | ---: |
| C1 | 85,276 | 42,305 |
| C2 | 143,327 | 102,111 |
| C3 | 147,026 | 95,927 |
| C4 | 93,222 | 44,836 |

These are serialized data-body bytes, excluding the identical reviewer question;
they are not input token counts or model-performance measurements. Check code,
source and archive retention intentionally take priority over maximum compression.

The eight derived views are hash-bound CAS artifacts in an external dev-run-v1
journal. Validation reconstructs original state and archived argument objects,
checks equal evidence within pairs, and verifies the four original requests against
their active model inputs. Eight source journal/envelope files stay byte-identical.
Five new preparation tests plus 28 existing source-design tests pass; Ruff passes.
Documentation-layout and diff checks accompany this change. Production runtime,
full suite, Docker, tool/evaluator smoke and provider calls are NOT_RUN.

## Next decision

The requested provider-free duplicate check and input preparation are complete.
No live collector, model/repetition/cost grant or dispatch capability is added.
Review the evidence-preservation boundary before any paid design. If live testing is
later requested, freeze model/settings/repeats/cap and the same evidence-support rubric
for both views, with missing evidence allowing uncertainty. Keep the runtime baseline;
this packet does not establish an interpretation failure or a context improvement.
