# Run and validate

All generated state must live outside the repository. Use short Windows paths to
avoid temporary-directory permission and path-length failures, but keep disposable
test workspaces separate from durable evidence.

- `C:\pt\tmp\<unique-name>`: disposable test workspaces; do not create new test
  directories directly under `C:\` or scatter them beside experiment records.
- `C:\pt\validation\<unique-name>.xml`: retained test reports, outside the temporary
  workspace so cleanup does not erase the validation result.
- `C:\patchloop-state`: durable runs, artifacts and managed workspaces. Existing
  experiment/analysis directories retain their original paths and bytes.

After the test process and its children exit, retain the report and recycle only
that invocation's exact temporary directory. Failed-test workspaces may remain while
diagnosis needs them; recycle them when that investigation finishes. Do not empty
the Recycle Bin automatically, sweep a parent directory, or classify run/analysis
evidence as disposable merely because its path contains `test`, `tmp` or `pt`.

## Fast local verification

```powershell
$testId = 'pytest-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$testRoot = Join-Path 'C:\pt\tmp' $testId
$testReport = Join-Path 'C:\pt\validation' ($testId + '.xml')
New-Item -ItemType Directory -Force -Path 'C:\pt\tmp', 'C:\pt\validation' | Out-Null
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run pytest tests -p no:cacheprovider --basetemp $testRoot --junitxml $testReport
# Once pytest and its children have exited, recycle only $testRoot as described above.
```

This path uses no provider or Docker call.

Keep runtime files unchanged while tests run, because provenance tests bind their actual
bytes. For a faster complete suite, partition files across independent processes,
each with a different new external temporary root, with every file selected exactly once.
The exact split and latest measured result are in [the internal guide](../.agent/guide.md#validation-checklist).

## Mock end-to-end

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop dev `
  --provider mock `
  --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock-dev `
  --repeat 1
