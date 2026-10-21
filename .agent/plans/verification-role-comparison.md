# Same-context verification versus an independent verifier

Status: return-delivery defect repaired locally, 2026-10-21. Same-checkpoint
contrast survives; final execution qualification and freeze remain pending. See
the [return fix](../../docs/history/2026-10-21-verification-role-return-fix.md) and
the earlier [qualification](../../docs/history/2026-10-21-verification-role-qualification.md).
The [implementation record](../../docs/history/2026-10-21-verification-role-executor.md)
remains the earlier local implementation evidence.
No execution packet is frozen and no paid work is authorized. Previous allocations
are closed. Every proposed run remains official=false and claim-ineligible.

## Question and evidence

The [latest probe comparison](../../docs/history/2026-10-21-probe-purpose-results.md)
offered the bound-purpose interface in all 54 B requests, but it was never used.
B1 submitted after regression success while the original caller still failed.
Public evidence already made its completion claim unsupported before acceptance
grades were opened. The rejected-batch size-transition defect was subsequently
[fixed locally](../../tests/test_dev_segment_rejection.py).

At equal total resources, does an independent verification context reduce wrong
completion judgments and produce more accepted repairs than a mandatory separate
verification phase inside the original agent's context? The intervention targets
both nonselection of verification and persistence of an untested repair hypothesis.
Both arms receive the mandatory phase, so this comparison isolates the additional
context/role separation and bounded handoff package, not the benefit of making
verification mandatory.

Alternative explanations are missing caller knowledge, choosing an incorrect
reproduction, ignoring correct feedback, inadequate repair ability, and starving
repair by reserving verification resources. Independence can also lose useful
history. Correct verification without accepted repair would weaken the claim that
context separation solves the repair bottleneck. Equivalent evidence and errors
in both arms would weaken the context-persistence explanation. This exposed task
cannot establish a general single-agent or multi-agent advantage.

## Arms and common behavior

Use one final implementation commit derived from
c0e8bddb64b087f13c7fb854807b627fd6bf105b, including its transition fix. Final commit
and runtime/adapter hashes are TBD. Both arms use the current purpose/observation
interface, verification-state separation ON and the same public tools and prompts.

| Arm | Verification context | Return to repair |
| --- | --- | --- |
| A: same-context phase | The repair agent continues its native conversation with the common verification instruction and read-only tool mask. Existing size/result transitions still apply. | Same stream; the bounded report and its public evidence remain available through the ordinary context policy. |
| B: independent verifier | Pause repair; create one same-model stream from the common public packet and verification instruction. Do not copy repair plans, conclusions, private reasoning or native continuation items. | Resume the paused repair stream with the same bounded report/evidence delivery interface as A; discard verifier native continuation. |

Run phases serially; never have concurrent repair and verification. B is independent
of the repair conversation, not independent of model knowledge or systematic errors.
No stronger verifier model, extra solver, debate, voting, second verification pass
or free model-generated handoff is included. B's history reset, different cache
reuse and extra input reconstruction are part of the treatment and must be measured.
There is no claim that total visible information is identical between the arms.

The common phase instruction asks the model to establish the original public
caller, environment, inputs and expected behavior; distinguish helper/regression
coverage from that requirement; seek a relevant countercondition; and state what
its observations do and do not establish. Derive these from public task/source,
without naming an Astroid function, prescribing its fix or supplying an evaluator
case. The instruction and report schema are byte-identical across arms.

## Schedule within one row

Use a diagnostic controller, leaving the product's default architecture unchanged.
The following envelopes are identical in A and B and subdivide the existing limits.

| Phase | Model calls | Actions | Accepted edits | USD |
| --- | ---: | ---: | ---: | ---: |
| Initial repair | 28 | 60 | 3 | 0.48 |
| Verification | 6 | 20 | 0 | 0.20 |
| Repair after feedback / submission | 6 | 20 | 1 | 0.20 |
| Row total | 40 | 100 | 4 | 0.88 |

These are ceilings and reservations, not promised numbers of useful responses.
Unspent initial/verification resources flow only to the final repair phase within
that row, including unused edits. They do not enlarge verification's
envelope or another row/arm. Initial repair cannot borrow the later reserves.
Verifier calls, counting, report generation/delivery, correction turns and any
subsequent repair are all charged to the same row ledger. Phase switches do not
reset action, mutation, failure, correction, inspection or wall-clock counters.
Keep the single 1,800-second deadline including the existing 330-second evaluation
reserve. Do not add per-phase timeouts. Record time spent and remaining at each
phase; reserved calls/cost cannot guarantee a phase is reached before that deadline.

