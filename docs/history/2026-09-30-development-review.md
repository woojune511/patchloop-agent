# Development review: close the ablation loop, retain the working agent

## Decision

Stop the repeated prompt/context/prior-decision diagnostic series. Do not implement
another memory field, compulsory explanation, automatic probe gate, source-authority
ranking or default context removal from these results. This review found no newly
established, unresolved cross-task runtime contract defect that warrants such a fix.
Keep the working baseline. There is no new experiment or feature queued by this review.

This is not a conclusion that the agent is good enough or cannot improve. It is a
decision that the available evidence does not yet select an effective implementation.
The current-status snapshot is shortened to preserve this decision rather than making
successive historical diagnostics look like an active development queue.

## Scope and evidence strength

Reviewed the 24-run six-task boundary panel, 12-run basic/current panel, three-task
original-input pilot and named AnyIO/tox/toqito/HF follow-ups. Together these records
mention twelve task identities: Pydantic, HF Hub, Fromager, Loguru, PDM, pgmpy,
pyfakefs, AnyIO, tox, toqito, MontePy and darts. This is not a new twelve-task evaluation.
Fresh, seeded, continued, response-only and post-run operator evidence remain separate.

Rechecked the saved panel aggregates, 45-journal evidence/action inventory and the
stricter survey's 95 source-journal hashes and chains. These inventories overlap and
include historical runtime versions. Counts below are not independent samples or
estimates of current-baseline failure prevalence. No hidden tests/reference patches
or private failure details were read; only saved acceptance/safety summaries were used.

## Task-level disposition

| Task(s) | Strongest relevant observation | Development disposition |
| --- | --- | --- |
| Pydantic | All four panel repairs passed public checks but failed acceptance; public post-run replay exposes an overbroad provider/profile condition in all four | Confirmed public boundary/coverage gap, but no proven general harness correction |
| HF Hub | Same panel pattern; three patches lose explicit-versus-ambient distinction, fourth repairs it yet retains an unexplained acceptance failure | Distinguish known boundary error from residual unknown; no claim that one check fixes the task |
| PDM | One panel failure; proposed missing-path explanation did not fail the public replay | Cause unresolved; reject this explanation as a basis for code changes |
| pyfakefs | Current run reacts to broken-symlink public regression, narrows a catch and passes; Basic passed public checks but failed acceptance | Positive repair capability; a bundled single comparison cannot attribute gain to one feature |
| AnyIO | Registered lifecycle failures lead to same-check recovery; setup-target omissions coexist with saved-patch acceptance PASS | Do not convert unanswered setup questions into demonstrated task failures |
| tox | Seeded missing-default probe leads to targeted handler repair; response reviewers identify the mismatch even without retained decisions | Counterexample to universal inability to use optional evidence; not a fresh-solve improvement |
| toqito | Original attempt hit cost cap before validation; separate continuation shows unsupported expected-value/applicability reasoning and later unfinished verification | Resource censoring, reasoning error and check coverage are distinct; not a universal memory defect |
| Fromager, Loguru, pgmpy | Successful panel controls; more process prose did not improve acceptance | Preserve these paths; no evidence-based new feature from the controls |
| MontePy, darts | Original-input pilot completes short repair/check paths and passes original isolated evaluation | Environment/repair can work with current capabilities; no added procedure needed from these traces |

Sources: [boundary panel](2026-09-29-boundary-pair-panel-results.md),
[basic/current](2026-09-28-basic-current-baseline-comparison.md),
[public replay](2026-09-29-boundary-discrimination-replay.md),
[strict delivery audit](2026-09-30-retained-counterexample-audit.md),
[original pilot](2026-09-28-original-pilot-results.md),
[toqito mechanism](2026-09-28-general-failure-mechanism.md).

## Common problems versus implementation candidates

**Verification coverage is the clearest repeated weakness.** All 24 panel runs
submitted and reached evaluation with safety PASS and no infrastructure/resource
NOT_RUN. All final public checks passed, including nine acceptance failures. Public
replay confirms missing distinguishing inputs for Pydantic and HF; it does not explain
all nine failures. The instruction produced more explicit cases but no reliable repair
benefit; none of those 24 agents ran a probe. Absence of calls is not proof that probes
were unavailable. Adding those operator-authored cases to task packages could improve
those packages' checks, but would change the information supplied to the solver and
would not establish a general harness improvement. No such check expansion is made.

