# Explicit planning ON/OFF full-run comparison

Date: 2026-09-26. Eight fresh solves completed; `official=false`, `claim_eligible=false`.

## Problem and hypothesis

The preceding source-supplementation diagnostic did not change the immediate Pydantic
applicability question while the first plan and continuation were fixed. Repeated public
traces suggested an early interpretation might narrow later investigation. That did not
establish first-plan anchoring. The existing planning OFF option allowed a feature ablation
without adding another prompt, reviewer or task-specific hint.

## Intervention and execution

The user approved two repetitions per arm on Pydantic synthetic tool reasoning v1 and
HF Hub Xet endpoint propagation v5. A was `brief-v1`; B was `none`. Order was
PA1/PB1/PB2/PA2/HA1/HB1/HB2/HA2, $1.20 each, $9.60 total, no transfer or extension.
Both used `gpt-5.4-2026-03-05`, xhigh, 25,000 desired output, segmented-v1,
result-or-size-v1, probes enabled/probe-policy none, repair-recheck, protected-v1 and
per-call-v1, with 40 calls/100 tools/4 mutations/1,800 seconds. Exact root `.env`,
prepared source/dependencies and existing images were bound before dispatch.

This tests the whole explicit planning feature: instructions, annotation schema, plan
projection and review signals. OFF retains xhigh reasoning and run-local notes. It does
not isolate first-plan timing. Fresh actual inputs matched per task after normalizing
only declared planning differences, measured preparation time and derived segment ID.
No candidate, prior plan/notes or evaluation feedback was injected.

An external wrapper reused ordinary run_dev, the existing bounded collector, zero-retry
transport and public input/usage audits. Predecessor files and runtime stayed unchanged.
Collection HEAD was `2fc16faed1996cce11faac418e56a1ea79ca193b`; runtime `4d2fc8ba`,
tool surface v45. Frozen packet: `C:\pt\analyses\planning-off-compare-20260926-v1`.

## Result and public behavior

| Task | ON acceptance PASS / planned | OFF acceptance PASS / planned |
| --- | ---: | ---: |
| Pydantic | 0/2 | 2/2 |
| HF Hub | 0/2 | 0/2 |
| Total | 0/4 | 2/4 |

All eight started, submitted, completed isolated evaluation and passed safety.
Acceptance FAIL was ON 4/OFF 2; NOT_RUN 0; infrastructure stops 0. All ultimately
passed their registered public checks. There were no model-selected probes or repeated
rejected edits. These activity counts alone are not performance evidence.

Pydantic ON plans described all field-mode profiles while also mentioning preservation
of existing profile/provider behavior. Each later changed only the shared serializer, using field format
as the applicability condition. Both OFF runs added a default-false profile requirement,
enabled it in the provider-supplied profile, and consulted it in serialization. This
distinction is visible in the public task and code; no hidden evaluator detail was read.
Both OFF repairs passed acceptance, but neither independently tested the discriminating
ordinary-profile case. Better repair scope is observed; better verification selection is not.

HF Hub remained unresolved in both arms. HA1 completed caller wiring before checks;
HB1, HB2 and HA2 used public failures to repair missing forwarding. Automatic rechecks
are separated from model-selected checks. All four then passed 292 public contract cases
and 15 regressions and submitted. Planning OFF did not improve acceptance here.

Public-source review identified a further unexecuted concern: all four H patches pass
`HfApi.self.endpoint`, but its unchanged constructor resolves an omitted argument to
`constants.ENDPOINT`, losing explicit-versus-default provenance. The public omitted-endpoint
case uses the direct module function. No new candidate case was run, and this is not
asserted to explain the hidden failure. Behavioral review was unblinded and public-only.

## Cost, resources and validation

Recorded total was **$5.988843**; cache-neutral repricing was **$8.776395**. ON costs
$2.414778 / $3.651450 cache-neutral; OFF costs $3.574065 / $5.124945. These are settled
usage-ledger values, not an invoice. The unused $3.611157 is closed. No retry, resume,
replacement, transfer, additional sample, Docker startup or image acquisition occurred.

All 88 generations completed; 89 counts include one rejected 64,861-token candidate
in HB2. That request was not dispatched: input_tokens triggered a new segment. Maximum
dispatched input was 55,619. There were 38 segments: 8 initial, 29 major-result and one
input-size transition. Pydantic kept 25,000 output ceilings throughout. Some H ceilings
fell with remaining budget, reaching 6,426 in HB2, but no incomplete response or limit
terminal occurred. HB1 used all four mutations; other runs did not. Resource effects
must not be collapsed into a claim about planning or continuity alone.

All 88 actual inputs, nine journal chains, settled usage and 77 protected file hashes
verified. The new collector's final focused 10 tests passed in 65.713 seconds, with
42 related regression tests passing. An initial seed-normalizer failure was fixed and
retained before freeze. Ruff and ON/OFF mock smoke passed through isolated evaluation
and actual public-state delivery. Full core regression was not rerun because runtime
code did not change. Documentation verification is recorded with the final closure.

## Decision and next question

The acceptance difference is confined to two Pydantic repetitions per arm. Keep OFF as
a comparison candidate, with defaults and chosen working baseline unchanged. This is a
small selected development comparison, not a general success rate or proof that planning
causes failure. First-plan anchoring remains an unisolated hypothesis.

The smallest next mechanism to examine is the demand to create a plan before reading
source. Delaying that first requirement while retaining later planning could separate
premature interpretation from useful subsequent coordination. It is not implemented or
funded by this closed group. Do not add a task-specific hint or another review template.

## Evidence

- Full protocol, metrics, public review, validation and closure:
  `C:\pt\analyses\planning-off-compare-20260926-v1`.
- Durable live group: `C:\pt\planoff0926a`, `run_dev_planoff0926a`.
- Plan contract: [brief planning](../../.agent/planning-experiment.md).
- Preceding result: [post-search declaration comparison](2026-09-26-declaration-checkpoint-comparison.md).
