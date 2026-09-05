# Internal implementation guide

This is the agent-only companion to the required root `AGENTS.md`. It summarizes
active contracts for navigation; checked-in source remains the behavioral authority.

## Source map

```text
patchloop/dev/runner.py   loop composition, gates, context, terminal handling
patchloop/dev/tools.py    tool grammar, spans, mutations, checks, finish
patchloop/dev/state.py    append-only JSONL, action/provider recovery
patchloop/dev/cost.py     reviewed prices and pre-dispatch admission
patchloop/agent/model.py  journal-managed Responses adapter, zero retries
patchloop/repository.py   audited checkout, workspace, full diff
patchloop/sandbox/        registered local/Docker checks
patchloop/verifier/       separate private evaluation and static policy
patchloop/contracts.py    task, manifest, result, and evaluator models
tasks/                    public/private packages and declared checks
```

## Loop and tool contract

The only runtime is mutable `dev-head`. Its public workflow gates are
`needs_mutation`, `needs_visible_checks`, and `ready_to_submit`; there is no plan
state or plan tool.

One model response may request either, when that tool family is exposed by the
current gate and action horizon:

- 1–4 parallel `search_files` and/or `read_file` calls, or
- exactly one `replace_text`, `run_check`, `finish_task`, or `stop_task` call.

Every call requires one bounded public `turn_decision` with `mode`, `basis`, and an
`evidence_goal` only for inspection. Mode must match the requested tool family.
Parallel reads all use `inspect` mode, while each call may state the distinct rationale
and evidence goal for its concrete query or range. These are actions selected from
preceding public evidence, not promises about unseen results, a plan phase, or a
reasoning transcript.

The provider request uses required tool choice, and the application validates the
smaller batch grammar above. Mixed, empty, duplicate-action, and oversized batches
receive one short correction. A second consecutive protocol/incomplete violation
terminates the row; any valid completed tool batch resets the correction allowance.
Optional inspection remains available only while both model-call and tool-action
budgets exceed the minimum path through mutation, all required checks, and finish plus
bounded allowances: two calls for rejected-mutation recovery and one failed-check path
per distinct visible-check ID, limited by remaining accepted mutations. Check index `i`
reserves `3 + i` calls for a missing-anchor targeted read, one replacement, that check,
and every earlier check invalidated by the repair. After failure, retain
`replace_text` immediately when current post-image evidence exists; offer the restricted
read beside it only with optional slack. Require the read only when that current exact
anchor is absent. Each allowance remains held until its matching failure; consuming one
does not erase the other. `completion_possible` separately reports whether
the actual remaining budgets cover the best-case path;
`protected_completion_possible` includes the unused allowance. Neither is an alias
for mutation capacity.
With one optional turn left, expose reads with `last_opportunity` and tell the model
they close next; with none, remove them and record/project `tool_policy_transition`.
Reopen them through the same transition when a changed gate restores slack. A first
source read required to establish a mutation anchor belongs to the minimum path. The
legacy 24/3 counters are telemetry, never an action mask. Corrections must be generated
from the actual allowed-tool set and must not name a missing tool.
`first_search_observation` is query-novelty telemetry only. Marginal gain requires at
least one newly covered line from a tracked public source and is split into editable and
supporting coverage. A zero-match, covered-only, shifted, or contained observation is
not progress merely because its query or span hash is new. When a current anchor exists,
two consecutive zero-coverage inspection batches make the next parallel batch a warned
final opportunity in context and `turn_started`. If it adds coverage, reset the current
plateau and reopen exploration while retaining advisory commitment history. If it adds
none, close broad read/search for that diff with `evidence_plateau`; this is neither a
terminal nor a block on targeted recovery reads. Clear it after successful mutation or
check/completion transition.

An unexecuted `run_check` may be available on the first turn while the action horizon
has slack; on a changed diff it is direct completion work. A check that already failed
is not offered again on the same diff. A failed check with current exact mutation evidence
offers `replace_text` immediately and, if protected slack remains, one optional
path-restricted `read_file`; `targeted_check_repair_required` is true only when the
current anchor must first be reacquired. `finish_task` is exposed only for a non-empty
diff with no untracked files after all visible checks pass on that exact diff.
`stop_task` is always exposed as an explicit unsuccessful terminal; it never submits
or evaluates.

