# Prior-decision ablation: collector and scoring ready

Follows [input preparation](2026-09-30-prior-decision-preparation.md). Provider-free
implementation/verification only; no new paid collection has occurred.

## Fixed comparison

New A retains the ten prior public decision objects in the previous reduced-context
views; new B removes only those objects. Other framing, task/source/check/probe
evidence, question and output schema remain fixed. Both arms need fresh responses.
The four dev-train checkpoints are the same two HF v5, AnyIO v3 and tox v1 snapshots.

`diagnostics/prior_decision_sampler.py` binds the prepared views to 16 responses:
A/B twice per case, paired AB/BA order reversed on the second repetition. It reuses
the existing report schema/parser and shared cost/dispatch engine without modifying
them. gpt-5.4-2026-03-05, xhigh, 60K maximum input / 25K maximum output, 30 minutes,
exact C:/Users/geonj/Documents/PatchLoop/.env, proposed new total USD 9 cap.
No tool execution, retries, corrections, resume, Docker, evaluation or paid grading.

The [new frozen scoring contract](../../.agent/prior-decision-sampler.md) references
the previous case-specific rubric and explicitly resolves the observed ambiguities:
recognizing a relevant HF discrepancy need not assert conclusive task failure;
report a stricter sensitivity for applicability-uncertain borderline passes; AnyIO
setup omissions are not_assessable rather than incorrect beliefs. Grade masked
reports and save excerpts before revealing labels. No pooled solve rate or runtime
adoption claim. Removal still changes length and does not eliminate all framing.

## Verification

31 focused tests passed: collector 6, prepared views 9, existing report collector 11,
documentation 5. Ruff passed. Tests cover exact requests/no chaining or actions,
count/transport/billing stop-all behavior, cap mismatch and input artifact tampering;
existing report tests cover malformed/incomplete output and continuation uncertainty.

Actual-input mock completed 16 responses/eight pairs. Every outgoing request hash
matched its frozen cell, with real provider creation, credentials and tool execution
patched to fail if reached. Source preparations revalidated after collection.
Mock usage/cost counters are simulated; actual API calls and new spending are zero.
Runtime unchanged; task/evaluator smoke not applicable to this response-only wrapper.

## Frozen records and next boundary

- Input packet: C:/pt/analyses/prior-decision-preparation-20260930-v1/packet.json,
  SHA sha256:4382e95030d986ed2112d0ece9783083517422e9b17bf0693f2cce33b1f9fb0b.
- Collection plan: C:/pt/analyses/prior-decision-collection-plan-20260930-v1/packet.json,
  SHA sha256:404dd4f98077ba3b18c6b45a16baaea8570d595e2516d033285b39eebf0d5274.
- Sampler content set:
  sha256:a8f6484ade56c883f4edc14b31fcbce14b7e9a7eb3fa8b99ef43ecb2159fb105.
- Actual-input mock: C:/pt/analyses/prior-decision-collection-mock-20260930-v1,
  run_dev_sample_c4ef4d63fca048bf.
- Plan journal: run_dev_priordecisionplan; request artifacts and offline receipt frozen.

Official Standard pricing rechecked 2026-09-29 UTC: input USD 2.50/M, cached USD 0.25/M,
output USD 15/M. Full maximum reservation USD 0.525/call, USD 8.40 for all 16 calls.
[Pricing source](https://developers.openai.com/api/docs/pricing). Recheck on execution
UTC date if it changes. Proposed output root C:/pt/priordecisions0930a must be fresh.

Approval NOT_GRANTED; no live approval file created. Prior budgets remain closed.
The next action is an exact approval for this new USD 9 / 16-response scope; neither
preparation nor successful mock authorizes live calls.
