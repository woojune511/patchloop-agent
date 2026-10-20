# Plan revision grounds: approved C/D comparison

Date: 2026-10-16. This is a fresh user-approved allocation, official=false and
claim_eligible=false. Previous approvals and unused money do not carry forward.

## Question and intervention

Does retaining the predecessor plan and requiring revision grounds reduce unsupported
closure of unfinished verification, change actual verification/repair, and improve
independent acceptance? The prior C exit audit found both already-completed plans and
unsupported closure. More checks are optional; reasons and tool counts are not quality.

Control C: b34e911d88acab74e431120c8e39760cc2656c25.
New D: fcfa496dfb57f7e0d79616e5389fac034cfbc6b2.
D is a report label, not a new runtime version. Compare the whole runtime change from
the first model turn, not an isolated sentence or exclusively a post-PASS intervention.
The existing PatchLoop launcher uses internal A=C and B=D; the manifest binds this.
Do not use the separate mini-SWE runtime or pool historical C outcomes into this control.

## Fixed scope and allocation

- Inputs: tasks/dev-train/current-dev20/{7,10,13,19}/public.yaml, respectively
  pydicom-1139, pydicom-901, astroid-1333 and sqlfluff-1763; dev-train only.
- Two fresh solves per task per version, sixteen total and eight per version.
- gpt-5.4-mini-2026-03-17, xhigh, desired output 25,000, standard/global;
  credential file C:/Users/geonj/Documents/PatchLoop/.env.
- Each row: USD 1.20, 40 model calls, 100 actions, four accepted edits, 1,800 seconds
  including 330 seconds reserved for registered evaluation. Total cap USD 19.20.
- Current policy, brief-v1, segmented-v1, result-or-size-v1, retained source 24,000,
  probes enabled, probe-policy/recheck none, repair-recheck true, protected-v1,
  per-call-v1. No shared run notes or same-seed claim.
- Waves C1, D1, D2, C2; roster order 7,10,13,19; two workers per wave. Each row has
  an isolated workspace, interpreter, journal and ledger. Keep task/source/dependency/
  image/native grader identities equal across arms. Count immediately before dispatch,
  reserve conservatively, use zero SDK retries, and never transfer unused row budget.

The user's approval: "좋아. 이전 C와 이번 버전을 같은 4개 태스크에서 각각 2회씩,
총 $19.20 상한으로 진행해줘. manifest와 SQLFluff를 포함한 환경 검증을 먼저 마치고
이상 없으면 실행해서, 계획을 닫은 근거·실제 추가 검증과 수정·독립 평가 결과를
구분해 비교해줘."

## Three separate measurements

1. Plan grounds: retain pre/post plan, revision/removal/completion/conditional weakening,
   reason, assessment and referenced public evidence. Compare C's basis/plan/assessment
   with D's added reason using the same public-only rubric. Include finish with a null
   plan update and unfinished plan. Separate field presence, rejected annotation and
   actual feature exposure from evidentiary support. Classify executed current-diff
   inputs/assertions/results, justified public-scope exclusion, explicit source inference,
   or unsupported closure. Source inference is not executed proof. Regression PASS
   alone does not establish a requirement's reproduction or verification. Verification
   already completed before first PASS can justify closure without an extra check.
2. Actions: first PASS is the first nonempty candidate with healthy required receipts
   for its exact diff. Count post-PASS behavior only after model receipt. Separate reads/
   searches, attempted/completed probes/selected tests/checks, regression repeats versus
   requirement-specific checks, and attempted/rejected/accepted edits. Distinguish source
   and test edits, first/final patch identities and fresh PASS after any later edit.
   Adding/reading tests does not mean executing them; internal deliberation is unmeasured.
3. Quality: per-task /2 and per-arm /8 final independent PASS/FAIL/ERROR/NOT_RUN,
   registered/native agreement, safety, cleanup and billing. First-PASS versus final
   evaluation separates late FAIL-to-PASS repair, PASS-to-FAIL regression and earlier
   trajectory effects. Missing evaluation is not a wrong-answer verdict.

Freeze the public-log judgment before inspecting independent grade results. Automated
agreement guards may inspect grades for stopping; no grade feeds back into solving or
public audit labels. Arm blinding is not claimed because D's new fields reveal it.
No hidden tests, reference patches, private specs, prior solutions or evaluator feedback
enter solver context. Use only registered coding-agent actions.

After all solver/provider activity closes, grade at most one extra first-PASS candidate
per row: sixteen extra, thirty-two total candidate identities including finals. Reuse
that row's receipts when first/final hashes match. Use existing local images, two workers,
registered replay 330 seconds and native subprocess 600 seconds per candidate. No paid
judge; offline evaluation never increases solver resources or provides repair feedback.

## Decision and stop rules

A positive panel quality signal requires all sixteen grades/accounting known, more
D successes than C, and no task with fewer D successes. A task decrease is a tradeoff.
More explanations alone are explanation change; more verification alone is behavior
change. Neither proves correctness. Small, development-exposed four-task repeats do
not establish generalization or statistical significance. Incomplete grading/infra
mismatch holds the quality judgment; no replacement runs or automatic follow-up.

Before provider dispatch freeze a fresh external manifest binding exact revisions,
runtime/helper hashes, public/opaque private task identities, prepared source/dependencies,
installed images, grader/interpreter, effective request, pricing, roster, caps and approval.
Check raw HEAD bytes and actual import origins; run both exact-arm mocks, public import/
operation/selected-test canaries, two-worker origin smoke, reconstruction/replay and
accounting-stop tests. SQLFluff must load default configuration and core plugin exactly
once and execute an ordinary lint/parse operation in the actual probe/check environment;
import success alone is insufficient. Do not repair it with solver-visible task hints.

Stop all pending admissions on count/transport/billing/cleanup uncertainty, identity
drift or unexplained completed grader disagreement. A settled known row limit closes
that row only. Preserve already-admitted usage. No retry, resume, replacement, image
pull/build, Docker Desktop startup, prompt/target/budget tuning or paid continuation.
New generated state stays outside the repository in hash-chained dev-run-v1 journals;
closed historical artifacts remain byte-identical.

Registered rates were checked against the
[official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini):
USD 0.75 input, 0.075 cached input and 4.50 output per million tokens. Documentation
does not establish account access; provider/count uncertainty remains a hard stop.
