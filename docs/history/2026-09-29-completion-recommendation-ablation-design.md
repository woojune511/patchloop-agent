# Latest completion recommendation: frozen diagnostic

Date: 2026-09-29. Prepared, live NOT_RUN. Follow-up to the
[decision audit](2026-09-29-observation-decision-audit.md); no runtime default change.
Contract: [completion recommendation ablation](../../.agent/completion-recommendation-ablation.md).

## Question and controlled change

B2 retained an external current-candidate counterexample but selected the remaining
registered check after the first PASS, despite ample resources and offered inspection.
Does the latest computed action recommendation contribute to that choice?

Use exact B2 turn two, after xet-endpoint-contract PASS and before the next decision.
A preserves its saved request. B only removes latest completion_guidance.next_action
and the imperative recommendation to run upstream-xet-regression. The original
statements about diff currency and submission eligibility remain. System prompt,
public task/check definitions, counterexample, plans, tools, budgets, earlier native
history and opaque encrypted continuation remain identical. No added reminder to
notice the counterexample. This isolates the latest recommendation, not earlier
instruction effects, the horizon labels, or all completion-oriented language.

The source model request hash is
sha256:8cbe81fbe17049de6daaffd910f5c280e8b50d462f899d812c5768b576e40efa;
source turn turn_4ad4bf0a34d448d7a4c7b0a4d71f3d5e in run_dev_21504b465fd94901.
The sampler verifies actual active input equality and the prepared request binding.
Reconstruction verifies that no other state changes; the native prefix is untouched.
The existing tested decision sampler counts and collects responses without running
any requested tools. This is a local diagnostic, not a fresh solve or repair run.

## Exact proposed execution

Task hf-hub-xet-endpoint-propagation v5, dev-train; model gpt-5.4-2026-03-05,
xhigh, maximum 25K output / 60K input; credential
C:/Users/geonj/Documents/PatchLoop/.env. Three samples per arm, six total in
A1 B1 B2 A2 A3 B3 order. NEW invocation cap USD 4 and one 1800-second deadline.
The closed USD 8 allocation does not carry over. No SDK retries, correction calls,
replacement, resume, Docker, tool execution or evaluator execution. All repetitions
stop on count/transport/billing uncertainty. Exact paid authorization is pending.

Official GPT-5.4 pricing reviewed 2026-09-29:
https://developers.openai.com/api/docs/models/gpt-5.4
USD 2.50 input, 0.25 cached input and 15 output per million tokens at this context
length. Six no-cache full-ceiling reservations sum to USD 3.15. The USD 4 cap is an
admission ceiling, not an estimated bill. Refresh prices on execution UTC date.

## Frozen assessment and limits

Score explicit recognition of the supplied unresolved discrepancy and selection
of a targeted public read/search/probe capable of resolving it, separately and
jointly. Generic additional work, prose length or repeating unrelated checks does
not count. Preserve invalid/incomplete responses and public-grounded challenges to
the diagnostic's applicability. Record response-only judgments before revealing
arm labels when using collector review packets; no blind-review claim.

No returned action has executed. Task acceptance and safety remain NOT_RUN.
Six same-checkpoint samples cannot establish generalization or reliable repair.
A null result cannot exclude effects already carried in the unchanged history.
No new gate, concern structure, or task-specific hint is bundled into this comparison.

## Preparation and validation

Frozen packet:
C:/pt/analyses/completion-recommendation-ablation-20260929-v2/packet.json
Hash: sha256:7d9e7a0fbaf21b48a85d10ee10b21314b34328a73f1a4abb92a23ff56e56c019.
Source and implementation/runtime/price/request hashes verified; six cells load.
Preparation made zero provider calls and read no credentials. V1 remains preserved,
superseded only because Ruff line wrapping changed its implementation hash; no
provider execution occurred there either.

Four new tests plus 39 shared collector tests passed, including exact projection,
wrong-checkpoint rejection, reservation arithmetic, cost/uncertainty/deadline stops,
no sampled mutation execution and no resume. Ruff passed after formatting fixes;
the four new tests were rerun. Documentation-layout and diff checks are run for
this change. Existing shared mock collector coverage is appropriate here; task
repair/submission/evaluation behavior is unchanged and not executed by this sampler.
