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

The readiness result must not be reported as the answer to the long-term question.
Readiness execution is paused until evaluator v2 and a successor A/C source are qualified.

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
| C | `structured` | R2 delivery/suite qualified offline; evaluator-v2 successor not qualified |
| D | `selective_structured` | Deferred; applicability calibration and score policy incomplete |

For this readiness panel, C means all three approved generic rules in frozen D-110 `group_provenance`
order. It does not mean
embedding retrieval or threshold selection.

## 4. Four-run readiness matrix

The historical offline plan is `experiments/ac-structured-pilot-v2.plan.yaml`; the exact R2 suite is
`experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml`.

| Order | Task | Condition |
| ---: | --- | --- |
| 1 | Moto #7208 | A `no_memory` |
| 2 | Moto #7208 | C `structured` |
| 3 | Babel #1042 | C `structured` |
| 4 | Babel #1042 | A `no_memory` |

Each row uses a fresh workspace and no state from another row. There is one repetition, no automatic
replacement and no retry. Condition order is counterbalanced across the two tasks.

## 5. Controlled variables

All four rows must share:

- `gpt-5.4-mini-2026-03-17`, medium reasoning, standard mode, default tier;
- transport retry 0 and `store=false`;
- SYSTEM_PROMPT_V3, tool schema v2 and phase-evidence-v5;
- exact task package, base commit and official evaluator per task;
- max output 25,000, total-token ceiling 3,000,000 and wall timeout 3,600 seconds;
- no model/tool call-count ceiling;
- identical pricing/accounting and schedule qualification; D-126 observed official default-tier list prices
  of $0.75 input, $0.075 cached input and $4.50 output per 1M text tokens.

The only planned treatment difference is exact selected-memory content.

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

D-108's +702 token count covers one request shape, not every live turn. D-124/D-125 prove local/mock completion
behavior only; no reservation, result, candidate or execution hash exists. Consumed external attempts remain
canonical in `docs/09-evidence.md`.

D-142 is source-qualified and unactivated, with planning disposition deferred. It has no runtime artifact and
cannot qualify changed evaluator bytes. Evaluator v2 therefore requires new source, suite and runtime identities;
the A-null/C-exact-three treatment itself remains unchanged.

Evaluator-v1 safety is literal PASS. V2 derives typed evidence from accepted events, verified CAS and exact requested
policy; marker hits are redacted. Missing→NOT_RUN, checker error→ERROR, violation→FAIL, complete→PASS. Separate
authority and receipt gate runner selection, persistence and qualification; raw results remain unofficial.
Executable v3 is consumed Docker-blocked; v4 records manual start without proving readiness. V5 is source-qualified,
unapproved and unattempted, so it produced no Docker/`.env`/SDK or evaluator evidence.

## 7. Run-completion gate

The D-125-qualified completion source makes the four-row matrix analyzable only if every row:

- reaches a terminal state;
- is trace-qualified and cost-settled;
- records complete provider response usage with exact token-count reconciliation;
- reaches either the historical official v1 evaluator or receipt-qualified v2 path and binds all verdicts
  consistently with SCRR and resolved/task-failure outcome;
- binds a specific evaluator-v2 safety result and its evidence rather than accepting a verdict string alone;
- has no infrastructure, qualification, diagnostic or budget-terminal confound.

If any row fails this gate, preserve all evidence and mark the panel inconclusive. Do not replace or rerun only
the failed row. D-125's local consumption is fail-closed/no-resume; mocked finalization recovery never reruns a
row. Cross-store/global/cross-clone protection, actual kill and power-loss durability remain unverified.

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

## 11. Deferred experiments

After valid readiness, the planning target is the frozen 12-task core panel × A/C × at least two repetitions
(at least 48 rows). Exact schedule, analysis, runtime and cost require preregistration before held-out unblinding.
The full A/B/C/D design remains later: freeze B/D first or use a separate fresh held-out panel afterward. The
historical `experiments/core.template.yaml` is not modified or authorized by this decision.
