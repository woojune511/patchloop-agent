# Evaluation protocol

Status: current normative protocol. Historical milestone protocols are archived at
`docs/archive/snapshots/d121/04-evaluation-protocol.full.md`.

## 1. Questions and dataset roles

Long-term question: under a fixed coding-agent runtime, how do no memory, raw trace, structured memory and selective
structured memory affect held-out scope-compliant success, cost and negative transfer?

Immediate readiness asks only whether an exact fixed structured bundle traverses the full workflow beside no memory.
R8 completed that four-row development matrix; it is not the long-term answer. `data/dataset-manifest.yaml` assigns
calibration, memory-development, development-validation, core same-repo, core cross-repo and external-acceptance roles.
External acceptance never enters the core aggregate.

## 2. Conditions and development matrix

| ID | Condition | Status |
| --- | --- | --- |
| A | `no_memory` | Implemented baseline |
| B | `raw_trace` | Deferred; portable redaction contract incomplete |
| C | `structured` | Exact frozen D-110 three-entry bundle |
| D | `selective_structured` | Deferred; applicability/score policy incomplete |

R8's consumed schedule was:

| Order | Task | Condition |
| ---: | --- | --- |
| 1 | Moto #7208 | A `no_memory` |
| 2 | Moto #7208 | C `structured` |
| 3 | Babel #1042 | C `structured` |
| 4 | Babel #1042 | A `no_memory` |

Rows used fresh workspaces and no retry/replacement. They shared `gpt-5.4-mini-2026-03-17`, medium reasoning,
standard/default tier, retry 0, `store=false`, SYSTEM_PROMPT_V3, tool schema v2, phase-evidence-v5, exact task/image/
evaluator, 3M input/350k output/3.35M aggregate, 25k/response, 180 model, 300 tool and 3,600 seconds. R8 reserved
`$3.825`/row, `$15.30`/panel and `$18`; actual cost was `$0.3664215`.

A is null; C renders the exact three texts in frozen order on every request. No retrieval/ranking or reviewer/source
material enters model input. R8 raw v2 results remain `official=false` despite receipt-qualified completion.

## 3. Completion, metrics and interpretation

Analysis requires every scheduled row terminal, trace-qualified, usage/cost-settled, evaluator/verdict-consistent and
free of infrastructure, qualification, diagnostic and budget confounds. V2 also requires authenticated receipt and
typed safety evidence. Rows cannot be replaced. Cross-clone and kill/power-loss durability remain unverified.

A complete matrix may report terminal/evaluator reach, delivery integrity, SCRR/verdicts, flips, token/call/duration/
cost and paired C-minus-A deltas. It cannot claim causal or general memory improvement, production readiness,
significance/confidence, per-rule efficacy, retrieval quality or population negative transfer. R16 supplies an
official estimate for the frozen held-out panel only; R11, R14 and R15 remain incomplete operational observations.

Private specs, hidden/reference evidence, known-bad patches and traces cannot tune tasks, memory, thresholds, prompt,
selection or policy. Moto/Babel cannot become fresh validation after their outcomes informed changes. Partially
unblinded R11/R14/R15 may repair infrastructure contracts only.

## 4. Preregistered held-out A/C

The preregistration freezes 12 tasks × A/C × two repetitions = 48 rows and complete-panel SCRR. Deterministic
100,000-sample percentile stability and exact 4,096-sign sensitivity are assumption-based, not population confidence.
Eligible evaluator FAIL and typed agent terminals score zero; infrastructure confounds are inconclusive.

- R7 sealed 0 settled/1 unsettled/47 not-started after qualification-byte drift.
- R11 candidate `sha256:f48a0de...a6b0` sealed 2 settled/1 observed-unsettled/45 not-started: `$0.15699525`
  settled and `$0.41801625` observed-started. A hidden failure and evaluator-control collision block analysis.
- Development-only evidence set equal A/C to 1M/100k/1.1M and `$57.60`/`$60`, excluding R11 outcomes and held-out
  task content. R14 candidate `sha256:67475f57...307fd` consumed it and sealed 0 settled/1 observed-unsettled/47
  not-started with `$0.126342` observed.
- R15 candidate `sha256:e11ece55...64f8bc` separately consumed the same envelope and sealed 2 settled/
  1 observed-unsettled/45 not-started: `$0.2002335` settled and `$1.112112` observed-started.
- R16 candidate `sha256:24044c1e...8813` consumed a fresh approval and completed 48/48 settled rows at
  `$27.24465825`, with 15 resolved, 14 task failures and 19 typed agent failures. No retry/replacement/resume occurred.

R14's immutable reason is `DURABLE_EVIDENCE_AUTHENTICATION_FAILED`. Post-runtime
`TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH` records that completion compared the candidate
1M/100k/1.1M budget with the immutable suite's 4M/500k/4.5M tuple; it grants no reauthentication/reclassification.
R15 preserves the same historical campaign reason while the successor diagnosis
`TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH` records the old qualifier's impossible v1-rich requirement
for a sanitized v2 budget terminal.

Contract R11 → binding R11 → materialization R7 → execution R8 → preflight R16 was the corrected source path consumed
by R16. Candidate-v3 bound the realized schedule and runtime/cost; every next-row admission required
persisted-v5/row-v2 plus budget/semantic revalidation. Known legacy R7/R11/R14/R15 history requires its exact allowlisted
final-file/content/journal triple.

R16's official frozen-panel results are no-memory 8/24 and structured 7/24, so C-minus-A is `-1/24`. The deterministic
100,000-sample stability interval is `[-1/4, 1/6]`; the assumption-based sign-flip sensitivity is `p=1`; benefit and
negative-transfer flips are 3/24 and 4/24. Same-repo effect is 0 and cross-repo effect is `-1/12`. These quantities do
not authorize a causal/general memory claim or reuse of the now-unblinded panel. Another experiment requires a fresh
preregistered design and separate authority; no candidate or approval exists now.
