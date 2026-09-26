# First-plan timing comparison: 2026-09-27

## Problem and hypothesis

The separate [planning ON/OFF comparison](2026-09-26-planning-off-comparison.md)
found Pydantic repairs with different applicability conditions. Its whole-feature
ablation could not isolate whether an initial plan formed before reading source was
anchoring later work. The [timing implementation](2026-09-26-after-source-planning.md)
added an opt-in request after source delivery while retaining later planning.

This fresh group tests that timing change. It does not test a new planning template,
require a diagnostic phase, or inject task-specific repair hints.

## Frozen intervention and execution

- A: `brief-v1`; B: `brief-after-source-v1`.
- Tasks: `pydantic-ai-synthetic-tool-reasoning` v1 (P) and
  `hf-hub-xet-endpoint-propagation-v5` v5 (H), existing `dev-train` packages.
- Order: PA1, PB1, PB2, PA2, HA1, HB1, HB2, HA2; repeat=1 each.
- Model: `gpt-5.4-2026-03-05`, xhigh, desired output 25,000 tokens.
- Segmented-v1/result-or-size-v1, probes enabled/probe-policy none, repair-recheck,
  protected-v1 inspection, per-call-v1 cost admission; 40 model calls, 100 tool
  actions, 4 accepted mutations, 1,800 seconds, counted input at most 60,000.
- $1.20 per slot / $9.60 group; exact repository `.env`; zero SDK retries.
- Fresh workspaces from the same task's prepared source/dependencies; existing
  Docker and images only. All runs `official=false`, `claim_eligible=false`.
- Frozen HEAD `93ec0afb13c13e3ca89b027fdabaf1c234995c00` and runtime
  `sha256:9320c697313e8340762a3fe48eb8717ef547e95a3696354d7fdad9d90d9935c6`.
- Plan identity `sha256:41d962b14e1197ae2c11d0d0838144f989f9898530b4d67ac36910a309df23c0`.

The new external wrapper reused ordinary `run_dev` and the prior public input,
continuation and usage audits. Within each task, A/B request differences were planning
policy and run root;
initial input normalization retained the complete ordered tool schemas and all public
task/diff/check state, removing only declared timing/policy differences, measured
preparation time and derived segment identity. Later behavior was not normalized away.
Instructions and review signals jointly express the first-plan timing policy.

## Results

| Task | A acceptance | B acceptance |
| --- | --- | --- |
| Pydantic | 0/2 | 1/2 |
| HF Hub | 0/2 | 0/2 |
| Planned total | 0/4 | 1/4 |

Every slot started, submitted and completed evaluation; safety PASS 8/8, NOT_RUN 0,
infrastructure stops 0. PB1 was the sole acceptance PASS. All 76 provider responses
completed; no count, provider, billing, continuation, cleanup or integrity uncertainty
occurred. Collection wall time was 3,425.598 seconds. No retry, replacement, resume,
additional candidate execution or default change followed the result.

| Metric | A | B |
| --- | --- | --- |
| Recorded USD | 2.466473 | 2.833167 |
| Cache-neutral USD | 3.625385 | 4.063215 |
| Model calls / verified actual inputs | 38 / 38 | 38 / 38 |
| Maximum counted/dispatched input tokens | 46,515 | 54,606 |
| Segments, including initial segments | 18 | 18 |
| Minimum admitted output ceiling | 23,626 | 11,927 |
| Repeated rejected edits / probe actions | 0 / 0 | 0 / 0 |

Total recorded cost was $5.299640, or $7.688600 with cached input repriced at the
uncached rate. The $4.300360 remainder is closed. Each arm had four initial segments
and fourteen `major_result_reviewed` transitions. Pydantic output ceilings stayed at
25,000 throughout; HF ceilings shrank in HA1, HB1 and HB2. No response exhausted its
output ceiling, and no run ended at a resource limit. Different costs/input sizes
remain possible influences; this is not evidence of a pure continuity effect.

## Public behavior and limits

The intended timing change occurred: all A first plans preceded source results in
call 1; all B first plans followed those results in call 2. No voluntary early B plan
occurred. First mutation calls were PA1 5, PB1 4, PB2 4, PA2 6, HA1 5, HB1 4, HB2 5,
HA2 4. Earlier editing by itself is not correctness evidence.

Pydantic PB1 asked in call 2 whether a generic field-mode change would be too broad.
It then read the profile definition, added a default-false compatibility flag,
consumed it in the shared serializer, and enabled it in the provider-supplied profile.
PA1, PA2 and PB2 used field mode alone as the applicability condition. PB2's first
batch had already delivered the full profile and provider definitions before its
first plan, so source-before-plan did not reliably elicit the needed distinction.
All four ran the same two registered checks and passed. None independently probed
ordinary-profile preservation. This is an observed repair-scope difference, not
proof of better verification selection or the exact hidden failure cause.

HF HA1 and HB1 used public contract failures to repair missing forwarding paths:
72 failing cases fell to 24 and then zero. HB1's intervening reads investigated the
caller relation and obtained a contiguous source anchor for two same-file edits.
HA2 and HB2 completed the forwarding edits before their first checks, which passed.
All four ultimately forwarded `self.endpoint` through the client metadata wrapper.
Their plans described explicit-endpoint preservation, but later expectations often
narrowed endpoint-less preservation to direct/module helper calls. No independent
probe examined whether a stored endpoint still represented an explicit argument.
The public-source concern from the prior record remains unresolved; private evaluator
details were not read, and acceptance failures are not attributed to that concern.

## Validation and evidence

External root: `C:\pt\analyses\planning-after-source-compare-20260927-v1`.
Live group: `C:\pt\planafter0927a`; group id `run_dev_planafter0927a`.

- `protocol.md`, `pricing.json`, `plan.json`: exact frozen design and provenance.
- `validation.json`: 12 focused tests PASS in 51.995 seconds, 68 related tests PASS
  in 128.981 seconds, Ruff PASS. Both actual mock inputs reached mutation, public
  checks, submission and isolated acceptance; mock safety remained NOT_RUN.
- An initial authored mock assertion assumed two plan revisions; repair-recheck
  legitimately produced three. The fixture assertion was corrected and all twelve
  focused tests rerun; the original 9 PASS / 3 ERROR receipt remains intact.
- The runtime was unchanged. The earlier broad-suite timing/Git failures and passing
  unchanged-code rechecks remain in the implementation record; no new broad-suite
  success is claimed here.
- `metrics.json`: all 76 actual inputs and settled usages, nine journal chains, and
  124 frozen protected files verified; 849 historical tracked files preserved.
- `*-public-timeline.json`, `*-public-delivery.json`, `behavior.json`: source/action/
  check evidence and a post-hoc, unblinded review bound to those public artifacts.
- `result.md`, `post-validation.json`, `closure.json`: human summary, final document
  validation and commit-bound closure. Generated run state remains outside the repo.

## Decision and next question

The completed difference is one acceptance, below the frozen two-result follow-up
threshold. Direction is uncertain; keep CLI defaults and the selected baseline fixed.
The separate planning-OFF result is not a third arm or a fair cross-group ranking.

First-plan timing alone is not established as the next improvement. The useful
unresolved question is how the agent chooses to test applicability before generalizing
a shared implementation condition. PB1 provides an observed pre-edit question to
study, while PB2 shows that delivering the relevant declarations alone is insufficient.
Consider simplification before adding another template, mandatory reviewer, probe rule
or state structure. This closed group authorizes no additional paid allocation.
