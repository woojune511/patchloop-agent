# Verification purpose comparison

Date: 2026-10-16. The user approved the immediately preceding proposal with
"그럼 실험해볼까": the exact D/E revisions, four tasks, sixteen solves and USD 19.20
ceiling below. Dispatch remains conditional on manifest and environment validation.
Every run is official=false and claim_eligible=false. Historical allocations remain closed.

## Repetitions and cost ceiling

Compare previous D with the purpose-preserving guidance, labeled E in this report:
four tasks, two fresh solves per task per arm, sixteen solves total and eight per arm.
The allocation is USD 1.20 per solve and an invocation-wide ceiling of USD 19.20, including
all provider usage. No budget transfers, extra repetitions or paid judges. These are
ceilings, not a spending target; reservations and settled charges remain separate.

## Decision criteria

Judge three outcomes separately, with no minimum number of extra checks:

1. Purpose and grounds: a strong mechanism signal requires the target unsupported
   closure to recur in fresh D, exposure of the new instructions and relevant purposes
   in E, and zero unsupported closures or conditional weakenings in E. A reduction
   with remaining failures is partial change. If D does not reproduce the problem,
   or the relevant purpose is never exposed in E, prevention is NOT_ASSESSABLE.
   Report eligible runs and purposes per task; omission of a purpose cannot count
   as successful preservation. Inspect public requirement gaps even without a plan.
2. Actual behavior: report additional executed verification and accepted edits, their
   timing and evidence. More reasoning text, checks or edits alone is not success.
   Sufficient existing evidence or specific source inference may justify finishing
   without another check; unexecuted behavior must remain labeled unverified.
3. Independent quality: a positive panel signal requires known outcomes/accounting
   for all sixteen rows, agreement of the registered and native graders, more E
   acceptances than D, and no task with fewer E acceptances. Report failure to submit
   separately from a graded wrong answer; ERROR or NOT_RUN holds the quality judgment.
   Every submitted final candidate must have fresh healthy required public receipts
   for its exact diff, with safety and cleanup reported separately.

Equal acceptance, including 0/8 versus 0/8, establishes no quality improvement even
if grounds or behavior improve. A task decrease is a tradeoff. Two repeats on four
development-exposed tasks support descriptive findings, not statistical significance
or generalization. Close the allocation after this panel; a failed criterion does not
authorize tuning, replacement solves or another comparison.

## Revisions and observed problem

| Report arm | Exact solver revision | Launcher arm |
| --- | --- | --- |
| Previous D | fcfa496dfb57f7e0d79616e5389fac034cfbc6b2 | A |
| This change E | 5fbce0c59ef5359393e67b09ce5ff4bf0de715dc | B |

E is a report label, not a runtime version. The only runtime changes are guidance
in `DEV_SYSTEM_PROMPT` and `working_plan.INSTRUCTIONS`: preserve the original
input/path/observable outcome, reject suite PASS or another path as a substitute,
and judge completion from current-diff execution or specific source inference.
There is no new tool, schema, mandatory verification gate or resource allowance.
Both instructions apply from the first turn, so this tests the combined change
across the whole trajectory, not an isolated sentence or only post-PASS behavior.

The [D astroid audit](../docs/history/2026-10-16-astroid-plan-closure.md) found the
original purpose being replaced before first PASS, despite retained plans and reasons.
One run substituted a neighboring path's success and regression checks; another made
the promised check conditional on suite failure. Context loss was not observed.
The [prior C/D panel](../docs/history/2026-10-16-plan-grounds.md) recorded D 0/8
acceptance and two unsupported closures. Those outcomes motivate this question and
are not pooled with the fresh D control. Plausible alternatives remain: D now closes
plans adequately, E changes only wording, or the remaining repair problem is outside
this mechanism. Either arm may already have sufficient evidence without extra checks.

Freeze a common launcher/helper identity for both arms at preparation. Do not absorb
later runner changes such as 8e538f4 into one arm or substitute current HEAD for E.
This is separate from the pending [revision comparison](revision-comparison.md),
which has a different roster and baseline.

## Fixed tasks and resources

| Index | Public task instance | D solves | E solves |
| --- | --- | ---: | ---: |
| 7 | pydicom__pydicom-1139 | 2 | 2 |
| 10 | pydicom__pydicom-901 | 2 | 2 |
| 13 | pylint-dev__astroid-1333 | 2 | 2 |
| 19 | sqlfluff__sqlfluff-1763 | 2 | 2 |

Inputs are `tasks/dev-train/current-dev20/{7,10,13,19}/public.yaml`. Preserve these
development-exposed tasks, including both astroid repeats, without outcome-based
selection. Fresh isolated workspaces, interpreters, notes, journals and ledgers are
required; historical runs and seeded repairs are not controls.

- Model: gpt-5.4-mini-2026-03-17, xhigh, desired output 25,000, standard/global;
  credential file C:/Users/geonj/Documents/PatchLoop/.env.
- Per solve: 40 model calls, 100 actions, four accepted edits and 1,800 seconds,
  including 330 seconds reserved for registered evaluation, within USD 1.20.
- Current agent policy, brief-v1, segmented-v1, result-or-size-v1, retained source
  24,000, probes enabled, probe-policy/recheck none, repair-recheck true,
  protected-v1 and per-call-v1. No shared notes or extra review call.
