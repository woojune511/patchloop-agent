# Full fixed dev20 on the frozen verification-reuse runtime

Date: 2026-10-31 KST. Status: CLOSED. All runs official=false, claim_eligible=false.

## Question and decision

The user chose a full 20 run after the [three-task reuse run](2026-10-31-verification-reuse-1411-results.md),
rather than another round of prompt changes aimed at residual repetition. The question
was which correctness, verification, completion and efficiency failures remained
across the entire fixed development-exposed roster. This matters because a passing
small panel and lower check counts do not establish broader repair correctness.

No solver intervention was made: runtime was frozen, and all tasks 1-20 were attempted
once in ascending order with two workers. Outcome selection, midway fixes, retries,
seed patches, earlier counterexamples and cross-run notes were excluded. The previous
three-task and older full 20 results are historical context, not matched causal controls.

Result: **11 independent PASS, 8 FAIL, 1 unsubmitted/NOT_RUN**. Nineteen submitted
candidates have safety PASS; task 18 has safety NOT_RUN. All 300 model calls and
302 input-count requests settled. Cost **USD20.2818755**, under the USD80 invocation cap; batch wall
**5,513.593 seconds (91m54s)**. Allocation is CLOSED, not_started=0, stopped=false.
Two completed counts exceeded the 60K input bound and triggered segmentation before
dispatch; the smaller requests were recounted. No transport/count/billing uncertainty,
SDK retry or additional independent evaluation occurred. The single deadline stop stayed task-local.

The evidence supports keeping the current implementation while prioritizing concrete
correctness and completion failures. Another generic reuse sentence or mandatory
probe gate is not justified. Task 14 demonstrated autonomous counterexample-driven
repair; task 8 retained a public failure confirmed separately after the batch. These
are distinct observations, not a causal estimate of the guidance's contribution.

## Frozen scope and preparation