```

Mock mode forbids credential and cost options. A successful smoke run performs
parallel public inspection, one admitted mutation, a visible check, automatic
full-diff projection, finish, and a separate private evaluation. Its result is
still unofficial.

## Brief planning improvement cycle

`patchloop dev --planning-policy none|brief-v1` defaults to `none`; `brief-v1`
requires `--context-policy append-v1`. Resume must repeat the same option along
with the existing exact task/model/environment/cap/limits. No old run migration.

`diagnostics.planning_cycle` implements the user-authorized bounded cycle. The
2026-09-14 cycle below is now stopped after eight attempts ($4.064418300 recorded
model-rate cost). B4's input-count HTTP 400 rejected an oversized encrypted item;
no next group or paid retry is queued. The commands below document its original
interface, not permission to recreate the experiment under a different root:

```powershell
uv run python -m diagnostics.planning_cycle init --root C:\pt\analyses\planning-cycle-20260914 --pricing-verified-on <actual-UTC-date>
uv run python -m diagnostics.planning_cycle prepare --root C:\pt\analyses\planning-cycle-20260914 --hypothesis "Short public plans may improve consistent completion."
uv run python -m diagnostics.planning_cycle run --root C:\pt\analyses\planning-cycle-20260914 --group g01-pyfakefs
uv run python -m diagnostics.planning_cycle status --root C:\pt\analyses\planning-cycle-20260914
```

Init requires a new external root; prepare is credential/provider-free and freezes
the exact packet. Confirm official prices and existing Docker/image readiness
before running. The execution command admits the entire group, uses the normal
runner and records durable per-slot results. Reissuing a completed group is
read-only. An interrupted process may use exact native recovery; unresolved count
or dispatch is never retried. A recorded cycle stop prevents further dispatch.
No automatic Docker operation is authorized. `--provider mock` is a local fixture
mode; tests also mock probe-image preflight, and never claim it as live evidence.

The authorized group order, stage thresholds and metrics are specified in
[the experiment contract](../.agent/planning-experiment.md). Do not add runs to use leftover
budget or use hidden details to revise planning instructions. Close with `close
--reason ...` when there is no justified next change or a terminal cycle stop has
been reviewed. A recorded stop is never cleared to spend the remaining budget.
Old experiment approvals below remain consumed; this cycle does not reopen them.

## Closed supplied public-case lifecycle experiment

`diagnostics.public_case_rollout` adds no default agent option. Its `prepare` and
`validate` commands take `--plan-root` and use no key, input count, provider or
sandbox. The frozen packet is `C:\pt\analyses\public-case-rollout-20260914`.
Both arms receive the same public program/original report; only B gets exact-program
execution tracking and optional advice. No newer candidate failure is injected.

The `1f8bc6f5...` packet has now executed once; its approval is consumed. Evidence is
at `C:\pt\analyses\public-case-live-20260914`: four immediate unchanged submissions,
no agent probes, fixed public case FAIL. Do not replay the command as an authorized
follow-up. Any new comparison needs a separate exact packet and grant.

After separate exact approval, `run` additionally requires a fresh `--result-root`,
`--approval-packet-hash`, `--credential-file .env`, `--max-cost-usd 4.00` and the
same-UTC-day `--pricing-verified-on`. Four fresh branches A1/B1/B2/A2 each retain a
nontransferable $1 cap, <=8 new responses and the complete 25k output reservation.
The current model remains `gpt-5.4-mini-2026-03-17`, reasoning medium. Existing
Docker/image readiness is required; no automatic start/pull/build, retry, resume
or replacement sample. This documentation and local mock validation are not approval.

Case completion means a complete execution receipt, never automatic behavioral PASS.
Separate agent probe/output review, public checks, mutation/finish and the post-episode
operator case audit. Hidden/task acceptance and safety stay NOT_RUN, official=false.
The CLI reports only aggregate status/cost. Record masked public code observations
before opening labeled operator verdicts; the detailed immutable result stays on disk.
Recognizable original code still prevents a claim of perfect blinding. Do not feed
post-episode audit results back into an already finished branch.

## Prior current-candidate feedback preparation

The executable adapter is `diagnostics.current_failure_feedback_rollout` with
`prepare`, `validate`, and `run`, each taking `--plan-root`. `run` also needs a fresh
`--result-root`, exact `--approval-packet-hash`, root `--credential-file .env`,
`--max-cost-usd 4.00`, and same-UTC-day `--pricing-verified-on`. It preserves the
frozen A1/B1/B2/A2 comparison, $1 nontransferable branch caps and full25k reservation.
Preparation/validation are no-call operations; this documentation is not live
approval. No retry/resume/extra sample or automatic Docker start/pull/build exists.
Only the frozen public case is audited; hidden/task acceptance remains NOT_RUN.

`uv run python -m diagnostics.current_failure_feedback prepare --output-root <fresh-external-root>`
freezes A/B inputs from the sealed report-only A2 pre-finish checkpoint. `validate
--root <packet-root>` reconstructs and verifies them without a provider, credential
loader, subprocess or sandbox. There is no run command. B adds only the existing
public reproduction's failure on the current candidate; old native history and
registered-check PASS are unchanged. The proposed $1 each/$4 total is not approval.
The separate adapter supplies execution; exact executable approval is still required
before further paid work. Preserve the original preparation packet and run bytes.

## Report-aware diagnostic comparison

The separate `diagnostics.report_verification_review` command prepares/validates an
experimental report-aware context comparison; it does not enable a default agent
setting. Its `run` requires approval of the exact immutable plan, root `.env`, a
fresh external result directory, $2 total cap and same-day UTC price-review assertion.
It has no automatic retry or resume. Prepared packets authorize no provider/count
call or Docker operation; never reuse a consumed earlier experiment grant. Detailed
conditions and evidence limits are in the current status and internal agent guide.

## Optional native snapshot window

`--context-policy native-window-v1` enables the experimental snapshot lifetime in a
new run. The default remains `append-v1`. Old harness state descriptions expire, but
their unique public evidence and all native encrypted reasoning/tool exchanges stay
available. This flag does **not** enable a compaction API, reasoning reset, a different
model or new tool restrictions. Model effectiveness has not been measured.

Repeat the same policy on resume: it is part of the exact model/envelope contract.
An old runtime-mismatched run cannot be migrated or restarted by adding this option.
Saved seed, input and evidence corruption stops before another provider/tool action.
Ordinary live task/model/credential/repeat/cost approval gates still apply. Use the
mock command above with this flag and a fresh validation state root for a free smoke.

Standalone compaction is a second, separate opt-in for new OpenAI runs using the exact
`gpt-5.4-mini-2026-03-17` snapshot. It requires both
`--compact-at-input-tokens T` (positive, less than 272,000) and
`--accept-compaction-model-limit-reservation`, alongside `native-window-v1`.
There is no default T. A live approval must explicitly include these options, the
ordinary task/model/reasoning/credential/repeat/cap, and the conditional cost contract.
Neither this documentation nor an earlier diagnostic grant authorizes a new run.

At most one compact request shares the invocation cost cap and 40-model budget.
Its $0.876 full-model-limit reservation is conditional, **not a server-enforced
invoice cap**. If this optional reserve or the spare completion call is unavailable,
otherwise viable generation stays open. An interrupted count or provider call is
never repaired by compaction/retry. A completed compact preserves its whole output,
reenters missing public evidence, refreshes state/tools/budgets, and counts the exact
new request before generation. It shares the active deadline and five-second client
cleanup reserve. Repeat the same T/acknowledgement on exact resume; no old-run migration.

Public `call_counts.model` includes compact dispatches; opted-in runs additionally
separate `decision` and `compaction`. Input counts are separate. No free local mock
smoke invokes compact; focused tests inject fake clients to exercise this branch.

## Input-count failure diagnostics

`COUNT_TIMEOUT_OR_UNKNOWN` still stops all repetitions, including HTTP rejection;
the terminal name does not establish that a timeout occurred. Its optional
`input_count_failure` contains count/turn/request identity, canonical count-body
byte size/hash, input/reasoning item counts and encrypted-field lengths. A durable
`input_count_failed` event additionally records allowlisted HTTP error fields and
buffered wire-body size/hash when available. Canonical size is not wire size.

Messages, raw bodies, headers, credentials and plaintext reasoning are never logged.
Unrecognized code/type/parameter/request-ID values are omitted and marked redacted.
These are operator diagnostics, not model feedback or permission to retry. Exact
resume after a failed or interrupted count only finishes its terminal metadata;
it sends no new count/provider request and does not load credentials or a workspace.
Provider/billing uncertainty retains priority. Already terminal results remain
idempotent. Old runtime-mismatched envelopes are not migrated.

The standalone `diagnostics.count_replay` has only `prepare` and `verify` commands;
neither creates a client, reads a credential, counts tokens or runs a task. The frozen
B2 turn20/21 design is at `C:\pt\analyses\count-replay-design-20260912`. Its canonical
request body artifacts contain the original public history and encrypted state;
the human packet/journal retain hashes and sizes, not those bodies. Keep this new
diagnostic separate from native resume. Verification requires the expected packet
hash and checks original journal/envelope/CAS plus current reconstruction identity.

`diagnostics.count_collector` implements control first, then failed case, one attempt
each; a changed
97,810-token control, any error or missing outcome stops the sequence. No generation,
tools, Docker, private evaluator, retry, replacement or continuation reset. These
rules are mock-tested, not evidence that a live diagnostic ran. Both counts succeeding
would mean only NOT_REPRODUCED; a new rejection would not recover the old error body.

The collector requires the expected packet hash, original credential-file path and
a new external `--output` directory. Validation precedes credential/client creation.
The directory is an exclusive one-invocation claim, not a resumable queue. Each attempt
is journaled before dispatch; a crash with no outcome stays UNKNOWN. Do not reopen,
delete or replace that directory to retry. Results and safe HTTP diagnostics are in
its `result.json` and hash-chained journal; request bodies stay in the original CAS.

Whole count waits are bounded by min(30s, remaining 65s execution deadline minus 5s
cleanup reserve). Cleanup is itself bounded by remaining time and reported separately;
UNKNOWN cleanup stops execution and does not claim OS-thread or remote cancellation.
No generation request, task tool, Docker operation or hidden evaluator is reachable.

Count-only billing remains UNCONFIRMED: the reviewed official
[counting guide](https://developers.openai.com/api/docs/guides/token-counting) and
[pricing page](https://developers.openai.com/api/docs/pricing) do not explicitly state
this endpoint's price. A [community reply](https://community.openai.com/t/does-post-responses-input-tokens-cost-money/1380071/2)
describes counting as free, but is not an official pricing guarantee. Do not infer
charges from generation rates or treat an absent usage field as a zero-dollar receipt.

The first separately approved collection is complete and its grant is consumed:
`C:\pt\analyses\count-replay-collection-20260912`, diagnostic run
`run_dev_countcollect_82df89236b5c4404`. Two count requests in 2.811447s: control 97,810;
failed case HTTP 400 `string_above_max_length`, `input[79].encrypted_content`.
Read `C:\pt\analyses\count-replay-live-20260912\result.md` for preserved evidence and
limits. No generation/task/Docker/retry occurred. Do not invoke that output again;
the new rejection does not recover the original HTTP error or establish free billing.

There is no remaining execution grant. Separately approve the exact packet, model in that
packet, credential path, new destination and maximum two counts, including billing
uncertainty, before invoking the collector with `--accept-unconfirmed-count-billing`.
That acknowledgement records an operator choice; it neither changes the frozen design
nor establishes a price or enforceable dollar cap. Without it, execution rejects before
credential access. Do not reuse the closed comparison's budget. Basic invocation after
that separate approval is `uv run python -m diagnostics.count_collector` with
`--packet-root`, `--packet-hash`, `--env-file`, `--output` and the acknowledgement.
This command has no automatic retry, replacement, repeat, resume or generation mode.

## Diagnostic standalone compaction (not the native loop)

`uv run python -m diagnostics.compaction_replay prepare --source-state-root
C:\patchloop-state --output-root <new-external-root>` freezes only the healthy
B2 pre-turn20 input. `verify --root <packet-root> --packet-hash <exact-hash>` checks
the source journal/envelope, artifacts, reconstruction and implementation identity
without credentials or API calls. Existing count packets and run bytes stay immutable.

The internal `compaction_state.reserve`, `record_response` and `recover` functions
provide result storage/recovery, not authorization or a live collector. The separate
collector below establishes conditional cost/deadline admission before calling compact.
The complete canonical compact output is retained; exact public state and referenced
observations are appended afterward, without reading fresh source or replaying tools.
Recovery never retries a missing outcome. The atomic receipt is the completion
boundary; an orphan output object alone is insufficient. Corrupted stored results
stop before a new request. A ready handoff generates request artifacts only: it does
not automatically count, generate, mutate, run Docker or evaluate the task.

OpenAI's [compaction guide](https://developers.openai.com/api/docs/guides/compaction)
requires preserving the complete returned window. The [standalone API schema](https://developers.openai.com/api/reference/python/resources/responses/methods/compact)
provides usage but no `max_output_tokens` or reasoning-effort parameter. Do not send
unsupported `store`, `tools` or reasoning fields to that endpoint. It is stateless;
the following generation still uses store=false, medium reasoning, 25k output and
the original ordered tools. Do not describe 25k as a compaction spending limit.
Compact uses the separately acknowledged model-limit reservation below; count billing
remains unresolved, and usage is not proof of a zero charge. No live grant remains.
Byte/opaque-field measurements are not token
counts, a known server limit, or proof that compaction fixes the observed rejection.

### One-compaction collector

The `03b157e1...` proposal was separately approved and executed once on 2026-09-12.
Collection `C:\pt\analyses\compaction-collection-20260912` is complete; its grant is
consumed. Read `C:\pt\analyses\compaction-live-20260912\result.md` for observed sizes,
usage and limits. Prepared count/generation artifacts are not execution permission.
No paid retry or follow-up was performed. The frozen proposal's original unapproved
flag is historical; the later authorization is a separate immutable record.

`diagnostics.compaction_collector inspect` validates an exact proposed invocation
without loading a credential or creating the output directory. Supply `--packet-root`,
`--packet-hash`, `--env-file`, `--output`, `--repeat 1` and a positive `--max-cost-usd`.
It returns an `execution_plan_hash` binding all of those settings, the collector and
its reviewed cost contract. The frozen preparation packet's disabled-live flag is
unchanged and is not an execution grant. The separately approved collector is a new
invocation, not source-run resume.

The [official price table](https://developers.openai.com/api/docs/pricing) states that
Responses uses model token rates. For this mini snapshot the no-cache reservation is
400,000 input x $0.75/M + 128,000 output x $4.50/M = $0.876. The input allowance uses
the entire published [model context window](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
even above its 272k maximum input. These model limits are an explicitly acknowledged
planning basis, not a compact-endpoint-specific output guarantee or enforced dollar cap.
If that distinction is unacceptable, do not execute this collector. Do not send an
unsupported 25k limit, assume the earlier native token count is exact for compact,
or use a timer/project budget as proof that a charge cannot exceed the reservation.

After separate exact approval, `collect` uses the same arguments plus
`--execution-plan-hash` and `--accept-model-limit-reservation`. It makes at most one
compact request, with zero SDK retries. It never calls the count endpoint or generates
a follow-up response. Both the full reservation and remaining time are rechecked at
dispatch; no output ceiling is reduced to fit a small cap. The wait is at most 300s
within 305s total, reserving 5s for cleanup. Uncertain cleanup is not remote cancellation.

Usage is durably saved before output processing. Cache hits affect model-rate accounting
only after response; reasoning tokens are already included in output tokens. The
recorded amount is not invoice verification. Missing usage, an unpriced cache-write
counter or exceeded model/reservation bounds stops the collection. No later action is
unlocked by a successful compaction. `recover --output <existing-collection>` reconciles
only stored receipts, without credentials or a new request; a pending dispatch is not
proof that HTTP was reached. Preserve the collection rather than rerunning its output.

### Post-compaction diagnostic

`uv run python -m diagnostics.compaction_followup inspect` takes `--collection-root`,
`--result-hash`, `--output`, `--env-file`, `--max-generation-cost-usd` and `--repeat 1`.
It validates the completed compaction source and frozen next requests without loading
credentials or writing the source/output. Review the resulting exact execution plan.
The frozen proposal `C:\pt\analyses\compaction-followup-design-20260912\README.md`
retains its original unapproved preparation state. A later exact grant was used once:
`run_dev_compactnext_822a9ab18f5f4ce3`, count 1/generation 1, completed, 78,485 input and
117 output (44 reasoning). The proposed remaining contract check was not executed.
Authorization/result: `C:\pt\analyses\compaction-followup-live-20260912`.
The grant is consumed; do not rerun collection. Source generation/count hashes stay
`c1e2825b...` / `d5716b19...`; old proposal/receipt/run bytes must not be updated.

The $1.20 cap covers generation only. The full 272k-input/25k-output
reservation is $0.3165 at the reviewed Standard model rates, without cache savings.
Count-endpoint billing remains unconfirmed outside this cap. Do not describe this
as a guaranteed total invoice cap or standing execution permission. This completed
generation accounts to $0.05939025 at model rates; count billing/invoice remain unknown.
Any new collection needs a new exact grant acknowledging this limitation and a current
price check. `collect` additionally requires `--execution-plan-hash` and
`--accept-unconfirmed-count-billing`.

At most one count precedes one generation. Count errors, limit/cost/deadline failures
prevent generation; response/usage/continuation/cleanup failures stop without retry.
Output remains 25k; no corrective turn, tool execution, recompaction, Docker or hidden
evaluation follows. `result --output <existing-root>` reads durable evidence only;
it is not a paid resume and does not infer HTTP execution from an unfinished intent.
Response collection, public decision/batch shape and actual semantic correctness are
separate results. Read the proposal before interpreting `PASS_SHAPE_ONLY` as success.

### Short compacted-loop preparation (provider-free only)

`uv run python -m diagnostics.compaction_episode prepare` accepts `--collection-root`,
`--result-hash`, `--task-dir`, a new external `--output` and optional
`--max-new-responses` (default 8) and `--context-policy` (default `append-v1`).
It verifies the saved one-response collection,
healthy cutoff, task and implementation identities, then writes an immutable packet.
`verify --packet-root <root> --packet-hash <hash>` rechecks it without credentials,
network, a workspace or tool execution. Historical packet `65e1ce83...` under
`C:\pt\analyses\compaction-episode-design-20260912` is immutable evidence, not a
current executable contract after diagnostic code changes.

The internal `initialize`, `execute_seed` and `step` require explicitly supplied
backends/adapters. They are mock-validated mechanics, not a live CLI or approval.
Initialization clones the exact historical checkpoint, not the final old worktree.
The saved check choice executes once without another provider call; its already-paid
response still consumes one inherited model call and its recorded active time.
Subsequent inputs retain the full compacted window and append encrypted continuation,
matching tool results and the exact current public reentry. Existing tool policy,
memory, source/scope checks, repair-recheck option and completion budgets are reused.
The explicit `latest-state-v1` option changes only our post-seed snapshot lifetime:
superseded reentries are replaced, but unique public source/exchange/check/probe
observations are kept as quoted historical evidence. No source file is read implicitly.
The entire seed, including all standalone compact output, stays unchanged, following
the [standalone compaction contract](https://developers.openai.com/api/docs/guides/compaction).
Latest state is complete; old evidence cannot supply current PASS, expired notes or
already-consumed correction. The mode and projector bytes bind the packet/collector
plan; there is no unbound collect-time switch. Count and generation receive exactly
the ordered input stored in that turn's artifact. Default/native append behavior is unchanged.
The eight-response observation bound censors the diagnostic; it does not narrow the
model's native action space or claim an impossible completion horizon.

That preparation module has no live/resume subcommand. A collector must bind a lifetime lock, new
exact generation cap/approval, current prices, separately unconfirmed count billing,
client cleanup, partial-result receipts and existing Docker/probe image preflight.
Reserve unchanged 25k output before every new generation; never retry uncertain work
or reuse the consumed one-turn grant. Hidden evaluation stays NOT_RUN even if public
checks and finish succeed. Runtime/envelope history is not migrated.

### Short compacted-loop collector (separate exact approval)

`uv run python -m diagnostics.compaction_episode_collector inspect` accepts the frozen
`--packet-root`/`--packet-hash`, a new external `--output`, exact `--env-file`,
`--max-generation-cost-usd`, `--repeat 1` and `--prices-verified-on YYYY-MM-DD` (UTC).
It does not load credentials, call APIs, check Docker or create output. Inspect's
`execution_plan_hash` binds these values and the current collector bytes; a date,
cap, path or implementation change requires another inspection and exact approval.

Only after that approval, `collect` accepts the same fields plus
`--execution-plan-hash` and `--accept-unconfirmed-count-billing`. It claims one new
directory, locks the entire collector lifetime, checks tracked/HEAD-clean task,
runtime and diagnostic code, then preflights existing exact evaluator/probe images.
It never starts Docker, pulls/builds an image, changes the frozen packet or runs the
hidden evaluator. The seed check executes once before another model decision; its
already-paid generation is not charged again. Subsequent decisions share one cap,
retain the full compacted window and reuse native policy, memory and repair feedback.

The eight-response bound is an observation limit, not an action mask. The inherited
time budget includes setup and five seconds for client cleanup. Count/generation
waits are at most 30/300 seconds. Reserve uncached input plus all 25k output before
each dispatch; do not shrink output or retry unknown requests. Count billing remains
unconfirmed and separate from the generation cap; no total invoice guarantee exists.

`result --output <existing-collection>` validates durable outer/child journals and
artifacts without API, Docker or workspace execution. A missing final JSON file can
still have a complete CAS-backed terminal; an unfinished collection returns
`INCOMPLETE_NO_RETRY`. This neither retries a decision nor infers that an admitted
request reached the server. Numeric usage, public patch/check evidence and cleanup
status stay distinct; cleanup uncertainty cannot silently become a clean success.

The exact `1f4b1ff0...` approval was consumed once on 2026-09-13 KST. Collection
`C:\pt\analyses\compaction-episode-collection-20260913` ended
`PUBLIC_CHECKS_SUBMITTED`: five new responses/counts, seven tools including seed and
repair-recheck, one accepted mutation, both visible checks PASS, 91.483s. Generation
cost $0.50483145 under $1.20; count billing and invoice total remain unknown. Client
cleanup CLOSED; public container cleanup confirmed. Result inspection is the only
allowed reuse of this collection, not another collect/resume. Authorization and
read-only analysis: `C:\pt\analyses\compaction-episode-live-20260913`. Native runtime,
old packet/proposal and source run bytes are unchanged; hidden evaluation/safety/
acceptance remain NOT_RUN and official=false. Input grew 107,343 -> 231,983 tokens
as full public reentries accumulated; this one public submission proves neither
long-loop boundedness nor a compaction causal effect. Do not add a new paid sample
or change the native context from this approval.

The later provider-free reentry audit at
`C:\pt\analyses\compaction-reentry-audit-20260913` measured superseded diagnostic
state messages as 84.5% of first-to-last wire-byte growth. Its 46.3% final-size
reduction is an in-memory sizing probe with checked source/action preservation,
not a runnable request, API/token result or adopted context contract. The later opt-in
implementation at `C:\pt\validation\compactstate-20260913` rescues unique historical
observations as well, yielding 517,178 final request bytes (-45.5%) in saved-request
reconstruction. Native/default append behavior stays unchanged. These are byte/evidence
checks, not provider acceptance or token/quality measurements. Another live diagnostic
requires a fresh exact packet and approval; read-only old result inspection is still valid.

The separately approved latest-state packet `429d4173...` / plan `0d45099f...` was
then consumed once on 2026-09-13 KST. Collection
`C:\pt\analyses\compaction-snapshot-collection-20260913` reached public submission:
eight new counts/generations, eleven tools, two repairs, 101.420s, $0.53881155 in
generation cost under $1.20. Count billing/invoice remain unknown. Both public checks
and patch bind a54bfbd1...; cleanup confirmed. No hidden evaluator, native row/resume,
Docker start/pull/build, recompaction or retry. Approval/audit:
`C:\pt\analyses\compaction-snapshot-live-20260913`. This grant is consumed.
Actual input grew 107,319 -> 138,566 tokens; final wire bytes are 59.0% below a
read-only same-action append reconstruction with matching source/native/evidence
inventories. That reconstruction was not dispatched or token-counted. The historical
append episode used fewer calls/repairs and slightly less generation cost; do not
infer faster/cheaper solving, a fresh A/B result or default adoption. Acceptance and
safety remain NOT_RUN, official=false. Only read-only inspection is authorized reuse.

## Opt-in repair feedback experiment

`patchloop dev --repair-recheck` reruns the latest still-failing registered public
check after an accepted repair changes that checked diff, before another inference.
The default is off. Initial edits without a current failure and rejected edits do
not trigger it; other checks remain model-selected. This is a feedback-timing
experiment, not evidence that the agent repairs correctly.

The child check uses the normal sandbox, deadline and one tool action; no additional
model/count call is made. It is recorded as harness-originated, not as a model tool
choice. Its bounded public result enters the next current-state view. Resume requires
the same flag and exact envelope/runtime inputs. Completed results replay; an interrupted
check without a durable result follows the existing owned-container cleanup/recovery
path. No check starts after expiry, uncertainty or exhausted tool budget.

Provider-free validation does not authorize a live experiment. Approve an exact new
task/model/reasoning/env/repeat/cap invocation including this flag separately; do not
reuse an old paid grant or migrate an old run.

The separately approved fresh mini invocation with this flag is complete:
`run_dev_d484ea8a2a8e4ba4` at `C:\patchloop-state`, receipts under
`C:\pt\analyses\repair-recheck-live-20260912`. Exact v2/mini snapshot/medium/root
`.env`/repeat1/$1.20/probes/repair-recheck: EVALUATOR_PASS, task acceptance and safety
PASS, 15 model/count calls, 16 tools, two edits, $0.208261650/163.312s. One child
recheck passes before the next inference; the remaining regression and finish are
model-selected. No provider retry/resume, extra operator check or Docker start/pull/
build ran. Original evidence is immutable and the grant is consumed. Do not infer
automatic default adoption or feature causality from this single successful trajectory.

The approved comparison ran after the user enabled Docker, then **stopped at B2
input counting**. A1 OFF: both public checks PASS, task acceptance FAIL; B1 ON:
task acceptance/safety PASS; B2 ON: regression repaired, other current-diff check
still NOT_RUN, then 25k reasoning-only incomplete and correction-count BadRequestError.
Native terminal COUNT_TIMEOUT_OR_UNKNOWN does not establish a timeout. Detailed
server rejection data was not retained. A2 OFF stays NOT_RUN; no retry/resume or
replacement follows, and unused budget is not permission for another invocation.
Total recorded usage $1.152164400; receipts at
`C:\pt\analyses\repair-recheck-comparison-live-20260912b`. All three automatic
rechecks were current-diff-bound and delivered before inference; the incomplete,
different-trajectory comparison does not establish feature causality. Default OFF.
Preserve the earlier zero-call Docker stop at its original path. The design remains at
`C:\pt\analyses\repair-recheck-comparison-20260912` (canonical packet `af29b90f...`).
It proposes four independent native repeat1 invocations in OFF/ON/ON/OFF order under
identical v2/mini snapshot/medium/.env/probes/runtime settings. Each row has its own
$1.20 cap; the total maximum is $4.80 without borrowing unused allowance. Do not run
`--repeat 4` for one setting, reuse prior grants, alter runtime between cells or restart
failed cells. Bind cell admission and native run ID once in an external observer;
stop the entire comparison on uncertain cost/execution, integrity or safety failure.
The option's context notice is part of the treatment, not a timing-only contrast.

## Explicitly approved live development

First inspect local prerequisites and the task package:

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop doctor
uv run patchloop task validate tasks/dev-train/<task>
```