1. Initial repair offers normal registered repair tools, but defers finish_task
   until verification has ended. Enter verification at the first safe point when
   a nonempty candidate meets existing mechanical finish prerequisites, or before
   another action/request would exceed any initial envelope, whichever comes first.
   A safe point has no unresolved admitted tool batch or unknown mutation outcome.
   A completed known rejection uses the existing correction/transition rules.
2. Pin the exact current diff, base and dependency identities. If no edit exists,
   verify that unchanged candidate and record NO_CANDIDATE_AT_ENTRY. Do not silently
   extend initial repair. A global terminal failure or explicit stop_task ends the
   row; it does not force a later phase or count as a successful abstention.
3. Both verification phases offer the same registered source/dependency reads,
   searches/history search, bounded probes and visible checks; no mutation,
   finish_task or unrestricted shell. Probe setup may create only its existing
   sandbox fixtures. Keep the candidate frozen, including tests. Use the same
   installed environment and registered actions, not an extra evaluator backend.
4. A new diagnostic finish_verification action returns a report, not a submission
   or acceptance. Its assessment is at most the existing 1,500 characters; evidence
   uses the existing two reference slots. Validate provenance and schema, not the
   semantic verdict. A report can find a defect, support the candidate, or state
   uncertainty. Do not require an ORIGINAL label or a passing probe to finish.
   Within that bound, state reviewed scope, caller/setup/input, expected versus
   observed behavior, remaining counterconditions and the proposed next check/fix.
   The host binds the diff and actual receipt identities; it supplies no conclusion.
5. Verification ends on that report or its first exhausted envelope. Exhaustion
   produces a host status VERIFICATION_INCOMPLETE, never a fabricated model verdict.
   The final repair phase receives actual receipts plus the report/status. It may
   repair, check, submit under the original finish contract, or stop. A positive
   verifier report grants no new finish permission and a negative one is advisory.

Complete and reconcile already admitted work before changing phases. Keep existing
registered timeouts and global-deadline admission. A check that cannot run within
those existing rules is unavailable, distinct from choosing not to check; do not
shorten its timeout or extend the row. Existing call/action completion-path
forecasts remain additional constraints; these envelopes cannot bypass them.

Return reports bind the reviewed diff. Any later edit makes their behavioral
verdict stale. The repair agent must use existing checks/replays or a clearly
identified source inference for the new diff; no free second verifier is added.
Record whether it repaired the reported failure, introduced a regression, ignored
the report, or explicitly remained uncertain.

## Context and evidence contract

The common public packet is built deterministically from the row's actual public
state before selecting the arm adapter: issue and constraints, source/dependency
identities, current diff, and already observed source/check/probe receipts.
Use the existing source selection and size limits. Include original program/input/
environment and recorded observations when admitted; mark model-authored expected
values and scope declarations as unverified. Never turn them into measured facts.
Do not prefetch a missing caller, add an oracle-selected snippet, or fill a gap from
another run. Additional acquisition costs registered actions in both arms.

B excludes repair-authored working plans, explanatory conclusions and native
continuation. Executed probe programs and declared expectations can appear as
explicitly attributed execution artifacts, not accepted interpretations. The
verifier may search the same public observation corpus; it does not gain access
to repair messages or reasoning through history search. Apply this verification
search mask to A too, although A retains its own preceding native conversation.

Keep segmented-v1, result-or-size-v1 and brief-v1 unchanged in every stream.
Changing phase is not a forced segment transition of the repair stream. B's new
stream initialization is logged separately from result/size transitions. On
return, the repair stream processes the report as ordinary new public material;
only the existing rules may require a size/result transition. Never inject the
verifier's encrypted continuation into the repair stream.

For both verification arms, initialize active notes from the common public packet
and generic verification question, without promoting repair-authored interpretations.
A's previous interpretations can still exist in its native context. Keep the same
two open-question source-reference slots, including supporting and
countercheck evidence. Do not allocate another pair per role or concatenate two
working-note stores. At each switch, use one active bounded note/reference state;
archive the inactive state only in the external journal, with no automatic union
on return. Existing native history can retain old material as it already does.
Receipt identities are provenance, not extra retained source-body slots.

