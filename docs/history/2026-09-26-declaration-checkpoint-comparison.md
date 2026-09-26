# Live post-search declaration comparison

Date: 2026-09-26. Four responses collected; `official=false`, `claim_eligible=false`.
Task acceptance and safety remain `NOT_RUN`.

## Problem and hypothesis

The selected failed Pydantic run sought the serializer and field mode without explicitly
investigating which profiles require empty reasoning metadata. The public task distinguishes
that applicability requirement from a field's format. The optional declaration expansion
delivers adjacent literal documentation using a generic source rule. The question was
whether that extra source changes the immediate public question after the original first
plan and searches, while retaining the existing interpretation and native continuation.

## Intervention and execution

The previously prepared packet was validated unchanged and collected once from code HEAD
`5a961978bdb94667e4beaf13fc75cb7776fb5a94`. Task was the exact checked-in dev-train
`pydantic-ai-synthetic-tool-reasoning` public package; model was `gpt-5.4-2026-03-05`,
xhigh. A restores the source request; B adds 12 public source lines and recomputes only
source-dependent state. Plan, notes, prompt, schemas, task/diff/checks, budgets and
continuation stay fixed. Core runtime remains `4d2fc8ba` / tool surface v45.

The user's instruction to proceed authorized A1/B1/B2/A2, each an independent next
response, under a $2.40 invocation cap. The exact root `.env` was used with reviewed
standard prices, count-before-dispatch and zero retries. All four responses completed;
two balanced blocks finished with no uncertainty stop or uncollected cell. Tools selected
by the model were never executed, and no Docker, evaluator, correction or later response ran.

## Public evidence and result

Anonymous decisions were reviewed and saved before reading arm mapping or per-arm usage.
All four proposed only reads/searches in `models/openai.py`:

- A1 sought the history serializer and whether one helper could insert the field.
- B1 sought shared ownership and distinguished receiving code from sending code.
- B2 sought direct/history mappers and whether one edit or coordinated edits were needed.
- A2 sought the same ownership/mode paths; its plan repeated plain-profile preservation
  but did not ask how applicability differs among profiles using field format.

Explicit format-versus-applicability investigation was absent in A 0/2 and B 0/2 public
responses. These are next-question observations, not failed repairs or acceptance scores.
Some code-location questions were concrete and could change the edit structure. No repeated
improvement on the target distinction was observed. The evidence ends at the proposed
action and its purpose: no new source answer, resulting edit or acceptance was measured.

## Cost and integrity

Recorded usage cost was $0.201923; repricing the same tokens without the cache discount
gives $0.331235. A totals $0.113337 / $0.162585 without cache discount; B totals
$0.088586 / $0.168650. Cache exposure differed, including uncached A1, so the cheaper
recorded B total does not establish an efficiency benefit. These are usage-based ledger
amounts, not an account invoice. The unused $2.198077 is closed.

The maximum input was 22,912 against a 60,000 bound; maximum output was 2,658 against
a fixed 25,000 ceiling. Collection active time was 78.409 seconds. Every input count
matched returned usage; canonical/ordered request hashes and the journal chain verified.
All 18 snapshotted packet/source/public-task files stayed unchanged. Post-collection
validation rechecked prepared source and opaque continuation without a provider call.
No hidden evaluator material or private reasoning was read for the behavioral review.

This follow-up changes documentation only. Five documentation layout/link tests and Ruff passed;
core tests and mock smoke were not rerun because executable code did not change.
The preceding implementation's local and mock evidence remains separate from live results.

## Decision and unresolved question

Keep declaration expansion optional; this selected checkpoint does not justify default
adoption or an automatic longer comparison. It does not prove eventual failure or a
general absence of benefit. The next mechanism must address testing a proposed repair's
applicability against preservation requirements, beyond delivering more source text.
Whether the fixed first plan anchors the later question remains unresolved; the experiment
held plan and continuation constant and therefore does not isolate their causal role.

## Evidence

- Contract: [checkpoint sampler](../../.agent/declaration-checkpoint.md).
- Prepared packet: `C:\pt\analyses\declaration-checkpoint-20260926-v1` (unchanged).
- Live run: `C:\pt\declcheckpoint0926a`, `run_dev_sample_832b9a505af545cc`.
- Report, blind assessment, usage/request audit and closure:
  `C:\pt\analyses\declaration-checkpoint-live-20260926-v1`.
- Implementation evidence: [frozen declaration decision](2026-09-26-declaration-checkpoint-sampler.md).
