# Helper delivery and revision reservation: checkpoint follow-up

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run preparation
- Origin Date: 2026-10-28
- Verification Status: local preparation VERIFIED; live execution NOT_RUN
- Version Label: probe-revision-repair-plan-v1

Official=false, claim-ineligible. One operator-assisted continuation is prepared;
the fresh invocation cap is pending. Prior allocations remain closed.

## Question and design

The [previous continuation](2026-10-28-public-counterexample-repair-results.md)
resubmitted the unchanged candidate after five reads and two helpers. Its second
helper output was omitted at a completion handoff, and optional exploration spent
the response capacity needed for a revision. The model still acknowledged the
supplied public counterexamples. These observations motivated the
[delivery and resource fixes](2026-10-28-probe-delivery-revision-reservation.md),
which passed local projection and saved-budget replays.

Test whether the model now makes a new repair using delivered public evidence and
preserved revision capacity, while retaining original caller behavior and public
compatibility. Restore the same starting checkpoint as the failed continuation;
do not restore its later failed exploratory trajectory. Keep model, public packet,
limits and ordinary verification unchanged. Both fixes change together, so a single
follow-up cannot isolate their individual effects or establish a statistical gain.

Competing explanations remain: the model may still choose finish despite available
editing, fail to derive a repair, or make a new but incorrect workaround. Correct
output delivery and available editing with no repair would weaken an explanation
based only on lost evidence or an inaccessible edit window. A correct public repair
with failed isolated acceptance would remain an incomplete task repair.

## Fixed inputs and resources

- Task: Astroid-1333, dev-train `current-dev20/13/public.yaml`.
- Source: `C:/pt/caller-completion-repair-run-v1/repair`,
  `run_dev_3e21775752a54cae`, cut 212, excluding the prepared request itself.
- Candidate:
  `sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f`.
- Model: `gpt-5.4-2026-03-05`, xhigh, one run.
- Credential path: `C:/Users/geonj/Documents/PatchLoop/.env`.
- Proposed fresh invocation cap: **USD3.38078870**. Inherited historical spending
  is USD1.11921130, preserving the USD4.50 cumulative limit. This is a new allocation
  at the same cap, not permission to spend any old unused balance.
- Eight remaining responses including at most one protocol correction, 13 ordinary
  actions plus one final public matrix, at most two additional accepted edits.
  A successful revision opportunity is reserved, not two guaranteed repairs.
- Context 60K, normal output 40K, correction output 25K. Approximately 1353.349
  solver seconds, 390 evaluation seconds and 35 final-matrix seconds remain.
  Ordinary limits are 20 total responses, 39 actions, three edits and 2365 seconds;
  the final matrix keeps combined original limits at 40 actions and 2400 seconds.

The public packet, dependency:pylint read-only registration, source, original case
identity and positive processing witness are unchanged. Historical opaque reasoning,
future trajectory, private evaluator details, reference/operator patches and new
repair hints are not injected. On changed diffs, the supplied outcomes are historical.
The revision reserve applies only to the measured current candidate and does not
make public counterexamples a finish-blocking gate.

## Outcomes and interpretation

Record these separately from action counts and normal finish:

1. Actual helper result delivery to the next model request, including exact public
   stdout/host observations, completeness flags, currency and no duplication.
   No helper or no relevant handoff means that path's uptake is unexercised.
2. Current policy and available edit path after optional exploration. If the
   limiting boundary is never reached, the closure mechanism is unexercised.
3. New accepted mutation, its hypothesis, original caller replay, target processing
   evidence and public regression on the current diff. Reused old PASS is not a
   newly verified repair.
4. Normal finish/submission and the final public matrix on the submitted diff:
   all eleven baseline-correct cases must pass, including the three candidate
   regressions. The preexisting twelfth discrepancy stays separately reported.
5. Isolated task acceptance, safety, settled new cost and active time.

The final matrix executes once after normal completion; its output is not returned
for a further model revision. The model may use ordinary offered probes beforehand.
Do not claim all public counterexamples passed merely because finish succeeded.
Public repair support requires a new candidate, retained original behavior, fresh
required checks and eleven matrix passes. Task acceptance remains a separate result.

Monitor the collector process and only the new result directory's journals/results.
Use ordinary runner deadlines, immediate input counting, zero SDK retries, and stop
on count, transport, billing, execution or cleanup uncertainty. No automatic restart,
Docker startup, image pull or build. A settled unsuccessful observation is a result,
not a reason to rerun the experiment.

## Preparation evidence and execution package

Runtime implementation commit: `fed389aaf949c3f46a9f79a4750e25ee5ea16415`.
Preparation used the existing diagnostic's finite offline clients. First request
parity, a successful source read and delivery to the subsequent request passed.
An independent shared-context reviewer checked fixed conditions and the actual
first-request revision binding. Existing source/image/dependency identities passed
read-only preflight. Provider calls, live token counts and target executions: zero.
Credential contents were not read. No implementation or policy changed in this
preparation turn; prior focused and quick/mock evidence remains linked above.

The actual first request, rather than the inherited forecast in manifest
`remaining_budget.cost.completion_cost`, contains the active revision reservation.
It is bound to the measured candidate, with no verification credit or gate change.
Read/search/helper reserve four responses and five actions; selected-test execution
retains its existing six-action floor. Same outer model/tool schemas are preserved.

- Plan directory: `C:/pt/probe-revision-repair-plan-v1`.
- Manifest:
  `sha256:16f9df355f2e4412925b4ba48fd30094bc8096fc38326714a3e6896247cf8676`.
- Public packet:
  `sha256:7d8166d7cfb6d9fa2f6a46364d16ba0534a4031a2c18cfeeaa7362960af31372`.
- First normalized request:
  `sha256:f9e1b580a7030746a6c7850b5e79d500850e91f3ab67aba3599b107dce278b88`.
- Preflight:
  `sha256:fbb64b14c8d73377a49c560e3f0527decfb012d5df893d7ed5cdc80129b93570`.
- Result directory: `C:/pt/probe-revision-repair-run-v1` (not created).
- Exact command after approval of the fresh cap:
  `& 'C:/pt/probe-revision-repair-plan-v1/run.ps1'`.

Status: READY_PENDING_FRESH_CAP. Local preparation establishes executable parity
and environment readiness only. It does not establish model uptake or repair gain.