## Mutation and causal pivot

`replace_text` accepts one exact occurrence of `old_text` and its `new_text` in one
tracked, existing, allowed public file. The model never serializes patch headers or
hunk counts. The gateway verifies the current file and evidence anchor, performs the
replacement, then derives the bounded Git diff and canonical full worktree diff used
by checks and submission. It rejects stale or out-of-range occurrences, newline ambiguity,
untracked files, new paths, and scope violations, and restores the exact pre-image on
failure. The mutation also requires:

- `hypothesis`
- `expected_behavior`
- exact `path`, `old_text`, `new_text`, and occurrence

The model does not select or serialize evidence IDs for mutation. The gateway finds
all previously observed public spans whose path and file hash are current and whose
line range covers the complete exact anchor, then deterministically binds the most
recent one. It journals that span ID and the admitted anchor range, but projects only
whether current post-image evidence remains available. No covering current span is an
`evidence_invalid` failure with the required path/range; evidence validation remains
fail-closed.

Before invalidating edited-file
pre-image spans, a successful mutation revalidates any unchanged, uniquely occurring
span against the post-image hash. It also registers one bounded replacement post-image
span bound to the current file and diff hashes. Those spans can authorize a same-file
repair only when the exact current anchor overlaps one; an edit elsewhere still
requires a current read/search span. Resulting paths, file count, line count, dependencies, tests,
and public API remain constrained by the public task. If one public failure signature
repeats across two distinct diffs, the next
mutation additionally requires `falsified_prior_hypothesis` and
`alternative_mechanism`; this never creates a separate planning turn.

Project `mutation_scope_budget` before mutation with complete current-diff lines/files,
limits, and remaining headroom; headroom is not the replacement's line count. If the
complete candidate violates scope, roll back first and return typed baseline, candidate,
delta, actual, limit, and overage fields. Record the restored baseline as the failed
result's workspace hash. A scope or general replacement-contract failure permits only a
viable `replace_text` or `stop_task`; `anchor_invalid` and `evidence_invalid` permit one
targeted read of the failed path before repair. A recovery key binds that opportunity
to the baseline diff plus path, old text, and occurrence; repeating the same failed
anchor does not re-arm it, while a materially different anchor starts a new lineage.
Broad inspection never reopens solely because mutation failed.

## Context boundary

The deterministic context artifact puts current workflow gate, remaining budget,
action horizon, mutation readiness, mutation scope budget, and the bounded evidence
ledger before the larger task text. It also contains the public task, current full diff, the exact latest tool
batch, a recency-ordered current-source working set, recent visible-check output, the
complete current-diff check status, exact remaining check IDs, bounded
`last_successful_mutation`, bounded `last_failed_mutation`, and the latest three
batch-level attempt-result-next-question cards. The ledger merges covered line ranges
per path and records canonical search observations and the latest public inspection
intent; it stores neither raw reasoning nor semantic claims inferred by the harness.
The successful-mutation
projection separates current actionable post-image evidence from historical action
inputs. A successful check card names
the next remaining check instead of treating PASS as a failure. A failed mutation
retains its bounded exact replacement, full replacement hash, intent, anchor, evidence
IDs, error, parsed error location, failure class, and typed scope arithmetic across later
reads and process resume. A later failed mutation replaces it; a successful mutation
clears it. `mutation_readiness.state=ready_to_attempt` means only that current exact
anchor evidence exists, not that the semantic fix is sufficient. From turn two onward, the
actual model input carries the immediately preceding calls and exact public results as
native `function_call` / `function_call_output` items, followed by current derived
state without duplicating those results. One content-addressed model-input artifact
binds that sequence. Each read action in the batch card carries its corresponding
decision once. Identical evidence is counted per fingerprint at the unchanged diff.
A cache hit still costs one tool action, but its observation-level gain is recalculated
against the current coverage ledger. It may be signaled but is not hard-blocked. Never
add raw reasoning, private task material, hidden tests, reference
patches, or evaluator details.

Before each new model turn, recompute best-path completion feasibility after replaying
any pending durable batch. If mutation, all required checks, and finish cannot fit the
remaining model/tool/mutation resources, expose only `stop_task` for introspection but
do not dispatch it to the model. Record existing `LIMIT_REACHED` with
`completion horizon exhausted before provider dispatch` and bounded horizon arithmetic.
Terminal resume returns that same public result. These semantics are tool-surface `v7`;
do not migrate old envelopes or journal bytes.

