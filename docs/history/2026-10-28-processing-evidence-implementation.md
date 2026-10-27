# Processing evidence, fixture scope and pre-target attempts

Date: 2026-10-28. Status: IMPLEMENTED and LOCALLY_VERIFIED.
official=false, claim-ineligible. No model/provider/count or Docker execution.

## Problem and decision

The [latest normal-run analysis](2026-10-28-canonical-diagnostic-analysis.md)
distinguished three demonstrated defects. Removing F0010 by processing an empty
initializer did not establish child-file analysis. A generated cache included in
selected inputs changed call identity without changing the fixture. An earlier
invalid keyword failed before target entry but remained a verification case.
These affect repair correctness and verified delivery, so raising limits would
not address their causes. The user requested the three mechanisms and the bad
example be corrected, with short local verification.

Base: `7034fb13322f2298bcf7057d5340f60536716f1b`. The saved live and diagnostic
records remain immutable. No evaluator detail, hidden test or reference patch was
used or projected into coding-agent context. The positive signal in the new toy
tests is fixture-owned, not a task-specific runtime rule.

## Intervention

1. Fresh `invoke-declared-call-v7` diagnostic rules add `role=failure|processing`.
   Each selected call pairs expected failure=false and processing=true. The host
   derives both from complete per-call captures using existing code-token rules.
   Missing processing after error disappearance is a mismatch, not success or
   UNKNOWN. A single call/code cannot occupy contradictory roles. Silent targets
   can use null rules to observe actual returned/processed data and error state.
2. `reproduction_workspace()` and `reproduction_outputs()` create stable sibling
   roots. Input selection rejects overlap with the designated generated root or
   its ancestors. Real fixture bytes still determine identity; intentional warm
   caches are fixtures. There is no generic ignored-cache list or HOME exclusion.
3. The observer records `target_started` immediately before the declared call.
   Completion separates only proved, settled v7 pre-target attempts from case
   obligations. All linked actions must be complete and bound to the same request;
   malformed/no markers, legacy records, entered targets and uncertain receipts
   remain obligations. Excluded attempts keep identities, counts and immutable
   journal rows, and continue consuming existing action/acquisition/cost limits.
   No valid baseline still means the original task obligation is unverified.
4. Guidance replaces `target(['path'], option=False)` with a positional example
   and explicitly requires the inspected target signature. It replaces the
   all-negative desired example with positive-processing evidence instructions.

Wire identity is v65. Existing v1-v6 bindings, observer/program bytes and judgment
semantics remain unchanged; old live envelopes cannot resume on a new runtime.
No new tool, model call reserve, correction slot or increased limit was introduced.
Existing current-diff replay, failure feedback, bounded revision, checks and finish
carry the new observations. Request-attempt audit is visible in normal compact
completion state and final submission verification; small repair contexts retain
their existing focused projection.

## Local evidence

Evidence root: `C:/pt/behavior-local-v1` (`summary.json`, JUnit receipts and
hash-chained `runs/run_dev_processinglocal20261028.jsonl`). Runtime hash:
`sha256:1efe175d82fa407d1d91c144dfb9082f82e9052e3199bf0c224f563eaaeafca5`.
Tool surface: `sha256:5392aa6cba33742da80ad989dfc86dee28391261e4b25d743ba05179c17e113e`.

- Canonical/processing/normal-runner core: 35 PASS, 24.954s. The two normal
  continuations separately exercise changed error wording and loss of processing;
  both deliver the current failure to the actual prepared next request, revise,
  run public checks and finish. The missing-processing case also crosses a handoff.
- Observer + existing capture/workspace owners: 49 PASS. Maximum entrypoint plus
  call-path wrapper is 7,985 chars, within the unchanged 8,000-char host allowance.
  Independent comparison found six legacy observers and ten rendered normal/path
  programs byte-identical to HEAD. No old semantics were retroactively changed.
- Pre-target obligations: 16 PASS. A corrected baseline can verify and submit
  while preserving the earlier request attempt. No baseline, target entry, mixed
  calls, pending dispatch, absent flags and uncertainty cannot gain that credit.
- Quick: 568 cases / 159.286s, initially 557 PASS and 11 fixture failures.
  One synthetic legacy fixture mislabeled v5 receipts with the latest channel;
  one shared current fixture still emitted v6 code-only declarations. They were
  corrected without changing runtime or weakening assertions. Three failed nodes
  passed in a 23-case owner selection; the remaining eight passed in a 16-case
  selection (60.759s), including diagnosis-to-isolated-mock evaluation. The other
  isolated mock smoke already passed in quick. No second full quick run was needed.
- Current schema snapshots: 11 PASS / 1.429s after auditing the delta (run_probe
  role field and guidance only). Frozen hashes/branches stayed unchanged. Ruff
  PASS; final documentation layout and diff checks PASS.

This is split local validation, not a claim of one clean full-suite run. The
core selections stayed under two minutes; the existing broad quick selection
took 2m39s on this host. Provider/count calls, Docker calls and paid cost: zero.

## Interpretation and next question

This preserves the host canonical-judgment design while correcting observation
coverage and identity/accounting boundaries. The local intervention would be
unnecessary for a case already observing both intended processing and failure,
with disjoint fixture/output scope and no pre-target request errors; such calls
continue through the existing path.

A same-call positive code can still originate from an unrelated item. Rules and
null-rule extractors are model-selected evidence, not a semantic correctness
certificate. Input/output separation is explicit, not automatic filesystem
read/write inference; callers must classify intentional cache inputs correctly.
Local mechanism PASS cannot establish model repair gain, Astroid correctness or
held-out generalization. Live-model selection and use of discriminating evidence
remain NOT_RUN for this revision. No new paid execution is authorized here.
