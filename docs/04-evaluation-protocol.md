# Evaluation protocol

상태: current normative protocol. Historical per-milestone protocols are archived at
`docs/archive/snapshots/d121/04-evaluation-protocol.full.md`.

## 1. Research questions

Long-term question:

> Under an otherwise fixed coding-agent runtime, how do no memory, raw trace, structured memory and
> selective structured memory affect held-out scope-compliant success, cost and negative transfer?

Immediate readiness question:

> Can an exact fixed structured bundle be delivered through the full workflow without leakage, ambiguity or
> process failure when compared contemporaneously with no memory?

The readiness result is not the long-term answer. R3 through R6 are immutable inconclusive attempts; R8 completed
the exact four-row development-readiness matrix under its R10-qualified source. R7/R9 is superseded unexecuted.

## 2. Dataset roles

`data/dataset-manifest.yaml` is authoritative.

| Role | Current use |
| --- | --- |
| Calibration | Schema/evaluator plumbing only |
| Memory development | Failure review and entry authoring |
| Development validation | Rendering, no-match, leak and live runtime readiness |
| Core same-repo | Future held-out transfer evaluation |
| Core cross-repo | Future cross-repository generalization evaluation |
| External acceptance | Separate interoperability lane; never core aggregate |

The current A/C readiness uses the complete two-task development-validation panel. It does not consume a
held-out result.

## 3. Memory conditions

| ID | Condition | Current status |
| --- | --- | --- |
| A | `no_memory` | Implemented baseline condition |
| B | `raw_trace` | Deferred; portable selection/redaction contract incomplete |
| C | `structured` | Exact-three delivered through resolved, qualified Moto and Babel runs in R8 |
| D | `selective_structured` | Deferred; applicability calibration and score policy incomplete |

For this readiness panel, C means all three approved generic rules in frozen D-110 `group_provenance`
order. It does not mean
embedding retrieval or threshold selection.

## 4. Four-run readiness matrix

The v11 plan binds sealed, consumed R8; v10/R9/R7, v9/R8/R6, v8/R7/R5, v7/R6-qualification/R4 and
v6/R5-qualification/R3 remain immutable predecessors.

| Order | Task | Condition |
| ---: | --- | --- |
| 1 | Moto #7208 | A `no_memory` |
| 2 | Moto #7208 | C `structured` |
| 3 | Babel #1042 | C `structured` |
| 4 | Babel #1042 | A `no_memory` |

Rows use fresh workspaces and one repetition. Preflight may retry transient pre-provider failure; campaign rows do
not retry or replace, and any confound makes the counterbalanced panel inconclusive.

## 5. Controlled variables

All four rows must share:

- `gpt-5.4-mini-2026-03-17`, medium reasoning, standard mode, default tier;
- transport retry 0 and `store=false`;
- SYSTEM_PROMPT_V3, tool schema v2 and phase-evidence-v5;
- exact task package, base commit and official evaluator per task;
- cumulative input/output/aggregate ceilings of 3,000,000/350,000/3,350,000 tokens, with reasoning counted as
  output;
- max output 25,000 per response, max 180 model calls, max 300 tool calls and wall timeout 3,600 seconds;
- identical pricing/accounting and schedule qualification; D-126 observed official default-tier list prices
  of $0.75 input, $0.075 cached input and $4.50 output per 1M text tokens.

The only planned treatment difference is exact selected-memory content.

R8 reserves full-price input/output at `$3.825` per row and `$15.30` per panel, with `$18` cap and `$2.70` slack; it
assumes no cache discount. The equal A/C thresholds are informed by one R3 development row, not held-out-safe,
invoice/completion predictions or proof extra capacity resolves C.

## 6. Memory delivery qualification

D-122 predecessor evidence and current D-125 offline tests prove:

1. A renders no selected-memory text or memory-delivery event.
2. C renders exactly the three approved D-105 texts in frozen D-110 `group_provenance` order on every
   model request.