Keep 24,000 retained source characters, 60,000 counted input tokens, 1,048,576
request bytes, 262,144 encrypted-item bytes, eight search results and the current
whole-original/48k overflow behavior. The report, tool receipts, source excerpts
and packet consume these limits; there is no side-channel context allowance.
Probe source plus observer stays within 8,000 characters. Keep observation/output
limits, ordinary probes with no automatic probe recheck, repair-recheck,
protected-v1 inspection, one consecutive correction, four parallel reads,
24 consecutive inspections and three failed-mutation repair turns unchanged.

Audit actual dispatched inputs at entry, ordinary transitions and return. Record
which caller/setup/countercondition and other-function branch bodies were never
obtained, selected but excluded, delivered then lost, restored, or still present.
Record newly displaced evidence and whether the verifier's report survived to
the repair decision. Reconstruct same-snapshot A/B input projections locally for
packet differences; live trajectories can diverge and are not paired eviction tests.

## Proposed allocation and stopping rules

| Binding | Proposed value; not authorization |
| --- | --- |
| Task | tasks/dev-train/current-dev20/13/public.yaml; dev-train Astroid-1333 |
| Both roles' model | gpt-5.4-mini-2026-03-17; xhigh; desired output 25,000 |
| Credential file | C:/Users/geonj/Documents/PatchLoop/.env |
| Repetitions | A 3, B 3; six fresh isolated rows, each repeat=1 |
| Serial order | A1 B1 B2 A2 A3 B3; no concurrent rows |
| New spending cap | USD 0.88/row, 2.64/arm, 5.28 allocation-wide |
| Local assessment cap | Twelve caller checks, six native evaluations; one worker |
| Proposed preparation/execution roots | C:/pt/verification-role49 / C:/pt/verification-role49-live |

Use the previously prepared public source
C:/pt/ld20p01/s/13/prepared-source.json and dependency manifest
C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json, including
Pylint 2.12.2. Pin task/base/source/dependencies and installed image identities
at freeze. Do not start Docker or pull/build images automatically. Runs share no
notes, patches, feedback or reusable model responses. Provider cache behavior is
measured rather than assumed. Repetition IDs are not matched stochastic seeds.

