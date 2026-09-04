# Current status

`dev-head` is the only active coding-agent runtime. It is mutable, development-only,
and always records `official=false`. The available commands are `patchloop dev`,
`patchloop doctor`, and `patchloop task validate`; legacy Rapid and provider-backed
claim commands are absent.

## Targets and limits

- focused local validation: under 2 minutes
- default one-row live limit: 1,800 seconds
- 40 model calls, 100 tool actions, and 4 accepted mutations
- one consecutive protocol/incomplete correction and at most 4 parallel reads
- completion-slack inspection with one warned final opportunity, independent bounded
  two-call mutation/check recovery reserves, and a non-blocking zero-gain commitment
  signal; legacy 24/3 counters are telemetry only
- `repeat=1` by default, 6 maximum, under one invocation-wide cost cap

## Authority

Mock execution carries no provider authority. One exact live `patchloop dev`
invocation authorizes only its declared `dev-train` task, model, credential file,
repeat count, and positive total cap. It never authorizes an image pull/build,
another task, an automatic retry after uncertainty, or a confirmatory claim run.

Repository policy alone never initiates paid work. The thirteen live observations below
were separately authorized. None authorized an image pull/build, automatic
Docker startup, transport retry, or additional row.

## Evidence state

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
The current provider-free successor separates those roles. Exact mutation inputs remain
in append-only `action_started` provenance, while the agent-facing successful-mutation
projection contains only validated `actionable_evidence_span_ids`. Known historical
IDs on a retry may be ignored only when separate current evidence authorizes the exact
anchor; arbitrary unknown IDs and uncovered anchors still fail closed. The scheduler
now holds independent two-call reserves for rejected-mutation and failed-check recovery,
and reconstructs both from durable batches. Two consecutive successful zero-new-span
inspection batches add a soft mutation-or-stop recommendation without changing the tool
surface. No paid retry or fourteenth live row is authorized.
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

Deterministic hunk recount remains the correct mutation-wire fix, not a stronger
repeated-read terminal or replacement mutation interface. The retrospective replay
now confirms that it accepts one exact provider-emitted diff while preserving the
canonical submission identity. That patch passed all version-1 visible checks but
failed task acceptance, exposing a later public-feedback boundary: those checks
covered valid-format regressions but did not execute the issue's missing-key and
catch behavior.

Task version 2 preserves version 1 and adds one black-box visible check derived only
from the public issue and repository API. It exercises actionable missing-key
feedback, available record-key reporting, the canonical `logger.bind()` /
`{extra[key]}` guidance, and both catch modes without requiring an implementation
shape or exact full sentence. Its task content hash is
`sha256:61704553b8ba733bad7350561eec397a7a6c04365a56ef61854a9e12cefe259d`.
The fifth and sixth rows used this exact identity. Version 3 preserves version 2 and
accepts the semantics promised publicly rather than one literal phrasing. The sixth
row's submitted patch passes the version-3 evaluator provider-free, but that does not
retroactively change the version-2 terminal. The eighth through thirteenth live
observations used the separate pyfakefs task described below. The thirteenth row is
terminal and no retry or fourteenth live row is authorized.

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
the later thirteenth row was separately authorized and is now terminal. No fourteenth
row is authorized.

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
and the single shared allowance. The current provider-free successor separates both
evidence roles and failure reserves, and adds only a soft zero-gain commitment signal.
No paid retry or fourteenth row is authorized.

A confirmatory lane is not considered until three distinct tasks submit without a
harness/contract terminal and at least two privately pass. That threshold opens a
design review only; it does not support a quality or generalization claim.