3. D-110 index/marker/text drift, missing input or unknown entry fails closed.
4. No embedding load, query encode, similarity, rerank or threshold occurs.
5. Source provenance, vectors, raw traces and reviewer-only fields never enter model input.
6. For the same durable event prefix, the normalized offline A/C request pair differs only at the
   selected-memory field and its derived hashes/counts. Later live turns may diverge with agent trajectory.
7. Input-token counting, truncation-disabled behavior and durable usage evidence remain intact.

D-108's +702 tokens cover one request shape. R3 live C delivery consumed 2,963,919 tokens before submission and says
nothing about task effect. `docs/09-evidence.md` owns exact observations.

R10 bound R8 source/plan/suite/split-budget/bounded-call and strict machine-contract identities while preserving
A-null/C-exact-three. Candidate `sha256:60c67908...cff9e` then received one exact approval and is consumed. Raw v2
results remain `official=false`; receipt qualification supplies completion eligibility.

## 7. Run-completion gate

The D-125-qualified completion source makes the four-row matrix analyzable only if every row:

- reaches a terminal state;
- is trace-qualified and cost-settled;
- records complete provider response usage with exact token-count reconciliation;
- reaches either the historical official v1 evaluator or receipt-qualified v2 path and binds all verdicts
  consistently with SCRR and resolved/task-failure outcome;
- binds a specific evaluator-v2 safety result and its evidence rather than accepting a verdict string alone;
- has no infrastructure, qualification, diagnostic or budget-terminal confound.

R3 failed this gate at Moto C and left Babel unstarted. R4 sealed before provider dispatch at `$0` because its
paid-plan capability revalidation selected the legacy budget. R5 Moto A then resolved through evaluator v2, but a
legacy null-call/aggregate-only terminal qualification rejected it and halted the other three rows. No row may be
replaced. R6 Moto A then resolved and passed evaluator v2, but its runtime evidence recorded the legacy call-guard
policy and qualification halted the other rows. R8 then produced four resolved, qualified and settled rows. Its raw
completion adapter misclassified the valid v2 qualification envelope; append-only offline correction records the
complete matrix without rewriting the result. Global/cross-clone and kill/power-loss durability remain unverified.

## 8. Metrics

Primary readiness metrics:

- terminal, trace-qualified and evaluator-reached status;
- A memory count 0 versus C exact-three delivery integrity;
- request-diff, leak scan and truncation status.

Descriptive task metrics, only after the complete matrix:

- hidden/regression/scope/safety and their SCRR conjunction;
- A-fail/C-success and A-success/C-fail directional flips;
- accepted submission and process outcome;
- input/output/reasoning tokens, model/tool calls, duration and list-price cost;
- C−A deltas and cumulative memory overhead.

## 9. Interpretation boundary

Allowed statement:

> The exact fixed structured bundle could/could not be delivered leak-safely through the full workflow, and
> these two development-validation pairs showed the following descriptive direction and cost.

Not allowed:

- general or causal memory improvement;
- held-out or cross-repository generalization;
- statistical significance or confidence intervals;
- individual-rule efficacy, because all three rules are bundled;
- retrieval/selective-policy quality;
- a population negative-transfer rate;
- production/core readiness.

## 10. Leakage and selection controls

- Use both development-validation tasks; do not hand-pick one after inspection.
- Do not use exact memory-source tasks as efficacy rows.
- Do not inspect private specs, hidden results, reference/known-bad patches or source traces for task selection.
- Freeze task/index/text identities before outcomes.
- Never tune the fixed bundle on Moto/Babel results and then reuse the same rows as fresh validation.

## 11. Preregistered held-out A/C

The record freezes 12 tasks × A/C × two repetitions = 48 rows and a scheduled-row complete-panel SCRR contrast.
It specifies deterministic 100,000-sample percentile stability and an assumption-based exact 4,096-sign sensitivity;
neither is design-based or a population confidence claim. Eligible evaluator FAIL and typed agent terminals score zero;
infrastructure confounds are inconclusive. `$252`/`$275` need fresh pricing; execution/unblinding remain closed.
