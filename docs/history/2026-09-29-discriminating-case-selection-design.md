# Discriminating-case selection: prepared diagnostic

Following the [public replay](2026-09-29-boundary-discrimination-replay.md), test
whether an agent selects evidence that can falsify its candidate's applicability
condition. The prior boundary-pair instruction increased explicit examples without
reliably selecting such evidence. This is a selection diagnostic, not another
full-run quality experiment. Live execution is NOT_RUN pending a new exact cap.

## Fixed inputs and intervention

Use each A1 run from C:/pt/boundarypair0928b, immediately before its first run_check
decision. The patch has already been applied, but no check/probe observation has
occurred. The seam was chosen to hold a concrete candidate fixed while measuring
selection before verification; it is not before the first edit. H's first patch
alone was incomplete, so a pre-first-edit seam would test a different question.
Retain the actual native model input, including earlier public inspection, plans,
notes and opaque reasoning continuation. No future action, final evaluator feedback
or investigator counterexample is appended.

Exact dev-train task packages:

| Case | Task | Version |
| --- | --- | --- |
| P | pydantic-ai-synthetic-tool-reasoning | 1 |
| H | hf-hub-xet-endpoint-propagation | 5 |
| F | fromager-recursive-orphan-removal | 1 |
| L | loguru-invalid-format-feedback | 3 |
| D | pdm-ignore-active-venv-resolution | 2 |
| G | pgmpy-stable-skeleton-order | 1 |

A/B share a request to choose one public verification action, state a concrete input
and requirement-derived expectation, and refrain from editing/submitting. B adds
only a generic falsification criterion: seek inputs satisfying the same code guard
while differing under the requirement. No example, target field, endpoint condition,
or expected bug is supplied. Existing tool definitions stay unchanged, including
their pre-existing general falsification advice. This therefore measures the
incremental effect of the more specific selection criterion, not falsification
advice versus none. Do not force a fabricated counterexample on correct candidates.

Two samples per arm/case = 24 responses. Alternate A/B order by case and reverse in
repeat two. All tasks were used before; F/L/G provide useful controls, but this panel
cannot establish transfer to new task families. Source state may anchor the model.
A targeted read can be reasonable yet leave a one-response outcome unresolved.

## Measurement and boundaries

Full rubric: [.agent/discriminating-case-selection.md](../../.agent/discriminating-case-selection.md).
Freeze anonymous public grades before opening arm mapping. Grade independent
expectation validity and whether the selected evidence could expose the specific
candidate condition separately from tool syntax and expected execution feasibility.
Keep non-discriminating examples, unsupported expectations, justified unresolved
reads, scope violations and incomplete responses distinct. Do not require matching
the operator's known counterexample. Successful controls expose invented-bug bias.
Same-investigator masking is not independent blinding; wording can disclose B.

Returned tools are collected only. Probe execution, setup correctness, reproduction,
repair and private acceptance remain NOT_RUN. An execution follow-up should first
freeze all selections, then use the registered probe path without silently repairing
model programs. L/D/G stdlib-only limitations remain visible and must be separated
from selection quality. No default adoption follows a positive selection result.

## Cost and validation

Proposed new cap USD 13, 30 minutes, exact credential
C:/Users/geonj/Documents/PatchLoop/.env, gpt-5.4-2026-03-05 xhigh, 25K output ceiling,
60K input limit. At the [official rates](https://developers.openai.com/api/docs/models/gpt-5.4)
reviewed 2026-09-29 local date (USD 2.50 input / 0.25 cached / 15 output per million),
full uncached reservation is <=USD 0.525 per response, <=USD 12.60 for 24 responses.
Collection rechecks pricing on its execution UTC date. Count before dispatch; no
SDK/protocol retries, resume, replacements or automatic follow-up. Count, transport
or billing uncertainty ends the whole invocation. Earlier allocations are closed.

The diagnostic reuses the existing response-only collector and adds no production
runtime feature. Preparation reconstructs each saved prepared request, verifies its
hash and equality to the actual delivered input, verifies no prior check/probe result,
then binds source journal/envelope, runtime, implementation, schedule and A/B requests.
Historical input counts are 23,186-49,912; new input counts are NOT_RUN until dispatch.
Preparation does not load credentials. Exact request and checkpoint identities are in
C:/pt/analyses/discriminating-case-selection-20260929-v1/packet.json, hash
sha256:39ac2525fb39d6964a6a90eae05af5c871a8d4c5209a277a11a6696c5cd8858a.
All 24 cells reconstructed and the frozen packet revalidated locally.
Focused projection/cap tests, shared collector tests and documentation checks passed
(47 tests); Ruff and diff checks passed. Shared collector tests cover no tool execution,
exact approval, uncertainty stops and no restart. These are local mocked checks, not
live provider or task-solving evidence.
