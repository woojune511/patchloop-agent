# Positive-result guidance: fresh repair comparison

Date: 2026-10-03 KST. Allocation closed after all eight authorized fresh solves.
Execution commit: 943a41ded361d00e8cad252f7d214d6c3f5a43aa.
Every run is official=false and claim_eligible=false.

## Decision and evidence boundary

Preserve the selected baseline. B had one more accepted solve overall, but did not
resolve more tasks in both repetitions, as the frozen decision rule required.
Repetition 1 was A 0/2 versus B 1/2; repetition 2 was A 1/2 versus B 1/2. No A success
was lost. B used 53.2% more recorded cost and 42.8% more elapsed time, exceeding both
25% tradeoff triggers. The correctness criterion already fails, so the observed
extra solve does not justify a default change with this additional overhead.

Positive-result guidance was exercised and produced useful observations. This is
not evidence that the principle is ineffective: on task 1733 B succeeded twice,
while A succeeded once. It is also not evidence of general superiority or a complete
positive-verification routine. These are two development-exposed tasks, two fresh
repetitions per arm, with varied repair trajectories and incomplete final probes.
The existing baseline also produced an accepted 1733 repair without a probe.

The investigation changed the decision from an untested guidance proposal to a
live-tested intervention that misses its adoption threshold. It preserves the
baseline and closes the allocation. No next prompt variant, execution-path rule,
preservation rule, compulsory probe, new annotation or completion gate is selected.

## Question, intervention and fixed scope

The [preparation and predicate replay](2026-10-03-positive-verification-preparation.md)
established why this question matters: a symptom-only check accepted other wrong
output, whereas an unchanged elicited expected-output predicate distinguished all
four public controls. Its old quote rejection and NOT_RUN record remain unchanged.
Predicate authorship alone did not establish autonomous selection or correct repair.

The question was whether one paragraph teaching independent positive expected
results changes actual verification and final task correctness. Alternatives were
failure to select the check, incorrect invocation, correct observations followed by
an incorrect repair, or baseline already finding the same useful repair.

A used the selected brief-v1 instructions. B replaced only its generic final
paragraph with guidance to assert public expected results, preserve relevant output
content/layout, normalize only permitted differences, use properties for multiple
valid outputs, and distinguish setup uncertainty from observed behavior. System
instructions outside that paragraph, tools, state, task inputs, public dependencies,
evaluation and resource limits were held fixed. Runtime defaults were not changed.

The human explicitly approved two dev-train SQLFluff tasks, 1733 and 1625, A/B twice
each, with gpt-5.4-2026-03-05, xhigh, 25,000 desired output tokens. Each row had caps
of USD 3, 40 model calls, 100 actions, four accepted edits and 1,800 seconds. The
invocation cap was USD 24, using the repository .env credential file. Policies were
segmented-v1/result-or-size-v1, brief-v1, probes enabled with policy none,
repair-recheck, protected-v1 and per-call-v1. Existing prepared sources, dependencies
and digest-pinned images were reused. No image acquisition occurred.

Order was frozen as shown below. Every row started from a fresh base workspace;
prior patches, controls and grading results were not supplied to the solver.
The wrapper restored ordinary instructions after each row. No provider retry,
row replacement, resume, budget transfer or follow-up dispatch occurred. Count and
usage settled for every row; there was no resource or infrastructure censoring.

## Results

Original acceptance is the registered isolated task grade. Public example means
the separate, pre-dispatch-frozen operator program applied to the submitted patch:
complete expected SQL lines for 1733, and empty L031 results for both explicit TSQL
examples for 1625. Both programs reproduced failure on the unchanged base. They
ran after the entire paid batch, outside solver context, against hash-verified
submitted workspaces. Their results do not replace original grades.

| Row | Original acceptance | Public example | Cost USD | Elapsed seconds | Model calls | Probes |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 1733 A1 | FAIL | FAIL | 0.4344105 | 252.637 | 6 | 0 |
| 1733 B1 | PASS | PASS | 2.8073370 | 1586.128 | 24 | 5 |
| 1625 B1 | FAIL | PASS | 0.6917635 | 607.277 | 12 | 1 |
| 1625 A1 | FAIL | PASS | 0.7089485 | 591.661 | 8 | 0 |
| 1733 B2 | PASS | PASS | 1.6127725 | 853.870 | 17 | 4 |
| 1733 A2 | PASS | PASS | 1.0377605 | 565.561 | 13 | 0 |
| 1625 A2 | FAIL | PASS | 1.5017235 | 1004.107 | 17 | 1 |
| 1625 B2 | FAIL | PASS | 0.5303265 | 398.945 | 10 | 1 |

| Measure | A | B |
| --- | ---: | ---: |
| Completed / submitted | 4/4 | 4/4 |
| Original acceptance | 1/4 | 2/4 |
| Frozen public examples | 3/4 | 4/4 |
| Final-diff public regression | 4/4 | 4/4 |
| Sandbox safety | 4/4 | 4/4 |
| Recorded cost USD | 3.6828430 | 5.6421995 |
| Elapsed seconds, summed | 2413.966 | 3446.220 |
| Model calls / tool actions | 44 / 78 | 63 / 108 |
| Probe invocations | 1 | 11 |