## State and recovery

Each run owns an external `dev-run-v1` JSONL stream with sequence, prior hash, and
event hash. Mutations and checks use `action_id + input_hash`; identical input
replays the durable result, conflicting reuse fails closed, and an admitted
mutation is reconciled after a crash instead of applied twice. A provider start
without durable usage is uncertain and must not be retried automatically.

New runs also own one immutable `dev-run-envelope-v1`. `--resume-run-id` requires
`repeat=1` and an exact match for provider, task, runtime, model, reasoning,
credential path hash, cost cap, limits, and sandbox identity. Pre-envelope runs
cannot resume. A run-lifetime OS lock rejects concurrent execution. Generic turn
and tool-batch events recover a durable model decision without another provider
call; exact per-turn tool availability and native call/output linkage are stored at
the turn boundary. OpenAI turns additionally store provider-encrypted reasoning and
its output ordering in the external content-addressed artifact store; journal rows
contain only its reference, counts, and order hash. The next stateless request replays
that reasoning with matching calls and public results. Plaintext reasoning and
summaries are never retained. Missing, damaged, reordered, or action-mismatched
continuation evidence ends at `PROVIDER_CONTINUATION_ERROR` before another tool or
provider call. Counters, legacy inspection telemetry, settled cost, latest batch, and
active execution time are rebuilt from unique journal events. Process downtime
contributes only to run age.

## Live and evaluation boundary

Live mode accepts only checked-in `dev-train` tasks and requires an explicit model,
credential file, positive total cap, and repeat count. The credential is injected
directly into the SDK and is never placed in the process environment inherited by
repository or evaluator subprocesses. Active runtime/lock files and the selected
task package must be tracked and HEAD-clean; unrelated pathspecs do not block live
preflight. The local evaluator image and digest are checked before provider
dispatch; no pull/build/start occurs.

Actual request input is counted immediately before generation. The ledger reserves
uncached input plus a conservative output ceiling, lowers that ceiling when needed,
and emits `COST_CAP_REACHED` without generation when the minimum request cannot fit.
Transport retry is zero. Count, provider, or billing uncertainty stops remaining
repetitions. Provider completion records structural output evidence only: item
count, non-tool count, item types, a shape hash, and an encrypted-continuation artifact
reference. Request `reasoning.encrypted_content` with `store=false`; never persist
response text, plaintext reasoning, or a reasoning summary for protocol diagnosis.

After finish, the canonical submitted diff is content-addressed and an immutable
manifest is recorded before evaluator execution. It binds task bytes, full runtime
bytes, model/tool/sandbox identities, the visible-check diff, changed files, and
the submitted artifact. The evaluator validates those inputs before workspace or
check execution, then a clean workspace receives the exact artifact and private
files. Agent context is never resumed with evaluator output.

Task acceptance contains hidden, regression, and scope results only. Safety is a
separate typed result for runtime contract, constrained tool surface, managed
workspace, and requested sandbox policy. Docker evidence maps match/violation/
missing-or-invalid to PASS/FAIL/ERROR; local/mock Docker policy is NOT_RUN.
`EVALUATOR_PASS` means only task acceptance. Public summaries always expose both
axes and `claim_eligible=false`; every result remains `official=false`. Never use
`AuditSpec.prohibited_behaviors` as an automatic safety oracle.

## Default limits

- 40 model calls
- 100 tool actions
- 4 accepted mutations
- 1,800 seconds per row
- one consecutive protocol/incomplete recovery
- four parallel reads
- completion-slack inspection with one warned final opportunity and independent
  two-call mutation-failure and check-failure recovery reserves
- a soft mutation-or-stop signal after two consecutive zero-new-span inspections;
  it never changes the tool surface
- legacy 24-turn and three-repair-read fields retained as telemetry only
- 25,000 desired output tokens per provider call, reduced by cost admission
- one repetition by default, six maximum

## Development decisions and next seam

- Edit `dev-head` directly in small commits; do not version ordinary fixes.
- Keep memory disabled until completion and submission reliability are established.
- Keep mutation intent embedded in the mutation turn.
- Treat the exact live invocation as bounded development authority.
- Recover historical executables only from checkpoint `b71ddeee`; do not restore
  their active import graph.
