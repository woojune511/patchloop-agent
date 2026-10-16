# Requirement-evidence judgment: approved comparison

Date: 2026-10-16. The user approved the scope below and execution after manifest and
environment verification. This is a new allocation; prior approvals and unused funds
do not carry forward. All runs are official=false and claim-ineligible.

## Question and fixed intervention

Does the new completion guidance make unfinished verification and unsupported public
requirements affect observable decisions, and does independent acceptance improve?
The prior assessment panel had seven assessment-only exits and no acceptance gains.
The public-only exit audit identified abandoned verification plans and regression
PASS treated as stronger evidence than it supplied. Additional actions are optional;
evidence-supported completion without a redundant check is a legitimate outcome.

Previous B: a18976699ed16533516b4347df935e0dea51d161.
Current C: b34e911d88acab74e431120c8e39760cc2656c25.
The previous B and C's parent have identical patchloop runtime trees and lockfiles.
The intervention is the complete five-file guidance change, not a single sentence.
It is present from the start, so pre-PASS improvements and post-PASS changes differ.
Use the existing PatchLoop launcher, not the separate mini-SWE diagnostic path.

For compatibility the reused launcher uses internal arm A for previous B and arm B
for current C. The new manifest binds this mapping; reports use previous B/current C.

## Roster, resources and authorization

- Exact public inputs: tasks/dev-train/current-dev20/{7,10,13,19}/public.yaml:
  pydicom-1139, pydicom-901, astroid-1333, sqlfluff-1763.
- Two fresh solves per task per version: sixteen rows, eight per version. Historical
  B outcomes are reference only and are not pooled with the fresh control.
- gpt-5.4-mini-2026-03-17, xhigh, desired output 25,000, standard/global endpoint;
  credential file C:/Users/geonj/Documents/PatchLoop/.env.
- Each row: USD 1.20, 40 model calls, 100 actions, four accepted edits, 1,800 seconds
  including a 330-second registered-evaluation reserve. Invocation cap USD 19.20.
- Current policy, segmented-v1, result-or-size-v1, brief-v1, retained source 24,000,
  probes enabled, probe-policy/recheck none, repair-recheck true, protected-v1,
  per-call-v1. Keep task/source/dependency/image/grader identities equal across arms.
- Waves previous-B1, current-C1, current-C2, previous-B2; fixed roster order, two
  workers per wave. Each row has its own workspace, interpreter, journal and ledger.
- No historical solution, experiment protocol, private tests, reference patch or
  grader feedback enters solver context. No shared run notes or fixed-seed claim.
- All model usage counts immediately before dispatch with conservative reservations
  and zero SDK retries. No budget transfers, replacement, retry, resume or extra run.

The user's instruction was: "좋아. 이전 B와 이번 버전을 같은 4개 태스크에서 각각 2회씩,
총 $19.20 상한으로 진행해줘. manifest와 환경 검증을 먼저 마치고 이상 없으면 실행해서,
실제 추가 검증·수정 여부와 독립 평가 결과를 구분해 비교해줘."

## Measurements and decision criteria

First PASS is the first nonempty candidate with healthy required-check PASS receipts
on that exact diff. Save its patch hash, remaining resources, offered tools and the
actual next model request. Count post-PASS actions only after the agent receives it.

Report separately: assessment/plan declarations; reads/searches; attempted and
completed probes/selected tests/checks; attempted/rejected/accepted edits; source
versus test changes; first/final patch identity; and fresh checks after later edits.
Record verification already completed before first PASS. Account for unfinished or
rejected plans with evidence meeting their purpose, a supported reason they do not
affect completion, continued investigation, or unsupported closure. A longer
assessment, an acknowledged limit or a tool count is not correctness evidence.
Internal deliberation is not measured. No extra probe or edit is a success quota.

Independent quality: final registered/native PASS, FAIL, ERROR and NOT_RUN, agreement,
safety, cleanup and known billing, per task out of two and per arm out of eight.
Also show actual evaluated and first-PASS-exposed denominators; missing evaluation
is not a wrong-answer verdict. Compare first-PASS and final acceptance to distinguish
late FAIL-to-PASS repair, PASS-to-FAIL regression and pre-PASS effects.

After all solver/provider activity closes, independently evaluate at most one extra
first-PASS candidate per row (16 extra, 32 total candidate identities including finals).
Identical first/final candidates reuse that row's bound receipts. Offline grading
uses existing local images, no paid judge, two workers, registered replay 330 seconds
and native subprocess 600 seconds per candidate. Native grading and offline replay
are outside the solver window; they never increase solver resources or feed back.

A panel quality signal requires complete known grading/accounting, more current-C
acceptances and no task with fewer current-C acceptances. A task-level decrease is
a tradeoff. More verification with unchanged acceptance is behavior change only.
First-PASS FAIL to final PASS is observed late repair; a better first-PASS candidate
is an earlier-trajectory effect. No generalization or statistical-significance claim
follows from these four development-exposed tasks. No automatic adoption/follow-up.

## Preparation and stopping

Before paid dispatch bind exact checkout/runtime, helper, task/public/opaque private
package, source/dependency/image/native grader, effective request, model/price,
credential path, roster and caps in a fresh external manifest. Verify actual import
origins, raw HEAD bytes, mock submissions, public environment canaries, two-worker
origins, observer reconstruction, changed-candidate replay and accounting stop paths.
Keep original closed artifacts immutable and new generated state outside the repo
in hash-chained dev-run-v1 journals. Never pull/build images or start Docker Desktop.

Stop new admissions on count/transport/billing/cleanup uncertainty, identity drift or
unexplained completed grader disagreement. A known, settled row limit closes only
that row under its fixed allocation. Preserve already-admitted usage. Do not change
targets, prompts, budgets or repair decisions in response to hidden grading. Close
the allocation after the frozen rows; unused money does not authorize another run.

Registered mini rates were rechecked against the
[official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini):
USD 0.75 input, 0.075 cached input and 4.50 output per million tokens. Account access
is not established by documentation; count/provider uncertainty remains a hard stop.
