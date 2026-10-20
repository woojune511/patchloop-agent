# Seeded selected-test diagnostic preparation

Date: 2026-10-03. Provider-free preparation; official=false, claim-ineligible.
Follow-up to [selected public tests](2026-10-03-selected-public-tests.md).

## Problem and question

The saved SQLFluff 1625 A1 patch passes the public issue examples but fails an
existing public CLI test. B1 passes those particular checks. Operator replay proved
the new optional `run_tests` tool can expose the regression; it did not establish
that the agent chooses the check or acts correctly on its result. That distinction
affects task correctness and justifies this bounded diagnostic.

The leading question is autonomous verification selection. Plausible alternatives
are failure interpretation, repair quality and failure to recheck an edited diff.
Delivering the exact CLI node would bypass selection, so the agent receives only
the original public task, current source/diff, ordinary tools and the shared existing
seed notice. Operator criteria are kept out of model inputs.

## Prepared change and boundaries

[Frozen design](../../.agent/selected-tests-diagnostic.md) and
[driver](../../diagnostics/selected_tests_diagnostic.py) reuse the existing seeded
runner. Both runs have the same baseline instructions and resources; only their
starting patches differ. One seed consumes one of four mutation slots. The new
driver fixes order, limits, immutable inputs, stop-all behavior and post-run public
assessment. No runtime, task, evaluator, prompt policy or default was changed.

Proposed scope: A1 and B1 once each, `gpt-5.4-2026-03-05` xhigh, desired output
ceiling 25,000 tokens, USD 3 per run / USD 6 invocation, 40 calls, 100 actions and
1,800 seconds per run. Original private acceptance and safety remain separate.
This is a seeded diagnostic, not a fresh-solve comparison or tool-effect estimate.
The prior eight-run approval is closed; fresh exact paid authorization is pending.

## Provider-free validation

Preparation uses existing Docker images and locked offline dependencies, without
image acquisition, provider calls or new hidden evaluation. Exact-base workspaces
are independently reconstructed and saved seed hashes verified. Public controls:

| Starting candidate | Public CLI node | Two public TSQL examples |
| --- | --- | --- |
| Base | PASS | FAIL |
| Saved A1 | FAIL | PASS |
| Saved B1 | PASS | PASS |

Initial receipts are preserved at
`C:/pt/analyses/selected-tests-diagnostic-20261003-v1`. Inspection then corrected
the new controller's settlement interpretation: normal terminal records omit
`billing_state`; only uncertainty emits `UNKNOWN`. Runtime behavior was unchanged.
Final preparation is independently repeated at
`C:/pt/analyses/selected-tests-diagnostic-20261003-v2`; its packet binds the committed
driver/contract, runtime, task/model identities, source/dependencies and calibration.
The packet is created after commit, preventing a circular commit/hash dependency.

Focused seeded-run/tool integration: 72 passed, 1 Windows symlink skip in 79.33s.
After settlement tests were added: 27 diagnostic/documentation tests passed in
11.82s. Both scripted repair and preservation reach isolated mock acceptance PASS,
with safety NOT_RUN. Checks cover model receipt delivery, no operator hints, seed
slot accounting, frozen-scope changes, missing/mismatched approval and stop-all
on uncertain or over-cap results. Scripted choices are transport evidence only.
Ruff passed. Standalone mock smoke `run_dev_df3b159b1c5349e7` reached acceptance PASS,
safety NOT_RUN, zero provider cost (`C:/pt/stmock01`). The full repository suite
was not rerun for this diagnostic-only change; no runtime source changed.

## Decision and unresolved work

The inputs and discriminating public checks are ready for an exact two-run proposal.
No paid solver run, autonomous selection result, quality gain or adoption follows
from preparation. A1 must independently expose, repair and recheck the CLI mismatch
while preserving the examples; B1 must preserve the checked behavior. Missing
submission, final public verdicts, original acceptance and safety are reported on
separate axes. Review public action/result evidence after execution; no automatic
extra sampling or prompt change is authorized.