**Failure handling is not uniformly broken.** Eleven registered failure events across
eight trajectories and three tasks led to edits and later same-check PASS. This does
not prove task correctness (HF is a counterexample), and blocking gates/selection of
completed trajectories confound channel comparisons. Only one seeded HF episode meets
the strict criterion for a delivered current counterexample left in an unchanged final
patch. HF's other treated episode and tox repaired the identified public behavior.
The record therefore does not justify forcing every model-authored failed assertion
into a blocking product-defect state. Source: [cross-task audit](2026-09-29-cross-task-evidence-action-audit.md).

**Probe failures have heterogeneous causes.** The deduplicated historical screen has
56 unsuccessful outcomes: 22 dependency/helper imports, 4 setup validations, 2 syntax,
2 API/inspection, 1 sandbox restriction, 2 candidate exceptions, 2 numerical expectation
disagreements, 1 tox mismatch and 20 lifecycle/applicability-unresolved outcomes.
These are not 56 incorrect repairs. The 22 import outcomes are not evidence for 22
current environment defects: repeated historical paths and old profiles matter.
AnyIO's missing pytest dependency was reproduced and corrected; exact comparison,
nonexistent API and syntax mistakes need different remedies. A single probe wrapper
cannot fix the validity of a mathematical oracle. Sources:
[survey](2026-09-29-optional-probe-survey.md),
[readiness correction](2026-09-27-anyio-probe-readiness.md),
[probe construction](2026-09-28-probe-construction-analysis.md).

**Confirmed plumbing bugs already received narrow fixes.** Size-triggered recount
admission and inherited execution-receipt lineage were corrected and locally tested.
They are legitimate engineering fixes, but diagnostic/fork-path repairs are not evidence
of higher agent accuracy. Do not reopen them as new research hypotheses without a
new failure. Source: [boundary fixes](2026-09-29-observation-boundary-fixes.md).

**Resources are not the dominant cause in the completed panel.** Toqito's original
USD 1.20 cap left no useful completion allowance; the unsubmitted candidate was NOT_RUN.
The successful controls and 24 completed panel episodes do not support globally
increasing budget or imposing an unvalidated completion reserve. A budget fix would
need its own observed resource failure and would still not establish semantic quality.
Source: [funding analysis](2026-09-28-minimum-completion-funding.md).

## Why the recent loop is closed

Generic pair instructions, disposition requests, completion-wording removal, broad
context removal and retained-decision removal did not select a robust default quality
improvement. Later studies mainly assessed isolated public responses on already exposed
checkpoints. Naming a discrepancy, retaining an ID, using a note or choosing a probe
is not an executed correct repair. More repetitions of slight framing changes would
not resolve this mismatch between the measured outcome and the product objective.

The prior-decision comparison did show successful tox judgment without those removed
explanations. It did not improve the target current-HF judgment; the one primary A win
depends on a borderline grade. These are useful negative findings, now closed, not
a reason to launch the next adjacent ablation. See [last results](2026-09-30-prior-decision-results.md).

## What would justify development again

A concrete implementation should start from a reproducible violation in the current
agent contract (missing/corrupted public output, wrong candidate binding, inaccessible
supported execution, or incorrect action/recovery handling), or a mechanism with a
specific predicted repair improvement. Identify the code owner and regression before
editing. Routine reproducible bugs need a focused fix/test, not another model A/B.

For a proposed quality intervention, the decision evidence must include executed
patch correctness, regressions and cost/time under a bounded approved run; public
reasoning grades are auxiliary. Task-specific diagnostics must stay labeled rather
than becoming undisclosed solver hints. Existing exposed tasks support regression
checks, not held-out generalization claims. These are criteria for future work, not
an instruction to start another investigation now.

## Record and validation

New external record: C:/pt/analyses/cross-task-development-review-20260930-v1/review.json,
hash-bound in run_dev_developmentreview. It records source hashes, panel recomputation,
11 recovery links, 56 category counts and 95 reverified journal chains. Prior histories
remain unchanged. No new model call, credential load, task/Docker execution, private
evaluation or budget allocation. Runtime code remains unchanged; documentation tests
validate the consolidated status and this follow-up. No runtime smoke was needed.