- Execution HEAD: `1ec9198ad181400a0b5061902e4fc9fef67ac85f`; solver change: `1569ec49`.
- Runtime: `sha256:06b0bbc8bd933616c7e40495a87bdaf76207db10f477263d98bbb6ab0cb8e866`.
- Fixed checked-in `tasks/dev-train/current-dev20/1..20`, one fresh attempt each.
- `gpt-5.4-2026-03-05`, xhigh, 25,000 maximum output tokens; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`. No credential contents in evidence.
- USD4 per task / USD80 total, two workers, no transfers or retries.
- Per task: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds, with the
  same 330-second evaluation reserve inside that limit. Solver execution has a
  separate earlier deadline; task 18 stopped there, not after spending 30 full minutes.
- segmented-v1, result-or-size-v1, brief-v1, current agent, probes enabled/none,
  probe-recheck none, repair-recheck, protected-v1, per-call-v1, public-checks-v1.
- Exact input counting before dispatch, zero SDK retries, default service tier.
  Count/transport/billing/continuation/cleanup uncertainty would stop new admissions;
  settled task failure or limit exhaustion remains row-local.

[Official Standard pricing](https://developers.openai.com/api/docs/pricing) was
rechecked on 2026-10-31: USD2.50 input, USD0.25 cached input and USD15 output per million
tokens. The runtime 60K input bound stays below the 272K tier boundary.

All 20 source/task/dependency contracts, local images, and public import/operation/
selected-test canaries passed before provider dispatch. No Docker startup, image
pull/build, host dependency installation or prepared-dependency modification occurred.
SQLFluff public checks did install a bundled example plugin into temporary sandbox
directories. Preparation initially stopped at task 13:
the older dependency descriptor omitted task-required `pylint==2.12.2`. The existing
compatible caller asset was selected and its 788 files verified. No provider call had
occurred. Original failed-preparation bytes were retained; passed canaries 1-12 were
reused after exact request/task/source/image and durable-receipt verification. Canaries
13-20 were then executed. This is preparation evidence, not solver verification.

The final manifest binds 84 inputs. Reviewer validation checked all 20 requests,
capabilities and dependencies. Task 13's execution profile stayed python310;
some other descriptors preserve an older wheel-resolver image as provenance, which
must not be confused with the pinned execution image.

## Per-task results

Row seconds include each scheduler row's work; parallel rows must not be summed into
batch wall time. Actions include harness-origin rechecks. Edits count accepted
mutations; rejected attempts are not accepted edits.

| Task | Independent acceptance / safety | Calls / actions | Edits / probes | Row seconds | USD |
| --- | --- | --- | --- | --- | --- |
| 1 marshmallow-code__marshmallow-1343 | PASS / PASS | 12 / 12 | 1 / 2 | 454.324 | 0.6743640 |
| 2 pvlib__pvlib-python-1072 | PASS / PASS | 10 / 13 | 2 / 2 | 367.578 | 0.5875370 |
| 3 pvlib__pvlib-python-1154 | PASS / PASS | 9 / 11 | 1 / 1 | 401.543 | 0.5194725 |
| 4 pvlib__pvlib-python-1606 | PASS / PASS | 7 / 10 | 1 / 0 | 396.229 | 0.5078010 |
| 5 pvlib__pvlib-python-1707 | PASS / PASS | 7 / 7 | 1 / 1 | 359.541 | 0.4703940 |
| 6 pvlib__pvlib-python-1854 | PASS / PASS | 7 / 10 | 1 / 1 | 325.973 | 0.3899690 |
| 7 pydicom__pydicom-1139 | FAIL / PASS | 10 / 10 | 1 / 1 | 281.882 | 0.4613695 |
| 8 pydicom__pydicom-1413 | FAIL / PASS | 17 / 31 | 1 / 3 | 676.720 | 1.2657615 |
| 9 pydicom__pydicom-1694 | PASS / PASS | 11 / 16 | 2 / 3 | 386.425 | 0.6841835 |
| 10 pydicom__pydicom-901 | FAIL / PASS | 22 / 40 | 2 / 2 | 716.633 | 1.4918800 |
| 11 pylint-dev__astroid-1196 | PASS / PASS | 13 / 18 | 1 / 2 | 434.247 | 0.7567635 |
| 12 pylint-dev__astroid-1268 | FAIL / PASS | 10 / 18 | 1 / 2 | 200.015 | 0.5047125 |
| 13 pylint-dev__astroid-1333 | FAIL / PASS | 37 / 69 | 3 / 4 | 952.267 | 2.9629410 |
| 14 pylint-dev__astroid-1866 | PASS / PASS | 10 / 13 | 2 / 2 | 434.389 | 0.7443040 |
| 15 pyvista__pyvista-4315 | PASS / PASS | 8 / 9 | 1 / 1 | 437.562 | 0.6412160 |
| 16 sqlfluff__sqlfluff-1517 | FAIL / PASS | 23 / 39 | 2 / 1 | 891.724 | 1.7657750 |
| 17 sqlfluff__sqlfluff-1625 | FAIL / PASS | 21 / 28 | 2 / 0 | 605.919 | 1.2336975 |
| 18 sqlfluff__sqlfluff-1733 | NOT_RUN / NOT_RUN | 37 / 61 | 2 / 10 | 1465.769 | 2.8282275 |
| 19 sqlfluff__sqlfluff-1763 | FAIL / PASS | 20 / 41 | 2 / 1 | 648.178 | 1.3744920 |
| 20 sqlfluff__sqlfluff-2419 | PASS / PASS | 9 / 16 | 1 / 0 | 342.431 | 0.4170145 |

Totals: **300 calls, 472 completed actions, 30 accepted edits, 39 probes, 30 required
checks and 7 selected-test actions**. Two mutation attempts were rejected. All 19
submitted deliveries remain `unverified_delivery`: registered original-case proof,
public observations, submission and independent acceptance are separate.

Input tokens 8,584,367, including 4,134,272 cached; output tokens 541,538. Provider dispatch
occupied 8,606.337 seconds out of 10,779.349 summed row seconds, about **79.8%**. Public
action intervals total 913.808 seconds. These are descriptive concurrent-work metrics,
not time that can all be eliminated. Reasoning content was not read. Repeated-model
performance, a causal speed gain and held-out generalization remain unmeasured.

## What the public evidence shows

### Autonomous counterexample and repair: task 14

After 1,380 public tests passed, the agent tested a sibling string operand with a float
format specifier. It observed `ValueError`, despite the helper catching/printing it
and returning execution PASS. The actual next input delivered that output while
submission eligibility was already ready. The agent added production `ValueError`
handling and an asserting regression, passed 1,381 tests, and replayed the same helper
with its normal control preserved. Independent acceptance and safety passed. This
is the requested observation-to-repair sequence; it is not proof that this particular
guidance caused it or that the original pylint caller was replayed.

### Public residual defect: task 8 and the separate operator follow-up

The agent's first bytes helper succeeded. It then changed input representation to
bytearray/array, found a conversion failure, and repaired that different path. The
candidate passed 214 public tests and its changed-representation replay. It never
inspected the upstream `DataElement.value` setter branch that splits bytes containing
`0x5c` before `_convert_value` runs. The new conversion logic operates too late for
that path. Independent acceptance failed; private failure details were not inspected.

After the full batch CLOSED, a separate operator-only public diagnostic executed
exactly two sandbox programs: unchanged base and the exact submitted candidate, with
three identical cases each through `Dataset.add_new` and `Dataset.save_as`. It used
`array('H', ...).tobytes()` for the public report's bytes-producing `tostring()` intent.
No model, private evaluator, retry, image acquisition or solver feedback was involved.

| Public case | Base | Submitted patch |
| --- | --- | --- |
| OL normal bytes `01000200` | bytes, VM1, saved | bytes, VM1, saved |
| OB bytes `01005c00` | bytes, VM1, saved | bytes, VM1, saved |
| OL bytes `01005c00` | MultiValue, VM2, save TypeError | MultiValue, VM2, save TypeError |

Both controls passed in both arms; the target still raises a bytes-like-object
`TypeError` during `Dataset.save_as`. The predicted public residual path is therefore
**executed and confirmed**. This is an operator-discovered defect, not autonomous
agent discovery or proof of the private evaluator's exact failing assertion.
The submitted patch was not corrected or independently reevaluated.

### Successful checks can support an incomplete or weakened behavioral oracle

- **7:** The explicit PersonName iteration/containment caller passes 39 tests and a
  substantially overlapping helper. Broader interface/encoding behavior was not
  established; the exact independent failure remains unknown.
- **10:** A valid additive-test rejection of module-level imports rolled back the
  first batch. The stronger proposed test would have emitted a caller log record
  and asserted exactly one output; it never executed. The accepted local-import test instead checked logger level
  and handler type. The stronger proposal was delivered immediately after rejection,
  but absent from later public inputs; the original issue remained visible. This is
  a retention gap plus narrowed plan, not proof of forgetting or its causal effect.
  Actual emitted-record behavior was never tested. Independent failure attribution
  and the explicit-debug output compatibility question remain unresolved.
- **12:** The exact `Unknown().as_string()` AttributeError was reproduced and removed.
  The agent chose empty-string semantics by analogy with EmptyNode and asserted that
  choice. The issue does not specify the exact string; output correctness beyond
  crash removal was not established. Independent failure cause is unknown.
- **13:** Public checks passed while actual pylint callers still failed. The agent
  continued through two caller/interface failures and three production edits; final
  replay removed the comparable F0010 and traceback. Independent acceptance still
  failed. Formal original-case binding was absent; that is not absence of all caller
  reproduction. The final input omitted the oldest F0010 observation, but final
  wording about the "exact" report may refer to environment/path identity.
- **16:** The first patch made a disallowed trailing delimiter succeed; the public
  suite caught a real success-guard regression. The second edit restored those
  guards and preserved original input in failure results; 167 tests passed. The
  subsequent helper returned a whole-file parsing error without crashing. The
  public issue permits reporting invalid doubled terminators, so this observation
  alone does not establish a residual violation or explain independent FAIL.
- **17:** The reported simple no-join case and a join control pass. The final guard
  uses one recursively collected FROM element as a proxy for no join. Nested-query
  scope is an unexecuted concern, not a demonstrated evaluator failure cause.
- **19:** The first failure was a new-test constructor error before production code.
  A test-only correction led to 147 PASS. The probe asserts failed-encoding original
  preservation and successful UTF-8 writing. Actual dbt/postgres/CLI/noqa paths and
  the independent failure cause remain unverified.

Test-only corrections after an initial failure occurred in 2, 9, 17 and 19. They must not be
counted as additional production repairs. Other untested boundaries in audit records
are questions, not automatically required features or known residual defects.

### Completion bottleneck: task 18

The base formatter's 9-space error was reproduced, with a normal SELECT control.
Rule isolation and a second fix showed a first-pass/idempotence problem. Several
later probes added information, but some failed before their intended observation
because of incorrect `LintedFile` access or rule constructor/configuration usage.
The proposed indent-buffer mechanism remained unmeasured before the first patch.

Baseline reproduction to first edit took **868.456 seconds**, including 21 searches,
10 reads, eight further probes and 26 model dispatches. These are diagnostic/decision
intervals, not guaranteed avoidable time. The first patch produced **5 rather than 8
spaces**, with 506 other tests passing: a real unsuccessful repair. A later helper
confirmed 5→8 on a second fix and a clean plain-SELECT control.

A second production edit was accepted. Its mandatory recheck did start, but only
**11.493514 seconds** remained, compared with a requested 300-second timeout. It
ended with deadline exhaustion, no test verdict, and confirmed cleanup. The final
model decision had consumed 96.600140 seconds after an input showing 117 solver
seconds. Terminal: `LIMIT_REACHED`, "active deadline exhausted during sandbox
execution"; 37 calls, two accepted edits, USD2.8282275. The last candidate is retained
but unverified/unsubmitted. No private evaluation ran. This is neither evaluator
FAIL nor transport/billing uncertainty, and unused edit/cost allowance was not time.

## Repetition versus useful verification

Six tasks (**4,8,11,13,15,20**) selected tests inside an already-passing declared scope,
without a new patch/input/assertion at that decision. Current PASS and reuse guidance
were actually delivered. Missing collection telemetry or an explicit node receipt
was repeatedly used as the reason; task 4/8 had no optional selector. Actual earlier
collection is unreported, so declared overlap is not an exact execution-equivalence
attestation. Task 6 instead ran a new file outside its required explicit-file check:
that selection closed a real coverage gap and must be retained.

No strict unchanged-diff successful registered-check/probe replay was identified.
Task 10 replayed an identical helper after a **test-only diff** change, with the
previous output still visible and replay guidance offered. That follows current
whole-diff freshness rules, rather than proving lost observations. Many probes
partly repeat controls while adding input forms, assertions or sibling failures;
counting all of them as duplication would erase useful evidence, including task 14.

Redundant inspection is separately documented: task 2 repeated an unchanged test
read, task 8 repeated two searches with no new observed lines, task 10 repeated five
negative issue-string searches as cache hits, and task 13 had seven zero-gain receipts
inside 25 inspection actions between a caller failure and the next edit. Tool success
or note counts alone do not establish diagnostic progress.

## Concrete system defect and next decision

Task 17's YAML fixture lies under declared additive root `test`, but the validator
rejects non-Python test edits using the same error as an undeclared root. The message
therefore misidentifies the limitation. The Python-only policy itself was not changed;
recovery preserved the test's intent in a new Python file. This is a concrete small
diagnostic correction for the next implementation, not a fix made during this run.

Prioritize original input/caller fidelity and preserving behavioral expectations
when recovery reshapes a test, using task 8's now-confirmed public failure as the
concrete case. Investigate task 18's failed-helper and diagnosis-to-edit delays before
increasing limits or adding another gate. For repeated selection, bounded factual
execution receipts are a candidate; another generic prompt is unsupported. No new
memory store, mandatory probe quota, deadline policy, YAML support or paid experiment
was implemented or scheduled here. These conclusions apply to this exposed 20-task
single-attempt run, not unseen software tasks.

## Evidence and validation

- [Preparation manifest](C:/pt/reuse20-20261031-v1/manifest.json):
  `sha256:180b482dfae8ba28582165ab3c9a86eb4d9c3e19131f60c6857e328dc5d1ac4b`.
  User authorization and readiness receipts are adjacent. Original `execute.py` and
  corrected `execute-ready.py` are both bound; the failed preparation is preserved.
- [Batch result](C:/pt/reuse20-run-20261031-v1/result.json):
  `sha256:9ac9aeb10604125686f7f29f152657a9360d81597767eb7694f4e62051c0af40`.
- [Settled summary](C:/pt/reuse20-run-20261031-v1/summary.json):
  `sha256:1726816739880e503fffa213473b3418ab5c48302d9dbc0517baef3595941fec`.
- [Public flow](C:/pt/reuse20-run-20261031-v1/analysis/public-flow.json), CAS:
  `sha256:a0e7d075431c229330460e6dbab22ed13a63a2da6125b24aca185c41a1b6fa91`.
- [Per-task public audits](C:/pt/reuse20-20261031-v1/audits/): exclusive files 01-20,
  CAS and separate append-only hash-chained journals. Interim syntheses are retained.
- [Independent final provenance validation](C:/pt/reuse20-20261031-v1/audits/batch-independent-validation.json):
  `sha256:8a92f88ac5af61e6eabeaf861220a9b1410e956b7b02a5baa1bbf573eeb39d65`.
  All 84 bindings, 20 journal chains, 19 submitted patch hashes, settled counts and
  token-based cost reconciliation passed. This does not query the provider's invoice
  or establish semantic correctness.
- [Task 8 operator public result](C:/pt/reuse20-public8-20261031-v1/result.json):
  `sha256:81470235771cb09029ec56f2207a0974f52f420e2c59dc550055ee0a0aa34fea`;
  reviewed plan `sha256:7ad7cbbd76796330ab68d74983da9bb24d2737835f27d2b23fd8bf5dce9395a9`.
  Two public probe executions, zero model/evaluator calls, no solver feedback.

Runtime validation predates this measurement: quick 1,308 PASS/1 host-symlink SKIP
including isolated mock, final wording/contract 156 PASS and Ruff. This reporting
change is documentation-only; its six documentation tests passed. The
[test receipt](C:/pt/reuse20-20261031-v1/audits/documentation-tests.json) and final
reporting validation are stored with the external audits. No raw provider reasoning
or private evaluator bodies were used in this public analysis. Historical reports
and closed evidence remain unchanged; no historical approval was reused.