- Keep confirmatory work in a future, separately frozen lane.

The context, resume, provenance, and typed-safety seams are locally implemented.
The second live row confirmed exact latest-batch projection and cache reuse but
exposed an ambiguous mutation encoding contract. The third live row confirmed that
the provider can call `apply_git_diff` with the raw-diff prefix, then exposed the next
boundary: one invalid hunk count was reported exactly on the next turn, after which
the agent returned to read/search for the remaining 37 turns instead of repairing
the mutation. The fourth live row confirmed that failed-mutation continuation fixed
that visibility problem: all 13 failures appeared exactly in the next context and
the repair card remained present in all 23 later turns. All 13 replacement diffs
still contained incorrect hunk totals, while a read-only `git apply --check --recount`
accepted each one against the retained isolated workspace.

A provider-free retrospective then replayed the first exact diff through the current
gateway. Recount accepted it, version-1 visible checks passed, and the exact submitted
artifact failed task acceptance while Docker safety passed. This moves the active
development boundary beyond mutation transport: the version-1 checks did not execute
the central missing-key behavior. Preserve that package as version 1. Version 2 adds
one public black-box check for actionable missing-key diagnostics, available keys,
the canonical `logger.bind()` / `{extra[key]}` pairing, and both catch modes. Do not
project evaluator details or derive further assertions from hidden output. The fifth
live row used version 2, accepted one mutation, and passed three visible checks. It
then produced two completed responses with no function call before invoking the
remaining `upstream-format-regression`, ending at `PROTOCOL_VIOLATION` with no
submission or evaluator. The old journal cannot reveal whether those responses were
reasoning, messages, or another non-tool item because their output shape was not
recorded.

The sixth separately authorized live row used the aligned tool contract and the same
version-2 task identity. Every one of 38 completed provider responses contained a
function call. The agent recovered from four rejected mutation actions, accepted one
mutation, passed all four visible checks on one canonical diff, and submitted that
same diff to the isolated evaluator. Task acceptance failed while typed Docker safety
passed. The private oracle enforced a literal example spelling that the public
contract explicitly did not require, so this is public/private contract-mismatch
evidence rather than a sound negative coding-agent verdict. Keep the hidden wording
out of agent context and preserve version 2 unchanged.

Keep repeated-evidence detection diagnostic-only. The bounded continuation evidence
does not support a hard workflow gate or a replacement mutation DSL. The smaller
current correction uses Git's deterministic recount for hunk totals while preserving
all existing mutation and submission checks. Version 3 now preserves version 2 while
replacing its literal private phrasing assertion with a semantic call-and-reference
pairing. Provider-free Docker validation makes the clean base fail, the reference and
the sixth-row exact candidate pass, and every declared known-bad patch fail acceptance.
Both passing patches also pass the full manifest-bound evaluator with all task and
safety axes PASS. This does not rewrite the immutable version-2 live result.

The separate local API defect is fixed as a small import-contract change. The
`patchloop.dev` and `patchloop.verifier` package roots retain their public exports but
resolve them lazily, and the runner depends directly on the evaluator core. A
fresh-process regression verifies lightweight package imports and both formerly
order-dependent submodule import orders. This changes no task or evaluator semantics.

The preserved `pyfakefs-makedirs-parent-traversal` version 1 had only an upstream
regression visible check. Version 2 adds a public black-box contract for POSIX,
Windows, bytes-path, and leaf-mode parent traversal while preserving every hidden,
reference, known-bad, environment, and audit byte. Its clean/reference/nine-known-bad
Docker matrix and manifest-bound reference evaluation pass provider-free.

The seventh separately authorized live row used that exact version-2 identity. It
ended at the 40-model-call limit after 44 reads and 42 searches, with no failed tool,
mutation, check, submission, or evaluator. The relevant `makedirs` source was present
in every context from turn 2 onward, and the final context still said
`needs_mutation` with one model call remaining. Treat this as a mutation-commitment
failure after sufficient public evidence, not another projection, task-contract, or
tool-transport failure. The soft repeated-evidence detector emitted no signal because
interleaved newly observed spans clear all fingerprint counts.

