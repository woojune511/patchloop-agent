# Pydantic evaluator contract audit

## Three questions and findings

1. **Do hidden assertions follow public requirements?** No contradiction was found
   in the inspected synthetic-tool-reasoning v1 package. The public issue explicitly
   assigns empty-field insertion to a provider-supplied profile, preserves that
   requirement when copied/reused, and exempts independently constructed plain
   OpenAI profiles. The private wire matrix tests those distinctions, renamed
   fields, send modes, existing content and tool identity/order. The two capability
   flows exercise ordinary and synthesized history across later requests.
2. **Is an unnecessary implementation mandated?** No new setting name, signature
   hash or source-patch identity is asserted. The evaluator compares emitted request
   behavior and uses existing public providers/profile overrides. Its synthesized
   flow also assumes existing tool-search names and auto_load_ identifiers; this
   is fixture coupling, bounded by the public requirement to preserve IDs/order
   and deferred exchanges. This audit does not prove every valid implementation
   would be accepted, but found no HF-style undocumented API extension requirement.
3. **Do calibration controls discriminate?** Fresh provider-free execution rejected
   the clean base and saved PA1 overbroad repair, while accepting the reference.
   The reference passed 84 wire cases and 8 local mock-response flow requests.
   Failures were serialization assertions, not infrastructure/setup failures.

The known PA1 condition-ownership error is independently supported by the earlier
[public replay](2026-09-29-boundary-discrimination-replay.md): it fixes required
provider behavior but also inserts an empty field for a plain same-field-mode
profile. That preservation requirement is explicit in public text. Unlike HB2,
the available evidence supports a real saved-repair defect; it does not establish
a general current-agent cause or select a prompt/harness intervention.

## Limits and decision

The hidden matrix has no explicit empty configured field-name case, despite the
public nonempty-name qualification. Its renamed-field case and reused-profile
case are separate, not a full cross-product. These are coverage limits, not proof
of an incorrect accepted patch. An empty-field-name preservation control is a
concrete candidate for future evaluator coverage, subject to baseline behavior
verification; this audit does not modify the task or retune its oracle.

Only three controls were freshly executed. The reference is the package's existing
reference, not an independently authored repair. This was direct hidden-command
calibration, not a new full isolated EvaluationEngine verdict or autonomous solve.
The recorded FAIL of other panel rows is not fully explained by one assertion.
Keep the task, runtime and historical verdicts unchanged. No evaluator replacement
or paid run is justified by this audit alone.

## Evidence and validation

New external hash-chained record:
C:\pt\analyses\pydantic-contract-audit-20261001-v1,
runs/run_dev_pydanticcontractaudit.jsonl. The protocol binds task/evaluator hashes,
base/reference/PA1 controls and expected outcomes before execution. Receipts bind
source diffs and complete sandbox outputs. PA1's original journal chain and saved
submitted-patch hash were checked before applying it to a new workspace.

Used the existing pinned evaluator image and prepared source through the normal
DockerSandbox registered-check path. All three checks completed without timeout
or cleanup failure. No network provider calls, credentials, image acquisition,
Docker startup, task-package mutation or original artifact changes occurred.
Private evaluator details remained operator-only; no coding agent was invoked.

Six package identity/integrity/projection tests PASS. Documentation layout/link/
size and diff whitespace checks validate this documentation-only change. Runtime
suite and mock smoke were not repeated; no runtime implementation changed.
