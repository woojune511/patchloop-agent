# Current status

`dev-head` is the only active coding-agent runtime. It is mutable, development-only,
and always records `official=false`. The available commands are `patchloop dev`,
`patchloop doctor`, `patchloop task validate`, and `patchloop task prepare-source`;
legacy Rapid and provider-backed
claim commands are absent.

## Current seam: three-task baseline stopped; line-table compatibility fixed

The user authorized the proposed six-run baseline without further confirmation:
tox-cross-section-empty-substitution, pdm-ignore-active-venv-resolution and
anyio-interrupt-runner-cleanup, each twice. Fixed order T1/P1/N1/N2/P2/T2;
gpt-5.4-2026-03-05/medium, segmented-v1, brief-v1, probes enabled, probe-policy none,
repair-recheck and unchanged 40/100/4/1800s/25000 limits. Each repeat=1, root .env,
$1.20/run and a new $7.20 aggregate cap. Fresh prepared-source clones for every run
and isolated evaluation; no historical plans, patches, notes or cases injected.
Root: `C:\pt\analyses\gpt54-multitask-baseline-20260916-v1`.

All three exact sources were prepared; six offline run/evaluation clones verified.
Operator tests:13 PASS/3.24s; Ruff PASS; pre-run mock reaches isolated acceptance PASS.
T1:acceptance PASS/safety PASS,6 model calls,1 edit,$0.223374500.
P1:acceptance FAIL/safety PASS,5 calls,1 edit,$0.190006500 after its public check passed.
N1 was interrupted on infrastructure failure: all three public check attempts failed
inside line_trace.py before the target tests started. Python 3.13's dis.findlinestarts
can report None, and the collector compared it to zero. The model changed callback
shapes to work around that error; those actions do not establish task-solving quality.

The operator closed the group without replay or replacement. N1 has18 known generation
usage records,$0.869843500,3 edits and2 probes; its19th input count was interrupted.
Total recorded cost:$1.283224500. One unresolved count, no unresolved generation or tool
action, no remaining Docker containers. N1's original journal remains unterminated and
unchanged; separate interruption/group-stop receipts record the boundary. N2/P2/T2 never
started. All29 dispatched inputs preserve public task/diff/check state and exact wire
hashes; prepared-source information is absent. No hidden evaluation details were read.
The incomplete baseline supports no further model/policy/default-adoption conclusion.

After closing the frozen group, skip None line numbers in the collector. Four synthetic
generator/async-generator exit0/7 cases reproduce the old failure and pass after the fix.
Focused114 PASS/17.340s; Ruff PASS; full2341 PASS/8 SKIP,693.812s,110 files/four processes
with --durations=15 and unchanged runtime/test hashes. Fixed-runtime mock reaches isolated
acceptance PASS with all4 inputs verified. Two synthetic checks in the existing anyio
Python3.13.13 image preserve exit0/7, line collection and confirmed cleanup; no task
candidate or private test was rerun. Validation:`C:\pt\validation\line-trace-none-20260916-v1`.
No retries, extra paid samples, automatic resume, image start/pull/build or default change.
Report:`C:\pt\analyses\gpt54-multitask-baseline-20260916-v1\result.md`. All official=false.

## Prior seam: model A4/B4 closed; GPT-5.4 follow-up signal

The user's follow-up proceed authorizes one fresh model-only A4/B4 group after the
closed context comparison. A=`gpt-5.4-mini-2026-03-17`, B=`gpt-5.4-2026-03-05`;
both medium, segmented-v1, brief-v1, pyfakefs parent-traversal v2, probes enabled,
probe-policy none and repair-recheck. Same source bytes, fresh workspace per run,
root .env, repeat1, $1.20/run and new $9.60 aggregate cap; fixed order
A1/B1/B2/A2/B3/A3/A4/B4 and unchanged 40/100/4/1800s/25000 limits. No prior agent
state is injected. New root: `C:\pt\analyses\model-only-compare-20260916-v1`.

The exact full GPT-5.4 snapshot now has reviewed standard short-context prices
($2.50 input/$0.25 cached input/$15 output per million tokens). It requires the
existing counted segmented input bound below 272K, where official pricing increases.
No context/plan/tool behavior changes. Focused contracts/segments:62 PASS/104.867s;
full regression:2337 PASS/8 SKIP in667.570s across110 files/four processes with
--durations=15 and unchanged runtime/test hashes. Ruff PASS. The final no-call
operator/wire tests pass10/10 in2.80s; an initial test-only missing price-review
fixture was corrected. Both mock runs reach one edit, public check, submission and
isolated acceptance PASS; all8 inputs preserve public task/diff/check state.
Two real-source clones rehearse without Git network/provider/Docker calls.
Implementation commit:1f7b366. Runtime/task/source/prices were frozen before execution.

All8 runs completed once in the fixed order. Mini:1/4 acceptance PASS,1 submission,
3 NOT_RUN. GPT-5.4:3/4 PASS,4 submissions,1 acceptance FAIL,0 NOT_RUN. No infrastructure
or count/provider/billing/continuation/cleanup uncertainty stop. All submitted rows
have safety PASS. All148 counted/generation calls have completed, known usage;
185 tool actions. All actual request hashes/task/diff/check/plan/notes/error deliveries
pass public audits. All15 applied candidates have a same-diff public check (23 checks).

Recorded cost mini$2.043326250/GPT-5.4$1.261343000,total$3.304669250 under$9.60;
GPT-5.4's group cost is38.3% lower. Uncached equivalent:$2.994158250/$2.142335000;
these are token-use normalizations, not bills. No cost/input-limit terminal or lowered
output ceiling. A1/A4 stop on accepted_mutations, A3 on model_calls completion horizon.
First applied edit calls:mini16/11/none/18,full5/3/8/8; total model calls112/36.
Mini has17 rejected proposals (2 path,14 anchor,1 scope); full has0. A3 repeats identical
path/old_text/new_text proposals beyond the first3 times. Mini A2 recovers across
public-check failures and passes after3 edits. Full rows each use1 edit and pass both
public checks, so this group does not establish improved recovery after a failed check.
B1 still fails final acceptance. No hidden evaluator details were used to explain it.

Max input tokens49658/40225; segment counts5/8/12/9 versus4/3/3/3, all noninitial
transitions major_result_reviewed. One probe per arm; counts do not establish benefit.
9658 historical and4396 recent protected files unchanged. Nine owned test roots recycled;
durable source/run/evaluation evidence remains in place. The acceptance gap2 meets the
fixed follow-up signal rule. Prioritize confirmation on other dev-train tasks before
default adoption; no extra samples, retries, automatic resume or default change here.
All results official=false. Report: `C:\pt\analyses\model-only-compare-20260916-v1\result.md`.

## Prior seam: prepared sources verified; context A4/B4 closed, direction unresolved

Optional `--prepared-source` uses one audited source for independent run/evaluator
workspaces without another remote fetch. The preparation command binds original
URL/base, Git commit/tree and exact public worktree bytes; source path/hash stay in
the envelope/journal, never agent context. Invalid/missing/changed source stops
preflight without fallback. Existing source creation is unchanged when omitted.
Active resume revalidates source; terminal/completed-evaluation recovery is metadata-only.

The user authorized implementation plus one new context-only A4/B4 comparison:
A=append-v1, B=segmented-v1, same brief-v1 planning, mini 2026-03-17/medium,
pyfakefs v2, probes/probe-policy none, repair-recheck, root .env, repeat1,
$1.20/run/$9.60 aggregate and unchanged global limits. Fixed order
A1/B1/B2/A2/B3/A3/A4/B4; all fresh, no prior patches/notes/cases. No default adoption.
Focused/wire plus snapshot-drift verification passes 33 cases; the final source
suite passes 26/26 in26.980s. Full regression:2332 PASS/8 SKIP across110 files,
739.561s, four workers with --durations=15; runtime/test hashes stayed fixed.
One final Ruff line-wrap has identical Python AST; Ruff and both final-runtime
mock runs PASS. Each mock has one edit,4 model/5 tool calls, isolated acceptance
PASS/safety NOT_RUN. All8 actual inputs preserve task/diff/check state without
source metadata. No provider/count/real Docker calls in this validation.
The exact pyfakefs source is prepared and two independent clones rehearse without
fetch. Full regression exceeds two minutes; focused validation remains below the
target. No context or planning policy changed. Implementation commit:c2802f9.

All8 live runs completed once in the fixed order without infrastructure/uncertainty
stop. A:0/4 acceptance PASS,0 submissions,4 NOT_RUN. B:1/4 PASS,2 submissions,
1 acceptance FAIL,2 NOT_RUN. Submitted rows have safety PASS; others NOT_RUN.
A1/A2/A3/B3/B4 stop at completion horizon with accepted_mutations as the sole
blocking resource. A4 voluntarily stops after incorrectly claiming both current
checks passed; its actual input still shows contract NOT_RUN on the final diff.
No cost/input-limit terminal. No extra candidate execution to infer missing acceptance.

Recorded cost A$1.974031950/B$1.580162850,total$3.554194800 under$9.60;
uncached equivalent A$5.038812750/B$2.519849250,total$7.558662000, not a bill.
Max input tokens A170130/B45964; request bytes A737210/B257002. B segment counts
9/9/6/6, all26 noninitial transitions major_result_reviewed. First accepted edit
calls A15/14/20/16 versus B24/14/15/12. Exact rejected-proposal repeats:0 both arms.
All30 accepted candidates have same-diff public checks;39 checks and5 probes total.
B2's candidate probe informs a subsequent successful repair; B3's probe fails
before its intended observations. Probe/plan counts alone are not improvement evidence.

All204 actual request hashes/task/diff/check/plan/notes/feedback deliveries verified;
204 known usage records, all completed,259 tool actions. Source metadata stays
outside model input; original source and frozen configuration remain unchanged.
9658 historical and1741 recent protected files unchanged. No retry/replacement/
auto-resume/default adoption. Acceptance gap1 is direction unresolved by the fixed
rule. Next candidate: model-only comparison under fixed base settings, outside this
closed grant. Report: `C:\pt\analyses\context-policy-compare-20260915-v1\result.md`.
All results official=false; no hidden evaluator details used for diagnosis.

## Prior seam: edit-assumption comparison stopped; effect unresolved

User proceed/delegation covers one new A4/B4 group: A=brief-evidence-v1,
B=brief-assumption-v1, order A1/B1/B2/A2/B3/A3/A4/B4. Both use pyfakefs parent-traversal
v2, mini 2026-03-17/medium, segmented-v1, probes enabled with probe-policy none,
repair-recheck, root .env, repeat1 and $1.20 per run/$9.60 aggregate. Global limits
and output admission stay fixed. No historical notes/reasoning/patch/cases injected.
Only the plan-content instruction differs; no review timing, tool, memory or gate change.
This is not reopening the stopped $40 cycle or any other finished grant.

The external operator delegates to run_dev, reserves all slot caps, rechecks frozen
inputs and prepared Docker/image identity, and stops the group on count/provider/
billing/continuation/cleanup or execution-integrity uncertainty. No retry, replacement,
fallback, automatic resume, Docker start/pull/build or extra sample. Settled ordinary
task failure continues the fixed independent order. Acceptance and public behavior,
not plan revisions alone, are the outcome measures. No default adoption or extension
is automatic; hidden evaluator details never inform agent input or causal diagnosis.

Three agent runs completed: A1/B1/B2 all passed public checks and submitted, but
acceptance FAIL/safety PASS. A2 stopped at source preflight: exact-SHA Git fetch
could not connect to github.com:443 after 21,086ms. A2 had zero count/model/tool
calls, zero cost and acceptance/safety NOT_RUN. B3/A3/A4/B4 never started. A later
single TCP check succeeded; the earlier network cause and Git-fetch recovery are
not established. No retry/resume/replacement; this packet is closed, not A4/B4-complete.

A1/B1/B2 used16/27/25 model calls, cost $0.203784600/$0.442179600/$0.421231950.
Total recorded model-rate cost $1.067196150 (uncached equivalent $1.642533750),
all68 usage records known. All68 actual inputs retained task/diff/plan/notes and
current mutation/check feedback; native delivery references resolve in the input.
Last plan revisions2/20/9; findings0/0/2; zero probes. B1 stored/updated n1, delivered
it in9 inputs, then expired it on source change. It also repeated the same53-line
candidate five times against the50-line limit despite delivered typed feedback.
More revisions did not establish better behavior or acceptance. One A/two B agent
observations are unbalanced and insufficient for an efficacy conclusion.

Keep brief-assumption-v1 opt-in; no default adoption or another prompt adjustment.
Before any separately frozen continuation experiment, address/rehearse source
availability. No extra samples based on unused cap. Official mini standard prices
rechecked2026-09-15: input0.75/cached0.075/output4.50 USD/M. Operator9 PASS/3.62s;
final read-only receipts8 PASS/1.06s, Ruff PASS, no runtime change/full-suite rerun.
541 recent and9,658 historical protected files unchanged. Record/report:
`C:\pt\analyses\assumption-planning-compare-20260915\result.md`. official=false.

## Prior seam: opt-in edit-assumption planning implemented and locally verified

`--planning-policy brief-assumption-v1` extends unchanged brief-evidence-v1 guidance
at the existing post-mutation review: tie one newly assumed/reimplemented/bypassed
behavior to a concrete public input/setup and distinguishing observation, carry it
as untested when existing evidence does not address it, and choose a useful next
action. Rejected proposals remain distinct from the current rollback baseline.
This is one content axis, not a new planning phase or a claim of semantic coverage.

Default OFF, old planning prompts/identities, native tool schemas/order, memory,
review timing, tool masks, budgets and finish gates are unchanged. No mandatory
probe, semantic judge, extra call, injected historical case or task modification.
The new policy is bound through the existing v39 wrapper/model/envelope/manifest;
append and segmented context both work. No old run or closed paid packet migration.

Next comparison is fresh A=brief-evidence-v1/B=brief-assumption-v1, changing no other
factor. No new paid packet or live efficacy evidence exists yet. Local records:
`C:\pt\validation\assumption-planning-20260915`. official=false.
Focused55 PASS/101.86s; full2306 PASS/8 skips/921.915s across109 files, Ruff/diff PASS.
Full runtime/test hashes stayed fixed. OFF/baseline/new mock runs each reach one edit,
visible checks, finish and isolated smoke acceptance PASS/safety NOT_RUN, four model
turns/five tools/two segments. Both ON plans reach revision2 in the final actual input.
No count/provider/compact/Docker call; no live behavior improvement measured. The new
instruction adds912 UTF-8 bytes, not measured API tokens. Existing three planning
identities match; 199 recent and 9658 historical protected files remain unchanged.
Full regression exceeded the two-minute target; do not describe it as a fast full cycle.

## Prior seam: verification narrowing traced; no transport loss found in two runs

Read-only A1/A3 public trace audit verified task/diff/plan/notes and count/dispatch
identity across all 32 requests. A1's first edit at T14 already framed verification
as enough for registered checks; A3 T13 said submit if the first check passes before
that check ran. All original public goals remained present. A1 v1's original concern
survived projection and was explicitly resolved by the model at T17 using upstream
PASS; A3 never requested a memory update. No plan/concern transport loss was found.
The projection omits only repeated interpretation text and concern turn metadata,
not original statement/progress/status/evidence. No runtime fix was made.

Public static review: A1 bypassed an already observed file-versus-directory guard
in its new traversal branch; A3's prefix stack discards leading relative `..`.
These are unexecuted public-code observations, not newly reproduced hidden failures.
The focused visible check has four absolute-path calls; its PASS alone cannot settle
all relative/symlink/existing-target assumptions. Do not infer complete upstream
test coverage from its aggregate result. All 32 requests offered run_probe; the
last inputs still had three edits and 24/26 model calls. This was not forced by budget.

Next candidate is one plan-content axis after edits: connect a newly assumed/bypassed
behavior to a concrete discriminating public input/observation, not another goal recap.
No implementation/adoption/new paid packet yet; no mandatory probe, judge or stronger
mask. This does not isolate model ability from earlier prompt/workflow effects.
53 focused contract tests PASS/1.140s; documentation3 PASS, Ruff PASS. 184 recent
and 9,658 historical protected files unchanged; one owned pytest root recycled.
No provider/count/candidate/Docker/evaluator execution or repeated full suite/mock.
Report: `C:\pt\analyses\verification-narrowing-20260915\result.md`. official=false.

## Prior seam: submission-guidance diagnostic closed; no observed action change

Eight independent responses at the two fixed public checkpoints all selected
finish_task: current recommendation A4/4, eligibility-facts-only B4/4. Zero probe,
inspection or edit selections. Removing the latest recommendation did not change
the action here; the cause remains unresolved, not proof the whole harness is sound.
Both source plans already said to submit after the remaining regression passes.
C1 revision15/n1/v1 were delivered; all four responses proposed plan/note updates
and resolving the concern by PASS. C2 revision14 had no notes; all four updates were
null. These are unexecuted annotation proposals, not a new gateway-delivery test.
The full public task was present. Examine earlier verification-criterion narrowing
before adding storage features or forcing probes. Keep runtime/default guidance
unchanged, close the packet, no automatic further sample or default adoption.

Eight count/generation calls, all usage known, four complete pairs, 44.583s;
$0.058860900 of $1.20 (uncached equivalent $0.128758500). B removes 172 UTF-8 bytes /
31 input tokens per request. All eight returned continuations/identities verified.
No tools, correction, retry, normal live row, hidden evaluation or Docker operation.
Task acceptance/safety NOT_RUN; response selection is not submission or task success.
9,658 protected files and 138 recent records unchanged; two owned pytest roots recycled.
Report: `C:\pt\analyses\submission-guidance-20260915\result.md`. official=false.

### Closed diagnostic contract

`diagnostics.submission_guidance_sampler` compares the last current-state action
recommendation with submission-eligibility facts, not a new runtime default.
Two public checkpoints from the closed probe group are fixed: A1 turn17 and A3
turn15. A reconstructs the recorded request; B changes only the latest
completion_guidance.message and next_action (null). Current diff, PASS table,
budgets, tools/order, goals, sources, notes, concerns and authored plan stay exact.
Both source segments already contain no native reasoning; no reset is introduced.
Earlier cues and authored plans remain, so this does not remove every submission cue.

The user's proceed/delegation covers eight independent responses, two per arm at
each checkpoint, mini 2026-03-17/medium/25k, root .env and one shared $1.20 cap.
Reserve complete A/B pairs, count immediately before each dispatch and stop on
uncertainty. No sampled tool execution, chaining, retry/resume, correction, hidden
evaluation, new live row or additional sample. This is a new diagnostic grant,
not reuse of the closed group or the old completion-signal experiment.
The output is action-selection evidence, not task success or a runtime improvement.
No default guidance, plan/memory contract, tool mask, task or global limit changes.
Results belong under `C:\pt\analyses\submission-guidance-20260915`.
Provider-free validation: 23 new cases; 115 combined sampler/documentation/mock
cases PASS in 64.549s, Ruff/diff PASS. The mock reaches isolated evaluation.
No normal runtime change; the preceding full-suite result is not a new execution.

## Prior seam: reusable-probe comparison closed; mechanism unused, no observed advantage

Fresh fixed A=probe-policy none/B=cases-v1, four runs each at `a1156982`, used
pyfakefs v2, mini 2026-03-17/medium, segmented-v1, brief-evidence-v1, probes and
repair-recheck. Only the probe option differed; no previous case/code/plan was
injected. The user's delegation covered this new eight-run group, not an old grant.

| Result | A: none | B: cases-v1 |
| --- | ---: | ---: |
| Task acceptance PASS / all runs | 1/4 | 1/4 |
| Submitted / all runs | 4/4 | 3/4 |
| Recorded USD | 0.932819850 | 1.170729300 |
| Uncached-equivalent USD | 1.596026250 | 1.965868500 |
| Probe calls / cases / replays | 0/0/0 | 0/0/0 |

All 161 exact requests offered run_probe; all 90 B inputs carried the new schema
and empty current catalog. No invocation tested the live storage/comparison/replay
path. This is not evidence that the capability was hidden or that reuse improved
performance. Tied four-run samples establish neither equivalence nor a causal effect.
Retain default OFF and stop this group; no extension, extra sample or stronger mask.

Seven submissions passed current-diff visible checks; isolated acceptance passed
only A4/B1, with safety PASS for all seven. B3 exhausted four edits with a public
regression failure and stopped before another dispatch: LIMIT_REACHED, evaluation
NOT_RUN, still in the denominator. Public trace shows wrong-object helper calls and
file-parent error regressions in B3; no hidden assertion details were read. Both
successful patches recursively process parents, but differ in size/implementation.

Public task/diff/plan/notes delivery verified in every request. Explicit findings
appeared only in A1/B1; no annotation loss was found. Maximum input 52,067 tokens,
request 286,473 UTF-8 bytes, encrypted item 70,776 bytes. 161 generation/count calls,
183 tools, 18 accepted edits; $2.103549150 of $9.60, 35m40.173s. No retry, unknown
usage, compact, post-hoc sandbox run or Docker start/pull/build. Runtime unchanged.
Operator 9 PASS/3.16s, receipt 6 PASS/1.33s; Ruff/diff PASS. Prior full suite/mock
results are not new executions. 9,658 protected files plus 81 recent records remain
unchanged. Two new pytest roots recycled; durable new runs preserved. official=false.
Report: `C:\pt\analyses\probe-cases-compare-20260915\result.md`.
Next analysis should examine verification sufficiency/repair choices, not presume
another storage feature or compulsory probe is justified by non-use.

## Prior seam: opt-in reusable public probe cases implemented and locally verified

`--enable-probes --probe-policy cases-v1` connects an already completed public JSON
observation to a model-authored candidate program and allows exact rerun by case ID.
The same run_probe tool executes only the candidate on rerun; the reference is not
re-executed. Up to three recently executed cases remain in current working state,
with source/reference identity and current/historical diff currency. Store prepared
code at action admission and case definition/result together at completion. Window
and segmented views replace old case state without reviving historical matches.

Default none preserves the existing system prompt, schemas/order and v39 surface
hash. The opt-in contract binds model/envelope/manifest/tool identity. No new tool,
planner/model call, automatic experiment, required probe, action mask or finish gate.
JSON equality to the selected reference is matched/mismatched/not_compared, not task
acceptance, a trusted oracle, or proof the program exercised the intended project.
Reference stdout is bounded to 2,048 UTF-8 bytes; normal probe source/execution limits
and all global budgets stay unchanged. Plans/notes/concerns are not auto-updated.
See [the exact contract](../.agent/probe-cases.md).

Focused 74 PASS/69.014s; full 2,259 PASS/8 SKIP in 824.218s; Ruff/diff PASS.
The focused subset meets two minutes; the full four-worker suite does not.
Fresh OFF/ON mock transcripts both reach isolated task acceptance PASS, safety NOT_RUN.
OFF keeps 4 model/5 tools; scripted ON uses 7 model/8 tools/1 mutation,
reference once and candidate twice, mismatch then
match across the edit. Actual input receipts preserve the case through handoff.
This is deterministic transport/execution evidence, not real-model improvement.
No paid/count/compact call, credential loading, real Docker operation or old resume.
9,658 protected files/eight original journals/closed report plus 92 recent evidence
files verified unchanged. No change to task packages or historical reports.
Report: `C:\pt\validation\probe-cases-20260915\result.md`. All results remain official=false.
Next behavioral step is a fresh fixed comparison with only this option changed;
neither prior planning samples nor a passing mock establish its effectiveness.

## Prior seam: all seven plan-format submissions have public behavior defects

Provider-free diagnosis of the exact seven submitted CAS patches found Linux
public-goal discrepancies in every candidate. BASE plus seven fresh clones ran
16 cases with same-image Python3.10.19 native/fake controls; no patch repair.
Trailing separators bypass parent creation or precreate the leaf; relative-prefix
handling omits the first component or roots at the wrong place; exception ordering
loses side effects. A1/B1 `staging/.` and B3 relative file-parent behavior are new
regressions; file/../child is already wrong in BASE. These are public defects, not
attribution of the historical hidden assertions. A2 was unsubmitted and remains
in the earlier all-run success denominator, not this submitted-code matrix.

B2 gives the clearest evidence-to-candidate gap: its original relative probe
`a/../b/../c` observes native creation of `a`, `b`, `c`, but its candidate creates
only `b`, `c`. Both probe questions/stdout, the full task and revision6 plan were
in the actual first-edit input; notes were empty. The initial code skips creation
of the first relative component; the only later edit removes the caller mode
argument, leaving that path logic unchanged. Presence is not comprehension, but
missing delivery does not explain this instance. Correction: the matrix's first
B2 case is a relative variant; its original absolute a/b/../c probe PASSES the
candidate. A separate same-image replay confirms first-original PASS/second FAIL.

Linux mismatches /16: BASE14, A1/B1/A3=6, B2=12, B3=13, A4/B4=4. This targeted,
post-hoc case set is not a new benchmark or A/B success rate. Native Windows uses
host Python3.14.5 versus fake-on-Linux3.10.19; retain that qualification. Return
status alone is insufficient: B4 raises the expected EEXIST but misses a directory
that native creates before raising. Do not infer all visible tests are absolute:
the custom traversal check is, while upstream regression covers other behavior.

Next design candidate is a small reusable public behavior case connecting reference
observations to execution on the current patch. run_probe already supports edited
code; replaying native-only source does not test the candidate. Existing concerns
are model interpretations, not executable assertions. No new implementation, paid
sample, forced probe/tool mask or default adoption follows from this diagnosis.
This does not isolate segmented-v1's causal effect or rule out other context flaws.

Matrix13.976s, one supplementary B2 Docker execution; owned cleanup confirmed in
all nine. Evidence24 PASS/0.281s, Ruff/diff PASS. No provider/count/compact/hidden
execution, credential loading, Desktop start/pull/build or old resume; runtime
unchanged, no full-suite/mock repeat.9658 protected files/eight old journals/closed
report plus39 recent and22 comparison records unchanged. task_acceptance NOT_RUN,
official=false. Report: `C:\pt\analyses\plan-format-public-20260915\result.md`.

## Prior seam: eight-run plan-format comparison closed; no efficacy signal

At `d2e7e98d`, packet `c1ec4594...` compared old `brief-v1` (A) with
`brief-evidence-v1` (B), four fresh runs each in A1/B1/B2/A2/B3/A3/A4/B4 order.
Both used segmented-v1, mini 2026-03-17/medium, pyfakefs v2, probes/repair-recheck
and unchanged limits. Only the opted-in planning instructions differed. The user's
delegation covered this fixed group without per-run approval; no old grant reused.

| Result | A: brief-v1 | B: brief-evidence-v1 |
| --- | ---: | ---: |
| Task acceptance PASS / all runs | 0/4 | 0/4 |
| Submitted / all runs | 3/4 | 4/4 |
| Recorded USD | 1.514111850 | 1.046292150 |
| Noncached-equivalent USD | 2.303030250 | 1.730925750 |
| Input tokens | 2,315,379 | 1,687,141 |

All seven submissions passed both current-diff visible checks, then EVALUATOR_FAIL
with public class PRIVATE_EVALUATION_FAILED; safety PASS. A2 exhausted four accepted
edits with a failing visible check: pre-dispatch LIMIT_REACHED, evaluation/safety
NOT_RUN, still included in the success denominator. Total $2.560404000 of $9.60;
172 generation/172 count/211 tools, 23 edits, 38m3.623s. No unknown usage, retry,
extra sample, compact call or cleanup uncertainty. Cheaper failed trajectories
do not establish better cost per success; four samples per arm are exploratory.

All172 exact request hashes, public goal/diff/plan/notes and seven submitted patch
identities verify. All eight created plans; all28 B plan texts used the headings.
Major-result plan changes: A19/26, B12/20; changes/nulls are not proof of meaningful
review. New B4 delivered notes in19/21 requests and plan revision7, yet failed.
B1/B2 last stored revisions5/12 versus delivered4/11 are finish-time updates,
not lost next-turn delivery. Maximum input53946 tokens/request283594 UTF-8 bytes/
encrypted item113164 bytes stayed inside segmented management bounds; only
major-result transitions occurred, no size-pressure or incomplete-response path.

Public traces show insufficient candidate verification despite working delivery:
B1/B2 closed uncertainty after visible PASS; B3 kept its pre-repair plan; B4 planned
regression then submission. B2's two valid probes observed native OS behavior on
an empty diff, not the edited fake candidate. All B final inputs still offered
read/search/probe/edit with remaining calls27/25/17/20 and edits2/2/2/1.
A2/A4 also made concrete object-API/anchor/bytes errors; do not reduce every failure
to premature submission. No private details/reference patches were used to explain
these runs, so exact hidden failing assertions remain unattributed.

Do not adopt the new plan format by default, expand tasks or add paid samples from
this completed group. This tests neither planning ON/OFF nor segmented-v1's causal
effect. Next candidate is provider-free public-behavior reproduction on these exact
submissions before another prompt change, not a stronger tool mask or forced probe.
No such post-hoc sandbox execution is included here. Report and frozen receipts:
`C:\pt\analyses\evidence-plan-compare-20260915\result.md`.

Operator mock9 PASS/4.00s and final receipt7 PASS/1.03s; repository Ruff, operator
F/I and diff checks PASS. Runtime unchanged, so no new full-suite/mock-smoke claim.
9658 protected files/eight old journals/closed report plus39 recent inputs unchanged.
Only prepared Docker/images were used; no Desktop start/pull/build or old resume.

## Prior seam: opt-in evidence-linked plan format implemented and locally verified

`--planning-policy brief-evidence-v1` reuses the existing <=3,000-character whole
`plan_update` with three short headings: `Behavior`, `Evidence / open assumptions`,
and `Next discriminating action`. The content contrast connects required behavior,
observed evidence/unresolved assumptions, and the observation that would change
the next edit or submission decision. No task-specific case, repair or hidden hint.
This is a testable format hypothesis, not a demonstrated fix for model reasoning.
Existing brief-v1 prose already requests evidence-aware planning.

Append and segmented contexts are supported. Default none, old brief-v1 instructions,
tool schemas/order, review timing, notes, gates, continuation and global budgets stay
unchanged. Bad/missing headings are not an action error; null preserves the prior
plan. The new instruction contract has its own model/envelope/manifest/tool identity
over the unchanged v39 base. No old-run migration or closed-cycle restart.

Provider-free verification: focused33 PASS/53.18s, Ruff/diff PASS; full2228 PASS/
8 skips/731.984s (106 files, four external-temp workers; no runtime/test change
during execution). OFF/old/new mock each4 model/5 tools/1 edit/2 segments through
isolated acceptance PASS, safety NOT_RUN; both ON revision2 plans are verified in
the next actual input. New instruction text adds904 UTF-8 bytes, not a token count.
Preserved9658 protected files/eight old journals/closed report plus39 recent inputs
and diagnosis files. No provider/count/compact, credential-value loading, Docker
operation or paid comparison. Report and immutable verification receipts:
`C:\pt\validation\evidence-planning-20260915\result.md`.
Next behavioral step is a separately
frozen fresh-run comparison of old/new planning with the same context/model; it is
not executed or authorized by a passing mock. See the
[planning contract](../.agent/planning-experiment.md).

## Prior seam: B's public defects and premature verification closure identified

Both B submissions miss traversal side effects for Linux
`makedirs("staging/../release/")`: the trailing separator makes `tail` empty and
bypasses their new recursive-parent guard. Without the trailing slash both work.
Both also introduce EEXIST for `makedirs("staging/.")`, where real Linux and the
original base succeed. Fourteen public-goal cases, fake Linux/Windows and native
controls reproduce these defects without private test details or candidate repair.
The original B public terminals remain PRIVATE_EVALUATION_FAILED; these examples
are not claimed to identify the exact historical hidden failing assertions.

The incomplete guards were already in first mutations at B1turn17/B2turn11,
before any noninitial segment event. Initial creation of these defects is not
caused by discarding earlier reasoning segments. Public goal/diff/plans/notes and
planning instructions verify in the first-edit/final actual inputs. At finish,
read/search/probe/mutation were still available; remaining calls14/27 and edits1/3.
Both executed zero probes. B1 corrected reported permissions and broken-link errors;
the remaining weakness is checking an incomplete hypothesis beyond passing visible
checks. Plans9/2 were delivered, but narrowed to check completion and submission.
No transport, forced-stop or old-submission defect was found. The causal effect of
the combined segmented policy remains unseparated; no default adoption/removal.

Native Windows/Python3.14.5 disagrees with the assumed universal intermediate side
effect; B matches the simple existing-base case and A does not. Fake modes run on
Linux/Python3.10.19, so retain this version/host qualification. The Linux/native
controls use the same image/Python. A acceptance PASS is not complete conformance.
Do not interpret this targeted post-hoc matrix as new A/B performance evidence.

Five isolated pinned-Docker observations, host controls, exact patch/scope checks:
8.766s; evidence tests13 PASS/0.14s, Ruff/diff PASS, all cleanup confirmed. No paid,
count/compact, hidden rerun, Docker start/pull/build, runtime/task/prompt change or
old resume. 9658 protected files/eight old journals/closed report plus19 recent
inputs preserved. No full-suite/mock repeat for operator-only work.
Report: `C:\pt\analyses\b-failure-public-20260915\result.md`.

The diagnosis proposed one planning-content contrast connecting a specific
assumption, its observed evidence and an untested discriminating case to the next
action. Current prose instructions already ask for this; do not call another
warning a transport fix. No extra planner, mandatory task-specific probe, stronger
tool mask or diagnostic-hint injection. It did not itself implement or authorize a
new paid packet; the opt-in implementation is recorded above.

## Prior seam: public POSIX counterexample rejected the proposed B failure

The provider-free `makedirs("staging/../release")` case from an existing current
directory passes in all four submitted A1/A2/B1/B2 patches. Each creates both
`staging` and `release`, matching real Linux `os.makedirs`; the unmodified base
creates only `release`. This rules out the proposed POSIX parent-existence shortcut,
not the earlier B task-acceptance FAILs or all traversal defects.

The missed dependency was `FakeFilesystem._valid_relative_path`: POSIX prefix
validation precedes normalization, so `exists("staging/..")` returns false and
B's guard correctly enters recursion. The earlier static inference was wrong.
No context/planning/tool-policy repair follows from this result. B's acceptance
failure remains causally unresolved; do not adopt segmented-v1 from input savings.

One public program ran on five fresh local clones (base plus four exact CAS patches),
with native controls and the already-present pinned image. Full diff identity and
scope checks pass; all cleanup confirmed. Execution8.354s; receipt tests7 PASS/0.13s;
repository/diagnostic Ruff and diff checks PASS. No runtime/task/candidate changes,
paid/count/compact call, hidden evaluation, Docker start/pull/build or old-run resume.
9658 protected files/eight old journals/closed report and14 recent evidence files
remain unchanged. No full-suite/mock repeat for an operator-only diagnostic.

Next candidate: the same public behavior in Windows mode, where prefix validation
takes a different branch, with a native Windows control. Not executed or proven
here; no new paid packet. Report and receipts:
`C:\pt\analyses\relative-parent-case-20260915\result.md`.

## Prior seam: B-first segmented comparison completed; no default adoption

Approved packet `1cb64071...` ran once in B1/A1/A2/B2 order at `53a6470c`.
A=append-v1, B=segmented-v1; both mini 2026-03-17/medium, brief-v1 planning,
probes/repair-recheck, pyfakefs v2, fresh starts and unchanged limits. No runtime
changes during the group. A acceptance2/2 PASS; B0/2 PASS. All four passed visible
checks, submitted and received safety PASS. Four samples do not establish superiority.

| Slot | Task acceptance | Model/tools | Accepted edits | Recorded USD |
| --- | --- | ---: | ---: | ---: |
| B1 | FAIL | 27/35 | 3 | 0.354255300 |
| A1 | PASS | 22/23 | 3 | 0.697157850 |
| A2 | PASS | 21/25 | 2 | 0.433121550 |
| B2 | FAIL | 14/14 | 1 | 0.143340900 |

Total$1.627875600 of$4.80,84 generation/84 counts/97tools; group16m6.439s.
No cost/transport/cleanup uncertainty, SDK retry, extra sample or compact call.
A1 had one reasoning-only25k incomplete response with matched integer usage;
the allowed protocol recovery continued to PASS, unlike the prior unknown-usage stop.

B reduced aggregate input from2,322,228 to1,026,380tokens; maximum single input
134,129→47,679tokens and request892,408→245,477bytes. Noncached-equivalent cost
$2.065041→$0.922425. This is smaller input/cheaper unsuccessful trajectories, not
improved cost per success. B segments6/3, all major-result transitions; no live
size-pressure transition was exercised. Do not adopt segmented-v1 as default.

All84 exact request hashes, public goal/diff/plan/note/concern delivery and all four
final-input/submitted-patch identities verify. Stored/last-delivered plan revisions:
B1=9/9,A1=5/4,A2=7/6,B2=2/2; A's final update accompanied finish. B1/A2 each had
one finding that later expired with source_changed; their concern remained visible.
A1/B2 generated no findings. Transmission worked on these checks; semantic use and
optimal evidence selection are not established. Hidden details were not used in analysis.

Next seam: provider-free public-case verification of B's recursive parent-existence
guard for relative traversal from an existing base, before any context/planning fix
or new paid packet. This is a public-code hypothesis, not the proven hidden failure.
No extra case was executed here. The group is complete and its grant consumed.
Report: `C:\pt\analyses\segmented-pilot-bfirst-20260914\live-result.md`.
Operator mock5 PASS/0.921s; Ruff/diff PASS; runtime unchanged, no full-suite repeat.
9658 protected files/eight old journals/old A1/packet preserved; no Docker start/pull/build.

## Prior seam: B-first segmented comparison preparation (provider-free)

Prepared a separate B1/A1/A2/B2 packet after the usage-diagnostics repair. The old
group stopped before any B sample, so this predeclared balanced mirror starts B;
it does not resume the old group or reuse A1. A=append-v1, B=segmented-v1, both
brief-v1 planning/probes/repair-recheck, mini 2026-03-17/medium, pyfakefs v2,
root `.env`, repeat1, unchanged limits and desired25k output ceiling. Proposed cap:
$1.20 per fresh slot / $4.80 total, two samples per arm. No default agent change.

`diagnostics.segmented_pilot prepare --order b-first` selects this order; the
existing default stays a-first. Inspection binds the order, exact fresh slot paths,
requests and caps as well as runtime/task/config identities. Cost observations
include SDK field presence, count relation and UNKNOWN billing, not just legacy sums.
Preparation cannot execute runs, load credentials or inspect Docker. Actual input
fit is still measured only by the runner at dispatch, not by the task-only rehearsal.
Destination: `C:\pt\analyses\segmented-pilot-bfirst-20260914`.
Packet `1cb640713918beacd3f45dfa3d20b5688111060def697a4910fe9eba5a4a4097`,
prepared at `cba713fb`; repeated read-only inspect PASS. No live state/approval
created, provider/count/compact/Docker calls0. See that directory's `result.md`.
This is a new packet proposal, not approval or evidence of A/B improvement. The
stopped packet/grant remains closed; exact new-packet approval precedes paid work.
Focused packet/usage/source-gate tests56 PASS/7.163s; Ruff/diff checks PASS. Local
CSV mock append/OFF and segmented/brief-v1 both reach isolated acceptance PASS,
safety NOT_RUN (3.917s/4.521s); segmented delivers revision2 across two segments.
Receipt: `C:\pt\validation\segmented-pilot-bfirst-20260914`. Production runtime
hash is unchanged from the prior full-suite receipt, so the full suite is not repeated.
Focused command/Ruff/mock command total18.20s. Protected9658 files, eight planning
journals, old A1 and old packet unchanged; .env only integrity-hashed, not loaded.
Official standard/global rates checked2026-09-14: $0.75/$0.075/$4.50 per million
input/cached-input/output tokens ([API pricing](https://developers.openai.com/api/docs/pricing)).

## Prior seam: provider usage evidence (provider-free)

The adapter now preserves missing/null/literal-zero/invalid SDK usage fields before
compatibility defaults, plus count relation/delta and bounded failure kind.
Missing output usage cannot silently become free output; malformed cache counts
cannot silently be clamped into accepted usage. The existing absent-cache-breakdown
no-discount fallback is preserved and marked. Reasoning/total counts remain telemetry.
Provider/decision events, crash recovery and terminal/public `provider_usage_failure`
retain this evidence; `billing_state=UNKNOWN` qualifies the legacy cost sum.
The compatibility error/terminal and whole-invocation stop remain; no correction,
retry, later repetition or continuation recovery can bypass billing uncertainty.

This is observability/accounting validation, not a repair of the provider's
reasoning-only response. A1's missing-vs-null-vs-zero condition is still unknowable
from its old normalized counters. No old run/packet/approval is changed or reused.
No input/schema/tool-policy/planning/model change, paid call or Docker operation.
Tool-surface remains v39; runtime content changes and exact old resumes are not migrated.
Verification receipts: `C:\pt\validation\usage-evidence-20260914`.
Focused136 PASS/76.190s; final affected81 PASS/111.011s; Ruff/diff checks PASS.
Full105-module/2199-case run took1100.846s and found11 packet-test setup failures:
those unit tests incorrectly required a committed developer checkout. Only their
fixture changed afterwards, with a regression proving the real source gate still
blocks preparation. Final combined receipt:2192 PASS/8 SKIP, not a second full run.
Local CSV mock append/OFF and segmented/brief-v1 both reach edit/check/finish/isolated
acceptance PASS, safety NOT_RUN (8.459s/10.079s); segmented delivers plan revision2
across two segments. Protected9658 files, eight old journals, A1 and packet unchanged.
Follow-up: a separately frozen comparison packet for the changed runtime;
the stopped A1/B1/B2/A2 group remains closed, with no automatic paid execution.

## Prior seam: approved segmented pilot stopped on A1 usage uncertainty

The new packet `1615423f...` was approved and dispatched at `c3ae0bff` on 2026-09-14.
A1/append-v1 (`run_dev_f2f219820e874648`) ended `PROVIDER_TIMEOUT_OR_UNKNOWN` after
16 model calls / 16 counts / 20 tools / 3 accepted edits, 364.384s. This was **not
a demonstrated transport timeout**: response 16 returned reasoning-only incomplete,
reason `max_output_tokens`, but its normalized usage counters were all zero against
a successful pre-dispatch count of 79,749. The adapter's missing-usage/zero-value
normalization does not preserve which raw condition occurred. Billing is UNKNOWN;
recorded model-rate cost for the first 15 responses is $0.218970, not total invoice cost.

The frozen group stopped without retry. B1/B2/A2 were NOT_STARTED; no submission
or evaluator, so task acceptance and safety are NOT_RUN. No A/B efficacy conclusion.
All 16 final request hashes, public task/current diff and plan/note delivery validate.
Plan created once, updated 11 times; revision12/263chars reached the last request.
Three of four consumed major-result review opportunities updated the plan; initial
draft is counted separately, and the final pending review had no normal decision.
Explicit findings stayed empty in all 16 requests. First edit was call9; two of
13 inspections gained no new coverage. Mode and upstream failures each received a
repair and passing recheck, but the earlier contract PASS expired after the last edit.

Last input: 355,075 complete serialized UTF-8 request bytes / 69 items, largest
replayed cipher28,600bytes. The response produced a new1,675,704-byte encrypted item,
stored but never resent. This is not the previous oversized-input rejection, nor
proof of exactly25k tokens consumed: reliable final usage is unavailable. Read/search,
replace/check/probe/stop remained available and completion was possible.
Runtime/packet/9658protected files/eight old journals/closed result are unchanged.
Result: `C:\pt\analyses\segmented-pilot-20260914\live-result.md`.
Next candidate is provider-free diagnosis of missing/zero/mismatched usage evidence;
do not weaken uncertainty stops or restart this group automatically.

## Prior seam: fresh segmented-policy pilot preparation (no paid execution)

`diagnostics.segmented_pilot` prepares/inspects a separate four-run packet; it cannot
execute runs or load credentials. Proposed order A1/B1/B2/A2, A=append-v1,
B=segmented-v1. Both use brief-v1 planning, probes, repair-recheck, pyfakefs
parent-traversal v2, mini snapshot 2026-03-17/medium, root `.env`, repeat 1,
unchanged 40/100/4/1800 limits and 25k desired output ceiling. Proposed new cap:
$1.20 per invocation / $4.80 group. Closed planning/compact grants are not reused.

Packet destination: `C:\pt\analyses\segmented-pilot-20260914`. Freeze runtime/task/
model/sandbox/schema identities and distinct fresh slot roots. The task-only input
rehearsal verifies equal public information, not a real initial request or token fit.
Actual dynamic requests remain journaled and counted by the existing runner.
Official standard/global mini prices were checked on 2026-09-14 against the
[API pricing table](https://developers.openai.com/api/docs/pricing):
$0.75 input / $0.075 cached input / $4.50 output per million tokens.

This is a combined-policy exploratory comparison, not an isolated test of reasoning
reset or state compression. Record acceptance/submission, repair/recheck, actual
plan/note delivery, request bytes/tokens and settled/noncached-equivalent cost.
Two samples per arm do not establish superiority. Stop the entire group on cost,
provider/count, execution/cleanup or integrity uncertainty; report unstarted slots.
Preparation does not authorize execution. Exact new packet approval is the next gate;
no B4 resume, old sample reuse, Docker start/pull/build or default-agent change.
Validation: 12 packet + 35 segmented regression tests PASS in 75.540s, Ruff/diff
checks PASS. Local CSV mock reaches one edit, checks, finish and isolated acceptance
PASS/safety NOT_RUN in 5.503s (four mock turns, five tools, two segments, zero cost;
no real probe/Docker). Receipts: `C:\pt\validation\segmented-pilot-20260914`.
The runtime hash is unchanged from the prior full suite, so it was not repeated.
9658 protected files, eight old journals and the closed-cycle result remain unchanged.

## Prior seam: v39 segmented public working state (provider-free)

Implemented opt-in `--context-policy segmented-v1`, supporting planning none/brief-v1.
Defaults stay append/OFF. Native reasoning/call/result identity stays exact inside
each segment; after major-result review or size pressure, the next segment receives
current public facts and latest unverified notes/plan, not older reasoning/history.
No summary/planner/compact call or new action schema. Required task/diff/check/failure/
mutation evidence and global execution/cost limits do not depend on model annotations.

Experimental management bounds: 60,000 counted input tokens, 1 MiB complete UTF-8
request JSON and 256 KiB per encrypted item. Byte checks precede counting; changed
requests are recounted. A fresh handoff still too large ends LIMIT_REACHED. These
are not inferred API limits. Unknown provider/count/cost state or corrupt artifacts
cannot be bypassed by segment switching. CAS-before-event handoffs and native/count
recovery preserve global counters and pending-action idempotency; no old migration.

B4 read-only projection with identical current schemas/settings: 2,175,132 -> 99,185
bytes (85 -> 5 items). All 261 selected source lines, exact task/diff/check status,
bounded mutations/correction remain; total retained observed lines 815. No unseen
source added. Previous-segment reasoning/native history is omitted, while historical
plan revision 1 and empty findings remain unchanged. No task-success inference.
Evidence: `C:\pt\validation\segmented-context-20260914\b4-comparison-verified.json`.

Validation: final segmented/hash-contract focus 44 PASS / 81.734s; shared planning,
window/continuation/source focus 139 PASS / 104.212s. Full 103-file suite took
762.928s: one stale v38 expected hash failed, then the repaired module and strengthened
mutation crash cases passed targeted rerun with production runtime unchanged.
Combined receipt: 2147 PASS / 8 skips; not a second full-suite invocation.
Ruff/diff checks PASS. Final planning OFF/ON local smoke each uses four mock turns,
five tools, one mutation, two segments through isolated acceptance PASS / safety
NOT_RUN (3.649s / 4.061s). ON revision 2 is delivered after handoff; empty OFF/ON
findings remain empty. Source-note tests separately prove retention and expiry.
9658 protected files, eight original journals and closed-cycle result are unchanged.
No real provider/count/compact call, Docker execution, old-run resume or new paid
comparison occurred. The closed planning cycle and B4 remain immutable.
Contract and remaining performance risks: `.agent/plans/segmented-context.md`.

## Prior seam: oversized-continuation diagnostic complete; compact also rejects the item

The separately approved packet `9cf5b985...` ran once at `6bf1aa68` on 2026-09-14.
Standalone compact returned HTTP 400 `string_above_max_length` for the same
`input[83].encrypted_content` that input counting rejected in B4. Terminal:
`COMPACT_ENDPOINT_REJECTED_INPUT_SIZE`; no compacted window or usage was returned.
Exactly one compact attempt, no retries/count/generation/tools/Docker/activation;
client cleanup CLOSED. Model-rate and invoice costs remain unknown, not zero.

This rules out post-failure standalone compact of this exact unchanged window as
a working recovery path. It is not just a count-endpoint failure or oversized plan.
No numeric field limit, context-token fit, reason for the preceding reasoning-only
response, or guaranteed prevention by earlier compaction is established. The next
step is to clarify provider continuation input/output compatibility before selecting
a preventive runtime change; do not restart the planning comparison or retry this
input under the consumed grant. No default runtime/planning change was made.

Result, authorization and audit: `C:\pt\analyses\oversized-continuation-live-20260914`.
Durable output: the prepared packet's `execution` directory. Two result-only
recoveries are byte-idempotent; 9658 protected files, all eight source journals and
the closed cycle result remain unchanged. The preparation's NOT_AUTHORIZED flags
are historical; the separate live `approval.json` records the user's later grant.

### Prior preparation: one standalone request, provider-free validation

`diagnostics.oversized_compaction` now prepares, inspects and collects at most one
separately authorized standalone compact request. It uses B4's exact failed input
(85 items, one 1,717,452-character encrypted item), not a healthy earlier cutoff.
It does not retry count, generate an action, activate a window, or resume B4/the
closed planning cycle. The native runtime and planning defaults are unchanged.

The executable packet is `C:\pt\analyses\oversized-continuation-executable-20260914`;
its full hash, commands and claim boundaries are in its `result.md`. Two no-call
inspections agree. Source/request, installed SDK, implementation, credential path,
cost reservation and destination are bound before dispatch. A fresh-directory
claim and execution lock prevent reuse; interrupted work recovers evidence only.
Usage persists before output validation. Only a complete valid public/opaque
window is retained; malformed output is rejected without saving plaintext reasoning.

The $1.20 diagnostic budget reserved $0.876 using published model limits;
this is **not an API-enforced dollar/output cap**. The separate approval accepting
that limitation was consumed by the call above; the closed $40 cycle is not reused.
The preparation itself made no API call or credential-client load. Source context
fit remains unverified despite the known field-size rejection. Official contract:
[compact parameters](https://developers.openai.com/api/reference/python/resources/responses/methods/compact),
[whole-window handling](https://developers.openai.com/api/docs/guides/compaction).

Provider-free validation: 205 focused/compaction regression tests PASS in 87.33s,
Ruff PASS, and OFF/ON mock smoke each reaches edit, checks, finish and isolated
acceptance PASS/safety NOT_RUN (four mock turns/five actions, zero provider cost).
9658 protected files, all eight original journals and the closed-cycle result match.
Receipts: `C:\pt\validation\oversized-compact-20260914`. The full suite was not
repeated: runtime bytes still match the preceding 2069-pass verification below.

### Prior intervention: planning content guidance revised; comparison remains closed

The supplied public-case/advice experiments below are closed diagnostics, not the
next execution queue. The current intervention is `--planning-policy brief-v1`,
OFF by default and append-v1 only: a short public work plan updated alongside a
normal tool action. No planner API, mandatory probe, stronger tool mask, memory
rewrite or context-policy change is added. Plans are unverified model-authored
records; they do not grant check PASS or submission eligibility.

The post-cycle public audit found no lost annotation or missing review signal.
All 191 actual model requests had empty explicit findings; the only note creation
was in A2's final submission response. B4 made error-driven repairs despite its
unchanged initial plan, so neither model incapacity nor plan staleness as the cause
of failure is established. The audit is at
`C:\pt\analyses\planning-memory-audit-20260914`.

The current runtime changes only planning content instructions: name concrete
unfinished work and the observation/check that could settle an assumption; after
an observed result, state what it confirmed/contradicted/left unresolved and the
remaining work and verification. Generic workflow recaps and invented updates
are discouraged. Null, review timing/consumption, storage, schema/order, notes,
tool policy and budgets are unchanged. The existing instruction-hash binding
updates ON identity without migrating old runs. This is a provider-free change,
not a new live group, adoption or evidence of improved model behavior.

This change passes 54 focused tests in 37.01s, Ruff, and the complete provider-free
suite: 2069 passed/8 skipped in 708.903s (101 files, four isolated temporary roots).
The full-suite two-minute target was not met. OFF/ON mock smoke each reaches one
edit, checks, finish and isolated acceptance PASS/safety NOT_RUN in four mock turns
and five actions, with zero provider calls/cost. Validation receipts and the exact
content-only/OFF-parity audit are at `C:\pt\validation\planning-content-20260914`.

The user authorized this improvement cycle up to $40 without repeated per-run
approval. Each fresh mini/medium invocation remains repeat=1, capped at $1.20,
with probes and repair-recheck enabled in both arms and the existing 40/100/4/1800
limits. First compare four OFF/four ON pyfakefs-v2 runs; at most two justified
single-axis planning revisions and qualified loguru-v3/hf-v1 extension follow.
Maximum 32 runs/$38.40 of reserved invocation caps; unused budget is not a target.
The first eight fresh runs executed at `5bdb524a`: OFF acceptance 1/4, ON 0/4;
both arms submitted 2/4. Durable model-rate cost is $4.064418300, not invoice/count
billing verification. B4 stopped the cycle at `COUNT_TIMEOUT_OR_UNKNOWN`: a known
HTTP 400 `string_above_max_length` for `input[83].encrypted_content`, not an actual
timeout. Its preceding response spent all 25,000 output tokens in reasoning,
returned no action and produced one 1,717,452-character encrypted item. The next
model call was never dispatched. No retry, second version or extension ran.

All four ON drafts were created and actual delivery verified. Only 1/30 valid
post-initial review decisions updated the plan; three plans remained exact initial
inspection/edit/check descriptions. B1 stopped with an incorrect completion claim
despite a current NOT_RUN check and `run_check` being available. These observations
do not establish that plan staleness caused task failure. Keep planning OFF; no
benefit/adoption claim. The cycle is stopped, not a pending paid queue. A separate
provider-returned continuation-size contract investigation precedes any future
comparison; do not reset state or change ceilings to bypass this stop.

The first implementation's focused validation passed 66 tests with
4 unsupported-combination skips in 104.018s. The complete rerun passes 2067 tests
with 8 skips in 640.416s (101 files, four isolated workers); the two-minute overall
target was not met. Six old live-checkpoint tests now verify read-only rejection
on runtime mismatch, preserving their compatible-runtime replay assertions and
all old code/packet bytes. Ruff and both OFF/ON mock smoke pass; each mock makes
one edit, checks, submits and reaches isolated acceptance PASS/safety NOT_RUN.
The OFF prompt/schema/decision wire is unchanged, and 9658 protected files match.

`diagnostics.planning_cycle` freezes each group's runtime/task/configuration and
reuses completed results or exact native recovery. It stops the whole cycle on
provider/count/cost/integrity/cleanup uncertainty. Prepared Docker/images only;
no automatic start/pull/build. Details and the predeclared decision rule are in
[the planning experiment contract](../.agent/planning-experiment.md). External evidence
are at `C:\pt\analyses\planning-cycle-20260914\result.md`; local receipts live under
`C:\pt\validation\planning-cycle-20260914`. All results remain `official=false`.

## Targets and limits

- focused local validation: under 2 minutes
- default one-row live limit: 1,800 seconds
- 40 model calls, 100 tool actions, and 4 accepted mutations
- one consecutive protocol/incomplete correction and at most 4 parallel reads
- budget-only public inspection with advisory coverage/causal signals, a bounded
  two-call mutation-rejection allowance and order-independent distinct-check recovery
  reserves; legacy 24/3 counters are telemetry only
- `repeat=1` by default, 6 maximum, under one invocation-wide cost cap

## Local storage housekeeping

The user-approved 2026-09-10 cleanup recycled 598 completed standalone pytest
temporary roots: 115 directly under `C:\` and 483 inside the existing scratch
containers. These held 748,262 files / 1,894,300,495 logical bytes. The number of
top-level `C:\` directories fell from 167 to 52. The Recycle Bin was not emptied;
this is recoverable housekeeping, not a claim that disk space was freed.

Exact source/Recycle Bin mappings and preservation checks are retained under
`C:\pt\maintenance\cleanup-20260910`. All 42 primary run journals, actual run and
analysis records, credentials, user-owned `AGENTS.md`, and historical report/archive
bytes remain unchanged. Recycled test trees match their pre-move file metadata;
retained evidence and protected files pass content-hash checks. Historical test
basetemp references may now point to recycled scratch; do not rewrite those receipts
or confuse that disposal with missing live-run evidence.

New disposable test roots belong under `C:\pt\tmp`, with validation reports stored
separately and the owned scratch recycled after process completion/diagnosis. The
human operations guide and agent guide now document that lifecycle. Three focused
documentation tests and Ruff pass. Runtime/task bytes are unchanged; no new full
runtime suite, mock smoke, Docker operation or provider invocation was required.

## Closed diagnostic: supplied-case A/B, no behavioral improvement

The exact `1f8bc6f5...` packet ran once from the frozen A2 checkpoint. All four
branches chose finish on their first response, submitted unchanged `5c3c2067...`
(23 added lines), and made no new mutation, registered check or probe. Both inherited
registered checks remain PASS, but the fixed operator public case is FAIL: expected
`a,b,c`; actual `a,a/b,c`. One identical final candidate was audited once and reused.

Both B requests contain the same supplied code, `no_current_result`, and advisory
`next_action=run_probe`; the tool is available. Each first view retains 16 model/75
tool/one mutation and 1590 seconds. No context loss, action mask, token/cost/horizon
exhaustion or provider uncertainty explains this immediate finish. Public decisions
cite check PASS and retain the wrong n2 interpretation of skipping `..`. Memory is
present, but its interpretation is model-authored and unverified. Its causal influence
was not separately tested. Unknown concern-ID updates were rejected non-blockingly;
those errors did not prevent probes or terminate a repair attempt.

Initial delivery/advice works, but no probe/edit means later case replay, historical
currency and delivery dedup remain mock-tested, not exercised by this live comparison.
Do not adopt this advice by default or claim an autonomy gain. The prior current-failure
experiment elicited repairs when concrete failure was supplied; merely supplying its
program/status did not elicit observation here. The next direction was subsequently
replaced by the explicitly approved planning cycle above. This old packet grants no
new execution; its one-checkpoint/two-per-arm contrast does not identify an internal cause.

Evidence: `C:\pt\analyses\public-case-live-20260914` (`result.md`, masked-code review,
audit/transcript/context and immutable journals); same-name validation receipts.
Four Responses/counts/actions, 40.638s, known model-rate cost $0.130343400. Count
billing/invoice UNVERIFIED; cached-input differences are not efficiency evidence.
All 8782 protected hashes match; the single operator container is confirmed absent.
Actual wire matches the approved manifest hashes. Stored A/B JSON files use canonical
object-key order, so a prior audit's file-equals-wire assumption was corrected without
changing requests or rerunning. Masked code observations preceded labeled verdicts,
though the recognizable baseline prevents a claim of perfect blinding.

Approval consumed; no automatic paid retry/resume/extra samples, Docker start/pull/build,
hidden evaluator or default runtime/task changes. Task acceptance/safety NOT_RUN,
official=false. This is a failed behavior intervention, not a missing live result.

## Prior supplied public-case lifecycle implementation

`diagnostics.public_case_lifecycle` and `diagnostics.public_case_rollout` implement
the selected small experiment. Both arms receive the same frozen public program and
original report. Only B adds exact-program/current-diff execution references and
advice; default runtime, tools, notes, gates and budgets are unchanged.

Case identity is harness-owned. Match raw UTF-8 source and the durable action/input,
full diff, task/environment and execution receipt. Preserve exact-case evidence after
unrelated probes, make it historical after edits, and retain currency after rollback.
Process completion (including stdout false), check PASS and concern resolution never
become semantic PASS: behavior remains NOT_ASSESSED. Guidance uses only offered tools,
keeps required repair/check priorities, and does not require a probe before finish.

The identical public source is delivered once per native append history, followed by
a verified source reference; missing delivery falls back to the same bounded body.
Result bodies stay in native feedback, not duplicated in the status. Case/receipt
bindings are durable and replayable without extra tools or provider calls. Unknown
dispatch/cost and existing cleanup/deadline rules retain priority. CLI output hides
labeled candidate/case verdicts so masked code observations can precede unblinding.

Fresh executable preparation: `C:\pt\analyses\public-case-rollout-20260914`; receipts
under the same name in `C:\pt\validation`. First inputs retain the report-only A2
cutoff/native prefix; no newer failure report, repaired branch or private material
is added. This tests use of a supplied case, not autonomous case generation.
Preparation uses no credentials/count/provider/Docker/candidate execution. All 43 new
tests and 125 selected regressions pass; the four-arm mock covers repair, public check,
optional exact-case probe, finish and separate operator audit. No hidden evaluator or
full default runtime suite was rerun. This is contract verification, not agent success.
No-call preparation/two identical validations took 2.228s; 8761 protected hashes match.
Focused validation plus final Ruff/docs recheck took 105.471s. A validation-helper-only
line-length error was corrected; its failed receipt is retained. Four owned pytest
roots were recycled with content-hash/restoration receipts; no durable run was moved.

Proposed A1/B1/B2/A2 remains mini/medium/25k, <=8 new responses and $1 each/$4 total,
with inherited 16 model/75 tool/one mutation. Exact new approval is required after
local validation; no retry/resume/extra samples or Docker start/pull/build is authorized.
Task acceptance/safety NOT_RUN, official=false; no default adoption or quality claim.

## Prior public-case replay/lifecycle design

The next experiment is specified at
`C:\pt\analyses\public-case-loop-design-20260914\design.md`. It is design-only,
with no provider/count, Docker or candidate execution and no default runtime change.
Existing `run_probe` already binds source/diff identity; verification concerns bind
model judgments, not same-case semantic coverage. The earlier report-review arm
already supplied reminders, so another longer reminder is not the selected change.

Both fresh comparison arms will receive the same sealed public reproduction program.
Only B adds bounded exact-program/current-diff execution tracking and corresponding
advice. Retain actual output references; process completion, registered-check PASS
and concern resolution never become automatic case PASS. Current results become
historical after edits; unrelated newer probes do not erase matching evidence.
Use the existing run_probe inputs, voluntary actions, native/opaque history and caps.
Do not add forced probes, submission gates, case-ID tool shortcuts or planning tools.

This tests use of a supplied case, not autonomous counterexample generation. Reuse
the report-only A2 checkpoint; add no later failure result, other branch's repair or
hidden material. Source is identical across A/B; differences are lifecycle/advice as
a single treatment, not separated subfield effects. Proposed $1 each/$4 total is not
approval. The implementation above follows this design; an exact execution grant
still requires the new locally verified executable packet.

Existing-contract validation: 80 tests and Ruff PASS in 16.413s; no-call source/cutoff
feasibility 0.447s. The frozen public source is 3222 characters/UTF-8 bytes and fits
the unchanged probe limit. All 8751 protected hashes match. This validates design
dependencies, not a new feature or agent improvement. One owned pytest root was
recycled with content hashes/restoration mapping; actual run/workspace bytes remain.

## Prior current-failure A/B executed; local repair signal, no adoption

The exact `4eacdc10...` packet ran once: A1/B1/B2/A2 from the frozen nested A2
checkpoint, mini/medium/25k, $1 each/$4 total. A1/A2 submitted the unchanged
`5c3c2067...` candidate and both fail the independent public case. B1/B2 each
made an immediate stack/pop repair and both pass that case. B1's new bytes/str
concatenation regression fails the visible parent-traversal check at fake_os.py:955;
B2 passes both visible checks and submits `6d7c7010...` (517 upstream tests pass,
570 skip). Public-case repair is not hidden acceptance or broad correctness.

B1 spent its last inherited mutation allowance; after the check failure, 14 model
calls/73 tool actions but zero mutations remained. The horizon stopped it before
another count/provider call. This is not token, cost or transport exhaustion.
No branch ran an agent probe. B2 still said no further probe was needed despite
having that tool; its same-case PASS comes only from the post-episode operator.

Native/opaque history, exact frozen first requests and B-only report delivery pass
integrity checks. B's report becomes historical after mutation. Initial notes and
guidance are identical across arms; B2's later note updates reach subsequent requests.
Both B repairs preceded new notes. Memory delivery is not missing, but model-authored
interpretation and completion judgment can remain wrong. No mandatory gate is justified.

Evidence: `C:\pt\analyses\current-failure-feedback-live-20260914` (`result.md`,
audit/interpretation/transcript/context and container receipts); validation same-name
under `C:\pt\validation`. Eight Responses/counts/actions, three operator executions
with one identical-candidate reuse, 111.427s, known model-rate cost $0.469017450.
All 7852 protected hashes match; six owned containers are absent. Count billing/invoice
UNVERIFIED; cached-token differences are not efficiency evidence. Collector stdout
revealed labeled outcomes before masked code review, so do not claim a fully blind review.

Next: design one generic public-case verification/completion loop experiment, keeping
registered-check PASS distinct from reproduced-case resolution. No hardcoded fix,
forced memory/plan, default adoption or automatic paid continuation. One selected
checkpoint/two samples per arm do not establish generalization or autonomous discovery.
This approval is consumed. Runtime/task are unchanged; hidden/task acceptance and
safety NOT_RUN, official=false; no retry/resume/extra sample or Docker start/pull/build.

## Prior current-failure collector, provider-free validation

`diagnostics.current_failure_feedback_rollout` now connects the frozen comparison
to the existing bounded dispatcher, public gateway, recovery and operator audit.
It restores the nested A2 prefix against the original run's runtime/task/base
contract. The inherited 24 model calls, 25 tool actions and three accepted edits
leave 16/75/1; old provider usage is evidence, not new diagnostic cost.

Both arms keep the original report. Only B durably binds the newer current-diff
observation, projecting it once in each unsent request/context. After a mutation
it becomes historical; rollback keeps it current. Notes, opaque/native history,
registered PASS, completion guidance, tool order and voluntary finish stay intact.
Report corruption blocks pending tools, while provider/count uncertainty keeps
its prior priority. Recorded terminal recovery is read-only; there is no resume
command or permission to retry an interrupted paid experiment.

The proposed one-shot packet is A1/B1/B2/A2, mini/medium/25k, eight new responses
maximum per branch, $1 each/$4 total, root .env, probes/recheck enabled. Full output
reservation and independent caps remain; unused branch funds do not transfer.
The fixed public case audit runs only after settled episodes, with same-candidate
reuse and no agent credit/feedback. No hidden evaluation or default agent change.
Actual paid execution still requires separate approval of the executable packet;
the previous input-preparation grant is not that approval.

Executable packet: `C:\pt\analyses\current-failure-feedback-rollout-20260914`
(`result.md`, `plan.json`); validation receipts use the same name under
`C:\pt\validation`. Plan SHA-256:
`4eacdc10d51c4e3589f25013504f399621dfa1909bc00f6a8fa7276b7113ab0c`.
106 focused/compatibility/documentation tests and Ruff PASS in 52.829s. No-call
preparation and two validations took 1.400s with network/process/key loading blocked;
all 7830 protected hashes match. Mock four-arm execution covers repair/check/finish,
independent caps, uncertain dispatch and pending replay; it is not semantic repair
evidence. No real provider/count, Docker or candidate-code execution occurred. Full
runtime suite/isolated-evaluator smoke were not rerun: default runtime is unchanged.
Next: separately approve this exact four-branch packet, then verify current prices
and already running Docker/images before the one-shot comparison. No default adoption.

## Prior current-candidate comparison input preparation

`diagnostics.current_failure_feedback` prepares/validates the next comparison; it
has no run command. Both arms restore report-only A2 immediately before its last
decision (`turn_25853d06430f4e199d6b7b8ae68fd82f`), on failed diff `5c3c2067...`.
A retains the old historical report; B adds the independently observed current
result: relative entries `a`, `a/b`, `c`, versus expected `a`, `b`, `c`. The input,
fixture and expected behavior come from the same existing public reproduction.
No fix hint, new source, fake failed check or mandatory action is added.

All 24 opaque reasoning items/native call-result pairs, notes, source delivery,
tools, registered PASS and finish eligibility remain unchanged. A's request is
byte-identical to its recorded input count request (540827 bytes); B adds 1296 bytes.
Only the latest unsent snapshot differs. After an edit the supplied failure is
historical, not a verdict on the new candidate. The old final response and other
branches' repair code are not inputs. This is a post-hoc selected failure case,
not autonomous discovery or evidence that the new agent would have succeeded.

Proposed next execution is fresh A1/B1/B2/A2, at most eight new responses each,
mini/medium/25k, with a planning-only $1 per branch/$4 total cap. This raises the
old $0.50 branch cap to reduce known censoring of repair/check/finish, but does not
guarantee eight funded calls. No paid execution is approved by preparation.
Its then-next step was collector adaptation, mock recovery and executable sealing;
that step is now completed above, without granting paid execution.
No default runtime/task change, new candidate execution or Docker operation.

Prepared inputs: `C:\pt\analyses\current-failure-feedback-20260914` (design.md and
packet.json); receipts: `C:\pt\validation\current-failure-feedback-20260914`.
91 focused/compatibility/documentation tests plus Ruff PASS in 47.747s; no-call
preparation and two validations took 0.412s. All 7809 protected hashes match. Full
runtime suite and isolated-evaluator smoke were not rerun: this adds only an
input-preparation diagnostic, not an execution/default-runtime change.

## Prior report-aware review execution: mixed result, no adoption

The approved `08e28fe7...` packet ran once in fixed A1/B1/B2/A2 order. Final candidate
case outcomes are A1 PASS, A2 FAIL, B1 PASS, B2 FAIL: one of two in each arm, not a
general success rate. All eight new registered checks PASS. A1's candidate was not
submitted: full25k cost reservation censored it before its fifth provider dispatch.
B1/B2/A2 submitted; hidden/task acceptance and safety remain NOT_RUN, official=false.

B1 repaired with a component stack, then probed the reported path. The first probe
used nonexistent fs.path; the agent corrected the probe and observed a/b/c directories
with mode0755. This is relevant same-input evidence, not a complete oracle reproduction
(fixture/cwd/umask are not explicitly set; all entries are not enumerated). The separate
fixed operator case PASS is independent evidence. The correct mutation preceded probes.
B2 still submitted break-to-continue code producing a,a/b,c, exactly like A2. Its final
view retained modified_unverified, recommended run_probe, and actually offered that tool;
16 model calls/75 tool actions/one mutation remained. Delivery worked; consistent action
selection and causal repair did not. The internal model cause remains unseparated.

A2 wrote/reused an incorrect causal note before submission, so absent memory alone is
not an adequate explanation. B1/B2 wrote notes only alongside finish, not before their
earlier choices; nonexistent v1/v2 resolutions were rejected without blocking valid tools.
No report loss, missing opaque/native history, tool closure or protocol error was found.
This small comparison does not justify default adoption or another mandatory gate.

Evidence: `C:\pt\analyses\report-review-live-20260914`; result.md/audit.json,
public-transcript/context-notes-audit, blind-review, interpretation and container records.
18 Responses, 19 counts, 18 agent actions, three separate operator executions with one
identical-candidate reuse; 224.595s; known model-rate cost $0.729577950. A1 had no cache
hits and was censored with $0.125567750 left against a $0.210039750 next-call reserve
(130053 input plus full25000 output). Other branches had cache hits, so neither cost
nor submit count isolates efficiency. Count billing/invoice remains UNVERIFIED.
All 6919 protected hashes match; 13 owned cleanup receipts and exact container absence
verify. No retry/extra sample/resume, Docker start/pull/build or runtime/task change.

Next candidate: design, not execute, one current-failure-feedback diagnostic on the
common failed patch using actual a,a/b,c observations, separating verification initiation
from repair after concrete evidence. Do not expand tools, force notes/plans or adopt B
on these samples. This grant is consumed; remaining funds authorize no further execution.

## Prior report-aware review preparation, not default adoption

`diagnostics/report_verification_review.py` connects the existing public bug report
to a harness-authored working-context entry and completion advice, only in experimental
arm B. Arm A stays report-only. It retains the report's input/fixture/expected output
by reference, distinguishes the original failure from a modified-but-unverified
candidate, and references current-diff probe results for semantic review. An edit,
registered-check PASS, probe exit zero or model note resolution never becomes an
automatic case verdict. Existing notes/questions, native encrypted reasoning and
tool exchanges, action space, budgets and submission eligibility are unchanged.

When registered checks pass but no current-diff probe is recorded in the recent view,
B suggests the optional probe if actually available; finish remains offered. With
probe evidence, B asks the model to compare its actual case and output, not repeat
the probe automatically. Unrelated or inconclusive probes do not prove repair. This
is a salience/lifecycle experiment, not a semantic verifier or forced planning/memory.

The diagnostics-only collector reuses the existing bounded execution/admission/audit
path. Prepare/validate/run support fresh A1/B1/B2/A2 branches at the same A2 pre-turn22
checkpoint, two samples per arm, at most eight new responses and $0.50 per branch/
$2 total proposed cap. Preparation authorizes no paid execution. Prior F1/F2 motivate
the comparison but are not fresh controls. No hidden evaluation, larger model/cap,
default runtime change or further execution under the consumed grant is authorized.

Validation and exact packet receipts are retained under
`C:\pt\validation\report-review-20260914`; the prepared comparison belongs under
`C:\pt\analyses\report-review-20260914`. Provider-free results establish input,
lifecycle and recovery behavior only, not improved agent repair. Runtime/task/user
and historical bytes remain protected. A separate exact-packet approval is needed
before a live comparison, with a fresh price review and already running Docker/images.

Frozen plan SHA-256: `08e28fe788bb5084c43c1133532a0cd64f1dadb009bdf9dad2a7d762a26174e5`.
Final focused/compatibility validation: 123 tests and Ruff PASS in 73.259s. Mock cases
cover optional finish, probe evidence/currency, rollback, pending replay and four-arm
execution; the real checkpoint restores without executing candidate code. Preparation
plus two validations took 1.644s with network/process/credential loading forbidden.
A/B serialized requests are 473,815/474,905 bytes (+1,090, not token counts). Read-only
projection of all eight prior F1/F2 turns preserves native prefixes and leaves both
post-edit cases unverified at submission. This is not evidence of changed agent behavior.
All 6,892 protected hashes match. No provider/count/Docker operation or candidate/private
execution occurred; full runtime suite and isolated-evaluator smoke were not rerun.

## Prior failure-given repair diagnostic completed; approval consumed

The exact `0291bb5e...` executable packet ran once: two independent F1/F2
mini/medium/25k continuations, $0.50 each/$1 total, existing Docker/images only.
Both immediately used the supplied missing-b report for an accepted mutation, ran
the two registered visible checks on their new diff, and submitted after four calls.
Neither ran a probe on the concrete report. An independent post-episode public
audit found F1 FAIL (a, a/b, c) and F2 PASS (a, b, c), not two bug repairs.

F1 changed break to continue without moving the accumulated prefix upward at '..',
so b was created beneath a. F2 popped a component stack at '..', fixing the supplied
str/empty-cwd/Linux case. Both registered checks PASS even for the failing F1;
registered completion is not evidence for this additional reported behavior.
F2's success is local repair evidence, not all-path correctness or hidden acceptance.

All eight requests retain the report, opaque/native history and run_probe availability.
After mutation the report is correctly historical evidence, not a resolved finding.
The old working question still concerns the registered contract; no report-specific
verification concern was created. F1 never updates notes. F2 writes only at finish,
with a non-blocking rejection of nonexistent v1/v2 resolutions; this terminal update
cannot explain an earlier decision. No cap, timeout, incomplete output or tool closure
forced submission. The exact prompt/memory cause remains unseparated.

Evidence: `C:\pt\analyses\failure-given-live-20260914` (`result.json`, `audit.json`,
`public-transcript.json`, `context-notes-audit.json`, `interpretation.json`, `result.md`).
Eight provider/count calls, eight agent actions, two operator case audits; 103.400s;
known model-rate cost $0.352175400. F2's lower cost is cache-dependent, not evidence
of less reasoning. Count billing/invoice remain UNVERIFIED. Six owned container
cleanups and exact absence verify; 6,438 protected hashes match. No retry, resume,
extra sample, operator repair, broader panel, hidden evaluation or default runtime
change. Task acceptance/safety remain NOT_RUN; official=false.

Next: scope one generic report-to-verification context/lifecycle comparison, keeping
the triggering input and current-diff confirmation distinct from registered-check
completion. Do not adopt a hard gate, larger cap/model or claim memory causality from
two samples of one checkpoint. The grant is consumed; remaining funds authorize no
further calls. Execution/validation records are preserved outside the repository.

## Prior failure-given collector preparation (approval consumed above)

The next diagnostic separates autonomous bug discovery from repair after a concrete
public failure report. `diagnostics/failure_given_repair.py` restores the same A2
pre-turn22 checkpoint and adds only `operator_public_feedback` to its latest unsent
current-state snapshot. The chosen `a/../b/../c` observation is bound to the existing
public Linux receipt and identical `43fb9b2b...` patch: real OS creates a, b and c,
while the candidate creates a and c. No source location or replacement hint is supplied.

The 21 encrypted items, 21 native action/result pairs, system prompt, tools, notes,
current visible PASS and budgets remain unchanged. No fake tool result, extra user
message, failed-check gate, repair allowance or mandatory probe is added. After an
edit the report is historical, not evidence that the new candidate still fails.
The serialized request grows by 1,601 bytes (472,214 to 473,815); input tokens are
not counted. Only the selected public case is projected, not the other panel cases.

The frozen input design remains `C:\pt\analyses\failure-given-repair-20260914\ready`,
packet `8a1ea07a...`. The new diagnostics-only
`diagnostics/failure_given_repair_rollout.py` reuses the existing bounded collector,
gateway, dispatch and reconciliation, with one request/context projection hook.
Mock coverage includes mutation/probe/check/finish, rollback, correction restoration,
six crash boundaries, report corruption before pending mutation, terminal idempotency,
non-transferable cost/turn caps and experiment-wide uncertainty stops.

After settled episodes only, a separate operator audit can run the frozen public
case on each distinct final candidate. Identical diffs reuse that audit, not agent
credit. Its receipts are not fed back into finished branches. Execution errors retain
evidence and stop further audits; an uncertain experiment starts no audit. The rubric
separates acknowledgment, admitted repair, agent same-case recheck, operator audit,
current visible checks and finish. Earlier runs are not new randomized controls.

Executable packet: `C:\pt\analyses\failure-given-executable-20260914`, `plan.json`
SHA-256 `0291bb5e23b35a9c3f8b4950bef6a3ab8328b00ed98d182c9a48daa3730597f0`.
It fixes two independent F1/F2 continuations on the same v2 checkpoint:
mini-2026-03-17/medium/25k, root `.env`, probes/repair-recheck retained, <=8 new calls
each, $0.50 each/$1 total, no transfer, retry, experiment resume or extra sample.
Full-output reservation can censor a branch; eight calls are not guaranteed funded.
Official global/default-tier prices were reviewed on 2026-09-13 UTC. The executable
requires an exact packet grant and current UTC price-review assertion; prepared
authorization remains false. Model-rate accounting is not count-endpoint/invoice proof.

111 focused collector/design/documentation tests passed in a 72.032s parallel batch;
final Ruff resolves two line-length findings in the external verification helper only.
Actual checkpoint clone/replay preserves the frozen initial request, inherited
21 model calls/22 actions/two mutations and all 21 encrypted items, without executing
candidate source. Packet preparation/revalidation forbids network/process/credential
loading; 6,418 protected hashes match. Receipts:
`C:\pt\validation\failure-given-rollout-20260914`.
At preparation time, separate approval was pending; the invocation is recorded above.
No provider/count/Docker/pyfakefs-candidate/hidden execution occurred in preparation.
The default v38 runtime and task are unchanged; the full runtime suite and isolated
evaluator smoke were not rerun. Synthetic checks/probes test plumbing, not model repair.
Task acceptance/safety remain NOT_RUN; all evidence remains official=false.

## Prior counterexample-review comparison completed; no adoption

The exact `65020919...` packet ran once in A1/B1/B2/A2 round-robin order using the
approved mini/medium/.env settings, unchanged v38 and $0.50 each/$2 total caps.
All four continuations submitted the unchanged public-PASS checkpoint patch
`43fb9b2b...`. A1, A2 and B2 finished immediately; B1 ran one Windows-mode bytes
parent-traversal probe, saw both directory assertions pass, then finished.

Five provider/count calls, five tool actions, zero new mutations and zero new
registered checks completed in 57.693s. Known model-rate cost: $0.194283150.
The public PASS receipts were inherited on the identical diff, not newly executed
tests. Hidden evaluation/task acceptance/safety remain NOT_RUN; official=false.
The previously demonstrated public counterexamples remain unrepaired because
candidate bytes are identical. This is not four new task successes.

Initial A/B bytes, all encrypted/native history prefixes and the single B suffix
match the approved design. B1's real probe result reached its next request and
was acknowledged in its public finish rationale. There was no cap, deadline,
output saturation or unavailable-probe termination. The narrow Windows/bytes case
was meaningful but did not expose a remaining bug; failure repair was unexercised.
One extra probe in two B samples is not a repeatable improvement in patch quality.
Do not adopt the instruction or infer planning/memory causality from this panel.

Cost is cache-sensitive: first A/B requests had zero cached input; second samples
each reused 102,784 tokens. Model-rate totals are not invoice/count-billing proof.
Code evidence was label-masked, but operator progress already showed arm/count
metadata, so this was not independent fully blinded judging. Terminal-only note
updates also tried nonexistent concern IDs; these were rejected without blocking
finish and cannot explain an earlier choice in these continuations.

Evidence: `C:\pt\analyses\counterexample-review-live-20260913` (`result.json`,
`audit.json`, `blind-observations.json`, `interpretation.json`, `result.md`).
5,571 protected hashes verify; one owned probe-container cleanup is confirmed and
its exact container is absent. No Docker start/pull/build, retry, resume, extra
sample, operator repair or hidden execution occurred. The approval is consumed;
unused budget does not authorize more calls. Next is a separately scoped decision
about discriminating-case selection and completion confidence, not another paid run.

## Prior counterexample-review preparation (approval consumed above)

The approved no-call preparation selects A2 (`run_dev_8d592587618448b7`) immediately
before turn22: both current visible checks PASS, with 19 model/78 tool calls and
two accepted mutations remaining. Its saved native request replays exactly from
the public prefix and matches the original count/dispatch hashes.

Control A keeps that request unchanged. B adds one generic system-prompt suffix:
seek an unestablished patch assumption, derive a potentially refuting public input,
probe it, and respond to the observation. No concrete operator counterexamples,
new source, forced tool choice, required plan/note, or reasoning reset is added.
All 21 encrypted items, 21 native call/result pairs, task, memory and tools stay equal.
The existing prompt already suggests probing concrete uncertainty; this tests a
more explicit proactive review instruction, not newly available tools.

Design: two new samples per arm, A1/B1/B2/A2 round-robin, up to eight new calls each,
mini-2026-03-17/medium/25k, append-v1, probes/repair-recheck retained. Planning caps
are $0.50 each/$2 total, no transfer; caps can censor an episode and do not guarantee
32 funded calls. No paid authorization is included. Prompt-prefix cache effects and
behavior are scored separately; one selected checkpoint cannot establish generality.

The diagnostics-only collector now reuses native request construction, the existing
bounded dispatcher, gateway and reconciliation. It restores the two inherited
accepted mutations and the automatic repair-recheck events, counts new automatic
checks as tools, and returns their feedback through the native runtime path.
Both initial requests match the frozen bytes. Subsequent B requests retain the
suffix once; B can still mutate or finish without a probe. Memory, encrypted
continuation, ordinary tool policy and default runtime are unchanged.

Each branch has its own $0.50 ledger, full-25k admission and eight-response bound.
Cost/turn censoring leaves other branches available, with no budget transfer.
Count/provider/billing uncertainty or unconfirmed sandbox cleanup stops the whole
experiment. Pending durable actions reconcile before a new dispatch; no uncertain
provider/check/probe is retried. Public terminal receipts use the last recorded
diff, not a new Git operation after deadline or a claim about an uncertain worktree.
The executable command requires the exact packet hash and a fresh exclusive result
root. It has no experiment resume or automatic retry.

Immutable design: `C:\pt\analyses\counterexample-review-20260913`. New executable
packet: `C:\pt\analyses\counterexample-review-executable-20260913`, `plan.json` hash
`6502091980b8b38dc6c47e730c6418c51e95a953cec4c793e3b6e16b6434e367`.
85 focused tests passed in 93.071s, including mock lifecycle and real-prefix no-call
restoration; 5,556 protected file hashes match. Receipts: `validation.json`,
`final-validation.json`, `result.md`. The follow-up Ruff receipt resolves a single
line-length error in the external audit helper, with collector/runtime bytes unchanged.
At preparation time, paid approval and actual execution were pending; the completed
invocation is recorded above. This historical preparation did not itself execute
provider/count/Docker/candidate/hidden work and remains official=false.
The full runtime suite and isolated-evaluator smoke were not rerun for this
diagnostics-only change; synthetic gateway rollouts cover probe/mutation/check/finish.

## Prior public counterexamples reproduced; no runtime change

The approved provider-free diagnostic fixed 14 public-spec-derived POSIX cases
before execution and compared actual Linux os.makedirs with BASE/A1/B1/B2/A2.
The five existing-public-sandbox executions completed in 21.313s, with identical
real/fake initial fixtures and identical real-OS oracle results across subjects.
The pinned public Python image reports Linux/Python 3.12.13, umask 0o022.
No provider, hidden evaluator, Windows/macOS, new agent run or patch repair ran.

Actual-OS agreement: BASE 1/14, A1 11/14, B1 11/14, B2 8/14, A2 7/14. These are
selected post-hoc diagnostic cases, not hidden scores or a new A/B success ranking.
A2's predicted `a/../b/../c` omission is now reproduced: real OS leaves a, b and c;
A2 leaves only a and c. The same bytes-path case agrees, consistent with a string-only
`component == ".."` early break. B2 mishandles existing destinations and the modes
of directories created before an error, as well as link traversal.

Even B1, which passed the prior isolated evaluation, differs on three cases:
`file/../leaf` creates leaf instead of raising ENOTDIR; link-plus-parent traversal
creates the destination in the wrong directory. This supplements, not rewrites,
the prior EVALUATOR_PASS: finite check success is not all-input correctness.
All four candidates differ on the two valid-directory-link traversal cases.
The remaining demonstrated issue is incomplete preservation of path semantics;
planning/memory/context-policy causality and benefit from requiring probes are
still unproven. These operator cases must not be described as agent-authored checks
or automatically injected into the default prompt/task as repair hints.

Evidence: `C:\pt\analyses\public-counterexamples-20260913` (`packet.json`,
`results.json`, `result.md` and per-subject sandbox receipts). Packet `06cd6fb9...`;
5,514 historical/task/user/analysis file hashes verify. Five owned container cleanups
are confirmed and absent. The owned 128-file temporary clone was recycled with
hash-verified recovery receipt. Six diagnostic utility tests pass in 0.08s; final
docs/Ruff and cleanup receipts are bound by completion.json. No runtime/default change or
full-suite/mock rerun; all diagnostic task_acceptance flags are NOT_RUN and official=false.
Next decision: one generic behavior experiment for public-requirement combination
checks, without treating this task's counterexamples as cross-task solution hints.

## Prior native context A/B completed; four-row approval consumed

The exact `8f016079...` packet ran once in A1/B1/B2/A2 order, append/window/window/
append. All four were fresh pyfakefs v2/mini-2026-03-17/medium/root `.env` repeat1
runs on unchanged v38, probes/repair-recheck ON, $1.20 each/$4.80 total, no transfer.
API compact was disabled in both arms; encrypted continuation was retained. All
96 generation ceilings stayed 25k; 40/100/4/1,800 limits and defaults are unchanged.

| Row | Context | Terminal | Task acceptance | Model/tool calls | Known cost USD |
|---|---|---|---|---|---:|
| A1 | append | AGENT_STOPPED | NOT_RUN | 26/28 | 0.556358850 |
| B1 | window | EVALUATOR_PASS | PASS | 21/28 | 0.380706000 |
| B2 | window | EVALUATOR_FAIL | FAIL | 27/38 | 0.541517400 |
| A2 | append | EVALUATOR_FAIL | FAIL | 22/23 | 0.369103950 |

Total known model-rate cost **$1.847686200**; invoice/count billing remains
independently unverified. Three submissions have both current visible checks PASS
and safety PASS. A1 has no submission/evaluation: NOT_RUN is not a hidden-test FAIL.
All results remain `official=false`/`claim_eligible=false`. There were 96 input counts,
117 tools, nine automatic repair-rechecks and 1,000.949 active seconds; no probe call.

B has 2/2 submissions and 1/2 acceptance PASS versus A's 1/2 submissions and 0/2 PASS.
With only two rows per arm this is a descriptive signal, not adoption evidence.
Both arms used 48 model calls. B used 25.90% fewer input tokens, but only 0.35% less
known cost because its cached-input share was lower (59.10% vs 73.60%). B also used
more inspections (41 vs 33). Different trajectories and the window system notice/
archive representation prevent a pure deletion-only causal interpretation.

The public-code distinction is solution completeness, not demonstrated evidence
loss: B1 handles all raw prefixes using existing mkdir behavior; A2 stops prefix
creation at the first `..`; B2 delegates only non-`..` paths back to the original
implementation while leaving manual entry handling in its traversal branch. A1
stops after remaining public regression failures and repeated 52/50 scope rejections.
Private failure details were not inspected, so these public observations are not an
exact attribution of hidden failures. No additional candidate checks were executed.

All 96 saved inputs replay exactly from their then-available journal prefixes;
count/dispatch hashes, native ordering and submission/current-PASS diff binding
verify. A1/B1/B2 never proposed notes. A2 made six memory updates, one finding was
created/updated and delivered on 17 turns; an invalid citation was rejected without
blocking its action. This is real note use, not proof of a correct plan or solution.
Two read-only audits agree (3.717s each), 5,483 protected files verify, and 19 public
check container cleanups are confirmed. No retry/resume/extra sample, Docker start/
pull/build, task/runtime/default edit, or private feedback occurred.

Evidence: `C:\pt\analyses\native-window-comparison-live-20260913` (`result.md`,
`analysis.json`, approval/observer/result and final validation receipt). The original
preparation packet and its 31-case/12.474s receipt are immutable. New operator stop
tests pass (10/0.81s); docs/Ruff verification is recorded in `completion.json`.
Full runtime tests/mock were not rerun because runtime bytes are unchanged.
Next: a separate decision on provider-free public-spec edge-case validation before
choosing one loop change. Do not automatically adopt window, force notes or add
paid samples; this experiment does not isolate a single remaining cause.

## Prior native-window pilot succeeds; compact not exercised

The exact `30bec892...` packet approval was consumed once. Fresh run
`run_dev_ebfe33596eed4353` reaches **EVALUATOR_PASS**, task acceptance **PASS** and
safety **PASS**, with `official=false`/`claim_eligible=false`. It uses pyfakefs v2,
mini-2026-03-17/medium, native-window-v1, probes/repair-recheck, root `.env`, repeat 1,
T=60000 and the approved shared $2 conditional planning budget.

There were 19 generation/count calls, 20 tool actions, two accepted mutations and
121.047 active seconds. Known model-rate cost is **$0.19483845**; count billing and
the invoice total remain separately unverified. All generation ceilings stayed 25k.
Peak counted input was **45,507 tokens**, below 60k, so compact is **NOT_EXERCISED**,
not a successful compact/activation/recount test. No forced call or extra sample followed.

After 14 inspections, turn15 implements raw-path recursive creation. Turn16's public
check identifies intermediate-directory mode; turn17 separates parent default mode
from the requested leaf mode, and the automatic child recheck passes. Turn18 passes
upstream regression (517 passed/570 skipped), then turn19 finishes. The +23/-1 patch,
both current visible PASS records and submission share `ab096b01...`. Private evidence
is read only as aggregate verdicts, never as agent feedback.

All 19 prepared/count/dispatch inputs reconstruct exactly from their available journal
prefixes; current task/diff, public evidence and once-only native pairs remain bound.
The final input retains 735 source-version line facts, 36 public exchange versions,
15 observation versions and 18 prior reasoning items. All memory updates are null;
this run does not demonstrate model-authored working-note use. Two read-only audits
agree (1.120s/1.019s); 81 artifacts and 5,061 protected files verify. Three public check
container cleanups are confirmed and those exact containers are absent.

Evidence: `C:\pt\analyses\native-compaction-pilot-live-20260913` (`result.md`,
`analysis.json`, immutable approval/observer/result). The design packet remains unchanged.
No runtime/task/default change, retry, resume, answer seeding, Docker start/pull/build
or additional paid request occurred. This one successful trajectory is not a matched
A/B result or proof of a causal quality/cost improvement. Native compact and long-window
failure prevention remain untested live; any next experiment needs a separate decision.
Three documentation tests and Ruff pass after recording the result. Full runtime
tests/mock were not rerun for these documentation-only changes; their dated receipt follows.

## Verified runtime: v38 opt-in native compaction runner

Phase 3 connects the durable compact adapter to the existing agent loop, without
changing default `append-v1` or enabling compact via `native-window-v1` alone.
New mini-snapshot runs must additionally set a positive counted-input threshold
and explicitly acknowledge the conditional model-limit reservation. No threshold
is selected by default; no paid packet or execution is authorized by implementation.

The runner freezes each candidate input before counting. Only a healthy completed
tool batch can compact, with one spare model call beyond minimum completion, a
full shared-cost reservation and the existing active deadline. The entire returned
window becomes an immutable seed; missing exact public evidence reenters once as
quoted history. Latest state explicitly repeats the public task and alone supplies
current notes/checks/budgets/tools. A fresh post-compact request is counted again.

Durable count/input pairs, seed activation and consumed-exchange cursors recover
without repeating generation or mutation. Compact usage counts against the same
invocation cap, its dispatch against the 40-model budget, and elapsed time against
1,800 active seconds; downtime is excluded. Interrupted/unknown calls never retry.
Tool argument schema/order, 100 tools, four accepted mutations and 25k generation
ceiling remain unchanged. Tool-surface identity is v38; old runs are not migrated.

Provider-free checks: 44 new cases PASS/52.149s; 109 compatibility cases PASS/18.694s;
Ruff PASS. All 91 test files yield 1,803 PASS/four real-Docker opt-in skips. Longest
full worker is 384.729s: focused checks meet two minutes, the full suite does not.
Mock `run_dev_05c974e7447c4506` reaches mutation/check/finish/isolated acceptance PASS
in 4.468s, four model/five tool actions, safety NOT_RUN and cost zero. Compact itself
is exercised by injected-provider runner tests, not by the ordinary mock adapter.
Runtime: `sha256:a6595319b770bc91e733e138273ee22de698a9fd707ce5543cfe06d0dd67d765`.
Evidence: `C:\pt\validation\native-compact-runner-final-20260913`. A fresh system
notice after compact supersedes the retained no-compaction/task-inheritance text;
the original seed remains unchanged. No real provider/count/
compact, Docker operation or task-package modification occurred. Next is a separate
exact opt-in experimental packet (now prepared above), not default adoption or a
model-quality claim.

## Prior layer: durable compact adapter, before runner integration

Phase 2 of the [implementation plan](../.agent/plans/native-context-window.md) adds
a run-scoped compaction handoff. It reuses shared response validation, bounded
transport and the previously reviewed conditional cost reservation. Preparation
binds input/seed/policy/runtime and remaining invocation budget; dispatch requires
an explicitly supplied client. No CLI or runner path calls this adapter yet.

The complete validated output stays in CAS, in provider order. Retained public
messages/actions must match observed input; opaque state is never decoded. Usage is
durable before output validation. Recovery verifies source, output and receipt;
started/usage-only crashes never authorize retry. The caller's deadline also bounds
request and owned-client cleanup. Unknown cleanup or billing prevents activation.
An atomic receipt does not itself activate a window or settle the runner's ledger.

Provider-free checks: 60 adapter cases PASS/9.586s and 100 existing compact/transport
cases PASS/30.395s. All 90 test files yield 1,759 PASS/four real-Docker opt-in skips;
longest full worker 362.932s (focused meets two minutes, full does not). Ruff passes.
Mock `run_dev_702e01bb86114453` reaches mutation/check/finish/isolated acceptance PASS
in 4.628s, four model/five tool actions, zero cost; safety NOT_RUN. The saved real
compact response's 23 items/22 public messages pass the shared validator read-only.
Evidence: `C:\pt\validation\native-compact-adapter-20260913`.
Runtime: `sha256:15b7fb6ce5168931cd82865deb1bc8adce519c441963408522754437abd3ad9b`.
All 4,571 prior protected files and 112 phase-1 evidence files are unchanged.
Default input behavior and v37 surface are unchanged. No real provider/count/compact,
credential loading, Docker execution or task-package modification occurred.

At that layer, runner integration and CLI admission remained unimplemented; the
new section above supersedes that next seam. Its historical receipt is unchanged.

## Prior layer: v37 opt-in native snapshot window; no compaction

The first layer of the [implementation plan](../.agent/plans/native-context-window.md)
is implemented. Default `append-v1` preserves its input wire and append-only contract.
New runs can select `--context-policy native-window-v1`: only superseded post-seed
harness state descriptions expire. Unique public source/receipt observations remain
as exact historical evidence; native reasoning/call/output items and their order are
unchanged. The latest complete state alone supplies budgets, current checks, notes
and corrections. Current references resolve in the visible window, never only in CAS.

The policy is bound into the request, model hash, envelope and saved turn metadata.
Resume verifies the immutable seed, parent input, native sequence and public evidence
before pending tools or another inference. Old runs are not migrated. Tool schemas,
action masks, output ceilings, cost admission and 40/100/4/1,800 limits are unchanged.

Read-only replay passes for all 65 saved A1/B1/B2 inputs in 14.258s. At the last normal
input, compact-JSON **input-array** bytes fall 33.67% / 36.77% / 31.69%, including
rescued evidence and new policy instructions. These are not full HTTP request bytes,
token savings or model-quality results. The 1,701,176-character encrypted item remains
exact; this change does not repair or retest the earlier per-field rejection.
4,571 prior protected user/task/history/external files match their earlier receipt.
Evidence: `C:\pt\validation\native-window-20260913`.

Provider-free validation: 138 focused tests PASS in 61.77s; Ruff PASS; all 89 test
files selected once yield 1,699 PASS / four real-Docker opt-in skips. Longest full
worker is 382.43s, so the full cycle exceeds two minutes. Opt-in CLI mock
`run_dev_91de969f3e434039` reaches mutation/check/finish/isolated acceptance PASS in
4.73s, with four mock turns, five tools and one mutation; safety NOT_RUN, cost zero.
All four saved window inputs revalidate, and the 65-input replay/protected-file check
still matches after the suite. No real provider/count/compaction or Docker execution.
That layer's next candidate was the durable compact adapter (now implemented above).
Runner scheduling, threshold T, a paid packet and default adoption remain separate;
the new flag alone does not call compaction or reset reasoning.

## Prior audit: native-input growth and the rejection are separate

Read-only reconstruction of all 65 inputs in A1/B1/B2 validates 65 original count
admissions and 64 generation hashes. Native state accumulation is real: removing
superseded views in an in-memory sizing probe would reduce the last counted requests
by 33.70% / 37.53% / 31.47% respectively. These are byte-reduction upper bounds,
not token savings or deployable requests; historical receipt rescue is not included.
Source facts, current selection/state and native encrypted/call/output items stay exact.
Old view observation versions still need reconciliation before any removal contract.

B2 turn20 -> turn21 grows 1,716,122 JSON bytes; 1,701,293 (99.14%) is one new reasoning
item. Its encrypted field has 1,701,176 characters, once only, matching the earlier
count endpoint's string_above_max_length evidence. State removal leaves this field
unchanged. No new count/generation was sent; exact server field limit and generation
endpoint behavior remain unknown. B1 also completed with 101,831 input tokens, above
B2's pre-failure 97,810: no token-only saturation/compaction threshold is established.

Two guarded audits agree in 3.855761s; ten accounting/evidence fixtures plus three
docs checks PASS/0.784s; Ruff PASS. 4,649 protected files and native runtime unchanged.
No credentials, API/count/compaction, Docker/task/hidden evaluation, or runnable modified
input. Evidence: `C:\pt\analyses\native-input-audit-20260913`. Acceptance/safety NOT_RUN,
official=false. Source reconstruction files match source commit 22798e34...; the full
historical runtime envelope remains non-resumable under the current exact contract.

Next candidate is an explicit native context-window lifecycle design, reusing the
normal-checkpoint compaction and validated full-window/public-state continuation path.
Do not blindly prune current append-only native history or promise this prevents a
future oversized reasoning item. No new implementation, model/tool-policy change,
default adoption or paid grant follows from this analysis.

## Prior live: latest-state diagnostic reached public submission; grant consumed

The exact `0d45099f...` approval (packet `429d4173...`) was consumed once on
2026-09-13 KST. Collector `run_dev_compactcollectloop_ef29a44a32a64717`, child
`run_dev_compactepisode_999605443f744e56`, ended `PUBLIC_CHECKS_SUBMITTED` in
101.420s: eight new generations/counts, eleven tools including seed/rechecks, two
accepted repairs. Generation cost $0.53881155 under $1.20; separately unconfirmed
count billing is not a guaranteed invoice cap. This is the isolated healthy pre-turn20
diagnostic with latest-state-v1, mini/medium/25k, inherited probes/repair-recheck,
not a native live row/resume, new compaction or default-loop adoption.

Probes exposed bytes components versus str traversal constants. The first repair
incorrectly expected make_string_path on a string literal to match the path type;
automatic recheck returned the same failure. A helper read then matching_string(path,
token) repair passed the contract recheck; upstream regression passed (517/570
skipped) and finish succeeded. Both PASS checks/submission bind `a54bfbd1...`, one
file/+33/-0/no untracked. Six public container cleanups confirmed; client CLOSED.

Actual input tokens: 107,319 -> 111,303 -> 115,395 -> 120,527 -> 123,219 -> 129,082
-> 135,028 -> 138,566. Final complete request 566,920 UTF-8 bytes versus 1,381,335
in a read-only same-action append reconstruction (-59.0% bytes, not counted tokens).
All seed/native encrypted history, current state and cumulative public evidence
remain exact: 1,279 source facts, 28 exchange versions, 33 observation versions.
Nineteen historical observation versions rescued; all new memory_update values null.
Two result inspections agree (0.167361s); two projection replays/inventory checks
0.492546s. All 4,218 protected files and 234 completed collection files match.

The historical append episode also submitted, using five responses/one repair and
$0.50483145. Actions/cache hits differ: smaller input growth is demonstrated here,
not faster solving, lower total cost or better model quality. Default runtime/v36
unchanged; no automatic retry, extra sample, Docker start/pull/build or hidden
evaluation. Acceptance/safety NOT_RUN, official=false. Evidence:
`C:\pt\analyses\compaction-snapshot-live-20260913`; collection:
`C:\pt\analyses\compaction-snapshot-collection-20260913`.
Next: interpret this bounded result before any adoption or separately approved paid
comparison; do not infer a new memory/planning requirement or reuse the grant.

## Implemented: opt-in diagnostic snapshot lifecycle; default unchanged

`diagnostics.compaction_episode prepare --context-policy latest-state-v1` now binds
one diagnostic-only change in the packet/collector: replace superseded post-seed
state messages, retaining unique public evidence separately as quoted history.
The default remains `append-v1`; the native agent, v36 tools, notes/policy, limits
and task are unchanged. The entire seed (including standalone compact output),
native encrypted/call/result sequence and latest complete reentry stay exact.

Source is rescued as complete LF lines with original raw-file hashes and gaps;
public exchange versions and harness-only check/probe receipts are retained exactly.
Historical PASS/currency flags cannot replace the latest check table. Old corrections
and expired note interpretations are not reintroduced as current instructions/memory.
The projection precedes input counting/artifact recording; those artifacts deterministically
reconstruct it. Pending/terminal diagnostic work still cannot be retried or resumed.

Two provider-free replays of the five saved requests agree in 0.653178s. Final complete
request: 948,877 -> 517,178 serialized UTF-8 bytes (-45.5%), preserving 942 source
facts, 22 public exchange versions and latest state/notes/checks. Seven unique past
observation versions were separately rescued; this is deliberately less aggressive
than the earlier size-only probe. This does not measure tokens, API acceptance or behavior.
Final preservation: 4,182 files match, excluding the two edited diagnostic modules
and the collector regression test added after the initial 4,183-file replay receipt;
runtime hash is unchanged. Receipts: `C:\pt\validation\compactstate-20260913`.

Validation: 17 focused tests PASS/21.589s, 89 related regressions PASS/123.997s,
then collector-mode binding plus three documentation checks PASS/6.424s; Ruff passes.
The broad regression run slightly exceeded two minutes. These are 110 test executions
(107 distinct tests), including mock/local repair -> recheck -> public finish and
crash/no-retry coverage, not a new native full-suite or isolated hidden-evaluator run.

The execution packet was subsequently approved and consumed as described above.
Old packets/journals remain immutable; changed diagnostic hashes prevent reusing old
execution contracts, while completed results remain read-only inspectable. Implementation
validation itself made no provider, input-count, Docker or hidden-evaluator calls. Acceptance/safety NOT_RUN,
official=false; this is not a default-loop adoption or new model-quality result.

## Prior audit: repeated-state growth isolated

Read-only analysis of the five completed compacted requests attributes 439,219 of
519,521 added wire bytes (84.5%) to superseded post-seed state messages. Reasoning
items added 47,564 bytes (9.2%); new native calls/results added 26,755 (5.1%). These
are serialized UTF-8 byte shares, not token shares or model-effect measurements.
Every new quoted call/result item (12/14/14/12/14) was already present earlier in
that input. Reentry both expands selected source and quotes dependency-linked old
results, then the episode appends that one-shot restoration bundle on every turn.

An in-memory size probe retained the entire seed and every native item plus latest
state, omitting only superseded post-seed reentries: last request 948,877 -> 509,654
bytes (-46.3%). This trace retained 942 source facts and 22 public action versions;
no runnable request, count call or behavioral equivalence claim was produced.
This identifies a snapshot/history lifecycle issue in the diagnostic wrapper, not
the same measured growth in the default native loop or a compaction quality cause.

That audit motivated the opt-in implementation above, not adoption of its size probe.
Do not reset reasoning, change tool masks or infer a paid grant from the audit.
Two guarded audits agree in 0.662391s; seven independent synthetic checks pass.
All 4,169 protected files/runtime match. Evidence:
`C:\pt\analyses\compaction-reentry-audit-20260913`; API/count/tool/Docker/hidden calls 0.

## Prior live evidence: approved compacted short loop reached public submission

The exact `1f4b1ff0...` grant was consumed once on 2026-09-13 KST by
`run_dev_compactcollectloop_770d791800604acd`; child
`run_dev_compactepisode_a24b09c546ff4deb` ended `PUBLIC_CHECKS_SUBMITTED`.
This is a short diagnostic continuation of the healthy pre-turn20 checkpoint,
not a new native live row or native resume. Mini/medium/25k, native v36 policy,
probes and the original repair-recheck option were unchanged.

The previously collected seed check ran once without regeneration and failed on a
bytes parent-traversal path with FileExistsError. Two source inspections preceded
one accepted replacement excluding the final significant component from precreation.
The opt-in harness recheck passed, then the model requested upstream regression
(517 passed, 570 skipped) and finish. Both PASS checks and the submitted artifact
bind `43894e2c...`: one file, 33 additions/0 deletions, no untracked files.

Five new generations/counts, seven tool actions including seed/recheck, one accepted
mutation, 91.483s. Known generation cost $0.50483145 under the shared $1.20 cap;
count billing remains separately unconfirmed and invoice total unknown. All five
requests preserved the compacted prefix and appended prior encrypted continuation/
matching call outputs once. All new memory updates were null. Client cleanup CLOSED;
three public Docker checks record confirmed owned-container cleanup. No start/pull/
build, hidden evaluator, recompaction, automatic retry or paid resume occurred.

Do not infer a compaction causal effect or generalized mini/native-loop success from
one branch with no fresh control. Input grew 107,343 -> 231,983 tokens; each turn
appended another 93,518-106,658-character public reentry while retaining prior ones.
The last input retained five earlier reentries totaling 497,060 characters. The
read-only analysis above now separates those repeated state/source-exchange bodies;
neither discard observed evidence nor launch another paid sample from this result.
Task acceptance/safety remain NOT_RUN, official=false.

Two post-run read-only result inspections agree in 0.183008s; all 221 collection files
and 3,937 protected predecessor files/runtime match. Original proposal/packet/run/.env
and user-owned files remain unchanged. Collection:
`C:\pt\analyses\compaction-episode-collection-20260913`; authorization and analysis:
`C:\pt\analyses\compaction-episode-live-20260913`.
The earlier collector validation remains 104 cases/119.415s plus Ruff at
`C:\pt\validation\compactcollect-20260913`; it is distinct from this live evidence.
No new full native suite or hidden evaluator smoke is implied by the documentation update.

## Prior implementation: short compacted-loop mechanics prepared; no new live execution

`diagnostics.compaction_episode` prepares and verifies a diagnostic continuation of
the already-collected check proposal below. The native runtime and tool-surface v36
are unchanged. It restores the healthy pre-turn20 checkpoint in a new isolated
workspace, reuses the seed decision once, then joins real tool feedback, encrypted
reasoning and current public state for subsequent bounded decisions. It does not
resample the seed, prune the full compacted window, reset reasoning or run hidden
evaluation. The original opt-in repair recheck is retained.

The native history restorer does not accept compacted windows. The diagnostic keeps
the exact compacted wire prefix separate from a local observed-source reconstruction
index. Only the full saved prefix plus new exchanges and public reentry are sent;
the old native encrypted history is not reintroduced as model input. No unobserved
source or private evaluator evidence is added.

29 provider-free cases pass in 54.005s: seed/check/finish, failed-check repair and
recheck, parallel results and notes, correction continuity, integrity/cost/deadline
failures, and crash points without duplicate calls/actions. Sandbox time expiry keeps
`LIMIT_REACHED`; cleanup uncertainty retains the native abort instead of becoming a
generic error. These are mocked/local fixture results, not pyfakefs behavior results.

Packet `65e1ce83...` at `C:\pt\analyses\compaction-episode-design-20260912` is
`PREPARED_NOT_EXECUTABLE`, with an eight-new-response observation bound, not a new
action mask. Global 40/100/4/1800 and 25k output limits remain unchanged. Two no-call
verifications match (0.448505s); real checkpoint hydration matches diff, checks and
19 model /20 tool /2 mutation counters (3.989775s). The already-paid seed consumes
one further inherited model call and 7.517505s, not a new generation charge. Its actual
check is still unexecuted. All 3,897 protected files and native runtime are unchanged.
Evidence: `C:\pt\validation\compactloop-20260912`.

Related regression adds 188 passing cases in 51.188s; final focused+regression total
is 217 cases /105.193s, excluding earlier debugging runs. Ruff passes. No native full
suite or isolated evaluator rerun was needed for these diagnostic-only changes.

Only preparation/verification CLI and injected step mechanics exist. Next implement
the bounded live collector: exact new grant/cap, current prices, count-billing
disclosure, lifetime lock, client cleanup, partial receipts and existing-image
preflight. No paid grant is carried over. API/credential/Docker/hidden-evaluator work
is zero in this stage; acceptance/safety NOT_RUN, official=false.

## Prior diagnostic: compacted input accepted; appropriate check proposal, not executed

The separately approved `aa469bad...` follow-up completed with exactly one input count
and one generation: `run_dev_compactnext_822a9ab18f5f4ce3`, same mini/medium/.env/repeat1,
25k output limit and unchanged frozen request. Both endpoints report 78,485 input
tokens; output is 117, including 44 reasoning tokens. The response is completed and
proposes `run_check(parent-traversal-contract)`. The current public state agrees:
upstream regression PASS, that contract NOT_RUN, gate `needs_visible_checks`.

The original turn20 used 97,810 input and exhausted 25k output entirely on reasoning
without a tool call. This sample uses 19.76% fewer input tokens and returns a relevant
action; the new encrypted reasoning item is 1,484 characters. This is positive evidence
for compaction plus exact public reentry, not isolated causality or repeatability.
All 22 original messages remain; the historical control was not rerun. The original
oversized turn21 item was not compacted, and opaque semantic fidelity is unproven.

Generation model-rate accounting is $0.05939025 (cached input zero), within the actual
full-output reservation $0.17136375 and approved generation cap $1.20. Count billing is
UNCONFIRMED outside that cap; total invoice is unknown. Journal duration 7.517505s,
cleanup CLOSED. `RESPONSE_COLLECTED` and `PASS_SHAPE_ONLY` do not establish full argument
validation, source/scope admission, actual check results or task success. Tools,
Docker, hidden evaluation, correction, recompaction and retries were all zero.
The exact grant is consumed; no automatic continuation or default loop change.

Two no-call inspections matched the frozen plan in 0.142799s before dispatch, and two
read-only result checks preserved collection bytes. All 3,879 protected files and
native runtime remain unchanged. Evidence:
`C:\pt\analyses\compaction-followup-live-20260912\result.md` and `analysis.json`;
collection: `C:\pt\analyses\compaction-followup-collection-20260912`.
The frozen proposal and older receipts retain their original preparation-time values.

The preceding implementation passed 188 focused cases in 40.79s and Ruff under
`C:\pt\validation\compactnext-20260912`; that was provider-free preparation, not this
live execution. Next seam is to review a bounded actual-loop validation, not infer
task acceptance from a proposal or dispatch another paid request. All results remain
official=false, acceptance/safety NOT_RUN. No native full suite or mock task rerun.

## Prior diagnostic: one standalone compaction completed; follow-up behavior untested

The separately approved one-request diagnostic completed as `COMPACTION_COMPLETE`:
`run_dev_compactcollect_5d1017bb7cf54445`, B2's healthy pre-turn20 public input,
`gpt-5.4-mini-2026-03-17`, standard tier. Usage is 93,107 input / 1,069 output tokens;
model-rate accounting is $0.07464075, not an invoice-verified charge. Journal duration
is 9.927731s and client cleanup CLOSED. Count/generation/tool/Docker/hidden evaluation
and retries are all zero. The exact one-compaction grant is consumed.

Encrypted history decreased from 133,464 to 7,308 characters (94.52%). The complete
returned window is 181,806 canonical bytes; after exact public reentry and unchanged
generation settings, the prepared request is 315,757 bytes versus 448,333 (29.57% less).
These are serialized sizes, not input token counts. All 22 original messages remain
content-equivalent, including 20 developer messages: accumulated state descriptions
were not removed. Reentry restores the public task, diff, 319 selected source lines
and six referenced public action pairs; the returned window is not pruned.

Two evidence-only recoveries are byte-idempotent. Source/code/CAS/journal checks pass;
3,838 protected files and native runtime are unchanged. The original oversized
1,701,176-character turn20 output was not an input to this healthy-cutoff diagnostic.
This does not establish repaired turn21 input, next-endpoint admission, valid model
actions, semantic preservation inside the opaque item or task success. Next seam is a
separately scoped count/generation diagnostic of the frozen next request, not default
loop adoption or an automatic extra call. Acceptance/safety NOT_RUN, official=false.

Evidence: `C:\pt\analyses\compaction-live-20260912\result.md` and `analysis.json`;
collection: `C:\pt\analyses\compaction-collection-20260912`. Original packet/proposal
remain immutable; the new authorization and result record this later approval.

## Prior implementation: one-compaction collector; provider-free validation

`diagnostics.compaction_collector` adds provider-free `inspect`, a separately
approved one-request `collect`, and evidence-only `recover`. It consumes the unchanged
B2 pre-turn20 packet; native runtime, schemas and existing run bytes are unchanged.
No token count, generation, tool, Docker or hidden-evaluator call follows compaction.
The input/output handoff below is reused without changing the frozen design.

The official Responses pricing rule supports model-rate accounting: mini input
$0.75/M, cached input $0.075/M and output $4.50/M. The collector conservatively
reserves 400k input plus 128k output tokens ($0.876), with no expected cache saving.
This applies published model limits as an explicit planning assumption, not a
documented compact-endpoint output guarantee or server-enforced dollar cap. Exact
execution-plan approval and `--accept-model-limit-reservation` are required; a strict
endpoint-enforced cap remains unavailable. The proposed $1.20 plan is not a live grant.

Admission checks the source, model/tier, credential path, repeat=1, destination,
full reservation and exact plan hash before loading credentials. One durable dispatch
intent, zero SDK retries and a 300s request/305s execution budget (5s cleanup reserve)
bound execution. Usage is saved before output processing; malformed output or a crash
cannot turn observed usage into free work. Price-table accounting and verified invoice
charges remain distinct. Uncertain outcomes, exceeded assumptions or cleanup failures
stop, with no retry or paid resume. Recovery only reconstructs recorded evidence.

Verification: 163 focused collector/compaction/transport/count/source/docs tests PASS
in 30.05s; Ruff PASS. Two identical real-input inspections took 0.094s, with zero
credential loads or API calls. Execution proposal `03b157e1...` is stored under
`C:\pt\analyses\compaction-execution-design-20260912`; it proposes $1.20 for one compact
request and is explicitly unapproved. Native runtime and 3,821 protected files remain
unchanged, including the old packet. Receipts: `C:\pt\validation\compactcollector-20260912`.
No actual count/compact/generation/Docker/task execution; no new full native suite or
task mock smoke. Model-limit applicability and actual compaction behavior remain
unverified live; do not turn mock success into a hard billing or task-success claim.

## Prior implementation: diagnostic compaction handoff, provider-free only

`diagnostics.compaction_replay` now freezes the original healthy B2 pre-turn20
input for the standalone compact endpoint. It does not feed back the oversized
turn20 response, reset encrypted reasoning, or change the default agent/runtime.
The complete returned compacted window is preserved as-is. A following exact public
state message restores the task goal, current diff, selected source bodies, budgets
and referenced public check/mutation evidence from existing observations only.

`diagnostics.compaction_state` reserves one attempt and stores validated output in
external CAS with a durable receipt and hash-chained journal. Recovery reconstructs
identical count/generation requests without calling a provider; missing outcomes stop
UNKNOWN, not retry. Plaintext reasoning, incomplete action pairs and corrupted
artifacts are rejected. Usage survives an invalid output; charges remain unknown.
The diagnostic transport supports compact with the existing bounded async wait and
zero SDK retries. There is no live compaction collector or automatic next request.

The official standalone compact schema has no output-token or reasoning-effort
parameter. The unchanged medium/25k settings apply to the *next generation*, not to
the compaction pass. Resolve its cost-admission contract and obtain exact separate
approval before live collection; the earlier count grant is consumed. A smaller
opaque item is an experimental outcome, not a guarantee or task-success claim.
All results remain official=false, task acceptance/safety NOT_RUN.

Validation: 133 focused compaction/transport/count/source/docs tests PASS in 23.69s;
Ruff PASS. The real packet `C:\pt\analyses\compaction-design-20260912` (`504756b2...`)
passes two identical no-call verifications in a 0.264s preparation/verification cycle.
Reentry preserves 319 selected source lines and six referenced public action pairs;
its 106,578 canonical bytes are not a measured compacted-window size or token count.
All 3,797 protected files, native runtime and the old count packet remain unchanged.
Receipts: `C:\pt\validation\compaction-20260912`. No credentials, count, compaction,
generation, Docker or task execution occurred. Full native suite and task mock smoke
were not rerun for this diagnostic-only change; SDK transport tests use mock responses.

## Prior diagnostic: count-only replay observed an encrypted-field length rejection

The separately approved two-count diagnostic is complete. Control turn20 returns the
same 97,810 tokens; unchanged turn21 returns HTTP 400 `string_above_max_length` at
`input[79].encrypted_content`. This is a new rejection of the original frozen input,
not a recovered copy of the original error. No retry, resume, generation, Docker or
task execution followed. Collector time: 2.811447s; client cleanup CLOSED.

The rejected field has 1,701,176 characters, exactly matching the durable continuation
stored after the original turn20 response. It appears once in the request; previous
input is an unchanged prefix. That response exhausted 25k output/reasoning tokens
without a tool call. The new failed HTTP body is 2,164,348 bytes and matches the frozen
hash. This identifies a per-field string constraint, not evidence of a total-token
limit or transport timeout. Exact server length limit and why the provider produced
such a large opaque item remain unknown; the generation endpoint was not tested.

Evidence: `C:\pt\analyses\count-replay-live-20260912\result.md` and `analysis.json`;
collection `C:\pt\analyses\count-replay-collection-20260912`, run
`run_dev_countcollect_82df89236b5c4404`. Two no-call admissions agreed; 3,784 protected
files and native runtime are unchanged. Count billing remains UNCONFIRMED/null, not
a proven zero-dollar charge. Acceptance/safety NOT_RUN, official=false; grant consumed.
Next seam is offline continuation-size/admission and supported compaction investigation,
not an automatic ciphertext reset, new model run or another count request.

## Prior implementation: count-only collector; provider-free validation

`diagnostics/count_collector.py` now executes the frozen B2 count protocol separately
from the native agent. It permits only the count endpoint, one attempt per case,
control first; case 2 requires the original 97,810-token control. Errors, interruption,
changed control or deadline exhaustion stop the sequence without retry or resume.
The collector reuses the diagnostic async client: zero SDK retries, at most 30s per
request within a 65s execution deadline, including a reserved 5s for client cleanup.
Only safe error fields and body hashes/sizes are retained, never raw error bodies.

Admission validates the original packet/source/current reconstruction and credential
path before loading a key. A new external destination is claimed exclusively; started
attempts are durable before dispatch, and an interrupted destination cannot be reused.
Cleanup uncertainty is explicit, not a claim of remote cancellation. The collector's
code/transport hashes and outcomes live in a new journal; old packet/run bytes stay
unchanged. Runtime, tool surface, model inputs and native billing policies are unchanged.

The prior design's disabled live flag remains immutable and is not an execution grant.
A future collector invocation requires exact separate approval that acknowledges
unconfirmed count billing; its explicit CLI acknowledgement is not evidence of free
counting or a dollar cap. Community replies support a free-counting expectation, but
are not an official pricing guarantee. Count cost remains `null`, not inferred zero.
No actual count/model request, credential load, Docker or task execution occurred.
The previous comparison grant is closed; all results remain official=false.

Focused collector/count/transport/sampler/docs regression: 159 PASS in 65.77s;
Ruff PASS. Two real-packet read-only admissions agree (0.547s); 3,776 protected files,
including the frozen packet, old runs, runtime and `.env`, match their original hashes.
Receipts: `C:\pt\validation\countcollector-20260912` and
`C:\pt\validation\countcollector-focus-0912a.xml`. Full runtime suite and mock task
smoke were not rerun for this standalone diagnostic-only change. The original B2
rejection cause is still unresolved; mock success is not a reproduced live result.

## Prior preparation: frozen count-only design

`diagnostics/count_replay.py` prepares and verifies a new operator-only packet from
B2 turns 20/21. It reconstructs each original request and native call/output order,
then freezes only the exact count body. No new source, changed context, continuation
reset, model request, tool execution or old-run resume is introduced. The default
agent/runtime and v36 surface are unchanged. The module has no live collection mode.

The proposed order is successful-count control first, failed-count case second,
at most one request each. Any error, interruption or changed control count stops
before another request. Two successes mean NOT_REPRODUCED, not proof of a transient
historical error. Source/CAS/config tampering and stop rules are tested without a
provider. The exact frozen design and two no-call verifications are retained under
`C:\pt\analyses\count-replay-design-20260912` (packet `f8342755...`). Both verify
identically in a 0.443s preparation/rehearsal cycle; 3,759 protected files are unchanged.
The focused count/diagnostic/sampler/docs regression passes 112 tests in 50.68s;
Ruff passes. No new full runtime suite or mock smoke was needed for this standalone
diagnostic-only change; prior runtime validation below remains historical evidence.

At preparation, execution was disabled. The official token-counting guide and pricing
page reviewed on 2026-09-12 do not explicitly establish count-only endpoint billing;
do not label it free or treat generation token prices as its proven price. Resolve
that cost uncertainty and obtain exact separate approval before live collection.
The old comparison grant is closed. All evidence remains official=false.

## Prior implementation: bounded input-count failure evidence; no paid retry

Input counting now records operator-only request shape/size and a durable
`input_count_failed` receipt before its existing COUNT_TIMEOUT_OR_UNKNOWN terminal.
The receipt retains HTTP status, allowlisted error code/type/structural parameter and
request ID, plus the buffered HTTP body size/hash when available. It never retains
error messages, raw bodies, headers, credentials or reasoning plaintext. Unknown
field values are omitted, not shortened into logs. Native model context is unchanged.

A failed or interrupted count cannot restart on resume: exact-envelope recovery
returns the same bounded failure evidence without loading credentials, a workspace,
Docker or a provider client. Earlier provider/billing uncertainty keeps priority.
Terminal resume is byte-idempotent. Surface v36 and native inputs/tools/limits remain
unchanged; runtime content changes, so old nonterminal envelopes are not migrated.

The frozen B2 turn20/21 requests reproduce their original request hashes without any
API call. Canonical count-body UTF-8 size grows from 448,226 to 2,164,348 bytes;
the largest encrypted item grows from 30,692 to 1,701,176 characters. These are
offline canonical measurements, not captured wire bytes or proof of an API limit.
The original server rejection remains unresolved. Evidence is at
`C:\pt\validation\countdiag-20260912\offline.json`; 3,704 protected files, excluding
the two intentionally edited existing runtime files, and 30 sealed comparison files
are unchanged. No old run, task, credential or historical evidence was modified.

Focused SDK-mock/privacy/count-failure/resume tests: 42 PASS in 37.78s; Ruff PASS.
The full 80-file provider-free suite passes 1,448 tests; four real-Docker cases skip.
Four external groups took 325.65/320.84/316.56/317.31s, exceeding the two-minute full
cycle target; one existing JUnit record-property compatibility warning remains.
Mock `run_dev_0bd40e245b0742ee` reaches edit/check/finish/isolated EVALUATOR_PASS in
3.889s: four model turns, five tools, zero count calls/cost, task acceptance PASS,
safety NOT_RUN. Reports and smoke/offline evidence are under `C:\pt\validation`.
No live provider/count request, Docker operation or pyfakefs task execution occurred.
The prior comparison grant remains closed; this change does not authorize a new row,
ciphertext reset or automatic retry. All results remain official=false.

## Prior comparison: stopped at B2 input counting; no automatic continuation

After the user enabled Docker, the approved OFF/ON/ON/OFF packet `af29b90f...` ran
under unchanged runtime `28f08d7c...`/v36, v2 task, mini snapshot/medium/.env/probes.
Each repeat1 invocation retained its $1.20 cap; total maximum was $4.80. Evidence:
`C:\pt\analyses\repair-recheck-comparison-live-20260912b` (`result.md`,
`analysis.json`, `failure-analysis.json`, observer). The earlier zero-call Docker
preflight stop and original design remain immutable at their prior paths.

| Cell | Run suffix | Current public checks | Task acceptance | Cost |
| --- | --- | --- | --- | --- |
| A1 OFF | `2d9ac37041ae4c28` | both PASS | FAIL | $0.334105050 |
| B1 ON | `1cd3d953c69240e7` | both PASS | PASS | $0.333564450 |
| B2 ON | `03b4fcac720b4760` | regression PASS; contract NOT_RUN | NOT_RUN | $0.484494900 |
| A2 OFF | no run | NOT_RUN | NOT_RUN | $0 |

Total recorded model usage: $1.152164400, 64 model calls, 65 count attempts, 72 tools,
seven accepted edits and 706.868 active seconds. Safety A1/B1 PASS, B2/A2 NOT_RUN;
all official=false/claim_eligible=false. Only aggregate private verdicts were read.
A1 repaired its mode failure and selected manual recheck. B1's two harness rechecks
exposed a new NameError then PASS; B2's harness recheck repaired seven regression
failures. All three child results reached the next inference on the correct diff.

B2 turn20 still had checks/read/search/mutation/probe/stop available, 21 model calls,
80 tools and two edits remaining. It consumed all 25,000 output tokens as reasoning
without a tool call. The next correction retained the encrypted item (1,701,176
characters) and all 19 native call/output pairs. Turn21 input counting failed with
BadRequestError; terminal COUNT_TIMEOUT_OR_UNKNOWN, not a proven timeout. No model
request21 dispatched. The detailed server error was not retained; a size/continuation
boundary is a hypothesis, not an established API limit or exact rejection cause.

The uncertainty rule closed the comparison, leaving A2 NOT_RUN with no retry/resume
or replacement. Mini task acceptance success recurred, but different initial patches
and an incomplete comparison prevent a causal recheck/success-rate claim. Default
stays OFF. This motivated the bounded count-error implementation and offline request
shape/size inspection above, not another paid row or speculative reasoning reset.
64 provider and 65 count request hashes, continuations, 204 referenced artifacts
(sum across runs), submitted diff identity and owned-container absence verify.
All 3,706 protected files and prior stop bytes are unchanged; runtime/task unchanged.
Result documentation: three tests PASS (0.057s), Ruff/diff checks PASS; no full runtime
suite or mock smoke rerun, and no disposable documentation-test workspace created.

## Prior single-row result: fresh mini plus repair-recheck reaches task acceptance PASS

The exact separately approved invocation completed as `run_dev_d484ea8a2a8e4ba4`
at `C:\patchloop-state`; approval, public trajectory and integrity receipts are at
`C:\pt\analyses\repair-recheck-live-20260912` (`result.md`, `analysis.json`). Fresh
v2 task/base, mini `gpt-5.4-mini-2026-03-17`/medium/25k, root `.env`, repeat1,
$1.20 cap, probes and `--repair-recheck`; runtime `28f08d7c...`/v36 are unchanged.

Result: **EVALUATOR_PASS**, task acceptance PASS and typed safety PASS, 15 model/count
calls, 16 tools, two accepted edits, $0.208261650 and 163.312 active seconds. The final
19-line diff (+18/-1, one allowed file) passes both visible checks and isolated
evaluation. Public regression reports 517 passed/570 skipped. Only aggregate private
verdicts are observed; no private failure details or feedback entered agent decisions.
This remains official=false/claim_eligible=false, not a benchmark or success-rate claim.

Nine source inspections and one real-OS probe precede the first mutation at turn11.
The agent chooses recursive raw-path creation using the existing split/mkdir helpers,
instead of the previous run's component prepass. Turn12's public check fails at the
intermediate-mode assertion. Turn13 immediately changes recursive parent creation
from the caller's mode to PERM_DEF while retaining the requested leaf mode. The harness
then reruns that exact failed check once: PASS on the new diff, before turn14 inference.
Turn14 runs the remaining regression check; turn15 submits. No rejected mutation,
protocol correction, token exhaustion, provider uncertainty or redundant repair occurs.

The child is charged once as a tool action, with no model/count call and no fabricated
native function call. Its current PASS is present in turn14's reconstructed public
state. Fifteen exact request hashes/continuations, 14 continuation follow-ups, 51
referenced artifacts and the check/worktree/submitted patch identity verify; all
3,645 protected files remain unchanged. Optional memory updates are all null; native
observations and encrypted continuation are present, not an empty-memory experiment.

Interpretation: feedback timing is live-verified and this mini run solved the task.
The better initial algorithm and correct mode repair both precede the automatic
recheck. One different stochastic trajectory cannot establish that recheck caused
the success, improved success rate, or removes the value of notes. Default stays off.
Preserve this result; a later matched repeat/comparison needs its own exact approval.
This grant is consumed: no automatic retry/resume, extra check, model/budget change
or Docker start/pull/build follows.

Result documentation passes three focused tests (0.054s), Ruff and diff checks.
Runtime/task bytes are unchanged; no full runtime suite or mock smoke was rerun.
The documentation tests created no disposable pytest workspace.

## Prior implementation: opt-in repair-recheck feedback

`--repair-recheck` is implemented, default **off**, under tool surface v36. After
an accepted mutation changes a diff with a current public failure, the harness
reruns the latest still-failing registered check before the next inference. Initial
edits without a current failure and rejected edits do not trigger it. Other checks,
semantic repair choices and notes stay with the agent; no new action mask or plan
requirement is introduced. The native tool schema/order and encrypted history are unchanged.

The child is explicitly harness-originated, costs one normal tool action and active
time, and makes no model/count call. Its exact parent/check/diff identities and
start/finish receipts support resume; durable results replay without execution.
Current feedback is delivered through the existing bounded public check state, not
a fabricated model function call. The option is bound in the exact envelope.
Pending recovery precedes a new completion-horizon decision, while provider/cleanup
uncertainty, deadline and workspace boundaries retain their stopping behavior.

The 18 focused tests pass in 62.96s, including six crash boundaries, default-OFF
behavior, native feedback delivery, current-failure selection, last-mutation horizon,
budget/deadline/drift, terminal resume and uncertainty precedence. The final 79-file
regression selection is 1,425 passed / four real-Docker opt-in skips; Ruff passes.
Four initial failures were an obsolete v35 hash assertion and three frozen-diagnostic
tests expecting admission under their old runtime. Updated tests require unchanged
runtime-mismatch rejection, never migrated evidence or relaxed execution gates.
Their 68-case compatibility/documentation rerun passes in 86.25s. The longest full
worker took 298.86s: the whole validation cycle is **not** under two minutes.

CLI mock `run_dev_bb4e471f35954f76` at
`C:\pt\validation\repair-recheck-smoke-20260912a` reaches mutation/check/finish/
isolated acceptance PASS, safety NOT_RUN, four mock turns/five tools/one edit/$0.
Its enabled option correctly does not add a recheck without a prior failure; the
focused synthetic failure tests exercise the child. Runtime `28f08d7c...` and v36
surface `e02c52b5...` match validation and smoke. Detailed receipts are at
`C:\pt\validation\repair-recheck-20260912.md`. No live run, provider
call, Docker start/pull/build, task change or original evidence update is authorized
by that implementation alone. Its later separately approved live observation is
recorded above; causal agent-quality benefit remains unestablished; official=false.

## Prior result: frozen third candidate publicly checked

The separately approved public-only check of the fresh run's third candidate is
complete at `C:\pt\evaluations\mini-third-candidate-20260912` (`result.md`). Exact
30-line candidate `7c97d024...` was restored from the saved turn23 context and turn22
admission, in a separate no-hardlink base clone. It was not repaired or resumed.

Both registered checks ran once: contract FAIL at the same public line23 permission
assertion as the fourth candidate; regression 6 failed/511 passed/570 skipped.
The bytes call and its assertions precede this failure in the verified straight-line
public script. Thus the fourth edit was unnecessary for that observed bytes case,
not proof the third candidate was correct. Parent-file errno and broken-symlink/
trailing-separator failures remain. No fourth-candidate rerun or new baseline ran.

Execution took 13.189s (checks 1.176s/10.604s), with zero provider/count calls and
$0 model cost. Candidate/diff/policy identities, container cleanup and 3,388 protected
files verify. No hidden evaluator, patch repair, Docker start/pull/build, retry,
runtime/task change or original-run update occurred. Task acceptance/safety NOT_RUN;
official=false/claim_eligible=false. These are operator observations, not agent checks.

This motivated the opt-in repair-and-recheck feedback experiment above, not another
automatic paid row, budget increase or mandatory notes. Rechecking can supply a
current counterexample; correct repair and broader behavior preservation remain
unproven. Its implementation is a separate follow-up, not authority from this completed check.

Three documentation tests and Ruff pass. Runtime/task bytes did not change, so no
full runtime suite or mock smoke was rerun. No disposable pytest tree was created.

## Prior run: fresh-start mini completed; grant consumed

The separately approved default-mini reproduction completed one new native run,
`run_dev_91384f8a97354835`, at `C:\patchloop-state`. Read-only approval/analysis is
at `C:\pt\analyses\mini-fresh-start-20260912` (`result.md`). It starts with an empty
diff, no notes/source/old continuation, and full 40/100/4 budgets; no checkpoint,
answer patch or private feedback was seeded. Runtime a3d7f3c0/tool surface v35,
task v2, mini snapshot/medium/25k, root `.env`, probes enabled and $1.20 cap were unchanged.

Result: `LIMIT_REACHED`, 27 responses/counts/tools, four accepted edits, three failed
public contract checks, $0.441195300 and 220.438 active seconds. The final 32-line
diff is within scope, but its intermediate directories still receive the leaf mode;
the last check fails the public `0o755` permission assertion. Regression, submission
and isolated evaluation did not run. The sole horizon blocker is accepted mutations,
with 13 model/73 tool calls left. No token ceiling, transport or protocol error occurred.

After the third edit, the model uses an old bytes error to justify its fourth edit
without rechecking. Exact inputs already include the post-image, NOT_RUN current
checks, historical failures and pending-recheck guidance; check/probe/read/search
remain available. This repeats a stale-verdict-use pattern, not demonstrated feedback
loss. The third candidate was untested in the native run; the separate public-only
check above establishes the narrower bytes result, not overall PASS. Four note updates
yield one retained note; receipts and source rebinding verify, but repair outcomes
are not incorporated. Absent internal planning or a need for mandatory notes is unproven.

All 27 request hashes and encrypted continuations, 26 continuation follow-ups,
81 referenced artifacts, check policy/diff identities and 3,231 protected files verify.
Owned check containers are absent. No retry/resume, extra task check, private diagnosis,
Docker start/pull/build or default-loop change occurred. The subsequent third-candidate
check and separately approved repair/recheck-loop observation are recorded above.
Neither authorizes another automatic paid row or budget increase. Task acceptance and
safety NOT_RUN; official=false/claim_eligible=false. This one run is not a success rate.

Result documentation passes three focused tests (0.050s), Ruff and diff checks.
Runtime/task bytes are unchanged; no full runtime suite or mock smoke rerun. No
pytest scratch tree was created by these documentation-only tests.

## Prior result: frozen mini submissions independently evaluated

The separately approved operator evaluation of both publicly submitted mini patches
is complete at `C:\pt\evaluations\pl43-mini-recovery-v1`; read `result.md` there.
No patch was repaired and no agent was resumed. Each exact artifact was applied once
by the unchanged evaluator in a fresh no-hardlink workspace at the audited base.

| Diagnostic source | Diff lines | Public regression | Task acceptance | Evaluation safety |
|---|---|---|---|---|
| C1/A/1 | 49 | PASS | PASS | PASS |
| C1/A/2 | 28 | PASS | FAIL | PASS |

Both scope results PASS; evaluation durations are 8.518s and 8.356s. The second
aggregate failure class is `PRIVATE_EVALUATION_FAILED`, not an infrastructure error.
No hidden case, error detail or reference solution was opened for diagnosis or fed
back to the agent. Do not attribute that failure to the earlier public receiver-risk
observation without independent public evidence.

Submitted/applied/checked hashes and manifest/policy evidence verify; 2,845 protected
files are unchanged and both evaluations' owned containers are absent. There were
zero provider/count/probe calls, $0 new model cost, no Docker start/pull/build, retry
or new live row. The original diagnostic's NOT_RUN records remain immutable.
Evaluation safety applies to these operator executions, not the whole source agent.

Mini produced one independently accepted patch from this checkpoint. This is not
a fresh-start full-run result, a 50% overall success rate or cross-task evidence.
The subsequently approved fresh-start reproduction is recorded above, without seeding
either patch or private feedback. No context reduction, forced notes, default-loop
change or further paid execution is authorized by these results.
All evidence remains official=false and claim_eligible=false.

Evaluator/documentation focused tests pass (12 cases/7.78s), followed by three final
documentation cases/0.10s, Ruff and diff checks. Runtime is unchanged; no full suite
or mock smoke rerun. The one owned pytest root was hash-verified and recycled with
a restoration receipt; both durable evaluation workspaces remain in place.

## Prior diagnostic: mini recovery completed; grant consumed

The exact `mini-recovery-budget-v1` invocation completed all eight fresh checkpoint
episodes: `run_dev_episode_collection_a78ccd1085a8478b`, 76 responses/count calls,
83 tool actions, $2.55174405 / $5, 994.987 seconds. Billing is fully known; there
were no incomplete responses, protocol errors, request failures or unstarted cells.
Result root: `C:\pt\analyses\pl43-mini-recovery-live-v1`. Anonymous public code
observations were sealed before mapping, followed by exact request/continuation,
usage and public check/submission identity audits at
`C:\pt\analyses\pl43-mini-recovery-assessment-v1`; read `analysis.md` there.

| Public checkpoint | Historical descriptions A | Initial-current-state B |
|---|---|---|
| C1, before turn14; 4 mutations left | 2/2 public submissions | 0/2 |
| C2, before turn21; 1 mutation left | 0/2 | 0/2 |

Two mini branches repaired public failures, passed both checks and submitted at
new responses 13 and 11. The other six reached native `LIMIT_REACHED`, exclusively
blocked by exhausted accepted mutations with 10-16 model calls still available.
There were 23 mutation attempts/16 accepted, 23 public checks and two probes.
Peak output was 10,449 / 25,000 tokens; peak input 159,552 / 272,000. These failures
are not evidence for raising the output ceiling or resetting encrypted reasoning.

Several failed repairs confused backend helpers with wrapper methods. In C1/B/1,
the exact next request contains the corrected post-image, historical failure labels
and pending-recheck guidance, yet the public decision treats an untested repair as
already failed. This is incorrect use of delivered evidence, not demonstrated loss
of that feedback. One publicly passing candidate retains an unexecuted receiver-risk
branch; public PASS does not establish complete task correctness. No new memory
updates were proposed, including by successful branches; absent internal planning
or a benefit from mandatory notes is not established.

The trial does not support removing inherited state descriptions: the opposite
direction repeats at C1, but not both checkpoints. With two samples per cell and
only one remaining C2 mutation, a general causal explanation remains unresolved.
Both arms append all new native state/results/encrypted reasoning; B is not ongoing
current-only compaction. The eight-response window would miss both submissions,
but this does not isolate longer observation from the earlier instruction repair.
No default context, model, memory, tool surface v35 or task changed.

The consumed packet remains at `C:\pt\analyses\pl43-mini-recovery-design-v1`, hash
`sha256:ce3e9de64c93c324fa78ef2132b7f569be924c6fcb9db0511faa712f9016a976`.
It fixed mini `gpt-5.4-mini-2026-03-17`, medium, 25k, root `.env`, shared $5/1,800s,
count30s/response300s and order C1/1 AB, C2/1 BA, C1/2 BA, C2/2 AB. Already-running
Docker/pinned images were used without start/pull/build. No retry, resume, extra
sample or hidden evaluator ran. `task_acceptance=NOT_RUN`, `safety_state=NOT_RUN`,
`official=false`; this is not a fresh full-run success rate or a model comparison.

Next is a separate decision about one evidence-backed intervention or independent
candidate evaluation, not automatic context reduction, forced notes, extra action
masks or budget increases. Inspect the delivered-source/receiver and check-diff
counterexamples first. No additional paid work or default-loop change is authorized.
The prior provider-free implementation receipts (188 related cases and default mock
`run_dev_21fe1d793876457e`) remain distinct from these live public observations.
This result-documentation change passes three documentation tests (0.19s), Ruff
and diff checks. The 1,366-file preservation map, packet/protocol and implementation
hashes are unchanged; no full runtime suite or mock smoke was rerun for docs only.

## Prior repair: diagnostic request waits

The short-episode collector now caps input counting at 30 seconds and response
waiting at 300 seconds, each clipped to the remaining shared/branch execution
deadline. A diagnostic-only async SDK facade cancels the entire request, including
a trickling response body; merely passing an HTTPX per-I/O timeout was insufficient.
No provider worker is launched. Local response parsing is checked before admitting tools.
These are operational experiment limits, not model latency guarantees: the 28 saved
completed responses peaked at 60.279 seconds, while the unknown dispatch consumed
about 22m26s. They do not prove why that old request failed.

Exact new packets/envelopes bind the wait policy and transport implementation.
Receipts distinguish count/response waiting, local response processing, usage and
continuation validation, and late pre-tool admission. Only allowlisted error labels,
phase, IDs/hashes, elapsed time and effective limit are recorded, never SDK messages,
headers, raw response bodies or plaintext reasoning. A received response can retain
verified usage even if action parsing fails; late parsed decisions/continuations are
preserved without executing tools. Unknown billing still stops the whole experiment,
without retry/resume. Local cancellation does not establish remote billing status.
Client cleanup is bounded to five seconds per owned client before the existing
read-only metadata tail; cleanup outcomes are durable, including failures.
Loop closure does not wait for an OS DNS executor to finish: such work cannot
re-enter the closed loop, but this is not a hard process/OS-thread termination promise.

No default runtime, model, context, memory, tool schema or task package changed.
Provider-free receipts belong under `C:\pt\analyses\pl43-request-waits-v1`; no paid
call, input-count API call, Docker operation or pyfakefs evaluation is authorized by
this repair. The later mini-only execution above used its own exact grant;
it is not a claim that mini performance improved.

Validation: 192 distinct related cases pass (32 focused in 73.97s, 27 final collector
in 112.58s, 131 shared regressions in 108.72s; the final 18-case boundary/docs check
adds two new cases and repeats sixteen). Ruff passes. The first collector run took
127.36s; removing redundant multi-group work from the lock test brought its final
run below two minutes without dropping the separate 16-window schedule test. This
is not a full-runtime-suite rerun or a two-minute aggregate workflow. Diagnostic
mock reaches public checks/finish; separate default mock `run_dev_ce016b90431140df`
at `C:\pt\smoke\pl43-request-waits-v1` reaches isolated `EVALUATOR_PASS`, safety
NOT_RUN, zero cost and official=false. The 16 saved first requests and 1,366 protected
files retain their exact bytes/hashes. This is fixture/integrity evidence, not new
pyfakefs acceptance, a recovered charge or model-quality evidence.

## Prior repair: diagnostic episode instructions

The snapshot-to-episode instruction mismatch below is fixed in diagnostics only.
Before the first request, `model_state_episode.episode_request` replaces the flat
snapshot notice with the existing native conversation contract plus an initial-archive
lookup rule. Immutable task/archive and checkpoint `source_bodies` are distinguished
from later `harness_current_state.state`, native outputs and current file identities.
Sent messages, public inputs, tool/property order, encrypted replay and the standalone
one-response sampler are unchanged. No default model, agent policy or memory change.

Preparation v2 binds the instruction hash and separates source request identities
from new exact first-request identities. The collector verifies both canonical and
ordered request hashes; old preparations are rejected before task/credential access,
not migrated. The new preparation is non-executable, not a renewed paid grant.

Validation: 19 focused cases in 63.384s, 25 collector cases in 117.263s, and 76 reused
sampler/source/conversation/documentation cases in 17.757s pass, plus Ruff. These are
120 related cases, not the full runtime suite or a two-minute aggregate workflow.
The collector mock reaches public mutation/checks/finish. A separate default mock
smoke at `C:\pt\smoke\pl43-episode-instructions-v1` reaches isolated evaluation:
`run_dev_e680c529bc3849cb`, `EVALUATOR_PASS`, safety NOT_RUN, cost zero, official=false.
That fixture result is not pyfakefs task acceptance or measured agent improvement.

Read-only real-input verification at `C:\pt\analyses\pl43-episode-instructions-v1`
checks all 16 independent starting requests and 16 saved mini inputs, including
14 follow-ups: only instructions change; current source bytes and public histories
remain identical. No old response was executed or old request rewritten. The 1,367
protected files outside the two edited diagnostic modules retain their hashes.
No provider/count call or Docker operation ran. The separate request-wait repair
above now follows this instruction change. New paid comparison still requires a
new exact packet/approval.

## Prior mini decision trace: diagnostic instruction defect found

Read-only tracing of the two C1/repeat1 mini episodes is complete at
`C:\pt\analyses\pl43-mini-decision-trace-v1`. The full public task, current observed
source and encrypted continuation are present; all 16 responses completed with
inspection/mutation tools available. New working notes and verification concerns
remained empty, with no attempted update discarded. This does not establish that
explicit planning is necessary or that the supplied context is optimal.

Historical-state mini first forwarded leaf mode into parent recursion, then
immediately removed that argument after the public permission failure. Its repaired
final diff is untested. Current-state mini used a backend helper on the wrapper's
`self`, hit AttributeError, then searched for the correct owner. Both eight-response
windows ended during recovery, not at the agent's global completion horizon.
An `isabs` search returned only the Windows branch header, without answering its
stated implementation question; no persistent public open question followed.
This illustrates a tracking gap, not the proven cause of the helper exception.

One concrete **diagnostic-only input defect** is verified: snapshot instructions
still direct the model to top-level state, the initial archive and `source_bodies`,
while all 14 follow-ups append nested `harness_current_state.state` and new native
results. Four post-edit inputs retain historical initial source bodies. Current
bytes are available and resolve correctly; the instructions misidentify their
authority/location. The default native runtime has the correct separate contract.
Whether this mismatch caused either mini error is **not established**.

The diagnostic snapshot-to-episode instruction repair is implemented above, without
changing the default agent or forcing plans/notes. The separate bounded collector
waits and sanitized failure-phase receipts are also implemented above. Any later
evidence-to-code/unfinished-question
experiment requires a new packet and approval; the old grant cannot be resumed.

Seven public-trace assertion groups pass; 1,369 bound files remain unchanged.
This analysis adds no provider/count call, task execution or hidden evaluation.
`task_acceptance=NOT_RUN`, `official=false`; report and hashes are in the external
analysis root. Current-state condition removes only inherited pre-checkpoint state
descriptions, not new full-state accumulation; input growth is measured, but its
performance effect remains unproven.

## Prior partial short-episode result; no automatic continuation

The exact $5 packet below was approved and executed once on 2026-09-11 at
`C:\pt\analyses\pl43-short-episode-live-v1`, run
`run_dev_episode_collection_dd2a43b37b8d406c`. The grant is consumed. Terminal is
`PROVIDER_TIMEOUT_OR_UNKNOWN`: 29 counted dispatches, 28 completed responses,
31 tool actions, 1,801.237s including read-only finalization. Known completed usage
costs **$1.420476**, with one additional request's billing unknown. This is not a
confirmed total cost. No retry, resume, extra sample or hidden evaluator ran.

Blind public observations were sealed before condition mapping. At pre-turn14
(C1), repetition 1 produced:

| Model / inherited state descriptions | Responses / actions | Public outcome |
|---|---:|---|
| mini / historical | 8 / 8 | Mode failure, then accepted repair; final candidate untested at window end |
| mini / current | 8 / 8 | Missing-helper failure; recovery search at window end |
| GPT-5.4 / historical | 4 / 4 | Both public checks PASS, same-hash finish |
| GPT-5.4 / current | 6 / 7 | Both public checks PASS, same-hash finish |

Both submitted candidates passed the existing regression with 517 passed / 570
skipped. Eight-response windows are censored observations, not proof the mini
branches could never recover. At pre-turn21 (C2), D and B each returned one
inspection response; C's first request had no durable response/usage and A was
never dispatched. No C2 mutation/check occurred; its visible statuses are inherited.
Repetition 2's eight windows remain unstarted. **The model-associated C1 difference
is observed, but model/context effects are not replicated or causally resolved.**

The last request occupied roughly 22m26s of the remaining shared deadline. Its
exception type/phase was not persisted, so provider delay, transport/SDK timeout
and response-processing failure cannot be separated. This is not evidence of a
25k output-token ceiling: all 28 returned responses were complete, maximum output
9,642. A serial request can consume other arms' time despite balanced cost reserves.
An additional provider-free implementation candidate is a bounded per-request wait
and sanitized failure-phase record in the diagnostic collector, not new agent gates.
It has not been implemented; no default model/context/memory change is selected.

Read-only audit verified all 29 request identities, 28 continuation artifacts and
22 follow-up replays, six check-policy/diff bindings and two submission identities.
There were zero new `memory_update` proposals; this neither erases inherited notes
nor proves note generation is needed. Details and sealed observations are under
`C:\pt\analyses\pl43-short-episode-assessment-v1`. The factor changes only inherited
state descriptions, not ongoing native context accumulation. Task acceptance and
safety remain `NOT_RUN`, `official=false`. No automatic Docker start/pull/build.

## Prior short-episode collector implementation

`diagnostics/model_state_episode_collector.py` now binds the prepared experiment
to one exact invocation: immutable packet/implementation/runtime/task identities,
fixed model prices, a **$5 shared cap**, an exclusive result root and
run-lifetime locks. Preparing, validating and inspecting never load a credential,
call a provider or use Docker. The implementation evidence below preceded the
single paid execution above; it does not confer another execution approval.

The new packet is `C:\pt\analyses\pl43-short-episode-execution-v2\packet.json`,
`sha256:422ea586587c7a059fd48c65f6fcc9530c41874eb776f4594c5c944cce2a6776`.
It fixes mini/GPT-5.4 medium/25k, the two row43 checkpoints and two repetitions of
four conditions, at most eight responses per independent window. Every next depth
reserves all active arms at the 272k-input/full-output bound before dispatch; a
four-arm depth reserves $2.743. Actual inputs are counted just before dispatch.
**$5 does not guarantee all 16 windows or 128 possible responses.** Unobserved
windows and cost/step/deadline censoring are separate from agent failure.

The 1,800-second shared deadline reaches checkpoint cloning and public actions.
No retry/resume occurs after cost, count, transport or continuation uncertainty.
Durable usage determines billing; read-only `inspect` never resumes pending work.
A discovered deadline-finalization defect is fixed in the collector: after task
execution stops, an independent ten-second read-only Git metadata tail can preserve
final candidates. If a snapshot is missing or drifts, retain partial evidence with
no invented candidate binding. Never relax the gateway execution deadline.

Twenty-two collector tests pass in 110.02s, including actual local mock
read -> mutation -> both visible checks -> finish, deadline/transport faults,
concurrent-entry rejection and immutable crash inspection. Both real checkpoints
also restore exact requests, tools and counters with the shared deadline; the
packet validates twice without calls. Receipts are under
`C:\pt\validation\pl43-episode-collector`. This is provider-free implementation
evidence, not improved agent performance or hidden acceptance.

Related validation totals 166 passing cases: 22 collector, 45 episode/factorial/
review (126.96s), 96 reused engine/sampler (116.24s), and three documentation
(0.05s), plus Ruff. The 45-case group exceeds the two-minute target; these are
related tests, not a full-runtime rerun or a single two-minute workflow. Exact
public decision arguments and results are paired in anonymous receipts. The earlier
unapproved execution-v1 draft is preserved but superseded, not overwritten.
All 1,298 protected files, source journal/envelope, `.env` and user `AGENTS.md`
retain their hashes. Eight owned temporary roots were recycled with identical
contents and restoration mappings; durable packets/validation remain in place.

That packet's one approved invocation used root `.env` and execution-day verified
prices. Its occupied result root is immutable and cannot be reused or resumed.
Any further paid experiment needs a separately bound packet and exact approval.
Default agent/runtime, task packages and prior evidence remain unchanged.

## Prior inspection audit and short-episode preparation

The read-only follow-up at `C:\pt\analyses\pl43-inspection-audit-v1` compares all
25 saved inspections with the exact source bodies in their original requests:
16 return new source ranges, six return only already delivered ranges, and three
searches return no matches. Five covered-only reads at pre-turn21 revisit the
already supplied editable function to acquire an exact anchor. One public decision
already states the eventual repair direction; it is not evidence of an executed
repair. New coverage is not proof of usefulness, nor is repeated coverage proof
of a defective memory. **Cause remains unresolved.**

`diagnostics/model_state_episode.py` reuses the existing short-rollout gateway,
native continuation, correction and cost arithmetic. It prepares fresh independent
A/B/C/D starts, never selected old responses, and supports injected short episodes:
read/search -> returned public evidence -> mutation -> model-requested checks/finish.
The eight-response observation bound is censoring, not a new agent action mask.
The history factor is inherited pre-checkpoint state; new native state views,
encrypted reasoning and calls/results accumulate in every arm. This is not ongoing
current-only compaction. Production runtime/tool surface v35 is unchanged.

That preparation module has no credential/client construction or live CLI. The
separate collector above supplies exact-grant, lock/deadline and fail-stop binding;
it does not inherit paid authority from the completed experiment. No provider,
Docker or hidden evaluator execution accompanies this implementation.

The new preparation is `C:\pt\analyses\pl43-short-episode-design-v1\packet.json`,
`sha256:dc8f431ea408ce311270f2e42cd2ccbfc16d3ed6f7b8efa888c87e3ba1b5ac02`.
Both actual checkpoints restore exact first requests/tool sets with 13/13/0 and
20/20/3 model/tool/mutation counters. Related provider-free validation passes 111
tests: 13 new cases in 69.80s, 63 engine/sampler cases in 104.12s, and 35 factorial/
review/documentation cases in 79.21s, plus Ruff. This is not a full-runtime rerun or
a claim that the entire debugging/validation cycle took under two minutes.
Receipts are at `C:\pt\validation\pl43-episodes`. All 1,298 protected files, source
journal/envelope and user `.env`/`AGENTS.md` retain their hashes. Eight owned scratch
roots were recycled with content-identity checks and recorded restoration paths;
pre-existing repository scratch and old experiment records were not changed.

## Completed model x state-history diagnostic (cause unresolved)

The explicitly approved frozen packet completed as `run_dev_sample_4bf128b8d21744d5`
at `C:\pt\analyses\pl43-model-state-live`: 16 independent responses/counts, all four
balanced blocks, $0.9615305 / $5, 159.184s, no retry/correction/chaining. The earlier
host rejection started no process; explicit payload/destination/spend approval
preceded this first actual invocation. This grant is consumed.

Anonymous code and execution observations were frozen before unblinding at
`C:\pt\analyses\pl43-model-state-assessment`. All batches are valid: 14 inspection
batches (25 actions), two admitted mutations and four Docker public checks, with
confirmed cleanup and no check-cache reuse. No hidden evaluator runs.

| Condition | Pre-turn14, repetitions 1 / 2 | Pre-turn21, repetitions 1 / 2 |
| --- | --- | --- |
| mini / history | inspect / inspect | inspect / inspect |
| mini / current | inspect / inspect | inspect / inspect |
| GPT-5.4 / history | mutate, contract FAIL / inspect | inspect / mutate, both PASS |
| GPT-5.4 / current | inspect / inspect | inspect / inspect |

The first 29-line candidate raises FileExistsError then calls the unavailable
`FakeOsModule.raise_os_error`, failing the first public contract call; upstream
regression passes. The later 39-line candidate delegates non-`..` paths back to
`FakeFilesystem.makedirs` while retaining the traversal change, passing both public
checks. Both upstream executions report 517 passed / 570 skipped. Neither proposal
is credited as original-agent checking/submission or hidden task acceptance.

Actual input falls from 45,804 to 25,970 tokens at turn14 and 85,984 to 46,102 at
turn21 when only older state descriptions are removed. Every output completes in
349-3,991 tokens, below 25k. All 16 ordered requests and encrypted continuations,
27 function references, candidate/check bindings and recorded costs validate.

The shorter input shows no repeated quality improvement; the lone public-pass
repair does not establish a model or history benefit. Inspection-only responses
are unassessed repair quality, not failures: this one-response design cannot observe
their next repair. Conclude **cause unresolved**, retain default runtime/context/
model/memory/tool policy, and do not automatically buy more samples or adopt a fix.
All results remain `official=false`, `task_acceptance=NOT_RUN`, `safety_state=NOT_RUN`.

All 1,298 protected runtime/task/history files, `.env`, user-owned `AGENTS.md` and
the original journal/envelope retain their pre-run hashes. The 16 owned checkpoint
copies (2,051 files) were recycled with complete content identity and restoration
mapping in `scratch-recycled.json`; durable results remain in place. The initial
Windows housekeeping-helper failure and typed-interface correction are recorded
there, separate from the completed Docker checks. Three documentation tests pass
in 0.066s and Ruff/diff checks pass. No new full runtime suite is claimed for this
result-only documentation change.

### Preparation and provider-free validation (before collection)

`diagnostics/model_state_sampler.py` prepares a separate 2x2 comparison at row43
turns 14 and 21: mini/history, mini/current, GPT-5.4/history, GPT-5.4/current.
Both models use medium and a fixed 25k output ceiling. Every input starts fresh,
without old encrypted reasoning, and retains the same public task/current state,
exact observed sources and complete quoted public call/result archive. Only the
model and older state descriptions vary. Default runtime/task/tool surface v35,
native continuation, optional memory and action policy remain unchanged.

The fixed order balances four-arm blocks across two cutoffs and two repetitions,
up to 16 independent responses under one proposed $5 cap. Each block reserves full
output plus the 272k input admission bound for all four arms; actual input counting
still precedes each dispatch. This can stop below $5 rather than shrink output or
leave a cost-truncated comparison block. Transport/count/billing uncertainty stops
everything; no retry, model substitution, chaining or automatic follow-up.

`diagnostics/model_state_review.py` separately restores each checkpoint in an
external workspace, validates exact replacements and total scope, and executes only
the declared public checks/inspections. Check results can be reused for the same
checkpoint/candidate hash, without giving the original agent check credit.
Anonymous observations are frozen before a separate read-only unblinding report.
Inspection is not automatically a failed mutation; unseen regressions and mutation
quality after non-mutation remain unassessed. No hidden evaluator or paid judge runs.

The prepared packet is `C:\pt\analyses\pl43-model-state-design\packet.json`, hash
`sha256:8e5c7710ea7162f6f91bd31fcdc9b05b5098afc61330108243aa9572d04d72b7`.
Sampler identity:
`sha256:c3429a2dcef5b24deab165de0908c28a5efdd237799b79f27660d4248ec796ce`.
Two read-only revalidations agree. Full mini requests are 198,883/113,575 bytes
(turn14 history/current) and 352,612/187,444 bytes (turn21), not fresh token counts.
Both actual checkpoints restore exactly without tools: 0/36 diff lines and 0/3
inherited mutations. Restoring a checkpoint is not executing a sampled proposal.

All 237 focused/regression cases pass in two parallel groups: 35 new/docs tests
in 73.68s and 202 prior sampler/design tests in 97.58s. XML execution span is 99.382s;
Ruff passes. The local synthetic diagnostic smoke reaches admitted mutation, both
public checks, cache reuse, blind freeze and unblinding; it is not a model-quality
result. Receipts are under `C:\pt\validation\pl43-model-state`. All 1,298 protected
runtime/task/history files, `.env`, user-owned `AGENTS.md` and source run bytes are
unchanged. No full runtime-suite or private-evaluator smoke rerun is newly claimed.
The nine owned temporary roots were recycled, not permanently deleted; exact
restoration locations remain in `scratch-recycled.json` beside the validation receipts.

Preparation itself made zero paid/count/Docker/hidden-evaluator calls; its proposed
$5 ceiling was not execution approval. The separately approved collection and
public assessment above are diagnostic evidence, not a new default-agent live row
or a measurement of native encrypted-continuation effects.

## Prior seam: explicit draft review does not change proposed behavior

The approved pilot completed as `run_dev_sample_28ab0479aac64fe9` at
`C:\pt\analyses\pl43-draft-review-live`: four independent responses/counts,
$0.0700872 / $1.20, 38.615s, and zero sampled tools, corrections, retries, Docker
or evaluator executions. The earlier host rejection started no process. Explicit
payload/destination approval then preceded the first actual invocation; this grant
is consumed. No further sampling or live row is authorized.

Anonymous static review at `C:\pt\analyses\pl43-draft-review-audit` was frozen
before unblinding. A1/A2/B1 reproduce the draft code exactly; B2 only changes line
wrapping. All four have the same AST as the draft, preserving its false EEXIST and
intermediate-directory mode contradictions. All observed old_text anchors match;
all new memory updates are null. These are static facts, not gateway/check results.

Actual inputs are 50,675 tokens for A and 50,702 for B. Reasoning tokens are
A1=34, A2=93, B1=215, B2=316; completed outputs are 1,003-1,252 of 25,000 tokens.
All four ordered requests and continuation artifacts validate; each request retains
13 original reasoning items and 13 native call/result pairs. Protected files (1,069)
and the new live files (17) remain unchanged during review.

This intervention shows no executable improvement over a neutral second opportunity.
It does not establish internal reasoning, memory failure or that every reviewer is
ineffective. Keep the default runtime/task/prompt unchanged; do not adopt this extra
review call or automatically repeat it. This is a four-proposal pilot at one reused
failure-selected checkpoint, not a general quality or task-acceptance result.
Documentation tests (3, 0.10s) and Ruff pass. No full runtime suite or runtime mock
smoke is newly claimed; the documentation validation created no disposable test root.

## Prior seam: draft review versus neutral second opportunity prepared

`C:\pt\analyses\pl43-draft-review` freezes row43 turn 14 and the first collected
requirements-focus proposal (A1) as explicitly unexecuted data. Both arms retain
the same 54 preceding items, 13 encrypted reasoning items, source/tool history,
optional notes, unchanged worktree/check state and model settings. Only the latest
`draft_reconsideration.harness_instruction` differs: A chooses the next action;
B first compares the draft's executable behavior with the existing public requirements.
Neither names the known defects or supplies an operator repair or new example.

Full requests are 258,422 / 258,605 bytes (+183), not token counts. This is review
framing/wording, not a length-matched attention experiment. The draft sample's own
new reasoning is not loaded or replayed, and no fake native call/output is added;
this is content-only reconsideration, not continuation of that sampled response.
The original unreviewed draft is not a randomized no-extra-inference control.

The preparation proposed four independent A1/B1/B2/A2 responses, mini/medium/25k,
shared $1.20 and zero tools; preparation itself did not authorize or execute collection.
Runtime/task/prompt/tool-surface v35 are unchanged. The standalone collector adds
only the new diagnostic kind to its read-only inspector; prior packet identities
remain immutable and require their recorded implementation for exact revalidation.

All 82 focused draft/source/shared-collector/documentation tests pass in 37.59s,
including four-response fake collection and no new draft-reasoning reads; Ruff passes.
That preparation added no provider/count/Docker/task/evaluator or model-quality result.
See the [operations contract](operations.md#draft-review-pilot-row-43).

## Prior seam: proposal review and public repair boundary characterized

The provider-free audit at `C:\pt\analyses\pl43-proposal-review-boundary` separates
mutation admission from semantic review. Exact source, scope and diff identity are
validated; hypothesis/expected_behavior are model claims, not checked invariants.
The sampled B1 even promises to preserve mode while its code violates the public
mode condition. Optional notes/verification concerns retain authored observations;
they do not independently review a draft, and none was authored in this pilot.

A new scripted CSV regression uses real local gateway/check execution: one read,
three admitted edits, three checks and finish. An earlier assertion first masks a
second declared behavior; each failure is mapped to the public statement, repairs
use post-image evidence without rereading, and journal reconstruction preserves the
first failure. Final submission binds the passing diff. This is a fixture workflow
result, not an LLM self-repair result or execution of any sampled pyfakefs proposal.

No new delivery/action-mask defect explains the sampled proposals. The observed
weakness is constructing and reviewing a candidate before spending mutation slots;
its internal cognitive cause remains unproven. Keep the runtime, task and prompt
unchanged. Next test whether a bounded draft-review instruction improves actual
replacement code beyond a neutral second attempt, without supplying the known
defects/repair. No reviewer call, paid collection or live row is run or authorized.

A separate diagnostic limitation was reproduced: `python -B -c` executes and
returns its traceback, but the inline-source mapper expects the executable directly
before `-c` and leaves the public location unmapped. The task's plain `python -c`
form is unaffected. This limitation is recorded, not fixed or blamed for row43.
All results remain `official=false`; no task acceptance or safety claim is added.
The 56 focused workflow/concern/feedback/documentation tests pass in 32.20s, including
the existing annotation-aware mock through isolated CSV evaluation; Ruff passes.
No full runtime suite or separate mock CLI invocation is newly claimed.

## Prior seam: requirements proximity pilot shows no proposal improvement

The explicitly approved four-response pilot is complete on `d5a411a` as
`run_dev_sample_e54f9963571a4f1d` at
`C:\pt\analyses\pl43-requirements-focus-live`. Four counts and four completed
mini/medium responses cost $0.081974700 under the shared $1.20 cap in 48.434s.
Zero sampled tools, corrections, retries, Docker or evaluator executions occur.
The initial host-review rejection never started a process; explicit approval to
transmit the historical public context and opaque reasoning to the official API
preceded the first actual invocation. Both the invocation and transmission grants
are consumed; no additional sampling, feedback rollout or live row is authorized.

Anonymous static review was frozen before unblinding at
`C:\pt\analyses\pl43-requirements-focus-review`. Both A samples and both B samples
propose the same two public contradictions: they create a missing final directory
then raise EEXIST because it now exists, and use leaf mode for intermediate dirs.
A2 additionally omits the real docstring from its exact old_text anchor. All four
memory_update values are null. None of these proposals is applied: gateway/check
and task-acceptance outcomes are NOT_RUN, not four executed test failures.

A counts 49,648 tokens and B 50,210 (+562). Outputs complete at 838–2,489 of 25,000
tokens; every ordered request and continuation verifies, with all 13 historical
reasoning items preserved in each request. The 991 protected files and all 17 live
result files remain unchanged during review. Cache warmth differs, so per-arm cost
is not an efficiency result. Task acceptance/safety are NOT_RUN, official=false.

Repeating public requirements nearer the decision does not improve these four
proposals. The observed gap is translating requirements into implementation rules
and checking the proposed code, not a demonstrated new delivery/memory-storage
defect. Old source docstrings also describe applying mode to parents, while the
public check distinguishes parent and leaf modes; this is a potential conflicting
cue, not proof of the model's reasoning. No inference about encrypted-state anchoring
or general model ability follows from this single checkpoint. Do not adopt the
repetition field by default; next investigate public-requirement/proposal validation,
without injecting a repair or treating more prompt text as a demonstrated fix.

## Prior seam: first-decision requirements proximity pilot prepared

The provider-free packet at `C:\pt\analyses\pl43-requirements-focus` fixes row43's
pre-first-mutation turn 14. Control A reconstructs the historical canonical request
hash exactly (`511b1fc7`), despite the different historical runtime. B changes only
the latest state's `public_requirements_at_decision`: verbatim public issue and all
visible check declarations already present in the input. The other 54 input items,
13 encrypted reasoning items, source history, optional notes, tools/order, model,
medium reasoning and 25k ceiling are unchanged. Full requests are 253,546/256,004
bytes; no fresh token count is claimed.

The standalone collector proposes four independent next responses A1/B1/B2/A2,
zero sampled tool executions and one shared $1.20 cap. No response is chained,
corrected, retried or evaluated privately. Anonymous static action review is fixed
before sampling; first accepted mutation, repair and submission remain unobserved.
This tests proximity plus repetition/extra bytes, not pure memory use or attention.
Two samples per arm at one failure-selected checkpoint cannot establish agent quality.
No default runtime, task, prompt or policy is changed. Collection has not run;
exact packet/collector/task/model/credential/sample-count/cap/output-root approval
is still required. See the [operations contract](operations.md#requirements-proximity-pilot-row-43).

All 95 focused sampler/shared-collector/documentation cases pass in 45.108s, including
four-response fake collection with zero tool executions; Ruff passes. Two read-only
validations produce identical output. Runtime bytes remain unchanged, so no full
runtime suite or runtime mock smoke is newly claimed. The completed owned pytest
root is recycled with content verification and a restoration mapping; reports remain
under `C:\pt\validation`. Provider/count/Docker calls are zero.

## Prior seam: first-mutation public trace audit

The 2026-09-11 read-only audit at `C:\pt\analyses\pl43-first-mutation` traces B2's
inherited implementation back to row43's first mutation, turn 14 / decision seq151.
All 22 saved inputs, contexts and encrypted continuations verify; all 21 request
extensions preserve previous items and native call/result order. The source and B2
journal chains verify, their first 20 decisions/diff bindings match, and 70 read
source files remain unchanged. The historical runtime differs from current v35;
the audit uses stored inputs, not an assumed historical request reconstruction.

After 13 inspections, the first mutation had the public mode assertions and 350
observed source lines, including helper normalization, permission and platform
behavior. Read/search/probe remained available, with 27 model / 87 tool actions and
four mutations left. Output completed at 1,860 of 25,000 tokens. All 22 decisions
used memory_update=null: source history was retained, but no working note or
verification concern was authored. No new delivery, continuation or memory-storage
defect is demonstrated, so runtime, prompt, tools and task bytes are not changed.

The first edit replaced delegation with a broad traversal algorithm. It discarded
compatibility behavior and introduced false EEXIST and uniform-mode errors. The
agent correctly repaired those two direct public failures; the weaker behavior was
generalizing the rule to untested path combinations, not total inability to read
feedback. B2 later restored no-parent delegation without revisiting traversal's
remaining assumptions. This is public behavioral evidence, not internal-reasoning
access or attribution of a private evaluator failure.

The first-mutation input contains 226,142 serialized bytes / 49,648 recorded input
tokens. Accumulated state and optional-note usability remain hypotheses, not proven
causes; byte shares do not measure attention or token shares. The system prompt was
already identical to current guidance about behavior ownership and unverified
assumptions. Next compare one small evidence-to-decision change from the same
pre-mutation public checkpoint; do not inject the operator solution, add mandatory
tools, or claim that more prompt text alone fixes this. No such comparison was run.
The audit executes no provider/count, Docker, task, probe, check or evaluator.
Only analysis/docs are added; official=false/claim_eligible=false remains unchanged.
Three documentation tests and Ruff pass. No full runtime suite or mock smoke is
rerun for this documentation-only change; pytest did not create its unused basetemp.

## Prior seam: frozen operator repair passes isolated task acceptance

The separately approved 2026-09-11 evaluation at
`C:\pt\evaluations\pl43-b2-repaired` accepts the exact 49-line operator patch
`sha256:c69bf63cc3a7fc7c91054888501b538c9d7a4314849baabb2c2525c80e120610`.
Task acceptance, public regression, scope and typed evaluation safety are PASS;
failure_class is null. One standard evaluator invocation in one fresh no-hardlink
workspace takes 7.559s. Runtime v35, task v2 and its 50-line limit are unchanged.
No provider/count/probe call, model cost, repair, retry or new live row occurs.

Manifest/task/runtime/image and submitted/applied/checked patch bindings verify;
2,025 protected files, including the original B2 and operator repair, are unchanged.
CAS/journal and execution-policy evidence verify, and owned containers are absent.
The new evaluation ID is `run_dev_operator_b2_repair_eval_20260911`. Historical
operator probes are referenced as source evidence, not relabeled as executions in
this evaluation. The schema-required model field is explicitly a no-model metadata
placeholder; the evaluator and Docker checks are real, not mock task acceptance.
Only aggregate private results are read back; no hidden case or failure detail is
used as an agent hint. Detailed aggregate report and audit are under the new root.

This establishes an accepted implementation within the current task scope, not an
improvement in the original agent. A read-only comparison of B2's last five public
actions shows probe -> mutation -> two checks -> finish. The probe concerns two
no-parent regressions; the mutation restores the old implementation for no-parent
paths, leaving the custom `..` traversal semantics unchanged. Public checks genuinely
pass, so finish was consistent with its gate. All five responses complete, and their
optional memory_update values are null. These observations do not establish context
loss, a disabled tool or output-token saturation as the cause of B2's remaining bugs.

The evidence points to incomplete behavioral verification, especially interactions
between the changed traversal and preserved destination/mode/platform semantics.
It does not reveal the model's internal reasoning. B2 inherited only one remaining
accepted mutation; the operator used three candidates and additional public cases.
Do not treat this as a controlled agent comparison or evidence that all resource
limits are sufficient. Further loop work should test public behavioral questions and
evidence-to-repair decisions, without copying this solution into memory or adding
mandatory tools on this single result. All evidence remains official=false/claim_eligible=false.
Twelve existing evaluator/documentation tests and Ruff pass. Their new owned pytest
scratch is recycled with verified content and an exact restoration mapping; durable
evaluation workspaces and prior roots remain in place. No new full runtime-suite or
mock-smoke execution is claimed. See result.md and original-public-comparison.json.

## Prior seam: separate B2 operator repair passes public validation

The 2026-09-11 repair at `C:\pt\repairs\pl43-b2` preserves the original B2 run,
submission, task v2 and runtime. Three operator-authored candidates use an independent
no-hardlink clone at the audited base. The final `final.patch` changes only
`pyfakefs/fake_os.py`: 48 added + 1 deleted = 49 lines, within the unchanged 50-line
scope. Its hash is
`sha256:c69bf63cc3a7fc7c91054888501b538c9d7a4314849baabb2c2525c80e120610`.

The unchanged, previously frozen POSIX matrix now matches real `os.makedirs` in
30/30 cases (original B2: 18/30). POSIX traversal follows resolved directories,
then validates the final target separately; default parent mode, requested leaf
mode, existing-file rejection and trailing separators remain distinct concerns.
No-parent paths retain the existing implementation.

A separate 24-case public Windows comparison exposed a platform distinction:
Windows may normalize `..` before directory creation, depending on which parents
already exist. Unconditionally applying POSIX traversal side effects is incorrect.
The repair uses Windows parent-existence/recursive creation behavior and preserves
drive-relative paths. Candidate agreement increases from 6/24 to 23/24 to 24/24;
neither the cases nor the task's registered checks are changed to obtain this result.
Native Windows uses Python 3.14.5; fake Windows and the POSIX oracle use 3.12.13.
This is a bounded behavioral comparison, not a cross-version equivalence claim.

Both original public checks pass on the final patch hash; upstream reports
517 passed / 570 skipped. The final four sandbox executions take 11.267s combined.
There are five public probes, four public registered-check executions and one
stdlib-only native Windows case batch across all three candidates. Provider/count
calls and model cost are zero. Private evaluation is NOT_RUN; no private evaluator
input, hidden failure detail or reference patch is loaded or used.

This repairs an operator candidate, not the agent loop: it does not demonstrate
better agent reasoning, memory, tool selection or generalization. Do not back-credit
the original B2 result, inject this patch into agent context, or change the tool mask.
Native macOS, Windows ACL/mode and symlink/junction/network-share behavior remain
unverified. Any private acceptance evaluation is separate work. Detailed public
receipts, candidate history and the downloadable patch are retained with `result.md`;
all results remain `official=false`, `claim_eligible=false`.

Audit verifies all 234 protected original/diagnostic files and runtime bytes,
candidate/check identity, CAS/journal integrity and absence of owned containers.
The new Windows scratch is recycled with a verified restoration mapping; no existing
scratch is touched. Three documentation tests and Ruff pass. Runtime is unchanged,
so no new full runtime suite or mock smoke is claimed.

## Prior seam: independent public diagnosis reproduces B2 semantic gaps

The 2026-09-11 operator diagnostic at `C:\pt\analyses\pl43-b2-public` uses only the
public v2 requirement, B2's unchanged source and an independently authored case matrix.
No private evaluator files, failure details or reference patch are read or used.
One fixed-image public probe compares 30 cases with real POSIX `os.makedirs` on
Python 3.12.13: 18 match and 12 differ. This selected edge-case matrix is not an
agent success rate or a general input-distribution estimate.

The differences cover accepting an existing file with `exist_ok=True`, skipping
the final existing-target error when the path ends in `..`, wrong leaf mode/error
with trailing separators, and wrong destination after repeated separators or a
symlink followed by `..`. Basic traversal/bytes/mode controls, the four tested invalid
parent cases and two terminal-dot cases agree; not every suspicion is a defect.
The direct code problem is incomplete filesystem semantics in the hand-written
parent-traversal branch: raw token position, existence and lexical dirname are not
equivalent to the actual leaf, directory type and resolved parent. Many upstream
cases continue through the unchanged no-parent branch, leaving these combinations
untested. Memory/prompt causation and any exact hidden-failure mapping remain unknown.

The probe completes in 6.328s with no truncation; its zero exit means the comparison
ran, not that B2 passed all cases. Source/diff, journal/CAS and policy receipts verify;
219 prior files and runtime bytes are unchanged and the owned container is absent.
There are zero provider/count/private-evaluator calls and $0 model cost. No patch,
runtime/task change, private reevaluation, Docker startup/pull/build or paid row occurs.
Windows/macOS native behavior is not newly verified. See `result.md` and `audit.json`.

Next implementation should separate traversal side effects from final-target checks
and verify existing directory/path primitives before reusing them; do not assume a
recursive wrapper alone fixes lower-level path normalization. Freeze public behavioral
cases before repair, preserve task v2, and use a separately approved versioned successor
if registered checks change. No tool mask, mandatory probe/memory or budget expansion
is justified by this diagnostic. All results remain `official=false`, `claim_eligible=false`.
Three documentation tests pass in 0.058s and Ruff passes. No new full runtime suite
or mock smoke is claimed; the requested pytest basetemp was not needed or created.

## Prior seam: B2 submits publicly but fails isolated task acceptance

The separately approved 2026-09-11 operator evaluation is complete at
`C:\pt\evaluations\pl43-b2`; `result.md` and `audit.json` contain the aggregate report
and integrity checks. The exact B2 submission remains the same 39-line patch:
`sha256:0ed4a24551e7a171969b032fd61ccb6bb4c91aba71c522e01b0f17fa0a1e1708`.
Public regression and scope PASS; private evaluation and task acceptance FAIL;
typed safety PASS. The canonical failure class is `PRIVATE_EVALUATION_FAILED`, not
an evaluator exception. The isolated evaluation completed in 7.206s.

One new workspace used a no-hardlink local clone at the original audited base,
then the standard evaluator applied the exact submitted artifact. Manifest/task/
runtime/image, visible/submitted/applied diff and execution-policy bindings verify.
The prior public probe receipt was derived exactly from its durable action event;
no probe was rerun. All 1,835 protected files remain byte-identical and the owned
containers are absent. There were zero provider/count/new-probe calls and $0 model
cost, with no Docker startup/pull/build, repair, retry or normal live row.

This evidence belongs to a separate operator evaluation, not a resumed B2 run.
The original comparison still records `PUBLIC_CHECKS_SUBMITTED` and NOT_RUN private
evaluation; its immutable bytes and scores are not rewritten. B2's public submission
is not task completion. This result neither identifies the semantic cause nor proves
a private-oracle error, harness defect or general probe benefit. Private failures
are not supplied to the coding agent or converted into public repair hints. Further
diagnosis must begin with public requirements and independent public cases; no
mandatory-probe policy or additional model experiment follows from this check.
All results remain `official=false`, `claim_eligible=false`.
Twelve existing evaluator/documentation tests pass in 6.577s; Ruff passes. Runtime
and task bytes are unchanged, so no new full-suite or mock-smoke claim is made.

## Prior seam: post-hoc A1 checks limit the stop diagnosis

`C:\pt\pl43-stop-validity-a` checks the exact previously untested probe-pilot A1
candidate in a fresh external workspace; review/audit are at
`C:\pt\pl43-stop-validity-review-a`. The 48-line diff is unchanged:
`sha256:7a4f5b54b0240f00006d8a975b02a3431cac6af016be0e11fd1686fb3ba5c0c6`.
Traversal passes; upstream reports one macOS broken-link trailing-separator failure,
516 passed and 570 skipped. This is operator evidence, never back-credited to A1.

The prior suggestion that A1 necessarily confused zero edits with zero useful actions
was too strong. `completion_possible=true` is conditional on successful checks, not
a correctness prediction. With an actually failing candidate and no mutation left,
stopping can be rational. The code's remaining failure is now observed; whether the
model predicted it or reused a historical verdict remains unknown. Its stop wording
was not an executed current-diff check, and the new failure list contains only macOS,
not both platform failures asserted in the stop. Do not score every unchecked stop
as a memory/policy defect or adopt an obligatory check/stop prohibition from this case.

One exact operator candidate restoration and two registered checks complete in
19.899s, with zero provider/count/probe calls and $0. The original task, limits and
image remain fixed; Docker was already running, with no startup/pull/build. No paid
resume/retry, new A/B or normal row is performed. Private evaluation/task acceptance/
aggregate safety/submission remain NOT_RUN and `official=false`.
Audit verifies the journal, 62 CAS objects, candidate/check identities, two owned
containers cleaned up and absent, 7,033 preserved prior files and 199 unchanged new
execution files. Existing recheck/projection/docs tests pass 40 cases in 43.403s;
Ruff passes. Runtime is unchanged, so no new full-suite/mock claim is made.

## Probe-first comparison collected; no default policy adoption

The bounded comparison completed at `C:\pt\pl43-probe-live-a`; analysis and read-only
audit are at `C:\pt\pl43-probe-review-a\result.md` and `audit.json`. Ordinary A submits
0/2; probe-first B submits 1/2 after both public checks pass. This is one checkpoint
with two samples per arm, not demonstrated general probe benefit or task acceptance.
No new runtime prompt/mask, mandatory probe policy or normal live row follows.

| Branch | New responses/actions | Final diff | Observed outcome |
|---|---:|---:|---|
| A1 ordinary | 4/4 | 48 lines | AGENT_STOPPED without current-diff checks |
| B1 probe-first | 6/6 | 43 lines | Upstream macOS failure, then LIMIT_REACHED |
| B2 probe-first | 5/5 | 39 lines | Both public checks PASS; PUBLIC_CHECKS_SUBMITTED |
| A2 ordinary | 2/2 | 50 lines | Upstream macOS failure, then LIMIT_REACHED |

There are 17 counts/completed responses/actions, $0.584686950 recorded cost and
233.059 collector seconds. Full 25k admission is preserved; output tokens range
176–3,748. No cap/response/deadline censoring, incomplete response or paid retry occurs.
Both B branches author and execute one probe, then return to the ordinary loop.
B2 reproduces both platform errors and delegates paths without `..` to the original
implementation, limiting the new traversal logic's scope. Its 39-line checked and
submitted diff is `sha256:0ed4a24551e7a171969b032fd61ccb6bb4c91aba71c522e01b0f17fa0a1e1708`.
Upstream reports 517 passed/570 skipped; traversal also passes. Private evaluation,
task acceptance and aggregate safety remain NOT_RUN, with `official=false`.

B1 probes only Windows, then restores platform-specific handling but still uses an
unprocessed trailing-separator operand for macOS link checks. B1/A2 each report one
macOS failure (516 passed/570 skipped); accepted mutation exhaustion then legitimately
blocks further repair. A1 instead voluntarily stops on an untested candidate while
`run_check`, two NOT_RUN checks, null current failure, explicit recheck guidance and a
viable three-call completion path remain in its actual input. Its current failure
claim had no new check in the agent trajectory. The later operator check above
confirms a remaining failure without showing how the model reached that judgment.
All 17 memory updates are null. Native input/continuation delivery passes audit, but
note use or the model's internal attention is not established. Review useful probe
questions, small behavior-preserving repairs and current-diff rechecks separately;
do not infer that more tool restrictions or duplicated guidance would solve this.

The public operator counterfactual is complete at
`C:\pt\pl43-repair-check-review-a\result.md`. Removing trailing separators from link
operands repairs cleanup but still leaves an empty path component and EEXIST; using
the same stripped operand for component splitting also passes traversal and upstream
checks (517 passed / 570 skipped) within the unchanged 50-line scope. This establishes
a feasible public repair, not agent success, private task acceptance or probe benefit.
The operator's patches, probes and diagnosis are not supplied to the next model inputs.

The preceding preparation uses `diagnostics.probe_first_view`.
Both arms start from row 43's frozen pre-turn-21 current public failure. A keeps the
ordinary loop; B changes only the first probe phase's `tool_choice` to the official
Responses forced-function form for `run_probe`. The model must author its own probe.
The complete native input, encrypted reasoning, sources, optional notes, tool schemas
and order, model/medium/25k settings and inherited budgets remain byte-identical.
No production tool mask, prompt, task or runtime default changes; runtime stays v35.

The frozen packet is `C:\pt\pl43-probe-first-design-a`; the preparation audit is
`C:\pt\pl43-probe-first-prep-a\audit.json`. A is the exact 424,331-byte original;
B is 424,359 bytes. Both retain 83 input items, including 20 encrypted reasoning
items. Read-only validation succeeds twice with 5,955 protected files unchanged.
These are serialized-byte and preservation measurements, not counted-token savings.

The separate collector contract specifies A1/B1/B2/A2, at most
eight new responses per branch and one shared $1.20 cap. Probe/correction work consumes
the same inherited budgets. B returns to the ordinary loop after native feedback
from its first probe attempt, including a failed probe; protocol corrections remain
bounded. Review question usefulness, interpretation, repair and recheck/submission
separately. Preserve normal admission, replay and uncertainty stops; cap/response
censoring is not an uncensored task failure. This is not a default mandatory-probe policy.

The original preparer and frozen design remain `PREPARED_NOT_EXECUTABLE` with
`collector_implemented=false`; their bytes are not migrated. The subsequent proceed
request implements the separate `diagnostics.probe_first_rollout` collector. Its new
plan binds the frozen design, all diagnostic dependencies and runtime hashes. It
reuses the existing ordinary request builder and shared JIT cost driver, but not the
old B source-inlining intervention. Only the probe phase changes tool choice; its
actual mask also governs bounded protocol correction. No operator hints are added.

Recorded decisions/batches are reconciled before a new dispatch or horizon stop.
Probe execution failure releases the phase; cleanup uncertainty stops all branches.
A completed probe/check result is replayed, but an execution without its durable
result stops as `TOOL_EXECUTION_UNKNOWN` rather than running again. Mutation recovery
uses the exact admitted candidate; other-file drift is rejected. Missing provider
dispatch completion or known usage without a recoverable decision stops without
another provider call. Terminal reconciliation is read-only; the CLI has no paid
resume and refuses an existing result root. This is not normal `dev --resume-run-id`.

The latest proceed request consumed this separate four-branch comparison once.
The earlier preparation/tests remain provider-free synthetic evidence, distinct
from the now collected model trajectories. This is not a new normal live row.

The executable plan is frozen at `C:\pt\pl43-probe-collector-plan-a`; audit and
handoff are at `C:\pt\pl43-probe-collector-review-a`. Both initial request hashes
match the original A/B design exactly, repeated plan validation is byte-identical,
and 6,065 existing evidence files were unchanged at implementation handoff. The later
`C:\pt\pl43-probe-preflight-a` verifies tracked-clean implementation/task inputs,
already-running Docker, pinned local images and execution-day official pricing.
The live review verifies 313 CAS objects, four journal chains, native prefixes,
continuations, exact initial A/B requests, phase release, usage and shared-cap
admission. All six owned probe/check containers have confirmed cleanup and are absent.
6,174 prior protected files and 849 live files remain unchanged. No Docker startup,
pull/build, private evaluation or normal runtime change was performed.
The documentation update passes all three layout/link tests, Ruff on `patchloop tests`
and `git diff --check`; the unchanged runtime's full suite/mock smoke is not rerun.

Collector validation: 178 cases pass in two overlapping groups (74 in 55.73s and
104 in 69.90s), plus Ruff. The new cases exercise first-probe release, ordinary-loop
repair/check/finish, shared-cap uncertainty, incomplete correction, candidate replay,
native artifact tamper and missing execution receipts. No new model samples are used.
Normal-runtime mock `run_dev_e2ee0c2be6ec45ea` at `C:\pt\pl43-probe-collector-smoke-a`
reaches mutation/check/finish/isolated EVALUATOR_PASS in 4.54 command seconds: four
mock turns/five actions, one mutation, zero cost and safety NOT_RUN. Keep this smoke
separate from diagnostic task acceptance, which is NOT_RUN. Runtime code is unchanged;
the full normal-runtime suite is not rerun. `uv` rebuilt the local `.venv` for Python
3.14.5 during validation; the declared `dev` extra restored pytest/Ruff. No `.env`,
lockfile, task or historical run changes were made.

## Sequential reliability review fixes (provider-free)

The 2026-09-09 review is recorded externally at `C:\pt\pl-system-review-a\review.md`.
The subsequent implementation request authorizes local fixes and provider-free
validation, not another paid row or Docker execution. These edge-case defects are
not established causes of row 43's problem-solving failure.

First fix: v35 preserves owned-container cleanup uncertainty even when the launcher
raises. Confirmed cleanup preserves the original exception; unconfirmed cleanup
becomes typed `SANDBOX_CLEANUP_FAILED`, retains policy/hash evidence through the
gateway, and stops further execution. Mocked launch/cleanup/interruption and durable
replay tests pass with existing cleanup/deadline cases: 14 passed in 4.05s at
`C:\pt\pl-fix-cleanup-green-b`; focused Ruff passes. No real Docker/provider call.

Second fix: completed evaluation now has one durable receipt, validated and finalized
without entering workspace/provider/sandbox execution on resume. PASS, FAIL, evaluator
error, cleanup uncertainty and deadline outcomes preserve their original artifacts,
message, active time and repetition-stop decision. Two crash boundaries, changed second
verdict prevention, artifact tamper and uncertainty precedence pass 22 cases in 61.93s
(`C:\pt\pl-fix-eval-green-b.xml`). This closes the after-`evaluator_finished` crash gap,
not the earlier uncommitted-evaluation window. Existing run bytes are not migrated.

Third fix: mutation-specific recovery forecasting uses the shared B/P calculation
on the immediate attempt, including its initial rejection. The independent 2,728-state
oracle found 434 prior two-call omissions; corrected forecasts match all states while
minimum admission remains unchanged. New and existing workflow/budget/feedback cases:
93 passed in 10.81s (`C:\pt\pl-fix-budget-green-a.xml`). No new action gate or cap increase.

Fourth fix: readable mixed LF/CRLF notes now use the same observational normalization
as source reads. Raw hashes, exact rebinding, stale/ambiguous expiry and the stricter
mutation newline policy remain unchanged. New tests first reproduce five mixed-EOL
failures; the fix plus source/note lifecycle regressions pass 48 cases in 14.27s
(`C:\pt\pl-fix-notes-green-a.xml`). This fixes storage/lifecycle, not optional note non-use.

Fifth fix: registered-check output now uses bounded streaming retention, preserving
the existing stdout-first byte/complete-line format, separate trace-report channel and
exit verdict while discarding excess output. Process/pipe/container uncertainty still
stops execution and carries typed policy evidence. Capture and surrounding regressions:
171 passed in 12.50s (`C:\pt\pl-fix-capture-green-d.xml`), including harmless local
flood/timeout and mocked Docker cases. Independent legacy-format comparison matched
2,500 inputs; no new concrete defect was found in that cross-review.

Sixth fix: main repository/Git operations receive finite timeouts and remaining active
time, with file-backed exact output to avoid the Windows post-timeout pipe-drain path.
The row clock now starts before workspace/preflight; already finished mutation/check
metadata has a bounded recovery tail, and submission reuses the admission Git identity.
Uncertain Git interruption stops all repetitions; it does not claim descendant-tree
cleanup. New deadline/receipt/reconciliation cases: 23 passed in 10.98s, plus 27 existing
resume/evaluator/mock cases in 31.80s. Whole filesystem operations remain cooperative,
and invocation task/envelope hashing remains outside the row clock. The tool surface
stays v35 with these semantics hash-bound; arguments/order, limits and task bytes stay fixed.

Completed-evaluation recovery also verifies explicit typed completed-check leaf CAS
references, not only their parent provenance. The two new missing/tampered cases were
first reproduced and then passed; final frozen full-suite verification covers this
refinement together with all six fixes.

Final frozen validation on `b0da0e7`: Ruff PASS; all 63 test files pass with
**1,108 passed / 4 opt-in Docker tests skipped** at `C:\pt\pl-fixes-final-b`.
The nine groups take at most 115.51s each; the full three-worker test/preservation
phase takes 225.594s, not under two minutes. The first full attempt exposed old
synthetic mock signatures and a stale identity expectation; test-only corrections
pass 91 focused cases before this complete rerun. Runtime and protected state stay fixed.
Mock `run_dev_5efcad90f9ca4cdc` at `C:\pt\pl-fixes-smoke-a` reaches mutation, visible
check, finish and isolated evaluation in 4.02 command seconds: four mock turns/five
actions, one accepted mutation, task acceptance PASS, safety NOT_RUN, zero cost.
Checked/submitted/isolated-applied diff identity matches. Existing 1,249 task/history
files, 168 run/lock files, 3,446 CAS artifacts, prior diagnostic roots, `.env`, user
`AGENTS.md` and all prior untracked entries remain unchanged. Full implementation
notes: `C:\pt\pl-fixes-review-a\implementation.md`. No paid/Docker/live row was run.

Design follow-up is kept separate from those confirmed defects. The offline
`diagnostics.current_source_view` prototype preserves the full native prefix and
selected current sources, but makes their bodies inline in only the latest view.
Its 26 cases pass in 0.85s. Frozen row-43 A retains all 385 selected lines, 82 prior
items and 20 encrypted reasoning items; request size grows 424,331 -> 440,593 UTF-8
bytes (`C:\pt\pl-fix-source-view-a`). No model-effect/token-saving claim or default
context change follows. An external synthetic edit-unit comparison confirms the
separate-edit versus wide-anchor tradeoff, not a cause of row 43's failure. Existing
mutation schema/counting and optional notes remain unchanged; neither diagnostic
authorizes or implements paid collection. The original fresh-state/order pilots
remain immutable evidence, not runtime defaults.

## Current-source presentation comparison completed

The separately authorized A/B follow-up is complete on collector `29eb5fb`, with
unchanged v35 runtime: four fresh short branches, 12 counts/completed responses,
12 tool actions, **$0.387835350**, 204.030s, zero submissions/private evaluations.
Evidence: `C:\pt\pl43-source-live-a\result.json`; analysis and independent audit:
`C:\pt\pl43-source-review-a\result.md` and `audit-v2.json`. This is not normal row 44.
No branch hits the shared $1.20 cap or eight-response bound; maximum output is
5,503 tokens. First A/B inputs count 91,222/94,639 tokens (424,331/440,593 bytes).

A1 searches twice, gains 79 new helper lines, mutates, then stops. A2 and B2 each
recover one scope rejection, mutate, then stop. Their current checks are NOT_RUN,
current failure is null, `run_check` is available, and the three-call minimum
completion path still fits. The agent nevertheless treats the previous failure as
current. A2 explicitly repeats a Windows failure its new patch actually repairs.
B1 mutates then runs regression: 21 failures include calling a filesystem helper
on the wrong object (`self.ends_with_path_separator`). After this observed failure,
zero remaining accepted mutations correctly causes pre-dispatch `LIMIT_REACHED`.
Distinguish that terminal from the other three voluntary untested stops.

Separate post-hoc operator checks in `C:\pt\pl43-source-operator-a` run no provider
calls and never modify the live branches. A1/A2/B2 all pass the public traversal
contract; upstream respectively has 3/1/1 failures. A2/B2 repair the two Windows
cases but retain the macOS case. These six checks are not agent verification or
submission credit. All 12 new memory updates are null. Source-body inlining alone
has no demonstrated completion benefit; two samples per arm cannot establish a
general effect. Do not describe A1's novel supporting coverage as duplicate search.

Next candidate: a single-factor test of clearer post-mutation state communication,
separating historical failures and unavailable further mutation from the still-open
check/finish path. The nested mutation-horizon warning may compete with the overall
completion signal, but this cause is unproven. No default inlining, memory mandate,
new hard gate, runtime change or further paid draw is implied by this result.
Audit verifies native prefixes/continuations, 292 branch CAS objects, billing,
seven owned-container cleanups and unchanged historical/task/run/credential bytes.
Acceptance/safety remain NOT_RUN, `official=false`, `claim_eligible=false`.

### Completion-signal follow-up: completed, no observed action difference

The bounded comparison is complete on collector `5df509a`:
`run_dev_sample_a746407355254569`, eight counts/eight completed responses,
**$0.203554800**, 47.671 active seconds, zero tool executions. Result and audit:
`C:\pt\pl43-completion-live-a\result.json` and
`C:\pt\pl43-completion-review-a\result.md` / `audit.json`.
Each arm selects three stops and one upstream check; all four matched checkpoints
choose the same tool in A and B. The sole check-selecting checkpoint is C4 (source
A2). C2 (source B1) originally checked but both fresh responses stop; C4 originally
stopped but both fresh responses check. Identical original inputs can yield different
selections, so these single samples cannot establish a general treatment effect.

All six stop responses describe upstream failure as current despite NOT_RUN/null
current-failure state and available checks. This is an unsupported current-check
verdict, not evidence of token exhaustion, a missing check tool or an exhausted
minimum completion path. Outputs use 296-613 tokens; each treatment removes 158 bytes
and 31 counted input tokens. All eight memory updates are null, with native/encrypted
history retained. The latest-field-only explanation is not supported; do not adopt
the omission, force notes, prohibit stops or add another equivalent instruction.
How historical verdicts are weighted against the current candidate remains unisolated.
An unchecked stop alone is not proof of a memory or action-policy bug: the model may
predict failure from source and rationally stop when no repair remains. Distinguish
such predictions from observed check results; the public wording does not resolve
the internal cause.
The four related checkpoints and one sample per condition do not prove no effect.

Anonymous review precedes unblinding. Separate audit verifies exact paired requests,
native prefixes/continuations, billing, 34 CAS objects and 5,268 protected files.
Task acceptance/safety remain NOT_RUN; this is not row 44, submitted code, executed
verification or a runtime improvement. The following preparation/validation details
remain the experiment's input contract, not another unconsumed collection authority.

Inspection of the actual final inputs finds more than correct status fields:
`completion_guidance` already leads with `run_check`, and `pending_recheck.guidance`
explicitly says the failure is historical and zero edits does not prevent checks or
submission. This is not a missing-instruction bug. Do not add equivalent prose or
claim another prompt sentence would have prevented the stops.

`diagnostics.completion_signal_view` prepares/validates a narrower one-field ablation.
For a nonempty candidate with zero remaining mutations, current nonfailed checks and
an available completion path, control A preserves the exact original request. B only
omits the latest `action_horizon.mutation_completion_horizon`. The explicit zero-edit
counter, completion/check guidance, pending historical failure, sources, notes, tool
schemas/order/settings and full native prefix remain exact. Earlier copies of the
forecast remain historical; this does not reset reasoning or remove all old warnings.
Eligibility is a diagnostic-input filter, never a runtime tool gate.

Four paired inputs from the preceding A1/B1/B2/A2 checkpoints are frozen at
`C:\pt\pl43-completion-view-a`. Each B is exactly 158 UTF-8 bytes smaller, with
unchanged prefix lengths 94/86/90/90 and reasoning-item counts 23/21/22/22. This is
not a counted-token saving or a model-effect result. All four still recommend the
same public check. The read-only preparation verifies 5,254 protected files unchanged.
Focused projection/completion/documentation tests pass 72 cases in 8.95s, plus Ruff.
Existing source/native rollout regressions pass 47 more in 68.32s; result-doc tests
pass again. Mock `run_dev_06e51698c0d640a6` at `C:\pt\pl43-completion-smoke-a` reaches
mutation/check/finish/isolated evaluation: four mock turns, five actions, task
acceptance PASS, safety NOT_RUN and zero cost. That is not a model treatment result.
The unchanged normal-runtime full suite is not rerun for this diagnostic-only change.
Normal runtime/tool surface stays v35; no default policy, schema, model, memory,
collector execution or paid authority changes. This module exposes only prepare and
validate, with zero provider/count/tool calls. `PREPARED_NOT_EXECUTABLE` is not a
completed behavioral comparison; outcome claims require a separately bounded collector.

The subsequent proceed request authorizes one bounded next-response comparison, not
another normal row. `diagnostics.completion_signal_sampler` revalidates these four
frozen pairs against their native-input/count journal events before loading credentials.
Schedule: C1 A/B, C2 B/A, C3 A/B, C4 B/A, with C1-C4 mapped to source A1/B1/B2/A2.
Maximum eight responses, one per checkpoint/arm; no sampled tool execution, chaining,
correction, judge call, retry/resume or private evaluation. The original model snapshot,
medium reasoning, encrypted history, 25k output and exact `.env` path remain fixed.
The shared $1.20 cap is admitted just in time: fresh count plus full 25k output before
each dispatch. No future trajectory is guaranteed; an uncollected cell is censored,
not an agent failure. Other samplers retain their original future-reservation policy.
New packet/sampler hashes bind this policy; previous diagnostic bytes are not migrated.
Normal runtime and task bytes are unchanged; collection is now complete as above.
Provider-free validation passes 29 new cases in 12.07s and 139 projection/collector/
documentation regressions in 62.88s, plus Ruff. Mock `run_dev_ca8ad90fdf494637`
at `C:\pt\pl43-completion-dev-smoke-b` reaches isolated EVALUATOR_PASS in 3.97 command
seconds, with four mock turns/five actions, task acceptance PASS, safety NOT_RUN
and zero cost. The unchanged normal-runtime full suite is not rerun.

## Authority

The earlier eight-response/zero-tool completion-signal comparison
is complete under its shared $1.20 cap. Do not repeat it or infer row 44, a second
collection, Docker startup/image operations, sampled tools or normal-runtime changes.

The current-source presentation A/B approval has been consumed by the completed
comparison above; it is not normal row 44 or authority for another paid draw.
The initial Docker-unavailable preflight is
preserved at `C:\pt\pl43-source-preflight-a\result.md`. The user's subsequent explicit
startup request resolved that blocker (`C:\pt\pl-docker-start-20260910-a.md`); no image
pull/build or data reset occurred. One real registered-check/probe smoke passes in
3.75s (`C:\pt\pl43-source-docker-a.xml`) with confirmed cleanup, no provider calls.

`diagnostics.current_source_rollout` connects the frozen row-43 pre-turn-21 request
to four fresh short rollouts, A1/B1/B2/A2. A uses normal source references; B inlines
only selected source bodies in each new current-state view. Earlier native items,
ciphertext, schema order and settings stay intact. Source v34 and executing v35 are
bound separately; this is not old-run resume or migration. Each branch inherits
20 remaining model calls, 80 tool actions, one accepted mutation and 1,601 active
seconds; the diagnostic additionally caps new responses at eight per branch.
All branches share one $1.20 ledger, a 1,800-second experiment deadline and zero
SDK retries. Full-25k-ceiling JIT admission can censor the comparison; no complete
trajectory reserve is claimed. Private evaluation is not run. Compare new inspections,
accepted mutations, complete public check results, submission, calls and cost; small
failure-selected samples do not establish general agent quality. The normal runtime
is unchanged. Collection status and measured outcomes must come from a fresh result,
not preparation or mock artifacts.

Collector validation: 76 current-source/native-rollout/documentation cases pass in
67.64s at `C:\pt\pl43-source-tests-final-a.xml`; Ruff and whitespace pass. These
include real frozen-checkpoint hydration without dispatch, exact first A/B inputs,
native wire-prefix/ciphertext preservation, mock mutation/check/finish, six crash
boundaries, four-branch uncertainty stops and full-ceiling cap admission. Earlier
test-only failures were a tiny-fixture reference assumption and an invalid synthetic
stop code. No runtime fix or policy change was needed. The v35 runtime hash remains
the fully validated one; the full runtime suite is not rerun for this diagnostic-only
change. Historical source/run/CAS/task/owned-file hash checks remain clean.

Mock execution carries no provider authority. One exact live `patchloop dev`
invocation authorizes only its declared `dev-train` task, model, credential file,
repeat count, and positive total cap. It never authorizes an image pull/build,
another task, an automatic retry after uncertainty, or a confirmatory claim run.

Repository policy alone never initiates paid work. The forty-three live observations below
were separately authorized. None authorized an image pull/build, automatic
Docker startup, transport retry, or additional row.

The user's latest exact normal-row approval authorized the now completed
[row 43](#latest-live-observation-row-43-partial-repair-and-voluntary-stop)
once on v34: v2 task, gpt-5.4-mini-2026-03-17, medium, root .env, repeat 1,
$1.20 total cap, probes enabled, new run in `C:\patchloop-state`.
Earlier exclusions remain scoped to their historical receipts. The v34 local-only
implementation did not authorize this row; the separate live approval is consumed.
No row 44, paid retry/resume, historical candidate execution or further sampling is authorized.

The subsequent implementation-only go-ahead completed the [failure-order collector](#failure-order-collector-implemented-no-paid-execution).
The user then explicitly instructed execution without another approval request,
authorizing that prepared four-response/$1.20/zero-tool pilot by reference. It is now
[collected](#failure-order-comparison-four-responses-collected), not a new normal row.
No further samples, tool-feedback rollout, retry/resume or runtime change is implied.

The six-response medium/high comparison on three frozen row-39 inputs is now collected.
It executed no selected tools and is not row 40. See [the pilot findings](#frozen-next-action-comparison-six-responses-collected).
No default-effort change, further paid sampling or new live row is authorized.
The [fresh-state comparison preparation](#prepared-fresh-state-comparison-not-executed)
and [four-response collector](#fresh-state-collector-implemented-no-paid-execution) are complete.
The user's subsequent exact approval by reference authorized the now
[collected four-response comparison](#fresh-state-comparison-four-responses-collected).
No further paid samples, task execution or new live row are authorized.

The user's subsequent exact approval by reference authorized one shared-$1.20
tool-feedback follow-up of all four existing responses. That experiment is now
[complete](#four-seed-short-rollout-completed): ten new responses, fifteen tools,
$0.542493150, and no submitted branch. Both fresh-state branches repaired the original
four regression failures but introduced two new ones. That approval did not authorize
further paid execution, a default-context change, retry/resume or normal row 40. See also
[the frozen follow-up contract](#four-seed-short-rollout-preparation).

## Failure-order comparison: four responses collected

Commit `08ec618f` collects `run_dev_sample_36bef4eebfaa4954` at
`C:\pt\pl43-order-live-a`: SAMPLES_COLLECTED, four immediate input counts and four
completed responses, **$0.119271000** known cost under the shared $1.20 cap,
**37.890s** active time, zero tools/retries/corrections. Task acceptance and safety
remain NOT_RUN; `official=false`, `claim_eligible=false`. This is not row 44.
Official OpenAI Docs pricing for the pinned snapshot was reviewed on execution UTC
date, and the registered rate hash matched. Both arms count 91,222 input tokens.

The frozen pre-turn-21 input differs only in the latest failure-summary order.
Anonymous review was recorded before unblinding:

| Arm | First independent response | Second independent response |
| --- | --- | --- |
| A: original order | Combined macOS/Windows repair proposal; static complete diff 54/50 lines | Search the named macOS test, with intent covering both failure classes |
| B: reordered summary | The same named-test search, with intent covering both failure classes | Search wrapper helper usage, focusing on macOS |

A1's old text matches delivered current source. Its proposed code addresses both
reported mechanisms, but text-only reconstruction from the canonical public diff
gives 53 additions plus one deletion, four lines over scope. This is not an observed
gateway rejection or executed semantic result. The three searches remain unexecuted;
do not call them task failures or a repeated search loop across independent samples.
All four note updates are null, without a memory treatment or storage failure.

No clear ordering benefit is observed. The unchanged original input can already
yield a combined repair; information loss or compulsory first-item selection is not
established. The actionable observed weakness is integrating all failure classes
with the complete patch constraint, not a reason to add another gate or sort policy.
Two draws per arm do not estimate a causal ordering effect or whole-run success.
Earlier native summaries/stdout still retain their original order, so this tests only
the latest card. All outputs complete below 3,970 tokens; no saturation is observed.
Different cache hits make per-arm cost unsuitable as an efficiency comparison.

Read-only review at `C:\pt\pl43-order-review-a` verifies 22 journal events, 12 CAS
objects, four exact ordered requests and encrypted continuations, independent cost
arithmetic, and unchanged collected bytes. `.env`, user-owned `AGENTS.md`, 1,249
task/history files, 51 runtime/diagnostic files, 168 prior run files, 3,446 prior
artifacts, earlier reviews/designs and 175 untracked entries remain unchanged.
Only current result documentation changes; no candidate, task, check, Docker or
evaluator execution occurred. Documentation tests and Ruff pass; the frozen runtime
suite/mock is not repeated for this result-only receipt. No default ordering/memory
change, further paid work, tool rollout or normal row 44 follows from this pilot.

## Failure-order collector implemented: no paid execution

The read-only follow-up at `C:\pt\pl43-decision-a` freezes row 43 immediately before
turn 21. It confirms delivery of all three failure rows and the relevant helper
source; it does not establish why the model chose a partial repair. The new
`diagnostics/failure_order_sampler.py` connects that pinned audit to the existing
one-response collector, outside the normal agent loop.

The prepared design at `C:\pt\pl43-order-design-a` has two arms: original input (A)
and only the latest state's failure-summary rows permuted `[1,2,0]` (B). Both retain
the same 83 input items, 20 encrypted reasoning items, native tool receipts, older
state views, source, budgets, tool-schema order, medium reasoning and 25k output
ceiling. Each full request is 424,331 UTF-8 bytes; these are not token counts.
The proposed schedule is A1/B1/B2/A2, four independent next responses and zero
selected-tool executions. Reviewer labels and later decisions never enter requests.
This small, failure-selected pilot tests sensitivity to this presentation change;
it cannot establish whole-run quality or justify a permanent sorting rule.

Local verification passes 161 relevant regressions, including 33 new cases, in
71.99s and 37.58s groups; Ruff and documentation checks pass. The actual frozen
requests also pass fake collection at `C:\pt\pl43-order-smoke-a`. Its four adapter
responses/counts and recorded cost are simulated, not paid evidence. Separate mock
`run_dev_ccc20ba4bacc4efa` reaches mutation, check, finish and isolated EVALUATOR_PASS
at `C:\pt\pl43-order-dev-smoke-a`, acceptance PASS / safety NOT_RUN, with zero cost.
The unchanged normal runtime's full suite is not rerun for this diagnostic-only
change. Detailed receipts and preservation checks are at `C:\pt\pl43-order-wire-a`.

Normal runtime v34, task packages, `.env`, user-owned `AGENTS.md`, historical files
and prior external state remain unchanged. Prepare/validate load no credential and
make no count/provider/tool call. Collection requires new exact four-response/zero-tool
approval, packet/collector identities, credential path, $1.20 total cap, fresh pricing
review and a new result root; see [operations](operations.md#failure-order-pilot-row-43).
The 272,000-token per-request limit is an enforced admission ceiling, not a guessed
count. At that implementation checkpoint no paid collection, Docker execution,
retry/resume or row 44 was authorized. The later separately instructed pilot is above.

## Latest live observation: row 43 partial repair and voluntary stop

The separately approved v34 run `run_dev_9b91e06c13ff4bd3` ends **AGENT_STOPPED**:
22 model/count calls, 22 tools, four accepted edits, no rejected edits, **$0.464054850**
and 224.094 active seconds. No submission or isolated evaluation occurs
(`evaluator=null`); this is not EVALUATOR_FAIL or an aggregate safety verdict.
The final candidate is 46 diff lines (45 additions / one deletion), unverified.

Thirteen inspections precede turn 14's first edit. Turn 15 reports false EEXIST;
turn 16 repairs it, and turn 17 reports wrong intermediate-directory permissions.
Turn 18 repairs mode handling and turn 19 passes the public contract. Turn 20's
upstream regression has three failures / 514 passes / 570 skips: one macOS broken-
link case and two Windows errno cases. Turn 21 uses the last edit on the macOS
branch only, then turn 22 stops without rechecking. Old helper bodies, including
macOS handling and Windows ENOTDIR-to-ENOENT translation, were delivered at turns
4/6 and remain exact native receipts before the initial rewrite. All three public
failure rows reach the final repair decision untruncated. The Windows translation
is not restored by that edit; this static observation is not a new check verdict.

At the stop decision, 19 model calls, 79 tools and 1,582 active seconds remain, with
zero mutations. `run_check` and `run_probe` remain available. Both final-diff checks
are NOT_RUN, old failure is explicitly historical in `pending_recheck`, and current
completion guidance recommends a check. The stop summary reuses the prior candidate's
PASS/FAIL; the final candidate has no measured outcome. No missing tool, forced read,
token saturation or pre-dispatch horizon terminal explains this stop. However, merely
forcing a recheck would not repair the two unaddressed Windows cases. The earlier
failure to plan the last mutation across both reported failure classes is the more
actionable bottleneck; no new gate, cap increase or runtime fix follows automatically.

All 22 decisions use `memory_update=null`; no finding, question or concern is stored
or rejected. The compact prompt/schema is present and note projection is exact.
This row observes no improvement in explicit note use, not a storage failure or a
causal proof that memory non-use caused the outcome. Native history and encrypted
continuation remain intact. All responses complete, largest output 3,931 tokens;
no protocol correction, paid retry, resume or probe occurs.

Read-only audit at `C:\pt\pl43-review-a` verifies 66 public artifacts, 22 continuations,
21 immutable prefixes, four mutation identities, four public policy hashes and four
owned-container absences. Runtime stays at `bf74bf93`; only result documentation
changes. No earlier candidate, new check or evaluator is executed for analysis, and
no private feedback is reinjected. Hash checks preserve `.env`, user-owned `AGENTS.md`,
1,249 task/history files, 46 runtime files, all 164 prior run files / 3,381 artifacts,
earlier review/audit files and all 175 prior untracked entries. Documentation-layout
tests (three cases), Ruff and whitespace checks pass; runtime hash stays unchanged.
The implementation suite/mock is not rerun for this documentation-only receipt.
Row 44 requires new exact approval.

## Latest live observation: row 42 fixed-runtime submission with acceptance failure

The separately authorized run `run_dev_2dc51a86320d43d1` completes with
**EVALUATOR_FAIL / task acceptance FAIL / safety PASS**,
`failure_class=PRIVATE_EVALUATION_FAILED`, `official=false`, `claim_eligible=false`.
It uses 18 model/count calls, 19 tools, one accepted edit, 197.140 active seconds
and **$0.287173950**. There are no rejected mutations, protocol corrections, retries
or probes. Fifteen inspections precede the first edit at turn 15. Turns 16/17 pass
the public contract and all 517 upstream cases (570 skipped); turn 18 submits the
same 45-line diff (44 additions / one deletion). Isolated acceptance then fails.

Saved evaluator evidence records 10 passing cases, one failure and one error.
Static inspection of the submitted public code explains both observed defects:
the raw component split retains a trailing empty component, causing duplicate
creation of the final directory; treating each visited prefix as a creation target
also propagates EEXIST for an existing file parent instead of ENOTDIR. The relevant
`makedirs`, `create_dir` and `_path_components` bodies were delivered at turns 4/6/8
and remain exact native receipts in turn 15's actual input. This is not evidence
of missing source projection or an old candidate being evaluated. No private case
body or evaluator feedback is reinjected into the coding agent.

| Observation | Row 41 | Row 42 |
| --- | --- | --- |
| Task acceptance / safety | PASS / PASS | FAIL / PASS |
| Model calls / tools | 22 / 23 | 18 / 19 |
| First accepted edit | Turn 17 | Turn 15 |
| Accepted / rejected edits | 2 / 3 | 1 / 0 |
| Cost | $0.431456850 | $0.287173950 |

Twenty-five meaningful envelope fields agree, including runtime/model/task identity,
limits, cap, credential-path hash and sandbox/probe identity. The first actual model
input is byte-identical: `sha256:ed2d0f5371823334d55881f5d7d9a83c8210f23c5848cdeae265e11d5a4d07db`.
Row 42 uses no working-note updates versus row 41's 13, but these are observed choices,
not a controlled memory intervention. At submission, inspection, mutation and probe
remain available with 23 model calls and three accepted edits remaining before the
finish decision. The model judges no further public uncertainty worth probing;
neither exhaustion nor a forced stop caused this failure. No public check fails,
so v33's repair/pending-recheck path is not exercised in this row. One success and
one failure establish neither a success rate nor a causal v33 effect.

All 54 public input/context/continuation artifacts, 18 encrypted continuations,
17 immutable prefixes and eight outcome artifacts verify. Visible-checked,
submitted, worktree and evaluator-applied patch hashes match. Two visible and three
evaluator policy hashes verify; the two visible owned containers are confirmed absent,
and evaluator policies record cleanup. The read-only analysis at `C:\pt\pl42-review-a`
runs no additional candidate/check/evaluator/provider execution. `.env`, user-owned
`AGENTS.md`, 175 prior untracked entries, 1,249 task/history files, 160 prior run files,
3,317 prior artifact files and both prior review directories remain unchanged.
Runtime v33 stayed frozen at that result-only checkpoint. Row 43 later received the
separate approval above; v34 guidance compression adds no failure-specific
task hint, gate or candidate fix.
The three documentation-layout tests, Ruff and `git diff --check` pass; the runtime
hash is reverified unchanged. The full implementation suite and mock are not rerun
for this documentation-only receipt; their frozen-runtime evidence remains below.

## Latest live observation: row 41 repair, recheck and submission

The separately authorized normal v33 run `run_dev_872af7b3c9524a04` completes with
**EVALUATOR_PASS / task acceptance PASS / safety PASS**, `official=false` and
`claim_eligible=false`. Exact task/model/medium/.env/repeat-one/$1.20/probes/state-root
conditions are unchanged. It uses 22 model/count calls, 23 tools, two accepted edits,
265.983 active seconds and **$0.431456850**. Probes are enabled but none is invoked.

The first accepted edit remains turn 17. Fourteen inspection actions precede it;
turn 12 targets the read-only helper and is rejected, and turns 15/16 exceed the
50-line scope at 72/59 lines. These rejected proposals consume no accepted mutation.
Turn 18's public contract fails at the exact intermediate-permission assertion
(`0o755`). Turn 19 correctly replaces the intermediate prefix's caller-supplied
`mode` with `PERM_DEF`, leaving the final leaf's mode separate. Turn 20 receives
`current_public_failure=null` plus the historical native receipt in `pending_recheck`
and immediately rechecks: PASS. Turn 21's upstream regression passes 517 cases
(570 skipped); turn 22 submits the same 30-line diff (28 additions / two deletions).
Isolated evaluation then passes without reinjecting private results into the agent.

All 22 encrypted continuations and 21 immutable input prefixes verify. The submitted,
visible-checked, applied evaluator and worktree hashes agree. Sixty-six public input/
context/continuation artifacts and five outcome artifacts verify, as do three visible
and three evaluator execution-policy hashes. The three visible owned containers are
confirmed absent; evaluator policies record owned cleanup. Thirteen non-null note
updates yield 12 applied receipts and one partial receipt: resolution cites an observed
mutation, not a completed check/probe (`unobserved_verification_result`). The valid finding
and main check continue; resolution is corrected after the actual check result.
No protocol correction, provider retry, resume or budget increase occurs.

This observes the intended failure -> repair -> recheck -> submit flow, not a causal
proof that v33 produced success or a generalization result. Early scope/path mistakes,
first-edit latency and eight unchanged concern updates remain efficiency observations.
Runtime stayed at commit `96d4a122` through both live rows; v34 below is not live-tested.
Read-only evidence: `C:\pt\pl41-review-a`. `.env`, user-owned `AGENTS.md`, all 175
pre-existing untracked entries, 1,249 task/history files, 156 prior run files and 3,241
prior artifacts remain unchanged. This approval was consumed by row 41 alone;
row 42 subsequently received the separate approval recorded above.

## Current implementation: compact optional memory guidance (v34)

The system prompt's memory block and the repeated memory/verification schema
descriptions are shorter. Existing fields, nullable/required structure, constraints,
tool order, source binding, six-note/three-concern lifecycle, delivery and restart
remain unchanged. No model/API/continuation setting, action policy, budget, task
or extra call changes. Notes remain optional, public, run-local and model-authored;
current evidence does not certify the note's interpretation.

The read-only row-41/42 audit found working storage/projection, not a new transport
defect. Row 41 refines the same two IDs and repeats concern updates; row 42 supplies
only null updates. These choices do not isolate a memory effect. V34 consolidates
existing guidance about reusable facts, citation timing, identity and uncertainty;
it does not add mandatory notes, semantic judging or private failure-specific hints.

System prompt: **7,965 -> 6,943 characters**. The dedicated block, including its two
trailing newlines, falls **3,368 -> 2,346**; with unchanged conversation instructions,
the actual system message is **9,422 -> 8,400** characters. The canonical UTF-8
memory schema falls **4,047 -> 3,149 bytes**. Five/six-tool schema examples save
4,490/5,388 bytes, with check-ID enums omitted consistently. These are character/byte
measurements, not billed-token savings or evidence of better agent decisions.

Tool-surface v34 binds this description change; `dev-run-v1` and input shapes do
not change. Old envelopes/journals are not migrated; an old nonterminal run cannot
resume on a mismatched runtime. Local comparison and validation records are in
`C:\pt\pl34-memory-a`; `C:\pt\pl41-42-memory-a` remains the read-only audit.
That implementation authorized no live row. Row 43 later received separate approval
above; row 44 and any paid comparison require another exact approval.

Ruff, 80 focused memory/feedback cases and nine final compression/wire cases pass.
All 54 test files pass across the final nine groups: **915 passed, four real-Docker
opt-ins skipped**. Two stale prose/full-schema-hash expectations from the first
pass were corrected, and only their two groups reran; runtime bytes stayed fixed.
The longest group command is 119.83s; the staged workflow including reruns is not
an under-two-minute cycle. Existing citation, expiry, optional/null update,
nonblocking rejection, native delivery, restart, privacy and completion tests pass.

Mock `run_dev_f378a3d7f2724dde` at `C:\pt\pl34-smoke-a` reaches mutation, visible
check, finish and isolated EVALUATOR_PASS / acceptance PASS / safety NOT_RUN:
four mock turns, five tools, one accepted mutation, zero count/provider calls and
zero cost, in 5.26 command seconds. Runtime content is
`sha256:1cd81f909921c3c8ef34c0452b35db32a67421e3b45d42e525dfac057f7c53ea`;
tool surface is `sha256:00d059e1093394877e4a0a50716f89cf0c8db72576e45a16daf8821c0471d108`.
This verifies local contracts and smaller descriptions, not improved live memory
use or task acceptance. No Docker/provider execution or old-run migration occurred.
Preservation hashes keep `.env`, user-owned `AGENTS.md`, task/history and old
run/artifact/review files unchanged; all 175 prior untracked entries remain in place.

## Previous implementation: current failure versus pending recheck (v33)

The model-facing current view now separates an observed failure on this diff from
an edited-but-unchecked candidate. `current_public_failure` keeps current failures
and their exact public diagnostics unchanged. After repair, `pending_recheck` names
the current diff, unchecked status and previous failure's native receipt instead
of repeating old recurrence/repair claims as an active current failure. A receipt
reference requires matching action/check/diff and the complete failure payload;
missing delivery retains the bounded original observation as historical/unbound.
Recheck PASS clears pending; recheck FAIL supplies the new current failure.

Canonical audit context, original native tool results and saved input prefixes
remain unchanged. The short prompt distinguishes hypothesis from verified defect
and recommends rechecking a repair before reusing the old failure as evidence;
independently supported edits remain available. No forced read/check, stop rejection,
new action mask, model/API setting, tool input/order, scope or limit change is made.
Tool-surface v33 binds the presentation semantics; `dev-run-v1` stays unchanged and
old envelopes are not migrated. The prompt is 7,965 characters versus v32's 7,973.

The new regression reproduces the old active-looking historical focus. A read-only
comparison of all 25 saved row-40 inputs changes only the failure/pending fields at
turns 20/22/23/24; source evidence, available tools and budgets stay identical.
Row 40 already delivered historical labels and recheck advice, so this is a clarity
repair, not proof that the model lacked that information or would now solve the task.
The implementation validation executed neither an earlier candidate nor a new live
row. Rows 41/42, and then row 43 on v34, received the separate approvals above; no
row 44 or paid follow-up is authorized. Provider-free implementation evidence is in
`C:\pt\pl33-feedback-a`; the old `C:\pt\pl40-review-a` remains read-only.

Ruff and the final focused repair/recheck/identity/tool/prompt group pass: 69 cases
in 103.49s. All 53 test files run exactly once on the frozen final runtime in nine
fresh external roots `C:\pt\pl33-final-b{1..9}`: **906 passed, four real-Docker
opt-ins skipped**. The longest group is 117.99s; the entire staged workflow is not
claimed to take under two minutes. The 19 new cases cover current versus historical
focus, exact native receipt/fallback, recheck PASS/FAIL, optional edits/inspection,
rollback, immutable history, restart/replay and privacy.

Mock `run_dev_47b590d48d744c5e` at `C:\pt\pl33-smoke-a` reaches mutation, visible
check, finish and isolated EVALUATOR_PASS / acceptance PASS / safety NOT_RUN in
5.70 command seconds: four mock turns, five tools, one accepted mutation, zero
provider/count calls and zero cost. Runtime content is
`sha256:0a5a7386b3c2c2251e374815fc62c83663dbbe9650a42722c9ed571fcdd2542d`;
tool surface is `sha256:4c927d9a5e6ee6b9ea04115129c603160073e49508a78baec80ccd2493bcb16e`.
Hash checks preserve `.env`, user-owned `AGENTS.md`, tracked task/history bytes and
all old `C:\patchloop-state` run/artifact bytes. No live effectiveness claim follows.

## Previous implementation: complete-line public check feedback (v32)

Public checks now retain complete LF/CRLF lines at the sandbox byte-prefix limit,
the gateway's 12,000-character per-stream tail, and the recent-check 4,000-character
tail. An intact unterminated EOF line is retained if it fits; an overlong or partially
cut line is omitted. The existing stdout-first sandbox byte allocation and all output
ceilings are unchanged. `truncated` reports sandbox or subsequent delivery clipping.

Failure diagnostics are extracted from already captured public output before gateway
clipping. Final pytest summary rows take priority over intermediate chained exceptions;
otherwise recognized pytest exception lines or Python terminal frames provide the
exception type. Unframed log words and mixed/unknown terminal types remain null.
`public_check_failure.failure_summary` preserves literal public failure/comparison
lines (up to eight lines / 4,000 characters), observed count and omission status.
It does not infer expected/actual direction, cause, test acceptance or execution order.
This durable summary reaches current failure focus and native tool output, and is
restored unchanged on action replay/restart. Earlier journal feedback is not reparsed.

The row-39 B tail's false `exception_type="turn"` and the unreported gateway clipping
both reproduce on the preceding runtime. This fixes feedback accuracy, not the
candidate's leaf-link semantics: neither B branch had a model turn after that check.
No prompt, action mask, model setting, limit, task package or tool input/order change
is introduced. Output semantics are bound by tool-surface v32; `dev-run-v1` stays the
same, old envelopes are not migrated and no paid run/resume or Docker execution is
authorized by this provider-free implementation.

Ruff and 46 new focused cases pass (4.63s), including malformed qualified exception
names, LF/CRLF/UTF-8 boundaries, mixed exceptions, literal comparison preservation,
pre-clipping diagnostics, unchanged outcomes and native/restart/action replay. All
52 test files run once on the final runtime across eight fresh external roots
`C:\pt\pl32-full-final-a{1..8}`: **887 passed, four real-Docker opt-ins skipped**.
The longest group is 120.53s, slightly above the two-minute target; the full staged
workflow is not claimed to fit two minutes. Partition and read-only stored-output
analysis are in `C:\pt\pl32-feedback-a`.

Mock `run_dev_54fbfa663cfc46b9` under `C:\pt\pl32-smoke-a` reaches mutation, the
registered visible check, finish and isolated EVALUATOR_PASS / task acceptance PASS / safety
NOT_RUN in 5.05 command seconds: four mock turns, five tools, one accepted mutation,
zero provider/count calls and zero cost. It does not measure the coding model's repair
ability. Runtime content is
`sha256:78ee51337d43c39de7e035f55ce0fac6a4ad2d782fae83ae4d17295e6329557b`;
tool surface is `sha256:99c1205b2182ffae25bd2647aca2b83c726df5963094a95c6368d57493ca1c79`.

## Previous implementation: explicit mutation pre-state and completed identity (v31)

A successful `replace_text` now records its completed candidate in the result's
`workspace_diff_hash`, equal to `output.worktree_diff_hash` and the mutation/post-image
diff identity. `output.baseline_diff_hash` explicitly preserves the full pre-edit diff.
The baseline comes from the original admission even when a resumed process finds the
candidate already applied. The incremental replacement's `output.patch_hash` remains
separate from both full-diff hashes. These are action-time snapshots, not a claim that
a historical result describes the workspace at later replay.

The read-only row-38 audit found the prior ambiguity in all four successful edits:
the outer workspace hash named the pre-edit diff while the inner worktree hash named
the post-edit diff. The source was actually changed and the final current-state view
was correct. This is a feedback identity inconsistency, not evidence of an unapplied
repair, and not proof of why the model ignored recheck guidance. The final candidate
remains untested. No additional stop validation, forced check, action mask, prompt,
model setting, scope or resource-limit change is introduced.

Reads, searches, probes and checks retain their existing snapshot identity. Failed
mutations retain the rolled-back workspace identity and existing typed baseline/
candidate diagnostics. Durable action IDs/inputs, source references, note lifecycle,
check invalidation and finish identity remain unchanged. Tool-surface v31 binds the
new output semantics; `dev-run-v1` and tool input shapes/order are unchanged. Older
run/envelope bytes are not migrated and saved native prefixes are never rewritten.
Implementation alone authorized no Docker/provider execution, historical candidate repair/
recheck or retry/resume. Row 39 received the subsequent exact approval recorded below;
row 40 requires separate approval.

The new regression first reproduces the old pre-state-as-result mismatch, then Ruff
and all 118 focused identity/recovery/projection/completion/contract cases pass in
95.54 seconds. All 47 test files run exactly once across six fresh parallel external
roots `C:\pt\pl31-full-a{1,2,3,4,5,6}`: 717 passed, four real-Docker opt-ins skipped.
Groups pass 71/77/48/129/187/205 cases in 85.85/71.97/66.44/72.47/107.86/99.19 seconds.
The eight new cases cover LF/CRLF, sequential non-empty baselines, incremental versus
complete diff identity, admission/replacement/result crash boundaries, exact completed
replay, scope rollback/cache preservation, actual native/context delivery and unchanged
check/finish eligibility at zero edits. Runtime bytes stayed fixed across validation.
Focused validation and each full-suite group meet two minutes; the staged sequence
including smoke and audit is not claimed as a sub-two-minute workflow.

Mock `run_dev_52c7646bb0b54864` under `C:\pt\pl31-smoke-a` reaches mutation, visible
check, finish and isolated task acceptance PASS/safety NOT_RUN: four mock turns, five
tools, one accepted mutation, zero provider/count calls and zero cost. Its pre/post,
checked and submitted identities verify. Tested runtime hash is
`sha256:94cdd9067d777ba2bd2246dd8ea8fa9dbefcbba758ac886e037f1a9702950853`;
tool-surface hash is
`sha256:43e2a53673700c48b46247df8b1d91e7ce2af52b88d042f00d843128e9e5f6de`.
No model prompt or tool input changes. Row 38's journal remains hash-identical; this
local consistency correction establishes neither live rechecking nor task correctness.
Final preservation hashes match for `.env`, user-owned `AGENTS.md`, all 1,249 tracked
task/historical files and 148 prior run files; all 175 preexisting untracked entries remain.

## Previous implementation: current permissions and action-bound note feedback (v30)

The provider-free follow-up labels each observed source group with
`edit_permission=allowed|read_only`, using the same public path matcher as mutation
admission. Forbidden paths still take precedence. The label does not grant anchor
evidence, imply semantic readiness or change offered tools. No source is read to create it.

A successful mutation that expires source notes now carries `working_notes_after_batch`
even with no memory update. The notice belongs to that exact action and current diff;
later unrelated reads/checks do not repeat it. A later current view references the full
exact memory receipt already delivered in native history rather than re-emitting its
historical success/rejection body. Missing or mismatched delivery keeps inline feedback.
Canonical audit context, original receipts, prior native prefixes and durable lifecycle
remain intact. Note expiry, unknown-ID rejection and main-action independence do not change.
Tool-surface identity is v30; input shapes/order, global limits, model settings, task bytes
and action masks are unchanged. Existing envelopes are not migrated.

Row 37's read-only analysis distinguished 13 inspections that added coverage, three
zero-match searches and two covered-only inspections. One covered-only search was a cache
hit; both reread ranges were still present in the actual input. Path rejection and the
65/54-line scope failures were correct and reached the next decisions. Source groups
previously lacked adjacent permission labels, but the public constraints were delivered.
Notes first appeared at turn 23. Turn 25 changed their broadly cited source and expired
both IDs; turns 26/27 repeated those IDs despite current-state/unknown-ID guidance.
Both findings failed in each partially applied update; only other annotation fields
applied. The unannotated mutation lacked native expiry feedback, and turn 26 re-emitted
a 1,018-byte old success receipt beside the correct empty current ID list. These are
observed presentation weaknesses, not proof that they caused the model's repeated IDs
or earlier exploration. The row remains immutable task acceptance PASS/safety PASS,
`official=false`, with no broader effectiveness claim.

Ruff and 55 focused cases pass in 36.26 seconds. The complete 46-file provider-free suite
passes 709 cases, with four real-Docker opt-in cases skipped. Six parallel processes use
fresh roots `C:\pt\pl30-full-a{1,2,3,4,5,6}`, each file exactly once: 71/77/48/129/179/205
passed in 90.29/75.99/70.22/76.79/84.64/102.93 seconds. Runtime bytes stayed fixed throughout.
The 28 new cases cover existing exact/glob/case/forbidden permissions, inline/native/header
presentation, exact receipt matching and fallback, unannotated expiry, rollback/nonexpiry,
LF/CRLF, later-action non-repetition and completed-mutation-before-batch crash/restart.
Focused validation and each full-suite process meet two minutes; this is not a claim that
the entire staged validation sequence, including smoke, took less than two minutes.

Mock `run_dev_1277b7cb3db8495f` under `C:\pt\pl30-smoke-a` reaches mutation, visible
check, finish and isolated task acceptance PASS/safety NOT_RUN in 5.11 command seconds:
four mock turns, five tools, one accepted mutation, zero provider/count calls and zero cost.
Tested runtime hash is
`sha256:3ff59ea10d353900bbae0da311011ac06c4a033b8e6693026a0ec074ddd38882`;
tool-surface hash is
`sha256:0617d3a20f4e5921b9fddb00cf1e638d0f26adda1982cfe877e8587c9f1116d8`.
The base system prompt remains 7,973 characters; native framing adds only the label's meaning.

Read-only reprojection of row 37 labels the wrapper allowed and helper read-only, attaches
the two expiries to turn 25's mutation output, and reduces turn 26's repeated receipt from
1,018 to a 139-byte reference. Current IDs stay empty; the historical receipt stays exact.
The journal hash remains
`sha256:3f935d7aa2749a3cb3936ecaa6b0fdee35f428ad88ab31e8ab8c96c3b5697988`.
This is a representation check, not a candidate execution or measured model benefit.
Final preservation hashes match for `.env`, user-owned `AGENTS.md`, 1,249 tracked task/
historical files and 144 existing run files; all 175 preexisting untracked entries remain.
Implementation alone authorized no Docker/provider work, historical candidate execution
or retry/resume. Rows 38 and 39 received subsequent exact approvals recorded below;
later rows require their own exact approval.

## Previous implementation: position-bound mutation feedback references (v29)

New model-facing successful mutation results reference unchanged source already delivered
in native tool history. The admitted replacement position, pre/post raw-file hashes,
complete candidate diff and exact delivered lines prove each reference; this is not a
similar-text search. Each span keeps its current identity, a normalized body hash and at
most 16 backward action/field/source-range/target-position references. Missing, conflicting,
partial or non-smaller delivery stays inline. Changed hunks, post-images and failures stay
exact. Durable mutation receipts, gateway evidence and previously sent native items are
not rewritten; restart resolves references deterministically without rereading source.

The obsolete `alternative_requirement_satisfied` flag is omitted from model-facing
mutation results, not raw receipts or recovery telemetry. `stop_task` no longer asks the
model to supply `evidence_span_ids`; its existing reason/summary and turn decision remain.
It still abandons the run without submission. No action mask, stronger stop rule, note
obligation, automatic recheck, task-specific hint or resource-limit change is introduced.
Tool-surface v29 changes the output semantics and only that stop input field; older
nonterminal envelopes remain subject to exact-match rejection, without migration.

A read-only reprojection of row 36's four native mutation outputs reduces their combined
serialized UTF-8 size from 135,440 to 28,572 bytes (78.9%). The final mutation output goes
from 33,409 to 5,373 bytes. All 12 unchanged-source spans become proven references; all
4,206 observed path/hash/line entries, post-images and other result fields remain exact,
apart from the retired flag. The journal hash remains
`sha256:197e0bd4a4daf6fc639d00567b3d4705d7f352f7ca1e95f27804c40c624c9d8f`.
This is an in-memory representation comparison, not a token/cost measurement, replay of
the historical candidate, or evidence that a new agent would finish successfully.

Read-only source analysis also finds the final candidate still has the Windows file-parent
ENOTDIR branch where the public upstream test expects ENOENT. The last repair changed a
different, absent-path branch. This establishes a public code defect, not the outcome of
an unexecuted final check. Delivered recheck guidance and sufficient budget were already
present. The source duplication and obsolete citation requirement are concrete interface
costs, but neither is proven to have caused the model's premature stop. In a separately
approved future row, assess repair of the public failing branch and current-diff rechecking
separately from delivery/byte reduction; do not infer either from model-authored prose.

Ruff and 93 focused cases pass in 25.22 seconds. All 45 test files ran once on fixed
runtime bytes across `C:\pt\pl29-full-a{1,2,3,4}`: 136/72/155/316 passed, two stale
ordered-schema expectations failed, and four opt-in real-Docker cases skipped. Those
expectations now reflect removal of stop's citation field; the final 31 affected feedback/
projection/documentation cases pass in 10.76 seconds. All 681 unique suite cases pass
across these executions, including 37 new reference/projection/restart cases. Group times
were 85.48/104.36/62.40/130.94 seconds; the longest exceeds the two-minute full-suite
target, while focused validation meets it.

Mock `run_dev_3c988fa1ae6d4fdf` under `C:\pt\pl29-smoke-a` reaches mutation, visible
check, finish and isolated task acceptance PASS/safety NOT_RUN in 5.57 command seconds:
four mock turns, five tools, one accepted mutation, zero provider/count calls and zero cost.
The envelope matches the tested runtime hash
`sha256:83c0f69696db8e5d7700719835f1d62a78a31ffeb646f1084718fb9be5b341a7`;
tool-surface hash is `sha256:85aa6d76fe3026f1c9a240f34521a55d7dd294affa577516cdf332cfbb66a2b5`.
The base system prompt remains 7,973 characters; native framing adds only a short reference
explanation. Final hashes preserve `.env`, user-owned `AGENTS.md`, 1,249 tracked task/
historical files and 140 existing run files. All 175 preexisting untracked entries remain.
Implementation alone authorized no Docker/provider execution, historical candidate
repair/recheck or retry/resume. Row 37 received the subsequent exact approval recorded
below; later rows require their own exact approval. All results remain `official=false`.

## Previous implementation: bounded probe observations and submission eligibility (v28)

The approved provider-free follow-up separates normal experiment execution from semantic
verification in the model view. `observation.execution_status=completed` replaces the
ambiguous probe PASS label there; `behavior_verdict=not_assessed` remains explicit for
every outcome. Up to four public files and three ranges per observation kind are shown
with omission counts. Unknown collection is not zero coverage. Full outputs/feedback,
original durable receipts, action/diff identity and execution policies remain unchanged.
Matching native observations are referenced from the compact state, not repeated.

The existing probe description now asks for a discriminating public input variation and
expected observation in its existing question/source fields. Completion guidance still
names `finish_task`, but says eligibility is not proof of untested behavior; it mentions
an optional probe only when offered. No action mask, limit, tool shape/order, mandatory
memory/review step, check credit or finish gate changes. Tool-surface identity is v28;
old envelopes and journals are not migrated.
Implementation alone did not authorize Docker/provider execution. The subsequent exact
live approvals recorded below do not follow automatically from this implementation.

Ruff and 68 focused cases pass in 38.68 seconds. All 44 test files were exercised once
across four new external roots `C:\pt\pl28-full-a{1,2,3,4}`. The groups recorded
109/84/237/213 passed, one outdated tool-description fingerprint expectation failed,
and four opt-in real-Docker cases skipped. The expectation is updated for the deliberately
changed descriptions; ordered input shapes remain pinned separately. The final 50
recheck/completion/observation/documentation cases pass in 20.07 seconds, including that
expectation: all 644 unique suite cases pass across these executions, with four skips.
Group times were
54.57/109.40/81.35/139.81 seconds: the longest full-suite group exceeds two minutes,
although focused validation meets the target. Runtime bytes stayed fixed across groups.
Mock `run_dev_3794b6c0a1414ddf` under `C:\pt\pl28-smoke-a` reaches mutation, visible
check, finish and isolated acceptance PASS/safety NOT_RUN, four model turns/five tools,
zero provider/count calls and zero cost. This is not live effectiveness or safety evidence.
The read-only row-35 probe projection adds 789 UTF-8 bytes and exposes five observed,
31 not-observed changed executable lines with one range omitted from the excerpt.
Its journal hash is unchanged; no candidate is re-executed. The system prompt is 7,973
characters, below the unchanged 8,007-character bound. Runtime hash is
`sha256:97acb41ef92ced7c8e83835d72067e4eaa10f3da094ca77b2413671d90c8b725`;
tool-surface hash is `sha256:fd23f26fec2344d2813cf694a377b708ece0dc96afb23f7562a6deb619827237`.
Final hashes preserve `.env`, user-owned `AGENTS.md`, all 1,249 tracked task/historical
files and 136 existing files in `C:\patchloop-state\runs`; all 175 preexisting untracked
entries remain listed and no writes targeted them. New validation state is under
the explicitly named `C:\pt\pl28-*` roots, not the existing live state.

Read-only row-35 analysis identified two public source defects: comparing relative
`current_path` with absolute `final_path` loses the requested relative leaf mode; treating
every existing non-directory as an invalid parent returns ENOTDIR for an existing leaf
file instead of preserving EEXIST. The public mode check uses an absolute path. These
are source-derived public defects, not a mapping to the uninspected private assertion.
The corrected Windows probe used doubled separators and entered only the delegation
return (changed lines 934-938), not the new traversal body. Nevertheless the next public
decision attributed POSIX and mode coverage to that probe, which only printed Windows
existence. That action's line feedback was delivered once in the next native input.
Every memory update was null; this establishes non-use, not a memory storage failure.
The v27 prompt already advised reuse and input variation; stronger generic wording alone
is not established as a solution, and the v28 change is not evidence of improved agent success.

## Latest live observation: row 40 type repair and mutation exhaustion

The separately approved normal invocation on `9c6cafa7` created
`run_dev_766c5a6ab2f04d82` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`LIMIT_REACHED`: 25 model/count calls, 25 tools, four accepted mutations,
197.000 active seconds and **$0.461354550**. No probe, stop, submission or isolated
evaluation ran. Task acceptance and safety were not evaluated; `official=false`.

- Turns 1-16 inspect the wrapper and helpers. The full higher-level `makedirs`
  (2760-2845) and `create_dir` (2090-2175) bodies were delivered at turns 6/8,
  including Windows errno translation and macOS trailing-separator handling.
- Turn 17 replaces the wrapper delegation with a direct component walk. Turn 18
  fails the bytes-path check with `TypeError: startswith first arg must be bytes or
  a tuple of bytes, not str`. Turn 19 makes the split/normalization separators typed.
- Turn 20 fails `TypeError: can't concat str to bytes`. Turn 21 changes the absolute
  prefix from `drive + self.path.sep` to `drive + path_sep`.
- Instead of rechecking that third candidate, turn 22 reads only 1090-1125 of
  `splitdrive`; its return paths extend through 1136. Turn 23 spends the final
  accepted mutation coercing `drive` to bytes, asserting that `splitdrive` returns
  text for bytes input. Static source inspection contradicts that premise:
  `make_string_path` uses `os.fspath`, and every drive return slices `path_str`.
  The added guard is a no-op for the supported str/bytes paths. The third candidate
  was not executed separately, so this is source-level evidence, not a recheck claim.
- Turn 24's public parent-traversal contract passes. Turn 25's regression returns
  **7 failed, 510 passed, 570 skipped**: broken-link parents expect ENOENT (2),
  POSIX file parents ENOTDIR (20), Windows file parents ENOENT (2), but receive
  EEXIST (17), each in normal/case-insensitive variants; the macOS trailing-separator
  broken-link case unexpectedly raises EEXIST instead of completing.

The direct walk substitutes blanket EEXIST and low-level `create_dir` for the existing
caller/helper behavior. This is a concrete semantic regression, not evidence that the
50-line scope is unsatisfiable. The repair process also spends its last edit on an
unverified, incorrect type premise. Actual model inputs at turns 22/23 already say
`historical`, `awaiting_recheck`, current checks NOT_RUN, and recommend `run_check`.
Thus this is not a missing-error or missing-currency-label observation. Whether the
retained historical failure wording contributes to the decision remains unisolated;
neither model internals nor a single run establish a purely model-only cause.

V32's two early TypeError summaries and exact streams reach turns 19/21 unchanged.
The final regression preserves all seven literal summary rows, reports gateway
clipping (`stdout` 11,987 characters, `truncated=true`), and correctly leaves the
mixed FileExistsError/AssertionError type null. That final result has no subsequent
model turn: minimum completion is blocked solely by accepted mutations (15 model
calls/75 tools remain). It is not token/cost/continuation failure or voluntary stop,
and non-repair cannot be described as ignoring that last error after receiving it.

The final 50-line diff (49 added/one removed), both final checks and workspace bind
`sha256:d3f40afb9044151d28eebe5b34667329c95b405e82b32ba079b63d82429f21f1`.
Current status is contract PASS / regression FAIL, with no untracked file, submitted
artifact or manifest. All four completed/baseline mutation identities and their native
deliveries verify. All 75 context/input/continuation artifacts, 25 current-state budget
projections and 24 append-only prefixes verify; 25 encrypted continuations are stored,
24 replayed exactly once. Every response completes and reports `current_turn` (a
provider-reported mode, not evidence of effective reasoning use). Largest output is
6,404 tokens; final input 110,692 tokens and newest state 11,710 UTF-8 bytes.
There are 17 inspections: 14 add coverage, two are covered-only and one is zero-match;
no cache hit, non-null memory update or probe occurs. Four policy hashes verify and
four exact owned containers are absent. The 279-event chain ends at
`sha256:3889f312f475527d504fe9bedf2af50a6d5adf5561e3d1eb713734e05f1254bc`.

Read-only audit and candidate copy: `C:\pt\pl40-review-a`. `.env`, user-owned
`AGENTS.md`, 1,249 tracked task/historical files, 152 prior run files, 3,168 prior
content-addressed objects and 175 existing untracked entries remain unchanged.
Runtime stayed at the previously provider-free-tested v32 hash throughout. No code,
prompt, context reset, tool mask or limit was changed for this row. The next diagnostic
target is evidence-to-edit validity and repair-then-recheck behavior, not an automatic
cap increase or stronger tool gate. No row 41 or historical candidate rerun is authorized.

## Latest live observation: row 39 rechecked and exhausted accepted mutations

The separately approved invocation on `dfb3f8e9` created
`run_dev_eaad5c70be16434f` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`LIMIT_REACHED`: 33 model/count calls, 34 tools, four accepted mutations,
360.375 active seconds and $0.712855950. No probe, stop, submission or isolated
evaluation ran. Task acceptance and safety were not evaluated; `official=false`.

- Turn 16 attempted the read-only helper; admission rejected `path_not_allowed`.
  Turn 19's wrapper proposal failed `anchor_invalid`. After another read, turn 21
  applied the first mutation, implementing direct component traversal in the wrapper.
- Turn 22's public contract failed on the bytes-path invocation with TypeError from
  mixing string and bytes paths. Turn 23 repaired the accumulator type. Turn 24 then
  failed the public intermediate-mode assertion: `/permissions/transient` needed `0o755`.
- Turn 25's proposal exceeded scope: baseline 47 lines, candidate 51, limit 50,
  delta four, over by one. Rollback retained the baseline. Turn 26 applied a smaller
  permission repair, and the parent-traversal contract passed at turn 27.
- Turn 28's upstream regression failed four cases (513 passed, 570 skipped): broken
  symlink parents returned EEXIST instead of ENOENT, and Windows file parents returned
  ENOTDIR instead of ENOENT, in both normal and case-insensitive variants.
- After three inspections, turn 32 applied the fourth edit. Its public decision proposed
  a one-line parent validation to fit the remaining diff-line headroom. Turn 33 actually
  rechecked that final diff: 21 failed, 496 passed, 570 skipped. All listed failures were
  `UnboundLocalError` for `next_dir`.

The final edit put `raise_os_error(...); next_dir = ...` on the same physical line as
the `if` condition. Read-only AST inspection confirms that both statements belong to
the conditional body: the normal false branch skips the assignment before the next
line reads `next_dir`. This is a directly observed control-flow defect introduced while
compressing the edit, not evidence that a valid solution cannot fit the 50-line scope.
The original four exception-semantic failures are not proven repaired by this candidate.

Unlike row 38, the final candidate was rechecked. After that failure, the harness
recorded `completion horizon exhausted before provider dispatch`, with seven model
calls and 66 tool actions remaining, minimum completion four calls, and only
`accepted_mutations` blocking. No 34th provider dispatch occurred. The terminal was
not a token/cost/provider failure or a voluntary premature stop. Final current-diff
status is upstream regression FAIL and parent-traversal contract NOT_RUN; the earlier
contract PASS belongs to the previous candidate and gives no current completion credit.

The final workspace has only `pyfakefs/fake_os.py`, 48 added/one removed lines, and no
non-ignored untracked files. Its 49-line diff and final check bind
`sha256:26e28fec2ef8e063037a97f78a3dbd2fb32999a34a94b5016eb88c5b5c6f6341`.
There is no submitted artifact, manifest or evaluator result. All four v31 successful
mutation receipts and actual native deliveries consistently distinguish original
baseline from completed candidate. This verifies identity delivery and observed
rechecking, not that v31 caused rechecking or improves general agent effectiveness.

All 99 context/input/continuation artifacts, 33 completion/currency projections and
32 unchanged input prefixes verify. All responses completed; 33 encrypted continuations
were stored and 32 replayed exactly once. All native source identities/lines, mutation
post-images and 83 source permission entries verify. All five check policy hashes verify;
all five line traces were collected and five owned containers are absent. All memory updates
were null. Eighteen inspections added coverage, three were covered-only and one search
was zero-match; there were no cache hits. First accepted mutation was turn 21. Final
input was 160,590 tokens, newest state 12,699 UTF-8 bytes, largest output 6,051 tokens.
The 370-event journal hash chain verifies at
`sha256:cf17509d072b278592c5a0bc9072f63fe384e4ed473cbca60c03c5625ed94b52`.
Approved runtime/task/model/credential-path/probe identities match preflight. `.env`,
user-owned `AGENTS.md`, 1,249 tracked task/historical files, 148 prior run files and
175 preexisting untracked entries remain unchanged. No historical candidate repair/
recheck, retry/resume or row 40 is authorized; further diagnosis uses saved evidence.

### Row 39 follow-up: scope feasibility and first-edit evidence

The approved provider-free audit reconstructs all four accepted edits in memory from
the public base source and durable exact replacements. Each preimage matches its raw
CRLF hash, and the final bytes match the immutable workspace. A fresh external bare Git
store computes whole-file `--numstat`; the existing pure `verify_scope` checks the same
public constraints. AST inspection checks assignment placement, without importing or
executing any candidate. The actual turn-32 input contains the correct 49/50 budget and
the existing warning that headroom is not replacement-text length.

| Final guard layout | Full diff lines | Scope | Assignment outside `if` |
| --- | ---: | --- | --- |
| Recorded semicolon edit | 49 | PASS | No |
| Put only the assignment on the next line | 50 | PASS | Yes |
| Put condition, raise and assignment on separate lines | 51 | FAIL | Yes |
| Same separate lines, remove the preceding added blank line | 50 | PASS | Yes |

The limit did not require the erroneous compression. These results prove feasible
line layout and block structure only, not correct exception semantics or passing checks.
No historical candidate was repaired in a worktree or rechecked.

At the first accepted edit, all 572 previously observed source lines are present in
the actual native input: 243 wrapper, 270 filesystem helper and 59 path-helper lines.
Public bytes-path assertions, intermediate `0o755`/leaf `0o700` assertions, read-only
permission labels and the instruction to identify/reuse existing behavior owners are
also present. Thus these failures are not explained by source projection loss.

- Turn 6 says it will inspect `create_dir`, but requests filesystem lines 2720-2788.
  That range starts inside `makedir` (2712-2762), a different function. The actual
  `create_dir` (2092-2143) has zero observed lines before the first edit. Its implementation
  was read only by this audit, not retroactively attributed to the model. The wrapper's
  `mkdir` body (890-912) was also not observed.
- The complete existing filesystem `makedirs` (2769-2823) was delivered, including
  the Windows ENOTDIR-to-ENOENT translation at 2821-2822. The first edit bypasses it
  and calls `create_dir(next_dir, mode)` directly, dropping that exception adaptation.
- Delivered `_path_components` overloads preserve bytes, and `abspath` distinguishes
  byte/string working directories. The new accumulator instead starts from string
  separator/cwd values. The first public check exposes that mismatch.
- The new loop passes the leaf mode to every `create_dir` call despite the public
  parent/leaf distinction. The next public failure exposes that separate preservation gap.

Before the first edit, 19 inspections comprise 15 new-coverage actions, three covered-only
reads and one zero-match search. Turns 9/12 reread parts of the already delivered helper;
turn 20 rereads the wrapper after a correctly rejected fabricated contiguous anchor.
The public decisions increasingly seek components for a direct walker; after the rejected
helper edit, the model ports that strategy into the allowed wrapper. This supports an
edit-strategy/evidence-use diagnosis, not a conclusion that all exploration was wasted.
Every memory update was null: non-use, not a demonstrated storage failure or proof that
mandatory notes would help. Prompt reuse guidance was already supplied.

No new deterministic delivery, scope-arithmetic or admission defect was established,
so runtime, prompts, masks, limits and task bytes remain unchanged. The next experiment
should hold the harness fixed and distinguish behavior-owner identification, preservation
of explicit public requirements and scope interpretation; it requires separate exact
authority. No stronger generic instruction, forced memory/check step, semicolon ban or
scope increase is justified by this audit alone.

The scripts and structured result are under `C:\pt\pl39-analysis-a`; scope reconstruction
was reproduced with fresh Git objects under `C:\pt\pl39-analysis-b`. The scope script
requires a new `--output-root` directly under `C:\pt`; neither script dispatches a provider
or executes task code. Seven scope/AST comparisons and source-delivery assertions pass.
The 370-event journal retains its hash above, and the final workspace hash remains fixed.
All 152 current run files, `.env`, user-owned `AGENTS.md`, 1,249 tracked task/historical
files and 175 preexisting untracked entries are preserved. This remains `official=false`.

### Frozen next-action comparison (six responses collected)

After the user approved by reference the disclosed six-response/zero-tool scope,
`run_dev_sample_789ffee05f9d4473` under `C:\pt\pl39-decision-live-a` completed at
`SAMPLES_COLLECTED`: six fresh input counts, six provider responses, $0.392849400
known recorded cost and 51.657 active seconds. It used the frozen v2 task inputs,
`gpt-5.4-mini-2026-03-17`, medium/high, root `.env`, one response per cell, the shared
$1.20 cap and full 25k output ceilings. No returned tool, correction, retry, candidate,
probe, evaluator or judge API call ran. This is a diagnostic pilot, not live row 40.

Before dispatch, the assistant rechecked the official Standard rates against the
registered price hash on 2026-09-07 UTC (2026-09-08 KST). This is not a separate human
price audit. Read-only checks verify all 32 journal events and 20 CAS objects, exact
frozen request bytes including tool/property order, and all six continuation hashes,
item orders and action links. Fresh input counts match the three historical counts.
Every response completed; no output ceiling was reached or dispatch left uncertain.

Anonymous public observations were fixed before opening the effort/usage map:

| Checkpoint | Medium | High | Static finding |
| --- | --- | --- | --- |
| C1, before turn 6 | Read helper lines 1258-1315 | Read helper lines 1262-1325 | Both ranges include the delivered `_path_components` headers and match the stated inspection goal. Reads were not executed. |
| C2, before turn 21 | 49-line proposed diff | 44-line proposed diff | Both loop over components with `create_dir(next_dir, mode)` and no separate intermediate-mode selection. High avoids medium's duplicate `exist_ok` normalization. Neither proposal was executed. |
| C3, before turn 32 | 49-line proposed diff | Identical replacement and candidate | Both put `next_dir = ...` inside the one-line `if` body after the error call. A normal false-guard path skips the required assignment. |

Full candidate counts use separate Git blobs, not replacement-line estimates. Frozen
cutoff source hashes are verified with the original CRLF bytes; AST parsing proves C3's
block structure without executing code. C2's delivered parent/leaf mode distinction
is not explicitly preserved by either replacement; the unobserved helper behavior is
an uncertainty, not an automatic semantic FAIL. Exact anchors and valid batch shapes
are not full gateway admission. Task acceptance and safety remain NOT_RUN.

Reproducible read-only audit scripts, fixed anonymous observations and the later
unblinding receipt are under `C:\pt\pl39-decision-review-a`. This is assistant static
inspection, not an independent human rating or separately sampled judge; collection
artifacts keep `grading=NOT_ASSESSED`. One pair per failure-selected, correlated state
cannot establish a win rate, repeatability or whole-agent improvement. In particular,
this pilot does not support treating higher effort alone as a fix for the last repair.
Observed cost/latency differences are not efficiency estimates; cache hits differ.

The sampler and v31 runtime remain unchanged. Pre/post hashes of `.env` plus user-owned
`AGENTS.md`, 1,249 tracked task/history files and 152 existing run-directory files match;
all 175 preexisting untracked entries remain. No further sampling, replay, tool execution
or row 40 follows from this result. The design and provider-free implementation record
below predates collection and remains distinct from this live receipt.

The approved design/preparation fixes the v31 harness and compares the same
`gpt-5.4-mini-2026-03-17` at medium versus high effort for one next response. No prompt,
tool mask/order, task, memory rule, output ceiling or historical input is changed.
The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
lists both efforts; this is not evidence that high will improve these decisions.

| Checkpoint | Decision being inspected | Historical input tokens |
| --- | --- | ---: |
| Before turn 6 | Locate the implementation named by the inspection goal | 21,225 |
| Before turn 21 | Preserve public behavior in the first proposed edit | 86,322 |
| Before turn 32 | Repair within scope without changing unintended control flow | 153,464 |

One fresh response per checkpoint/arm prescribes six generations. Row 39's
historical responses are calibration evidence, not the newly sampled medium control.
Both arms retain the exact medium-generated history and encrypted continuation: the
intervention concerns only the next decision, not an entire high-effort trajectory.
Original medium request hashes reproduce exactly at all three cutoffs; high differs
only at `reasoning.effort`. No future action/result, repair example or audit rubric is
added to the model input. This follows the existing native-continuation contract and
[official context guidance](https://developers.openai.com/api/docs/guides/reasoning#keeping-reasoning-items-in-context).

The external packet, protocol, reviewer-only rubric and read-only validator are under
`C:\pt\pl39-decision-design-a`. Packet hash:
`sha256:200e80988694023f381ac77f77ff5a62348f34f7f8200e4c6548e7a54caa8347`.
The preparation receipt stays `PREPARED_NOT_EXECUTABLE`, `dispatch_enabled=false`;
the separate live receipt above does not rewrite it. The validator confirms
all three request identities, cutoff/call-result/continuation linkage and identical
tool schemas/order. Eight tamper cases reject changed output caps, tools, input hash,
runtime, cutoff, effort, dispatch flag and a future input. Preparation performed no key
loading, provider counting/generation, tool execution, candidate execution or Docker operation.

The frozen six-response cap is $1.20, total active time 1,800 seconds, fixed 25,000
output tokens per response, zero SDK retries/corrections and zero tool executions.
Historical counts and registered row-39 rates give an all-uncached/full-output planning
reservation of $1.066516500, not a fresh price/count quote or guaranteed affordability.
The driver must recheck prices/counts and preserve the fixed ceiling for all
remaining cells; uncertainty stops the whole experiment, and budget pressure must not
silently reduce one arm's output capacity or history.

Review public action/code against prespecified contract, source-grounding, public
behavior and static-scope/control-flow criteria, initially blind to effort/cost/latency.
Valid inspection instead of mutation is not automatically failure; unexecuted behavior
is NOT_ASSESSABLE, never task acceptance PASS. Record casewise preference/tie/not-comparable,
not a general success rate. The [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
motivates explicit criteria and accounting for variability. These three failure-selected,
correlated states and one sample per arm cannot establish repeatability or generalization.

The normal `dev` and exact-envelope resume paths cannot execute this design.
[diagnostics/decision_sampler.py](../diagnostics/decision_sampler.py) now provides a
separately source-hashed `validate` / `collect` / read-only `inspect` entry point outside
the pinned v31 runtime. It reconstructs the exact original inputs and tools without
executing selected actions. The original prepared packet remains unchanged with
dispatch disabled; collection requires separate execution authority, never a flag
change to historical preparation or a normal repeat=1 invocation.

The sampler reuses the zero-retry adapter, exact input counting, integer cost ledger,
encrypted-continuation storage/verification and hash-chained `dev-run-v1` journal.
Each fresh request retains 25,000 output tokens. Admission protects all remaining
cells using historical input reservations, replacing the current cell's estimate
with its fresh count immediately before dispatch; later counts can still stop the
pilot. No arm/history is shortened to fit. Live admission binds an explicit same-UTC-day
review attestation for the registered price identity, not an automatically verified quote.
Uncertainty stops every remaining cell; a settled incomplete response is recorded
without correction. Usage is durable before further response artifact processing.
An exclusively created fresh external root prevents concurrent collection or retry;
`inspect` reports killed-process uncertainty without writes or resumed execution.
Public decision artifacts and independently shuffled review order omit arm/effort,
usage and latency. The unblinding map and encrypted-artifact hashes remain in the
diagnostic journal. Batch-shape checking is not full tool admission or rubric grading.
Canonical content hashes do not detect JSON object-property reordering. Implementation
review caught the sorted hash serialization being reused for transmission; the sampler
now preserves the original tool/property order for counting, dispatch and durable
request capture, with a separate order-sensitive identity. This diagnostic-only fix
does not rewrite any historical input, runtime schema or frozen request content hash.

The 39 new sampler cases and three documentation cases pass in 31.06 seconds. Tests
use synthetic public inputs and fake clients; credential loading, real client creation
and gateway execution are forbidden. They cover six-cell independence, input/approval
tampering, full-capacity reservation, parallel IDs, incomplete outcomes, opaque errors,
continuation corruption/action mismatch, deadline reduction, concurrent-root rejection,
crashes before/after dispatch/usage/sample recording and idempotent terminal projection.
Tool/property order is checked separately from canonical request-content equality.
The original three medium request hashes also reproduce through the new validator;
their high counterparts differ only in effort. This is collection reliability evidence,
not evidence that high makes better decisions.

Final Ruff passes for `patchloop`, `tests` and `diagnostics`. All 48 test files run
exactly once in six fresh external roots `C:\pt\pl39-sampler-final-b{1,2,3,4,5,6}`:
756 passed, four real-Docker opt-ins skipped. Groups pass 60/64/64/141/155/272 cases
in 96.37/116.62/92.00/102.77/100.79/100.25 seconds. The initial partition's longest
group took 133.98 seconds; redistributing tests brings every final group below two
minutes without omitting tests. The complete iterative implementation/validation
session is not a two-minute measurement.

The real frozen input fake-client smoke under `C:\pt\pl39-sampler-smoke-b`, diagnostic
`run_dev_sample_24e6f1aca57c43aa`, collects all six cells with original tool/property
order and no credential loader, real client or tool execution. Its usage numbers are
simulated, not billed. Existing dev-head mock `run_dev_5e78b26004514415` under
`C:\pt\pl39-dev-smoke-a` still reaches mutation, visible checks, finish and isolated
task acceptance PASS / safety NOT_RUN at zero provider cost. Sampler source identity:
`sha256:d5718e7b1021aae3c9e6cfb34d1b9ebe9aa9f14b2a77d920f198940d8c9ad16d`.
Runtime remains `sha256:94cdd9067d777ba2bd2246dd8ea8fa9dbefcbba758ac886e037f1a9702950853`.

Any further paid execution requires fresh exact approval of packet and sampler hashes, task/model,
both efforts, `.env`, one response for each of six cells, a new external result root,
zero tool executions and a shared $1.20 cap. The completed pilot, implementation and prior
single-row approvals do not authorize another pilot, row 40, retry/resume or historical candidate repair.
All results remain `official=false`, `claim_eligible=false`; task acceptance and safety
evaluation remain NOT_RUN. `.env`, user-owned `AGENTS.md`, task packages, pre-existing
untracked directories and all historical run/report bytes are preserved.

### Prepared fresh-state comparison (not executed)

The user approved preparation only for a follow-up at row 39's input before turn 32.
`diagnostics/fresh_state_design.py` adds standalone `prepare` / read-only `validate`
commands outside the pinned v31 runtime; it has no provider collection path. The
packet, protocol, reviewer-only rubric and separate public-equivalence audit are under
`C:\pt\pl39-fresh-state-design-a`, with status PREPARED_NOT_EXECUTABLE and dispatch disabled.
No key loading, provider counting/generation or historical candidate execution occurred.

Both arms retain the exact task, `gpt-5.4-mini-2026-03-17`, medium effort, tool/property
order, 25k output cap, current failure/check status and remaining budgets. A is the
original native request. B is an independent three-message request with the same core
coding instructions and task, a context-format-specific instruction suffix and one
complete current public state. It quotes all 32 prior public calls and their 32 exact
results as data, including public hypotheses, negative observations and check logs.
It resolves all 665 observed current source lines across four files and 21 continuous
ranges into direct bodies, preserving gaps and raw file hashes without reading the
task workspace. Those bodies also remain in the archive; this deliberate duplication
tests direct access alongside the other representation changes, not optimal compaction.

| Input | Native message/item count | Final serialized UTF-8 bytes | Fresh input token count |
| --- | ---: | ---: | --- |
| A, original native episode | 129 | 684,213 | Not requested; historical count 153,464 |
| B, fresh state plus quoted public archive | 3 | 265,083 | Not requested |

All current public state fields compare equal, and all public call/output objects,
argument/output strings and tool schema order are preserved. B omits 31 encrypted
reasoning items and replaces 32 accumulated developer state records with one current
record. It still retains prior public model-authored hypotheses; it is not memory-free.
Fresh reasoning, reduced state repetition, direct source presentation, native-to-data
conversion and format instructions change together. The result cannot isolate reasoning
continuation, token load, ordering or any one context mechanism. Smaller serialization
does not establish fewer billed tokens, a working repair or improved agent performance.

The proposed later schedule is A1/B1/B2/A2: two fresh responses per arm, four total,
medium throughout, zero returned-tool executions, no corrections/retries/chaining,
1,800 shared active seconds and a proposed $1.20 total cap. Preparation granted no paid approval.
At preparation, the six-cell medium/high collector could not execute this different design.
The subsequent provider-free implementation is recorded below; it grants no execution
approval. Fresh counts and current pricing remain admission work,
never infer B's count from its byte length. No default or production-loop change follows.

Packet hash: `sha256:1839a26def6adea31a288ccf2c084d8a77b80b166039e3491dffd141cbb1d8d7`.
Preparer hash: `sha256:3632c6fc93743b8865025cd89f0c785bd1149bb9b03badb76454c08beba2aaa2`.
The original medium request reproduces exactly, including its order-sensitive identity.
Twenty-eight new tests cover state/archive preservation, backward source revalidation,
gaps/blank lines, conflicts, privacy boundaries, future-input and order tampering,
fixed settings, read-only deterministic validation and forbidden key/provider access.
They pass with the 39 sampler tests, three documentation tests and existing isolated
mock E2E: 71 passed in 37.68s (38.299s shell wall time) under `C:\pt\pl39-fresh-checks-a`.
Ruff passes for `patchloop`, `tests` and `diagnostics`. The mock still reaches mutation,
visible check, finish and isolated task acceptance PASS / safety NOT_RUN; this is not
execution or acceptance of either proposed comparison arm. The complete runtime suite
was not rerun for this preparation-only change; its preceding 756/4 record is above.
No task, historical run/report, user-owned `.env`/`AGENTS.md` or v31 runtime bytes change.
The preparation remains `official=false`, `claim_eligible=false`, acceptance/safety NOT_RUN.

### Fresh-state collector implemented (no paid execution)

The subsequent go-ahead authorizes collector implementation and provider-free tests,
not sample generation. `diagnostics/fresh_state_sampler.py` validates the frozen
fresh-state packet and its original source design, then uses the shared diagnostic
collection engine. The six-cell medium/high command retains its distinct packet and
approval contract. The new command requires `--approve-four-responses-zero-tools`
and binds all three diagnostic implementation files, not just the new entry point.
Preparation/source request bytes and the v31 production runtime remain unchanged.

The exact schedule is A1/B1/B2/A2, both medium, four independent responses at the same
pre-turn-32 checkpoint. Every request preserves the frozen ordered bytes. Responses
are never chained, corrected, applied or evaluated. The public review omits arm,
replicate number, cost and latency; the journal retains the anonymous-ID unblinding
map. Returned reasoning is retained only as encrypted artifacts, never plaintext.
Read-only `inspect` supports both diagnostic kinds and never resumes either one.

Each request is counted immediately before generation. B has no historical token
count: byte length and A's old count are not substitutes. The collector enforces the
snapshot's [272,000-token maximum input](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
as a per-response admission ceiling and reserves that input plus the full 25k output
for every future response. Counts above the ceiling stop with INPUT_LIMIT_EXCEEDED;
insufficient shared cap stops with COST_CAP_REACHED before generation, never lowering
the ceiling or changing either input. At registered rates each future reserve is
$0.316500000; this is a maximum reservation, not measured cost or a fresh price quote.
The $1.20 cap, 1,800 active seconds, zero retries and uncertainty-wide stop remain.

Thirty-three new collector cases plus the old sampler/preparer, documentation and
isolated mock E2E pass 104 focused tests in 61.24s under
`C:\pt\pl39-fresh-collector-focus-b`. The other 46 files pass 714 cases with four
real-Docker opt-ins skipped, across six fresh `C:\pt\pl39-fresh-collector-full-a{1,2,3,4,5,6}`
roots. Group times are 66.80/105.42/107.53/105.65/83.80/29.37s. Together they cover all
50 files: 817 unique passed, four skipped; the isolated mock case runs in both stages.
Ruff and diff checks pass. Focused validation and each full-suite group meet two
minutes; the entire staged sequence including smoke is not a sub-two-minute claim.

The four actual frozen requests pass fake-client collection under
`C:\pt\pl39-fresh-collector-smoke-a`, with all ordered identities intact. Its counts,
responses and nested cost are simulated, not actual API usage. A reporting-script
argument error occurred after collection completed; read-only inspection produced
the final receipt without recollecting. Production mock `run_dev_750f8dad0a3a44b8` under
`C:\pt\pl39-fresh-collector-dev-smoke-a` reaches mutation, visible check, finish and
isolated task acceptance PASS / safety NOT_RUN: four mock turns, five tools, one
accepted mutation, zero provider/count calls and zero cost (6.69s command wall time).
Neither mock result is evidence of a fresh-state arm's semantic correctness.

Collector content hash is
`sha256:6e373bf4028426e39c2f4a6b27f0803e6311991c4d4029cd5252355ab2c58d0a`;
the shared six-cell module's new hash is
`sha256:c46a1731601d8df363f56823ee1ec57efe595370721ab1e670fafe029baa5faa`.
Both original prepared packets validate and the old six-response receipt remains
readable. Hashes preserve `.env`/user `AGENTS.md`, 1,249 task/historical files, 152
existing external run files and all 49 files across the two designs, collected pilot
and review. The 175 preexisting untracked entries and pinned v31 runtime remain intact.

This implementation does not establish which representation yields better decisions.
The frozen preparation stays PREPARED_NOT_EXECUTABLE. The subsequent paid approval
and same-UTC-day price review are recorded below; implementation alone did not grant
them. Neither diagnostic is live row 40. No task/candidate execution is authorized.

### Fresh-state comparison: four responses collected

The user's approval by reference authorized exactly A1/B1/B2/A2 at row 39's frozen
pre-turn-32 checkpoint: pyfakefs task v2, `gpt-5.4-mini-2026-03-17`, medium in both
arms, root `.env`, full 25k output ceilings, zero selected tools and $1.20 shared cap.
Invocation on `35f940d5` created `run_dev_sample_1272d5c8122c47cf` in
`C:\pt\pl39-fresh-state-live-a`. It finished SAMPLES_COLLECTED: four input counts,
four completed responses, known **$0.195174300** cost and **36.344s** active time.
The assistant checked official Standard prices on 2026-09-07 UTC before dispatch.
No corrections, retries, response chaining, Docker, candidate or evaluator execution.
Task acceptance/safety remain NOT_RUN, `official=false` and `claim_eligible=false`.

Anonymous public observations were frozen before inspecting arm/usage labels under
`C:\pt\pl39-fresh-state-review-a`. All 22 journal events, 12 CAS objects, exact ordered
requests and four encrypted continuation/action links verify. The read-only static
review uses only cutoff public state/source/traceback evidence. Scope counts are for
the complete sole changed hunk at the observed anchor; parsing is not task execution
or full gateway admission.

| Condition | Next decision | Observed static result |
| --- | --- | --- |
| A1, original native history | Exact replacement | 49-line candidate assigns `next_dir` inside the error if; normal paths skip assignment. |
| A2, same original input | Different replacement | 48-line candidate keeps assignment outside the if, but the parent guard is too late for the recorded broken-link failure. |
| B1, fresh public-state input | Two reads | Rereads 53 current wrapper lines and requests 56 unobserved helper source lines containing both public traceback sites. |
| B2, same fresh input | One read | Rereads 55 already supplied current wrapper lines. |

For A2, the existing trace shows EEXIST when create_dir encounters a broken link as
the next child of a valid parent. The added check of current_dir cannot catch this
before that child creation fails. Its claimed broken-link repair is therefore not
supported by the public control flow. A2 avoids A1's normal-path assignment defect,
but neither proposal establishes a correct repair. B1's new helper request is relevant
to the observed failures, so do not call both B responses wholly redundant or failed
repairs. Their later evidence and outcomes were not collected.

Fresh input counts are **153,464 for A** and **66,054 for B** each time: a 56.96%
reduction, not just smaller JSON. Output/reasoning counts are A1 1124/829, B1 740/516,
B2 611/516 and A2 1382/1017; no response reaches the output ceiling. Cached inputs
vary (0/5,504/65,920/152,960 in collection order), so observed costs cannot isolate the
representation effect. The bundled intervention changed reasoning continuation,
state repetition, source presentation and message structure together. Two responses
per arm at one failure-selected checkpoint establish neither causal attribution,
agent improvement nor a default-setting change. All five proposed calls have null notes.

Preservation checks retain `.env`, user `AGENTS.md`, 1,249 task/historical files, 152
prior external run files, 49 prior design/pilot/review files and all 175 preexisting
untracked entries. Runtime and collector content hashes remain unchanged. No further
sampling, tool/candidate execution, retry/resume or live row 40 is authorized.

### Four-seed short-rollout preparation

The follow-up is not a new normal row or terminal resume. It reuses every collected
A1/B1/B2/A2 response once, without selecting a preferred candidate or generating a new
seed. Four separate Git clones reconstruct the same pre-turn-32 diff and raw source
identities. New hash-chained journals explicitly label cutoff events as inherited,
not newly executed usage; source journals, designs, collections and reviews stay
immutable. The original checkpoint has 9 model / 68 tool / 1 accepted mutation and
1,477 active seconds remaining. The seed consumes the next model step, leaving at
most eight new responses per branch (32 total), not another 40-call episode.

The one-invocation cap is $1.20 for new calls only. Scheduling is
round-robin A1/B1/B2/A2, skipping terminal branches. Each request is counted immediately
before dispatch and must fit its full 25k output ceiling; capacity is never reduced
to fit. This cap does not guarantee all branches finish. Cap/transport/billing or
continuation uncertainty stops the experiment; unfinished branches are censored, not
scored as semantic failures. Each branch retains its active-time budget, excluding
other branches' waiting, under an additional 1,800-second whole-experiment deadline.
There is no restart, seed regeneration, automatic paid retry, image pull/build or
Docker startup. Registered public checks/probes and public finish are in scope; no
private evaluator or general task acceptance claim is part of this comparison.

Both arms use unchanged v31 gateway, source admission, projection, notes, correction
and completion policy. Their exact seed input prefix stays unchanged. All newly
returned encrypted reasoning, function calls and matching results are retained.
An identical short `followup_state_contract` field explains subsequent current-state
developer records in both arms; B's quoted archive remains historical data in its
initial developer record. This tests a one-time bundled reset/repackaging followed
by native continuation, not repeated compaction or encrypted-state reset alone.

Provider-free wiring under `C:\pt\pl39-rollout-wiring-a` applies only the two stored
exact replacements and executes the three stored reads in fresh copies. No task code,
Docker or provider runs. Both edits pass actual gateway admission: A1 is 49 diff lines,
A2 is 48. B1 gains 56 previously unobserved helper lines; its wrapper read and B2's
wrapper read gain zero. Prefix equality, current diff identities and eight remaining
model calls verify for every branch. These observations are not public check results
or evidence that B subsequently repairs the task.

The 24 focused synthetic tests pass in 49.80 seconds under
`C:\pt\pl39-rollout-focus-c`. They cover native continuation, parallel IDs, exact
mutation/check/finish flow, full-ceiling admission, horizon, typed failure feedback,
isolated artifact rebinding, fake-clock deadlines and whole-experiment uncertainty
stops. Crash boundaries preserve usage and action evidence without rerunning a provider
or mutation. Docker image identities were inspected read-only and match the pinned
check and probe images. Production runtime, task bytes and existing evidence remain
unchanged. At preparation time live outcome was unmeasured; mock PASS is not
comparison-arm PASS. The subsequent authorized execution is recorded below.

Final staged validation covers all 51 test files: **841 passed, four actual-Docker
opt-ins skipped**. The six runtime groups in `C:\pt\pl39-rollout-full-a{1..6}` have
714 passes / four skips (longest 108.41s); frozen sampler/design/docs compatibility
adds 103 passes in 68.56s, and the new focused group adds 24. Ruff and diff whitespace
checks pass. The staged whole sequence exceeds two minutes; no faster total is claimed.
Independent mock `run_dev_9f4f4d7ca0da4dd4`, in `C:\pt\pl39-rollout-dev-smoke-a`, reaches
isolated EVALUATOR_PASS / task acceptance PASS / safety NOT_RUN with four mock turns,
five tools, one accepted mutation and zero cost, in 7.96s. Preservation hashes match
for `.env`/user AGENTS.md, 1,249 task/historical files and 152 existing run files; all
175 preexisting untracked entries remain. Only new diagnostic state lives outside
the repository. This preparation did not itself authorize the paid follow-up.

### Four-seed short-rollout completed

The user subsequently confirmed the exact four-branch / at-most-eight-new-turns-each
scope and new shared $1.20 cap. One invocation on `3116cd29` completed at
`C:\pt\pl39-rollout-live-a`: 10 input counts / 10 new Responses, 15 tool actions
(including five selected by reused seeds), six public Docker checks, zero probes,
zero finishes and zero private evaluation. Elapsed time was 177.172s and known new
cost $0.542493150. Existing seed costs were not charged to this invocation. No
seed regeneration, paid retry, normal row 40, Docker startup or image pull/build ran.
Full public audit and analysis are in `C:\pt\pl39-rollout-review-a\summary.md`.

| Branch | New calls / tools | Final diff | Current-diff public result | New cost |
|---|---:|---:|---|---:|
| A1 original native | 1 / 2 | 49 lines | parent FAIL: UnboundLocalError; upstream NOT_RUN | $0.123215250 |
| A2 original native | 1 / 2 | 48 lines | upstream 2 FAIL / 515 PASS / 570 SKIP; parent NOT_RUN | $0.018701250 |
| B1 fresh state | 4 / 6 | 49 lines | parent PASS; upstream 2 FAIL / 515 PASS / 570 SKIP | $0.277969650 |
| B2 fresh state | 4 / 5 | 49 lines | parent PASS; upstream 2 FAIL / 515 PASS / 570 SKIP | $0.122607000 |

All branch terminals are LIMIT_REACHED with only `accepted_mutations` blocking:
the checkpoint left one accepted mutation, now consumed. A branches still had seven
model calls and B branches four; token/cost/time exhaustion did not stop them. All
responses completed within the unchanged 25k ceiling. No inference followed the last
failed check, so this is not evidence of ignoring that newly returned failure.

A1's single-line guard puts `next_dir` assignment inside the raising conditional;
the public check confirms an uninitialized local. A2's `current_dir` guard removes
the two Windows-file-parent failures but checks broken parents too late: creation of
the next component raises EEXIST before advancing the current parent. Two original
broken-parent ENOENT expectations still fail.

B1/B2 first propose over-scope candidates (57/50 and 56/50 lines), receive exact
typed failure and rollback feedback, then converge on the same full patch:
`sha256:60e1d12c826a69ce83d6c4dd46ba5eb183f29565942cf595c598fb2b20fba054`.
They replace direct `create_dir` with `filesystem.makedirs(..., True)`. All four
original upstream failure IDs disappear, but looping-link and trailing-separator
broken-link leaf cases now return ELOOP/ENOENT instead of expected EEXIST. Constant
`exist_ok=True` causes helper resolution where the original False path short-circuits
and preserves EEXIST. This is caller/leaf semantics lost during otherwise relevant
helper reuse, not proof that more inspection or a larger token cap was needed.

Fresh-state did lead to mutation and both checks, not endless reading. However the
helper pivot followed scope rejection; B2 reached the same patch without B1's new
56-line helper read. The higher-level helper was already cutoff evidence. Two samples
per arm at one failure-selected checkpoint do not isolate encrypted reset from public
history repackaging or feedback effects, and no default change is justified. All
memory updates are null; this does not validate improved note or probe use.

An independent runtime defect was reproduced from captured public
output: both B upstream results record `exception_type="turn"`, the suffix of a
`NoReturn:` source signature cut at the 12,000-character tail boundary. The gateway
copies only the sandbox's `truncated=false` flag and its broad exception regex accepts
the severed source token. This did not drive either candidate or a subsequent decision;
there was no next inference. The subsequent provider-free v32 output-boundary/parser
repair above leaves these experiment bytes and their causal interpretation unchanged.

Read-only audit verifies four journal chains, 434 per-branch CAS files including
inherited copies, ordered input/continuation/call-result identities, current workspace
diffs, check policy hashes and the exact billing sum. All six check cleanups are
confirmed. Owned files, 1,249 tracked task/history files, 152 old run files, 83 prior
diagnostic files and the 175-entry untracked list retain their inspected identities.
Production v31 and task bytes are unchanged. Public results remain `official=false`,
`claim_eligible=false`; task acceptance, safety and private evaluation are NOT_RUN.

## Row 38: stopped after an unverified final repair

The separately approved invocation on `2c303bfc` created
`run_dev_91f8c05b570c439b` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`AGENT_STOPPED`, with no submission or isolated evaluation: 20 model/count calls,
22 tool actions, four accepted mutations, 198.859 active seconds and $0.380645550.
The final candidate's task acceptance and safety were not evaluated; `official=false`.

- Turn 7 ran one normally exiting baseline probe about raw parent traversal. This
  is an observation, not semantic PASS or evidence about the later candidates.
- Turn 11 attempted the disallowed helper `pyfakefs/fake_filesystem.py`; admission
  correctly rejected it. Both the public path constraints and v30's adjacent
  `edit_permission=read_only` label were in the actual input.
- Turn 14 applied the first wrapper repair. The contract failed at 15 with
  FileExistsError at public command line 10, the raw parent-traversal invocation.
  Turns 16 and 17 applied two more repairs. There was no check between them, so
  turn 17's assertion that the preceding repair still failed was not established.
- Turn 18's contract failed at public command line 23: the intermediate directory
  `/permissions/transient` did not have the required `0o755` mode. Turn 19 applied
  the fourth repair, changing recursive parent creation to use the default mode.
- Turn 20 called `stop_task` with `no_safe_scoped_mutation` and claimed the current
  candidate still failed. Neither visible check had run on turn 19's final diff.

The actual final input marked both required checks `NOT_RUN`, offered `run_check`,
and explicitly recommended the parent-traversal check. It marked the earlier failure
`evidence_currency=historical`, `phase=awaiting_recheck`, and explained that exhausted
edit allowance does not prevent checks or submission after all checks pass. Completion
was possible with three minimum calls and 21 model/79 tool calls remaining at input
construction; zero accepted mutations remained. Thus the terminal was not forced by
completion, token, cost or provider limits, and a missing check tool does not explain it.
The public decision treated an old failure as current despite the delivered distinction.
Why the model did so is not established by this trace; final correctness remains unknown.

The final workspace contains only a 39-line diff in `pyfakefs/fake_os.py` (38 added,
one removed), with no non-ignored untracked files. Its hash is
`sha256:12c54957d4c994fea756c811dcb18c525415cd17a0d20675ed04478905f5dace`;
the last actual check bound the earlier
`sha256:33e8623251ff0fb485a498e48439358e6de41839412000616ad29cb1ddea6af0`.
No final-candidate probe, recheck, submitted artifact, manifest or evaluator result exists.

All 60 context/input/continuation artifacts, 20 completion/currency projections and
19 unchanged input prefixes verify. All 20 responses completed with reported
`current_turn`; 20 encrypted continuations were stored and the preceding 19 replayed
exactly once. All native observed source identities/lines and mutation post-images
remain exact. Two check policies and the probe policy/receipt hashes verify; both
check line traces were collected and all three owned containers are absent. Final
input: 99,855 tokens; newest state: 11,363 UTF-8 bytes; largest output: 8,439 tokens.
The 228-event journal hash chain verifies at
`sha256:c263afaad68bb4d6343515807965ef60d4a8fd0901decc83abef24666dd9289a`.

V30's permission labels match public policy in all 36 actual source-group entries,
but the disallowed edit was still attempted. Every memory update was null; note expiry
and receipt-reference changes were not exercised live. Twelve inspections added
coverage and one was covered-only, with no zero-match or cache hits. First accepted
mutation at 14 rather than row 37's 22 is an observation, not causal efficiency evidence.
Runtime/task/credential identities match preflight. `.env`, user-owned `AGENTS.md`,
1,249 tracked task/historical files, 144 prior run files and 175 preexisting untracked
entries remain unchanged. This row authorizes no retry/resume, historical candidate
repair/recheck or row 39; the next investigation can use the saved inputs read-only.

## Row 37: submitted and passed isolated evaluation

The separately approved invocation on `2a4cb654` created
`run_dev_36024bd4361343dd` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`EVALUATOR_PASS`: task acceptance PASS, safety PASS, no failure class, with
`official=false` and `claim_eligible=false`. It used 28 model/count calls, 28 tool
actions, two accepted mutations, 308.483 active seconds and $0.651385650.

- Ten inspection turns preceded an attempted edit to the disallowed helper
  `pyfakefs/fake_filesystem.py` at turn 11; it was rejected before application.
  Eight more inspections followed. Turns 20/21 targeted the allowed wrapper but
  exceeded scope at 65/54 diff lines against the unchanged 50-line limit.
- Turn 22 applied the first candidate. The public traversal contract passed at 23;
  regression failed at 24 with one failure, 516 passed and 570 skipped. The public
  failure was `test_makedirs_broken_link_with_trailing_sep_macos`: a broken link with
  a trailing separator raised FileExistsError.
- Turn 25 added the macOS trailing-separator broken-link handling in the allowed
  wrapper. Turns 26/27 reran both checks on that new diff; the contract passed and
  regression recorded 517 passed/570 skipped. Turn 28 called `finish_task`, followed
  by isolated task acceptance and safety PASS. No stop, probe, retry or resume ran.

The submitted diff changes only `pyfakefs/fake_os.py`, 45 added/three removed lines
(48 total), with no non-ignored untracked files. Current visible-check, submitted,
manifest and isolated-applied patch hashes all equal
`sha256:50de2cf13d33f02ef5eef62e87cad02f3ae263ba14f47170978b816844d852c4`.
The 321-event journal hash chain and all 84 context/input/continuation artifacts verify,
as do 28 completion/currency projections and 27 unchanged input prefixes. All 28
responses completed with reported `current_turn`; all encrypted continuations were
stored, with the preceding 27 replayed exactly once at the next turn. Four public check
policies and three isolated-check policy artifacts verify; all seven owned containers
are absent. Private evaluator output was not reinjected into agent context.

V29's native mutation-reference path was exercised: each accepted mutation references
four of its eight unchanged-source spans, with 726 inline source bytes retained where
references would not help. Their result sizes are 18,262 -> 12,788 and 16,369 -> 10,745
UTF-8 bytes, a combined 34,631 -> 23,533 (32.0%). Only those references and the retired
flag differ; all observed path/hash/line contents and post-images remain exact. These
are representation sizes, not a measured counterfactual token/cost saving. The final
input uses 139,707 tokens, its newest state 13,639 bytes, and the largest output 10,906
tokens. Four non-null note updates produced two applied and two partially applied
receipts; this shows use of the annotation path, not verified semantic benefit.

This row demonstrates actual failure-directed repair, current-diff rechecking and
submission, unlike row 36's unverified final stop. It does not isolate v29 as the cause:
the first accepted edit still took 22 turns and three earlier mutation attempts were
rejected. One familiar dev-train task is not a generalization or quality claim. The
new stop field and probe observation paths were not exercised. Runtime/task/credential
identities match preflight; `.env`, user-owned `AGENTS.md`, 1,249 tracked task/historical
files, 140 prior run files and all 175 preexisting untracked entries are unchanged.
No further candidate execution/repair follows automatically from this result. Row 38
received the separate exact approval recorded above.

## Row 36: stopped after an unverified final repair

The separately approved invocation on `9d070a9c` created
`run_dev_ef0c30a81dd848eb` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`AGENT_STOPPED`: 22 model/count calls, 22 tool actions, four accepted mutations,
210.968 active seconds and $0.533869800. There was no submission or isolated
evaluation; task acceptance and safety were not evaluated. `official=false` remains.

- Turns 1-11 inspected public source; turn 12 made the first accepted edit. The
  public contract exposed a bytes/separator type mismatch at 13. After one read,
  turn 15 repaired it. The next contract failed the intermediate-mode assertion;
  turn 17 repaired that behavior and turn 18 passed the contract.
- Turn 19's upstream regression reported five failures, 512 passed and 570 skipped,
  including broken-link and Windows file-parent cases. Turn 20 changed intermediate
  creation to the filesystem helper: the fourth and final accepted mutation.
- Turns 21/22 selected `stop_task` without rechecking that new candidate, claiming
  the contract still passed and regression still failed. Those were both results
  of the previous diff. The first stop supplied action IDs where current source
  spans were expected and was rejected; the second used an empty evidence list
  and was admitted. A voluntary stop is not proof that completion was impossible.

Both final native states explicitly show both current checks `NOT_RUN`, the earlier
failure as `historical`/`awaiting_recheck`, and guidance to use `run_check` despite zero
remaining edits. Before turn 22, 19 model calls/79 tools remained; check + check +
finish required three calls. `run_check`, both public inspection tools and `run_probe`
were available. This was not a token-ceiling or completion-horizon terminal, nor a
missing recheck tool. The public decisions conflict with delivered check currency;
this single row does not isolate the prompt/history/model cause of that interpretation.
The final candidate's correctness remains unknown, not a measured regression failure.

All 22 completion-guidance/check-currency projections and 66 context/input/continuation
artifacts verify, along with 21 unchanged native prefixes. All 22 provider responses
completed and reported `current_turn`; their encrypted continuations were stored and
the preceding 21 were replayed exactly once at the next turn. All 21 prior action
results occur in the final native input. That request used 135,822 input tokens;
its newest state was 10,867 UTF-8 bytes. The largest output was 13,104 tokens, below
the unchanged 25,000 ceiling. Every memory update was null, and no probe ran. V28's
probe observation and ready-to-submit guidance changes therefore have no exercised
live effectiveness evidence from this row.

The unsubmitted candidate changes only `pyfakefs/fake_os.py`, 33 added/one removed
line (34 total), hash
`sha256:79074e915e8de9967e2c76fd8ffd6c78ccb7f9d66cc45635b136af7cc936b301`.
The 247-event journal chain and four public-check execution-policy hashes verify;
all four checks collected changed-line feedback and their owned containers are absent.
Runtime/task/credential inputs match preflight. `.env`, user-owned `AGENTS.md`, 1,249
tracked task/historical files and 136 prior run files remain unchanged; all 175 old
untracked entries remain. No retry, resume, post-terminal candidate execution or repair
ran. Row 37 requires a separate exact approval, not automatic continuation of this row.

## Row 35: submitted, private evaluation failed

The separately approved invocation on `d1660947` created
`run_dev_38e45369894f43b1` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at
`EVALUATOR_FAIL`: task acceptance FAIL, safety PASS, failure class
`PRIVATE_EVALUATION_FAILED`, with `official=false` and `claim_eligible=false`.
It used 23 model/count calls, 25 tool actions, three accepted mutations and
274.327 active seconds, costing $0.510596700. There was no voluntary stop or retry.

- Turns 1-11 made 13 public inspections. Turn 12 proposed an out-of-allowance helper
  edit; turn 13's allowed-file candidate exceeded scope at 58/50 diff lines. Both
  rejections preserved the baseline. Turn 14 made the first accepted mutation.
- The public contract failed at turns 15 and 17, with direct repairs at turns 16
  and 18. The model then chose two optional probes on the final candidate. The first
  probe failed to compile because its raw Windows root string ended in a backslash;
  execution collection correctly remained unknown. The corrected second probe exited normally
  and collected current-diff line entries. These are diagnostics, not required-check PASS.
- Turns 21/22 passed the public contract and upstream regression; turn 23 selected
  `finish_task`. The latest native state explicitly suggested that submission, with
  both current checks PASS. Eighteen model calls, 76 tools and one mutation remained
  before that decision; this was not budget exhaustion.

All 23 canonical/native completion-guidance and check-currency projections match;
69 context/input/continuation artifacts and 22 unchanged native-history prefixes
verify. The 24 prior action results are present in the final native input, and all
23 responses completed with reported `current_turn` reasoning context. The final
request used 134,010 input tokens; its newest state message was 12,197 UTF-8 bytes.
Unlike row 34, no passing visible check was invalidated by a later edit in this row.
This verifies delivery and check-to-submit behavior, not a controlled stale-PASS
replication or proof that v27 caused the different decision.

The submitted diff changes only `pyfakefs/fake_os.py`: 40 added and one removed line,
hash `sha256:e9e47d7288c3305c2017b8508ab1e7c8e742e22becc9d09c5088ce3270011ee4`.
Visible-check, manifest, submitted-artifact and isolated applied/diff hashes match.
Evaluator regression and policy checks pass; the hidden check fails. Private evaluator
contents were not projected back, and no post-terminal candidate test or repair ran.
All four public checks collected execution feedback; the final summary still lists
nine changed executable lines as unobserved. Line entry is not branch/assertion
coverage, and these ranges alone do not establish the private failure's cause.

The 264-event journal hash chain, two probe receipts, execution-policy hashes and
submission provenance verify. All nine owned check/probe/evaluator containers are
confirmed absent. At this observation the runtime was
`sha256:5511b176cd864fd0ab843a39546ba84fcb6ea8f0230153d80b039a08f0c922bd`, tool surface
v27. `.env`, user-owned `AGENTS.md`, 66 prior journal/envelope files, 1,249 tracked
task/historical files and 106 old untracked entries are preserved. The only new run
is the one approved above. The subsequent read-only diagnosis and separately approved
provider-free v28 follow-up are described above. No historical candidate repair or resume
follows from them; row 36 required the separate exact approval recorded above.

## Row 34: stopped before submission

The separately reconfirmed invocation on `ae34d076` created
`run_dev_e9f798d9b3bb451c` under `C:\patchloop-state`: v2
`pyfakefs-makedirs-parent-traversal`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
root `.env`, repeat one, $1.20 total cap and enabled probes. It ended at `AGENT_STOPPED`
after 24 model/count calls, 24 tool actions, three accepted mutations and 235.781 active
seconds, costing $0.456825750. There was no submission or isolated evaluation; task
acceptance and safety were not evaluated. The model's completion claim is not a PASS.

- Turns 1-12 inspected public source; turn 13 added raw-parent recursion. The turn-14
  public contract failed its parent-mode assertion; turn 15 removed the leaf mode from
  recursive parent creation, and turn 16 passed that contract.
- Turn 17's upstream regression reported six failures, including parent-file and
  broken-link behavior. Three public inspections preceded turn 21's repair: recurse
  only when the parent does not exist, using `check_link=True`. Turn 22's regression
  passed, with 517 passed and 570 skipped.
- The last edit invalidated the earlier contract PASS. Turns 23/24 both selected
  `stop_task`, claiming all current checks passed. The first stop mixed stale source
  and action IDs and was rejected; the second supplied a valid source span and stopped
  with `no_safe_scoped_mutation`. No `finish_task` or probe was requested.

The final context and actual native input explicitly contain `needs_visible_checks`,
`parent-traversal-contract: NOT_RUN`, regression PASS and the remaining contract ID.
`run_check` remained available; 17 model calls, 77 tools and one mutation remained before
the last decision, while minimum completion needed only check + finish (two calls).
Finish was correctly unavailable until recheck. This is not ceiling exhaustion or a
completion-horizon/tool-removal stop. The public decision shows stale-PASS/completion
confusion; whether history presentation or model interpretation caused it is not isolated
by this single observation. Do not infer private reasoning or candidate correctness.

All four actual public checks returned `public_execution=collected`, preserved in their
native outputs and current-diff summary. The final regression entered changed executable
lines 934-936 and 938-940; blank lines 937/941 have no line event. No executable changed
line remained unobserved in that report. This validates the absolute-path collection and
delivery seam, not branch/assertion coverage or effective model use. Probes were unused.
All four owned containers are confirmed absent. The journal's 281-event hash chain,
envelope runtime and 72 context/input/continuation artifact hashes and sizes verify;
all 24 provider responses completed and reported `current_turn` reasoning context.

The final unsubmitted candidate adds eight lines in `pyfakefs/fake_os.py`, with diff hash
`sha256:71f25e6d936db80da405611ceaaa59c82950518d22798a97aad7909951276c69`.
Envelope, journal and candidate remain external; no submitted manifest exists. Runtime,
task, `.env`, user-owned `AGENTS.md`, 64 prior journal/envelope files, 1,249 tracked task/
historical files and pre-existing scratch entries are unchanged. No resume, retry,
post-terminal check or repair ran. Row 35 required the later separate approval above; all results
remain `official=false`, with no claim eligibility.

### Row-34 read-only completion-path diagnosis

Comparison of the saved audit context and actual native input isolates a projection
defect: the turn-23 audit card says to run the remaining `parent-traversal-contract`,
but this guidance occurs in none of the native non-reasoning items. In
`compact_model_state`, an inspection-card deduplication filter keeps only protocol
cards, also dropping unique check/mutation next-action guidance. The current NOT_RUN
table and remaining check ID do survive; this is not loss of every completion signal.

`recent_checks` simultaneously retains the previous diff's contract PASS without an
explicit current/historical label, requiring a hash comparison. Failure and working-note
projections do have currency labels. This asymmetry is a presentation weakness, not a
false PASS in the gateway's diff-bound check store. The final provider request reports
114,765 input tokens; its newest complete state message is 10,658 UTF-8 bytes. Large
historical context is measurable, but its causal effect on this decision is not proven.

The stop description already says without submission, but its reason
`no_safe_scoped_mutation` was interpreted in both public decisions as no more edit needed.
Admission validates the intent shape and source IDs, not the truth of completion prose.
That preserves voluntary stop; accepting it did not create a successful task result.
Do not add a prose validator, force a check, rewrite history, or infer that exposing
finish earlier would have solved the run. Prioritize a compact current completion view
with surviving next-action guidance, explicit historical PASS/recheck labels, and a
clear unsuccessful-stop versus successful-submit distinction.

Provider-free characterization reproduces guidance removal and intent-only stop admission
in memory. The 65 existing model-state/check-identity/recheck/conversation tests pass in
9.88 seconds under `C:\pt\pl34-analysis-a`, but do not assert delivery of the remaining-check
guidance in actual model input. Future regression must cover that final boundary, not
only the audit card. This diagnosis changes documentation only; it neither repairs nor
executes the saved candidate, calls a provider, starts Docker, nor authorizes row 35.

## Current implementation: tool surface v27

V27 repairs the completion-guidance delivery boundary diagnosed above. The latest
model-facing state starts with workflow gate, `completion_guidance`, current check
verdicts and remaining check IDs. The guidance is derived from the same current-diff
snapshot and offered tool policy as the context; it names one available next action,
not an automatically executed action or a new requirement. With a repaired candidate
and a remaining check, it explicitly names that recheck. Once required checks pass,
it points to `finish_task`.

This compact current guidance survives native-state projection independently of
historical attempt cards. Retained `recent_checks` keep their original action/check/
diff identity and verdict, with `evidence_currency` and `counts_toward_completion`
alongside them. An earlier-diff PASS remains a recorded PASS but cannot count toward
current completion. Original native results and prior state items are not rewritten.

Tool descriptions, prompt and correction distinguish submission through `finish_task`
from unsuccessful abandonment through `stop_task`. No further edit being needed is
not itself completion. Voluntary stop admission, reason codes, input shapes/order,
tool masks, budgets, output ceiling and exact submission checks are unchanged. No
prose validator, automatic recheck, extra planning/model call or history reset is added.
The tool-surface hash advances to v27; previous run/envelope bytes are not migrated.

The new public-only regression follows old PASS, a failure, repair, current regression
PASS, required recheck and submission through actual native input construction and
gateway restart. Before implementation it failed on the missing `completion_guidance`.
This demonstrates the harness delivery contract, not that a live model would choose
correctly. No historical candidate was executed or repaired. Implementation alone did
not authorize row 35; its later separately approved observation is recorded above.

Read-only reprojection of row 34's saved turn-23 native input confirms the intended
change: `parent-traversal-contract` is the suggested current recheck; its previous
PASS is historical/non-counting, as is the old regression FAIL. The latest regression
PASS is current/counting. The latest state message grows from 10,658 to 11,228 UTF-8
bytes (+570); the original input remains hash-identical. This is a local presentation
comparison, not resume or evidence of a different model decision.

### V27 local validation

Ruff and `git diff --check` pass. Focused completion/check-identity/state/conversation/
contract tests pass 140 cases in 43.65 seconds under `C:\pt\pl27-focus-b`. The full
provider-free suite passes 627 cases with four real-Docker cases skipped, using all
43 test files exactly once across `C:\pt\pl27-full-a{1,2,3,4}`: 60/68/145/354 passes
in 45.46/103.77/60.63/150.24 seconds. The longest group exceeds the two-minute target;
focused validation meets it. Full-suite/mock observed wall time, including local
read-only review gaps, is 162.18 seconds; do not claim an under-two-minute full cycle.

Mock `run_dev_ab6896e303234425` under `C:\pt\pl27-smoke-a` reaches mutation, visible
check, finish and isolated `EVALUATOR_PASS`: task acceptance PASS, safety NOT_RUN,
four mock turns, five tools, one accepted mutation and zero cost. Runtime bytes were
frozen throughout full pytest/mock. Runtime hash is
`sha256:5511b176cd864fd0ab843a39546ba84fcb6ea8f0230153d80b039a08f0c922bd`;
tool-surface hash is
`sha256:a38c04db17044dd2c3d53036808a3232e4dac67c3439bc890413536683028d4a`.
The prompt is 7,990 characters; description-free tool shapes and order are unchanged.
Preservation checks match `.env`, user-owned `AGENTS.md`, all 66 existing external
journal/envelope files, 1,249 tracked task/historical files and 106 old untracked entries.
No provider/input-count call, actual Docker execution, retry, resume or row 35 ran
as part of this provider-free validation.
All evidence remains `official=false` and `claim_eligible=false`.

### Retained v26 execution-feedback behavior

V26 adds advisory **changed-code execution feedback** to existing public checks and
enabled probes. Reading source, entering a Python line, checking an assertion, and
establishing semantic correctness are distinct. A PASS can now coexist with explicit
`not_observed_changed_ranges`, rather than implying that every added error path ran.
No additional model call, tool, forced experiment, action mask, acceptance condition,
or finish blocker is added; the prompt and complete tool input schemas stay unchanged.

The host selects only current tracked editable public Python additions/replacements,
bounded to eight files and 256 changed lines. A separately copied read-only stdlib
collector reports line entries in the launched Python thread; other threads,
subprocesses, branch/assertion coverage and deleted lines are not measured. File/raw-byte,
diff and run/action request identities bind results. Missing/invalid reports, source drift,
trace loss and timeout are unknown, never falsely unexecuted. Non-line-table positions
are distinguished from unobserved executable positions. The bounded report travels
separately from stdout/stderr's existing cap and carries no values or source bodies.

`public_execution_summary` unions only current-diff/current-file observations from durable
public action results. It preserves replay and native delivery, does not populate source
spans or validate a note's meaning, and suggests using relevant unknowns with existing
optional notes/probes. The collector is an in-process diagnostic, not tamper-resistant
attestation or safety evidence. Private evaluation is not instrumented or projected back.
Supported check launch shapes are Python `-c`, `-m`, and script, identified by executable
basename (`python`, `python3`, versioned Python 3, optional `.exe`) across POSIX/Windows
paths. The declared interpreter path and arguments are preserved. Other commands retain
their original launch and report unknown. No image rebuild or dependency is required.

The row-33 diagnosis found wrong object ownership for the newly introduced error-raising
calls despite an earlier public read containing the correct owner. An in-memory trace of
the saved public inline contract did not enter the three new error-raising lines. Further
public-derived synthetic checks exposed additional candidate boundary defects after a
temporary receiver alias. These are post-terminal diagnostics, not hidden inputs for the
agent, a repaired historical submission, measured full-suite branch coverage, or proof
that new feedback would have made the agent succeed. Avoid further tool restrictions or
another prose warning when concrete execution evidence is missing.

Initial v26 validation, before the interpreter-path correction below: Ruff and
`git diff --check` pass. Focused collector/contract/provenance/feedback
tests pass 95 cases in 16.65 seconds, including 38 new cases. The final provider-free suite
passes 587 cases with three opt-in real-Docker tests skipped, across groups of
60/68/85/374 (68.44/87.36/65.06/104.37 seconds) under `C:\pt\pl26-full-c{1,2,3,4}`.
Earlier validation updated an exact context-key test for the new summary. Final review
also separated malformed report metadata (unknown) from actual report-output overflow
(the existing output-limit outcome); the 16,000-byte report allowance is independently
bounded. Runtime bytes stayed frozen throughout the final full suite and smoke. Each
final group and focused phase is under two minutes, not the complete development
validation sequence including earlier passes/reruns. Tests cover actual
local Python inline/module/script launches, LF/CRLF, unobserved error lines despite PASS,
invalid/missing reports, source drift, trace loss, unmeasured threads, output bounds,
native delivery, current-diff union, replay and mocked Docker deadline/cleanup ordering.
Probe child exception/exit paths run with isolation mocked; no real Docker execution is
claimed. All 64 existing run journal/envelope files, `.env`, user-owned `AGENTS.md`,
1,249 tracked task/historical files and pre-existing scratch entries are unchanged.

Initial mock `run_dev_60bf5078e5ba466d` under `C:\pt\pl26-smoke-b` reaches mutation, visible
checks, finish and isolated `EVALUATOR_PASS`: four mock turns, five tools, one accepted
mutation, acceptance PASS, safety NOT_RUN, zero cost, 4.72-second command. The public
check records the two changed lines as entered and binds the same checked/submitted diff.
Envelope/manifest runtime hash is
`sha256:48d18956cd504573bbf52e50c095df591d52761eff1c0f3ef7364e010d375ab6`;
tool hash is `sha256:270506e1f41e2d439ac6a87797763f075027d94d584266c9df371173d47aa4fc`.
The prompt remains 7,938 characters, and the full ordered tool-input schema hash stays
`sha256:90db9c2f4c787e23dd598adc3d782d51f838572d71889c06266810588011ca9e`.
No provider/count call, Docker execution/start/pull/build, resume/retry or thirty-fourth
live row is authorized or executed by this change. All results remain `official=false`.

### Absolute interpreter path correction

The approved row 34 was paused at read-only preflight, before creating a run or calling
the provider: both actual v2 public checks use `/usr/local/bin/python`, but the collector
recognized only literal `python`/`python3`. Check execution itself was possible; its
changed-line feedback would have stayed unknown. Earlier synthetic Docker verification
used the bare executable name and missed this integration gap.

Executable-name recognition now handles declared paths without resolving a container
path on the host, substituting an interpreter, or changing the check's arguments/result
command. Regression tests load both real public check declarations (`-c` and `-m`) and
verify their collector mount and unchanged argv through a mocked Docker launch. Both
failed before the fix. Local tests execute inline/module/script shapes using the actual
absolute host interpreter; private/no-target and unsupported launches stay uninstrumented.
The opt-in real-Docker pair now uses `/usr/local/bin/python` too; its separately approved
execution is recorded below.

Focused validation: 84 passed in 10.85 seconds, one real-Docker case skipped; Ruff passes.
Full provider-free validation passes 614 tests, with four real-Docker cases skipped, in
the same four groups: 60/68/85/401 cases in 83.47/106.14/79.23/125.90 seconds under
`C:\pt\pl26-abs-full-a{1,2,3,4}`. The longest group exceeds the two-minute target; focused
validation does not. Runtime bytes were frozen throughout the full suite and mock.
The measured full-suite/smoke wall interval, including polling/review gaps, was 163.25 seconds.

Mock `run_dev_4b69a2a4630041ad`, under `C:\pt\pl26-abs-smoke-a`, reaches one accepted
mutation, visible checks, finish and isolated `EVALUATOR_PASS` in a 5.54-second command:
four mock turns, five tools, acceptance PASS, safety NOT_RUN, zero provider/count calls
and zero cost. The current check records both changed lines and binds the submitted diff.
All 64 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked task/
historical files and pre-existing untracked entries are unchanged. No actual Docker,
provider, old-run resume or paid row was executed for this correction.

Tool surface remains v26 with unchanged tool inputs, prompt, budgets, task package and
probe profile. Runtime hash changes to
`sha256:a4fe50d03e93c4c15b78d66329bf070bf1f48511d32301a455f72df7e5d2129c`.
Prior envelopes are not migrated. Implementation itself did not authorize Docker or paid
execution; row 34 was unexecuted at this checkpoint and required reconfirmed live approval.

### Corrected-path real Docker checkpoint

The separately approved absolute-path check/probe pair passes in 7.96 seconds on the
corrected runtime above, commit `0e81fffe`, under
`C:\pt\pl26-abs-docker-a\test_real_check_probe_line_fee0`.
The hash-chained journal is `run_dev_linevalidation_3c3ba21546c54e80`. Exactly one registered
check and one probe executed, using the already-local pinned clean Python image; no image
acquisition or Docker startup occurred. The check enters lines 1-3 and leaves error line 4
unobserved. The probe deliberately raises `ValueError` at line 4 and records lines 1-2/4;
comment line 5 has no line event. Both reports are collected, with current-diff union 1-4.
Completed replay preserves journal/results without relaunch, both exact containers are
absent, and public source/diff bytes are unchanged. Provider/count calls and cost are zero.
This validates absolute-path Docker collection on a synthetic public fixture, not the
private evaluator workload or model behavior. Runtime/test bytes are unchanged by this
checkpoint; only current docs record the result. Row 34 required separate exact approval,
subsequently given for the latest live observation above.
All results remain `official=false`, `claim_eligible=false`.

### Separately approved v26 Docker collector verification

On the initial v26 runtime recorded above, one synthetic registered check and one public probe
passed the opt-in integration test in 8.89 seconds. Evidence is under
`C:\pt\pl26-docker-real-a\test_real_check_probe_line_fee0`, with hash-chained journal
`run_dev_linevalidation_14158214d0ee43b2`. The check passed after entering lines 1-3;
changed raising line 4 remained unobserved. The probe deliberately raised the public
`ValueError`, recording lines 1-2 and 4 despite its diagnostic failure. Comment line 5
was correctly classified as having no line event. The current-diff union covers lines
1-4; completed replay preserves results and journal bytes without another execution.
Both exact containers are confirmed absent, source/diff bytes are unchanged, and report
frames do not leak into public stdout/stderr. The failed probe does not invalidate the
required check's PASS or grant source evidence. Provider/count calls and cost are zero.

`tests/test_dev_execution_docker.py` is default-skipped and requires separate explicit
Docker approval; its one case executes exactly this check/probe pair, not the three-case
isolation matrix. Ruff and 38 provider-free collector cases also pass (10.11 seconds,
the real case skipped), plus 19 documentation/contract cases in 0.40 seconds.
Only tests/docs changed; the previously recorded full suite and
mock remain the unchanged runtime's validation, not new executions. No start/pull/build,
private evaluation or paid row ran. This verifies container collection on a synthetic
public fixture, not improved model behavior or task success. It did not authorize row 34;
all results remain `official=false`, `claim_eligible=false`.

### V25 implementation and validation checkpoint

V25 repairs failure feedback without changing action availability or termination rules.
`current_public_failure.evidence_currency` explicitly labels current, historical, or
unbound/unknown evidence; the existing `repair_current_diff` / `awaiting_recheck` phases
remain. A historical failure is not a verdict on the edited candidate. Its guidance
names `run_check` only when offered, and at zero remaining mutations explains that
available checks and submission after current-diff PASS need no further edit. A current
failure instead names only offered repair/inspection tools. The prompt distinguishes
the current candidate's completion path from the feasibility of another mutation.

The additional row-32 audit compared post-edit turns 28/30/34: earlier failures were
retained in each, but the model rechecked with two/one mutations left and stopped with
zero. The failure kind and code also differed, so this is not a causal experiment.
The confirmed implementation defect was identical repair-oriented guidance before and
after an edit. A pure-policy simulation of the last state allows check/check/finish in
either check order if both pass, while an actual new failure with no mutations left
still makes completion impossible. It did not execute the final candidate or a model.

Tool names, complete input schemas/descriptions/order, scope, 40/100/4/1,800 limits,
25,000 output ceiling, native history and voluntary stop remain unchanged. No mandatory
check, extra planning step, stop rejection, automatic retry or model change is added.
Only the feedback/runtime identity changes; old envelopes and run bytes are not migrated.
Separate deterministic evidence/policy validation from model tool-selection evaluation,
consistent with the official [single-agent evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices#example-2).
No paid contrast experiment, Docker execution/start/pull/build or thirty-third live row
is authorized or executed by this implementation. All results remain `official=false`.

Validation: Ruff passes; focused feedback/context/contract tests pass 89 cases in
51.33 seconds. The full provider-free suite passes 549 cases, with three opt-in Docker
cases skipped, across groups of 60/68/85/336 (74.82/92.97/70.50/86.98 seconds), using
`C:\pt\pl25-full-a{1,2,3}` and `C:\pt\pl25-full-b4`. The fourth group was rerun after
replacing an exact v24 prompt-length assertion with the existing 8,007-character bound;
runtime files stayed frozen. The prompt is 7,938 characters and the full tool input
schema hash is unchanged. Eighteen added cases cover failure currency, offered-tool
guidance, conditional check/check/finish with zero edits left, genuine infeasibility,
voluntary stop, native delivery and mutation replay. Each final partition and focused
phase is under two minutes; the complete validation sequence, including reruns, is not.

Mock `run_dev_4b8f728934de4e53` under `C:\pt\pl25-smoke-a` reaches mutation, visible
checks, finish and isolated `EVALUATOR_PASS`: four model turns, five actions, one accepted
mutation, acceptance PASS, safety NOT_RUN, zero cost, 4.87-second command. Envelope and
manifest match runtime hash
`sha256:e1ae0f01fc181572eea43c92e4cd6edda93d280a993bebf35b9a3c3648bff9c5`;
tool hash is `sha256:2d44849e5e5f5039e8590f08324db75723d8c56eff7f5ecb365758da7071173d`.
In-memory row-32 reprojection preserves the saved failure evidence while qualifying
turns 28/30/34 as historical; it neither reruns the candidate nor predicts model choices.
All 62 existing run journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files and pre-existing untracked entries are unchanged.

### Thirty-third live row: public repair and submission completed, private acceptance failed

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 invocation:
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, $1.20 total cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed clean
tracked runtime/task inputs, credential format, both pinned local Docker images and
registered rates matching the official [API pricing table](https://developers.openai.com/api/docs/pricing).
V25 commit `bac7c70f4063224127c2b32bb429e3712056cfb2` produced
`run_dev_6159179ed34542f9`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
`PRIVATE_EVALUATION_FAILED`, 20 model/input-count calls, 20 actions, two accepted mutations,
$0.366307650, 196.811 active seconds and 198 seconds run age. All ceilings stayed at
25,000. No retry, resume, second invocation, Docker startup or image pull/build ran.
The isolated evaluator recorded hidden-tests FAIL, regression PASS and scope PASS;
its output was not reinjected into the coding agent. Every result remains `official=false`,
`claim_eligible=false`.

Fourteen inspections (eight searches, six reads) preceded the first mutation at turn 15.
The model introduced a raw-component traversal only for parent-directory paths, retaining
delegation for ordinary paths. The public contract failed at turn 16 on the intermediate
directory's mode. Turn 17 directly distinguished default parent permissions from requested
leaf mode. Turn 18 rechecked and passed; turn 19 passed upstream regression (517 passes,
570 skips); turn 20 submitted 36 additions and one deletion in `pyfakefs/fake_os.py`.
No mutation was rejected, no protocol correction occurred and no enabled probe was used.

The saved turn-17 input labels the failure current; turn 18 labels it historical and
explicitly offers `run_check` for the edited candidate. The model's public decision also
distinguishes the new candidate from the earlier diff. This observes successful delivery,
repair, recheck and submission, not causation by v25. Two mutation opportunities remained
at recheck and finish: the zero-mutations boundary responsible for row 32's untested stop
was not exercised. That targeted live behavior remains unverified. Fewer turns than row 32
is an uncontrolled trajectory difference, not an efficiency or task-success claim.

Read-only audit verifies all 20 saved inputs and 19 unchanged full-input prefixes,
matching current failure/check views, encrypted continuation order, count/dispatch hashes
and exact cost settlement. All responses report `current_turn`, not proof of effective
reasoning reuse. Input totals 895,551 tokens, including 611,712 cached (68.31%); output
totals 23,900 tokens, including 18,962 reasoning. Final input is 94,438 tokens and 425,204
serialized UTF-8 bytes; aggregate input artifacts total 3,789,254 bytes, excluding tools.
Eighteen journaled note updates contain five findings without note diagnostics.

Checked, submitted, current-worktree and isolated-applied patch identities all match
`sha256:dd779e12ae729a41e32b1c74bc994ff46b0eb96a1601dee1944e65aad90ad3cc`.
No untracked candidate files remain. Envelope, manifest and terminal/evaluator provenance
bind the preflight runtime; all three visible-check policy hashes and confirmed cleanup
records match. Journal SHA-256 is
`f7b9a178a92f21bf2ec64aa3ddf03b49c0e98b8fb4f801181c3112afdc805f8d`.
All 62 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files and old untracked entries are unchanged. This post-run change is
documentation only. The next diagnosis should examine remaining submitted-code semantics,
without treating public PASS as complete acceptance or adding a stop/tool gate. No repair,
paid contrast, retry, resume or thirty-fourth live row is authorized by this result.

Post-run documentation validation passes three tests under `C:\pt\pl33-docs-b`, Ruff
and `git diff --check`. The full suite/mock are not repeated for this documentation-only
record; runtime and task bytes remain the preflight-verified v25 inputs.

### V24 implementation and validation checkpoint

V24 separates the model's current working view from the complete public audit context.
Each appended `harness_current_state` record contains the complete mutable view; the
model does not apply nested set/remove operations or shifting array indices. Only the
unchanged public task is inherited from the initial message. Native encrypted reasoning,
calls and results remain byte-identical, in order, with no new user boundary or history
reset. Saved inputs bind the current view; canonical contexts and journal accounting
remain complete and separate. Old envelopes are not migrated.

The view keeps current tools/budgets, completion feasibility and closure warnings,
scope headroom, full diff, current failure/check currency, notes and corrections.
`current_sources` groups exact observed deliveries and lexical headers by path/raw
file hash; action ID, output field and inclusive line ranges identify native bodies.
Gaps stay gaps and unverifiable deliveries keep complete inline fallback. No source
is read by projection. Rolling inspection cards, coverage-detail arrays, span IDs and
observation counters stay in audit evidence, not repeated model state. Search aggregates
remain visible. Older mutation/check/probe bodies use native references only when the
matching result exists; current failure and typed mutation diagnostics remain explicit.

Out-of-allowance `replace_text` reports `path_not_allowed`, `rejected_path`, the actual
public `allowed_paths`/`forbidden_paths`, and unchanged baseline identity. It explains
that inspectable helper source is not necessarily editable. The pre-apply rejection,
replay key, rollback contract, action availability and mutation input schema are unchanged.

The row-31 audit found 1,824 assignments and 24 removals in accumulated state messages.
State bookkeeping explains 267,071 of the 291,951-byte final-input growth over row 30,
not lost native results or missing notes. Both rejected helper edits had the actual
allowance in input; the old generic error omitted those path names. These findings
justify clearer presentation and feedback, not a claim that they caused every semantic
error. Optional notes/probes, tool masks, task bytes, limits, model and output cap do not change.

An initial complete-view prototype still repeated file identities and made the final
input larger. Grouping exact source deliveries/headers removed that duplication.
Read-only in-memory reprojection of all 31 saved row-31 inputs now measures 651,085
versus 727,250 final canonical UTF-8 bytes (10.5% less), and 8,853,286 versus 10,011,657
aggregate bytes (11.6% less), excluding tool schemas. All native items, 30 unchanged-prefix
edges and source path/hash/action/field/line coverage match. This is not an old-run resume,
token estimate, cache/cost claim, or proof the model would solve the task. Dynamic tool
schema changes remain a separate cache limitation.

Ruff and all 531 provider-free tests pass in four concurrent groups of 60/68/81/322
(106.93/132.22/87.18/155.04 seconds), with three opt-in Docker cases skipped, under
`C:\pt\pl24-verified-a{1,2,3,4}`. Focused conversation/input coverage passes 78 cases in
40.49 seconds; final feedback/catalog refinements pass 32 in 30.98 seconds. New cases
cover 30 rolling states, unchanged audit-only metadata, exact source gaps/hash/fallback,
direct latest-state reading, stale check identity, immutable task and path-rejection
admission-crash/replay. An older synthetic fixture omitted the task at turn start but
introduced it later; it now consistently supplies the same public task. The runtime
contract was not relaxed. The full pytest phase exceeds the two-minute target; focused
tests remain under it. No full-cycle under-two-minute claim is made.

Mock `run_dev_8e267bd533ae42dc` under `C:\pt\pl24-smoke-a` reaches one mutation, visible
checks, finish and isolated `EVALUATOR_PASS`: four model turns, five actions, acceptance
PASS, safety NOT_RUN, zero cost, 6.69-second command. Runtime hash is
`sha256:964c628f70842b392f2d404d86eb7cc4f71e489aad3da856a0428174dc8a94e2`;
tool hash is `sha256:3a114a877f58c774aca0f555b106d7361df7b3087b4c04aa2903cbb9a49853cc`.
Independent audit also verifies 13,062 projected line occurrences against original
native bodies and canonical public source. Runtime files stayed fixed through full tests/mock.

No provider/count call, Docker execution/start/pull/build, old-run resume/retry or
thirty-second live row is authorized by this implementation. `.env`, user-owned
`AGENTS.md`, task/historical files, old external state and untracked work remain protected.
Hash checks confirm all 60 existing journal/envelope files, `.env`, user-owned `AGENTS.md`
and 1,249 tracked task/historical files are unchanged; all old untracked entries remain.
All results remain `official=false`, `claim_eligible=false`.

### Thirty-second live row: stopped after the final repair without rechecking

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 invocation:
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, $1.20 total cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked,
HEAD-clean runtime/task inputs, credential format, both pinned local Docker images and
registered prices matching the official [API pricing table](https://developers.openai.com/api/docs/pricing).
V24 commit `c62e52999b2b27ed2a015305ba344c9805986a46` produced
`run_dev_8f19af52fb0948ca`: `AGENT_STOPPED`, 34 model/input-count calls, 34 actions,
four accepted mutations, $0.778038600, 324.014 active seconds and 325 seconds run age.
All output ceilings remained 25,000. No retry, resume, second invocation, Docker startup
or image pull/build ran. There was no submission or isolated evaluation; task acceptance
and safety were not evaluated. All results remain `official=false`, `claim_eligible=false`.

Turn 13 attempted the uneditable `pyfakefs/fake_filesystem.py`. Pre-apply rejection
returned `path_not_allowed` with the actual `fake_os.py` allowance; no second disallowed
edit followed. Turn 25 made the first accepted edit, replacing delegation in the allowed
wrapper with a low-level path walk. Public traversal failures at turns 26/28 exposed a
bytes/string mismatch and incorrect intermediate-directory mode. The model repaired
those causes directly at turns 27/29. Traversal passed at turn 30, but upstream regression
at turn 31 reported five failures, 512 passes and 570 skips: `exist_ok`, empty-path and
Windows file-parent compatibility. After one read, turn 33 applied the fourth mutation
to those behaviors, leaving 49 added lines and one deletion in one tracked file.

Turn 34 selected `stop_task` with `no_safe_scoped_mutation` and cited the previous
regression failure. This was not a closed-check-tool or completion-horizon terminal:
the exact request offered `run_check`, both current checks were `NOT_RUN`, and the
previous failure was marked `awaiting_recheck` with distinct old/current diff hashes.
Before dispatch, seven model calls and 67 actions remained, versus a conditional
three-call path for two checks and finish. Accepted mutation budget was zero, so further
repair was unavailable, but checking the last repair was still possible. Its success
is unknown. The stop prose's traversal-PASS/regression-FAIL claim belongs to the older
diff, not this final candidate. Do not classify the final code from those stale verdicts.

There were 24 inspections: 14 added coverage, ten did not, with no cache hits. The first
accepted mutation was later than row 31 (turn 25 versus 23). Broad exploration and a
compatibility-sensitive rewrite still followed the explicit path feedback. One rejected
path attempt rather than two is an observation, not a controlled causal result. No probe
ran and no protocol correction occurred. Five note updates submitted six findings:
three created and three updated, all accepted, with all five receipts delivered once
in the next turn. Source changes expired the retained notes; no new findings followed
turn 26. Empty final notes are not evidence that note storage or delivery failed.

All 34 saved inputs reconstruct exactly, with 33 unchanged full-input prefixes and
matching native calls/results, encrypted reasoning and current operational state.
All responses report `current_turn`; this is delivery metadata, not proof of effective
reasoning reuse. The source catalog independently preserves 12,168 delivered line
occurrences. Canonical retained-source snapshots total 486,253 characters, with zero
duplicated inline retained-source characters in model state. Serialized input totals
11,359,517 UTF-8 bytes, final input 761,362 bytes, excluding tool schemas. These are not
token estimates or a controlled comparison with the different row-31 trajectory.

Provider usage totals 2,696,452 input tokens, including 2,047,488 cached (75.93%), and
30,612 output tokens (23,575 reasoning); final input is 177,062 tokens. Eight tool-schema
changes remain. All 34 count/dispatch hashes and cost settlements reconcile, and all
four public-check policy hashes/cleanup records pass audit; no isolated safety verdict
is inferred. Final untested diff hash is
`sha256:a6690fcbebaf70fec387f0617d53229309b20ef71ac1019f8afd5f6412843f0b`;
journal SHA-256 is `b41a434076bc51fa630e6147de81020098b5456c02908e941e3746aa863c50a4`.
No untracked candidate files remain. All 60 prior journal/envelope files, `.env`,
user-owned `AGENTS.md`, 1,249 tracked task/historical files and old untracked entries
are unchanged. Only current documentation records this result. A later diagnosis should
separate compatibility-preserving repair design, note expiry/use and stale-verdict stop
selection; the delivered data alone does not establish why the model made that choice.
No automatic repair, retry, resume or thirty-third live row is authorized.

Post-run validation passes all three documentation tests under `C:\pt\pl32-docs-a`,
Ruff and `git diff --check`. The full suite and mock are not rerun for this documentation-
only change; runtime and task bytes remain the preflight-verified v24 inputs.

### V23 implementation and validation checkpoint

V23 keeps the single user task and every encrypted reasoning/call/result item, but
replaces v22's mutable front-of-request state with an immutable initial state followed
by append-only developer-role state deltas. Each delta sets or removes exact nested
paths; unchanged fields are inherited, null/empty values are explicit, and an exact
container replacement is used when smaller than individual operations. No model
summarization, new user boundary, synthetic tool call, or paid compaction is introduced.
Already sent input items remain a byte-identical prefix of the next input. Equivalent
hydrated values generate identical delta bytes; the saved input and journal metadata
bind both the history and reconstructed current-state hash. Pending replay and uncertain
provider-dispatch handling remain unchanged. Old envelopes are not migrated.

The model-facing current source projection now references complete bodies already in
native results by action ID, output field, path, raw file hash and exact line range.
Adjacent/overlapping observations can jointly supply a range; missing lines, stale hashes,
conflicting text or more than 16 delivery references retain the complete inline fallback.
No unseen source is read. Canonical context artifacts, original results and mutation
admission retain their existing full-body and current-hash contracts. The `read_file`
description now states the existing inclusive 1–400-line rule; inputs and limits are unchanged.

The row-30 read-only audit explains this seam. Input cost rose from $0.317590050 to
$0.933049350 versus row 29 while output cost fell from $0.165379500 to $0.126819000.
Cached-input share fell from 26.18% to 8.73%. Every adjacent saved input changed its
front state before the native history, preventing that history from extending an exact
cache prefix. Six tool-schema changes remain a separate cache limitation; v23 does not
change action masks, tool ordering, model, reasoning settings, output ceiling or cap.
Source body duplication was 542,268 retained characters across 29 inputs, including
23,993 in the last input. These are character measurements, not billed-token estimates.
No source finding was submitted by the model; the initial question/concerns persisted,
so the absence of findings was not a memory-storage failure. Memory simplification is deferred.

The choice follows official [prefix-caching guidance](https://developers.openai.com/api/docs/guides/prompt-caching#preserve-conversation-history)
while preserving the active reasoning/tool sequence. Read-only, in-memory reconstruction
of all 29 row-30 saved inputs preserves every original native item and all 28 successive
input prefixes. Repeated retained-source body characters fall from 542,268 to zero.
This is not a smaller total wire claim: accumulated exact state deltas increase aggregate
canonical input bytes from 5,960,829 to 7,783,355, and the final input from 435,299 to
608,946 bytes. Tool schemas are excluded from these byte counts. A first prototype
replaced entire changed top-level fields and accumulated still more metadata; exact
nested changes reduce that overhead. No tokens, cache hit rate or dollar savings are
inferred from serialized size or ciphertext length. Historical run bytes are unchanged.

Ruff and all 518 provider-free tests pass in four concurrent groups of 60/68/60/330
(70.68/88.89/66.98/92.84 seconds), with three opt-in Docker cases skipped. New short
roots are `C:\pt\pl23-verified-a{1,2,3,4}`. The 25 new cases include exact prefix/state
reconstruction, a 256-pair nested JSON oracle, correction clearing, same-state hydration,
source identity/union/fallback and the advertised read boundary. Existing parallel,
mutation, privacy, cost-admission and crash/resume regressions pass under the new framing.
The focused conversation/contract run passes 59 cases in 12.70 seconds; the earlier
feedback refinement passes 54 in 19.52 seconds. Runtime files remained frozen during
the full suite and mock. Mock `run_dev_f84797eb6e034ce5` under `C:\pt\pl23-smoke-a`
reaches mutation, visible checks, finish and isolated `EVALUATOR_PASS`: four turns,
five actions, one accepted mutation, acceptance PASS, safety NOT_RUN, zero cost.
Mock command wall time is 4.87 seconds. Focused tests and the pytest phase stay below
two minutes; the manually orchestrated Ruff/full-suite/mock sequence took 166 seconds
including review/polling gaps and is not claimed as an under-two-minute full cycle.

These checks establish neither live cache hits nor improved model behavior/generalization.
All 58 existing journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files, and pre-existing untracked directory entries are preserved.
All results remain `official=false`, `claim_eligible=false`. This implementation checkpoint
authorized no provider call, Docker start/pull/build, resume, retry or thirty-first row;
the live observation below required separate exact approval.

### Thirty-first live row: cache reuse observed, public checks PASS, isolated acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked,
HEAD-clean runtime/task inputs, credential format and both pinned local Docker images.
The registered standard prices matched the official [API pricing table](https://developers.openai.com/api/docs/pricing).
V23 commit `bcd85f714b3994eb6aa3ea7b6ecb690b0858a063` produced
`run_dev_7754107f07f442e4`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
`PRIVATE_EVALUATION_FAILED`, 31 model/input-count calls, 31 actions, three accepted
mutations, $0.775517100, 267.171 active seconds and 268 seconds run age. All 31
output ceilings were 25,000. No retry, resume, additional invocation, Docker startup
or image pull/build ran; `official=false` and `claim_eligible=false` remain unchanged.

Turns 13 and 14 attempted to edit `pyfakefs/fake_filesystem.py`, outside the public
allowance, and were rejected before applying any candidate. The first accepted edit
at turn 23 instead added recursive parent creation in the allowed `fake_os.py` wrapper.
Traversal passed at turn 24, but upstream regression failed six file-parent/broken-link
cases at turn 25. Turn 26 guarded recursion with `lexists`; after one search, turn 28
replaced that guard with a condition limiting recursion to paths containing `..`.
Both public checks passed at turns 29/30 (regression: 517 passed, 570 skipped in 3.22
seconds). Turn 31 submitted seven added lines in one tracked file, with no untracked files.
There were 21 inspections: 17 added coverage, four did not, and none was a cache hit.
Probes were enabled but never invoked; there was no protocol correction.

The isolated task check reported one error in 12 cases: a trailing-separator traversal
path raised `FileExistsError`. In the submitted code, `dirname(name)` for a trailing
separator denotes the leaf itself without that separator. Recursive `makedirs(...,
exist_ok=True)` creates that leaf, then the final delegated call tries to create it again
with the original `exist_ok=False`. This is a semantic patch defect, not an old-workspace,
submission-hash or cost-limit failure. Public checks did not cover this combination.
No private evaluator output was reinjected, and no task/harness repair was made after the run.

All 31 canonical contexts and saved inputs reconstruct exactly; all 30 successive full
input prefixes remain unchanged. Native calls/results, encrypted continuation ordering
and state hashes reconcile. All provider responses report `current_turn`, which does
not establish effective reuse of earlier reasoning. Retained current-source bodies total
501,390 characters across canonical snapshots and zero duplicated inline characters in
the model-facing retained source projection; 374 span occurrences use native references.
Aggregate canonical input is 10,011,657 bytes and the final input 727,250 bytes, excluding
tool schemas. These are serialized-byte measurements, not token or billing estimates.

Provider usage is 2,508,902 input tokens, including 1,837,568 cached (73.24%), and 29,822
output tokens (21,060 reasoning). Input costs $0.641318100 and output $0.134199000.
Compared with row 30, cached-input share rises from 8.73% and total cost falls 26.83%,
but aggregate input grows 85.82% and final input grows from 90,851 to 178,154 tokens.
Six tool-schema transitions remain; turns 25 and 31 report zero cached tokens despite
preserved input prefixes. This is observed cache use, not a controlled estimate of the
change's savings or proof of agent efficiency. Task acceptance regressed in this row.

The model submitted 17 note updates and ten source findings across five updates: two
notes were created and then updated eight times, with no finding rejected. Sixteen
receipts appear once in the next native exchange; the finish-turn receipt remains durable
without another model turn. Two verification-resolution attempts were rejected without
blocking their checks; the final question is cleared and the advisory concern resolved
against public evidence. That resolution is not a guarantee of unseen task behavior.

All 31 count/dispatch hashes and cost settlements reconcile. Four public check policies,
three isolated check evidence records, five safety controls and five terminal artifacts
pass integrity/cleanup audit. Checked, submitted, managed-workspace and isolated-applied
patch hash is `sha256:476e1d9665c0212ba417e10f57b738d00165bd1c4cd2370c11a7a0e50fccf388`.
Journal SHA-256 is `77857a7b967ce95f1107873db795793a0b58963518b70cebe02b784f1c91729a`.
All 58 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, 1,249 tracked
task/historical files and existing untracked entries remain unchanged. Only current
documentation records this result. No automatic repair, retry, resume or thirty-second
live row is authorized.

Post-run validation passes all three documentation tests, Ruff and `git diff --check`.
The full suite and mock are not rerun: only current documentation changed, while runtime
and task bytes remain identical to the provider-free validated v23 checkpoint above.

### V22 implementation and validation checkpoint

V22 corrects the native conversation boundary, not the task or action policy. A request
now contains system instructions, one replaceable harness-state JSON prefix, one stable
user task, and the complete ordered native tool episode. Every encrypted reasoning item,
canonical call, and matching public result from that episode is retained exactly once.
The state prefix stays before the user boundary: updating budgets, current evidence,
notes or a correction neither invents a new user request nor accumulates old 24k snapshots.
Historical source/check results keep their original identities and are not current evidence
merely because they remain in history. Current-source admission stays fail-closed.

The saved input artifact supplies the immutable history prefix. Each `turn_started` records
content-free history counts and a history hash; resume checks this contract and all durable
reasoning references before pending tools or a new dispatch. Reasoning-only and rejected
batches append without losing the earlier episode; pending batch replay still finishes
first. Billing uncertainty keeps terminal priority. Whole-history input is counted by the
existing cost admission, with no silent truncation or paid compaction. Tool output/run
limits remain unchanged; the 24,000-character limit bounds retained current source, not
the complete native history. Full history can increase input cost and reach the cap sooner.

Provider completion/decision events now retain `response_reasoning_context` as the reported
`current_turn`/`all_turns`, or null when unreported/unrecognized. The selected GPT-5.4 mini
request still uses medium effort, `store=false`, encrypted continuation and the existing
25k desired ceiling; no GPT-5.6-only option is added. This telemetry establishes reported
availability, not that the model used evidence effectively. All plaintext reasoning,
summaries, private task material and evaluator feedback remain outside agent inputs.

The row-29 read-only diagnosis found two distinct issues. Every saved input replaced the
actual tool episode with only its previous batch and a fresh trailing user context.
[Official reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning#keeping-reasoning-items-in-context)
recommends preserving the active sequence since the last user message. Earlier integrity
audits proved ciphertext delivery, not provider-side reasoning reuse; effective mode was
not recorded. This is a structural risk, not a proven explanation of repeated inspection:
row 28 succeeded with the same framing. Row 29's executable body was present at turns
3-29, mutation was available from turn 2, and the first 26 decisions had null memory updates.

Separately, the submitted manual walker skipped the directory-type check at an existing
file target with `exist_ok=True`, and treated a trailing-separator split's empty tail as
termination, hiding parent traversal. Both defects existed in the rejected 60-line proposal
as well as the accepted 48-line edit: reducing to the unchanged 50-line cap did not introduce
them. Developer-only, provider-free in-memory public-input comparisons reproduced both,
plus premature ancestor-target rejection. They were not an isolated evaluator rerun and
were not injected into the coding agent. No task, old submission or historical run was edited.

Ruff and all 493 provider-free tests pass in four concurrent groups of 60/68/60/305
(72.78/90.91/68.34/94.61 seconds), with three opt-in Docker cases skipped. The 18 new
cases cover full-episode ordering, state field priority, correction carry, reported-mode
privacy, old-history damage, four crash boundaries, once-only mutation/provider execution,
whole-input counting and billing-uncertainty priority. The focused 54-case refinement
passes in 46.29 seconds. Final roots are `C:\pt\pl22-verified-b{1,2,3,4}`.
Mock `run_dev_719b638249c246aa` under `C:\pt\pl22-smoke-b` reaches mutation, visible checks,
finish and isolated `EVALUATOR_PASS`: four model turns, five actions, one mutation,
acceptance PASS, safety NOT_RUN and zero cost. The frozen Ruff/full-suite/mock sequence
takes 102.488 seconds, below the two-minute target. No runtime file changed during it.
An earlier full-suite pass attempt exposed a renamed test-local variable shadowing its
mock helper; that test was corrected. Review also preserved existing context field order
instead of alphabetically sorting the new state prefix. Neither change alters task behavior.
All 56 pre-existing journal/envelope files, `.env`, user-owned `AGENTS.md`, task packages,
historical directories and pre-existing untracked work are preserved.
No paid provider call, Docker start/pull/build, retry, resume, or thirtieth live row is
authorized by this change. All results remain `official=false`, `claim_eligible=false`.

### Thirtieth live row: full native history, public repair, isolated acceptance PASS

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked,
HEAD-clean runtime/task inputs, credential format, and both pinned local images in the
already running Docker service. V22 commit `1caa2859d6a99c8c211c9abf6e45ef4086b140c4`
produced `run_dev_f5f058fc5761480b`: `EVALUATOR_PASS`, task acceptance PASS, safety PASS,
no failure class, 29 model/input-count calls, 28 actions, two accepted mutations,
$1.059868350, 277.578 active seconds and 279 seconds run age. Results remain
`official=false`, `claim_eligible=false`. No retry, resume, extra invocation, Docker
startup, or image pull/build ran.

The first 18 turns made 16 inspections and two baseline probes. The one inspection
without coverage was turn 1's rejected 500-line read against the unadvertised 400-line
limit, not a repeated successful observation. All 15 successful inspections added new
coverage; none was a cache hit. Turn 19 proposed a 67-line mutation,
which scope rejected and rolled back. A third baseline probe at turn 20 failed with a
Python raw-string `SyntaxError`; this was diagnostic failure, not a sandbox-policy
violation. Turn 21's 52-line candidate was also rejected, and turn 22 accepted 38 diff
lines. Turn 23 requested both checks in one response, triggering the existing
single-action batch correction without executing either check. Turns 24 and 25 ran
them separately: traversal passed, upstream regression failed five cases involving
broken links and Windows file-parent error behavior. Turn 26 immediately added a
three-line delegation guard for paths without `..`, without another read. Traversal
and upstream regression then passed at turns 27 and 28 (517 passed, 570 skipped in
3.51 seconds). Turn 29 submitted the final 41-line diff: 38 additions and three deletions
in `pyfakefs/fake_os.py`, with no untracked files. Isolated evaluation passed.

All 29 saved inputs reconstruct exactly, including the rejected parallel-check batch.
The audit verifies 58 context/input artifacts, 29 continuation artifacts, unchanged
history prefixes, 27 executed native results plus two rejection results, and one note
receipt. Every request has one stable user boundary. All 29 provider responses report
`response_reasoning_context=current_turn`; ciphertext integrity and reported mode do
not prove how effectively the model used earlier reasoning. The only memory annotation,
at turn 1, creates an open question and two advisory concerns; no source finding is
written, and both concerns remain unresolved at finish. All three probes use the empty
baseline, so this row provides no candidate-probe or source-note effectiveness evidence.

This observation has fewer zero-coverage inspections than row 29 (1/16 versus 15/30)
and an earlier first accepted edit (turn 22 versus 29), but is not a controlled causal
comparison. Full request input grows from 8,317 to 90,851 tokens; aggregate input is
1,350,165 tokens, including 117,888 cached, with 28,182 output tokens (22,079 reasoning).
All admitted output ceilings remain 25,000. Cost rises from row 29's $0.482969550 to
$1.059868350 despite fewer model calls. Do not equate this single task success with
proven efficiency, generalization, or provider-side reasoning reuse.

The checked, submitted, managed-workspace and isolated-applied patch identities match
`sha256:d364976d54ce7f5c936ffc9884b6d215488b02fee152c44248380aa313b58ebe`.
All 29 count/dispatch request hashes and usage settlements reconcile. Seven public
check/probe policies, three isolated check evidence records, three probe receipts,
five safety controls and eight terminal artifacts pass identity/cleanup audit.
Journal SHA-256 is `414bf776dc136e558e546cb997bb4b32ada3f3d3a760fbb54acf3f5a8e8572a6`.
All 56 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, existing untracked
work, task packages and historical directories remain unchanged. No evaluator feedback
is reinjected into the coding agent.

The immediate post-run change only recorded this evidence in current documentation. Three documentation
tests, Ruff and `git diff --check` pass; the full suite and mock are not rerun because
runtime/task bytes remain identical to the validated v22 checkpoint. No automatic repair,
retry, resume, or thirty-first live row is authorized.

### V21 implementation and validation checkpoint

V21 removes repeated pre-observation inspection prose from the model-facing projection.
The original `turn_decision`, raw tool results, attempt cards, and encrypted continuation
remain durable and unchanged. Native input keeps the exact original call arguments;
the read/search result replaces only its echoed `inspection_intent` with an action-bound
reference. Derived ledger/outcome/attempt cards also refer to the decision instead of
copying its basis, goal, or memory annotation. Source text, actual outcomes, check errors,
coverage, cache flags, explicit notes/questions, current diff, and budgets are not redacted.
This is structural projection, not string matching or semantic judgment of the model.

References distinguish `preceding_function_call_arguments`, context-only
`latest_tool_result.inspection_intent`, and `journal_only` for historical intentions that
are not delivered now. They are marked `model_authored_pre_observation_intent`, not tool
findings. Context-only/mock delivery retains the original latest result intent once where
present. Ledger observations carry their actual action IDs, including after hydration;
identical cached reads or parallel calls never borrow another action's decision.
No tool input, system prompt, note lifecycle, policy, limit, or run schema changed.
Tool-surface identity changes to v21; old envelopes and run artifacts are not migrated.

The read-only row-28 analysis ruled out missing source as the initial repeated-read cause:
the three-line delegation body was already delivered before the model said it had not
seen the body. That pre-observation statement appeared four times in the next input.
The first source finding was only attempted at turn 14; its useful executable lines were
already observed, but its overly broad citation also included unobserved lines 893-904.
Both turn-15 findings cited the source then replaced by the same mutation and correctly
expired. The mutation hypothesis and expected behavior still reached subsequent turns;
expiry did not erase the plan. Seven existing lifecycle/feedback tests passed in 15.82
seconds during diagnosis. These observations do not establish why the model chose its
trajectory or justify mandatory notes, weaker source binding, or tighter inspection masks.

In-memory comparison of all 20 saved row-28 inputs reduces the turn-4 statement from four
copies to one. Original calls/encrypted items and all source/check/note/policy/budget
values remain exact. Total derived context length falls by 5,745 characters across those
20 inputs (turn 4: 18,426 to 18,014); this is not a measured token/cost or agent-success
improvement. Observation IDs missing from the old projection were joined from its durable
public results solely for this comparison. All 54 existing journal/envelope files remain
byte-identical. That implementation checkpoint authorized no provider or Docker execution,
retry, resume, or row 29; the live observation below required separate exact approval.

Ruff and all 475 provider-free tests pass in four concurrent groups of 60/68/60/287
(94.86/117.10/87.92/103.01 seconds), with three opt-in Docker cases skipped. External
roots are `C:\pt\pl21-verified-b{1,2,3,4}`. The 13 new projection cases pass in 2.60 seconds;
related context tests pass after updating two old expectations that required duplicate
decision prose. New tests preserve same-text source/notes, parallel ownership, cache
identity, current-envelope replay, encrypted item order, and unchanged ordered tool inputs.
Mock `run_dev_9ec8c92cf7e34e9a` under `C:\pt\pl21-smoke-b` reaches mutation, visible checks,
finish, and isolated `EVALUATOR_PASS`: four model turns, five actions, one mutation,
acceptance PASS, safety NOT_RUN, zero cost, `official=false`, and `claim_eligible=false`.
The frozen full-suite/mock sequence took 128.0 seconds, slightly over the two-minute
target; focused validation remained below it. No runtime file changed during that sequence.
System prompt length remains 7,880 characters. `.env`, user-owned `AGENTS.md`, task
packages, historical directories, and prior external run bytes were not changed.

### Twenty-ninth live row: public checks PASS, isolated task acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed HEAD-clean
tracked runtime/task inputs, credential format, and both pinned local images in the
already running Docker service. V21 commit `cb235c25d903e07948bcef31a7885140b4e13aa4`
produced `run_dev_7005744ccb5d4cc1`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
failure class `PRIVATE_EVALUATION_FAILED`, 32 model/input-count calls, 35 actions, one
accepted mutation, $0.482969550, 290.593 active seconds and 292 seconds run age.
Results remain `official=false` and `claim_eligible=false`. No retry, resume, additional
invocation, Docker startup, or image pull/build ran.

The first 26 turns performed 29 reads/searches. Turn 27 attempted a 60-line candidate;
scope rejected it against the unchanged 50-line limit, returned `over_by=10`, and restored
the empty baseline. Turn 28 reread an already observed range (cache hit). Turn 29 accepted
a 48-line candidate: 47 additions and one deletion in `pyfakefs/fake_os.py`, no untracked
files. Traversal passed at turn 30, upstream regression at turn 31 (517 passed, 570 skipped
in 3.34 seconds), and finish submitted at turn 32. Isolated task acceptance then failed.
This is a semantic acceptance failure, not a provider, token-ceiling, cost, or deadline
terminal. The execution checkpoint preceded the separate diagnosis recorded above.

The final visible-check diff, submitted artifact, managed workspace, and isolated
evaluator's applied diff all match
`sha256:76b50ccc326b99a286ab1b6540d8ba0b7664922f3498c21b5093c0d8b0b2a7ad`.
Read-only audit verified the journal chain, 64 context/input artifacts, all 32 encrypted
continuation artifacts, exact reconstruction of all 32 saved inputs (31 continuation
edges), 34 next-turn native results, 30 v21 inspection-intent references, two note receipts,
two public and three evaluator policy hashes with confirmed cleanup, and five terminal
artifacts. The typed 60/50 failure and restored baseline reached the next input unchanged.
Provider usage reconciles exactly with the terminal cost; no provider errors occurred.
All 54 prior journal/envelope files, `.env`, user-owned `AGENTS.md`, existing untracked
directories, runtime, task packages, and historical directories remain unchanged.
Journal SHA-256 is `8be79cd609dcc3b276d48a8cd792918c781e48d3668878a1a48af79da856668d`.

V21 removed the redundant intent fields as designed, but did not establish better agent
efficiency: 15 of 30 inspections added no source coverage, including five cache hits.
The original delegation body was delivered by turn 2 and remained in every actual input
from turns 3-29, while the model repeatedly asked to inspect it. Two findings were first
created at turn 27 and remained after the accepted edit; earlier decisions supplied no
memory update. Probes were available on 28 turns but never invoked. Retained source peaked
at 23,997 characters; bounded omission began at turn 25 and reached 151 helper-source
lines, not loss of the repeatedly requested editable body. The first accepted mutation
moved from turn 15 in row 28 to turn 29 here. These uncontrolled observations do not prove
that deduplication worsened behavior, nor support mandatory notes/probes or tighter masks.

Post-run changes only record this evidence in current documentation. All three
documentation tests, Ruff, and `git diff --check` pass. The full suite and mock were not
rerun because runtime/task code did not change after the v21 validation checkpoint above.
No automatic repair, retry, resume, or thirtieth live row is authorized.

### V20 implementation and validation checkpoint

V20 addresses two feedback affordances identified by the public row-27 audit. A working
note citing an executed public check now retains `check_result` beside its existing
action/input/diff identity: the actual `check_id`, boolean `passed`, and bounded
`exception_type` (null when absent). These facts are copied from the durable public
result, not the model's statement. Projection adds per-citation `currency` as current,
historical, or unknown when no diff identity exists. A later mutation changes currency,
not the earlier verdict. Failed actions and non-check results get no invented check
verdict. The label includes no traceback, source body, private path, or reasoning text.
Note application/recovery, nonblocking interpretation errors, and native receipt ownership
remain unchanged; this is not semantic validation of free-form prose.

The probe description now states its existing capability: current tracked public files,
including accepted edits, are importable read-only from `/workspace`; `/tmp` is writable
scratch. Only base Python and public project code are supplied, without network or
dependency installation. The optional experiment remains diagnostic, never required-check
credit. No sandbox/profile/image, tool input shape/order, action mask, or limit changes.
The system prompt replaces overlapping memory guidance with reusable behavior rules and
explicit assumptions: refine the same fact, retain distinct facts separately, and use
the existing current-failure card instead of overwriting reusable knowledge with status.
It is shorter than v19 and adds no model call, planning step, compulsory probe, or gate.

The diagnosis distinguishes observed defects from inferred model behavior. Row 27's actual
mutation inputs contained both separator helper examples and the existing mkdir wrapper;
its code still contradicted its stated normalization/delegation intent. One later note
cited the current AttributeError check but described an earlier diff's assertion failure.
Correct original feedback was present, and zero observed lines were omitted by projection.
Both real-OS probes were baseline observations; the candidate-import capability already
existed but was not explicit in the stable tool description. These changes test delivery
and discoverability, not whether another model trajectory will solve the task.
All old run/envelope bytes remain immutable. Runtime-mismatched nonterminal resume still
rejects. This implementation checkpoint did not authorize the separately approved row 28
below; it authorized no migration, retry, or subsequent live invocation.

Final provider-free verification passes Ruff and all 462 tests in four concurrent groups
of 60/68/60/274 (71.99/88.86/66.64/76.73 seconds), with three opt-in Docker tests skipped.
The 15 new cases cover actual PASS/FAIL/unknown exception labels, cross-diff false prose,
historical verdicts after mutation, parallel native receipts, durable-note crash/replay,
privacy, missing identity, and unchanged ordered tool input structure. Rebuilt contexts
agree by public values; replay from the same saved context is exact. A synthetic fixture
was corrected to restore both check history and in-memory state before testing this.
Roots are `C:\pt\pl20-verified-a{1,2,3,4}`. Mock `run_dev_fe269097df164a83` under
`C:\pt\pl20-smoke-a` reaches mutation, visible checks, finish, and isolated `EVALUATOR_PASS`:
four model turns, five actions, one mutation, acceptance PASS, safety NOT_RUN, zero cost,
`official=false`, and `claim_eligible=false`. The final frozen Ruff/full-suite/mock sequence
took 103.5 seconds, excluding earlier focused debugging. System prompt length fell from
8,007 to 7,880 characters. No paid call or Docker execution occurred; `.env`, user-owned
`AGENTS.md`, task packages, historical directories, and existing run bytes were not changed.

### Twenty-eighth live row: submitted task acceptance and safety PASS

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight confirmed tracked
HEAD-clean runtime/task inputs, credential format, and both pinned images in the already
running Docker service. V20 commit `5dc3c2a3809bc63f27e655cda03e5b13dd231d66` produced
`run_dev_a01ff61f95be4a57`: `EVALUATOR_PASS`, task acceptance PASS, safety PASS, 20 model
and input-count calls, 21 actions, two accepted mutations, $0.193324200, 133.016 active
seconds and 134 seconds run age. No retry, resume, second invocation, Docker startup,
or image pull/build ran. Results remain `official=false` and `claim_eligible=false`.

The first edit arrived at turn 15 after eight reads and seven searches across 14 turns.
It replaced the direct backend call with parent recursion and reused the existing `mkdir`
wrapper. Turn 16's public traversal check failed its intermediate-directory permission
assertion: recursive calls incorrectly inherited the leaf's explicit mode. Turn 17
identified that cause and removed `mode=mode` from the recursive call, without an
intervening read. Traversal passed at turn 18, upstream regression at turn 19 (517 passed,
570 skipped), and finish at turn 20. Isolated evaluation then passed. The submitted
`pyfakefs/fake_os.py` diff adds 13 lines and removes one, with no untracked files.

The final visible-check diff, submitted artifact, and isolated evaluator's applied diff
all match `sha256:83653e8d441d6b8ad5fb0e917b337e4e6b72a455f6100f66ef4d6f3ad164e432`.
Read-only audit verified the journal chain, 40 context/input artifacts, all 20 encrypted
continuation artifacts and 19 exact replay edges, 20 next-turn native results, eight
note receipts, three public execution-policy hashes with confirmed cleanup, and five
terminal artifacts. Prior 52 journal/envelope files and the active runtime hash remain
unchanged. Journal SHA-256 is
`297d50ef9aa517e4d768675fae81d7edf9450cd3eb8e9caa74a99d86c50dd527`.
Post-run edits only record this result in current documentation. All three documentation
tests, Ruff, and `git diff --check` pass; the full suite and mock were not rerun because
no runtime or task code changed after the v20 checkpoint above.

This is evidence of one successful repair trajectory, not that the v20 changes caused it.
Inspection remained open and probes were exposed on all 20 turns, but no probe ran and
no note cited a check, so the new check-result labels and candidate-probe description were
not behaviorally exercised. Four inspections added no source coverage, including one
cache hit. No observed lines were omitted; retained source peaked at 9,825 characters.
Turn 3 repeated a search despite the preceding native read containing the original
delegation body. Turn 14's finding cited still-pending lines 893-904 and was correctly
rejected without blocking the read. Turn 15 created two source findings, then the same
mutation changed their cited source and expired both; no later context retained a finding.
The original verification concern survived seven unchanged updates and remained advisory
and unresolved at finish. Memory-assisted efficiency and candidate probing remain
unestablished; success on this repeatedly used development task is not generalization.
This result did not authorize the separately approved twenty-ninth row above.

### V19 implementation and validation checkpoint

V19 fixes two evidence-continuity issues found by the read-only row-26 audit, without
changing action masks, model tool inputs, budgets, task packages, or acceptance gates.
An admitted exact replacement now maps previously observed complete unchanged lines
to their post-image positions. A one-line edit no longer discards an entire larger
observation. Raw pre/post hashes and exact body comparisons bind the mapping; touched
lines still require the explicit bounded mutation post-image. Unobserved gaps remain
gaps. Merged fragments retain the existing eight-span/per-span output bounds and the
24,000-character context projection bound. Durable mutation results restore the same
evidence after a crash, using the admitted offset and verified original bytes.

Source-note rejection keeps its existing code but distinguishes `never_observed` from
`stale_current_range`, with bounded requested/current/missing range metadata. Historical
coordinates are not current text proof. Errors remain nonblocking; no partial finding,
compulsory reread, new planning action, or automatic semantic validation is introduced.
Every retained check summary carries `action_id`, `check_id`, and `diff_hash` together;
concern resolution also records the actual cited check's name. The previous check-row
selection, native body deduplication, and model-authored interpretation boundary remain.

The row-26 diagnosis is more specific than the initial annotation summary below:
T2/T14 cited pending read ranges and were correctly rejected. T26/T28 cited unchanged
lines 943-948 that had been observed before T25's one-line edit and were still visible
in the current diff, but whole-span invalidation had removed them from admitted current
source. This was not a 24k projection omission. T28's wrong check citation was a model
error with a harness inconsistency: the correct ID was present in another card, but
missing from the retained regression summary itself. These deterministic fixes do not
establish why the model chose its successful solution or guarantee another live result.
Old run/envelope bytes stay immutable; current-runtime mismatches still reject nonterminal
resume. This implementation checkpoint did not authorize the separately approved row 27
below, nor the separately approved row 28. All results remain `official=false`.

Final provider-free validation passes Ruff and all 447 tests in four concurrent groups
of 60, 68, 60, and 259 (69.70, 86.16, 64.59, and 67.54 seconds), with three opt-in
Docker tests skipped. External roots are `C:\pt\pl19-verified-c{1,2,3,4}`. The new
33 cases cover positional source reuse, missing/stale range feedback, and check citation
identity. Earlier tests that assumed evidence loss now explicitly exercise truly unseen
source or deliberate span eviction; synthetic check fixtures include durable action IDs.
Normal/crash execution agrees for insertion/deletion, LF/CRLF, duplicate anchors,
no-final-newline text, and partial-line boundaries. Drift and unseen gaps still reject.
Final mock `run_dev_41da713dc2504dea` under `C:\pt\pl19-smoke-c5` reaches isolated
`EVALUATOR_PASS`: one mutation, four mock model turns, five tool actions, task acceptance
PASS, safety NOT_RUN, zero cost, `official=false`, and `claim_eligible=false`.
The frozen Ruff/full-suite/mock sequence took 93 seconds, excluding earlier focused
debugging. No provider or Docker execution occurred during that checkpoint; `.env`,
user-owned `AGENTS.md`, task packages, historical directories, and existing external run
bytes were untouched.

### Twenty-seventh live row: mutation capacity exhausted, no submission

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight passed tracked
HEAD-clean runtime/task inputs, credential format, and both pinned images in the already
running Docker service. V19 commit `6e4efbb634fc38f6c167758b567e45ba467fea11` produced
`run_dev_e68682d51d2a4dfa`: `LIMIT_REACHED`, 29 model/input-count calls, 30 actions,
four accepted mutations, $0.349973100, 195.406 active seconds and 196 seconds run age.
There was no submission, manifest, or private evaluation. All results remain
`official=false`; no retry, resume, second invocation, Docker startup, or image pull/build ran.

The first edit came on turn 18 after ten reads, six searches, and two baseline probes
across 17 model turns. Both probes passed and observed real-OS parent traversal; neither
executed a candidate patch. The entire run used 12 reads, eight searches, two probes,
four mutations, and four public `parent-traversal-contract` checks. Five inspections
added no source coverage. The upstream regression check was never reached.

| Edit / check turns | Observed change and public result |
| --- | --- |
| 18 / 19 | A manual component walker called `get_path_separator` on `self.path`; `AttributeError` stopped execution. |
| 22 / 23 | Moving that call to `self.filesystem` exposed `AssertionError: /visible/build`: whole-path `abspath` had removed the traversal components before walking. |
| 24 / 25 | Rewriting the walker to preserve the raw path introduced another wrong helper owner, `self.path._alternative_path_separator`; another `AttributeError` stopped execution. |
| 28 / 29 | Correcting that owner exposed `FileExistsError` for `/visible/release`: the code tested existence after creating the directory and treated the newly created leaf as pre-existing. |

The final candidate changes only `pyfakefs/fake_os.py`, adding 34 lines with no deleted
lines or untracked files. Its diff hash is
`sha256:a17c99b7e53425f034a991c65a49b8c7854963c775235fe4f76f5526b81970c9`.
It failed its public check and was not submitted. The scheduler then recorded
`completion horizon exhausted before provider dispatch`, with
`blocking_resources=[accepted_mutations]`: 11 model calls and 70 tool actions remained,
but zero accepted mutations could repair the failure. The conditional minimum completion
cost was four calls. There was no turn-30 provider dispatch. Cost and output-token limits
were not exhausted; all provider responses completed normally, with at most 3,359 output tokens.

Read-only audit verified 345 hash-chained events, 87 context/input/continuation artifacts,
28 exact encrypted-reasoning replay edges, and all 19 note receipts with a following
native delivery. All 20 retained check-summary rows matched the durable action/check/diff
identities. The four mutation post-images and 11 rebound source fragments matched the
actual admitted pre/post bytes. In particular, turn 24 reused the larger function anchor
after turn 22's one-line edit without an intervening read. There were no source-range note
rejections. One finding cited a nonexistent tool result ID and was correctly excluded
without blocking its probe; it also asserted the pending probe's result prematurely.
This is a model-authored annotation error, not missing tool-result delivery.

Both probe receipts and all six execution-policy hashes verified, with cleanup confirmed.
These checks do not establish an evaluator safety result: evaluation did not run.
Inspection stayed open, so closure-warning behavior was not exercised. No successful
check/concern resolution exercised the new resolution-label path. Runtime bytes and all
50 prior journal/envelope files remained unchanged. The new journal hashes to
`sha256:dab04b152155810eee272dea18159c41e943bdb85a64d15e2cfd09dc4707d071`.
Evidence continuity worked on the exercised paths, while the generated implementation
still failed public behavior. This does not prove either v19 quality regression or model
improvement relative to row 26. This result did not authorize the separately approved row 28.

### V18 implementation and validation checkpoint

V18 improves working-memory feedback without tightening the action mask. A concern's
original `statement` is immutable; an existing-ID upsert stores its latest `progress_note`.
An exact repeat of the original or current progress returns `unchanged`, preserving the
decision and update time. A distinct question needs a new concern ID. All concerns remain
model-authored, bounded to three, advisory, and resolved only with the existing evidence rules.

Source-note receipts explicitly describe `before_tool_batch`, including the update's diff
and historical `note_ids_after_update`. Current IDs live in `working_notes.available_note_ids`.
The next native owner output also labels `working_notes_after_batch`, including only that
batch's source-note expirations. Thus a pre-mutation successful note update no longer claims
that the expired ID is still available. The durable receipt, first-owner rule, and replay stay exact.

`observed_source_index` adds at most 16 lexical Python header locations within 4,000
serialized characters, using only already delivered current source. It adds no source read,
function-extent claim, or semantic proof. A conditional one-read/search policy preview now
lists all affected tools, including optional probes/checks, instead of warning about reads
alone. Other actions, new evidence, and larger parallel batches can have different successors.
No budget, tool admission, task case, mandatory experiment, or extra model turn is added.

The row-25 read-only audit found intact core-source delivery: no omitted observed lines,
at most 19,799 of 24,000 retained source characters, and the backend special-case source
already visible. It also found pre-mutation/current-note ID ambiguity, repeated rewriting of
one concern, and incomplete closure warnings. These are feedback defects, not proof that
context size or v17 caused the model's late edit or regression. V18 tests these contracts;
they cannot show that a different prompt would have solved row 25. Existing run/envelope
bytes are not migrated. That checkpoint did not authorize the separately approved row below.

The read-only comparison also caught a navigation implementation defect before release:
the observed editable fragment started inside a docstring, so assuming an initial code
state reversed quote boundaries and hid the real `makedirs` header. Ambiguous initial
bare triple quotes now disable literal masking for that fragment; entries remain explicitly
lexical candidates, not certified symbols. Known literal openings still suppress examples.
This uses no unseen source and does not change mutation evidence admission.
Reapplying the index read-only to row 25's pre-mutation context now retains the
`pyfakefs/fake_os.py:915` header: 16 entries, five omitted candidates, and 3,213 serialized
characters. This is a projection comparison, not a replay of the model's decisions.

Final provider-free verification passes Ruff and 414 tests in three concurrent groups
of 75, 144, and 195 (90.71, 83.92, and 86.28 seconds); three opt-in Docker tests were
skipped. Separate short external roots are `C:\pt\pl18-verified-6401-{a,b,c}`.
Mock `run_dev_0fde34f908a74d5e` under `C:\pt\pl18-smoke-6401` reaches isolated
`EVALUATOR_PASS` in 5.03 seconds through one mutation, four model turns and five actions:
task acceptance PASS, safety NOT_RUN, cost zero, `official=false`, and `claim_eligible=false`.
The final frozen Ruff/full-suite/mock sequence took 98 seconds, excluding earlier debugging
and focused checks. Native feedback is exact across restart; rebuilt context values are
equivalent even if JSON key order changes, and the same persisted context reproduces the
exact model input. No provider call, Docker operation, task change, or live row ran.

### Twenty-sixth live row: submitted task acceptance and safety PASS

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository `.env`, repeat 1, a $1.20 cap,
and `--enable-probes` under `C:\patchloop-state`. Initial read-only preflight found Docker
unavailable and made no run/provider call. After the user started Docker, preflight passed
tracked HEAD-clean runtime/task inputs, credential format, and both pinned local images.
V18 commit `1d361e06ceeb2d4d85a68840ebe354eda7fc52f5` produced
`run_dev_306785d397d640f3`: `EVALUATOR_PASS`, task acceptance PASS, safety PASS,
28 model/input-count calls, 32 actions, three accepted mutations, $0.432518400,
243.125 active seconds and 244 seconds run age. No second invocation, resume, automatic
retry, Docker startup by PatchLoop, or image pull/build ran. `official=false` and
`claim_eligible=false` remain explicit; this is development evidence, not a quality claim.

The first edit came on call 16, compared with call 31 in row 25. It replaced whole-path
delegation with recursive traversal using the existing path/mkdir helpers. Call 17 exposed
intermediate-mode handling; call 20 changed the recursive parent call to `PERM_DEF`, and
the public traversal contract passed at call 21. Call 22's upstream regression exposed
incorrect broken-link-parent errno (17 instead of 2). Call 25 changed parent existence
testing to `lexists`, allowing the existing leaf mkdir path to produce the proper error.
The regression passed at call 26 (517 passed, 570 skipped), traversal passed again at
call 27 on that same final diff, and call 28 submitted. The final patch changes only
`pyfakefs/fake_os.py`: 18 added/one deleted line, below the unchanged 50-line bound.
Submission and both final current-diff checks bind to
`sha256:49f389e710954eeda0572a20547f3b3bef74603614f4bb616f8c6a6ff9e1b69a`.
Isolated evaluation accepted that artifact; its summary was not reinjected into the agent.

The run used 23 inspections (13 reads, 10 searches), five with no new coverage and no
cache hits. The editable `makedirs` header appeared in every source index from call 2
through 28. Retained source reached 23,979 characters and at most 38 observed lines were
omitted; the working-set bound was not increased. Two concern originals remained stable,
with separate progress and eight exact-repeat no-ops. All 22 annotation receipts with a
following turn arrived exactly once with matching post-batch IDs/diff. Four source-note
range citations and one unknown concern ID were rejected without blocking actions.
Both concerns were marked resolved on the existing finish turn. One resolution reason
claimed regression-suite evidence while its action ID actually named the traversal check:
the gateway verifies current successful evidence identity, not semantic relevance. The
regression did independently pass, but this mismatch remains a model annotation limitation.

Probes were offered on all 28 turns but never used. No inspection-closure warning was
needed, so probe use and the new closure-warning boundary were not live-exercised.
No provider/protocol error or output-ceiling exhaustion occurred (maximum 7,471 output
tokens). Read-only audit verified all 348 journal events, 84 context/input/continuation
artifact hashes, 27 reasoning replay edges, five final artifact hashes, and all five
public-check policy hashes with cleanup confirmed. Journal bytes hash to
`sha256:3b9f61aeb31a52cac79b77132ff2f6916f00a87453356a417c4413b94f9369aa`.
Row-25 bytes remain unchanged. Faster editing and successful repair are observations,
not causal evidence that one v18 feature improved the model. This result did not authorize
the separately approved twenty-seventh row recorded above.

### V17 implementation and validation checkpoint

V17 separates the currently focused question from up to three run-local public
verification concerns. Optional `memory_update.verification_updates` creates/revises a
concern by stable `vN` ID, resolves it using already completed successful current-diff
check/probe evidence and a short explanation, or explicitly dismisses it with a reason.
Source-note expiry, focus changes, and unrelated check PASS do not erase these concerns.
Decisions apply to their exact diff; an edit makes old resolutions/dismissals unresolved
again, with their prior evidence marked historical. A baseline probe cannot resolve a
concern on a later candidate. Provenance validation does not prove semantic relevance;
all interpretations remain model-authored and unverified by the harness.

Concern updates share the existing first-non-null batch owner and native annotation
receipt. They are validated independently of ordinary findings/focus and never reject
the main action. An unresolved concern is never silently evicted when the three-item
working set is full. The journal stores the complete concern state and ID allocator;
resume restores them without recomputing prior decisions from final source bytes.
The current list is in `working_notes.verification`. Older check cards label their
concern IDs as snapshots at that check's completion, not current resolution authority.

After the last required visible check, feedback now invites reviewing remaining public
concerns and choosing a useful available experiment or submission, instead of commanding
immediate submission. Mutation feedback likewise allows a relevant check or experiment.
No new tool, model step, mandatory experiment, finish blocker, budget reserve, or
task-specific correctness oracle is introduced. The current gate and all tool/cost/time
limits remain unchanged. Provider schemas explicitly include the new five-field operation
objects; legacy local synthetic updates may omit the new array. Old run/envelope bytes
are not migrated, and nonterminal runtime mismatch still rejects resume.

The motivating read-only row-24 analysis found that source delivery was intact, but
the model's explicit invalid-parent uncertainty was overwritten while fixing mode,
and its only probe tested the baseline. The final context still offered inspection,
probe, and mutation with eight model calls left, yet its latest check card said to
submit. The cue's causal effect on the model was not experimentally established.
V17 targets uncertainty tracking and feedback consistency, not a larger context or
harder action mask. Existing task packages and the failed submission remain untouched.
Provider-free verification passes 59 focused concern/note/guidance cases and Ruff.
The frozen complete suite passes 336 tests in concurrent groups of 156 and 180, using
separate short external temporary roots; three opt-in Docker tests were skipped.
This full-suite invocation exceeded the two-minute target; it is not an under-two-minute
full-cycle result. The integration mock exercises non-null concern updates, rejects
same-batch resolution without rejecting the check, and resolves from its completed
result on the existing finish turn, with no additional model calls. Separate mock
`run_dev_36964c96d4834891`, under `C:\pt\pl-v17-smoke-4829`, reaches isolated
`EVALUATOR_PASS` in 4.97 seconds through one mutation, four model turns and five actions:
task acceptance PASS, safety NOT_RUN, cost zero, and `claim_eligible=false`.
These tests verify memory/feedback contracts, not improved live model decisions.
That local checkpoint did not authorize the separately approved twenty-fifth live row below.

### Twenty-fifth live row: public regression failure, completion horizon exhausted

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight verified HEAD-clean
tracked runtime/task inputs, credential format, the running Docker server, and both
local pinned images. V17 commit `8e6eedcee705bab1fea5cad5d850e764ed14dae2` produced
`run_dev_553ec14ad0d4441c`: `LIMIT_REACHED`, 37 model/input-count calls, 38 actions,
three accepted mutations, $0.486200250, and 312.967 active seconds (314 seconds run age).
No second invocation, resume, image pull/build, Docker startup, or automatic retry ran.

Thirty inspections (18 reads, 12 searches) preceded the first mutation on call 31;
18 added no source coverage and five were cache hits. Call 14 had reproduced the
baseline failure of the public parent-traversal check. The first candidate then failed
that check on bytes/str path assembly at call 32. Call 33 repaired the type-mixing error;
call 34 exposed intermediate-directory permissions, which call 35 repaired. The same
public contract passed at call 36. These are two successful local causal repairs after
late initial exploration, not a more efficient episode.

Call 37's required upstream regression reported 1 failed, 516 passed, and 570 skipped.
Its public macOS broken-symlink-with-trailing-separator case now raised `FileExistsError`
instead of completing. The new normalized whole-path existence check rejects the link
before the original backend's trailing-separator/macOS handling can run. The remaining
candidate is a 40-line diff (39 additions, one deletion) in `pyfakefs/fake_os.py`, hash
`sha256:8274b62bfc5f492526b31564b713ddc8ec58107ed49f3163a55acd747a3c4e35`.
It was not submitted. With three model calls and 62 tool actions left, recovery required
at least four calls: edit, both invalidated checks, and finish. The runner recorded
`completion horizon exhausted before provider dispatch`; the final failure was retained
but there was no subsequent model turn. No private evaluation or final safety verdict ran.
Do not label this result `EVALUATOR_FAIL`, task-acceptance FAIL, or safety PASS.

Concern `v1` was created on call 1 and appeared unresolved in all 36 following contexts.
The model repeatedly revised this single item (30 upserts) rather than maintaining
separate concrete concerns. Its statement narrowed from broad preservation requirements
to bytes assembly. Call 22's sole resolve attempt cited a read, not successful check/probe
evidence; the annotation was rejected without rejecting the read, and its receipt arrived
in the next model input. The concern remained unresolved through the three mutations.
An unknown source-note ID was rejected on call 3; a first source finding was stored on
call 11. Later note-ID/source-range errors also received nonblocking receipts. There
were 35 note-update events and all 35 matched their once-only next native delivery.

Probes were enabled but unused. The run never reached all-required-checks-PASS, so the
new final-review cue and successful current-diff concern resolution were not exercised.
Persistence and failure feedback worked, but meaningful uncertainty decomposition,
candidate experiments, and earlier editing are not demonstrated by this observation.
It does not establish that v17 caused the longer exploration or the task regression.
No provider/protocol error or output-ceiling exhaustion occurred (maximum 10,974 output
tokens versus the 25,000 desired ceiling). Read-only audit verified 453 journal events,
111 context/input/continuation artifact hashes, all 36 continuation replay edges, and
five public-check execution-policy hashes with cleanup confirmed. Journal bytes hash to
`sha256:6ae215fdd26f709347c30eb0e578d5882255b231d227edec2ab9c5357859e5e0`.
Prior row-24 bytes remain unchanged. All results remain `official=false`; no claim or
twenty-sixth live row is authorized.

### V16 implementation and validation checkpoint

V16 fixes public search path matching and separates executable edit admission from
full recovery protection. Search globs are case-sensitive and repository-rooted:
`*`, `?`, and character classes stay in one component; a whole `**` matches zero or
more directories. Thus `**/*` includes root files and `pkg/**/*.py` includes both
direct and nested files. Queries remain literal. `searched_file_count` reports eligible,
successfully decoded files actually searched before any output truncation, distinguishing
an empty file selection from a missing string. Tracked/public admission, hidden-file
exclusion, output limits, cache/replay, and task scope matching remain unchanged.

An optional edit now requires its successful minimum successor: the edit, every
invalidated visible check, and finish. Full failure-recovery reserves are reported
separately in `action_horizon.mutation_completion_horizon` and the durable turn boundary.
When that minimum fits but full protection does not, `replace_text` remains available
with a bounded warning. Current-baseline completion and conditional post-edit completion
are distinct. Inspection/probes still preserve their existing protected budget; a probe
does not grant check credit, imply a semantic failure, or force mutation.

Working-note `status=current` explicitly means cited evidence is current, not that the
statement has been semantically revalidated. Each projected finding is labelled
`interpretation_status=model_authored_unverified`; durable source bodies and lifecycle
replay are unchanged. Guidance favors causal mechanisms, closing answered questions,
behavior-bearing citations, reconsidering claims after an edit, and public experiments
for new assumptions. Exact replacement guidance favors the smallest sufficient anchor
without unchanged signatures/docstrings. An obsolete mandatory targeted-read sentence
is removed from anchor-failure feedback. These are guidance changes, not a new planning
tool, semantic oracle, blanket note expiry, fuzzy mutation admission, or read cap.

The preceding diagnosis verified that row 23 retained the editable function throughout
turns 3-29 and the normalization call from turn 8; repetition was not evidence eviction.
It also found a real false-negative search at turn 3 and a latent policy disconnect:
after a hypothetical final probe, eight calls remained for a four-call edit/check/finish
path, but the old policy required twelve protected calls. No probe was attempted then,
so that disconnect is not established as the cause of the recorded task failure.
V16 addresses these defects without changing task bytes, global limits, output ceiling,
tool names/input field shapes or order, or old envelopes. The separately approved
twenty-fourth row below executes this runtime; no further row is authorized.

Verification passes 75 focused search/guidance/tool/note cases, 16 focused budget cases,
and Ruff. The frozen complete suite passed 287 provider-free tests: 107 in 90.79 seconds
and 180 in 104.29 seconds, concurrently with separate short external temporary roots.
Three opt-in Docker tests were skipped. Both groups emitted only a pre-existing repository
pytest-cache permission warning; no test failed. Mock `run_dev_ae0880944bfd4697`, under
`C:\pt\pl16-smoke-355ec8`, reaches isolated `EVALUATOR_PASS` through one accepted mutation,
four mock model turns and five actions in approximately five seconds. Task acceptance is
PASS, safety NOT_RUN, cost zero, and `claim_eligible=false`. The regressions cover the
eight-call diagnostic-to-edit path, exact minimum/tool/capacity boundaries, complete check
invalidation, warning hydration, root/nested search and cache/restart, and the distinction
between current citations and unverified interpretation. These are local contract tests,
not evidence that the live model will explore less or produce a correct patch.

### Twenty-fourth live row: public repair succeeds, task acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. Read-only preflight passed the exact
tracked runtime/task, credential format, running Docker, and both local pinned images.
V16 commit `fcc8e79b11c1f3a478f07dcd894ab995ac3c1988` produced
`run_dev_89757e404d894362`: `EVALUATOR_FAIL`, task acceptance FAIL, safety PASS,
`claim_eligible=false`, and `official=false`. It used 33 model/input-count calls,
38 actions, two accepted mutations, $0.365351250, and 290.735 active seconds
(292 seconds of run age). No retry, additional run, image pull/build, or Docker startup ran.

Call 3's recursive `pyfakefs/**/*` search examined 62 eligible files and returned both
direct-child `makedirs` definitions, exercising the corrected zero-depth glob semantics.
The first finding was created on call 8, with subsequent updates and the explicit
`model_authored_unverified` interpretation label. Call 5's extra parallel memory update
received a nonblocking diagnostic. All 26 receipts with a following model turn appeared
once in the native output, without duplication in that request's user context; the final
finish-associated note update had no following turn. There were 27 note-update events.

Call 22 ran one public Python probe against the unchanged baseline, comparing real-OS
and fake-filesystem parent-traversal side effects. Its 50-byte output showed the baseline
difference; it completed in 2.844 seconds with cleanup confirmed. This was not a check of
the later candidate or a broad semantic matrix. The first mutation was accepted on call 27,
after 25 inspection turns / 29 read-search actions and that probe. Its exact anchor still
covered 20 lines; the later repair used 15. Neither was rejected, but this does not show
that the smallest-anchor guidance was fully adopted.

Call 28's public contract check failed on intermediate-directory mode. After two reads
on call 29, call 30 correctly changed recursive parent creation to `PERM_DEF`, retaining
the requested leaf mode. Both visible checks passed on calls 31-32; call 33 submitted
the same 14-line diff (13 added, one deleted) applied by isolated evaluation:
`sha256:543cd29ddfad4c629ae22fc6d1be6a3b98ef6d14e1222ce1f5560a610d57a8b3`.
Regression and scope passed. Private acceptance passed 11 of 12 cases, but a file-as-parent
case returned `ENOENT` instead of `ENOTDIR`. That is an exception-semantics failure,
not a stale submission or token/protocol terminal; private diagnostics were not reinjected.

Across the run, 16 of 31 inspections added no source coverage, including six cache hits.
The first edit still arrived late, so efficient evidence reuse is not established.
V16's minimum-path mutation admission and separate recovery warning were visible on
turns 28, 32, and 33, but no late-probe-to-repair sequence was exercised. All provider
responses completed; the largest output was 4,503 tokens, below the unchanged ceiling.

Read-only verification passed the 410-event hash chain, 99 context/input/continuation
references, six terminal artifacts, three evaluator policy artifacts, all 32 continuation
edges, 38 unique completed actions, and the exact durable cost sum. No provider or action
remains pending. Existing run bytes, `.env`, task packages, and user-owned work were
unchanged. Further diagnosis should use public evidence to examine repeated investigation
and incomplete exception handling, without copying private cases into agent context.
This observation is not a controlled comparison or generalization claim. No twenty-fifth
live row is authorized.

### V15 implementation and validation checkpoint

V15 repairs working-note lifecycle and makes annotation outcomes actionable. Notes retain
up to 24,000 characters of actually observed source per note, independently of active
read/mutation spans. Successful mutation `action_finished` events atomically bind the
rebound/expired note state outside the public tool result. Resume restores that recorded
decision rather than comparing historical mutations with the final workspace. Public
context exposes only bounded lifecycle IDs/reasons, not the retained source bodies.

An action-associated `memory_update_result` now separates note creation/update/rejection
from the main action's status. It identifies the finding, allocated or rejected note ID,
and a concrete correction without echoing rejected prose or unknown source references.
It is delivered on the first non-null update's native tool output; the same context uses
a delivery reference. Read outputs no longer duplicate unvalidated `memory_update`, while
original function-call arguments and encrypted continuation remain unchanged. Guidance
explicitly puts unanswered questions before observation and findings after observation;
new notes use null and later revisions use the ID actually allocated. No extra model
call, planning tool, hard exploration mask, or mutation/check budget is introduced.

The preceding read-only review distinguished two problems. Row 22's initial rejection
was legitimate (`pending` was not observed); subsequent updates targeted unallocated `n1`.
Bare codes reached context but did not give a clear repair receipt. Independently, a real
Git reproduction showed an unchanged note surviving one unrelated edit, disappearing
after a second, and resurrecting on resume. V15 fixes that storage/replay defect; it does
not claim that the defect caused row 22's early errors or that better memory guarantees
faster exploration. Changed or ambiguous cited text still expires, and unobserved sources
are never accepted. V14 runs/envelopes remain immutable. The separately approved v15 row
below did not authorize another row; later runs required separate approval.

Validation passes Ruff, 54 focused note/context/input cases in 35.35 seconds, and all
244 provider-free tests. The frozen full-suite groups ran concurrently: 64 passed in
90.67 seconds and 180 passed in 115.15 seconds; three opt-in real Docker cases were
skipped. New regressions cover actual sequential Git edits, LF/CRLF, changed/overlapping
ambiguous source, no resurrection, and crash before/after durable mutation completion.
Feedback regressions preserve parallel ownership, exact original calls, nonblocking
rejections, bounded private-free receipts, and normal call counts through mock evaluation.
Final mock `run_dev_b4a45c26a2e84022`, under `C:\pt\pl-v15-smoke-0d2aaa`, reaches
isolated `EVALUATOR_PASS` through one mutation, four mock model turns and five actions:
task acceptance PASS, safety NOT_RUN, cost zero, and `claim_eligible=false`. This
implementation validation made no Docker or provider call. The later approved live
observation is recorded separately below.

### Twenty-third live row: memory feedback observed, task acceptance FAIL

The user separately approved one new `pyfakefs-makedirs-parent-traversal` v2 run with
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. Preflight verified tracked, HEAD-clean
runtime/task inputs, the credential format, Docker availability, and both fixed local
image identities without starting, pulling, or building anything. On committed v15
runtime `61dea7880eb11fa588f0b17a0b516215972bb089`, run `run_dev_ac4248e1b75e4ad2`
ended at `EVALUATOR_FAIL`: task acceptance FAIL, safety PASS, `claim_eligible=false`,
and `official=false`. It used 32 model/input-count calls, 34 actions, one accepted
mutation, $0.361692000, and 340.828 active seconds (342 seconds of run age).
Probes were enabled but the model did not invoke one. No retry or additional row ran.

Call 4 created `n1`, before any mutation. Call 5 tried to revise it using an incompletely
observed source range; the main read succeeded while the annotation was rejected with
`unobserved_source_range` and a concrete repair instruction. Call 7 successfully updated
the existing note. `n2` was created on call 16. There was no unknown-note-ID rejection.
Call 22's parallel batch also produced the intended nonblocking additional-update
diagnostic. All 22 note-update receipts were hash-verified against their exact next
native tool output, with delivery references rather than duplicate receipts in that
request's public context. At the accepted mutation, unchanged `n1` rebound and `n2`
expired as `source_changed`; the next context agreed. This row had only one accepted
mutation and no resume, so the multi-mutation/restart repair remains provider-free evidence.

The first edit attempt still arrived on call 27 after 26 inspection turns (28 read/search
actions). Its whole-method anchor accidentally joined two original docstring lines and
was correctly rejected before a write. Call 28 read source and call 29 supplied a matching
anchor with a revised recursive-parent implementation. The accepted diff added four lines
in `pyfakefs/fake_os.py`. Calls 30 and 31 passed both visible checks, and call 32 submitted
`sha256:938e6fdbe6ce41c12f30382fa620caf7622750ab5892fb6e63deb039d527451d`.
Visible checks and isolated evaluation used that identical artifact. Regression and scope
passed, but private acceptance reported one trailing-separator failure. The submitted
`head and tail` guard skips parent creation when splitting a slash-terminated path yields
an empty tail; the remaining delegate still loses the walked-directory side effect.
This is a semantic boundary-case failure, not a stale submitted patch, token ceiling,
or provider/protocol terminal. Private evaluation was not reinjected into agent context.

Across the run, 17 of 29 inspections added no source coverage, including three cache hits.
That zero-coverage count is unchanged from row 22 despite much earlier valid note creation;
the first accepted edit moved from call 27 to call 29. Coverage alone does not establish
that a read was useless, and these two rows are not a controlled memory-effect comparison.
The result confirms live note admission/feedback delivery but not better exploration,
semantic completeness, or agent success. Both long mutation responses completed below
the unchanged 25,000-token ceiling, and no protocol correction was needed.

Read-only verification passed the 389-event hash chain, all 96 context/input/continuation
references, five terminal artifacts, three evaluator execution-policy evidence artifacts,
34 unique completed actions, and the exact durable cost sum. There is no pending provider
or action; owned check cleanup was confirmed. The journal and prior external run bytes
were not changed by analysis. The later twenty-fourth row required separate approval.

### V14 implementation and validation checkpoint

V14 adds stable run-local note IDs and optional public Python experiments. Findings
are explicitly created, revised, consolidated, or removed by short `note_id`, rather
than silently replacing every statement citing the same source. At most six remain;
source validation, stale-note expiry, nonblocking diagnostics, and durable resume remain.
The prompt encourages preserving useful mechanism observations, reusing existing
behavior owners, and testing unverified assumptions without requiring a separate plan.

`--enable-probes` explicitly enables `run_probe(question, python_source)`; it is off by
default and bound into the run envelope, sandbox identity, and manifest. A probe costs
one model turn and one tool action and is offered only when the protected completion
and recovery budget remains afterward. It never grants visible-check credit or forces
an edit. Only a locally present pinned public Python image is accepted, with an exported
tracked public source snapshot and separately hash-bound trusted wrapper. No evaluator
image, Git metadata, credential file, or hidden overlay is mounted. Experiments have
8,000-character input, 30-second execution, and 12,000-byte combined output limits,
plus the shared deadline and exact-owned-container cleanup. Missing image fails
preflight; there is no automatic startup, pull, build, or host execution fallback.
Receipts bind source/snapshot/diff/image/policy identities into failure and evaluator
provenance. Completed results replay without execution; interrupted experiments may be
repeated only after owned cleanup in a fresh snapshot, not claimed as exactly-once code.

The twenty-first-row diagnosis is narrower than "the root mechanism disappeared from
memory": recorded contexts retained it, while four or five of six findings often
repeated wrapper details and a later same-source update weakened the mechanism note.
V14 supplies explicit memory maintenance and optional counterexample experiments;
it does not establish that either change makes the agent solve the task.

V14 provider-free validation passes Ruff and all 215 tests. The frozen full-suite groups
passed 64 cases in 84.63 seconds and 151 in 82.70 seconds, running concurrently with
separate short external temporary roots. Forty new cases cover note maintenance,
probe isolation and budgets, crash/resume, receipt integrity, and failure provenance.
A final receipt-validator alignment to the gateway's 500-character action-ID limit
was rechecked with all ten probe-provenance cases (6.52 seconds). Mock
`run_dev_0e6b57566f77420b`, under `C:\pt\pl-v14-smoke-final`, reaches isolated
`EVALUATOR_PASS` through one accepted mutation, four model turns, and five actions.
Task acceptance is PASS, safety NOT_RUN, `claim_eligible=false`, and cost zero. At that
implementation checkpoint, probe launches and Docker policies were mocked. Implementation
alone authorized neither Docker execution nor a twenty-second live row.

### Separately approved real Docker probe validation

The user subsequently approved downloading the fixed Python image and bounded synthetic
Docker verification, without provider calls, evaluator-image changes, or another live row.
The digest remains `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Actual preflight exposed a naming defect: Docker stores `python@digest`, whereas the
runtime used `python:3.12-slim@digest`. Matching and lookup now normalize only the optional
tag, preserving repository, registry port, and digest; probe execution uses the canonical
reference too. Eight offline identity cases cover accepted aliases and rejected mismatches.

Real isolation and completed-action replay passed in
`C:\pt\pl-probe-real-b\real-probe-evidence0` (`run_dev_probevalidation_138c96e2b7644a30`).
The probe imported current modified tracked bytes, excluded synthetic secret/hidden/Git
and untracked files, enforced non-root/read-only/process restrictions, allowed ephemeral
scratch writes, and received no mandatory-check credit. Restart replay returned the same
result without another backend call or journal mutation. The 1.33-second execution left
no container. Only synthetic fixtures were used; the repository `.env` was not read/copied.

The first output-flood case (`run_dev_probevalidation_fa022e287979467c`) preserved the
12,000-byte output bound but reported cleanup uncertainty and halted the remaining tests.
An independent exact-container inspection confirmed absence. A real subprocess-pipe
regression demonstrated that stopping readers at the retention cap strands a pipe writer.
Readers now keep draining and discarding excess bytes while the existing main-thread
cleanup runs; ownership checks, failure handling, and the five-second reserve are unchanged.

The two remaining cases passed in 10.80 seconds under
`C:\pt\pl-probe-real-c\real-probe-evidence0`. The repaired flood
(`run_dev_probevalidation_872424ac8fe54e9d`) retained exactly 12,000 bytes, returned
`output_limit`, and confirmed cleanup in 1.69 seconds. The deadline case
(`run_dev_probevalidation_48e0ec7ff40b4969`) used a 6.563-second effective timeout within
a 12-second row budget, returned `timeout`/`deadline_exhausted`, and confirmed cleanup
in 7.48 seconds. Exact-container absence was independently checked in both cases.
All four actual container attempts and the completed replay remain diagnostic evidence,
not an agent-success or full sandbox-security claim. That approval did not authorize a live row.

Final regression passes Ruff and 224 provider-free tests, with three explicit Docker
tests skipped by default. The two frozen suite groups passed 64 cases in 89.66 seconds
and 160 cases in 88.00 seconds concurrently. Mock `run_dev_f5951bf0dd474039` under
`C:\pt\pl-probe-smoke-final` reaches isolated `EVALUATOR_PASS` through one mutation,
four mock model turns, and five actions; acceptance PASS, safety NOT_RUN, cost zero,
and `claim_eligible=false`. The separately enabled Docker cases passed as described
above; these were not invoked by the default suite.

### Twenty-second live row: task acceptance PASS

The user separately approved one new run of `pyfakefs-makedirs-parent-traversal` v2,
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, repeat 1, a $1.20 invocation cap,
and `--enable-probes` under `C:\patchloop-state`. On committed runtime
`f7849c664f43cd84d3c5badfb5b9c2b8a3beb012`, run `run_dev_309a71c0c16544ed` completed
at `EVALUATOR_PASS`: task acceptance PASS, safety PASS, `claim_eligible=false`, and
`official=false`. It used 33 model/input-count calls, 36 actions, two accepted mutations,
$0.385299450, and 315.937 seconds of active execution. No provider retry, image operation,
or additional live invocation ran.

At call 13, one optional probe observed real Linux `os.makedirs` side effects for three
string paths containing `..`/`.` and one bytes path. It returned 149 output bytes in
2.937 seconds with confirmed cleanup. Its question mentioned Windows, but its code did
not exercise Windows or compare the candidate fake implementation. This is a successful
public experiment, not evidence that the probe exhaustively validated the proposed fix.
Receipt `sha256:26819db65839c3b7f7d81013ddebe43652140ae7a2bdab97a3d673bfa42bee76`
is bound into the manifest and evaluator provenance; it grants no visible-check credit.

The first accepted edit arrived at call 27, after 25 inspection turns and the probe
(27 read/search actions plus one probe). It used recursive parent creation with existing
`self.path.split`, `exists`, `isdir`, and `self.mkdir` operations instead of manually
walking normalized components. Call 28's public check correctly localized the parent-mode
assertion. After a two-action inspection batch, call 30 changed the recursive parent mode
from the caller's mode to `PERM_DEF`, retaining the caller's mode for the leaf. Both
visible checks then passed and call 33 submitted a one-file, 14-added/1-deleted-line patch:
`sha256:6e5ba56bdbfc2022e2aef341a930b8c595b2427365a27657da5eea7d29f02ef9`.
The visible checks, submission, and isolated evaluation are bound to that same artifact.

Success does not establish efficient exploration or successful early memory maintenance.
Across the run, 17 of 29 read/search actions added no source coverage, including six cache
hits. The first note cited nonexistent tool result `pending` and was excluded; the next
five tried to update unallocated `n1` and were excluded as `unknown_note_id`. Recorded
contexts exposed these diagnostics but retained no findings before the first mutation.
A valid note was first allocated at call 30, expired after its cited source changed, and
was followed by a new current-source note and later successful updates. The trace therefore
does not support attributing this pass to improved working-memory reuse. Read-only review
of note creation/feedback motivated the v15 fixes above, not a new read cap.

The journal's 390-event hash chain, all 99 context/input/continuation artifacts, six
terminal artifacts, 36 unique completed actions, and durable cost sum passed read-only
integrity checks. All 33 responses carried continuation references; no provider or action
remained pending. This is one development success on one task, not a generalization or
official-quality claim. It authorized no subsequent row; row 23 required separate approval.

The September 5 review found remaining harness defects, not evidence that model
judgment alone explained unsuccessful runs. V12 corrects truncated/empty read evidence,
CRLF revalidation, contiguous multi-span mutation admission, and unsupported traceback
execution claims. Source projection merges observed ranges, prioritizes editable and
repair evidence within 24,000 retained characters, and deduplicates the latest native
results. Bounded run-local `memory_update` notes retain source-linked model observations
and one open question; they are not verified facts, raw reasoning, or cross-run memory.

Coverage plateau and repeated causal sites are advisory. Remaining completion and
recovery budgets determine public read/search availability, including after failures.
One order-independent calculation replaces declaration-index reserves. A rejected
optional edit does not invalidate an already checked rollback baseline. Correction
resume is journal-derived. Mutation admission binds the complete candidate diff before
atomic source replacement; recovery rejects other-file drift. A shared active deadline
reaches visible checks and isolated evaluation, with label-verified owned Docker cleanup
and partial provenance retained on timeout. Cleanup uncertainty stops all repetitions.

V13 makes the provider function schema and internal decision validator identical for
non-inspection actions: `evidence_goal` is now schema-constrained to exactly `null`.
If a provider call still fails local conversion, the journal records its public tool
name, canonical argument hash, at most four validation field paths and codes, and a
truncation flag. It never stores rejected raw arguments or validation input. The same
bounded diagnostic survives decision recovery and is included in the correction; a
second violation's terminal message names the concrete tool, field, and code.

V13 validation passes seven focused schema/diagnostic/resume cases, Ruff, and all 175
provider-free tests. The independent full-suite groups pass 64 tests in 80.06 seconds
and 111 tests in 58.33 seconds, completing concurrently in about 85 seconds. Mock run
`run_dev_d22310790c4a4696` under `C:\pt\pl-v13-smoke-a` reaches isolated
`EVALUATOR_PASS` through one accepted mutation, four mock model turns, and five actions;
task acceptance is PASS, safety NOT_RUN, `claim_eligible=false`, and provider cost zero.

A provider-free reconstruction of the nineteenth row's 39 public context boundaries
compared recorded source observations with the new projector. Editable source coverage
increased in 24 turns and decreased in none. Repeated line entries fell from 1,899 to 2;
the remaining two are inside preserved parallel native outputs, not duplicated retained
source. Maximum retained source was 18,272 characters. At turn 12, visible editable
coverage rose from 74 to 139 lines. This is an observation-selection comparison only:
no model was asked to act on the reconstructed context and no success is implied.

The v12 baseline validation passed Ruff and all 175 provider-free tests. Two independent pytest
groups pass 64 tests in 77.86 seconds and 111 tests in 57.10 seconds; the final Ruff,
parallel full suite, and mock cycle takes approximately 110 seconds including orchestration.
Mock `run_dev_935f54a2c3b84b8c`, under `C:\pt\pl-v12-smoke-final-f`, reaches isolated
`EVALUATOR_PASS` through one accepted mutation, four mock model turns, and five actions.
Task acceptance is PASS, safety NOT_RUN, `claim_eligible=false`, and provider cost zero.
Fault regressions include reordered parallel-result hydration, same-action read replay,
source-linked note upsert, unconsumed correction replay, complete-candidate crash recovery,
deadline expiry before dispatch/evaluator work, and owned-container cleanup uncertainty.
Earlier checkpoint counts and policies below describe history, not the current v17
contract. No twenty-fifth live row is authorized.

The separately authorized twentieth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, `.env`, one repetition, a $1.20 cap,
and a new run under `C:\patchloop-state`. Provider-free preflight passed without an
image operation. Immutable run `run_dev_7b604196d0924a0f` ended at
`INCOMPLETE_RESPONSE` after 29 model/input-count calls, 35 actions, one accepted
mutation, and $0.293222400. It performed 23 searches and 11 reads before mutating on
call 27; seven searches were zero-match and six returned only covered lines. The model
then returned completed `reasoning + function_call` responses twice, but local conversion
discarded both calls as `invalid_dev_tool_contract`. No check, submission, or evaluator ran.

Because v12 stored neither rejected arguments nor validation locations, the exact field
in those two historical calls is unknowable. A provider-free reproduction found one
concrete schema/validator mismatch consistent with the timing: `run_check` permitted a
string `evidence_goal` in the provider schema while the internal model required `null`.
V13 fixes that mismatch and makes any future conversion failure diagnosable; it does not
reinterpret the twentieth row as proof of that field value or as an agent-quality result.
The accepted edit also passed no visible check and recursively propagated the requested
leaf mode to parents, so its semantic correctness is not claimed.

The separately authorized twenty-first row used the same exact task, model, reasoning,
credential-file, repetition, cap, and external state root on committed v13 runtime
`619d684f13ee9e06abd948cb7f3f1ee286d747b1`. Immutable run
`run_dev_8ca863c580e54a18` reached submission and isolated evaluation without a provider
or local tool-contract error. It ended at `EVALUATOR_FAIL` with task acceptance FAIL,
safety PASS, `claim_eligible=false`, 34 model/input-count calls, 41 actions, two accepted
mutations, and $0.532119000 cost. Both visible checks passed on submitted patch
`sha256:7929e83dddafaf6089f06fef823c776f7257f29663864f5c75d111fd6d09cc25`.

The row spent its first 26 model turns and 33 actions on inspection. Its first replacement
was rejected for a stale anchor, then one read allowed the same proposal to apply. The
public permission assertion failed, the model correctly changed non-final traversal
directories from the requested mode to `PERM_DEF`, reran both checks, and submitted.
This confirms the v13 schema repair and failed-check action path, but not task success.
Provider-free probes derived only from the public real-`os.makedirs` contract demonstrate
that the submitted manual component walker is incomplete: `/link/../leaf` follows the
lexical parent instead of the symlink target's parent, and a trailing `/.` applies the
requested mode to the preceding directory instead of the recursive default. These are
public counterexamples to the patch; without inspecting hidden evaluator content, neither
is claimed as the exact private failing case. The remaining concerns are semantic strategy
selection and working-memory convergence, not another justification for a fixed read cap.

## Evidence state (historical checkpoints)

Ruff, the fast suite, and mock smoke pass. The current context-projection checkpoint
passed 29 tests in 16.45 seconds. The resume checkpoint passes 39 tests in 35.15
seconds. The provenance/safety checkpoint passes 54 tests in 50.43 seconds and
reaches mock `EVALUATOR_PASS` with task acceptance PASS and safety NOT_RUN. The
post-live mutation-encoding checkpoint passes Ruff and 56 tests in 50.92 seconds;
mock smoke reaches the same evaluator boundary through one accepted
`apply_git_diff` mutation. The failed-mutation continuation checkpoint passes Ruff
and 59 tests in 50.51 seconds; mock smoke still reaches that boundary. The hunk-recount
checkpoint passes Ruff and 62 tests in 55.10 seconds. Mock run
`run_dev_8ba03a7965a048c5` reaches `EVALUATOR_PASS` through one accepted mutation with
task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero model cost.
Provider-free retrospective run `run_dev_replay_d1d2519dbd9644f9` replayed the
fourth live row's first exact raw diff through the current gateway. Recount accepted
the mutation, all three version-1 visible checks passed on canonical diff
`sha256:317ac609a2a9e555d0c38a5bf489c1dc68edd9c81457f598dbbf81fe3570d8c7`,
and the isolated evaluator applied that same diff. Task acceptance failed with
`PRIVATE_EVALUATION_FAILED` while safety passed. This separates mutation transport
from semantic task acceptance; it is not a fifth live row or a provider result.
A preserved version-1 task and new `loguru-invalid-format-feedback` version 2 now
make the central public behavior executable. In provider-free Docker validation,
the clean base and the retrospectively replayed patch both failed the new public
contract check, while a temporary public-contract correction passed all four
visible checks and reached `finish_task`. No hidden evaluator ran for that
validation. Ruff and all 63 tests pass in 54.28 seconds. Mock run
`run_dev_99bbb59c944d4c37` reaches `EVALUATOR_PASS` with task acceptance PASS,
safety NOT_RUN, `claim_eligible=false`, and zero model cost.
The post-fifth-row tool-alignment checkpoint passes Ruff and all 69 tests in
69.15 seconds. Mock run `run_dev_6374b31034c44427` reaches the same isolated
`EVALUATOR_PASS` boundary through one accepted mutation; this is provider-free
contract evidence only.
The sixth live row reached submission and isolated Docker evaluation. All four
visible checks, the submitted artifact, and the evaluator-applied patch shared diff
`sha256:e55b934c407a36807344f2f9e378c54c10283e407b063033972183ea0f43254f`.
Task acceptance reported FAIL while safety reported PASS, but the failure came from
a private literal-phrase assertion stricter than the public version-2 contract. This
is evaluator-contract evidence, not a valid negative coding-agent verdict.
Version 3 preserves every version-2 public behavior and unchanged fixture while
replacing only the private literal oracle with a semantic call-and-reference check.
Its task content hash is
`sha256:21f5f668c4f6ef85a2c1a45f4371cbd050de0e73dfcf8605a3c398413374c15b`.
Provider-free evaluator run `run_dev_v3candidate_f1bb` applied the sixth row's exact
submitted diff and reported hidden, regression, scope, and safety PASS. A separate
evaluator run `run_dev_v3reference` reports the same four-axis PASS for the reference.
A Docker matrix made the clean base fail and all six declared known-bad patches fail
acceptance. Ruff and all 70 tests pass; mock run
`run_dev_db9548d402084112` reaches `EVALUATOR_PASS` with zero model cost.
The subsequent import-contract checkpoint makes the `patchloop.dev` and
`patchloop.verifier` package re-exports lazy and gives the runner a direct evaluator
module dependency. Fresh-process regressions verify that package imports load neither
heavy module and that both `dev.contracts`-first and `verifier.policy`-first orders
work while preserving the public exports. Ruff and all 73 tests pass in 70.71 seconds;
mock run `run_dev_d309590128764086` reaches `EVALUATOR_PASS` with task acceptance
PASS, safety NOT_RUN, `claim_eligible=false`, and zero recorded cost.
A preserved `pyfakefs-makedirs-parent-traversal` version 1 and new version 2 now
make the issue's POSIX, Windows, bytes-path, and leaf-mode traversal behavior visible
through a black-box repository API check. All environment, hidden, reference,
known-bad, and audit bytes are unchanged. Version 2 has task content hash
`sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87`.
A provider-free 11-case Docker matrix made the clean base fail, accepted only the
reference, and rejected all nine declared known-bad cases. Manifest-bound evaluator
run `run_dev_pyfakefsv2reference` reported hidden, regression, scope, and safety PASS
for the same reference artifact. Ruff and all 74 tests pass in 73.40 seconds; mock
run `run_dev_55d5e74e1bd743d1` reaches `EVALUATOR_PASS` with zero recorded cost.
The seventh separately approved row used that exact pyfakefs version-2 identity,
`gpt-5.4-mini-2026-03-17`, medium reasoning, one repetition, and a $1.20 cap. Run
`run_dev_42d9c3c06c6a4be9` reached durable `LIMIT_REACHED` after 198.531 active
seconds, 40 model calls, and 86 successful read/search actions, recording
$0.27031725. Public `makedirs` source evidence was present in every context after the
first turn, including the final context with gate `needs_mutation` and one model call
remaining. The agent attempted no mutation or visible check, submitted nothing, and
ran no evaluator.
The post-seventh-row working-state checkpoint introduced a requirement for every read/search decision
to carry a bounded public hypothesis, one evidence gap, and its decision after the
result. The state is bound to action identity but excluded from the operational read
cache key, then reattached after cache lookup so revised decisions cannot receive stale
text. It survives failed reads and resume, and its decision takes precedence over the
diagnostic stagnation wording without becoming a gate. Invalid provider state becomes
a bounded protocol error without discarding completed usage. Ruff and all 78 tests
pass in 83.55 seconds. Mock run `run_dev_6c167fa301ac40c3` reaches
`EVALUATOR_PASS` with one accepted mutation, zero cost, task acceptance PASS, safety
NOT_RUN, and `claim_eligible=false`.
A subsequent no-call preflight validates the ignored, untracked repository-root `.env`
without exposing its value, confirms the version-2 task content hash
`sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87`,
and matches the local evaluator image to digest
`sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c`.
Runtime and selected task paths match HEAD, Docker is available, and model pricing is
registered. This preflight grants no provider or eighth-row authority.
One subsequent, separately approved eighth row used those exact inputs. Run
`run_dev_07ad1af07d22489c` reached durable `LIMIT_REACHED` after 299.562 active
seconds, 40 model calls, and 60 successful read/search actions, recording
$0.34786650. It accepted no mutation and ran no check, submission, or evaluator.
Every context after the first carried working state on every latest result. Thirty-five
of the 60 per-call decisions explicitly proposed a mutation, edit, patch, or apply
action if their evidence condition was met, yet the next model turns continued to
select only reads and searches. The final context still had gate `needs_mutation`, two
current working states, and one model call remaining.
The post-eighth action-coupling checkpoint replaces that non-binding per-call future
state with typed decisions for the actual calls. Its initial parallel-read contract
required complete decisions to match, and each mode had to match its tool family.
At that checkpoint, OpenAI input reconstructed the immediately preceding public
function calls and exact outputs with call-ID linkage while retaining `store=false`
and excluding raw reasoning and private material. Tool schemas were derived from the
current gate, unexecuted checks, a completion horizon, and bounded inspection leases.
Repeated evidence remains diagnostic-only; no
stagnation terminal was added. Per-fingerprint counts now survive unrelated new spans
and checks at the same diff. This was provider-free implementation evidence and did
not itself grant ninth-row authority.
Ruff and all 78 tests pass; the full suite completed in 114.69 seconds with an external
short temp root. Mock run `run_dev_198843ed55274f09` reached `EVALUATOR_PASS` in four
model turns and five tool actions through one accepted mutation, with task acceptance
PASS, safety NOT_RUN, `claim_eligible=false`, and zero model cost. Read-only historical
trace inspection found 23 inspection batches before the first mutation in both the
fifth and sixth rows, and a maximum of three repair reads between failed mutations on
the sixth row. The 24/3 leases preserve those observed successful paths.
The separately approved ninth row used the same pyfakefs version-2 task, model,
reasoning, `.env`, repetition, and $1.20 cap. Run `run_dev_b79d22f70ae44854`
ended at durable `PROTOCOL_VIOLATION` after three model calls, one successful search,
no mutation, and $0.0077223. Native function-call/result linkage worked on the second
request. Both the second and third responses then returned valid parallel inspect calls
whose call-specific rationales differed, violating the application's exact free-text
equality rule. The first correction was present in the third public context. This is a
contract terminal before the completion horizon or inspection lease was exercised.
The post-ninth provider-free correction retains enforced `inspect` mode across parallel
reads but permits each call's bounded rationale and evidence goal to differ, preserving
all of them on the batch card. No tenth-row authority follows from this correction.
Ruff and all 79 tests pass; the final full suite completed in 113.24 seconds with a
short external temp root. Mock run `run_dev_a7724af70efb4984` reached
`EVALUATOR_PASS` in four model turns and five tool actions through one accepted
mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero
model cost.
The separately approved tenth row used the same pyfakefs version-2 tuple. Run
`run_dev_8efe75f7c8c14cbd` ended at durable `INCOMPLETE_RESPONSE` after 271.046
active seconds, 28 completed provider calls and input counts, 58 tool actions, no
accepted mutation, and $0.27773415. The first 24 inspection turns completed 23 reads
and 34 searches; the lease then removed both tools exactly as configured. Turn 25
used all 4,096 output tokens as reasoning without a tool call. The correction was
followed by a valid but expected-to-fail public check on the empty diff, which reset
the consecutive correction count. Turns 27 and 28 again used all 4,096 output tokens
as reasoning, and the latter closed the row. There was no submission or evaluator.
The immutable journal records each incomplete status, ceiling, usage, output shape,
and generic error code, but not the provider's `incomplete_details.reason`; therefore
output-ceiling exhaustion is a strong trace-based inference, not a directly preserved
historical field.
The first post-tenth provider-free correction raised the desired per-call output ceiling to
25,000, while retaining pre-dispatch reduction against the invocation-wide cost cap.
That ceiling is now part of model identity and the manifest. Future incomplete reasons
are preserved in provider, decision-recovery, correction, and terminal provenance.
Ruff and all 83 tests pass; the full suite completed in about 85.5 seconds with a
short external temp root. Mock run `run_dev_5e032eaf91ec4177` reached
`EVALUATOR_PASS` in four model turns and five tool actions through one accepted
mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero
model cost. No eleventh-row authority follows from this correction.
The post-tenth provider-free successor kept that 25,000-token ceiling while fixing the
two structural boundaries exposed by the same trace. With `store=false`, OpenAI
responses request, durably store, and replay provider-encrypted reasoning in original
output order with matching calls and public results. The journal contains hashes and
counts, not ciphertext or plaintext reasoning. Missing, corrupt, reordered, or
action-mismatched continuation ends at `PROVIDER_CONTINUATION_ERROR` before another
provider or tool call. Fixed 24/3 inspection leases ceased to be action gates: actual
model/tool completion slack drives `open`, warned `last_opportunity`, and `closed`
states. Before live execution, Ruff and all 86 tests passed; the full suite completed
in 111.40 seconds (112.09 seconds wall time), and provider-free mock run
`run_dev_e961ed4d987e43b1` reached isolated `EVALUATOR_PASS`.
The separately authorized eleventh row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_36d200ed199d4377` ended at durable `LIMIT_REACHED`
after 412.811 active seconds, 40 provider calls, 94 tool actions, one accepted mutation,
and $0.449133. All 40 responses stored one encrypted reasoning item; all 39 next-turn
replays preserved reasoning, function-call, and result linkage, while the journal and
public contexts contained no ciphertext. Turns 37 and 38 completed with 12,128 and
7,469 output tokens respectively, including 11,235 and 6,402 reasoning tokens, and
both emitted mutation calls rather than repeating the tenth row's 4,096-token boundary.
After 90 read/search actions, turn 36 advertised `last_opportunity` and turn 37
recorded the `inspection_open` to `execution_only` transition. Its first diff
contained an invalid bare `@@` separator and failed closed; the exact failure was
projected next, and turn 38 emitted a complete diff changing only
`pyfakefs/fake_os.py`. Both `parent-traversal-contract` and
`upstream-fake-os-regression` passed on that diff in turns 39 and 40. No model call
remained for `finish_task`, so there was no submission or evaluator execution.
The current provider-free correction leaves the 40/100 limits unchanged. Before a
required mutation it reserves one additional call for repairing a rejected first diff,
consumes that reserve after failure, and computes `completion_possible` from actual
remaining model/tool budgets as well as mutation capacity. The exact eleventh-row shape
now reaches repair, two checks, and finish at call 40 in the scheduler regression. Ruff
and all 87 tests pass; the final full suite completed in 88.79 seconds with a short
external temp root. Provider-free mock run `run_dev_22a91101f0224925` reached isolated
`EVALUATOR_PASS` in four model turns and five tool actions through one accepted
mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero
provider cost.
The separately authorized twelfth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_2e95d3d85fd84e2d` ended at durable `AGENT_STOPPED`
after 281.422 active seconds, 39 provider calls, 76 tool actions, one accepted
mutation, and $0.3471675. All 39 responses stored encrypted reasoning and all 38
next-turn requests carried the linked continuation; no response was incomplete.
Turn 35 advertised the final inspection opportunity and turn 36 closed inspection
with five calls reserved. The turn-36 mutation applied, then
`parent-traversal-contract` failed on its public permissions assertion in turn 37.
Turn 38 proposed a one-line repair in `pyfakefs/fake_os.py`, but the mutation contract
rejected it because no current source span covered that file: accepting the preceding
mutation had invalidated its source span, while the exact current hunk remained only
in `last_successful_mutation` and inspection was closed. The agent explicitly stopped
in turn 39. There was no submission or evaluator execution.
This is a new harness boundary, not task-acceptance evidence. A post-check repair must
be allowed to use the current-diff-bound `last_successful_mutation` hunk as exact
anchor evidence, and the horizon must reserve one bounded failed-check repair and
recheck path rather than only a rejected-patch repair. Keep current-span validation
fail-closed for edits outside that hunk. At that checkpoint no paid retry or thirteenth
row was authorized; the later thirteenth row required separate authority.
The provider-free successor now emits a bounded `mutation_evidence` post-image with
the accepted mutation's current file hash and diff hash, restores it after resume, and
references its span ID from `last_successful_mutation`. A follow-up mutation may bind
that evidence automatically only when its exact current anchor overlaps the same-file
post-image; stale hashes and anchors outside the hunk still fail closed. Scheduler and
validator now share the same test for an allowed, tracked, current-hash mutation span,
so an unrelated span cannot expose an unusable mutation action. Completion slack holds
two calls for one recoverable mutation/check feedback event: repair plus recheck. The
reserve survives the first accepted mutation, is consumed by a rejected mutation or
failed check, and is reconstructed from durable batch results on resume.
A regression reconstructs calls 34–40 as final inspection, mutation, failed check,
repair, two passing checks, and finish. Ruff and all 90 tests pass; the complete suite
finished in 110.58 seconds with an external short temp root. Provider-free mock run
`run_dev_6979578141064297` reached isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost. No hidden evaluator was run
against the twelfth-row repair, and no live authority follows from this correction.
The separately authorized thirteenth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_8ce8603c45e646a9` ended at durable `LIMIT_REACHED`
after 358.811 active seconds and 360 seconds of run age, with 40 provider calls,
76 tool actions, one accepted mutation, and $0.39132225 of provider cost. All 40
responses stored continuation references, no response was incomplete, and the largest
response used 8,503 output tokens. The trace contains 35 inspection batches and 71
read/search actions; nine batches yielded no new span and the longest such sequence was
three.
Four mutation calls followed. The first patch did not apply, the second violated the
paired causal-alternative fields, and the third applied. The first public check then
failed. The final repair cited the accepted mutation's current post-image together with
two IDs copied from its historical input. The old validator treated every ID as current
and stopped at an `unknown evidence span` before using the valid post-image.
There was no submission or evaluator execution.
The then-current provider-free successor separated those roles. Exact mutation inputs
remained in append-only `action_started` provenance, while the agent-facing
successful-mutation projection contained only validated `actionable_evidence_span_ids`.
Known historical IDs on a retry could be ignored only when separate current evidence
authorized the exact anchor; arbitrary unknown IDs and uncovered anchors still failed
closed. The scheduler held independent two-call reserves for rejected-mutation and
failed-check recovery, and reconstructed both from durable batches. Two consecutive
successful zero-new-span inspection batches added a soft mutation-or-stop recommendation
without changing the tool
surface. At that checkpoint, no paid retry or fourteenth live row was authorized.
Ruff and all 92 tests pass with the full provider-free suite under two minutes using an
external short temp root. Provider-free mock run `run_dev_7fc6bc7e982343e4` reached
isolated `EVALUATOR_PASS` in four model calls and five tool actions through one
accepted mutation, with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`,
and zero provider cost. This is local contract evidence, not another live row.
A later provider-free retrospective copied the thirteenth run's journal and retained
workspace to `C:\patchloop-test\r13-exact-replay-f81d3f60`; the original journal and
diff hashes remained unchanged. The new gateway accepted the exact final mutation
arguments (`sha256:e028b39659724aba8633b76928ea6e50c9e77eda95697d7b92944a0512ce2fff`),
classified two input IDs as currently valid and one known historical ID as stale, and
produced one-file diff
`sha256:9ea4efc3b82e7456ce7c4956e8b291ac6b1ba4b28b522a1aa267637cf765fa40`
with no untracked files. This confirms the evidence-role false negative is fixed.
Against the locally present digest-pinned Docker image, `parent-traversal-contract`
passed, but `upstream-fake-os-regression` reported 8 failed, 509 passed, and 570
skipped. The failures cover existing error behavior for broken links, file parents,
empty paths, and trailing separators. `finish_task` therefore failed closed. The old
gateway had blocked a semantically relevant repair, but not a submission-ready one;
this result warrants no further harness relaxation. No hidden evaluator or provider
call ran, and no fourteenth-row authority follows.

The later separately authorized fourteenth row used the same version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap. Run `run_dev_86ccd39d36ab4379` ended at durable `LIMIT_REACHED`
after 352.610 active seconds and 353 seconds of run age, with 40 provider calls,
70 tool actions, two accepted mutations, and $0.42157950 of provider cost. All 40
responses completed with encrypted-continuation references; none was incomplete or
reported a provider error. It used 331,742 input tokens and 38,394 output tokens,
including 28,758 reasoning tokens; the largest response used 13,921 output tokens.
The row spent its first 32 turns inspecting. Turn 32 advertised the last inspection
opportunity and turn 33 closed inspection as promised. A mutation-contract failure
reopened one warned inspection turn, after which three raw Git diffs failed structural
application before turn 38 accepted the first patch. The central public check failed
on intermediate-directory mode. Turn 40 accepted a one-line repair but no model call
remained to recheck or finish, so there was no submission or evaluator execution.
The final repair used undefined `helpers.PERM_DEF` even though `fake_os.py` imports
`PERM_DEF` directly. A provider-free copy at
`C:\patchloop-test\r14-final-repair-e84b5ab9` changed only that identifier. Both
registered public checks then passed, including 517 upstream passes and 570 skips.
No hidden evaluator ran, so this is public repair evidence rather than task acceptance.
The trace confirms encrypted continuation and announced tool-policy transitions, while
exposing three product boundaries at that checkpoint: syntactically novel overlapping
spans rarely triggered the soft commitment cue, raw unified-diff serialization wasted
recovery turns, and failed-check repair could lose same-file symbol/import context while
inspection was closed. The active provider-free successor now addresses those three
boundaries with a coverage ledger, exact replacement mutation, unchanged-span
revalidation, and one reserved targeted read. No paid retry or fifteenth row is authorized.
Focused contract tests pass 76 cases in 82.29 seconds. Ruff and all 95 tests pass in
87.75 seconds using external temp root `C:\patchloop-test\r14-seam-full-c`. Provider-free
mock run `run_dev_c185114854c54ad6` reaches isolated `EVALUATOR_PASS` in four model
calls and five tool actions through one accepted `replace_text` mutation, with task
acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero provider cost. This
validates local contracts only; it does not establish that a provider will use the new
evidence or mutation interface effectively.

The later separately authorized fifteenth row used the same version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap at external state root `C:\patchloop-state`. Run
`run_dev_6013912c916d4781` ended at durable `LIMIT_REACHED` after 449.030 active
seconds and 450 seconds of run age, with 40 provider calls, 46 tool actions, two
accepted mutations, and $0.4705068 of provider cost. The actions were 22 reads, 17
searches, one visible check, and six mutation attempts. The first accepted mutation at
turn 32 produced a 49-line diff; its public check failed at the first byte assertion on
line 15. Four repair attempts then proposed the same complete 56-line candidate from
that 49-line baseline, but the gateway returned only a generic scope error rather than
the observed 49 to 56 delta and 50-line limit. Turn 40 accepted a different 48-line
candidate, but no call remained to check or submit it. No evaluator ran.

All 40 responses carried durable encrypted continuation and none was incomplete or a
provider error; the largest output was 11,133 tokens under the 25,000 ceiling. The
failure was therefore not reasoning-state loss or a response ceiling. Seventeen
searches comprised seven zero-new-coverage observations, four supporting-only gains,
and six editable gains, but query novelty was still counted as progress. In addition,
turns 38 through 40 reported `completion_possible=false` while still exposing
`replace_text`. The active provider-free successor separates query novelty from actual
public-source coverage, keeps commitment active for the current diff once triggered,
returns typed baseline/candidate scope arithmetic, and writes a pre-dispatch
`LIMIT_REACHED` terminal when the minimum path no longer fits. No sixteenth live row is
authorized by this implementation.

Initial provider-free validation passed all 103 tests but took 195.256 seconds. A
profile of the slowest context test found 495 subprocesses: policy and context getters
recomputed the same Git diff 76 times and validated the same evidence file once per
span. The successor now groups evidence by path and captures one fresh public state
snapshot per scheduler decision, shared by policy and context but never cached across
tool or recovery boundaries. The focused 68-test tool/runner suite passes in 90.497
seconds, and the full 103-test suite passes in 96.713 seconds with external temp root
`C:\pt\snapshot-full-final`, restoring the two-minute target. Ruff passes. Current-code
mock run `run_dev_030e46d9a4d84395` reaches isolated `EVALUATOR_PASS` in four model calls
and five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost. This is local harness evidence,
not provider behavior or authority for a sixteenth live row.

The later separately authorized sixteenth row used the same version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap at `C:\patchloop-state`. Run `run_dev_6c36a082c3264559` ended at
durable `LIMIT_REACHED` after 389.391 active seconds and 390 seconds of run age, with
37 provider calls, 44 tool actions, one accepted mutation, and $0.43578705 of provider
cost. It performed 27 reads, 13 searches, three mutation attempts, and one public check.
All 37 responses stored encrypted continuation references; none was incomplete or a
provider error.

Before the first mutation, the projected context already contained a current span that
covered the complete proposed source anchor. The model nevertheless supplied a shorter
overlapping `evidence_span_ids` entry twice, and the old gateway considered only those
IDs. Both attempts failed mechanically and each failure re-armed another targeted read.
Turn 36 applied a mutation; the public check then failed at line 948 because the patch
called recursive creation with an empty parent path. Three model calls remained while
the measured repair/check/finish path required five, so the pre-dispatch completion
horizon correctly terminated the run. There was no submission or evaluator execution.

The active provider-free successor removes `evidence_span_ids` from the model-facing
`replace_text` schema. The gateway now selects the most recently observed span whose
path, current file hash, and line range cover the complete exact anchor, and journals
that binding. A recovery key also limits targeted-read repair to once per baseline and
failed anchor instead of once per repeated rejection. Tool-surface identity is `v8`;
old envelopes and journals remain immutable. This addresses the two deterministic
harness losses seen before the accepted patch while leaving its semantic check failure
as agent output. That change itself authorized no paid retry; the later seventeenth row
was separately authorized.
Ruff and all 105 provider-free tests pass; the final full suite completed in 80.787
seconds with external temp root `C:\pt\pl-v8-full-0905-c`. Mock run
`run_dev_32428b48e6b341d8` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation. Task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero.

The separately authorized seventeenth row used the same pyfakefs version-2 task,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and a $1.20 cap at `C:\patchloop-state`. Run `run_dev_4b32848a5621473e` ended at
durable `LIMIT_REACHED` after 320.531 active seconds and 321 seconds of run age, with
34 model/input-count calls, 42 tool actions, four accepted mutations, and $0.393104700
of provider cost. It performed 18 reads, 16 searches, four mutations, and four failed
public checks. All four mutations used the new gateway-selected current observation;
there was no evidence-ID, mutation-format, scope, provider, or continuation failure.

The first patch failed the public inline check at line 12 on `/visible/build`. The
second patch moved the first failure to line 23, the public assertion that intermediate
`/permissions/transient` has mode `0o755`. The final implementation instead passed the
requested leaf mode `0o700` to every created path component. The third and fourth
mutations changed path joining and Windows-separator handling even though line 23
continued to fail and the later Windows section had not run. Four accepted mutations
were then exhausted; the pre-dispatch horizon correctly stopped with six model calls
and 58 tool actions remaining against a five-call path blocked by mutation capacity.
There was no submission or evaluator.

This row isolates a public failure-localization and causal-pivot boundary. Raw stderr
was durable, but `<string>:23`, its exact public assertion, recurrence across diffs,
unobserved later source, and remaining mutation pressure were not joined into one
prominent state. Tool surface `v9` adds that bounded `current_public_failure` focus for
safely mapped inline Python checks, retains raw signatures separately, compares semantic
sites across diffs, survives reads and resume, and grounds causal guidance in the
current public statement. It makes no task-specific mode inference and adds no semantic
hard gate. No Docker operation, provider call, eighteenth live row, submission, or
hidden evaluation is authorized by this provider-free change.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass
in approximately 70.5 seconds with external temp root `C:\pt\pl-v9-full-a`. Mock run
`run_dev_dd14cc24d3fa46ef` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation; task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero. This verifies local wiring,
not a provider causal pivot or task-quality improvement.

The separately authorized eighteenth row used the same pyfakefs version-2 task, model,
reasoning, credential path, repetition, cap, and external state root. Immutable run
`run_dev_092cb8494e254124` ended at `AGENT_STOPPED` after 62.563 active seconds and
63 seconds of run age, with nine model/input-count calls, 16 tool actions, one accepted
mutation, one failed public check, and $0.078825000 of provider cost. It performed six
reads, seven searches, one mutation, one check, and one stop. There was no provider or
continuation error, submission, or evaluator execution.

Tool surface `v9` correctly mapped the failure to public inline line 10 and preserved
the current mutation post-image. The model then explicitly identified the redundant
final `FakeFilesystem.makedirs(normalized_path)` call as the cause of `FileExistsError`
and proposed removing or conditioning it. The scheduler nevertheless exposed only
`read_file` and `stop_task`: one old boolean treated a targeted read opportunity as a
mandatory predecessor and hid `replace_text`. Because no unresolved public evidence gap
remained, the system prompt made the ceremonial read unjustified and stop was a coherent
choice. This is a deterministic action-policy contradiction, not a failure of v9 failure
localization or missing model insight.

Tool surface `v10` separates targeted-read availability from required inspection. With
current exact mutation evidence, `replace_text` is immediately available and one
path-restricted `read_file` is merely optional when protected completion slack remains.
Without current anchor evidence, the restricted read remains required and is counted in
the minimum completion path. The gateway still validates exact current evidence, scope,
rollback, checks, and submission fail-closed; no task-specific repair is encoded.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass in
71.998 seconds with external temp root `C:\pt\pl-v10-full-a`. Mock run
`run_dev_b5d5b2473d6a414f` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation; task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero. This validates local action-
space wiring, not live use of the newly exposed repair.

The separately authorized nineteenth row used the same pyfakefs version-2 task, model,
reasoning, credential path, repetition, cap, and external state root. Immutable run
`run_dev_87185b3ce20a4333` ended at `LIMIT_REACHED` after 341.375 active seconds and
342 seconds of run age, with 39 model/input-count calls, 44 tool actions, two accepted
mutations, and $0.472921050 of provider cost. It performed 25 reads, 13 searches, three
replacement attempts (one rejected and two accepted), and three public checks. All 39
responses carried encrypted reasoning continuation. There was no submission or
evaluator execution.

The first replacement used stale docstring text in its exact anchor and was rejected.
After a targeted read, the next mutation implemented recursive parent creation. The
`parent-traversal-contract` check failed at its public intermediate-directory `0o755`
assertion. Tool surface v10 correctly exposed both immediate `replace_text` and one
optional targeted read. The model used that read to find `PERM_DEF`, repaired the parent
recursion, and the contract passed. The later `upstream-fake-os-regression` check then
failed two public broken-parent-link cases: expected `ENOENT`, observed `EEXIST`. At that
point one model call remained against a four-call repair, two-check rerun, and finish
path, so the pre-dispatch horizon correctly stopped the row.

This row confirms the v10 action-mask repair and isolates two later scheduling defects.
The sticky commitment was advisory only, so 33 inspection turns could consume nearly
all completion slack. The single shared failed-check allowance was then consumed by the
first check and did not protect a repair path for the distinct second check. Tool surface
`v11` makes the next batch after two consecutive zero-coverage batches a warned final
parallel inspection. New coverage resets the current plateau and reopens exploration;
another zero-coverage batch closes broad read/search for the current diff without a new
terminal or any restriction on targeted recovery reads. It also reserves one recovery
path per distinct visible-check ID, bounded by remaining accepted mutations and sized to
rerun earlier declared checks invalidated by a repair. No pyfakefs-specific solution is
encoded.
Focused scheduler tests and Ruff pass. All 109 provider-free tests pass in 77.62 seconds
with external temp root `C:\pt\pl-v11-full-0905-c`. Mock run
`run_dev_54650ea291e24cd0` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation; task acceptance is PASS, safety is
NOT_RUN, `claim_eligible=false`, and provider cost is zero. This is local scheduler and
wiring evidence, not live task-quality evidence.

Read-only hydration of the third live journal recovers its full failed-diff hash,
hypothesis, `loguru/_handler.py` anchor, and patch line 27. The first live row ran on
2026-09-02:
`loguru-invalid-format-feedback`, `gpt-5.4-mini-2026-03-17`, medium reasoning,
one repetition, and a $1.20 invocation cap. Run `run_dev_e89e940c0715474e`
reached a durable `LIMIT_REACHED` terminal in 141.147 seconds after 39 model
calls and 99 successful read/search actions. It accepted no mutation, submitted
nothing, ran no evaluator, and recorded $0.07907685 of provider cost.

After the local reliability plan, a second separately approved row repeated the
same task, model, reasoning, repetition, and $1.20 cap. Run
`run_dev_9939bd27c5d04819` reached durable `LIMIT_REACHED` after 209.250 active
seconds, 40 model calls, and 92 tool actions, recording $0.25888155. All 39 prior
tool batches were present in the next context and 39 exact requests used the
evidence cache. Unlike the first row, the agent attempted mutation twice, on turns
36 and 39. Both attempts used `*** Begin Patch` wrappers and were rejected because
the runtime required a raw Git diff. It accepted no mutation, submitted nothing,
and ran no evaluator.

After the mutation wire contract was made explicit, a third separately approved
row again used the same task, model, reasoning, repetition, and $1.20 cap. Run
`run_dev_ef58e14b40834f0b` reached durable `LIMIT_REACHED` after 172.780 active
seconds, 40 model calls, and 94 tool actions, recording $0.24390525. On turn 3 the
agent called `apply_git_diff` with the required raw Git-diff prefix, so the renamed
provider tool contract was accepted. The first hunk declared 20 post-image lines
but contained 21, and fail-closed `git apply --check` rejected it at the following
hunk header with `corrupt patch at <stdin>:27`. That exact failure appeared in the
next canonical context. The remaining 37 turns returned to read/search only. No
mutation was accepted, nothing was submitted, and no evaluator ran.

After failed-mutation continuation was implemented, a fourth separately approved row
used the same task, model, reasoning, repetition, and cap. Run
`run_dev_dd7c981c6d024bcf` reached durable `LIMIT_REACHED` after 293.264 active
seconds, 40 model calls, and 72 tool actions, recording $0.343095. It attempted 13
raw-diff mutations. Every failure appeared exactly in the next context, and the
repair card remained present in all 23 turns after the first failure. All 13 diffs
still had incorrect hunk totals and none applied. A read-only
`git apply --check --recount` accepted all 13 exact diffs against the retained
isolated workspace; that establishes structural applicability after recount, not
semantic correctness. No visible check, submission, or evaluator ran.

After hunk recount and the version-2 public contract were implemented, a fifth
separately approved row used the same model, reasoning, repetition, and $1.20 cap
on task version 2. Run `run_dev_329131da9a4940c3` reached durable
`PROTOCOL_VIOLATION` after 140.703 active seconds, 29 model calls, 55 tool actions,
one accepted mutation, and $0.1743726 of recorded cost. The contract, basic-format,
and patcher-field checks passed on that diff. The remaining
`upstream-format-regression` was not called before two completed provider responses
contained no function call, so no submission or evaluator followed. A later
provider-free run of that exact remaining public check against the retained diff
passed 20 tests. This is public check evidence only; it is not part of the immutable
live run and is not task acceptance.

After the tool contract was aligned, a sixth separately approved row used the same
version-2 task, model, reasoning, repetition, $1.20 cap, and external state root.
Run `run_dev_f1bb02f3e3154bb8` reached durable `EVALUATOR_FAIL` after 227.735 active
seconds and 229 seconds of run age. It made 38 model calls and 68 tool actions,
accepted one mutation, submitted one changed file, and recorded $0.26552445. All
provider responses contained at least one function call. All four visible checks
passed on the submitted diff, and the evaluator applied that identical artifact.
Regression and scope passed and typed Docker safety was PASS. Task acceptance failed
only because the private oracle required a particular example spelling even though
the public contract explicitly allowed equivalent wording. Version 2 therefore has
an acceptance-oracle mismatch and remains frozen as evidence.

The end-to-end live path reached an evaluator summary within the 30-minute row limit;
it did not produce a contract-valid task-acceptance result. See
[Evidence and limitations](evidence.md) for the exact observation and limits.

Historical executables are recoverable at checkpoint `b71ddeee`; immutable
historical artifacts and `docs/archive/` remain preserved. Current checkout
compatibility with those runners is intentionally unsupported.

## Next decision

Preserve rows 26-29 as immutable evidence. V22's local tests establish the native episode
and replay contract, not improved agent efficiency or semantic success. Evaluate a future
separately approved row along distinct axes: full-history delivery and reported reasoning
mode; first useful edit and repeated answered questions; optional note/experiment use;
correct public repair and final acceptance. Do not equate delivered ciphertext with actual
reasoning reuse, or infer feature causality from uncontrolled row comparisons. Keep private
feedback out of coding-agent inputs. Do not add mandatory notes/probes, weaken source
validity, tighten action masks, or raise limits merely from the row-29 outcome.
Neither uncontrolled row comparisons nor this reused development task establish
generalization. No automatic repair, retry, resume, or thirtieth live row is authorized.

The preceding decision after row 25 was:

The twenty-fifth row confirms bounded concern persistence and nonblocking annotation
feedback, but not effective use of those concerns: the single item was repeatedly
rewritten, no probe ran, and the first edit was delayed until call 31. Public bytes and
mode failures were repaired; a later public compatibility regression could not be
recovered within the remaining completion horizon. Review source-note reuse, concrete
uncertainty tracking, and preservation of existing backend responsibilities before
proposing another change. Do not infer that a larger budget or harder inspection mask
is the remedy, and do not convert this one uncontrolled observation into a causal claim.
No automatic repair, retry, or twenty-sixth live row is authorized by this result.

The preceding decision after row 24 was:

The twenty-fourth row exercises the corrected recursive search, explicit note-interpretation
labels, and minimum-versus-protected mutation admission. It also recovers from a public
permission failure and submits an identical checked artifact. Those working paths did not
establish efficient exploration or complete semantics: 16 of 31 inspections added no source
coverage, the first edit came on call 27, and the submitted code returned the wrong error
for a file-as-parent case. The only probe examined the baseline, not the edited behavior.
The subsequent read-only diagnosis identified lost unresolved concerns and unconditional
submission feedback alongside the model's incomplete exception handling. V17 now implements
independent concerns and current-diff evidence-backed decisions without adding hard gates.
Local regressions can verify these contracts, not prove that the live model will use them
well or solve the task. A future separately approved run can observe that behavior.
Do not promote private cases into model prompts, infer causality from uncontrolled row
comparisons, or default to a harder read cap or larger token budget. No twenty-fifth row
is authorized by implementation or local validation.
Earlier decisions below are historical context.

The first live failure exposed a context-projection defect: successful reads were
selected by lexicographic span hash, so requested source could disappear from the
next stateless request and trigger repeated inspection. The second live row provides
bounded evidence that complete latest-batch projection and exact-request caching now
operate in a live loop. The third row confirmed raw-diff tool selection but exposed
failed-mutation displacement. The fourth row shows that displacement is fixed: the
agent kept seeing the exact failed diff and attempted 13 replacements. The fifth row
then confirmed live mutation and three public-check passes, but stopped before the
fourth public check and submission. The sixth row confirms required tool selection,
complete visible-check traversal, submission identity, evaluator execution, and typed
safety in one live path. Its task-acceptance failure instead exposes a version-2
public/private oracle mismatch. The seventh row then exposed a distinct
action-selection/commitment failure after sufficient public evidence; it did not
exercise mutation, checks, submission, evaluation, or safety.
The eighth row confirms that failure persists even when the model's own bounded
decision is projected exactly into the next turn. The ninth row did not retest that
behavior because a cross-call free-text equality rule terminated first. The tenth row
confirms that the then-current public call/result continuation, completion horizon,
and 24-turn inspection lease operated live. Its failure moved to the response boundary:
once reads were removed, three reasoning-only responses each consumed the complete
4,096-token ceiling before a tool call, with one valid public-check batch between them.
The new encrypted continuation and completion-slack policy directly replace those two
structural mechanisms; increasing the ceiling remains only auxiliary headroom.
The eleventh row confirms both replacements live: every continuation edge linked, reads
remained available beyond turn 24, the last opportunity was announced, and the closed
tool surface elicited a mutation rather than another incomplete response. Its first
malformed diff was repaired on the next turn and both visible checks passed. The new
failure boundary is narrower: the horizon retained only the best-case four-call path,
so that one repair consumed the call needed for finish.
The twelfth row confirms the added rejected-patch reserve itself live: inspection
closed at turn 36, the first mutation applied, and the next turn ran the central
visible check. That check exposed a semantic permission defect. The model then formed
a bounded one-line repair, but the gateway required a current source span that its own
successful mutation had invalidated and could no longer be reread. Even if admitted,
three remaining calls could not cover repair, both checks, and finish. The next seam
was therefore current-hunk repair evidence plus one bounded failed-check recovery path,
not a larger global token or turn limit. The provider-free successor now implements
that seam while leaving the global limits unchanged.
The thirteenth row exercised that post-image path and produced a semantically targeted
repair, but exposed two residual harness couplings. Historical pre-image IDs were still
projected beside the current post-image and were validated as if all remained actionable;
the first stale ID rejected the whole call. Separately, a mutation-format failure had
already consumed the one shared recovery allowance before the visible check failed.
The current change removes historical IDs from the actionable projection, retains them
only as provenance, and splits mutation-failure and check-failure reserves. Its soft
zero-gain signal addresses repeated inspection as guidance rather than a new terminal or
tool mask. The evidence therefore points to evidence-role classification and recovery-
budget accounting, not a need to raise the global 40-call limit.

Deterministic hunk recount was the correct narrow fix for the malformed line totals in
the earlier Loguru rows: the retrospective replay confirms that it accepts one exact
provider-emitted diff while preserving canonical submission identity. The fourteenth
row supplies different evidence. Even with recount and exact failure feedback, the
model spent three tail turns reserializing corrupt hunks. The active interface therefore
moves mechanical diff construction into the gateway as `replace_text`; this is not a
stronger repeated-read terminal and does not repair arbitrary model intent. The replayed
Loguru patch passed all version-1 visible checks but failed task acceptance, exposing a
separate public-feedback boundary: those checks covered valid-format regressions but did
not execute the issue's missing-key and catch behavior.

Task version 2 preserves version 1 and adds one black-box visible check derived only
from the public issue and repository API. It exercises actionable missing-key
feedback, available record-key reporting, the canonical `logger.bind()` /
`{extra[key]}` guidance, and both catch modes without requiring an implementation
shape or exact full sentence. Its task content hash is
`sha256:61704553b8ba733bad7350561eec397a7a6c04365a56ef61854a9e12cefe259d`.
The fifth and sixth rows used this exact identity. Version 3 preserves version 2 and
accepts the semantics promised publicly rather than one literal phrasing. The sixth
row's submitted patch passes the version-3 evaluator provider-free, but that does not
retroactively change the version-2 terminal. The eighth through fourteenth live
observations used the separate pyfakefs task described below. The fourteenth row is
terminal and no retry or fifteenth live row is authorized.

The fifth row's terminal label described the application's tool-batch boundary, but
the stored evidence did not establish that the provider response itself was
malformed. Both
zero-tool responses completed and consumed output tokens, while the old adapter
discarded non-function output without recording its shape. More importantly, the
request allowed a zero-tool response even though the runner rejected one; the
context exposed only three recent checks rather than a complete current-diff status,
and every successful-check card incorrectly asked what the public “failure” had
falsified. The correction therefore aligns the request and runner with required
tool choice, projects all current check states and the exact remaining IDs, fixes
PASS guidance, records content-free response-shape metadata, and provides a
structured unsuccessful `stop_task`. Protocol recovery now counts consecutive
violations and resets after a valid tool batch. None of these changes reinterpret
the fifth row as a submission or evaluator result.

Operational resume uses an immutable envelope, exact contract comparison,
run-lifetime locking, journal-derived counters and cost, durable tool-decision replay,
and mutation reconciliation. Pre-envelope runs remain immutable and non-resumable.
Runtime and task content are byte-bound; the manifest precedes evaluation; task
acceptance and safety remain separate typed axes. That checkpoint authorized no retry;
the later thirteenth through twenty-fourth rows were separately authorized and are now
terminal. No twenty-fifth row is authorized.

The unrelated local import edge is now fixed. Package initialization no longer
eagerly imports the development runner or evaluator core, while the existing
`patchloop.dev.run_dev` and `patchloop.verifier.EvaluationEngine` exports resolve on
first access. The runner imports the concrete evaluator module directly. Fresh-process
tests cover both formerly order-dependent imports; no task, evaluator rule, or live
evidence changed.

The first distinct post-Loguru task is provider-free validated:
`pyfakefs-makedirs-parent-traversal` version 2 preserves version 1, exposes its core
public behavior as a visible check, and passes the reference/known-bad contract
matrix. Its seventh live row nevertheless spent all 40 model calls on successful
read/search actions and ended before mutation. The exact source remained visible, so
the next seam was turn-to-turn decision continuity, not another task revision. That
post-seventh provider-free seam carried `working_hypothesis`, `evidence_gap`, and
`decision_after_result` through successful, failed, cached, and resumed reads. The
eighth row proved the projection works live but did not change tool selection: all 60
actions were reads/searches even though 35 recorded decisions explicitly contemplated
mutation. Nine cache hits and 21 zero-new-span results produced no stagnation signal;
that remains a secondary observability defect, not the cause or grounds for a hard
terminal. The provider-free correction couples each typed decision to its actual tool
family, replays the preceding public tool exchange as native Responses items, and at
that checkpoint removed exploration tools at either the completion horizon or the
inspection lease. The ninth row confirms public call/result continuation but exposes
the separate mistake of requiring distinct parallel actions to duplicate the same
free text exactly. That
relational check is now removed while common `inspect` mode and all action-level
decisions are retained. Local trace/policy verification still preserves the observed
successful 24/3 paths as history, not as a sufficient-information rule. The tenth row
exercises the old general lease and exposes the separate 4,096-token response ceiling.
The active provider-free successor keeps the 25,000-token desired ceiling under the
existing cost admission, records exact future incomplete reasons, replays encrypted
reasoning across stateless turns, and derives inspection availability from completion
slack with bounded recovery reserves. `completion_possible` reports the best path,
while `protected_completion_possible` reports whether that path plus unused recovery
allowances still fits. The twelfth row exposed the post-check repair evidence and
horizon boundary. The thirteenth then exposed stale provenance in the actionable list
and the single shared allowance. The subsequent provider-free successor separated both
evidence roles and failure reserves, and added only a soft zero-gain commitment signal.
The fourteenth row confirms those two corrections but exposes the narrower mutation-
wire, evidence-saturation, and failed-check repair-context boundaries described above.
The fifteenth row confirms exact replacement and the targeted-check path, then exposes
three deterministic harness defects: query novelty masquerading as coverage, generic
scope-failure feedback, and mutation availability after the completion path was already
impossible. The current provider-free successor measures only new public-source lines,
separates editable from supporting coverage, keeps a same-diff commitment signal sticky,
returns complete candidate scope arithmetic after rollback, and terminates before a new
dispatch when minimum completion resources are unavailable. The sixteenth row exercised
these progress, scope-feedback, and pre-dispatch horizon contracts: the horizon stopped
correctly, while model-selected evidence IDs still wasted four calls before mutation.
Tool surface `v8` removes that join key and prevents the same failure lineage from
replenishing targeted reads. The separately authorized seventeenth row confirmed that
binding on all four mutations, then exposed the public failure-localization and causal-
pivot boundary now addressed by tool surface `v9`. The separately authorized eighteenth
row confirmed that focus and the model's correct repair diagnosis, then exposed the
mandatory-read action mask. Tool surface `v10` makes that read optional when current
post-image evidence already supports `replace_text`. The separately authorized
nineteenth row confirmed that repair path, then exposed repeated investigation and the
single shared failed-check reserve. The initial `v11` response closed broad inspection
after a warned zero-coverage batch and reserved recovery by check declaration order.
The subsequent review did not establish that stronger action masking was the right
remedy: it found projection, evidence, reservation, and recovery defects. `v12` replaced
those policies with the working-memory and budget-only contracts above. The twentieth
row exercised that context but exposed the provider-schema mismatch now fixed in `v13`.
The twenty-first row crossed that repaired boundary, recovered from a public check failure,
and submitted, but still spent 26 turns inspecting before its first edit and chose a broad
manual path walker with publicly reproducible semantic gaps. This is evidence for better
decision memory and edit-strategy guidance, not grounds for another hard action mask.
The twenty-second row then passed with a recursive edit and correct mode repair, while
still exposing repeated exploration and unsuccessful early note creation. The twenty-third
row exercised v15 note feedback successfully but retained repeated exploration and failed
one semantic acceptance case after submission. The twenty-fourth row then exercised the
v16 search/admission fixes and public permission repair, but still explored late and failed
exception semantics after submission. No paid retry or twenty-fifth row is authorized.

A confirmatory lane is not considered until three distinct tasks submit without a
harness/contract terminal and at least two privately pass. That threshold opens a
design review only; it does not support a quality or generalization claim.