Total: eight completed and submitted, USD 9.3250425, 107 model calls, 186 tool
actions, 12 probes, 5,860.186 summed row seconds. All final public regression and
sandbox-safety checks passed. These axes do not establish semantic correctness.
The first 1733 A patch still produced the wrong public output. All four 1625 patches
passed both frozen public examples despite failing original acceptance.

## Public trajectory review

- **1733 B1:** Five probes supplied causal observations. One traced indentation
  reaching eight spaces, L039 reducing it to five, and a later pass reaching nine.
  The agent changed L039, then removed its earlier L036 edit after regression
  failures. Original acceptance and operator replay passed. The successful repair
  followed executed discrimination, but no full expected-output assertion ran on
  the final diff. One diagnostic assertion failed after printing useful observations;
  that exit is not evidence of rejecting an incorrect repair candidate.
- **1733 B2:** An initial probe contradicted the idea that L036 retained the original
  separator space. The first edit copied existing indentation. A complete string
  comparison against the issue's expected SQL and a plain SELECT example passed,
  while public regression failed. A narrower edit passed regression and acceptance.
  An earlier probe raised a constructor TypeError; the final-diff probe raised
  TypeError while processing a setup value, before observing behavior. Thus complete
  expected-output verification is demonstrated on the intermediate diff only.
- **1733 A2:** Public regression feedback led baseline to narrow its indentation-copy
  condition. It passed original acceptance and operator replay without any probe.
  The successful repair capability therefore exists in A as well as B.
- **1625 B1/B2:** Both checked the current diff through a public API. B1 asserted no
  L031 on the reported TSQL query and preserved L031 on an ANSI alias query. B2
  asserted no L031 on no-alias and standalone-alias TSQL variants, and retained L031
  on a joined variant. Both final probes passed; both original task grades failed.
- **1625 A2:** Three edits and regression failures preceded a probe that showed equal
  top-level and recursive table counts. That observation weakened its repeated
  traversal explanation. Its fourth edit passed public regression and the frozen
  public examples, but original acceptance still failed.

B selected more probes, and its expected-output principle was sometimes used.
Probe count, successful execution and setup comparisons alone are not improvement
evidence. In particular, a positive result on an earlier diff or a probe that fails
before observing behavior does not verify the final submitted patch. Neither extra
fields nor a compulsory probe would resolve the demonstrated 1625 acceptance gap
merely by checking the same examples again.

The unresolved question is the boundary between 1625's explicit public requirement
and the remaining evaluated behavior. The present evidence does not decide whether
the missing coverage is another semantic requirement or a task/evaluation scope
difference. Original grades are preserved. Clarifying that boundary requires a
separate specific evidence question; no grading change, hidden-data projection,
additional comparison or automatic paid follow-up is authorized by this record.

## Reconciliation, artifacts and validation

External evidence root: C:/pt/analyses/positive-verification-20261003-v1.
Live row state: C:/pt/pv1live01/<row>/; no generated state was put in the repository.

- panel/packet.json, preflight.json, authorization.json, result.json and the
  run_dev_positivepanel hash-chained journal bind scope, approval and all outcomes.
  Packet SHA-256: bfdbaa3fa1a0b9b05b0a49236c1fe69b6a3ffb136c5f917c6233d7b388999c58.
- public-programs.json and public-base.json were frozen before dispatch;
  public-final.json contains the eight post-batch assessments. Submitted patch
  hashes were checked before and after read-only sandbox execution.
- audit.py / audit.json reconcile all child journal chains, actual A/B instruction
  text in every recorded model turn, model/runtime/task hashes, submitted and
  evaluation artifact hashes, current-diff checks, settled usage and row/invocation
  caps. Audit SHA-256: d58e6a22a691a0c2521a15a297d4185f0d0469a7bcd8743b75eff923af4046ec.
- decision.py / decision.json apply the declared repetition and overhead rules and
  record manual public-trajectory interpretation. Audit and decision have separate
  append-only dev-run-v1 journals. These stages made no provider calls.
- Pre-dispatch validation: final focused tests 27 passed in 16.86 seconds; full
  suite 4,013 passed, 16 skipped in 1,391.60 seconds; Ruff and diff checks passed.
  The full suite preceded one summary-output regression, covered by the final
  focused run. The preparation record links exact reports and the successful mock
  smoke, whose safety result remains NOT_RUN. Live sandbox safety here is 8/8 PASS.
- Documentation closeout: all five documentation tests passed. Report:
  C:/pt/validation/positive-closeout-docs-20261003.xml. Diff checks passed; current
  status and the history index remain within their byte limits. This closeout
  changes documentation only; the tested production runtime is unchanged.

All eight paid solves, their isolated evaluations and eight operator public replays
were executed. Default adoption, later domain-knowledge interventions, validation/
held-out tuning and claim-producing evaluation were not executed. The preparation
record and all older reports retain their original bytes and interpretations.
