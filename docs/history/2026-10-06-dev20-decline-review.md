# Dev20 decline: saved-evidence review

Date: 2026-10-06. User-requested explanation of the latest 10/20 to 9/20
transition. Operator-only analysis; no solver intervention or new paid scope.
This follow-up preserves the closed measurement and its original artifacts.

## Question and comparison

Separate the additional failure from the persistent ten unresolved tasks, and
determine whether the measurement exercised the intervening quality features.
The [measurement](2026-10-06-portfolio-dev20-results.md) contains nine PASS->PASS,
one PASS->FAIL (pvlib-1707), zero FAIL->PASS and ten FAIL->FAIL transitions.
All twenty submitted; registered/native verdicts agree, without evaluation,
transport or billing errors. This is one historical/current sample per task;
it does not establish a systematic performance decline or a feature effect.

The [frozen configuration](../../.agent/portfolio-v1.md) matches the old requests:
prepared probe dependencies absent, saved-program recheck disabled, and no
registered selected-test suites in these packages. Runtime bytes changed, but
this was not a test of those enabled capabilities. The separate prepared-probe
[comparison](2026-10-02-lite-sql3-probe-results.md) reached behavior execution yet
remained 0/3. Tool availability has been improved; repair improvement is unproven.

## The additional failure: pvlib-1707

Public issue: `physical(aoi=100, n=1)` should return zero instead of NaN.
Both runs used the same task hash, source base and model snapshot.

- Historical run `run_dev_7fe25679f9d34044` at `C:/pt/ld20live01/5` masked the
  final result where the refracted cosine is zero. Its first public check caught
  a Series-to-array regression; a second edit restored Series type/index. The
  final candidate passed original acceptance. It used no custom probe.
- Current run `run_dev_90727d989e85441b` at `C:/pt/pv1d20live05/5` instead sets
  first-interface reflectance to zero when the two indices match (seq 46/47).
  The later absorption division remains unchanged. This is a different candidate,
  not a replay of the historically accepted repair.
- Its attempted test addition for the exact issue scalar was rejected by the
  unchanged forbidden-test-path contract (seq 59/60). At seq 73 it then declared
  that verification must come from the existing public regression check. That
  check passed 30 tests (seq 74), and it submitted at seq 88/89 without a probe.
- The final delivered context still offered `run_probe` and `replace_text`, with
  35 model calls, three accepted edits, 1,664 seconds and USD 1.079410650 left.
  Submission was not forced by the actual remaining resource budget. Probe
  execution availability on this package was not tested in this review.

Operator-only original native output identifies the remaining failure: with
`n=1, L=0`, the absorption calculation still divides zero by zero at grazing/back
angles and returns NaN where evaluation expects zero. Native output records
30 passed / one failed. This is incomplete numerical boundary handling, not an
evaluation startup failure. It does not show that the exact issue scalar with
default thickness remains broken; source inspection predicts that scalar works.
The rejected scalar assertion alone would therefore not establish the missing
boundary or explain acceptance loss. Do not turn private failure contents into
task-specific guidance for another solver.

Evidence inspected: both original action journals and submitted patches, current
final model-input/context artifacts (public fields only), public task/source,
and `C:/pt/pv1dev20/native/5/output/logs/evaluation/lite-dev-controls-agent/agent/`
`pvlib__pvlib-python-1707/test_output.txt`. No reference patch or encrypted
continuation was read. No source program or evaluator was executed anew.

## What the recurring evidence supports

The [original ten-task diagnosis](2026-10-02-lite-dev20-failure-diagnosis.md)
contains mixed causes: disconnected/wrong-layer repairs, incomplete compatibility,
and more specific original grading requirements. Identical FAIL verdicts in the
new batch do not prove identical mechanisms; those ten new trajectories were not
individually diagnosed here.

The [final-verification audit](2026-10-02-lite-final-verification-audit.md)
already showed why replay alone is insufficient: a symptom-only SQLFluff predicate
missed an incorrect replacement output. The [trajectory review](2026-10-03-sqlfluff-trajectory-review.md)
found unsupported explanations of public regression failures followed by narrowing
conditions to fit known examples. Together these support a bounded concern about
repair scope and evidence interpretation. They do not prove a universal internal
model cause, memory failure, or that a mandatory check would improve acceptance.

Keep the runtime and original score. The decision remains that capability and
reliability work has not demonstrated repair-quality improvement on this panel.
The useful unresolved question is how the agent derives discriminating public
behavior/compatibility checks and uses their results to revise a repair. A new
intervention needs a concrete predicted benefit beyond more probes or explanations.
No prompt change, test300 preparation, rerun or new comparison follows from this review.

Validation scope: both journal hash chains (126/95 events), all six current
model-input/context hashes, submitted-patch identity, saved evidence inspection
and documentation layout/link checks. The first documentation check caught an
oversized history index after adding a link; the redundant index addition was
removed, leaving discovery through current status.
Runtime tests, mock smoke, live solves and evaluator reruns are NOT_RUN for this
documentation-only review; historical validation remains in its original records.