The post-seventh provider-free correction preserved the model's bounded public
`working_hypothesis`, `evidence_gap`, and `decision_after_result` on every read/search
result and attempt card. Action identity binds the state, while the operational read
hash remains the cache key; a cache hit therefore returns current decision state, not
the text from the call that populated the cache. Failed reads and process hydration
retain the same contract. The recorded decision takes precedence over diagnostic
stagnation wording, but no read is blocked and no new terminal exists. Local and mock
tests establish wire, cache, context, and recovery behavior only; they do not establish
live model compliance.

The separately authorized eighth row used the same version-2 task, model, medium
reasoning, one repetition, and $1.20 cap. Run `run_dev_07ad1af07d22489c` reached the
40-call limit after 60 successful reads/searches, no mutation, and $0.34786650. Every
context after the first projected all latest working states. Thirty-five per-call
decisions explicitly contemplated mutation/edit/patch/apply, but subsequent tool
selection remained read/search, including the final turn. Treat this as a live
decision-to-action coupling failure, not a context projection failure.

The post-eighth provider-free correction retired that future-decision contract. It
reconstructed one bounded native public tool continuation, validated typed decisions
against the actual tool family, and derived exposed tools from workflow evidence and a
completion horizon. At unchanged diff, general inspection leases 24 turns; a failed
mutation replaces that with three repair reads. It initially also required every
parallel read to repeat the complete free-text decision exactly.

The separately authorized ninth row used the same pyfakefs version-2 tuple. Run
`run_dev_b79d22f70ae44854` ended at `PROTOCOL_VIOLATION` after three model calls, one
successful search, no mutation, and $0.0077223. The next two responses each contained
valid read/search calls in `inspect` mode but gave those distinct actions different
rationales and evidence goals. The first rejection was present in the following public
context, yet the same application-only equality constraint failed again. Native call
and result linkage worked; the inspection lease was not exercised.

The post-ninth provider-free correction removed only that cross-call free-text equality.
Parallel reads still share enforced `inspect` mode, and each call-specific decision is
retained in its batch card. At that checkpoint the completion horizon, 24/3 leases, and
diagnostic-only stagnation behavior remained unchanged.

The separately authorized tenth row used the same pyfakefs version-2 tuple. Run
`run_dev_8efe75f7c8c14cbd` ended at `INCOMPLETE_RESPONSE` after 28 provider calls,
58 tool actions, no accepted mutation, and $0.27773415. The general inspection lease
removed reads after 24 turns, establishing that native continuation, completion horizon,
and lease all operated live. A valid public check on the unchanged empty diff failed as
expected. Three other responses used their complete 4,096-token output allocation only
for reasoning and emitted no tool call; the last two were consecutive and closed the
row. The old journal omitted `incomplete_details.reason`, so ceiling exhaustion is a
strong usage-based inference rather than a stored exact provider reason.

The first post-tenth provider-free correction raised the desired output ceiling to
25,000, retained and replayed provider-encrypted reasoning, and replaced the fixed 24/3
action gates with completion slack. The separately authorized eleventh row,
`run_dev_36d200ed199d4377`, confirmed those mechanisms live: all 39 continuation edges
linked, the last inspection opportunity was announced, and execution-only policy
elicited mutation calls whose 12,128- and 7,469-token responses completed. The first
diff failed on a bare `@@`; the next turn repaired it, and the accepted one-file diff
passed both visible checks. The row nevertheless reached 40 model calls before finish,
with 94 tool actions, $0.449133 cost, no submission, and no evaluator.

That row exposed one narrower scheduler defect. The horizon reserved only the four-call
best-case mutation/check/check/finish path, and `completion_possible` tested mutation
capacity without remaining budgets. The current provider-free successor holds one
additional first-mutation repair call, consumes it after failure, and reports actual
best-case budget feasibility. A scheduler regression reproduces the eleventh-row shape
through finish at call 40 while retaining the 40/100 global limits. Ruff and all 87
tests pass in 88.79 seconds; provider-free mock run `run_dev_22a91101f0224925` reaches
isolated `EVALUATOR_PASS` through one accepted mutation with zero provider cost.

