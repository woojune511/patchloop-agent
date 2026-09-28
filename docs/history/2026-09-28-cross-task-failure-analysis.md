# Cross-task failure analysis: existing evidence only

## Finding

The narrow hypothesis, repeated reuse of a mathematically refuted self-authored
oracle, is established for toqito only in this reviewed corpus. It is not established
as the dominant general coding-agent failure. A broader evidence-to-decision gap
appears across toqito, AnyIO, Pydantic and HF Hub, but these are different mechanisms,
not four demonstrations of one causal explanation or one effective remedy.

No new model calls, Docker runs, candidate executions, evaluator runs, harness changes
or prompt changes. This retrospective review was requested instead of further toqito work.

## Corpus and weighting

Selected five recent completed fresh-run groups, including successful tasks: planning
ON/OFF, first-plan timing, planning regression, corrected-environment AnyIO fresh solves,
and the original-input pilot. These contain 27 unique run IDs across eight task families.
Reviewed current records, metrics, public behavior audits and selected action timelines;
verified 28 timeline/delivery artifact hashes against their existing public audits.
This was not a fresh exhaustive audit of every native model input or all project history.

| Task | Fresh runs | Recorded acceptance | Public process observation |
| --- | ---: | --- | --- |
| Pydantic | 8 | 3 PASS / 5 FAIL | Generic field-mode condition substituted for provider opt-in in five patches; successful patches preserve provider-specific scope. Ordinary-profile discriminator not independently probed. |
| HF Hub | 8 | 8 FAIL | Public forwarding failures repaired; all ultimately pass registered checks. Explicit endpoint versus constructor-resolved default remains an untested public-source concern. |
| AnyIO | 4 | 2 PASS / 2 NOT_RUN | Failed preservation/repair plus exhausted budget; earlier probe dependencies missing. Corrected environment still yields one unsupported repair premise and a malformed diagnostic. |
| Fromager | 2 | 2 PASS | Parent ownership traced correctly; surviving-parent/ROOT references preserved. |
| pgmpy | 2 | 2 PASS | Stable graph snapshot scoped to each conditioning round. |
| toqito | 1 | 1 NOT_RUN | Edit exhausted completion budget; separate public audit establishes bad expectation and patch semantics. |
| MontePy | 1 | 1 PASS | Universe property/default bookkeeping traced into a successful local repair. |
| darts | 1 | 1 PASS | Fitted encoder output columns used in a successful mapping repair. |

These counts are an inventory, not a pooled success-rate estimate. Sixteen of 27
runs concern only Pydantic/HF; all 13 submitted acceptance failures in this selected
fresh corpus are from those two tasks. That concentration is partly our sampling
history, not evidence that their mechanism dominates unseen problems. Three NOT_RUN
results are resource-limited, not submitted wrong answers. Task versions, policies,
runtime hashes and dependencies differ. Only the three original-pilot tasks use the
pinned original benchmark evaluation; other task-package scores are not interchangeable.

Supplied-candidate repairs, toqito checkpoint continuations, response samplers and
operator replays are supporting process evidence only, never additional fresh tasks.
Earlier model/runtime groups and stopped collections are outside this bounded review;
absence here is not absence throughout project history.

## Failure mechanisms and strength of evidence

1. **Self-authored expectation treated as truth: narrow evidence in toqito.**
   Wrong conditioning and an overgeneral CQ formula influenced repair decisions;
   later responses reused the formula despite contrary observations in actual input.
   Multiple samples from one task remain one task-family observation. Other tasks
   mostly did not generate mathematical oracles, so this review cannot estimate the
   frequency of this failure conditional on oracle construction.
2. **Unmeasured premise promoted to a confirmed cause: directly observed in AnyIO.**
   N1 call 3 measured shared-runner survival and later test resumption. Call 4 says
   the probe confirmed caller cancellation, although that state was not measured.
   The condition-based repair fails public interrupt cases. Crucially, call 9
   acknowledges interruption without caller cancellation and revises the premise.
   This is an inference error followed by unsuccessful recovery, not proven persistent
   reuse of a contradicted oracle. A passing seeded AnyIO repair also contained an
   unnecessary-branch explanation not established by observations; not a new task failure.
3. **Applicability/preservation distinctions lost: public evidence in Pydantic/HF.**
   Pydantic timing PB1 call 2 asks whether the generic field-mode change is too broad,
   then introduces provider opt-in; PB2 instead edits the shared field-mode gate even
   after receiving provider/profile source. Both pass public checks, acceptance differs.
   HF repairs public missing-forwarding failures but does not independently inspect
   whether stored self.endpoint represents explicit input or a constructor default.
   These observations identify scope/verification gaps. They do not establish the
   private failing assertions or prove one hidden-failure cause.
4. **Probe construction can block observation: at least AnyIO and toqito.**
   AnyIO N1's wrapper-name assertion fails before instrumentation is installed.
   Toqito has syntax and exact-float setup failures. This broader category repeats;
   exact floating-point equality specifically is documented only in toqito here.
   A generic float example therefore is not yet established as the highest-value fix.
5. **Environment and resources are independent axes.**
   Earlier AnyIO probes lacked pytest/_pytest; the exact timeout path was not proven
   by that inventory alone. Corrected-environment N1 still fails, so environment
   readiness is necessary support rather than evidence of reasoning competence.
   AnyIO (two runs) and toqito (one) stop at cost/output limits without submission.
   Public failed repairs can coexist with resource-limited NOT_RUN. Wheel preparation
   and operator pre-dispatch binding errors are preparation incidents, not agent answers.

## Successful cases matter

Fromager and pgmpy preserve the relevant ownership/temporal distinctions from source
without custom probes; MontePy and darts also succeed with source reads and existing
checks. Pydantic has scope-correct patches, and AnyIO N2 successfully uses source and
observations while limiting its completion claim. Thus neither missing probes nor
short verification alone diagnoses failure. Requiring more probes universally would
add cost to successful paths without evidence that it addresses the actual bottleneck.

## Decision

Close toqito-specific investigation and pause the proposed float-guidance change.
Do not promote expectation-reconciliation advice or another generic warning on these
results. The transferable diagnostic question is whether an important repair or
preservation claim is backed by a source fact, an observation, or only an assumption;
this is an analysis lens, not an implemented runtime gate.

Existing evidence supports recurring scope/inference/verification gaps beyond toqito,
but cannot rank their prevalence on new tasks. The next evidence need is task diversity
under a fixed harness, with fresh tasks as the unit of comparison; no new experiment
was designed, authorized or run in this analysis-only turn. No hidden tests were used
for causal tuning, and all existing outcome labels remain unchanged.

## Evidence

External inventory: C:/pt/analyses/cross-task-failure-audit-20260928-v1/report.json;
run_dev_crosstaskaudit binds its source hashes, unique rows and exclusions.

- [Planning ON/OFF](2026-09-26-planning-off-comparison.md).
- [First-plan timing](2026-09-27-after-source-planning-comparison.md).
- [Three-task regression](2026-09-27-planning-off-regression.md).
- [AnyIO fresh solves](2026-09-27-anyio-fresh-solve.md).
- [AnyIO process audit](2026-09-27-anyio-observation-process-audit.md).
- [Public-check scope](2026-09-26-verification-scope-audit.md).
- [Original pilot](2026-09-28-original-pilot-results.md).
- [Toqito reconciliation](2026-09-28-expectation-reconciliation-results.md).

Validation is limited to artifact identities, inventory consistency and documentation.
No production code changed; runtime tests, mock smoke and benchmark replays were not run.
