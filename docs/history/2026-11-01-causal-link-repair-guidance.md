# Repair selection: connect the public input to the proposed cause

Date: 2026-11-01. Implementation and local validation; fresh live execution pending.
All development work is official=false and claim-ineligible.

## Problem and evidence

The [latest task8 run](2026-11-01-completion-reserve-task8-results.md), at a1833855,
submitted a buffer conversion repair but independently failed. The original task
supplied serialized bytes; the agent repaired direct array/bytearray inputs.
The [unchanged added test](2026-11-01-task8-public-test-comparison.md) establishes
that narrower patch effect, not correspondence to the reported failure.
The [public bytes/caller comparison](2026-11-01-task8-bytes-call-path.md) found a
reproducible original-path failure on both base and submission: the earlier setter
changes bytes to a list before the patched conversion. Those operator findings
must not become solver hints in a fresh run.

This matters because a plausible helper failure and passing regression can support
the wrong repair target. Increasing checks or budget without connecting the cause
to the public input does not resolve that gap. In the saved public trace, the agent
read the conversion but not the earlier value setter. The prior general instruction
already asked it to preserve inputs and inspect an unexplained producing step.
Therefore simple delivery of that reminder is insufficient evidence of uptake.

## Intervention and alternatives

Replace the general reminder with a concrete, brief causal contrast in the existing
`hypothesis`: public caller/input/setup -> cause precondition -> wrong result.
Name observed source/results linking those steps, distinguish inference and gaps,
and explain how the proposed edit changes the link. An unexplained intermediate
value directs existing reads/searches toward its producing caller, assignment or
conversion; an earlier transformation can make a downstream repair too late.

The existing `expected_behavior` distinguishes a source-supported discriminating
case from a relevant normal control, preserving the public representation and
caller. Predictions remain distinct from execution evidence, and adequate prior
evidence can be reused. Source evidence still supports a direct edit without an
exact reproduction. Shared descriptions reach both replace_text and edit_files.

This modifies the existing pre-edit prompt and two field descriptions only. There
are no new fields, state, gates, tools, mandatory probes, model turns or resource
limits. The 1-1,500 character bounds and execution validators are unchanged. No
pydicom-specific input, branch or patch is included in the runtime guidance.

The hypothesis is that an explicit causal comparison improves source selection and
repair targeting. An alternative is that source navigation or model judgment remains
weak despite correct articulation. Finding the right cause without the proposed
format would also weaken a claim that the format is necessary. A fresh run can
inspect the mechanism, but one selected stochastic task cannot establish causality
or generalization. Do not add a semantic admission gate based only on prose.

## Local validation

Evidence root: `C:/pt/causal-link-20261101-v1`.

- The existing generic CSV request-delivery test now covers both verification
  policies as well as both context and agent policies. It keeps the original task,
  changed-input helper failure and ordinary passing control distinct in the actual
  outgoing request; offered tools, observations, source and credit remain intact.
- Initial broader selection: 108 PASS / 4 FAIL in 141.477s. The four failures were
  an incorrect new test assumption that the default reproduction policy is always
  explicitly present; the gateway intentionally omits that default. Correcting the
  assertion required no runtime change. This broad selection exceeded two minutes.
- Corrected focused owner/documentation selection: **54 PASS in 19.089s**, including
  the four corrected combinations. Original and corrected logs/XML are retained.
- Explicit CLI mock smoke: `run_dev_b5f5181db91d4649`, isolated **EVALUATOR_PASS**,
  task acceptance PASS, safety NOT_RUN, 4 mock calls, 5 actions, 1 edit, USD0.
- Full quick selection: 1,502 PASS / 6 FAIL / 1 host skip in 386.931s. All six
  failures were current-description hash pins. The first correction run exposed
  one additional range-only description hash later in an already failing test.
  Restoring only the two descriptions reproduced all seven prior schema hashes,
  proving the remaining serialized content/order unchanged. Update those current
  pins only; historical-arm values stay exact. Final pin/compatibility rerun:
  **13 PASS**, covering every failed node. Combined quick result: **1,508 PASS /
  1 host skip**, with failed attempts retained rather than represented as clean.
- Full Ruff: PASS. Final documentation/link checks are recorded in validation.json.

These are local delivery and compatibility controls, not evidence that a live model
will find a missing condition. No paid provider call has been made for this change.

## Frozen follow-up question

Prepare one fresh dev-train task8 (pydicom1413) from public source, without prior
patches, helper programs, notes, diagnostic outputs or counterexample hints. Proposed
model is gpt-5.4-2026-03-05/xhigh, credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, one attempt, new total cap USD4, 40 model
calls, 100 actions, 12 edits, 1,800 seconds including 330 seconds reserved for the
single normal independent evaluation. Policies, source/dependency descriptors and
single-worker execution match the latest task8 baseline; only guidance and fresh
state differ. Commit/runtime and exact requests will be bound before authorization.

Compare actual public source selection, the original-input/cause connection,
discriminating observations, preserved assertions and resulting repair. Report
independent acceptance, safety, public checks, submission, cost and time separately.
More calls or compliant wording alone is not improvement. If the relevant decision
point is not reached, report that limitation. A repeated disconnected helper repair
would weaken this intervention and leave navigation/selection as an open question.

Do not dispatch without a new exact positive cap. Zero SDK retries; count, transport,
billing, continuation or cleanup uncertainty stops new work. No retry, resume,
additional evaluation, runtime edit or budget increase is included. Earlier unused
allocations remain closed. See the external validation and commit receipts, then
`C:/pt/causal-task8-20261101-v1` for the prepared proposal when available.