The separately authorized twelfth row, `run_dev_2e95d3d85fd84e2d`, confirmed encrypted
continuation on all 38 edges and closed inspection at turn 36 with five calls left. Its
first mutation applied, and the central visible check then failed on the public
intermediate-directory permission assertion. The next turn proposed a one-line repair,
but mutation validation rejected it because the successful mutation had invalidated
the only current span for `pyfakefs/fake_os.py`; read/search were already closed even
though `last_successful_mutation` retained the exact current hunk. Three calls also
could not cover the repair, two checks, and finish. The row deliberately stopped at
turn 39 after 76 tool actions and $0.3471675, with no submission or evaluator.

The next provider-free successor accepted a current-diff-bound successful-mutation
post-image as anchor evidence only for an overlapping repair in that same file, while
retaining current-span validation everywhere else. The separately authorized
thirteenth row, `run_dev_8ce8603c45e646a9`, reached one accepted mutation and one
failed public check, then rejected the final targeted repair because its evidence list
mixed the valid current post-image with IDs retained from the prior mutation input.
Its earlier mutation-format failure had also consumed the single shared recovery
allowance. The row ended at `LIMIT_REACHED` after 40 calls and 76 actions, with no
submission or evaluator.

The then-current provider-free seam projected only validated
`actionable_evidence_span_ids`, retained exact mutation inputs as journal provenance,
and tolerated known historical IDs only when independent current evidence covered the
exact anchor. Mutation-failure and check-failure reserves were independent. Repeated
zero-gain inspection produced only a soft commitment signal. The later fourteenth row
required and received separate authorization.
Ruff and all 92 tests pass under the two-minute provider-free target; mock run
`run_dev_7fc6bc7e982343e4` reaches isolated `EVALUATOR_PASS` with zero provider cost.
A provider-free exact replay then admitted the thirteenth row's final repair under the
new evidence classification. The central public check passed, but the digest-pinned
Docker upstream check reported 8 failures, 509 passes, and 570 skips; `finish_task`
failed closed. Treat the original rejection as a fixed harness false negative and the
replayed patch as non-submittable agent output. Do not weaken checks or add recovery
solely to make that historical patch pass.

The separately authorized fourteenth row, `run_dev_86ccd39d36ab4379`, confirms the
encrypted-continuation and action-space contracts: all 40 calls completed with
continuation references, turn 32 warned that inspection would close, turn 33 closed
it, and a failed mutation reopened one final inspection turn. It nevertheless ended
at `LIMIT_REACHED` after 70 actions and two accepted mutations. One typed-contract
failure and three structurally corrupt raw diffs consumed the protected tail before
the first patch applied. A public check failed, and the final repair used undefined
`helpers.PERM_DEF` instead of the directly imported `PERM_DEF`; no turn remained to
recheck. An external copy with only that identifier corrected passes both public
checks, including 517 upstream passes and 570 skips. No submission or hidden evaluator
ran.

The pre-fifteenth provider-free successor implemented that seam. New-span count was
syntactic telemetry; soft inspection gain came from non-overlapping coverage in
editable task paths plus the first canonical observation of a search. `replace_text` moves diff
serialization into the gateway while preserving current hash, tracked-path, scope,
rollback, recovery, and post-image contracts. A failed visible check consumes its
separate minimum three-call reserve and exposes exactly one targeted `read_file` turn over the
changed/current-evidence paths before replacement, full recheck, and finish. Unchanged,
uniquely occurring spans are revalidated across mutation so nearby import or symbol
evidence is not discarded solely because another line changed. Do not merely raise the
40-call limit, silently repair arbitrary model intent, weaken a check, or run a paid
retry/fifteenth row without separate authorization.
Focused contract tests pass 76 cases in 82.29 seconds. Ruff and all 95 tests pass in
87.75 seconds with an external short temp root. Provider-free mock run
`run_dev_c185114854c54ad6` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted `replace_text` mutation; task acceptance is
PASS, safety is NOT_RUN, `claim_eligible=false`, and provider cost is zero. This proves
local wiring and recovery only, not provider behavior or a fifteenth live row.

