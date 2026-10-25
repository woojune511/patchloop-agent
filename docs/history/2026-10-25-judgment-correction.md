# Captured-output judgment correction

Date: 2026-10-25. ARS experiment-agent / implementation and local validation.
`official=false`, `claim_eligible=false`. No provider, real Docker or live task
evaluation is part of this change.

## Problem and decision

The [resource pilot](2026-10-25-completion-resources-live.md) captured F0010 on the
original caller's stdout but authored a false observation by checking only stderr.
Both the raw capture and false JSON reached the model. Its subsequent notes treated
the failure as absent; 26 source inspections produced no edit. A later 25K protocol
correction also exhausted. More delivered text or nominal recovery money did not
repair the earlier interpretation.

This was selected because the missing capture-to-verdict connection corrupts the
repair premise before the newly implemented candidate diagnostics can operate.
The checked source compared authored JSON with expected/failure JSON, but did not
derive that authored value from the captured evidence. The proposed intervention
is deterministic consistency calculation followed by bounded baseline correction.
Capture loss would weaken this explanation; the live receipt and next-input audit
already showed complete per-call stdout. The selected diagnostic/caller can still
be semantically wrong even when extraction is mechanically consistent.

## Implemented

- `probe_judgment.py` and the fresh purpose schema bind up to four literal rules to
  explicit calls/boolean fields. The host checks stdout and stderr separately,
  derives JSON and records match witnesses. Unknown capture never means absent;
  disagreement retains authored/host values and confers no comparison credit.
- `observation_correction.py` permits one explicit changed extractor on the
  unchanged base. Frozen declarations and actual v4 caller/input/environment
  identity must agree. A correct baseline must reproduce the declared failure.
  Rejected starts spend the opportunity; exact recovery never redispatches.
- The runner and gateway block source exploration/mutation/finish during known
  contradiction. Actual dispatched and compacted state retains the judgment proof
  and bounded original program/request, so the extractor remains editable.
  A failed or unfunded correction returns VERIFICATION_INCOMPLETE. Existing
  transport/count/billing uncertainty keeps its primary terminal.
- A verified correction links action/case versions and excludes only the proved
  faulty judgment from active completion accounting. Its immutable receipt remains.
  Corrected candidate replay is ordinary replay and finish reuses current results.
- Findings/questions citing old judgments require revalidation; statements are
  preserved. A diagnostic conflict/unknown cannot resolve a verification concern,
  and superseded resolution evidence reopens that concern in the current view.
- Completion forecasts charge one correction model/probe action and the future
  corrected-case replay, then retain the minimum repair/check/finish path. Protocol
  correction allowance, overall caps and output defaults remain separate.

The implementation is documented in [the contract](../../.agent/observation-judgment.md).
Tool-surface identity advances from v54 to v55; old null/absent-field bindings and
observer program bytes retain their prior meaning. Existing live runs cannot be
resumed against changed runtime identities.

## Validation and interpretation

The focused owner selection is `tests/judgment-correction.txt`: host calculation,
lineage, gateway/runner transitions, memo currency, resource boundaries and exact
recovery. It includes an actual local per-call capture through a trusted adapter,
then conflict, corrected baseline, repair, candidate replay and finish. Another
scripted runner stops after two requests when correction remains inconsistent.
The fixture wraps a public CSV behavior to emit a diagnostic; this is local
mechanism evidence, not a model-generated Astroid repair or an independent task
acceptance result.

The 56 focused tests passed within two minutes; their exact duration was not
captured. A later dispatched-state test passed after adding the original request
projection (4.27 s). A separate output-exhaustion test passed (3.48 s), verifying
VERIFICATION_INCOMPLETE while retaining INCOMPLETE_RESPONSE as the stop cause.
The final fast suite passed 309 tests in 31.18 s (32.54 s process time), and Ruff
passed. It includes the existing isolated mock-evaluation smoke; mock safety is
NOT_RUN. Documentation checks and the final commit are bound in the external receipt.

The initial fast attempt passed 298 tests and failed 11 current schema-hash
snapshots. Removing only the new fields and restoring the previous purpose
description reconstructed every old digest. Only current expectations were
updated; frozen historical expectations remained unchanged. The 11 affected nodes
then passed (2.76 s). The initial failure is retained as `validation.json`, and
the final fast result as `validation2.json` under `C:/pt/judgment-local-v1`.
Runtime-bound inputs, command output and finalization are preserved there in
hash-chained dev-run-v1 journals and CAS. Final runtime identity is
`sha256:d4c94133e80b3bd6bc8df8a0bcbd6aecb2d2f57f4d9bc62f5f8f3e3fcf290bc7`.

The result changes the local contract: a known diagnostic contradiction must be
corrected before repair planning proceeds. It does not establish useful model
uptake, repair gain or generalization. `diagnostic_rules=null` retains the previous
arbitrary-value path and cannot promise semantic consistency. Action-level note
links identify revalidation scope, not proof every referenced sentence is false.
Separate setup-failed cases remain unverified rather than being automatically
retired; therefore a corrected conflict alone need not make all-case reuse eligible.

Next question is whether the model selects the structured diagnostic contract and
uses the immediate correction to establish a useful baseline under the unchanged
live budget. No new paid run, continuation, target evaluation or cap increase was
executed or authorized by these local tests. Historical pilot records remain intact.
