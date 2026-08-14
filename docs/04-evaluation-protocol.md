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

D-122/D-125 freeze A as null and C as the exact ordered three-text D-110 bundle on every request. Drift fails closed;
no retrieval/ranking or reviewer-only/source material enters model input. Paired requests differ only in memory and
derived identities; durable token/usage accounting remains active. D-108/R3 measure delivery overhead, not effect.
R8 is consumed and raw v2 results remain `official=false`; see `docs/09-evidence.md`.

## 7. Run-completion gate

Analysis requires every row terminal, trace-qualified, cost/usage-settled, evaluator/verdict-consistent and free of
infrastructure, qualification, diagnostic or budget confounds. V2 also requires its authenticated receipt and typed
safety evidence. R3-R6 failed distinct gates; R8 met them, with its stale projection corrected append-only. Rows cannot
be replaced; cross-clone and kill/power-loss durability remain unverified.

## 8. Metrics

Readiness metrics cover terminal/qualification/evaluator reach, A-null versus C-exact-three integrity, leak/diff and
truncation. Only a complete matrix adds descriptive SCRR/verdicts, flips, submission outcome, token/call/duration/cost
and paired C-minus-A deltas.

## 9. Interpretation boundary

The result may state whether the exact bundle traversed the workflow and report these two development pairs'
descriptive direction/cost. It cannot claim causal/general memory improvement, held-out/cross-repository or production
readiness, significance/confidence, individual-rule efficacy, retrieval quality or population negative transfer.

## 10. Leakage and selection controls

Use both development tasks, exclude memory-source rows, freeze identities before outcomes, and never select/tune from
private specs, hidden/reference evidence, known-bad patches or traces. Moto/Babel cannot become fresh validation after
their results informed changes.

## 11. Preregistered held-out A/C

The record freezes 12 tasks × A/C × two repetitions = 48 rows and a scheduled-row complete-panel SCRR contrast.
It specifies deterministic 100,000-sample percentile stability and an assumption-based exact 4,096-sign sensitivity;
neither is design-based or a population confidence claim. Eligible evaluator FAIL and typed agent terminals score zero;
infrastructure confounds are inconclusive. Refreshed prices preserve `$252`/`$275`; execution/unblinding remain closed.

R2 implements the strict suite, complete/inconclusive fixtures and deterministic analysis. R5 binds 12 metadata tasks,
hardened materialization and persisted-row authentication source. Materialization R1 records opaque templates and one
price capture without outcomes/private values. Execution-contract R1 binds exact schedule/cost, manifest and ephemeral
secret expansion; preflight R2 binds read-only Git/Docker-image/SDK/credential-presence checks. They performed no such
observation and created no candidate, expanded contract or authenticated row.