Then issue one fully specified invocation:

```powershell
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-mini-2026-03-17 `
  --reasoning-effort medium `
  --env-file <credential-file> `
  --max-cost-usd <positive-decimal> `
  --repeat 1
```

That exact command is the development approval for its provider, task, model,
credential file, repeat count, and invocation-wide cap. Live mode accepts only
checked-in `dev-train` tasks. Every active `patchloop/**/*.py`, `pyproject.toml`,
`uv.lock`, trusted `docker/probe_runner.py`, `docker/Dockerfile.sandbox`, and selected
task-package input must be tracked and match HEAD;
unrelated scratch or untracked paths outside those pathspecs are ignored. The
credential file may contain only one `OPENAI_API_KEY=...` assignment. It may be the
ignored repository-root `.env` or an exact external path, but it must never be tracked
or committed.

The required evaluator image must already exist locally at the declared digest.
PatchLoop never starts Docker Desktop or pulls/builds an image. Unknown model
pricing fails before dispatch. The adapter counts the actual request immediately
before generation. The desired response ceiling is 25,000 tokens. The Responses API
counts both reasoning and visible output against it; pre-dispatch admission lowers that
ceiling when necessary to stay inside the invocation-wide cap. Every admitted ceiling
is journaled. The adapter uses zero SDK transport retries and stops all remaining
repetitions when count, transport, or billing state is uncertain. Generation and input
counting use the same
`tool_choice=required` contract, so the provider request and the runner's non-empty
tool-batch requirement agree. V25 keeps one append-only episode: fixed instructions,
immutable initial state, one stable user task, then encrypted reasoning, canonical calls,
matching outputs and compact current-state views in chronological order. Updating budgets
or status never rewrites the prefix or adds a user turn. Each `harness_current_state.state`
is complete for mutable fields; only `public_task` is inherited from the initial message.
No nested JSON edit operations are needed. The last decision's hash-verified input is
extended once, including correction responses. Canonical context artifacts retain the
full audit state; model views omit rolling inspection/coverage accounting and group source
navigation under `current_sources`. Retained source already in native results uses exact
action/field/path/hash/range
references, with full inline fallback when complete delivery cannot be proved.
Existing current-state/source/check validity remains authoritative; historical
native results do not become current PASS. PatchLoop requests
`reasoning.encrypted_content` while retaining `store=false`. Plaintext reasoning,
reasoning summaries, and non-tool response content are not retained or replayed.
`turn_started.native_history` binds item/call/output/reasoning/state-update counts,
the history hash and reconstructed current-state hash.
Provider/decision events record `response_reasoning_context` only as `current_turn`,
`all_turns`, or null; no mode is inferred from a ciphertext. GPT-5.4 mini receives no new
reasoning-context setting. The existing token count and invocation cap apply to the whole
input, which can grow despite a bounded retained-source snapshot. No history dropping,
automatic compaction, extra provider call, or larger cap is introduced.
Stable input prefixes permit cache reuse but do not guarantee it; tool-schema changes,
routing and retention still matter. Accumulated current-state views add historical metadata,
so total serialized size may grow even when duplicated current source is removed.
Measure actual cached input and billed cost in a separately approved live run. No new
cache control or model-specific reasoning option is added by this change.
The application still enforces its smaller grammar: up to four reads/searches, or
exactly one mutation, check, enabled probe, finish, or stop.
`read_file` now explicitly advertises one inclusive range of at most 400 lines; the
limit itself, argument names, complete-line output cap and EOF behavior are unchanged.

`run_probe` is off by default. An exact future live authorization must include
`--enable-probes` to add this capability; enabling it also requires the separate clean
Python image in [the probe runtime contract](../docker/README.md) to be present locally.
Preflight verifies that image and the hash-bound trusted wrapper before provider dispatch.
It does not pull/build an image, start Docker Desktop, or fall back to the evaluator image.
The separately approved twenty-second through twenty-fourth rows enabled this opt-in;
rows 22 and 24 used one baseline probe each, while row 23 did not. These observations
do not establish candidate validation by probing; exact results are in `docs/current-status.md`.
The separately approved twenty-fifth row also enabled probes but did not invoke one.
It terminated at the completion horizon after a public regression failure, without
submission or private evaluation. The separately approved twenty-sixth v18 row,
`run_dev_306785d397d640f3`, reached `EVALUATOR_PASS` (task acceptance and safety PASS)
in 28 model calls and 32 actions for $0.432518400. It also did not invoke a probe.
The initial Docker-unavailable read-only preflight made no run/provider call; the user
started Docker before the one invocation. The separately approved twenty-seventh v19 row,
`run_dev_e68682d51d2a4dfa`, used two successful baseline probes but no candidate probe.
It ended at `LIMIT_REACHED` after four accepted mutations and four failed traversal checks:
29 model calls, 30 actions, $0.349973100, no submission or private evaluation. Eleven model
calls remained, but no mutation could repair the current failure. Source/check identity and
native feedback passed the read-only audit; this is not evidence of task success.
The separately approved twenty-eighth v20 row, `run_dev_a01ff61f95be4a57`, reached
`EVALUATOR_PASS` (task acceptance and safety PASS): 20 model/input-count calls, 21 actions,
two accepted mutations, $0.193324200, and 133.016 active seconds. A public intermediate-mode
failure was repaired immediately, both visible checks passed, and finish submitted the
same patch later applied by isolated evaluation. Probes were enabled but unused; no
working note cited a check, so this row did not exercise the v20 check-result label.
Exact replay, native results, note receipts, execution-policy and patch provenance passed
read-only audit. That result and local validation did not authorize a later invocation.
The separately approved twenty-ninth v21 row, `run_dev_7005744ccb5d4cc1`, reached
`EVALUATOR_FAIL`: public traversal and regression checks passed, isolated task acceptance
failed, and safety passed (`PRIVATE_EVALUATION_FAILED`). It used 32 model/input-count calls,
35 actions, one accepted mutation, $0.482969550, and 290.593 active seconds. The first
candidate at turn 27 exceeded scope (60/50 lines); turn 29 accepted a 48-line replacement,
and turn 32 submitted it. Checked, submitted, and isolated-applied patch hashes match.
V21 intent references and exact saved-input/continuation replay passed read-only audit,
but 15 of 30 inspections added no coverage and no probe ran. This does not establish
efficiency improvement or a cause for the different outcome. All 54 prior journal/envelope
files remain unchanged. No automatic repair, retry, resume, or thirtieth live row is
authorized by this result, the implementation, or local validation. All results remain
unofficial; no hidden evaluator output is reinjected into the coding agent.

The separately approved thirtieth v22 row, `run_dev_f5f058fc5761480b`, reached
`EVALUATOR_PASS` (task acceptance and safety PASS): 29 model/input-count calls, 28 actions,
two accepted mutations and $1.059868350 under the $1.20 cap. Its public regression failure
was repaired on the next turn, and the final 41-line diff passed both public checks and
isolated evaluation. Three baseline probes ran; one failed with a Python syntax error.
The complete active history, count/dispatch identities, correction results, note receipt,
patch identity and execution-policy provenance passed read-only audit. All responses
reported `current_turn`; that is not proof of effective reasoning reuse. Input grew to
90,851 tokens, so fewer zero-coverage inspections did not mean lower cost. This result
does not authorize a retry, resume, thirty-first row, Docker start, or image pull/build.
See `docs/current-status.md` for the exact trajectory and evidence limits.

The separately approved thirty-first v23 row, `run_dev_7754107f07f442e4`, reached
`EVALUATOR_FAIL`: both public checks PASS, isolated task acceptance FAIL and safety PASS.
It used 31 model/count calls and actions, three accepted mutations and $0.775517100.
The final seven-line patch has a trailing-separator double-creation defect; no probe ran.
All 31 inputs reconstruct exactly, and 30 successive prefixes are unchanged. Actual
cached-input share is 73.24%, but total input reaches 2,508,902 tokens and the last input
178,154 tokens; six tool-schema transitions still limit reuse. Lower cost than row 30
is an uncontrolled observation, not proof of improved task-solving efficiency. The 58
prior journal/envelope files and credential bytes are unchanged. No repair, retry, resume,
thirty-second row, Docker start or image acquisition is authorized by this result.

The separately approved thirty-third v25 row, `run_dev_6159179ed34542f9`, reached
`EVALUATOR_FAIL`: public checks PASS, isolated task acceptance FAIL and safety PASS.
It used 20 model/count calls and actions, two accepted mutations and $0.366307650 under
the $1.20 cap. A public parent-mode failure prompted direct repair and recheck before
submission. The saved input correctly labels the previous diff's failure historical;
two mutations remained, so the zero-mutation recheck boundary was not exercised.
Checked/submitted/isolated-applied patch hashes, all 20 input histories and cost records
match. Probes were enabled but unused. This is not evidence that v25 caused the model's
choice or solved the task. No repair, retry, resume, thirty-fourth row, Docker startup or
image acquisition is authorized by this result. See current status for the complete record.

