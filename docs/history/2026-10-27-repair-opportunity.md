# Preserving a diagnostic repair opportunity

## Material Passport

Date: 2026-10-27. ARS implementation and local validation follow-up; official=false.
Public source and scripted local fixtures only. No new paid experiment or repair
claim. Historical runs and their unresolved billing remain unchanged.

## Problem and decision

The [source-ready run](2026-10-27-source-ready-repair-live.md) retained the exception
packet, 148 public source lines and valid edit anchors. The model identified a
possible stream/tokenization mechanism but spent all twelve actions on inspection.
The operator's separate remaining-probe and mutation quotas did not reserve an
executable opportunity. Its already-fixed zero-action dispatch defect is distinct.

The ordinary runner already protects completion resources. The minimal intervention
belongs in the smaller seeded diagnostic operator, not another product-wide or
F0010-specific stage. This matters because an action-starved experiment cannot
distinguish choosing a poor repair from losing the chance to make one.

## Implemented scope

`source-ready-opportunity-v1` is an explicit new profile in
`diagnostics/exception_frame_repair.py`. The old information-pair and source-ready
profile requests remain unchanged. Same source, model settings, output/input limits,
eight normal responses, one correction, twelve actions, one probe and one accepted
edit apply. No model-authored hypothesis or extra diagnostic evidence is supplied.

- Before a probe, inspections preserve two tool actions and two normal responses
  for probe then edit/stop. After a probe, they preserve one. Direct edit/stop is
  always eligible when a funded response and action remain; no edit is forced.
- One pure calculation controls the model-visible opportunity, offered tools,
  maximum parallel inspection batch and validation of the returned batch.
- A correction can perform an action without spending another normal response.
  It cannot consume the successful successor's reserved cost. Invalid output and
  executed/rejected tools do not renew any allowance.
- Exact count precedes dispatch. Inspections reserve two future full normal
  allowances while the probe is unused, plus the unused correction allowance.
  Cost pressure first closes inspection, then if necessary closes the optional
  probe, rebuilding and recounting each narrower request at most once. Uncertain
  counting/transport/billing still stops all work.
  The prepared first-request hash binds the first counted input. If narrowed for
  cost, the first generation uses a separately recorded request/hash, as prescribed
  by this profile; it is not reported as the unchanged prepared input.
- Source preparation, one-edit termination, frozen original/control replay and
  public regression checks retain the existing implementations. Host checks use
  their separate existing deadline; they do not consume model decision slots.

This reserves a successful-path resource opportunity, not valid output, a useful
probe, enough wall-clock time, additional recovery, or a correct repair. Fewer
inspection opportunities may cause a justified stop or a premature hypothesis;
those are outcomes to measure, not reasons to force a patch.

## Local evidence

Focused operator/opportunity/source-packet/documentation validation passed 51 tests.
Quick passed 472 tests, including isolated mock evaluation. Ruff and diff checks
passed. Scripted cases cover ten reads then probe/edit, six one-read responses then
probe/edit, excessive parallel reads rejected before execution, correction at the
last response boundary, both cost reductions, voluntary stop, and uncertain recount
stopping before generation. These are mechanism tests, not actual model uptake.

Local receipt: `C:/pt/repair-opportunity-local-v1/runs/run_dev_repairopportunitylocal.jsonl`.
The three historical first-request payloads (A/B and source-ready B) were compared against their saved
JSON artifacts and remain identical. The new profile preserves every original
source-ready message and adds only its resource/opportunity projection at the
initial request. No credential, provider or target execution was needed for that
comparison.

## What to compare next

Request structure versus model settings is already a valid next question. It does
not need to wait for yet another successful repair under the current model. The
previous results establish delivery of useful evidence and some mechanism uptake;
they do not prove that every fact needed for the correct repair was supplied.

Use the opportunity policy as a fixed common condition for these comparisons.
It changes action selection and is itself an intervention, not a neutral cleanup
whose effect can be silently attributed to a model or prompt. A reservation-effect
comparison, if separately desired, would be a different question.

Hold the saved candidate, public information, source anchors, tools' capabilities,
repair/check horizon and declared resource policy fixed. First compare request
representations with one model configuration; separately compare one model-setting
factor with one request representation. A full two-by-two design can later identify
an interaction, but no arms, model changes, repetitions or paid budget are authorized
by this implementation. Any different price/admitted output across models must be
reported rather than described as identical compute.

Measure valid targeted probe, edit, original-call failure resolution, unchanged
control and public regression separately. An edit is not success; this seeded
development case cannot establish independent acceptance or general repair quality.
If preserved opportunities still produce uninformative probes or wrong repairs,
that weakens the opportunity-loss explanation and directs attention to action
selection, request burden or the selected model settings without adding more gates.
