# Darts public decision scope: investigation closed

Provider-free audit of the same saved A/B runs. No new model or task execution.
Keep the current baseline; no further Darts diagnostic or prompt comparison is
queued from this investigation.

## Question and method

The [mechanism diagnosis](2026-10-01-zero-width-ownership-diagnosis.md) explains
the task-local column loss. This follow-up asks whether public decisions identify
why verification omitted that boundary: was the nonzero-output premise explicit,
was a zero-width input considered then rejected, and what justified submission?

Revalidated A's 103-event and B's 131-event journals. Read all 9/10 action-start
public decisions, including their plans, note updates, mutation hypotheses and
expected behavior; compare with the two stored B probe programs and previously
validated execution results. Event numbers below are one-based JSONL ordinals.
No reasoning contents, encrypted continuation artifacts or private oracle were
accessed. These public explanations are observable statements, not a complete
account of the model's internal reasoning.

## Findings

| Question | A: previous guidance | B: assumption-directed guidance |
| --- | --- | --- |
| Stated repair expectation | Event 66: skipping drop_idx_ aligns maps, masks and counts; inverse should continue to round-trip | Event 64: skipping dropped categories keeps inverse mappings aligned with output width |
| Explicit premise that every original feature emits at least one column | Not found in audited public decisions | Not found in audited public decisions |
| Zero-width case considered and rejected | Not recorded | Not recorded; both programs use only ordinary multi-category cases |
| Scope assigned to regression | Event 80: existing naming/inverse tests pass, then submit | Event 78 initially plans to submit after regression; event 94 recognizes it does not exercise reported drop modes |
| Final submission basis | Event 96: regression PASS, no concrete remaining uncertainty | Event 124: ordinary first/if_binary probes and regression PASS, no remaining uncertainty likely to change submission |

Both runs anticipate preserved inverse behavior without explicitly stating or
testing the per-feature ownership condition needed when an output disappears.
That condition is the operator's source-derived explanation, not a verbatim model
belief. Neither record shows a deliberate rejection of the zero-width test.

A accurately describes preservation evidence from the regression file, then treats
the scoped repair as complete without direct drop-mode execution. B does distinguish
regression preservation from direct issue verification. It successfully corrects
its first probe's index expectation (event 109), but retains the same input domain:
one three-category feature with drop=first and one binary feature with drop=if_binary.
Those checks support their observed cases, not restoration of an original feature
with no surviving encoded column. B's decision to submit is broader than that
observed coverage; this does not mean it explicitly claimed all possible inputs pass.

## What the evidence resolves and does not resolve

The demonstrated failure is a missing boundary in verification followed by
submission of an incomplete repair. The source mechanism and selected public
counterexample are established. The records weaken a simple claim that B merely
mistook the registered suite for direct bug coverage: B expressly noticed that gap.
They also contradict inability to correct an invalid probe expectation.

They cannot distinguish failure to generate the boundary input, a narrower scope
judgment, overconfidence in the patch, or another internal selection process.
Successful source reads do not establish attention, and absence of a public
statement does not establish absence of internal consideration. No new delivery,
resource, tool-availability or runtime-contract defect is established here.

## Decision

Close this investigation without changing prompts, memory, tool quotas or submission
gates. The earlier guidance experiment already exercised direct checks without
improving the frozen patch results. More analysis of the same public decisions
cannot identify the missing internal causal distinction. A generic reminder or
another wording comparison would therefore lack new discriminating evidence.

Retain the zero-width case as operator regression evidence; do not silently add
it as a solver hint or redefine the recorded evaluation. Further improvement work
needs a new reproducible contract failure or a concrete mechanism with a predicted
repair benefit. This closes the present inquiry, not the broader correctness problem.

## Evidence and validation

`C:\pt\analyses\darts-decision-scope-20261001-v1\runs\run_dev_298f42b17c944304.jsonl`
contains source-journal hashes, exact action IDs, ordinals, public decisions,
mutation claims and probe programs. All three new events were read back through
hash-chain validation. Original artifacts remain unchanged.

Documentation layout/link/size tests (5), Ruff and diff whitespace validation
passed. No runtime code changed; runtime suite and mock smoke were not rerun.
Provider calls, credentials loaded, Docker/task executions and private evaluation: zero.