The separately authorized fifteenth row, `run_dev_6013912c916d4781`, ended at
`LIMIT_REACHED` after 40 calls, 46 actions, two accepted mutations, and $0.4705068. Its
first 49-line diff failed the public byte assertion. Four repairs each formed the same
56-line candidate against the 50-line limit, but generic feedback hid the 49 to 56
delta. Turn 40 accepted a different 48-line candidate without enough calls to check it.
The trace had complete encrypted continuation, no provider/incomplete error, and a
largest 11,133-token response. Seven of 17 searches added no coverage and four added
supporting-only coverage, while first-seen queries still counted as gain. Turns 38 to 40
reported `completion_possible=false` yet still offered mutation. Treat these as three
harness defects: progress semantics, mutation-feedback loss, and unenforced completion
horizon, not a reason to raise global limits.

The current provider-free successor separates novelty from public line coverage, keeps
a triggered commitment sticky for its diff, reports complete typed scope arithmetic,
routes mutation failures by class, and terminates an impossible tail before dispatch.
No Docker operation, provider call, or sixteenth live row is authorized by this seam.

The initial full run passed all 103 tests but took 195.256 seconds. Profiling showed the
same turn state was being derived through 495 subprocesses in the slowest context test:
76 repeated diff summaries plus span-by-span tracked-file validation. Do not address
this with a long-lived workspace cache. Group current observations by path, capture one
fresh `DevGatewayStateSnapshot` immediately before each scheduler decision, and share it
between policy and context. Re-observe after every tool/recovery boundary.

Ruff passes. The focused 68-test tool/runner suite now passes in 90.497 seconds and the
full 103-test suite in 96.713 seconds with external temp root
`C:\pt\snapshot-full-final`. Mock run `run_dev_030e46d9a4d84395` reaches isolated
`EVALUATOR_PASS` in four model
calls and five tool actions through one accepted mutation, with task acceptance PASS,
safety NOT_RUN, `claim_eligible=false`, and zero provider cost. This restores the
two-minute target without deleting or parallelizing tests and does not authorize a paid
row.

The separately authorized sixteenth row, `run_dev_6c36a082c3264559`, ended at
`LIMIT_REACHED` after 37 calls, 44 actions, one accepted mutation, and $0.43578705.
All 37 responses carried encrypted continuation. Before the first mutation, a current
span covering the complete proposed anchor was already projected, but the model twice
serialized a shorter overlapping span ID and the old validator rejected both attempts.
Each rejection re-armed another targeted read. Turn 36 finally applied a mutation;
the public check then exposed an empty-parent-path `FileNotFoundError`. With three calls
remaining versus a five-call repair/check/finish path, the pre-dispatch horizon correctly
stopped the run. There was no submission or evaluator.

Tool surface `v8` removes `evidence_span_ids` from `replace_text`. The gateway now binds
the most recent current covering observation itself, keeps the selected ID only as
journal provenance, and applies one targeted-read allowance per failed-anchor lineage.
This removes the mechanical join-key failure without weakening current-file, range,
scope, rollback, or submission checks. No Docker operation, provider call, or
seventeenth live row was authorized by that change; the later row required separate
authority.
Ruff and all 105 provider-free tests pass; the final full suite completed in 80.787
seconds with external temp root `C:\pt\pl-v8-full-0905-c`. Mock run
`run_dev_32428b48e6b341d8` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost.

The separately authorized seventeenth row, `run_dev_4b32848a5621473e`, confirmed the
v8 evidence binding on all four accepted mutations, then ended at `LIMIT_REACHED`
after 34 model calls, 42 tool actions, and $0.393104700. The first public inline failure
was line 12. The second moved to line 23, the public intermediate-directory `0o755`
assertion, and the last two remained there. The final code used the requested leaf
`mode=0o700` for all path components, but the later mutations instead targeted path
joining and Windows separators; that later Windows block had not executed. Mutation
capacity, not model/tool call capacity, then blocked completion. There was no
submission or evaluator.

Tool surface `v9` keeps raw check-output signatures for provenance and adds a separate
semantic site fingerprint for safely mapped registered `python -c` failures. Its
bounded `current_public_failure` joins the exact public statement, conservative
cross-diff location comparison, unobserved-later-source status, and remaining mutation
pressure. It survives intervening reads and restart until a relevant pass clears it.
Nested and unmapped traces remain uncertain, and no local variables, hidden paths,
private bytes, reasoning, task-specific semantic rule, new terminal, or semantic hard
gate are added. Ground the existing mutation hypothesis and `causal_revision` in this
card. Provider-free regression must preserve the row-17 public `12 -> 23 -> 23`
sequence. No Docker operation, provider call, or eighteenth row is authorized by this
change.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass
in approximately 70.5 seconds using external temp root `C:\pt\pl-v9-full-a`. Mock run
`run_dev_dd14cc24d3fa46ef` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost. This is local wiring evidence,
not live evidence that the model makes the intended causal pivot.