- Waves D1, E1, E2, D2; task order 7,10,13,19; two workers per wave. Keep source,
  task package, dependencies, installed images, native grader and host conditions
  equal across arms. Repeat indices do not imply matched random seeds.

## Public evidence audit

Before dispatch, freeze the audit rubric and a requirement map derived only from
the public task. They are operator analysis inputs, not additional solver hints.
For each verification purpose, record its earliest wording and input/path/observable
outcome, every revision/removal/closure, the stated reason, and the final assessment.
Follow the full journal chain rather than only the latest predecessor. Include a
null plan update at finish and purposes closed before the first public PASS.

Bind each judgment to journal event/hash, actual delivered request, candidate diff,
source location or executed input/assertion/result. Separate instruction delivery,
purpose visibility and evidence visibility from whether the model used them.
Classify the grounds as:

- Executed support: an observed result addresses that original purpose on the
  candidate being judged. A pre-edit result is not verification of a later diff.
- Source inference: specific current source addresses the original purpose and
  explains why any remaining gap does not affect completion. It stays unexecuted.
- Justified scope change: public requirements and current-diff evidence establish
  why the original purpose no longer matters; generic risk acceptance is insufficient.
- Unsupported closure: unjustified purpose deletion, suite PASS substituted for the target
  behavior, success on another path, "only test if the suite fails", a stale result,
  an unaccounted material gap, or merely listing an unexecuted limitation.

Report both per-purpose classifications and per-run results; any unsupported purpose
makes that run unsupported. Show runs with no applicable purpose as NOT_EXERCISED,
not as preservation successes. Audit final public requirement claims independently
so writing fewer plans cannot hide verification gaps. Explain genuine re-scoping;
neither matching keywords nor recording a reason establishes support.

Freeze public-log judgments before inspecting independent grades. Automated grade
agreement guards may inspect results only for stopping; neither grades nor private
tests, reference patches, evaluator details or prior solutions enter solver context
or public audit labels. Use one rubric for both arms; prompt differences mean arm
blinding is not claimed. No paid model judge is added.

## Actions and independent evaluation

First PASS is the first nonempty candidate with all required healthy receipts for
its exact diff. Start post-PASS counting when that result reaches the model.
Report both the whole trajectory and this later interval. Separate source inspection,
attempted/rejected/completed probes, selected tests and repeated public checks;
distinguish requirement-specific execution from regression-only repetition. Reading
or adding a test does not execute it. Private deliberation is unmeasured.

Count attempted/rejected/accepted edits, distinguish source and test changes, and bind
first-PASS and final patch hashes. Any later edit requires fresh required public PASS
and reassessment. A source read or a new explanation alone is not an executed check
or a repair. Record costs, model/action counts, wall time and remaining resources at
closure to distinguish a choice to finish from a forced resource stop.

Report final independent PASS/FAIL/ERROR/NOT_RUN per task out of two and per arm out
of eight, alongside submission, public checks, registered/native agreement, safety,
cleanup and settled cost. After solver/provider activity closes, evaluate at most
one extra first-PASS candidate per row: at most sixteen extra identities, thirty-two
including finals. Reuse the same row's receipts when first/final hashes match and
label reuse, not a second measurement. Missing first PASS is not a checkpoint failure.
Use existing local images, two workers, registered replay 330 seconds and native
subprocess 600 seconds per candidate. No offline feedback or extra solve follows.

Compare first-PASS and final verdicts to identify late FAIL-to-PASS repairs and
PASS-to-FAIL regressions. Differences established before first PASS belong to the
earlier trajectory. A favorable final arm difference without a late patch change
does not establish an effect of post-PASS review.

## Manifest and environment gates

Preparation must precede provider dispatch. Freeze a new external manifest binding
this protocol and approval, exact revisions, runtime and shared helper hashes,
actual system/planning prompt hashes, effective requests, task identities, source
and dependency bytes, installed image identities, grader/interpreter, reviewed
registered pricing, roster, waves and both row and invocation caps. Confirm raw
HEAD bytes, clean selected inputs and actual import origins. A local guide or later
checkout must not silently replace either frozen arm.

Run zero-provider mocks with both exact arms through isolated evaluation; distinguish
mock safety NOT_RUN. Verify distinct worker import origins, four-task public import,
ordinary-operation and selected-test canaries, checkpoint reconstruction/replay and
accounting stop behavior. Recheck SQLFluff in both the actual probe and registered
public-check environments: exactly one core entry point and loaded core plugin,
default configuration, ANSI/Jinja Linter, and parse/lint of `SELECT 1`. Import alone
is insufficient. Preserve any failed preparation and do not turn diagnostics into
solver-visible task hints. Existing C/D preflight results do not certify this panel.

Approval binds the proposed scope; it does not establish environment PASS. Paid
dispatch requires a frozen manifest and successful preparation. Count
immediately before dispatch, reserve conservatively and use zero SDK retries. Stop
pending admissions on count/transport/billing/cleanup uncertainty, identity drift or
unexplained completed grader disagreement. Preserve already-admitted usage; a known
settled row limit closes that row only. Do not retry, resume, replace, tune prompts
or targets, start Docker Desktop, or pull/build evaluator images. Generated evidence
stays outside the repository in append-only hash-chained dev-run-v1 journals;
closed historical artifacts remain unchanged.