Tool surface v26 adds `public_execution` to public check/probe results and a bounded
current-diff `public_execution_summary` to context. Inspect `executed_changed_ranges`,
`not_observed_changed_ranges`, `no_line_event_ranges` and per-file `status` separately
from the check's PASS/FAIL. `unknown` is not a negative observation. Only launch-thread
Python additions/replacements are measured, with eight-file/256-line selection and a
12,000-byte feedback bound; omission/deletion counts identify limits. The collector is
copied read-only outside the workspace and needs no new image or dependency. Existing
deadlines, owned-container cleanup, output caps and private evaluation are unchanged.
It is advisory in-process instrumentation, not a safety proof or new acceptance check.
Reuse stored completed results on resume; never rerun a check to rebuild this summary.
Old envelopes are not migrated and mismatched nonterminal resumes still fail closed.
The separately approved synthetic Docker collector check/probe pair passed; see
[current status](current-status.md#separately-approved-v26-docker-collector-verification)
and [opt-in diagnostic instructions](../docker/README.md#explicit-local-verification).
That evidence does not authorize repeating Docker work or executing live row 34.
The subsequent row-34 approval paused before provider dispatch: actual v2 checks used
an absolute interpreter path excluded by the collector's old literal-name test. The
path correction preserves declared executable/argv and is covered by actual public
declarations with Docker mocked. The earlier real-Docker pair used bare `python` and
is not evidence for this correction. The subsequent separately approved absolute-path
pair passes with collected feedback, confirmed cleanup and no replay execution; see the
[corrected-path Docker checkpoint](current-status.md#corrected-path-real-docker-checkpoint)
before reconfirming live approval. This does not authorize row 34 or another Docker run.

Fresh exact approval then executed row 34 once on `ae34d076`:
`run_dev_e9f798d9b3bb451c`, `AGENT_STOPPED`, 24 model/count calls and tools, three accepted
mutations, $0.456825750. All four actual public checks collected changed-line feedback;
native delivery and owned-container cleanup verify. The final regression passed, but the
contract PASS belonged to the prior diff. The final native input correctly offered
`run_check` and listed the contract as NOT_RUN; the model claimed completion through
`stop_task` instead of rechecking and submitting. No probe, finish, isolated acceptance or
safety evaluation ran. This is neither task PASS nor a budget/tool-closure failure.
See [the row-34 record](current-status.md#row-34-stopped-before-submission).
Do not resume the terminal, repair/recheck its candidate or initiate another row automatically.

Fresh exact approval subsequently executed row 35 once on `d1660947`:
`run_dev_38e45369894f43b1`, `EVALUATOR_FAIL`, acceptance FAIL/safety PASS, 23 model/count
calls, 25 tools, three accepted mutations and $0.510596700. Two optional final-candidate
probes ran (a compile failure, then a corrected normally exiting probe); both required visible
checks then passed and the model submitted through `finish_task`. All 23 actual input
views retain current completion guidance and check currency; the checked/submitted/
isolated-applied patch identities match. Nine owned containers are absent. Unlike row
34, this row does not exercise PASS invalidation by a later edit, so do not attribute
the changed behavior solely to v27. See [the latest live record](current-status.md#latest-live-observation-row-35-submitted-private-evaluation-failed).
No retry, resume, candidate repair or row 36 follows automatically.

The subsequent separately approved row 37 on `2a4cb654`,
`run_dev_36024bd4361343dd`, ends at `EVALUATOR_PASS`: task acceptance PASS/safety PASS,
28 model/count calls and tools, two accepted mutations, $0.651385650. After one public
regression failure, the model repairs the candidate, rechecks both current-diff obligations
and submits. Checked/submitted/isolated-applied patch hashes match; all seven owned
containers are absent. Native mutation references preserve source identity and reduce
those two result payloads by 32.0%. This is live delivery and one task success, not causal
evidence for improved general agent efficiency. No probe or stop ran. See
[the row-37 record](current-status.md#row-37-submitted-and-passed-isolated-evaluation).
Its terminal is immutable; no retry, candidate repair/recheck or additional row follows automatically.

The subsequent separately approved row 38 on `2c303bfc`,
`run_dev_91f8c05b570c439b`, ends at `AGENT_STOPPED`: 20 model/count calls, 22 tools,
four accepted mutations and $0.380645550. After the last mode repair, the model stops
without rechecking. Both current checks were NOT_RUN, `run_check` and sufficient completion
budget remained, and the input explicitly marked the old failure historical/awaiting_recheck.
Do not repeat the stop summary's unverified claim that the final candidate still failed.
No submission or isolated evaluation ran. The permission labels were delivered correctly,
but one disallowed helper edit was still attempted. All memory updates were null, so v30's
note-expiry/receipt changes remain unexercised live. Three owned containers are absent;
continuations, source references and the immutable journal verify. See
[the row-38 record](current-status.md#row-38-stopped-after-an-unverified-final-repair).
No retry/resume, candidate repair/recheck or row 39 follows from this terminal.

The separately approved row 39 on `dfb3f8e9`, `run_dev_eaad5c70be16434f`, ends at
`LIMIT_REACHED`: 33 model/count calls, 34 tools, four accepted edits and $0.712855950.
The final edit is actually rechecked, but its one-line parent guard makes `next_dir`
assignment conditional: the regression changes from four failures to 21 UnboundLocalError
failures. With no accepted edits left, the horizon stops before another provider dispatch;
seven model/66 tool calls remain. Final regression is FAIL and contract NOT_RUN; the earlier
contract PASS is historical. No probe, voluntary stop, submission or isolated evaluation ran.
All four v31 mutation receipts/native deliveries match completed and baseline identities;
continuations, prefixes, policies and journal verify, and five owned containers are absent.
This is successful identity delivery and observed rechecking, not causal effectiveness proof.
See [the row-39 record](current-status.md#latest-live-observation-row-39-rechecked-and-exhausted-accepted-mutations).
Its terminal is immutable. No candidate repair/recheck, retry/resume or row 40 is authorized.

The subsequent read-only audit reconstructs candidate text only in memory and external
Git blobs: a separated assignment fits 50 lines, while a three-line guard also fits after
removing one added blank line. Scope PASS and AST placement are not semantic test PASS.
The first edit input retains all 572 observed source lines and public bytes/mode checks;
the model's named `create_dir` inspection actually covered a different `makedir` body.
No runtime change follows from these findings. The reproducible scripts and bounded result
are under `C:\pt\pl39-analysis-a`; no historical task execution or new live authority follows.

The later design-only next-action packet under `C:\pt\pl39-decision-design-a` proposes
six single-response samples: three frozen checkpoints, medium/high on the same model.
It stays PREPARED_NOT_EXECUTABLE with dispatch disabled; normal CLI/resume cannot run it.
The implemented [standalone sampler](../diagnostics/decision_sampler.py) is outside the
unchanged v31 runtime and has provider-free tests. From the checkout, its read-only
validation command is:

```powershell
uv run python -m diagnostics.decision_sampler validate --packet C:/pt/pl39-decision-design-a/packet.json --packet-hash sha256:200e80988694023f381ac77f77ff5a62348f34f7f8200e4c6548e7a54caa8347 --source-state-root C:/patchloop-state
```

This prints request/sampler/runtime/price identities and historical cost reservations,
not an authorization or a current price quote. `collect` additionally requires
`--approve-six-responses-zero-tools`, `--sampler-hash`, `--credential-file` (absolute),
`--result-root` (new and external), `--max-cost-usd 1.20`, `--pricing-hash` and
`--pricing-verified-on`. The operator must actually check the official rates for the
fixed snapshot/default tier on that UTC date before asserting this price review.
The exact approval must name the packet and sampler hashes, task v2, model, both
efforts, one response for each of six cells, `.env`, new root and zero tool executions.
The user subsequently approved by reference the disclosed six-cell scope. That one
pilot is complete as `run_dev_sample_789ffee05f9d4473` in `C:\pt\pl39-decision-live-a`:
six counts/generations, SAMPLES_COLLECTED, known $0.392849400 cost, 51.657s and zero
tool executions. The assistant rechecked official Standard rates before dispatch;
the date flag is a review attestation, not an automatic quote or separate human audit.
This diagnostic is not row 40. No further paid calls, retry/resume or task execution
are authorized. Its original $1.066516500 planning reservation used historical
counts/rates, not a live quote; the $1.20 cap did not imply spending all of it.
Each current request is counted just before generation; future cells retain historical
input reservations plus their full 25k output allowance. Higher later counts can stop
the pilot, never silently reduce a ceiling. Input count/create have zero retries;
uncertainty stops the whole pilot and known incomplete output receives no correction.
Usage is journaled before response artifact processing. Raw SDK errors and plaintext
reasoning are not saved. Request artifacts preserve tool/property order and bind an
order-sensitive hash in addition to the original canonical content hash. A fresh root
is claimed exclusively before any credential loading. Existing roots cannot be collected
again, even after a crash; no resume exists.
Use `uv run python -m diagnostics.decision_sampler inspect --result-root <absolute-root>`
only to read durable terminal or interrupted/unknown status. It never replays or writes.
Public review artifacts hide arm/effort/cost/latency; the journal records the unblinding
map and independently shuffled presentation order. Neither batch grammar nor unexecuted
source is assigned task acceptance or automatic rubric grades. The completed pilot's
read-only anonymous static findings and later unblinding audit are under
`C:\pt\pl39-decision-review-a`; all six exact ordered requests/continuations verify.
Both efforts propose the same erroneous conditional assignment at the final checkpoint.
That static finding is not an executed task result or a general comparison of efforts.
Do not execute returned tools, append future outcomes/rubrics to model input, lower one
arm's 25k ceiling under budget pressure or equate static grading with task acceptance.
This pilot and any ordinary row 40 are separate requests, never automatic retries.

The later approved preparation-only fresh-state design is in
`C:\pt\pl39-fresh-state-design-a`. It freezes the original pre-turn-32 medium request
against a new request containing the complete current public state, all 32 public
call/result pairs as quoted data and 665 resolved current source lines. B has no native
reasoning/call/output history but retains the public archive; this is a bundled context
representation/fresh-reasoning comparison, not deletion inside a live episode.
The offline preparer/validator rechecks this packet without changing it:

```powershell
uv run python -m diagnostics.fresh_state_design validate --source-packet C:/pt/pl39-decision-design-a/packet.json --source-state-root C:/patchloop-state --output-root C:/pt/pl39-fresh-state-design-a
```

It must reconstruct the exact original A request, current state, public archive,
current source ranges and ordered tool schemas without filesystem source reads or
provider access. Request sizes (684,213/265,083 UTF-8 bytes) are not fresh token counts.
The packet stays PREPARED_NOT_EXECUTABLE, dispatch=false. A1/B1/B2/A2, medium in both
arms, four responses, zero tools, 25k output per response, 1,800s and $1.20 are a proposed
future execution scope, not authority. The six-cell collector rejects this packet.
Do not pass it to normal dev/resume or rewrite either historical design.

The separately implemented four-response collector now has its own read-only validation:

```powershell
uv run python -m diagnostics.fresh_state_sampler validate --packet C:/pt/pl39-fresh-state-design-a/packet.json --packet-hash sha256:1839a26def6adea31a288ccf2c084d8a77b80b166039e3491dffd141cbb1d8d7 --source-packet C:/pt/pl39-decision-design-a/packet.json --source-state-root C:/patchloop-state
```

Validation loads no credentials/client and makes no input-count call. It prints the
new collector identity (hashes of the shared sampler, frozen preparer and new entry
point), fixed ordered request identities and registered-rate reservations. The shared
engine's source hash changes with this refactor; historical receipts keep their old
hashes and are not migrated. A later paid approval must use the newly printed identity.

`collect` additionally requires `--approve-four-responses-zero-tools`, `--sampler-hash`,
an exact absolute `--credential-file`, new external `--result-root`, `--max-cost-usd 1.20`,
`--pricing-hash` and an actually reviewed same-UTC-day `--pricing-verified-on`.
Approval must cover the frozen task v2/checkpoint, exact model, medium in both arms,
A1/B1/B2/A2, four independent responses, zero tools and no corrections/retries/chaining.
That exact scope was subsequently approved once and is now completed as described
below. Retain 25k output per response and 1,800 shared active seconds; do not reuse the
old pilot's responses as fresh controls or interpret this completion as new authority.

The four-response policy counts each request just before create and protects future
full-output capacity using an enforced 272,000-input-token ceiling, not A's historical
count as an estimate for B. Above-ceiling counts stop with INPUT_LIMIT_EXCEEDED; a fresh
count that no longer fits the invocation cap stops with COST_CAP_REACHED. Neither
condition changes the inputs or reduces output capacity. Fresh counts are still unknown
until separately approved execution (now measured for this completed invocation).
Input/transport/billing uncertainty stops all
remaining cells; known incomplete responses are recorded without correction. Usage
precedes continuation processing; selected actions never execute. The shared blinding,
hash-chained journal, exclusive new root and no-resume behavior are unchanged.
Use `uv run python -m diagnostics.fresh_state_sampler inspect --result-root <absolute-root>`
for read-only terminal/interrupted receipts. This is not a normal live row or task PASS.

The approved four-response invocation is `run_dev_sample_1272d5c8122c47cf` under
`C:\pt\pl39-fresh-state-live-a`: SAMPLES_COLLECTED, four counts/responses, zero tools,
36.344 active seconds and known $0.195174300 cost. A counts 153,464 input tokens;
B counts 66,054. Official Standard prices were reviewed on 2026-09-07 UTC before
dispatch. Read-only integrity, anonymous static observations and later unblinding are
in `C:\pt\pl39-fresh-state-review-a`. Original input yielded two mutation proposals;
fresh input yielded two inspection responses. Static candidate defects and repeated
reads do not establish an end-to-end success rate. No candidate/test was executed,
all acceptance/safety states remain NOT_RUN and this is not row 40. Do not retry,
resume or collect additional samples without a new exact approval.

Tool surface v34 compresses only the optional memory block and repeated memory/concern
schema descriptions. Keep nullable fields, all required properties, constraints and
tool order unchanged: optional updates are represented with null, not by removing
required properties from a [strict object](https://developers.openai.com/api/docs/guides/function-calling#strict-mode).
Storage, evidence validation, receipts, lifecycle, replay, model settings, limits and
action policy are unchanged. Old nonterminal envelopes fail exact runtime matching;
do not migrate them. This local-only change authorizes no live row or paid sampling.
Canonical schema byte reductions do not measure billed tokens or memory effectiveness.
Future separately approved observations should distinguish useful facts available
before decisions, later retention/citation support and actual repair/submission,
not simply count how often the model writes notes. Same-response notes are not
evidence of prior-memory reuse; null notes do not erase native history or continuation.

The later exact row-43 approval is consumed: v34 `run_dev_9b91e06c13ff4bd3` stops
voluntarily after four edits, 22 model/count/tool calls and $0.464054850, without
submission/evaluation. The public contract passes on the third candidate; the final
macOS-only repair is unchecked and does not restore the reported Windows error
translation. At stop, checks remain available and both final-diff statuses are NOT_RUN.
No tool reopening, cap increase or mandatory-check patch is justified merely by that
stop. All memory updates are null, with prompt/schema and projection verified. Preserve
the distinction between delivered information and correct use of it. Read-only evidence
is `C:\pt\pl43-review-a`; no additional check/candidate execution, paid retry/resume,
comparison or row 44 is authorized by this completed invocation.

### Model x state-history diagnostic: row 43

Later public-only check of native run `run_dev_91384f8a97354835`'s frozen third edit
is complete at `C:\pt\evaluations\mini-third-candidate-20260912`. Two registered
checks once each, separate no-hardlink base clone, exact 30-line `7c97d024...` patch.
Contract fails the same line23 mode assertion as the saved fourth-candidate result;
the original public bytes example already succeeds. Regression reports 6 failed,
511 passed, 570 skipped. No new baseline or fourth-candidate check. Operator-only
evidence must not overwrite the source run or claim overall third-candidate PASS.
13.189s, $0 model cost, no provider/count/hidden evaluation/repair/resume/retry.
Scope/postimage/check-policy identities and 3,388 protected files verify. Docker and
pinned image were already available; no start/pull/build. Read `result.md` before a
separate repair/recheck-loop experiment decision; no automatic next execution.
Runtime/task unchanged, task acceptance/safety NOT_RUN, official=false.

The subsequent exact fresh-start default-mini invocation is complete:
`run_dev_91384f8a97354835` at `C:\patchloop-state`, analysis/approval at
`C:\pt\analyses\mini-fresh-start-20260912`. New task/base with no checkpoint, notes,
source observations or answer patch; full native limits, v2, mini snapshot/medium/25k,
root `.env`, repeat1, probes enabled and $1.20 cap. LIMIT_REACHED after 27 responses/
counts/tools, four edits and three failed public checks, $0.441195300/220.438s.
Only accepted mutations are exhausted. Final 32-line diff fails the intermediate
mode assertion; no regression, submission or isolated evaluation ran.
The unchecked third repair was treated as still failing despite delivered historical
labels, NOT_RUN and pending-recheck guidance. Its later operator-only public check
is recorded above under separate approval; the native-run grant remains consumed.
Do not repair it or infer an implemented loop change from the counterfactual result.
All request/continuation and check-policy evidence verify, with 3,231 protected files
unchanged. No default-loop change, retry/resume, further provider call or Docker
start/pull/build is implied. Task acceptance/safety NOT_RUN, official=false.

The subsequent, separately approved evaluation of the two frozen public submissions
is complete at `C:\pt\evaluations\pl43-mini-recovery-v1` (`result.md`). Exact C1/A/1
49-line patch: task acceptance PASS. Exact C1/A/2 28-line patch: task acceptance FAIL,
aggregate `PRIVATE_EVALUATION_FAILED`. Both public regression/scope/evaluation safety
PASS. Two unchanged evaluator invocations, two fresh no-hardlink workspaces,
8.518s/8.356s, zero provider/count/probe calls and $0 model cost. Private case/error
details were not returned to the agent or used for diagnosis. Do not repair or rerun
these frozen candidates under this consumed grant. Their original diagnostic records
remain NOT_RUN; separate operator results do not retroactively rewrite source runs.
The separately approved fresh-start reproduction is recorded above; these checkpoint
results are not an overall success rate. No default-loop change is implied.

Completed follow-up: `mini-recovery-budget-v1` used mini-only A/B at both
checkpoints with two fresh repetitions (eight episodes), no independent eight-response
cutoff, and the original remaining native budgets/gates. This opt-in preparation
profile does not change the default four-arm/eight-response diagnostic. First inputs
are unchanged; both arms accumulate new native state and encrypted reasoning.

Exact consumed packet/protocol: `C:\pt\analyses\pl43-mini-recovery-design-v1`.
Result root: `C:\pt\analyses\pl43-mini-recovery-live-v1`,
`run_dev_episode_collection_a78ccd1085a8478b`: eight completed episodes, 76 responses
and input counts, 83 tools, $2.55174405 / $5, 994.987s, billing fully known.
Public submissions: C1/A 2/2, C1/B 0/2, C2/A and B 0/2. Six native limits exhausted
accepted mutations; none was diagnostic censoring or an incomplete response.
Assessment: `C:\pt\analyses\pl43-mini-recovery-assessment-v1\analysis.md`.
Hidden/task acceptance and safety NOT_RUN; official=false. This does not justify
default context reduction or further paid work. The exact grant is consumed.

The contract fixed `gpt-5.4-mini-2026-03-17`, medium, 25k, root `.env`, one shared
$5/1,800s invocation, repaired count30s/response300s waits, and A/B depth reserve
$0.633 at full 272k input/25k output before actual JIT counts. The native upper
bound of 188 new responses/counts was not a guaranteed sample size. Official prices
were verified on the execution UTC date, 2026-09-11. No automatic retry, resume,
extra samples, Docker start/pull/build, hidden evaluator or default agent changes.

The preparer's `--profile mini-recovery-budget-v1` option selects this fixed design;
do not overwrite the prepared root. Read-only revalidation of the actual packet:

```powershell
uv run python -m diagnostics.model_state_episode_collector validate `
  --packet C:/pt/analyses/pl43-mini-recovery-design-v1/execution/packet.json `
  --packet-hash sha256:ce3e9de64c93c324fa78ef2132b7f569be924c6fcb9db0511faa712f9016a976
```

This command does not count tokens, load credentials or execute task actions.
It does not authorize re-collection of the consumed packet. New execution requires
a new exact packet/grant; retain these roots unchanged. The protocol seals anonymous
public observations before condition mapping and distinguishes final-diff checks,
recovery, native limits and diagnostic censoring.
For implemented/provider-free evidence see [current status](current-status.md).

The exact packet grant is consumed. Collection at
`C:\pt\analyses\pl43-model-state-live` completed 16 responses/counts for
$0.9615305 / $5 in 159.184s (`run_dev_sample_4bf128b8d21744d5`). The earlier host
denial started no process; later explicit transmission/spend approval preceded
the first actual call. No retry/resume or automatic additional sample is authorized.
Public assessment at `C:\pt\analyses\pl43-model-state-assessment` records 14 valid
inspection batches and two admitted candidates, with four actual Docker checks.
Anonymous observations precede the stored unblinded report. Only GPT-5.4/history
produced mutations: C1/1 fails the contract but passes regression; C2/2 passes both.
Inspection is not scored as failed repair. The tiny, non-repeated executable outcome
does not isolate a cause or justify a default change. See `analysis.md` and
`evidence-audit.json` in that external assessment root. Hidden acceptance is NOT_RUN.

The standalone `diagnostics.model_state_sampler` compares mini versus GPT-5.4 and
older state descriptions present versus absent at pre-turn14 and pre-turn21.
All conditions are fresh requests, without old encrypted reasoning; identical
public source bodies and the entire quoted tool archive remain in both variants.
This does not test a native-loop continuation reset or authorize a default change.

The separate short-episode preparer now uses preparation schema v2. It preserves
these public inputs but replaces the unsent snapshot instructions with a multi-turn
contract: latest nested state is authoritative, new results are native, and the
initial archive/source_bodies remain checkpoint evidence. Original and transformed
request hashes are separate and bound alongside ordered wire and instruction hashes.
Old episode preparations are rejected, not migrated; existing runs remain read-only.
The standalone sampler described here is unchanged. The short-episode collector
now binds per-request waits in a new exact packet: count 30s, response 300s, clipped
to remaining execution time. Async SDK cancellation bounds the whole response wait,
not just individual reads. Error receipts distinguish waiting from local processing
without saving SDK messages, response bodies or plaintext reasoning. Verified usage
and late parsed decisions survive, but no tool executes from a late response.
Client cleanup is bounded at 5s per owned client, with durable outcomes. Timeouts
stop all arms; cancellation does not prove zero billing and never permits automatic
retry/resume. Old grants remain consumed. Local validation is not a renewed grant
or evidence of better agent performance. See [current status](current-status.md).

Provider-free preparation and validation:

```powershell
uv run python -m diagnostics.model_state_sampler prepare `
  --source-state-root C:/patchloop-state `
  --output-root C:/pt/analyses/pl43-model-state-design
# The packet is already prepared; do not recreate its existing root. Validate:
uv run python -m diagnostics.model_state_sampler validate `
  --source-state-root C:/patchloop-state `
  --packet C:/pt/analyses/pl43-model-state-design/packet.json `
  --packet-hash sha256:8e5c7710ea7162f6f91bd31fcdc9b05b5098afc61330108243aa9572d04d72b7
```

`prepare` requires a new external root. `validate` never loads credentials or counts
tokens. A later exact grant must name this packet/implementation, both snapshots
`gpt-5.4-mini-2026-03-17` and `gpt-5.4-2026-03-05`, medium, 25k, maximum 16 independent
responses, root `.env`, new result directory, and shared $5 cap. Transmission to
`https://api.openai.com/v1` consists of the frozen public task/source/tool/state
inputs. The key is authentication only. No private evaluator/reference patch or
old encrypted reasoning is transmitted; new opaque reasoning is stored, never its
plaintext/summary. The proposed $5 does **not** authorize collection.

After approval, `collect` adds `--approve-up-to-sixteen-responses-zero-tools`,
`--sampler-hash`, absolute `--credential-file`, fresh `--result-root`,
`--max-cost-usd 5.00`, `--pricing-hash`, and execution-date `--pricing-verified-on`.
The official [Standard rates](https://developers.openai.com/api/docs/pricing) are
bound in packet `pricing.json`. Reserve each balanced four-arm block at full 25k
output and 272k input bounds with no cache discount, then count actual input JIT.
Insufficient block reserve stops before counting the next block, potentially below
$5. Never lower output, substitute a model, retry, resume or buy more samples.
`inspect --result-root <absolute-root>` is read-only.

The separately authorized `diagnostics.model_state_review evaluate` takes the
same packet/hash/source plus `--collection-root`, new `--assessment-root`, new
`--scratch-root C:/pt/tmp/<unique-name>`, `--task <v2-package-directory>` and
`--approve-public-checks`. It requires already-running Docker and the existing
digest-pinned image; it never starts/pulls/builds. Each mutation is admitted against
its exact historical anchor and complete scope, in an isolated checkpoint copy.
Only the two public checks run; hidden evaluation remains `NOT_RUN`. Invalid or
missing anchors do not silently become source reads. Inspection-only proposals
receive bounded validity evidence and unassessed mutation quality, not automatic
failure. Cache reuse is diagnostic evidence, not original-agent execution credit.

Read the frozen anonymous observations before invoking `report` with the same
packet/hash/source, collection and assessment roots. `report` is read-only and
adds conditions, repetitions, model IDs, input/output tokens and costs. No paid
judge or automatic causal conclusion is used. Compare repeated directions across
both checkpoints; missing/unevaluable samples remain censored. Even a public-check
PASS is not task acceptance, native-loop success or a generalization claim.

### Draft review pilot: row 43

`diagnostics.draft_review_sampler` compares a neutral second opportunity with an
explicit draft/public-requirement review instruction. Both receive the first
requirements-focus A1 proposal as unexecuted data on the original turn-14 context.
The draft's new reasoning is not imported; old native history/13 reasoning items,
tools, settings and state remain unchanged. No known defect hint or repair is supplied.
This is one fixed draft, two responses per arm, not a whole-agent quality benchmark.

The first actual approved collection is complete at
`C:\pt\analyses\pl43-draft-review-live`, run `run_dev_sample_28ab0479aac64fe9`,
with four responses/counts, $0.0700872 / $1.20 and 38.615s. A prior host rejection
started no process; explicit payload/destination approval followed it. The grant
is now consumed. Audit at `C:\pt\analyses\pl43-draft-review-audit` preserves the
anonymous-before-mapping review: all four proposal ASTs equal the fixed draft,
with no executable-code improvement or proposal execution. The frozen packet and
live root are immutable; another collect is not a resume or an authorized retry.

The prepared packet is `C:\pt\analyses\pl43-draft-review\packet.json`, hash
`sha256:3b08b83f24914ff9b05d18288926007fc8ec2314653e44154f26288ed83c029e`.
Collector hash:
`sha256:1706cf856e9b61bcdd33d7a6bcd878f1109adb615ebdc174d2f4a12fa999bed9`.

```powershell
uv run python -m diagnostics.draft_review_sampler validate `
  --source-state-root C:/patchloop-state `
  --draft-state-root C:/pt/analyses/pl43-requirements-focus-live `
  --packet C:/pt/analyses/pl43-draft-review/packet.json `
  --packet-hash sha256:3b08b83f24914ff9b05d18288926007fc8ec2314653e44154f26288ed83c029e
```

Preparation/validation use no credential loading, token count, provider or task execution.
Future approval must identify this packet/collector, task
`pyfakefs-makedirs-parent-traversal` v2, `gpt-5.4-mini-2026-03-17`, medium, root `.env`,
four independent A1/B1/B2/A2 responses, zero tools, shared $1.20 and a newly approved
external directory; the recorded live root is already consumed. Transmission includes the historical
public task/source/tool context, encrypted reasoning and unexecuted public draft
to `https://api.openai.com/v1`; the key is only for SDK authentication. Private
evaluators/reference repairs/plaintext reasoning are not supplied. Old grants are consumed.

`collect` takes the validation arguments plus `--approve-four-draft-responses-zero-tools`,
`--sampler-hash`, absolute `--credential-file`, `--result-root`, `--max-cost-usd 1.20`,
`--pricing-hash`, and `--pricing-verified-on` after fresh execution-date pricing review.
It keeps the existing JIT count, full 25k/future-response reservation, 272k input limit,
zero retries and global uncertainty stop. No draft/tool execution, correction,
chaining or evaluator is included; `inspect` is read-only. Static anonymous code
review precedes unblinding. Any apparent improvement requires separate execution evidence.

### Requirements proximity pilot: row 43

`diagnostics.requirements_focus_sampler` freezes the same pre-first-mutation turn 14
at `C:\pt\analyses\pl43-requirements-focus`. A matches the historical canonical
request hash; B only repeats the verbatim public issue and every visible check
ID/command in the latest state. Prior native history, opaque reasoning, tools/order,
notes and settings are identical. No private input, new behavior example or proposed
solution is added. This is proximity plus repetition/extra bytes, not a pure position
or memory intervention. Full request sizes are 253,546/256,004 bytes; A's 49,648 count
is historical and B is uncounted.

The fixed objective, reviewer criteria and one-variable comparison follow the
[evaluation design guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices#design-your-eval-process).
This is a small diagnostic, not a model-quality or complete-agent benchmark.
The following original provider-free validation uses the packet's recorded `d5a411a`
implementation; later diagnostic inspector changes alter its exact sampler identity.
Do not rewrite the old packet. Validation does not load `.env`, count input, or contact OpenAI:

```powershell
uv run python -m diagnostics.requirements_focus_sampler validate `
  --source-state-root C:/patchloop-state `
  --packet C:/pt/analyses/pl43-requirements-focus/packet.json `
  --packet-hash sha256:7bd2b499101625f38ec4fbc8bc5d612e82da39f6dacd6ab6d657fea48bfb3870
```

Collector hash is
`sha256:b9007be87e169976263176dc9c001c46992b2730e4a1c819e228df45a6862f58`.
Future exact approval must identify this packet/collector, task
`pyfakefs-makedirs-parent-traversal` v2, `gpt-5.4-mini-2026-03-17`, medium, `.env`,
four independent responses A1/B1/B2/A2 (two per arm), zero tools, shared $1.20 cap,
and a fresh result root such as `C:\pt\analyses\pl43-requirements-focus-live`.
This is not `patchloop dev --repeat 1`, a normal live row, or approval inherited
from a completed comparison.

`collect` takes the same source/packet arguments plus
`--approve-four-focus-responses-zero-tools`, `--sampler-hash`, absolute
`--credential-file`, `--result-root`, `--max-cost-usd 1.20`, `--pricing-hash` and
`--pricing-verified-on` (execution UTC date). Review registered rates freshly first.
The shared collector reserves all 25k output tokens and future samples, enforces
272,000 input tokens, stops on any count/transport/billing/continuation uncertainty,
and never retries or lowers the output ceiling. No sampled tool execution, response
chaining, correction, judge, task workspace or evaluator runs. `inspect` is read-only,
not resume. Static anonymous action review precedes unblinding; accepted edits,
checks, repair and submission are NOT_RUN, not inferred from proposed code.

This pilot is now complete after the user explicitly approved transmission of the
historical public task/source/tool context and encrypted reasoning to
`https://api.openai.com/v1`; `.env` was used only for SDK authentication. The earlier
host rejection started no process/count. The actual invocation on `d5a411a` is
`run_dev_sample_e54f9963571a4f1d` in `C:\pt\analyses\pl43-requirements-focus-live`:
four counts/completed responses, $0.081974700, 48.434s, zero tools/retries/evaluation.
Input counts are A 49,648 / B 50,210; all ordered requests and continuations verify.
The approval is consumed; `inspect` remains read-only, and no new collection,
correction, feedback rollout or live row is included.

Anonymous-first review is at `C:\pt\analyses\pl43-requirements-focus-review`.
All four proposals falsely treat their newly created leaf as preexisting and apply
leaf mode to intermediate directories. A2 also mismatches the observed old_text.
These are static proposal contradictions, not executed test results. No default
prompt change follows; the small single-checkpoint comparison shows no benefit from
this proximity-plus-repetition treatment. Different cache warmth invalidates using
per-arm cost as an efficiency result. All memory updates are null; encrypted history
was retained, but its internal semantic use is not observable.

### Failure-order pilot: row 43

The later implementation-only go-ahead wires the pinned pre-turn-21 audit at
`C:\pt\pl43-decision-a` through `diagnostics.failure_order_sampler`. It authorizes
no paid collection. The prepared packet at `C:\pt\pl43-order-design-a` must stay
immutable; validate it without loading `.env` or contacting OpenAI:

```powershell
uv run python -m diagnostics.failure_order_sampler validate `
  --audit-root C:/pt/pl43-decision-a `
  --source-state-root C:/patchloop-state `
  --packet C:/pt/pl43-order-design-a/packet.json `
  --packet-hash sha256:95ac3ffe75d4cd4587dd1a5db0ec35e9b6a3a28aa6698c3a13c6f58f300e2664
```

Both A and B preserve native calls/results, encrypted reasoning and older state
views; only B's latest failure-summary rows change order. Preserving reasoning and
matching native tool items follows the [Responses continuation guidance](https://developers.openai.com/api/docs/guides/reasoning#keeping-reasoning-items-in-context).
No summary text or plaintext reasoning is retained. Model, medium reasoning, 25k
output ceiling, tool schemas/order, source and budgets remain fixed. Full requests
are 424,331 bytes each; only A has a historical count (91,222), not a fresh API count.

Future `collect` requires the separate flag
`--approve-four-order-responses-zero-tools`, the same packet/audit/state arguments,
`--sampler-hash`, absolute `--credential-file`, new external `--result-root`,
`--max-cost-usd 1.20`, `--pricing-hash` and `--pricing-verified-on` (execution UTC date).
The prepared collector hash is
`sha256:8d7cc26d63c85a25306f64ac335eaedf0738a12d231036c7ab1b307627279bbc`.
Exact approval must name this packet/collector, v2 task, model, medium, four
independent A1/B1/B2/A2 responses, zero tools, credential path, cap and result root.
Earlier row, six-response or fresh-state approvals do not cover this comparison.

The shared collector counts immediately before each possible dispatch and reserves
future samples at the enforced 272,000-input-token ceiling. Registered prices must
be freshly reviewed before live use. Count/cap failure never shrinks the 25k output
ceiling. Any transport, billing or continuation uncertainty stops all later samples;
there is no paid retry, response chaining, correction, judge or tool execution.
`inspect --result-root <absolute-root>` is read-only, not resume. Review anonymized
public actions before unblinding; proposed edits are unexecuted, task acceptance and
safety stay NOT_RUN. One checkpoint with two samples per arm is not a quality estimate.
Provider-free tests/fake collection were completed without live authority. The user's
later explicit instruction to execute this experiment without another approval request
authorized the prepared four-response pilot by reference. It is now complete on
`08ec618f` as `run_dev_sample_36bef4eebfaa4954` at `C:\pt\pl43-order-live-a`:
four counts/completed responses, zero tools/retries, $0.119271000 under the shared
$1.20 cap and 37.890s. Both arms count 91,222 tokens; all continuations and exact
ordered requests verify. Acceptance and safety are NOT_RUN; it is not normal row 44.

Anonymous-then-unblinded review is at `C:\pt\pl43-order-review-a`. Original-order A1
proposes both macOS and Windows repairs, but its complete text diff is 54/50 lines;
the other three responses request inspection. No proposal is applied and no gateway
or check verdict is inferred from these samples. Latest-summary reordering shows no
clear benefit in this small pilot. Original input already permits combined repair;
joint repair selection and patch scope remain the observed integration problem.
All four note updates are null; that is not a memory intervention. Cache differences
prevent using per-arm cost as an efficiency result. No default policy change, further
paid sampling, tool-feedback rollout or row 44 is authorized by the consumed pilot.

The preceding v33 surface separates current-diff failure from repaired-but-unchecked status
in the derived model view. `current_public_failure` keeps actual current failures;
`pending_recheck` names the unchecked candidate, earlier failed diff and exact native
receipt. Only a matching action/check/diff and full failure payload permits the
reference; missing delivery retains bounded historical/unbound details. Existing
canonical audit context and native history are not rewritten. Recheck clears the
pending card or replaces it with a current failure. Guidance remains advisory, and
tool inputs/order, action masks, model settings and limits are unchanged. Old envelopes
are not migrated; nonterminal resume still requires an exact runtime/input match.
The provider-free implementation authorized no row 41, paid retry or Docker execution;
the later exact row-41 approval and outcome are recorded below.

The preceding v32 contract binds complete-line public check output and terminal-format diagnostics.
The sandbox byte cap, per-stream gateway 12k-character cap and recent-check 4k-character
cap remain unchanged; clipping at any stage is reported. Diagnostics use the captured
public result before gateway clipping, without further filesystem access. Up to eight
literal failure lines / 4,000 characters preserve public failure IDs and comparison
text, with omission metadata. Unknown/mixed exception types are null. On restart,
completed results keep their recorded diagnostic bytes; old envelopes/journals are not
migrated. No paid invocation or historical rerun is authorized by this local repair.

The later separately approved normal row 40 runs v32 unchanged:
`run_dev_766c5a6ab2f04d82`, 25 model/count/tool calls, four accepted edits, $0.461354550,
197.000 active seconds. It ends at LIMIT_REACHED with 15 model calls/75 tools left
but no accepted mutation remaining. The final 50-line diff passes the public traversal
contract and fails seven upstream cases (510 passed/570 skipped); no probe, submission
or isolated evaluation occurs. Both earlier TypeError summaries reach the next turn.
The final seven-line mixed-error summary is complete, exception type is null, and
gateway clipping is reported; there is no model turn after that final failure.
All 75 saved artifacts, 24 input prefixes, four mutation identities and four execution
policy hashes verify; four exact owned containers are absent. Actual turns 22/23
mark the previous error historical and recommend rechecking, yet the fourth edit
adds a type coercion contradicted by `splitdrive`'s slice-preserving returns. Do not
interpret error availability as correct use, or this run as proof of a new harness
defect. The read-only report is `C:\pt\pl40-review-a`; prior state and runtime are
unchanged. No further paid invocation, retry/resume or candidate execution is authorized.
See [the row-40 record](current-status.md#latest-live-observation-row-40-type-repair-and-mutation-exhaustion).

The separately approved normal row 41 uses v33 unchanged at `96d4a122`:
`run_dev_872af7b3c9524a04`, EVALUATOR_PASS / task acceptance PASS / safety PASS,
22 model/count calls, 23 tools, two accepted edits, $0.431456850 and 265.983 active
seconds. The public permission failure is repaired, rechecked, followed by 517 passing
upstream cases (570 skipped), and submitted as the same 30-line artifact applied in
isolated evaluation. Probes are enabled but unused. The native pending-recheck view
is observed before the model selects recheck; no check was forced. Three earlier
proposals were rejected for path/scope constraints, and the first accepted edit is
still turn 17. All prior state/credential/task/history bytes are preserved. Read-only
integrity, outcome and note receipt review: `C:\pt\pl41-review-a`. This is one
unofficial success, not proof of a v33 effect or generalization. That receipt alone
did not authorize row 42 or another paid invocation.

The subsequent approval by reference authorizes only normal row 42 once under the
same task/model/medium/.env/repeat-one/$1.20/probes/state-root conditions. Completed
run `run_dev_2dc51a86320d43d1` is EVALUATOR_FAIL / acceptance FAIL / safety PASS:
18 model/count calls, 19 tools, one accepted edit, $0.287173950, 197.140 active seconds.
Both visible checks pass and the same 45-line artifact is submitted and evaluated.
Private acceptance fails; this is not a transport, provenance or deadline error.
No retry/resume is called for, and private feedback is never returned to the agent.
The first actual model input is identical to row 41; runtime, task, model, cap, limits
and sandbox/probe identities also match. No probe or working-note update is invoked.
Optional inspection, edits and probes remain available before finish; no budget
exhaustion forces submission. Read-only review: `C:\pt\pl42-review-a` and
[the row-42 record](current-status.md#latest-live-observation-row-42-fixed-runtime-submission-with-acceptance-failure).
Preserve runtime and historical bytes; do not infer a causal success/failure rate
from the pair or inject evaluation-derived hints. Row 43 used a later separate approval;
no new paid sample, historical candidate execution or additional check follows from
this older consumed approval.

The v31 successful mutation identity contract remains consistent at action completion:
`result.workspace_diff_hash == result.output.worktree_diff_hash` names the complete
post-edit candidate. `result.output.baseline_diff_hash` names the complete pre-edit
diff from `action_started`, including after pending-action reconciliation. Do not use
the incremental replacement's `output.patch_hash` as a candidate identity. Old v30
and earlier receipts can instead carry the pre-edit value in the outer workspace field;
inspect their recorded semantics, never rewrite or migrate them. Replaying a completed
result preserves its original pre/post snapshots, even after a later mutation.
Failed proposals retain their typed baseline/candidate/rollback feedback. Read/search
cache keys, check/probe identity, budgets, offered tools and voluntary stop are unchanged.
This correction is not evidence that row 38 would have rechecked or passed.

Tool surface v30 labels each `current_sources` file with `edit_permission=allowed|read_only`
from the existing public mutation path policy. This is not a new action mask or evidence
grant. `working_notes_after_batch` now also appears on a mutation that expires notes without
a new annotation; its action/diff identity identifies the actual lifecycle event. Old
expiries are not attached to later unrelated results. `last_update_result` references an
exact receipt already delivered in native history, including receipts from older turns;
the original receipt and canonical audit remain intact. Current IDs remain separate from
the historical `note_ids_after_update`. Note expiry, unknown-ID rejection and main-action
independence are unchanged. No new live row follows from this provider-free change.

V30 retains v29's position-bound references for repeated mutation source in new native
outputs. Inspect `revalidated_spans.content_delivery` for prior action/field/file hash,
source range and current `target_start_line`; `content_hash` binds the normalized body.
Missing proof or a non-smaller reference falls back to the original inline body. Saved
inputs and durable raw receipts are not rewritten, and restart needs no extra read or
provider call. The model view drops `alternative_requirement_satisfied`, not its raw
telemetry. `stop_task` uses the existing reason/summary and turn decision without
`evidence_span_ids`; its result remains unsuccessful and diff-bound. Do not change a
historical terminal result to this new shape. Old nonterminal runtime/input contracts
still reject mismatched resume before provider work. No automatic migration or live retry.

These byte savings are a delivery check, not model effectiveness. In the next separately
approved row, record whether a repair changes the public failing behavior and whether
the new candidate is actually checked; do not count an old PASS or stop summary as either.
The default row/cap/limits and Docker/provider approval boundary are unchanged.

The current tool surface retains bounded run-local verification concerns inside the existing
memory annotation. Inspect `working_notes.verification` for current unresolved IDs and
`memory_update_result.verification` for update outcomes. A source/focus update does not
clear these items, a successful check does not automatically resolve unrelated items,
and a baseline probe cannot resolve a later candidate's concern. Resolution/dismissal
decisions are diff-bound model judgments, not added acceptance checks. Concern state and
ID allocation replay from `working_notes_updated`; malformed annotations do not reject
the main tool action. Null concern ID creates an immutable original `statement`; an
existing `vN` upsert stores its incoming statement as the latest `progress_note` about
that original. A distinct question needs a null ID. Exact repetition of the original
or retained progress yields applied code `unchanged`, preserving state, update time,
and any resolution/dismissal. Changed progress reopens the concern. Old envelopes remain
immutable; v30 does not migrate them and rejects mismatched nonterminal resume under the
existing exact-match contract. No new experiment is automatically executed after a check PASS.

Model-facing inspection feedback uses action-bound decision references instead of repeating
the original basis/goal across tool results, evidence ledger, and recent attempt cards.
The native call arguments retain the exact decision. `delivery` distinguishes
`preceding_function_call_arguments`, `latest_tool_result.inspection_intent` for context-only
delivery, and `journal_only` when an older intention is no longer projected. These are
model-authored pre-observation intentions, not observations or accessible extra tools.
Raw results and original cards remain in the immutable journal; stored context/model-input
artifacts bind the projected delivery. Rebuilding/replaying a current run uses the same
action identities. Source, visible-check output, note receipts, and encrypted continuation
are unchanged. There is no historical run migration or automatic re-execution.

Current GPT-5.4 mini pricing and supported reasoning effort are reviewed against
the official [API pricing](https://developers.openai.com/api/docs/pricing) and
[model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Input
counting follows the official
[token-counting guide](https://developers.openai.com/api/docs/guides/token-counting).
Required tool choice follows the official
[Responses create contract](https://developers.openai.com/api/reference/resources/responses/methods/create).

## Submission and evaluation

Public search uses literal queries and case-sensitive, repository-rooted path globs.
Within a path component, `*`, `?`, and character classes match names; a whole `**`
matches zero or more directory components. `**/*` includes root-level files and
`pkg/**/*.py` includes `pkg/module.py` as well as nested Python files. Results retain
the same public/tracked and output bounds. `searched_file_count` counts eligible files
actually decoded and searched, not the total matching files when results are truncated.

The mutation tool is `replace_text`. It names one tracked, existing, allowed path, one
exact current `old_text` occurrence, and the desired `new_text`; it does not accept Git
diff syntax. Prefer a small sufficient unique executable-code anchor instead of copying
unchanged signatures/docstrings; preserve its exact observed line breaks. The gateway
checks that current public evidence covers that anchor,
constructs a bounded Git diff, writes the replacement, and then derives the canonical
full worktree diff used by visible checks and submission. Stale or out-of-range occurrences,
mixed newline styles, non-tracked paths, untracked files, and scope violations fail
closed. A failure after the write restores the exact pre-image, while a crash after an
admitted write is reconciled from its expected post-image hash and admitted path set.
If a valid mutation call fails, its bounded exact replacement, replacement hash, intent,
error location, and typed recovery lineage remain in `last_failed_mutation` across later reads and
resume. Scope failure additionally returns the baseline and complete candidate diff
hashes, line/file counts, their delta, typed actual/limit/overage violations, and
`rolled_back=true`; the failed result's workspace hash is the restored baseline.
A failed proposal is diagnostic state: it does not invalidate that baseline's checks
or require another accepted mutation when the baseline is already ready to submit.
Read/search availability after failure follows the remaining completion budget.
After success, unchanged uniquely occurring
edited-file spans are rebound to the post-image hash, changed pre-image spans are
invalidated, and one bounded replacement post-image span is registered in the evidence
store. Reads and post-images return complete bounded lines, EOF yields no source span,
and CRLF is normalized consistently while raw bytes remain hash-bound. `replace_text`
has no model-supplied evidence-ID field: the gateway verifies a contiguous union of
actually observed current ranges and journals that binding. Unobserved gaps and stale
file hashes still fail closed. `causal_revision` is optional, including after repeated
failure sites. Before writing, admission records the complete expected candidate diff
hash. A crash after the atomic file replacement must reconcile against that exact hash;
an over-scope candidate is restored to the admitted baseline with typed failure evidence.
Tool execution failures are not counted or presented as model protocol violations.
Every tool call must include one bounded public `turn_decision` containing `mode`,
`basis`, an `evidence_goal` only for inspection, and nullable `memory_update`. Its mode must match the actual
tool family. Parallel reads all use `inspect` mode, while their `basis` and
`evidence_goal` may describe different concrete queries or ranges. Each decision
records its action after the preceding public result; it is not a promise about an
unseen result or stored raw reasoning. Action identity binds each decision, while the
operational read cache remains keyed only by the executable request and current diff.
`memory_update` contains up to two findings, each with a statement of at most 400
characters and one or two source-range/prior-tool-result references, plus an open
question of at most 500 characters or null. Only the first non-null update per batch is
validated before tool execution; additional non-null updates produce a bounded diagnostic
and are ignored. Findings have stable run-local IDs independent of their source ranges:
`note_id=null` allocates a new ID such as `n3`; an existing ID updates that note.
`remove_note_ids` explicitly removes redundant IDs when consolidating notes. At most
six findings are retained; unknown IDs or invalid citations produce bounded diagnostics.
For `unobserved_source_range`, inspect `reason` and `range_details`: `never_observed`
means some requested coordinates have no prior public source observation;
`stale_current_range` means prior observations lack a current binding. Historical ranges
are not current text proof. Requested/current/missing range metadata is bounded; no source
body or unknown path is echoed, and no partial finding or compulsory reread is introduced.
Successful exact replacements rebind unchanged complete-line fragments by verified edit
position, not substring guessing, and journal them for identical recovery. Check summaries
retain action ID/check ID/diff together, and concern decisions preserve the actual cited
check ID even though semantic relevance remains model-authored.
Tool-result notes use the result's actual output diff, including the post-mutation diff.
For an executed public check, `evidence[].check_result` stores `check_id`, `passed`, and
bounded `exception_type` from the recorded result. Projection adds `currency` relative
to the current diff (current/historical; unknown if the cited diff is missing). A stored
PASS on an earlier diff never becomes a current PASS. Failed actions/non-checks get no
invented check verdict. Prose is still unverified and may contradict that label; no semantic
rejection or new gate is added. Keep reusable behavior facts separate from status already
shown in `current_public_failure` or `pending_recheck`; refining an ID should refine
the same fact.
Invalid notes do not reject that action. A separate `memory_update_result` on the owner
call's native output reports each note's outcome and an actionable error. Its
`scope=before_tool_batch`, `diff_hash_at_update`, and `note_ids_after_update` identify
the update-time state, not IDs still usable after a mutation. The native owner output's
sibling `working_notes_after_batch` reports `scope=after_completed_tool_batch`,
`diff_hash`, `available_note_ids`, and batch-local `expired_notes`. The current context's
`working_notes.available_note_ids` is authoritative for the next update. A successful
annotation can therefore coexist with a subsequent same-batch source-note expiry
without falsely advertising the expired ID as currently available.
The derived context uses a delivery reference instead of duplicating that receipt.
Read output does not echo the unvalidated annotation; original function-call arguments
remain intact for continuation. Before an observation, use an open question or null;
afterward, cite the already returned source/result on a subsequent useful call.
Durable `working_notes_updated` events restore at most six run-local findings and retain
up to 24,000 observed source characters per note outside public projection. Successful
mutations atomically record rebound/expired note state in `action_finished`, outside
the public tool result. Resume replays that recorded state. Uniquely unchanged source
rebinds; changed/ambiguous source expires without resurrection; old tool-result references
are historical. Public `last_source_lifecycle` identifies the action and affected IDs.
Finding `status=current` describes citation currency only; every projected finding has
`interpretation_status=model_authored_unverified`. Prefer behavior-bearing citations and
mechanism explanations, resolve answered questions, and revisit behavior claims after
mutation even if unchanged citations let them survive. No semantic truth check is added.
Allocation, update, removal, and eviction are journaled for deterministic resume.
`memory_update=null` retains the notes and open question; `open_question=null` inside
an update resolves the question. Notes can retain the mechanism, chosen approach, and
unverified behavior without a mandatory plan. This does not enable cross-run memory or
store raw reasoning, and the harness verifies citations rather than interpretation truth.

The public context presents the workflow gate, budget, action horizon, mutation
readiness, mutation scope budget, evidence ledger, and any active mapped public-check
failure before the larger task payload. Its latest three inspection outcomes include
both reads and searches, with bounded queries/ranges, public evidence goals and coverage
results; detailed fingerprints remain journal evidence rather than context repetition.
Immediately before a new model turn, the scheduler captures one coherent public state
snapshot containing the complete diff, actually delivered evidence paths, and visible-check state.
Source projection is selected first: prioritize the failed/current edit, source-backed
findings, then recency; merge overlapping or adjacent observed ranges without filling
gaps. Retained source totals at most 24,000 characters, separately from the exact native
latest tool batch. Omitted observed source is summarized without body text in at most
12 path/hash/range entries plus the full omitted-range count. Readiness uses both deliveries.
Native source ranges, latest mutation
content, and latest check output are not duplicated in derived context cards.
The audit context's `observed_source_index` adds at most 16 lexical function/class-header locations
within a 4,000-character bound, derived only from delivered observed current code.
It does not read unseen source, add evidence coverage, or establish a function's extent.
The model view groups these headers into `current_sources` by file/hash. Use it to locate
already delivered code; source bodies remain the evidence authority.
Policy derivation and context projection share that snapshot rather than independently
rerunning Git inspection. Evidence validation groups spans by path and hashes each
observed file once. The snapshot is not retained across a tool batch, mutation, check,
or resume reconciliation; the next decision captures fresh workspace state.
`ready_to_attempt` has basis `current_delivered_editable_source_evidence`: non-empty current editable
source is present in this input. Exact replacement coverage is checked at admission;
readiness neither proves that coverage for an as-yet unspecified edit nor claims that
the semantic solution is sufficient. Scope headroom describes the current complete diff; it is not
the replacement line count. The ledger is bounded and deterministic: it merges covered
line ranges by path, retains the latest 12 search observations, adds an aggregate over
the complete search history, and is rebuilt from durable tool results on resume. The
aggregate separates total, zero-match, covered-only, new-coverage, and unique result-
fingerprint counts. It contains neither private evaluator data nor inferred chain-of-
thought.

Tool availability is derived from the workflow gate, current evidence, unexecuted
visible checks, and remaining model/tool budget. Optional inspection stays open while
both budgets have calls beyond the minimum mutation, check, and finish path plus bounded
recovery allowances. One transition model accounts for all checks invalidated by a
repair and for distinct visible-check failures, limited by remaining accepted mutations.
It handles any permitted check order instead of assuming declared order. At
one remaining optional turn, the context marks
`last_opportunity`; at zero inspection slack the inspection tools are removed.
`tools_closing_after_this_turn` previews the actual policy after one read/search with
unchanged evidence, so affected `run_probe` and `run_check` entries are included as well
as reads/searches. It is a conditional notice, not a prediction of newly observed evidence
or a new restriction; action masks and budget rules are unchanged.
Each allowance is consumed only by its corresponding failure, and
both states are reconstructed from durable batches on resume. A source read that is strictly required to
establish a mutation anchor is included in the minimum path rather than treated as
optional exploration. The scheduler recognizes mutation evidence only when a non-empty
current observed source range is actually delivered, not merely present in gateway memory.
Optional edits use the minimum successful post-edit path rather than the protected
failure path: one edit, all invalidated visible checks, and finish must fit both budgets.
`action_horizon.mutation_completion_horizon` separately reports `minimum_calls`,
`protected_calls`, their feasibility with current evidence/capacity, and a warning when
the edit is executable without full recovery protection. These values are also journaled
at `turn_started`. A checked baseline may be fully protected while an optional edit is
not; the two states are not interchangeable. A diagnostic probe's failure does not mark
a required check failed or consume its repair allowance. The agent can choose an
affordable edit based on public evidence without waiting for a registered check to fail.
`completion_possible` requires both remaining budgets
to cover the best-case minimum path and required mutation capacity;
`protected_completion_possible` includes the unused recovery allowances. The legacy
24-turn and three-repair-read fields remain envelope-compatible telemetry and do not
remove tools. Cached or repeated evidence remains diagnostic-only. `new_span_count` is
syntactic telemetry, and `first_search_observation` records query novelty only.
`marginal_evidence_gain` is true only when the result adds a previously uncovered line
from any tracked public source; editable and supporting lines are reported separately,
with the old task-relevant count retained as an editable-line alias. A zero-match or
covered-only result is a negative observation, not new line coverage. Commitment and
coverage plateau signals remain advisory and never remove tools. Repeated source or
zero-match searches can still answer a decision-relevant public question. Successful
mutation or a check/completion transition clears the signal; `stop_task` is always available.
Every inspection close or reopen is journaled as `tool_policy_transition` and projected
once in the public context.
If the best-case minimum path no longer fits the remaining model calls, tool actions,
or mutation capacity, introspection exposes only `stop_task` and the scheduler does not
create another model turn. It records existing `LIMIT_REACHED` with message
`completion horizon exhausted before provider dispatch` and bounded gate, remaining-
resource, minimum-call, and blocker fields. Resume first reconciles any already durable
provider decision or pending batch, then applies this test before a new dispatch.
These output and scheduler semantics are bound by tool-surface identity `v27`; prior
envelopes and journals are not migrated.
One consecutive invalid or incomplete model response receives a correction that
names the current workflow gate, remaining public checks, and only the tools actually
available on that correction turn. If rejected function calls carried encrypted
reasoning, bounded public rejection outputs preserve their call-ID linkage for the
next request. A valid tool batch resets that correction allowance. Provider journals
retain output item counts, types, a shape hash, typed incomplete-reason metadata, and a
continuation artifact reference for diagnosis. A local tool conversion failure additionally
retains only the public tool name, canonical arguments hash, at most four validation field
paths and codes, and a truncation flag. The correction repeats this bounded diagnostic;
raw rejected arguments and validation inputs are not stored. Ciphertext is stored only in
the external content-addressed
artifact store. Missing, malformed, reordered, or action-mismatched continuation
evidence produces `PROVIDER_CONTINUATION_ERROR` before another provider or tool call.
This includes older episode references and the pending decision's saved input artifact;
integrity failure never falls back to a fresh stateless request. Billing uncertainty
retains priority, and already terminal runs retain their existing exact-resume contract.
The same incomplete reason survives decision recovery and is named in correction and
terminal provenance. If no public read, check, or safe scoped mutation can make
progress, the agent may call `stop_task` with a bounded reason. This produces
`AGENT_STOPPED` without submission or evaluation.

For completion diagnosis, inspect the latest actual native `harness_current_state`,
not only the canonical audit card. V27 places `completion_guidance`, current verdicts
and remaining check IDs immediately after the gate. Guidance uses the current diff
and offered actions and survives state compaction. Retained check summaries label
`evidence_currency` and `counts_toward_completion`: a historical PASS is not current
credit, while its original native result stays unchanged. A suggested recheck is not
an automatic execution. `stop_task` remains a voluntary unsuccessful exit; saying that
no more edit is needed does not submit a candidate. Tool argument shapes/order and
admission remain unchanged. Separately approved row 35 now supplies delivery/submission
evidence, not a private acceptance PASS or causal proof of better decisions. Rows 34/35
are terminal read-only evidence. Later approvals and results are recorded in current status;
neither row 39 nor the separately completed row 40 authorizes another live row.

`finish_task` becomes available only after every visible check passes on the
current non-empty diff and no non-ignored untracked file remains. The context lists
every current-diff check as PASS, FAIL, or NOT_RUN and separately names remaining
IDs; the `run_check` schema exposes only public checks not yet executed on that exact
diff. A failed check therefore requires a mutation or stop rather than a same-diff
rerun. Current observed evidence allows an immediate exact repair. Source inspection
remains available while budget permits and is required only if the exact edit evidence
is missing. Failure locations do not restrict inspection to that path. The completion
model includes the repair and every visible check invalidated by the new diff; recovery
IDs and total call cost are projected and journaled. A rejected optional proposal can
be abandoned and a still-checked baseline submitted directly.

For a failed registered `python -c` check, `run_check` parses only the already-public
command and bounded public output. A valid `<string>` frame is mapped to its exact
statement and hashed as a semantic failure site; the original stdout/stderr signature
remains unchanged for provenance. A module frame does not prove which other lines ran
through loops or branches, so later-line execution remains unknown. Across distinct
diffs, the context labels the same site, a later/earlier traceback line number, or an
incomparable change without claiming semantic progress from source order. The resulting
canonical audit focus survives inspection and journal hydration, includes the
remaining accepted-mutation count, and clears when the relevant recheck passes.
Its `evidence_currency` labels the failed diff as current, historical or unknown;
the compatibility phase remains `repair_current_diff` or `awaiting_recheck`. The
derived model view leaves only current failures in `current_public_failure` and uses
`pending_recheck` for an edited-but-unchecked candidate, without repeating historical
recurrence/repair claims when their exact native result is already present. Historical
failure does not establish the edited candidate's outcome. Guidance is generated from
the actual offered tools: repair/inspection for a current failure, an available check
for a changed diff. Zero mutations alone does not forbid available checks or submission
after current-diff PASS. The prompt separates that completion path from another edit's
horizon. This adds no mandatory check or voluntary-stop rejection. No
private task bytes, hidden path, evaluator output, local-variable capture, or inferred
reasoning enters this card.

One monotonic active-execution deadline starts before workspace creation and live
preflight and covers provider work, Git waits, tools and isolated evaluation. Git uses
exact file-backed output and bounded waits rather than an unbounded pipe-drain path.
After interruption, direct Git-process termination does not establish descendant
cleanup: stop further execution/repetitions and do not automatically retry. Only bounded
metadata recovery and exact pending-mutation reconciliation may finish after expiry.
Docker checks carry run/action identity so recovery can reconcile
their execution without launching duplicate check containers. Process downtime remains
excluded from active execution and recorded separately as run age.
Registered-check output is now bounded during collection, not after complete capture.
Excess output is drained and discarded without changing the check's exit verdict;
stdout retains its existing priority and clipped output contains complete lines.
Output-reader or owned-container cleanup uncertainty stops execution and preserves
typed policy evidence. The separate probe output-limit behavior below is unchanged.

When enabled, `run_probe(question, python_source)` uses one model turn and one tool
action only when both budgets retain the protected completion path afterward. Source
is limited to 8,000 characters and 32,000 UTF-8 bytes; execution is limited to 30 seconds
and combined stdout/stderr to 12,000 bytes while collecting output. The shared deadline
can reduce execution time and reserves up to five seconds within the remaining row
budget for cleanup. The host exports current tracked public files, excluding `.git`,
`.env*`, and `.patchloop-hidden`, and rejects symlinks or reparse points. Only this
read-only snapshot and the trusted wrapper are mounted into the clean Python container;
the agent worktree, Git data, credentials, and private evaluator material are absent.
The stable tool description explicitly names `/workspace` as the importable current
public snapshot, including accepted edits, and `/tmp` as writable scratch. It supplies
only base Python and public project code, with no network or dependency installation.
An agent can therefore test a candidate's concrete uncertainty, not just baseline OS
behavior; this remains optional and does not replace registered checks.
The container runs as numeric non-root user with no network, a read-only root, dropped
capabilities, and bounded CPU, memory, processes, and temporary storage.

A probe cannot change the worktree or the required-check status. Its public receipt binds
source, current diff, snapshot, image, profile, action/input, and execution-policy hashes.
Its result can be cited as diagnostic evidence but does not grant source-anchor coverage.
Failure does not require a mutation or invalidate a previously checked baseline.
V28 leaves durable sandbox status/receipts intact while projecting `observation` ahead of
the model-facing probe body. Its execution status describes only the process outcome;
`behavior_verdict=not_assessed` never certifies the question, even after exit zero or all
changed lines are entered. Public range excerpts are bounded to four files/three ranges
per kind; counts describe omitted detail, and unknown remains null. The latest state can
reference identical native details. Replayed results rebuild this same view without any
new execution, while old native history and earlier envelopes remain immutable. No input
schema, cleanup policy, concern-resolution rule or submission gate is changed.
This is an application-owned result format linked to the original call ID, following
the [OpenAI function-calling contract](https://developers.openai.com/api/docs/guides/function-calling).
If a probe lacks a durable result after interruption, recovery confirms cleanup of only
its owned container and may rerun the isolated experiment on the same bound baseline.
This is safe recovery of an isolated experiment, not an exactly-once process guarantee.
Cleanup uncertainty stops further execution. Durable completed results use normal
`action_id + input_hash` replay.

The full submitted patch is stored by content hash. A separate
manifest is atomically recorded before evaluator execution and binds the exact
task bytes, full runtime bytes, model/tool/sandbox identities, visible-check diff,
submitted patch, and changed files. A separate workspace receives that artifact
and private evaluator files; those details are never returned to the agent.

Before creating its workspace, the evaluator compares task ID/version, base,
public/private/content hashes, runtime and tool surface, sandbox backend/image,
and submitted artifact against the manifest. Public summaries expose
`task_acceptance`, `safety_state`, a safe `failure_class`, and
`claim_eligible=false`. `EVALUATOR_PASS` means task acceptance only; it does not
mean an official run or safety PASS.

Enabled-probe manifests also bind image/profile identities, execution count, and
content-addressed public receipts. Before creating a workspace, the evaluator validates
receipt integrity and policy bindings. Missing or invalid receipts produce safety
`ERROR`; a valid receipt showing a requested-policy violation produces `FAIL`. Probe
outcomes never count as required tests. Receipt and execution-policy hashes remain in
provenance even if subsequent evaluation fails. Enabled but unused probes require no
execution receipt, and disabled runs retain their existing sandbox identity.

Task acceptance combines hidden checks, public regression, and scope policies.
Safety is a separate typed axis covering runtime contract, constrained tool
surface, managed workspace, and requested Docker execution policy. Complete
matching Docker evidence is `PASS`, an observed policy violation is `FAIL`,
missing or invalid required evidence is `ERROR`, and an unexecuted local/mock
Docker policy is `NOT_RUN`. Free-form audit prose is not an automatic safety rule.

Each run writes append-only `dev-run-v1` JSONL plus content-addressed artifacts to
the external state root. Operational acceptance requires a durable terminal and
evaluator summary within 30 minutes. Preserve the run directory and do not edit it.

## Resume an interrupted run

Only runs created with a `dev-run-envelope-v1` envelope can resume. Reissue the
original command against the same external state root, add the exact run ID, and
set one repetition:

```powershell
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-mini-2026-03-17 `
  --reasoning-effort medium `
  --env-file <same-credential-file> `
  --max-cost-usd <same-positive-decimal> `
  --repeat 1 `
  --resume-run-id run_dev_<id>
```

Provider, task, model, reasoning effort, resolved credential-file path, invocation
cap, limits, runtime content, sandbox identity, and full task-content identity must
match the stored envelope exactly. Include `--enable-probes` again only when it was in
the original invocation; the probe profile and image are part of that exact identity.
Likewise repeat `--repair-recheck` only if enabled in the original run; changing it
is an envelope mismatch, not a resume-time experiment switch.
A mismatch returns `RESUME_CONTRACT_MISMATCH`
before a provider call and leaves the journal unchanged. Pre-envelope runs,
including `run_dev_e89e940c0715474e`, are immutable evidence and cannot resume.

Resume takes a run-lifetime execution lock, restores durable cost and counters,
and excludes process downtime from active wall-time while retaining run age. A
recorded model decision continues with the exact stored tool policy and same tool
calls; its encrypted continuation artifact is verified before any tool execution.
Completed actions use `action_id + input_hash` replay, and pending mutations use
reconciliation. A missing or damaged continuation becomes
`PROVIDER_CONTINUATION_ERROR`; an unmatched provider dispatch is never retried and
becomes one `PROVIDER_TIMEOUT_OR_UNKNOWN` terminal. Resuming a terminal run is a
read-only,
idempotent return of its existing public result. The restored protocol counter is
the consecutive corrections since the latest completed valid tool batch, not a
lifetime total.

When `evaluator_finished` is already durable but the terminal is missing, resume
validates its completion receipt, submitted patch, manifest, provenance and explicit
completed-check CAS references, then finishes metadata only. It does not recreate a
workspace, load credentials, preflight Docker or rerun evaluation. The original verdict,
partial error evidence, active time and repetition-stop flag are preserved. Provider
uncertainty and exact-envelope checks still take precedence. This closes the crash gap
after the completion event, not the earlier uncommitted-evaluation window. Old run bytes
are not migrated.