The [official standard prices](https://developers.openai.com/api/docs/pricing),
checked 2026-10-21, are USD 0.75 input, 0.075 cached input and 4.50 output per
million tokens. The [snapshot](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
is unchanged. At 60,000 uncached input and 25,000 output, a request reserves up to
USD 0.1575; the USD 0.20 verification envelope does not guarantee six such calls.
At the existing 128-output admission floor, that worst-input request costs
USD 0.045576, so the envelope funds four minimum-sized requests, not useful
reasoning. Preserve per-call-v1 admission and its output reductions; do not
silently change to completion-reserve-v1. Report allocated versus actual output
ceilings and phase starvation. No new total token or context allowance is implied.

Use one nanodollar ledger, global clock and action namespace across both B streams.
Count immediately before every dispatch, retain zero SDK retries, account for
cached/uncached input and output with reasoning included once, and stop all rows
on count, transport, billing, local continuation or cleanup uncertainty. Recheck
prices at freeze and before live work; changed pricing requires review without
increasing these caps. No paid judge, retry, resume, replacement, top-up or extra
condition is included. An exhausted known phase cap follows the schedule; uncertain
state, manifest drift or an unreconciled action stops the allocation.

Assess only submitted exact patches after the public audit is sealed. Keep the
existing 600-second per-patch local assessment bound and 300-second native bound;
these post-collection checks cannot feed more agent work. Reuse a valid existing
native receipt once, counting it within the six-evaluation cap. Assessment ERROR
stops remaining assessments. No submission means unassessed, not an observed
behavioral FAIL. Prior settled and uncertain bills remain separate.

## Outcomes: judgment, mechanism and repair

Seal public annotations before reading fresh private acceptance grades. Mask row
codes where possible, while acknowledging that stream layout reveals treatment.
Use public issue/source, actual dispatched inputs/actions and receipt bodies;
never inspect encrypted reasoning or infer private thoughts. No grader rubric,
private tests, reference patch, private caller program or previous solution enters
either role. Automated validation checks provenance/completeness; semantic scope
and evidence use require an explicit public-evidence audit.

Retain the [public completion rubric](verification-state-comparison.md):
CONTRADICTED, UNSUPPORTED, SUPPORTED_DIRECT, SUPPORTED_INFERENCE, UNKNOWN,
NO_CLAIM and NOT_RUN. A helper PASS, declared purpose, closed concern, or
required=UNKNOWN alone cannot determine the label. Source inference is permitted
when it actually connects the original caller/conditions to the current behavior
and addresses contrary evidence. Setup failure is not a behavioral counterexample.
Bind each claim to the current diff, event/action/input and delivered receipt;
deduplicate recovery by action_id + input_hash.

| Measure | Definition and denominator |
| --- | --- |
| J_final, primary judgment | Assigned rows with a CONTRADICTED or UNSUPPORTED final repair-agent completion claim after verification; report /3 plus /assessable final claims. No claim, unknown, or unreached phase is a separate outcome. |
| J_any, historical continuity | Assigned rows with any such completion claim in any phase or role, counted once; report /3, all role-specific claims and later corrections. A later correction does not erase an earlier error. |
| V_wrong | Incorrectly supported or rejected candidate in the verifier report, judged from public evidence; preserve uncertainty. A report is not itself a final repair submission. |
| R, primary repair | Exact submitted patch passes native acceptance and both original missing/present caller controls; report /3 and each independent PASS/FAIL/ERROR/NOT_RUN component. |
| Reliability/resources | Submission, phase reached, report delivered, stop reason, model/action/edit counts, input/cache/reasoning/output tokens, cost, time, output ceilings and segment causes, per phase and total. |

J_final is chosen here to measure correction before final completion; J_any remains
visible to prevent hiding bad early judgments. Do not merge their denominators or
compare J_final with an old experiment's J_any as if identical. Report final-claim
absence and abstention separately: lower J caused only by silence, early failure,
or failure to reach verification is not improved judgment. An accidentally correct
patch does not retroactively justify an unsupported claim.

For each row retain the following chain with YES / NO_OBSERVED / UNKNOWN / NOT_RUN,
identities, brief public quotations and opportunities as well as assigned counts:

1. Phase reached and an editable candidate existed; model saw the instruction,
   tools, time and cost sufficient to attempt an applicable registered check.
2. Original caller/input/environment and countercondition acquired; helper-only,
   changed-setup and unobserved mappings stay distinct from faithful reproduction.
   Credit before/after comparison only with comparable actual baseline/current
   executions; a predicted baseline result is not a measured failure.
3. Evidence actually delivered in verification input, then interpreted correctly;
   original/expected/actual mapping is independently audited, not self-certified.
4. Actionable finding or supported uncertainty appears in a current-diff report,
   survives delivery to repair, and is explicitly applied or disputed on evidence.
5. Repair/check action responds to that finding; the final claim changes, remains
   justified, or repeats the error. Separate feedback use from mere mention.
6. Exact final patch independently accepted or rejected. Show J_final by R and
   verifier findings by subsequent repair outcomes, including unassessed rows.

Correct gap detection without actual repair is a verification gain only. Useful
feedback ignored by repair points to feedback application; feedback followed yet
still failing points to repair or incomplete verification; both roles missing the
same caller weakens the case for context separation alone. Report verification
resource exhaustion and repair opportunity loss alongside these explanations.

For a favorable exploratory screen require all six trajectories and required
assessments known, both arms to reach verification with a candidate in at least
two rows, J_final_B <= J_final_A - 2, R_B >= R_A + 2, and supported current-report
use in at least two accepted B repairs. Missing/ambiguous claims cannot create a
judgment margin: count ambiguous B claims against it and ambiguous A claims in
its favor. Require at least two assessable final claims per arm and a lower
conditional final-claim error rate in B. Otherwise report the measured stages
without adopting multi-agent repair or extending the sample. Three per arm is a
screen on one development-exposed task, not statistical or general improvement evidence.

## Provider-free implementation and freeze gates

Implement only the diagnostic phase controller, same-context/independent adapters,
bounded report delivery and grading extensions needed for this comparison. Keep
the default runtime unchanged. Before freezing any executable packet:

- Validate one shared ledger/deadline/action identity across roles and every phase
  boundary, including early finish eligibility, no candidate, cap exhaustion,
  rejected batch at a size transition, stale report after edit, and interrupted
  report delivery. No fake tool completion or extra correction allowance.
- Capture both wire paths with provider/counting stubbed. Initial repair requests
  must match after identity normalization. At a shared saved checkpoint, common
  verification instruction, tool schemas and public packet must match; enumerate
  only intended native-history/role differences. Verify no private or repair-plan
  leakage to B, no new forced repair segment, two references and unchanged limits.
- Use a small set of meaningful public synthetic grading fixtures: valid original
  failure, valid passing candidate, helper-only pass, setup error, source-supported
  inference, stale result, unsupported final claim, missing evidence/report and
  conflicting current observations. Check both false acceptance and false rejection.
- Replay public A1/B1/B2 artifacts from the latest probe comparison without changing
  stored bytes/grades. B1 is a known unsupported-completion diagnostic, not a new
  live control. Measure packet reconstruction and displaced evidence; replay cannot
  establish future uptake, useful output, live cost or repair improvement.
- Check resource feasibility mechanically with actual captured input sizes and
  the existing completion forecasts. Report the initial-patch/verification/final-
  repair opportunity under this split; failure to fund the minimum registered
  paths blocks freeze and requires revising the specification before approval.
  Do not tune the split from private results or change it after paid work starts.
- Run focused checks under two minutes, Ruff, quick tests including isolated mock
  evaluation in both arms, then the full suite at the final implementation commit.
  Keep existing assertions and skip policy; do not weaken tests to admit the plan.

Freeze an external packet binding the final implementation commit, this spec,
phase limits/triggers, schemas/prompts/masks, input projections, six row requests,
order and caps, source/environment, operator-only assessment hashes and validation
receipts. Journal generated state outside the repository as append-only hash-chained
dev-run-v1 events. The adapter/execution CLI and manifest discriminator must be
implemented and tested before their names can be advertised as runnable.

Only then request exact approval for the frozen task/model/credential file, six
rows and USD 5.28 cap. This document supplies no approval and no provider operation
is part of its preparation.

## Implemented interfaces and remaining preparation

`diagnostics.verification_role_panel` implements `capture`, `freeze`, and
`validate`; `diagnostics.verification_role_execution` implements `collect`,
`export`, `seal`, and `assess`. Run either module with `--help` for arguments.
The role-specific discriminator is `verification-role-comparison-v1`; the old
verification-state packet cannot authorize this executor. Only collection can
dispatch a provider, after exact fresh approval and the existing admission gates.

The executor reuses the existing loop, one ledger/deadline/action namespace, and
the serial allocation/stop/seal/assessment paths. Two journal read projections
select native histories; writes still use one original hash chain. Report receipts
are real idempotent actions. Verification history searches, including exact-ID
pages, expose public observations with repair annotations removed in both arms.
No default CLI policy or prompt changes when the diagnostic is unassigned.

The validation JSON additionally requires `verification_role.contract_hash` from
`verification_role.contract()` and file references for `same_snapshot_capture`,
`historical_packet_replay`, and `resource_feasibility`. Each receipt identifies its
`gate`, `passed: true`, the same contract hash, final `head`, `runtime_hash`, and
`implementation`, zero `provider_calls` and `input_count_calls`, plus nonempty
hash-bound `evidence` files. These operator-reviewed receipts must establish the
corresponding freeze gates above; placeholder or earlier-commit validation is
insufficient. Ordinary focused/quick/full XML receipts are also required. The
executor does not manufacture qualification from its implementation tests.

`diagnostics.verification_role_qualification` reconstructs immutable historical
inputs, captures both phase projections, enumerates source displacement and checks
saved-count-based cost admission without network access. Its replay has no run
envelope and cannot resume. Three historical entry pairs preserve native-history
contrast, common public state and identical schemas. Minimum-path funding is not
useful-output or candidate-availability evidence.

The repaired return path quotes only the current question's selected verifier
exchanges, with action/input/diff provenance, outside native continuation. Both
arms' reports bind source and tool-result references in the existing two slots.
No repair segment is forced: a continuing segment appends missing public quotes;
a normal fresh segment includes them as optional evidence. Only measured overflow
can omit them through the existing fallback, leaving delivery explicitly incomplete.
Verifier native continuation, unselected exchanges and owned note/plan envelopes
remain excluded from B's repair input. An edit expires selection priority as before.

Local fixtures now deliver both probe bodies in A and B. Historical entry contrast,
source displacement, phase split and budgets remain unchanged. These checks do not
establish model uptake or repair success. Complete the final-implementation full
suite and hash-bound execution qualification before freezing or requesting paid
approval. No new paid allocation or executable manifest was created.
