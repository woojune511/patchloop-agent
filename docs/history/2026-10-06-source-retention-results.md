# Source retention comparison: 24k versus 48k

Date: 2026-10-06. CLOSED, official=false, claim_eligible=false.
Execution commit: `a36a0e3bb2ac81e56ab9458b1cf63efc7a2682a3`.
Evidence: `C:/pt/sretp02`; fresh solver states: `C:/pt/sretlive01/1` through `8`.

## Question and decision

The preceding [source review](2026-10-06-resource-budget-context-review.md) found
previously observed arithmetic disappearing before an unsuccessful SQLFluff edit.
An offline 48k projection recovered it. The [option preparation](2026-10-06-source-retention-option.md)
therefore made a larger retained pool available without changing the 24k default.
This comparison tested whether that availability benefit produced correct repairs
under the same resource limits, rather than treating more retained text as success.

Keep the 24k default. Both arms achieved 2/4 accepted repairs, all on pvlib.
48k cost 72.26% more and used 33.67% more aggregate row time. Its two SQLFluff
runs exhausted their row allocations without submission. The prespecified
two-additional-success threshold failed; no quality or cost tradeoff justifies
adoption on this scope. No adjacent variant or follow-up panel is queued.

This is two development-exposed tasks with two repetitions per arm, not eight
independent tasks, a new dev20 score, or a general SWE-bench accuracy estimate.

## Frozen execution

