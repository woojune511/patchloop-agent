# Reference-free probe replay: closed four-row comparison

Status: COMPLETE / allocation CLOSED / official=false / claim_eligible=false.
Task outcomes: INCONCLUSIVE. Mechanism: NOT_EXERCISED. No default adoption.

## Problem, hypothesis and fixed scope

The [program-replay change](2026-09-30-probe-program-replay.md) made it possible to
retain and rerun a model-authored public program without first obtaining a healthy
JSON reference. The question was whether this additional capability improves
repairs beyond existing reference-based cases. A successful implementation alone
does not establish that agents select useful programs or improve task correctness.

Control A used reference-cases-v1; B used cases-v1 with save_program. Both retained
ordinary probes and reference registration/comparison/replay. They shared one clean
runtime, original public inputs, prepared environments and solving limits. No prior
patch, operator probe, Darts case matrix, trajectory or evaluator feedback entered
another row. No default-policy none arm was included.

The user explicitly approved four fresh repeat=1 rows, USD 3 per row and USD 12
invocation-wide. Order: Darts v1 A, Darts v1 B, MontePy v2 B, MontePy v2 A. Model:
gpt-5.4-2026-03-05, xhigh, desired output 25,000; segmented-v1, result-or-size-v1,
brief-v1, repair-recheck, protected-v1, per-call-v1. Each row allowed 1,800 seconds,
40 model calls, 100 tools and four accepted edits. Credential file: project .env;
credential contents are not recorded here. The common panel ledger retained each
row's ceiling, counted before dispatch, used zero retries and stopped on uncertainty.

Dispatch commit: `8f8d633142b2daab019eab7a7fe635b8a5d983e6` (PR #11 head).
Runtime hash: `sha256:ce57fe208761705d4935459b40835f24c6f60131a1b67950278d185051ecf2ef`.
The [frozen plan at that commit](https://github.com/woojune511/patchloop-agent/blob/8f8d633142b2daab019eab7a7fe635b8a5d983e6/.agent/probe-replay-comparison.md)
owns the predeclared interpretation rules. Both OS CI jobs passed before admission;
each ran 3,767 tests with 25 skips and mock isolated acceptance PASS, safety NOT_RUN.
Existing source/dependency contents and local image digests were revalidated without
starting Docker Desktop, acquiring images or modifying task packages.

## Executed results

Every row made one accepted edit and ended EVALUATOR_PASS. Acceptance and real
sandbox safety were each PASS in all four rows; no evaluator error, cap stop,
retry, resumed row, replacement row or unfinished provider call occurred.

| Row | Task | Arm | Public tests | Acceptance | Safety | Model calls | Active seconds | USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | original-darts-3065 v1 | A | 8 PASS | PASS | PASS | 6 | 173.003 | 0.323553 |
| 2 | original-darts-3065 v1 | B | 8 PASS | PASS | PASS | 6 | 165.184 | 0.339615 |
| 3 | original-montepy-933 v2 | B | 44 PASS | PASS | PASS | 7 | 168.173 | 0.3526335 |
| 4 | original-montepy-933 v2 | A | 44 PASS | PASS | PASS | 9 | 185.994 | 0.3963655 |

Total recorded provider-usage cost: USD **1.412167**, reconciled from all 28 settled
model calls to the four row totals and the common ledger. There were 28 input counts,
42 tool actions and 692.354 summed active seconds. This is ledger cost using registered
prices and recorded usage, not an independently reconciled account invoice.

Descriptive B/A cost and time ratios: Darts 1.049643 / 0.954804; MontePy
0.889667 / 0.904185. Each task has only one pair; these differences do not establish
a repeatable efficiency gain or causal effect of the capability.

## Mechanism audit and decision

All four runs executed **zero run_probe calls**: no reference case, reference-free
program registration or cross-edit replay was exercised. This was not a missing
tool/schema projection: content-hash-verified prepared provider requests offered
run_probe on every turn (A: 6 and 9 turns; B: 6 and 7 turns). All 13 B turns included
save_program; all 15 A turns omitted it. Model/tool identities and row journals
retained the intended arm distinction throughout execution.

Consequently there is no agent-authored probe whose setup, expected behavior or
unchanged cross-edit replay can be evaluated in this panel. Do not infer that the
feature is ineffective, that the agent should have used it, or that the successful
repairs resulted from program reuse. The advertised feature was unused.

Both paired acceptance outcomes tied, with no observed public regression:
**INCONCLUSIVE** for task improvement and **NOT_EXERCISED** for the proposed
mechanism. These are exposed development tasks, not unseen/general evaluation.
The earlier failed Darts run remains a separate immutable observation, not the A
control; its failure does not convert these successes into a feature improvement.

Keep the selected baseline at probe-policy none. The USD 12 allocation is closed;
unused funds do not authorize new tasks, prompt reminders, retries or more rows.
No additional paid comparison or default adoption follows. The unresolved question
is whether the capability helps when an agent actually chooses a valid public
experiment across an edit; this panel does not answer it or queue a new experiment.

## Evidence identities

External root: `C:\pt\runs\probe-replay-ab-20260930-v1`.
Panel journal: `runs/run_dev_4165fca2df444a36.jsonl`.
Independent closed audit: `audit/runs/run_dev_988e85bddf624aeb.jsonl`.
Proposal/approval/preflight root: `C:\pt\preflights\probe-panel-20260930`.
Proposal/approval journal: `runs/run_dev_1bbb0e4ac9764772.jsonl`.
Proposal hash: `sha256:104d99f9fc9592cddfd8d50870b1babe970852d5766899341e26b12764dc5bac`.
All generated records remain external append-only, hash-chained dev-run-v1 state.

| Row | Run ID | Submitted patch SHA-256 |
| --- | --- | --- |
| 1 | run_dev_7868d23d23534098 | a988e69d5ba9753a1b2f2977c47908db322e9ad0161dd0a7e226c4f16f5d164e |
| 2 | run_dev_8019d419050b4b7d | 8bb3c18d549e5048bf81dc7217d5d684afa26066cb9cecdfff38180a400bb4f1 |
| 3 | run_dev_c2a15bbfa60e405b | 1335cfb4998f013fdc7fd3a62f4e23d20933db137493ca5838847869d667bb61 |
| 4 | run_dev_89bb0839f1044f88 | 9ed57db44dfe9023bb8031e51e2b85581ade121733f1265feef5140d5e177310 |

The audit verifies all journal chains, prepared-request and submitted-patch hashes,
shared runtime identity, completed call accounting, public check/diff bindings and
arm-specific schema exposure. It makes no new provider call and does not rewrite
isolated evaluator outcomes or earlier historical evidence.