The separately authorized eighteenth row, `run_dev_092cb8494e254124`, ended at
`AGENT_STOPPED` after nine model calls, 16 tool actions, one accepted mutation, one
failed public check, and $0.078825000. Tool surface v9 mapped the `FileExistsError` to
public inline line 10 and retained the current mutation post-image. The model explicitly
diagnosed the redundant final `FakeFilesystem.makedirs(normalized_path)` call and named
the appropriate repair, but the scheduler exposed only `read_file` and `stop_task`.
The old `targeted_check_repair_inspection` state conflated a restricted read opportunity
with a required predecessor, while the prompt correctly discouraged a read without an
unresolved public gap. The resulting stop is a harness action-mask contradiction, not
missing failure evidence or a failed causal pivot.

Tool surface `v10` adds `targeted_check_repair_required` as the distinct prerequisite.
When a failed check still has current exact mutation evidence, expose `replace_text`
immediately and expose one path-restricted read beside it only when protected completion
slack remains. At the exact best-path horizon, omit that optional read. When the anchor
is absent, keep the targeted read mandatory and count it in the minimum path. Corrections
must describe those two states distinctly. Preserve gateway evidence validation, scope,
rollback, resume reconstruction, and same-diff check suppression. This change authorizes
no Docker operation, provider call, or nineteenth live row.
Ruff and the focused 74-test tool/runner suite pass. All 109 provider-free tests pass in
71.998 seconds with external temp root `C:\pt\pl-v10-full-a`. Mock run
`run_dev_b5d5b2473d6a414f` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost.

The separately authorized nineteenth row, `run_dev_87185b3ce20a4333`, ended at
`LIMIT_REACHED` after 39 model/input-count calls, 44 tool actions, two accepted
mutations, and $0.472921050. All 39 provider turns carried encrypted continuation. The
first replacement was rejected for a stale exact anchor, and the second implemented the
recursive behavior. The first public check then failed its intermediate-directory mode
assertion. Tool surface v10 correctly offered both optional targeted read and immediate
replacement; the repair switched recursive parents to `PERM_DEF`, and that check passed.
The later upstream regression check failed two broken-parent-link cases with `EEXIST`
instead of `ENOENT`. Only one model call remained against a four-call repair/recheck/
finish path, so the pre-dispatch horizon stopped the row. There was no submission or
evaluator.

Tool surface `v11` addresses the two remaining scheduler causes without encoding that
task's semantic repair. Two zero-coverage batches now announce one final parallel
inspection; new public coverage reopens exploration, while a further zero-coverage
batch closes broad reads for the current diff and leaves mutation or stop. Separately,
the horizon reserves one recovery path per distinct visible-check ID, ordered by the
declared check sequence and bounded by remaining mutation capacity. Consuming the first
check's reserve no longer erases the second's. Legacy check failures without an ID keep
their conservative consumed state. This change authorizes no Docker operation, provider
call, or twentieth live row.
Focused scheduler tests and Ruff pass. All 109 provider-free tests pass in 77.62 seconds
with external temp root `C:\pt\pl-v11-full-0905-c`. Mock run
`run_dev_54650ea291e24cd0` reaches isolated `EVALUATOR_PASS` in four model calls and
five tool actions through one accepted mutation, with task acceptance PASS, safety
NOT_RUN, `claim_eligible=false`, and zero provider cost.

Confirmatory design review still waits for three distinct harness/contract-clean
submissions with at least two private passes; that threshold itself proves no quality
or generalization benefit.

## Validation checklist

Run only what the change needs, then broaden to:

```powershell
uv run ruff check patchloop tests
uv run pytest tests --basetemp <short-external-path>
uv run patchloop dev --provider mock --task tasks/smoke/csv-quoted-newline/public.yaml --model mock-dev --repeat 1
```

Before handoff, confirm no private projection, repository-local run state, live
call, Docker mutation, historical artifact edit, stale active-doc link, or invented
result was introduced.
