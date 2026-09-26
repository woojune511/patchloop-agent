# Independent candidate generation and comparison

Date: 2026-09-26. `official=false`. Implementation commit: `22dc9e3`.

## Problem and hypothesis

Saved candidate reconsideration repeatedly passed registered checks and submitted
incorrect patches. The previous public audit identified Pydantic's broad field-mode
activation and HF's missing probe dependencies. Earlier fresh full-model Pydantic
success made candidate anchoring plausible, without establishing it as the cause.

Test whether a separately generated alternative helps the ordinary repair loop find
a behavioral difference, choose a distinguishing public check and improve its repair.
Keep the core model/runtime fixed and count generation in the method's cost.

## Change and validation

The optional seeded diagnostic accepts an exact public alternative patch/hash/base,
records it before the first turn and projects generic comparison guidance. It does
not apply the alternative, change tools/gates or import old plans/actions/verdicts.
Omission preserves previous behavior. The operator binds the alternative to a fresh
run's public submission irrespective of its evaluator outcome.

A separate literal setup.py metadata adapter reuses public wheel resolution and
offline installation without executing setup code. A fresh offline real-Docker
canary now imports requests and the exact-base HF Xet module. Existing source and
dependency identities, image and sandbox boundaries remain intact.

Focused tests: 23 PASS / 46.847 seconds. Related regression: 152 PASS / 434.851 seconds
with durations. Collector: 23 PASS. Documentation: 5 PASS. Ruff: PASS. Two new mocks
reach edit/check/submit/isolated evaluation in both context policies, with eight
actual input deliveries captured. Core runtime stays `4d2fc8ba` / v45; the full core
suite was not rerun. Local validation is separate from the following live outcome.

## Frozen live result

H `hf-hub-xet-endpoint-propagation-v5` and P `pydantic-ai-synthetic-tool-reasoning`,
`gpt-5.4-2026-03-05` xhigh, standard chosen baseline settings. One final sample per
task/method. A: $2.40 direct reconsideration. B: $1.20 fresh generation plus $1.20
comparison/repair. Fixed order HA, HG, HB, PG, PB, PA; total cap $9.60; repeat=1 each.
B has two phases, so equal dollars do not mean equal aggregate call/time limits.

| Method | PASS / planned | Started / submitted | NOT_RUN | Recorded cost |
| --- | --- | --- | ---: | ---: |
| A | 0/2 | 2/2 | 0 | $0.3107315 |
| B, including generation | 0/2 | 2/2 | 0 | $1.5989980 |

Both intermediate generations also submitted and failed acceptance. Total recorded
cost $1.9097295; no-cache equivalent $2.7797775. Unused $7.6902705 is closed. No
infrastructure stop, unknown billing, retry, replacement, resume or extension.
All 32 actual inputs, schemas, count/dispatch pairs and continuations were audited.

All four final runs submitted their saved seed unchanged after two checks. There
were no read/search tool calls, probes or new edits in those final runs. Exact B alternatives
were delivered on all six requests, but no behavioral comparison appeared in their
public action decisions. Delivery is not evidence of use.

HG did respond to a public contract failure: at call 9 it linked failed HfApi cases
and current wrapper source to adding endpoint propagation. Its checks then passed;
acceptance still failed. No hidden reason was investigated. HG used all four mutation
slots; its last two output ceilings decreased to 23,619 / 20,416. No run ended because
of cost or input limits, but those constraints remain part of the workflow.

PG's first plan already treated field-mode configuration as the insertion condition,
despite a public requirement specific to a provider-supplied profile. Source reads
correctly established the shared serializer/replay owner, and the call-6 patch used
only field mode, field name, tool calls and absent thinking. It added no separate
requirement discriminator. Passing checks were then treated as confirming provider
preservation, although their plain-provider example uses the default mode.

This repeats the seed's scope error in a clean context before any summary boundary.
It weakens an explanation based only on imported-candidate anchoring or memory loss.
It does not prove the cause of every acceptance failure. Neither alternative passed,
so the experiment also does not isolate comparison with a correct alternative.

## Decision and unresolved question

No improvement was observed in this sample; do not adopt the optional comparison as
a default. Keep the verified dependency preparation capability. The next diagnostic
priority is the early translation from a public applicability requirement into an
executable condition, distinguished from format settings. Review prior condition
and case-design attempts before adding another generic instruction or gate.

Detailed packet: `C:\pt\analyses\independent-candidate-compare-20260926-v1\result.md`.
Raw public records: `C:\pt\indcandidate0926a`; local validation:
`C:\pt\validation\independent-candidate-20260926-v1\result.md`.
Hidden evaluator details were not inspected; historical records remained unchanged.
No general efficacy claim, new default or further paid allocation follows from this result.