The user authorized the [exact design](../../.agent/source-retention-comparison.md)
with "실험 진행해줘". Both arms used the current-dev20 SQLFluff-1733 and pvlib-1072
packages, `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens, the exact
repository `.env`, and fresh repeat=1 requests. Only retained source differed:
A=24,000 versus B=48,000 characters. Source reads, prompt, source priorities,
segmentation, tools, model, task packages and other limits were unchanged.

Each row had USD 1.20, 40 model calls, 100 actions, four accepted edits and 1,800
seconds including 330 reserved for evaluation. The outer allocation was USD 9.60,
with no transfers. Four waves ran two distinct tasks in isolated processes with
separate clients, source copies, journals and ledgers. The shared admission stop
carried across waves. All eight rows started; no uncertainty stop occurred.

Probe replay remained off; ordinary probes, selected tests, additive Python tests
and repair rechecks remained enabled. The existing bounded protocol-correction
allowance was unchanged. No whole-run retry, resume, replacement, evaluator image
pull/build, cross-run memory or private evidence projection occurred.

Before dispatch, existing images passed import, public operation and selected-test
canaries. Operator-only public programs were frozen and calibrated: original
sources failed and saved successful agent submissions passed. SQLFluff compared
the complete issue output; pvlib checked timezone-aware and naive outputs, index
and name preservation, public rounded values and agreement within 1e-9. Calibration
programs and saved patches never entered fresh solver context.

## Results

| Row | Task | Arm / repeat | Submission | Registered / native | Public example | USD |
| --- | --- | --- | --- | --- | --- | ---: |
| 1 | SQLFluff-1733 | A1 | Yes | FAIL / FAIL | FAIL | 0.80301615 |
| 2 | pvlib-1072 | B1 | Yes | PASS / PASS | PASS | 0.11441205 |
| 3 | SQLFluff-1733 | B1 | No | NOT_RUN / NOT_RUN | NOT_RUN | 1.18830480 |
| 4 | pvlib-1072 | A1 | Yes | PASS / PASS | PASS | 0.14052960 |
| 5 | SQLFluff-1733 | B2 | No | NOT_RUN / NOT_RUN | NOT_RUN | 1.18312365 |
| 6 | pvlib-1072 | A2 | Yes | PASS / PASS | PASS | 0.11733090 |
| 7 | SQLFluff-1733 | A2 | Yes | FAIL / FAIL | FAIL | 0.43742115 |
| 8 | pvlib-1072 | B2 | Yes | PASS / PASS | PASS | 0.09519510 |

| Measure | A: 24k | B: 48k |
| --- | ---: | ---: |
| Accepted / allocated | 2/4 | 2/4 |
| Submitted | 4/4 | 2/4 |
| Graded FAIL | 2 | 0 |
| Unsubmitted, evaluation NOT_RUN | 0 | 2 |
| Settled USD | 1.49829780 | 2.58103560 |
| Aggregate row seconds | 1,790.069 | 2,392.844 |
| Model calls | 57 | 82 |
| Actual input tokens, including cached | 1,735,600 | 2,901,100 |
| Cached input tokens | 801,664 | 1,203,968 |
| Output tokens | 163,938 | 270,642 |

Total USD 4.07933340; unused USD 5.52066660 is closed. Batch wall time including
native assessment was 3,707.737 seconds (61m48s); subsequent operator public checks
and analysis are excluded. Aggregate row time includes preparation and registered
evaluation but excludes separate native assessment. These are observed times,
not a measured speedup against a serial control.

All six submitted patches had agreeing independent native verdicts and registered
safety PASS. Unsubmitted rows retain evaluation/safety NOT_RUN; cost exhaustion is
an unsuccessful allocated outcome, not an observed wrong-answer verdict. There
were no evaluation ERRORs or unstarted rows. Every count and provider call settled;
all row caps and the invocation cap held. No owned container remained at closeout.

## What the public traces show

**Wrong hypotheses survived passing regression checks.** A1 changed the L003
hanging-indent gate. Its first version failed regression; a narrower second version
passed 506 tests. A2 changed L036's whitespace deletion/newline insertion. It also
passed regression. Both submissions still put nine spaces before `my_id` where the
public issue requires eight. Neither reran the public behavior after its source
edit. At their finish decisions, `run_probe` and `run_tests` remained available,
with 14 and 23 optional model turns respectively. Submission was not forced by
the completion reservation in these two failures.

**48k was exercised but did not ensure the needed source stayed visible.** Both B
SQLFluff runs reached 48,000 retained characters, exceeding 24k in 34 and 31 prepared
contexts. First-edit selector replay exactly matched saved delivery hashes.
A1 had only observed L003 ranges 66-91, 140-260 and 320-610 before editing; its
missing later arithmetic had never been read. B1 had observed the entire file,
lines 1-799, but its first-edit request contained only 1-120 and 252-420. Increasing
capacity did not preserve all previously read parts of the active function.
The additional retained ranges and actual complete-request visibility are recorded
separately: retained-pool changes can duplicate text already present in history.
No rebuilt counterfactual request was dispatched or token-counted.

**The 48k SQLFluff rows spent their allocations before submission.** B1 made six
probes, including an invalid API call and a syntax error. At 33 calls, exploration
closed with the expected seven-model/eight-tool completion reserve. The next model
response consumed 25,000 output tokens without a tool call. Its existing one-time
protocol correction eventually edited L003's indentation replacement helper.
The public regression check passed, but after 36 calls the next minimum provider
request could not fit the remaining USD 0.01169520. B2 made seven probes and 33
model calls without any mutation. Its remaining USD 0.01687635 could not admit the
next request. Neither B run received a semantic acceptance verdict.

Probe nonzero exits are not all invalid programs: B2's action253 correctly failed
an assertion because the original output had nine spaces. Invalid setup/program
events were B1 actions144/320, B2 actions128/157, and A2 action134. The separate
`probe-exit-interpretation.json` clarifies the broad nonzero-exit counter originally
named `probe_execution_failures` in `summary.json`; original artifacts are intact.

**Test capability was selective, not globally disabled.** All four pvlib runs
added Python regression tests and passed native evaluation. A2 attempted to add a
YAML case to `test/fixtures/rules/std_rule_cases/L036.yml`; the registered additive
test contract rejected that fixture edit. The model then relied on the existing
regression suite instead of using an available probe or supported Python test.
The rejection explains why that proposed test did not run; it does not explain
away the later voluntary submission of an unverified hypothesis.

Pvlib's retained pools stayed below 24k in all four runs (maximum 15,763 characters).
Its four successes establish preservation on this control, not a larger-cap
mechanism. SQLFluff's two A failures, two B resource failures and changed search
paths leave sampling variation, source selection, source use, probe construction
and verification decisions intertwined. This pilot does not prove that larger
contexts universally hurt or identify a single sufficient repair intervention.

## Validation, evidence and remaining question

The comparison driver and relevant runtime/parallel/documentation checks passed:
49 tests in 31.66s, Ruff PASS, 48k mock isolated EVALUATOR_PASS with zero cost and
safety NOT_RUN. The unchanged runtime reused the previous combined full-suite
coverage of 4,340 passed / 19 skipped; that full suite was not repeated for this
diagnostic driver. Preparation corrected a local temp-directory access failure,
a selector that matched both solver/evaluator workspaces, and an overlong current
status page before paid dispatch. Those original records remain preserved.

The analysis first compared dispatch hashes directly to token-count hashes. For
cost-clipped output ceilings those intentionally differ. The final analysis uses
the exact selected count ID and `counted_request_hash`, and verifies actual input
tokens against both dispatch and response usage. No billing mismatch occurred.

Execution packet canonical hash:
`sha256:03395985c8ce1633ff01934e220da030b295418fa830216cea800841d24ec2b3`.
`closeout.json` file hash:
`sha256:d70f3c4da586f4e73c2447395a40de0b42ccff2568d65a01955e2dc61d9db558`.
It binds requests, calibration, validation, result, public checks, trace summaries,
selector replay, settled costs and validated journal chains. Individual public
decisions and source ranges are in `trace-row-*.json` and `retention-effect.json`.

The experiment preserves the 24k decision and weakens a capacity-only explanation.
The remaining engineering question is how to keep a repair hypothesis tied to an
executed positive public requirement while retaining enough resources to submit.
This record authorizes no new prompt, mandatory probe, automatic replay, ranking
model, context variant or paid run. Historical records and the user's AGENTS.md
change remain unchanged.
