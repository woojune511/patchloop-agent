# Implementation evidence — through 2026-07-31

This is a local implementation checkpoint, not the planned core experiment result.

## D-060 three-task no-memory budget pilot — live diagnostic complete

The checked-in
[`dev-no-memory-budget-pilot-20260731-r1.yaml`](../experiments/dev-no-memory-budget-pilot-20260731-r1.yaml)
uses a distinct `memory-development-no-memory-budget-pilot` purpose. It selects Hugging Face Hub,
PDM and pyfakefs from the immutable V4 budget-terminal population: pyfakefs recorded the maximum
total-token and wall-clock usage, PDM the maximum model calls, and Hugging Face Hub the maximum
tool calls. Each frozen memory-development task is scheduled once under `no_memory`; the dataset
manifest remains unchanged.

The suite freezes `gpt-5.4-mini-2026-03-17`, medium/standard/default, tool v2/context v5, 25,000
per-call output, and `40 model / 100 tool / 480,000 total token / 1,800 seconds`. At the official
standard rates rechecked on 2026-07-31, the conservative authorization reserve is `$2.2725` per
run and `$6.8175` for three runs under a `$7` cap. This is a reservation bound, not predicted
spend or evidence about free-tier billing.

The new `no-memory-budget-pilot-gate-v1` requires all three rows to be terminal, trace-qualified
and evaluated by the official evaluator with zero infrastructure, qualification, diagnostic or
budget-terminal error. Task success is reported separately. The purpose cannot create a memory
candidate, enter the comparison denominator or automatically unlock memory admission.

D-060 was later executed exactly once under approved execution hash
`sha256:61a7208bd6ee1a45b08511407d0c8c0658976685245a11d422077efdf9bdef4f`.
All three rows terminated and passed trace qualification without infrastructure or qualification
errors, but SCRR was 0/3. HF Hub stopped before evaluation on total-token admission; PDM and
pyfakefs reached the official evaluator and failed hidden acceptance. The suite, hash and run IDs
are immutable and must not be rerun.

The pre-live offline verification collected 731 tests and completed 724 passes with seven environment skips.
Five skips are the current execution context's unavailable Docker daemon and two are unavailable
Windows symlink creation. The new experiment tests pass the exact suite, cost reserve, approval
gate and result-gate cases; the qualification tests pass all three tasks, task/agent-failure memory
exclusion and missing-task plan tamper rejection. Repository-wide Ruff and `git diff --check`
passed, and dataset audit remains frozen at 25 packages with zero candidates. The five Docker
tests were then rerun against host Docker Desktop 4.83.0 / Engine 29.6.2 and passed 5/5, covering
the profile-bearing agent probe/review lifecycle, network denial, non-root/read-only execution,
host-secret/proxy isolation and runtime process-spawn/trusted-parent-signal denial. Current image
`sha256:1144b4be9927ac5882401185c326003383630eac9db84102ee3d71c06e261cac`
was created by exact ID and its actual `.Image` was verified before start. The kernel test entered
an audit-hook-free subinterpreter and observed `EPERM` for both process spawn and a harmless signal
0 check against the trusted parent. No managed probe container remained afterward.

## D-055 high-budget no-memory completion panel — live-complete

Cross-run memory admission is deferred because the V4 0/12 result contains nine pre-evaluator
exact-request budget failures and is not a usable no-memory baseline. The read-only structured
review proposal below remains historical candidate/hold evidence; no human review history or
memory index was created.

The consumed suite is
[`dev-validation-gpt54mini-completion-v6-pilot-r1.yaml`](../experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml).
It freezes the two admitted development-validation tasks—Babel as the previously completed control
and Moto as the harder state-accounting probe—at one `no_memory` repetition each. The model remains
`gpt-5.4-mini-2026-03-17`, medium/standard/default with 25,000 per-call output. The diagnostic
ceiling is 40 model calls, 100 tool calls, 600,000 total run tokens and 1,800 seconds.

Official OpenAI documentation was rechecked at 2026-07-30T22:25:47Z. The model page publishes a
400,000-token context window, 272,000 max input and 128,000 max output; the configured 25,000
per-call output is within that limit. Standard list prices remain input `$0.75/M`, cached input
`$0.075/M`, output `$4.50/M`. PatchLoop's conservative formula therefore reserves `$2.8125` per
run and `$5.625` for the panel under a `$6` suite cap. The user approved execution hash
`sha256:444cd7f2d00b3925a1227d1e9fc0436c68ba9700005b8416572c5fd654de1f78`,
bound to commit `59621ec`, the two Docker image digests and OpenAI SDK 2.47.0. The runner consumed
that authorization exactly once.

`no-memory-completion-gate-v1` separates runtime completion from task correctness. It requires
2/2 terminal rows, qualified traces and official evaluator arrival with zero infrastructure,
qualification, diagnostic or budget-terminal failures. Hidden/SCRR success is reported but is not required:
a hidden task failure after the evaluator ran is still completion evidence. A separate 20%
headroom check uses 480,000 token, 32 model calls, 80 tool calls and 1,440 seconds per run.

| Task | Run | Usage | Cost | Outcome |
| --- | --- | ---: | ---: | --- |
| Babel #1042 | `run_685c492e34f84fef` | 65,652 input + 3,304 output; 8 model / 9 tool; 47,040 ms | `$0.064107` | official hidden/regression/scope/safety pass; qualification 25/25 |
| Moto #7208 | `run_0814be408332479e` | 106,597 input + 2,838 output; 11 model / 14 tool; 95,593 ms | `$0.09271875` | official hidden/regression/scope/safety pass; qualification 25/25 |

The completion and panel-headroom gates passed 2/2. Infrastructure, qualification, diagnostic and
budget-terminal counts are all zero; both tasks also happened to pass SCRR. Across 19 generation
events, exact input and total token counts matched provider usage 19/19. Every response completed
with truncation disabled, `store=false`, no `previous_response_id`, no incomplete reason and no
cached input. Each run has one prepared patch, one applied mutation and one accepted submission;
there is no duplicate mutation evidence.

Actual calculated list-price cost is `$0.15682575`. The immutable experiment result hash is
`sha256:a540ff52f271cd22c58ca561e559d9608ac50b99889a523f8a9a3d80cf8822ba`;
the hash-chained `CampaignCompleted` event records the same hash. The experiment ID and approval
hash are now preflight-immutable.

The portable
[completion report](../reports/live-pilot/dev-validation-gpt54mini-completion-v6-20260731-r1.json),
[Babel submitted diff](../reports/live-pilot/artifacts/run_685c492e34f84fef-submitted.patch) and
[Moto submitted diff](../reports/live-pilot/artifacts/run_0814be408332479e-submitted.patch)
preserve the public claims boundary. The raw plan, journal, result and qualification bytes remain
hash-bound local `.patchloop` artifacts; a clean checkout cannot independently rehash those full
raw traces.

The unexecuted 250k single pilot
`dev-validation-gpt54mini-token-tail-v5-20260730-r1` is preserved as
`superseded-unexecuted`; preflight rejects it with `SUPERSEDED_SUITE`. The memory-development and
core 250k templates remain pending drafts and are not authorized. The successful n=2 panel proves
that this runtime can complete these two development-validation tasks under the 600k ceiling. It
does not estimate six-task baseline SCRR, failure distribution, memory benefit or a core budget.
Both traces had zero token-tail admission blocks and zero semantic replay. A 480k token / 40 model /
100 tool / 1,800 second, three-task memory-development pilot is only a provisional next candidate.
Its exact tasks are frozen from the immutable V4 campaign by resource maxima: pyfakefs for observed
total-token and wall-clock maxima, PDM for model-call maximum, and Hugging Face Hub for tool-call
maximum among budget-terminal tasks, with task ID ascending as the tie-break. It requires a new
suite, execution hash, cost review and explicit approval.

Pre-run commit `59621ec` partitioned every test file into four isolated groups and collected
658 tests: 655 passed and 3 existing environment/evidence-dependent tests skipped. The post-run
immutable closure then passed 218 tests across experiment, trace-qualification and portable
live-evidence coverage; repository-wide Ruff and `git diff --check` passed.

## Structured memory review proposal — human admission still pending

The V4 no-memory campaign's three task-failure sources were reviewed using public task contracts,
agent-visible event/source artifacts, submitted diffs, registered-check summaries and only the
generic task-failure outcome. The resulting maintainer-assisted proposal is
[`dev-no-memory-v4-structured-review-proposal.json`](../reports/memory-development/dev-no-memory-v4-structured-review-proposal.json),
content hash
`sha256:6ed23cc6056b910c1a781d77bf0d8fa297ec3f948cc54cfaf176539e83f8d7e7`.
It does not claim that the PatchLoop agent performed automatic post-run self-review.

`patchloop memory validate-review` recomputed the frozen dataset identity, campaign
report/execution/suite hashes, all three current failure/qualification/source-evidence/public-spec
bindings, the three portable submitted-patch hashes and referenced event sequences. It also
verified exact coverage of the three task-failure candidates and nine budget-confounded exclusions,
semantic-group membership, the canonical proposal hash and the leak/code-marker policy.

The outcome is deliberately asymmetric:

- The two tox repetitions are one `exception-origin-state-conflation` candidate rule. Their public
  evidence supports the same operation-boundary mistake and corrective action.
- The Loguru source is a separate `diagnostic-contract-unresolved` hold group. Public evidence did
  not isolate a defensible causal explanation, so the proposal does not turn it into a generic
  memory rule merely to reach a target count.
- The nine exact-request budget failures remain excluded from semantic memory review.

Validation reported three sources, two groups, one candidate, one hold, nine exclusions and a
passing leak scan. It also reported `human_review_status=pending`,
`review_history_written=false` and `memory_index_built=false`. No provider call was made.

Pre-run regression evidence contains 658 collected tests: 655 passed and 3 existing
environment/evidence-dependent tests skipped across the four isolated groups. Post-run closure
validation is reported in the D-055 section above.
The remaining memory gate was append-only human approval bound to proposal/rule/group provenance,
a group-aware builder and an exact embedding revision. D-054 now defers that work until the
completion panel and a new no-memory baseline establish an unconfounded source set.

## D-052 comparison draft — offline evidence only, pilot superseded by D-054

D-052 supersedes the future budget/runtime portion of D-045, D-048's current-runtime designation
and D-051's pending token-tail gate without changing historical evidence. Before D-054,
development-validation, memory-development and core draft suites used
`gpt-5.4-mini-2026-03-17`, medium/standard/default, `phase-evidence-v5`,
`21 model call / 50 tool call / 250,000 total token / 900 seconds` and
`max_output_tokens=25,000` for every memory condition.

The token projection uses durable `ModelCalled` telemetry. It prefers
`requested_input_tokens`, falls back to actual `input_tokens` only when requested is `None`, and
fails closed on invalid values. The contract is:

```text
projected_next_input =
  max(observed_input_tokens)
  + max(0, maximum_positive_consecutive_growth)

projected_turns = 5 before generation, 4 after generation
reserved_tokens = max_output_tokens + projected_next_input × projected_turns
cutoff = remaining_tokens <= reserved_tokens
```

At cutoff, only valid read/search actions are closed before `ToolCalled` and filesystem dispatch
with reason `token_tail_reserved`. Apply/check/diff/finish remain available. This is a nominal
corrective-tail policy, not a completion guarantee. The strict exact-request + full 25,000
response admission guard remains and can still terminate without a provider call.

The new evidence versions are `investigation-policy-v2`, `investigation-ledger-v2`,
`investigation-tail-policy-v2`, `context-build-evidence-v5`,
`tool-admission-blocked-v2` and `trace-source-evidence-v5`; the qualification envelope remains
`trace-qualification-v2`. Final offline verification on 2026-07-30 collected 635 non-live tests:
632 passed and 3 existing environment/evidence-dependent tests skipped. Repository-wide
`ruff check .` and `git diff --check` also passed. No provider call was made for D-052, so this is
not accepted-pilot, usable baseline, memory-effect or core evidence.

The D-052 comparison drafts were:

- `experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml`,
  experiment `dev-validation-gpt54mini-token-tail-v5-20260730-r1`; now
  `superseded-unexecuted`
- `experiments/dev-no-memory-v5.template.yaml`,
  experiment `dev-no-memory-v5-20260730-r1`, with `pilot_run_id: null`
- `experiments/core.template.yaml`, with the embedding revision still pending freeze

The experiments consumed under the 21-call/200,000-token contract
`dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`,
`dev-validation-gpt54mini-investigation-v4-20260730-r1` and
`dev-no-memory-v4-20260730-r1` remain immutable and are not requalified under V5.

The D-052 draft reserves were `$1.2375` for one run, `$14.85` for 12 runs and `$118.80`
for 96 runs. They are not current authorizations. D-054 reserved two `$2.8125` runs, or
`$5.625`, but the completed panel's calculated cost was `$0.15682575`. Adding it to the prior
measured list-price total gives the D-055 point-in-time total `$5.138372625`. Reserves are neither spend nor invoice
predictions. The project-wide `$150` cap is not machine-enforced; only suite-specific
`cost_limit_usd` is enforced.

## Historical D-045 200k future-primary contract

At D-045, future development-validation, memory-development and core suites shared the dated
`gpt-5.4-mini-2026-03-17` snapshot, medium reasoning, standard mode, default service tier,
25,000 per-call output, 21 total model calls and 200,000 run-total tokens. The 21st call is a
normal call shared fairly by every memory condition, not a `finish_task`-only reserve. At the
official standard list rates
rechecked at `2026-07-29T22:39:42Z`, the conservative authorization reserves are `$1.0125`
per run, `$12.15` for 12 runs and `$97.20` for 96 runs.
These values remain part of the consumed 200,000-token evidence and are superseded only for future
suites by D-052.

The terminal Terra r3 suite remains byte-preserved as
`experiments/dev-validation-pilot.template.yaml`; it is readable for historical interpretation
but preflight-blocked with `HISTORICAL_SUITE_IMMUTABLE`. The historical no-fault primary r1 contract is
`experiments/dev-validation-gpt54mini-campaign-pilot-r1.yaml`. Its approved execution hash was
consumed exactly once by the terminal r1 described below; the suite must not be rerun.
The corrective contract
`experiments/dev-validation-gpt54mini-campaign-pilot-r2.yaml` was later consumed exactly once by
the accepted primary r2 described below. The first `experiments/dev-no-memory.template.yaml`
campaign was also consumed and is immutable.
Contract/qualification targeted tests passed 137/137, and the full offline suite passed
534 with 2 skips. Ruff and `git diff --check` also passed.

## D-046 primary mini r1 terminal evidence

Execution hash
`sha256:969477ca029570ea61f9fca74fd3aa558f6e16ff9b5be1c7ffa8927ed1139047`
was consumed once by `run_6993722014bf4e3b` on clean harness commit
`844b1dbe359032c04b29f1e0dd15419486694400`.

| Boundary | Observed |
| --- | --- |
| Provider/model | `gpt-5.4-mini-2026-03-17`, medium, default tier |
| Budget | 20 model calls, 50 tool calls, 25,000 per-call output, 200,000 total, $2 cap |
| Usage | 131,266 input + 12,038 output = 143,304 tokens; `$0.1526205` calculated |
| Token integrity | 20/20 exact input counts matched; 20/20 responses completed; truncation disabled |
| Agent progress | patch applied; registered regression check passed; complete final diff read; `REVIEW` reached |
| Terminal | next generation blocked locally as `model_call_budget_exhausted`; no `finish_task` or evaluator |
| Qualification | 21/22; only `prompt_token_integrity` failed because the call-budget block is not a versioned valid ending |

The exact final diff is
`sha256:9ca2431c14ce0cd5fd49b19710498a7a55a33568c748d3e44fbe794a825e083d`.
A separate no-model Docker postmortem run `run_1a742732dae842e3` applied those exact bytes to the
same task base and passed hidden, regression, scope and safety with `official=true`. This is
candidate-quality evidence only: the paid source run remains `agent_failure`,
`evaluation_status=not_run`, `qualified=false`, and does not unlock the development campaign.
The machine-readable
[primary r1 evidence record](../reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r1.json)
and its public-source unsubmitted patch preserve that distinction and bind the local raw artifacts
without bundling provider payloads or private evaluator details.

This was not provider prompt truncation, an incomplete response, total-token exhaustion,
infrastructure failure or evaluator rejection. It exposed two bounded offline work items:
submission needs a fair tail-call policy under the frozen comparison budget, and deterministic
model/tool/wall-call pre-generation blocks need a versioned terminal schema and qualification
contract. D-047 below closes both offline work items. Any later provider attempt still requires a
new experiment ID, clean execution hash and separate $2 approval.

## D-047 call-budget offline contract

Future primary, memory-development and core suites use `max_model_calls=21`; historical primary r1
remains 20-call and qualification 21/22. Exact-token reservation continues to use
`model-generation-block-v1`. Model/tool/wall counter exhaustion at next-generation admission uses
`model-generation-block-v2` with three exact reason codes and `model → tool → wall` priority.

The qualifier independently verifies the exact payload field set, strict integer types, durable
call/token/duration counters, model/tool upper bounds, budget-guard actor, request CAS/body hash,
retry shape, terminal suffix and identical `RunFailed`/`RunResult` details. It also reconciles the
event-derived wall duration with `RunResult.usage`. Tests reject count, reason, type, extra-field,
duration, actor, result-wall-clock and over-limit-tool tampering, and do not reinterpret historical
unversioned generic blocks. A complete synthetic v2 terminal trace qualifies as
`agent_failure`; it does not reach the evaluator or count as task success. Runtime evidence allows
21 generations and blocks the 22nd before input counting or provider generation.

All consumed Terra pilot IDs, model-candidate mini r1/r2, D-037 r3-r6, primary r1/r2, both 12-run
experiment IDs and v4 pilot `run_d7207fbb06184dd3` are now preflight-immutable even if an approval
hash is supplied. No paid suite is currently approved. D-052 later closed the token-aware
corrective-tail design offline without a provider call. The maintainer-assisted structured proposal
is now validated, but D-054 defers human admission/group-aware index construction. The later D-055
two-task completion panel ran once and passed; it is also preflight-immutable.

Offline verification collected 571 tests and completed 569 passes with 2 existing skips. The three
directly affected runtime/qualification/experiment files contributed 238 passes. Repository-wide
Ruff checks and `git diff --check` passed. No provider call was made while producing this evidence.

## D-048 primary r2 and first campaign evidence

Corrective primary r2 execution hash
`sha256:eb13280308f3f2642504da8493982543bb466d9bafaa5031b727dd4503003411`
was consumed exactly once by `run_afd5080a77a34995` on harness commit
`624b1d0861f9907af0ca47d8fc25795d4923ca6d`.

| Boundary | Observed |
| --- | --- |
| Provider/model | `gpt-5.4-mini-2026-03-17`, medium, default tier |
| Usage | 7 model calls, 8 tool calls, 39,171 input + 4,523 output token; `$0.04973175` |
| Submission | one prepared/applied/submitted patch, exact submitted diff preserved |
| Evaluator | official hidden/regression/scope/safety and all policy verdicts pass |
| Qualification | `trace-qualification-v2` 23/23, evaluator reached, source evidence bound |

The portable
[primary r2 evidence record](../reports/live-pilot/dev-validation-gpt54mini-campaign-20260730-r2.json)
and [submitted patch](../reports/live-pilot/artifacts/run_afd5080a77a34995-submitted.patch)
preserve this accepted-pilot boundary without bundling raw provider payloads or private evaluator
details.

The separately approved `dev-no-memory-20260728` execution hash
`sha256:48c12899dcb4bacc13b582720df33ff402be38e5b601e130baab397b9dbe7809`
then completed all 12 scheduled rows on the same model/budget contract.

| Boundary | Observed |
| --- | --- |
| Matrix | 6 memory-development tasks × 2 repetitions, `no_memory`, 12/12 terminal |
| Qualification | 12/12 structurally qualified `agent_failure`; zero infrastructure or qualification errors |
| Evaluator | 0/12 reached; zero submitted patches |
| Usage | 231 model calls, 563 tool calls, 1,544,366 input + 52,204 output token; `$1.3931925` |
| Activity | 405 searches, 157 reads, one unsuccessful apply attempt; no `PatchPrepared` or `PatchApplied` |
| Terminal | six model-call-cap and six tool-call-cap failures |

This is not a no-memory performance baseline and is not automatically admitted to the memory
index. Across 562 read/search inspections, 216 were exact nonconsecutive duplicates and another 60
reads were fully covered by prior successful ranges. The portable
[campaign evidence record](../reports/memory-development/dev-no-memory-20260728.json) preserves the
12 row outcomes and claims boundary.

## Historical D-048 investigation-continuity offline contract

D-048 introduced `phase-evidence-v4` for fresh non-replay manifests at that time. Each model turn receives a bounded
`investigation-ledger-v1` rebuilt from append-only events, the latest checkpoint and verified
successful read/search CAS in the active mutation epoch. Exact searches and fully-covered reads
still consume one model action and one `ToolCalled`, but skip filesystem dispatch and close with
`LoopDetected(investigation-loop-v1)` plus `ToolReplayed(tool-replayed-v2)`. Two consecutive
no-progress observations set `strategy_change_required=true`.

The nominal corrective tail is `4 + 2 × visible-check count` tool calls and three model calls plus
one feedback call. Once that threshold is reached, all otherwise valid read/search requests,
including requests eligible for semantic replay, are rejected by
`ToolAdmissionBlocked(tool-admission-blocked-v1)` before `ToolCalled`; apply, registered checks,
diff review and submission remain available. The context policy projects the imminent model
generation before advertising read/search, matching the gateway counter after that generation is
recorded. Qualification reconstructs every v4 request ledger and rendered context from preceding
event/checkpoint/CAS evidence. A separate `investigation_lifecycle` check independently verifies
semantic-replay ordering, source identities, no-progress streaks, admission counters and the
absence of a correlated `ToolCalled` after an admission block. Replay/admission CAS is bound by
`trace-source-evidence-v4`, including the otherwise nested admission input bytes, and the same
bytes participate in the private-token scan. Shared admission/dispatch validation rejects bad
types, missing read targets and symlink escapes before a tail block can mask them. Event-time
resolved path and target bytes are frozen in `inspection-admission-preflight-v1`; qualification
uses that CAS instead of the mutable terminal workspace. Orphaned replay lifecycles, removed
semantic markers and replay of a truncated search fail closed. V1-v3 rendering, source
evidence and historical qualification hashes are unchanged. This policy is within-run repository
evidence applied identically to all four cross-run memory conditions; it does not add hypotheses,
solutions or reference/private data.

The final offline regression on 2026-07-30 collected 610 tests and completed with 607 passed,
0 failed and 3 environment-dependent skips in 352.2 seconds. The v4 context/gateway/state/
qualification subset and the 85-test agent-runtime suite also passed independently; Ruff and
`git diff --check` were clean. These are harness-integrity results, not provider or task-success
measurements.

No provider call was made while implementing this offline change. A later separately approved
pilot reached the evaluator and passed both `investigation_evidence` and
`investigation_lifecycle`; its run ID now populates
`experiments/dev-no-memory-v4.template.yaml`.

## D-049 phase-evidence-v4 paid pilot

Execution hash
`sha256:cc2117dc698cdc991ccbcad45bbcfa4302f1ac265bdfdcc0753b60b2fda6eba2`
was consumed exactly once by `run_d7207fbb06184dd3` on clean harness commit
`5045e398646ec73d615785aeb95f02e877c34c90`.

| Boundary | Observed |
| --- | --- |
| Provider/model | `gpt-5.4-mini-2026-03-17`, medium, standard, default tier |
| Campaign | 1/1 terminal, zero infrastructure/qualification/diagnostic errors |
| Usage | 10 model calls, 10 tool calls, 81,719 input + 5,952 output token; `$0.08807325` |
| Prompt delivery | 10/10 requested input counts equal provider usage; completed responses; truncation disabled |
| Evaluator | official hidden/regression/scope/safety pass; `scope_compliant_success=true` |
| Qualification | `trace-qualification-v2` 25/25; integrity, leakage and evaluator arrival pass |
| Rejected retry | one natural rejected candidate, one verified next-request retry, no failed source sequence |
| V4 investigation | 10/10 ledger contexts verified; mutation epoch reset observed |
| Unexercised live branches | semantic replay 0; tail admission block 0 |

The qualification hash is
`sha256:ca0262532809eb38faadc5f85aa231289f391628a9e68178093a8f22c474c813`
and its source-evidence hash is
`sha256:2177f638c28d19cba6c1d2c4fed0dbff7aaeab502f2b2baa809d44064991eddc`.
The campaign journal has four hash-chained events and its final result hash
`sha256:d3660772410bd521546a30114df0028db52b58a7f48b81c3c2c5c0f1afa3f16b`
matches the exact persisted result bytes.

The portable
[v4 pilot evidence record](../reports/live-pilot/dev-validation-gpt54mini-investigation-v4-20260730-r1.json)
and [submitted patch](../reports/live-pilot/artifacts/run_d7207fbb06184dd3-submitted.patch)
preserve the public claims boundary without bundling raw provider payloads, rejected candidate
bytes or private evaluator details.

This validates the live provider/evaluator path, v4 ledger reconstruction and one naturally
rejected patch retry. It does not provide live semantic-replay or tail-admission evidence, a
12-run no-memory baseline, cross-run memory benefit or core reliability result. The pilot is
immutable and must not be rerun. Its separately approved 12-run campaign is recorded below.

## D-050 exact-commit bridge and D-051 v4 12-run campaign

The campaign kept the pilot/current harness commit equality gate exact. It ran from a clean detached
worktree at pilot commit `5045e398646ec73d615785aeb95f02e877c34c90`, importing PatchLoop
source from that worktree while sharing the host's external `.patchloop` runtime root through a
junction. The root includes mutable SQLite and workspaces; append-only applies to event/artifact
evidence histories. The ignored bound suite differed from the pilot-commit template only by
`pilot_run_id: run_d7207fbb06184dd3`. This bridge did not authorize a descendant commit or a dirty
worktree.

Execution hash
`sha256:9befd0bf8b2eb7dbc25999786713581b4b6c95f2ad45df56e2f098a9252e5bac`
was consumed exactly once by experiment `dev-no-memory-v4-20260730-r1`.

| Boundary | Observed |
| --- | --- |
| Provider/model | `gpt-5.4-mini-2026-03-17`, medium, standard, default tier |
| Matrix integrity | 12/12 terminal, no duplicate or omitted row; zero infrastructure, qualification or diagnostic errors |
| Outcomes | SCRR 0/12; 9 `agent_failure`, 3 `task_failure`; evaluator reached 3/12 |
| Evaluated patches | hidden fail 3/3; regression/scope/safety pass 3/3 |
| Usage | 144 model calls, 153 input-count calls, 262 tool calls; 1,753,493 input + 118,321 output token |
| Prompt delivery | 144/144 executed input counts matched provider usage; 144/144 completed; truncation disabled |
| V4 investigation | semantic replay 26 across 10 runs; rejected retry 11/11; tail admission block 0 |
| Cost | `$1.84756425` calculated list price; `$4.981546875` cumulative |

All nine agent failures are `MODEL_GENERATION_BUDGET_EXCEEDED` with
`exact_request_budget_exceeded`: the exact next input plus the full 25,000-token response allowance
did not fit the remaining 200,000-token total budget, so no provider generation began. Eight blocks
occurred before the nominal investigation tail closed. One PDM repetition closed exploration after
two rejected candidates and one applied patch, but its next generation was still budget-blocked
before a tool-admission decision. No run exhausted the 21 model-call, 50 tool-call or 900-second
counter.

The result is a completed, qualified failure-trace collection campaign, not a usable no-memory
performance baseline. Machine eligibility alone does not admit memory. The nine budget-confounded
agent failures remain excluded. Three hidden task failures are provisionally reviewable as two
semantic groups—one Loguru and one consolidated tox group—but no rule has been human-reviewed,
admitted or frozen. Hidden assertion values and evaluator-only payloads are not included.

The portable
[campaign evidence record](../reports/memory-development/dev-no-memory-v4-20260730-r1.json),
[Loguru submitted diff](../reports/memory-development/artifacts/run_0794d94df2f24d87-submitted.patch),
[tox repetition 1 submitted diff](../reports/memory-development/artifacts/run_dbb2a02f3d2748a6-submitted.patch)
and
[tox repetition 2 submitted diff](../reports/memory-development/artifacts/run_1773c7d0906f4eb1-submitted.patch)
preserve the public claims boundary. Raw provider/request bodies and private evaluator evidence
remain in the ignored local store and are hash-bound rather than bundled.

The exact persisted result SHA-256 is
`sha256:e18b30c1552a3bcbf2f7538d8559a2fbb0ec76fa4968583338ee2414bc2cb734`.
The 26-event journal chain is valid, ends at
`sha256:efbdec4c1f2fb016acef6830a77959e28f03ee20f55e4a74fb151becf88de17c`,
and binds that result. The suite and schedule hashes are
`sha256:569666de18ec5a30021ad77896ff238f1e5e7fe81f4475a469cd2e6ba243acfc`
and `sha256:d0c510b697a3c3f373da2bc497120ced3c461bbfdc48b1f617c25d1b9ee80567`.
The execution hash, suite, journal and result must not be reused or rerun.

Post-capture validation passed all 42 `tests/test_live_pilot_evidence.py` tests and all 74
`tests/test_experiments.py` tests. Ruff and `git diff --check` also passed. These checks rehash the
raw local result, journal, plan and 12 qualifications when available, and always rehash the three
portable submitted diffs.

## Historical D-043 paid diagnostic evidence

The separately approved r6 execution hash
`sha256:d6a756dc69a7cf6e024d541b64a458a940ec41bdfeb3c403a3f01c539660e67b`
was consumed exactly once by `run_73f5aaf7328a4ea5` on clean harness commit
`1333ab968e2f144b632c0cb5ca341ebd30e0ca4e`.

| Boundary | Observed |
| --- | --- |
| Provider/model | `gpt-5.4-mini-2026-03-17`, medium, default tier |
| Budget | 25,000 per call, 200,000 total, $2 approved cap |
| Usage | 138,262 input + 13,800 output = 152,062 tokens; `$0.1657965` calculated |
| Token integrity | 19/19 exact input counts matched; 19/19 completed; truncation disabled |
| Agent/evaluator | one controlled rejection, one applied/submitted patch; hidden/regression/scope/safety all pass; `official=true` |
| Trace | `trace-qualification-v2` 23/23, leakage and source-evidence binding pass |
| D-037 diagnostic | controlled rejection 1, verified retry 1, rejected-action mutation 0; terminal `passed` |

The run validates the exact D-037 rehydration branch under one deliberate intervention and unlocked
only the separately approved fault-free primary mini pilot preflight that later became D-046 r1.
It does not estimate natural rejection
frequency, recovery rate or memory benefit. The frozen contract forbids automatic rerun. The
machine-readable
[r6 evidence record](../reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r6.json)
separates the controlled intervention, official task outcome and claims boundary, and includes
distinct rejected and accepted public-source patches. Through r6, six mini runs totaled
`$0.62150025`; including terminal primary r1, seven mini runs totaled `$0.77412075` and the ten
paid pilots then totaled `$1.602985125`. Corrective primary r2 later brought eleven paid pilots to
`$1.652716875`; v4 pilot `run_d7207fbb06184dd3` brings twelve paid pilots to `$1.740790125`.
The first 12-run campaign brings all 24 paid attempts to `$3.133982625` at configured list prices.
The v4 12-run campaign brings 36 paid run attempts to `$4.981546875`. Invoice and free-usage
treatment remain unverified.

Post-capture verification for the historical evidence at this point passed all 27 live-evidence
tests against the local raw artifacts,
including journal/result/CAS hash binding and private/provider-payload exclusion. Ruff and
`git diff --check` also passed. The D-043 implementation baseline remains the separately executed
529-pass/2-skip full suite; this evidence-only follow-up does not claim a new full-suite run.

## Executed gates

| Gate | Command | Outcome |
| --- | --- | --- |
| Lock consistency | `uv --cache-dir .patchloop/uv-cache lock --check` | pass, 78 packages resolved |
| Static analysis | `.venv/Scripts/ruff check . --no-cache` | pass |
| Tests | `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q -p no:cacheprovider` | 224 passed, 2 skipped |
| Package build | `uv build` | sdist and wheel built |
| Task contract | `patchloop task validate tasks/<split>/<task>` | five calibration plus twenty research packages pass |
| Dataset audit | `patchloop dataset audit` | pass: frozen 25-task manifest, research 20/20, stress 3/3, 30 derived runs, no blockers |
| Docker build | pinned base, `--network=none --provenance=false`, repeated twice | stable image ID in 2/2 builds |
| Docker isolation (native image) | network, UID, read-only workspace, host secret | all pass; external benchmark-image user remains separately disclosed |
| Research admission | Loguru #1451/#1297, AnyIO #1121/#1134, tox #3810/#3846+#3851, Hugging Face Hub #3180/#4056, PDM #2781/#3759, pyfakefs #991/#1269, Moto #7208, Babel #1042, SQLGlot #7187, Param #1117, MTPLX #21, FuseSoC #776, Dagster #33605 and Kubeflow Pipelines #13112 references ×3 plus declared negatives | research role target 20/20; references pass; all negative cases rejected; all `official=true` |
| Offline agent smoke | three tasks × mock/replay on Docker | 6/6 SCRR pass, complete trace, all `official=true` |
| Offline campaign | `patchloop evaluate --suite experiments/smoke.yaml` | 1/1 completed, 0 infra errors |
| Report regeneration | `patchloop report --experiment offline-smoke ...` | JSON/CSV/HTML and portable evidence bundle |
| Viewer routes | six ASGI route requests | all HTTP 200 |
| Portable bundle scan | username, absolute workspace, private/reference path scan | pass |

Latest bundled offline run: `run_671aa408ac4241ca`.

- SCRR: pass
- hidden: pass
- regression: pass
- scope: pass
- official: false
- model calls: 5 mock calls
- tool calls: 4
- measured active wall time: 1,144 ms

The one-task bootstrap interval `[1.0, 1.0]` is mechanically correct but not inferentially useful. It must
not be presented as benchmark evidence.

## Official offline agent smoke evidence

Commit `1ea257cbbcc2ce131b5c09508f6df8c62ed23ed8` was run against the pinned Docker evaluator.
Each of the three smoke tasks completed once with the task-aware mock and once with its checked-in,
content-hashed replay.

| Task | Mock run | Replay run | Observed |
| --- | --- | --- | --- |
| `csv-quoted-newline` | `run_5cd7103a1c6f4d7a` | `run_c468655d03ed4d08` | 2/2 SCRR pass, `official=true` |
| `config-falsy-override` | `run_1492e28b07dd4feb` | `run_403b92ac32264725` | 2/2 SCRR pass, `official=true` |
| `path-prefix-boundary` | `run_27339c856bee4242` | `run_bd06edd18bc9434f` | 2/2 SCRR pass, `official=true` |

Every accepted run records five model calls, four tool calls, five rebuilt contexts, one `PatchApplied`,
one `RunCompleted` and a final `DONE` checkpoint. Persisted `result.json` usage equals SQLite state.
The context scan found no hidden check ID or reference-patch locator; the first context also excludes the
private reference hash. Replay manifests bind the repository-relative JSONL path to its SHA-256.

The machine-readable [offline agent smoke summary](../reports/offline-agent-smoke/summary.json) records
run IDs plus manifest, result, provenance, submitted-patch, event-stream and checkpoint hashes. It also
keeps an exclusion ledger for one non-official Docker-daemon diagnostic run and six pre-fix runs whose
persisted result artifact omitted agent usage. Those runs were not counted in the 6/6 gate.

These are deterministic scripted runs with zero API calls and zero model cost. They establish harness,
trace and evaluator behavior; they are not evidence of live-model quality or memory effectiveness.

## Official Docker evaluator evidence

The pinned base image is
`python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Two network-disabled builds with BuildKit provenance disabled produced the same evaluator image ID:
`sha256:5d430c8dbf2e1222148909ed4c79c3cbf212aa25a94c8c2d0cbd0a97adfccf1f`.

| Fixture | Final run | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_251d172b049e49c3` | full success | success |
| no-op | `run_8da6d410add948e4` | hidden fail | rejected |
| regression | `run_9b86d529fd57493b` | regression fail | rejected |
| forbidden path | `run_9328887b3bfc4d12` | scope fail | rejected |
| dependency | `run_e68390d517824e4b` | dependency/scope fail | rejected |
| test tampering | `run_2f57822c729348c1` | tampering/scope fail | rejected |
| public API | `run_a7771fc59af24470` | public-API/scope fail | rejected |

The machine-readable [Docker gate summary](../reports/docker-gate/summary.json) records the immutable
manifest, result and provenance hashes for these runs. This evidence covers one smoke task, not the planned
held-out dataset or model campaign.

Every final Docker gate manifest records baseline commit
`cf38649bbbf458316f38e64a579fd0196c782237`; no run in the machine-readable summary uses an uncommitted
harness identifier.

## Smoke task expansion evidence

Two additional independently content-addressed snapshots were frozen in commit
`024a3a375dc9514be6d127199d10f7115659eecf`.

| Task | Reference run | Known-bad corpus | Observed |
| --- | --- | --- | --- |
| `config-falsy-override` | `run_57c437c24e154317` | no-op, partial falsey fix, regression, forbidden path | reference passed; 4/4 rejected |
| `path-prefix-boundary` | `run_395efa14bc7c4e59` | no-op, boundary-only fix, regression, forbidden path | reference passed; 4/4 rejected |

All ten expansion runs record the task commit and the same pinned evaluator image as the CSV gate. The
[smoke expansion summary](../reports/docker-gate/smoke-expansion.json) records task/spec hashes, run IDs
and manifest/result/provenance hashes. Together, the three smoke tasks cover parser state, merge semantics
and path normalization without sharing a solution.

## First additional calibration fixture

`duration-minute-boundary` is the first `dev-train` package. Its immutable snapshot keeps exact-minute
and sub-minute visible behavior working while deliberately rounding incomplete minute buckets upward.
The private acceptance checks values inside and near the end of those buckets.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_4c333240f3ae4a26` | full success | success, `official=true` |
| no-op | `run_02cdf575981042d5` | hidden fail | rejected |
| near-miss | `run_18b131fb74a84d1a` | hidden fail | rejected |
| regression | `run_51bc997fa1394e20` | visible regression fail | rejected |
| forbidden path | `run_a5b492be61d2433d` | hidden and scope fail | rejected |

All five manifests record clean harness commit `6152e9b207ee615f5c1dd0ec8dbefc09f075f951`
and the pinned evaluator image. The machine-readable
[dev-train task gate](../reports/docker-gate/dev-train-duration-minute-boundary.json) records task/spec,
patch, manifest, result and provenance hashes. This is calibration evidence, not a model run; it
made zero API calls and does not create a memory entry. A clean clone reproduced the declared snapshot
hash `sha256:a3508607ed05735c39f766580002fa29801440ee66301fbc85b1525114f079fe`.

## Second additional calibration fixture

`csv-final-record-flush` uses a separate chunked-parser API and source file from the multiline-CSV smoke
task. Its base snapshot handles newline-terminated records, chunk boundaries and quoted commas, but does
not finalize the remaining valid record when input reaches EOF.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_b01dedac6de84caa` | full success | success, `official=true` |
| no-op | `run_aad5c6d582d24e40` | hidden fail | rejected |
| near-miss | `run_6992b1281550416c` | hidden fail | rejected |
| regression | `run_4db275cfe376444f` | visible regression fail | rejected |
| forbidden path | `run_32865f2f94754584` | hidden and scope fail | rejected |

All five manifests record clean harness commit `76471df95e26857f42662b7514fa31896a5496a2`
and the pinned evaluator image. The machine-readable
[CSV final-record gate](../reports/docker-gate/dev-train-csv-final-record-flush.json) records task/spec,
patch, manifest, result and provenance hashes. This fixture gate made zero API calls and creates no memory
entry. A clean clone reproduced snapshot hash
`sha256:afa42fe0bcb75bc7f0f7969e394433d5c8e9c8ce34232ebbf5bb5416c2bcd680`.

## First research task admission

`loguru-invalid-format-feedback` comes from SWE-rebench leaderboard instance
`delgan__loguru-1451`, upstream issue #1450 and PR #1451. It is registered as
`memory-development`, not held-out. The source is pinned to Loguru commit
`2abeb0fa6d7be4b0455c6e0b580b1e9dab19005e`; the upstream resolution is
`b782e56fcf07fecf9545ff6ee2350baacb0968ce`.

The evaluator uses the official task environment at immutable digest
`sha256:181bd51aa34ebe84d749819dfbe9a2d3d215ff8f6406d897d790f876bc5f36db`.
Every run is network-disabled and uses harness commit
`d7cdd6fa1055311275ff4c8751051f47bb118ed5`.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_da8b68a7ed544b20`, `run_528b24d9038e47d5`, `run_63e461ef353b4756` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_0766fe431389477d` | base visible pass, hidden fail | rejected |
| generic diagnostic | `run_70725e940deb4260` | hidden diagnostic-content fail | rejected |
| catch-true only | `run_6ca5cfe1e4d84d88` | hidden catch-false fail | rejected |
| hardcoded reproduction | `run_51a443c8c3484b7b` | hidden alternate-key fail | rejected |
| swallowed catch-false | `run_67209fa6a07844cc` | hidden propagation fail | rejected |
| forbidden README edit | `run_f2cb40457ecb494d` | hidden and scope fail | rejected |

The upstream `tests/test_add_option_format.py` file reported 20 passes on each reference run. PatchLoop's
independently authored hidden oracle additionally checks both catch modes, actionable diagnostic content
and patcher-injected keys. The machine-readable
[research admission report](../reports/docker-gate/research-loguru-invalid-format-feedback.json) records
all manifest, result, patch and provenance hashes. It made zero API calls and is evaluator evidence, not
live-model performance.

## Second research task admission

`anyio-interrupt-runner-cleanup` comes from SWE-rebench instance
`agronholm__anyio-1121`, AnyIO issue #1060 and PR #1121. It is a hard
`memory-development` task pinned to base commit
`cb245dba9883516f2ed4c23899de157183a1cb50` and evaluator image
`sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320`.

The original upstream fix stopped an interrupted async test from resuming during fixture teardown.
Follow-up issue #1179 and PR #1180 later showed that the same handler incorrectly reset the runner for
normal pytest `OutcomeException` signals. PatchLoop therefore uses a hardened reference that preserves
both behaviors, and treats a source-equivalent normalization of the original fix as a known-bad patch.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened reference | `run_4b93be1d3b664ee4`, `run_127a2daf82c14f3b`, `run_863bf64317894ade` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_bcf39b1790d94d8f` | P2P pass, hidden no-resume fail | rejected |
| cancel without drain | `run_0e57530dd1f9485b` | hidden lifecycle fail | rejected |
| drop runner reference only | `run_48d940b39f694567` | hidden stale-task fail | rejected |
| swallow interrupt | `run_f572a38ce28446d6` | hidden propagation fail | rejected |
| normalized upstream fix | `run_3fc2bd62bc9d4a9e` | hidden expected-outcome lifecycle fail | rejected |
| forbidden test edit | `run_a888124ac80a47f7` | hidden, scope and tampering fail | rejected |

The 32 benchmark P2P tests passed on base and reference. Three unrelated upstream tests that need the
optional `hypothesis` package were explicitly deselected because that dependency is absent from the
pinned official image. The private signal/lifecycle oracle passed 20/20 supplemental repetitions with
the hardened reference. The
[AnyIO research admission report](../reports/docker-gate/research-anyio-interrupt-runner-cleanup.json)
records task, image, patch, manifest, result and provenance hashes. It made zero model/API calls.

## Third research task admission

`tox-cross-section-empty-substitution` comes from SWE-rebench leaderboard instance
`tox-dev__tox-3810`, tox issue #3809 and PR #3810. It is a hard `memory-development` task pinned to
base commit `02e9ed73da6a0f97f9167e957e1168d6116942ce` and evaluator image
`sha256:ffd1129e4be4692becf5011c874858918864d586267002a2917195726542de57`.

The regression followed an earlier same-section fallback change: a same-section value filtered to empty
must still signal the computed fallback, while an existing value reached through a `SectionProxy` must
resolve to an empty string rather than be treated as absent. The independent hidden oracle checks both
sides of that boundary and excludes the later, unrelated override-propagation behavior from tox PR #3951.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_69c2902bef904d70`, `run_4fc68a56c574420e`, `run_a50049ba72f04850` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_26381b0f1ede4362` | P2P pass, hidden fail | rejected |
| section `KeyError` on empty | `run_32cfdaf52afe4e2f` | hidden semantic fail | rejected |
| global factor empty | `run_7497de1bbeef42fe` | hidden and regression fail | rejected |
| hardcoded upstream section | `run_c03e7fdeedfc41e3` | hidden alternate-section fail | rejected |
| drop all cross-section values | `run_cd00d175dee740b5` | hidden and regression fail | rejected |
| forbidden test edit | `run_db7e448418114cea` | hidden, scope and tampering fail | rejected |

The base and reference passed all 29 benchmark P2P tests. The reference passed six independently authored
hidden checks on each of three official network-disabled Docker evaluations. The admission work also
fixed two harness defects before the final evidence set was frozen: Git patch evidence is decoded as
UTF-8 on Windows, and src-layout checks explicitly bind to the submitted source tree while preserving
the image-generated `tox/version.py` module. The
[tox research admission report](../reports/docker-gate/research-tox-cross-section-empty-substitution.json)
records task, image, patch, manifest, result and provenance hashes. It made zero model/API calls.

## Fourth research task admission

`hf-hub-xet-endpoint-propagation` comes from SWE-rebench V2 instance
`huggingface__huggingface_hub-3180`, Hugging Face Hub issue #3168 and PR #3180. It is a hard
`memory-development` task pinned to base commit
`6f9b87ecda5025259c69a1eb0ae6f8ee80d05d33` and evaluator image
`sha256:c698facf4c9a9e636b8dc114aa9bda6a17ee5f89fe3efd43f39a6543540e891f`.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_d5419f78c5584ab3`, `run_a35997231ad7495a`, `run_4d4da461a8b74ea4` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_e6276ffd6a974845` | P2P pass, hidden fail | rejected |
| parser only | `run_61cc4dc3fff94994` | hidden propagation fail | rejected |
| missing `HfApi` forwarding | `run_6e39f1dbc4034225` | hidden wrapper-path fail | rejected |
| missing download forwarding | `run_092c0061dce545f6` | hidden internal-path fail | rejected |
| unguarded substring replace | `run_7088ef71a036459b` | hidden foreign-route fail | rejected |
| hardcoded default endpoint | `run_e9281b5a7e6f46ab` | hidden endpoint-context fail | rejected |
| forbidden test edit | `run_5c1be518ea764f8f` | hidden, scope and tampering fail | rejected |

The base and every semantic partial fix passed all 15 benchmark P2P tests. The independently authored
eight-check oracle covers header and link parsing, relative and foreign-origin route preservation,
default and explicit endpoints, the low-level parser, internal download path and `HfApi` wrapper. It
also binds imports to `/workspace/src` and fingerprints the exact allowed public-signature delta, so the
broad task-level API permission does not widen acceptance. The
[Hugging Face Hub research admission report](../reports/docker-gate/research-hf-hub-xet-endpoint-propagation.json)
records all patch, manifest, result and provenance hashes from clean harness commit `ebf05dd5...`.
It made zero model/API calls.

## Fifth research task admission

`pdm-ignore-active-venv-resolution` comes from SWE-rebench V2 instance
`pdm-project__pdm-2781`, PDM issue #2779 and PR #2781. It is a hard `memory-development` task pinned to
base commit `881cd4e38d31663ae67bdae227ec1ccdfd5e2c77` and evaluator image
`sha256:a822ad3888e56650c18e9506f8d7882c145ed83d47d518e541e3e44406a929a0`.
PatchLoop normalizes the upstream gold to its production `src/pdm/project/core.py` hunk, excluding the
news fragment and benchmark test patch.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| normalized production reference | `run_0d4fa49d3001445b`, `run_d442b8a0f0c84c5d`, `run_ff83740fc8254969` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_072ec52983844c14` | base regression pass, hidden fail | rejected |
| outer guard removed only | `run_fc56d899d7c3408e` | hidden active-environment fail | rejected |
| direct lookup filtered only | `run_d7cfeeb5a7bf41eb` | hidden associated-environment fail | rejected |
| raw environment truthiness | `run_fc9ff1e3a4f04a53` | hidden false-like-value fail | rejected |
| skip associated environments | `run_886dd7ac5d9549b4` | hidden fallback fail | rejected |
| `VIRTUAL_ENV` only | `run_7eb8ce0b05ec4809` | hidden `CONDA_PREFIX` fail | rejected |
| string-prefix containment | `run_a4f6bdb83c444973` | hidden path-component fail | rejected |
| forbidden test edit | `run_8613c82a35eb49e8` | hidden, scope and test-tampering fail | rejected; aggregate safety remained `pass` |

The base checkout and all six semantic partial fixes passed 36 upstream regression tests. The benchmark
declares 37 P2P nodes because one passing false-flag parameter exists only after its test patch; the
independently authored ten-check hidden oracle covers that behavior without importing the benchmark
test. It also checks submitted-source binding, truthy and false-like settings, `VIRTUAL_ENV`,
`CONDA_PREFIX`, associated-environment and create fallbacks, path-component boundaries and saved
interpreter precedence. The forbidden edit was rejected by the scope and `test_tampering` verifier;
the current aggregate safety verdict remained `pass`, so it is not reported as a safety failure. The
[PDM research admission report](../reports/docker-gate/research-pdm-ignore-active-venv-resolution.json)
records all patch, manifest, result and provenance hashes from clean harness commit `035d7c7f...`.
This gate made zero model/API calls.

## Sixth research task admission

`pyfakefs-makedirs-parent-traversal` comes from SWE-rebench V2 instance
`pytest-dev__pyfakefs-991`, pyfakefs issue #987 and PR #991. It is a medium
`memory-development` task pinned to base commit
`7285b671883b8a06fc26466582a8a45baf508bf7` and evaluator image
`sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c`.
PatchLoop normalizes the upstream gold to the exact production hunk in
`pyfakefs/fake_os.py`, excluding `CHANGES.md` and the benchmark test patch.

| Patch | Runs | Expected boundary | Observed |
| --- | --- | --- | --- |
| normalized production reference | `run_009825262b514a68`, `run_7af592bb11bd4e1c`, `run_12873e02117e455b` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_0f7e30047ecf4639` | P2P pass, hidden fail | rejected |
| normalize before creation | `run_f3cae9f4ed4c4442` | regression and hidden traversal fail | rejected |
| one string parent only | `run_4faf97a4757940cf` | hidden bytes/mode fail | rejected |
| propagate leaf mode to parents | `run_e3a8ccad251245fd` | hidden intermediate-mode fail | rejected |
| ignore `exist_ok` | `run_dae4dc5afe1e43bd` | regression and hidden existing-leaf fail | rejected |
| stop after parent creation | `run_28df8167bca54794` | regression and hidden destination fail | rejected |
| swallow non-directory errors | `run_71fa030f5eb04a96` | regression and hidden error-policy fail | rejected |
| leave parent `FileExistsError` uncaught | `run_4007c8257dc443dd` | regression and hidden traversal fail | rejected |
| forbidden test edit | `run_17f66c01ff914266` | hidden, scope and test-tampering fail | rejected |

The base checkout passed all 517 benchmark-declared P2P tests and failed the private
acceptance suite; the same network-disabled command reported 570 platform skips. The
independently authored 12-check oracle binds `FakeOsModule.makedirs` to `/workspace` and covers
ordered POSIX and Windows traversal, nested and bytes paths, trailing separators, pre-existing
destinations, `exist_ok`, non-directory parents and leaf-only mode application. The reference
passed all 12 checks. The
[pyfakefs research admission report](../reports/docker-gate/research-pyfakefs-makedirs-parent-traversal.json)
records all patch, manifest, result and provenance hashes from clean harness commit `64b2f467...`.
This gate made zero model/API calls.

## Seventh research task admission

`moto-query-scanned-count` comes from SWE-rebench V2 instance
`getmoto__moto-7208`, Moto issue #7206 and PR #7208. It is a hard
`development-validation` task pinned to base commit
`624de34d82a1b2c521727b14a2173380e196f1d8` and evaluator image
`sha256:dfdf957ab30b8829e8b6bbfd693b00fab88b7979d3c856362fd5d66c489a1fee`.
PatchLoop normalizes the accepted PR to its production module and excludes the
benchmark test patch.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| normalized production reference | `run_cee764017ee14f6f`, `run_e3c92f006f094766`, `run_ebb46abb00ea4da9` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_7e5dad51ff294ca7` | regression pass, hidden fail | rejected |
| partition total only | `run_f3838733470e4876` | range, page and index count fail | rejected |
| key results before page | `run_a45ede4752554f08` | per-page count fail | rejected |
| limit without cursor | `run_659b65fc2bde4447` | final-page count fail | rejected |
| post-filter result count | `run_e752404041714902` | pre-filter count fail | rejected |
| index uses table count | `run_bc92fd9ff295438c` | GSI and page count fail | rejected |
| cursor subtraction without limit | `run_06f7c30a08ed4b85` | first and middle-page count fail | rejected |
| forbidden test edit | `run_6fa7ed308ac6435a` | hidden, scope and test-tampering fail | rejected |

The base and all six semantic partial fixes passed 182 selected upstream
regressions. The benchmark declares 173 logical P2P nodes; two truncated
parameterized identifiers expand the set to 179 concrete passing cases. Nine
endpoint tests outside the P2P declaration are explicitly deselected because
they attempt real AWS hosts under a network-disabled evaluator. The independent
nine-check oracle binds `Table.query` to `/workspace` and covers partition and
empty-query scoping, pre-filter accounting, range and GSI conditions, three-page
pagination, filtered limits, projection and reverse ordering. The
[Moto research admission report](../reports/docker-gate/research-moto-query-scanned-count.json)
records every patch, manifest, result and provenance hash from clean harness
commit `b4cc0ec8...`. This gate made zero model/API calls.

## Eighth research task admission

`babel-strict-grouped-decimal-trailing-zeroes` comes from SWE-rebench V2
instance `python-babel__babel-1042`, Babel issue #928 and PR #1042. It is a
medium `development-validation` task pinned to base commit
`aca7663728e08e9d60b192b11fa6626a60974929` and evaluator image
`sha256:864e84fc4bdf09252f7fda4f85665cc05155a7b1d75847d61c67325abce7ef5a`.
PatchLoop keeps the exact accepted production diff and excludes the benchmark
test patch.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_76d98886b57a46ff`, `run_d0b4c5c529d042b1`, `run_bf33a6f3a4ef42f9` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_a8f6829db59a4693` | regression pass, hidden fail | rejected |
| dot-decimal only | `run_cad3072044ae4125` | comma and Arabic symbol fail | rejected |
| positive only | `run_6377516927944677` | signed value fail | rejected |
| single-zero trim | `run_3d6585338f7648c3` | longer padding fail | rejected |
| normalize returned Decimal | `run_2e67c5483f094e52` | scale preservation fail | rejected |
| remove all fractional zeroes | `run_ee43f7dbdcbc487f` | significant internal zero fail | rejected |
| suffix-zero bypass | `run_299c0b5d1d174afa` | malformed grouping acceptance | rejected |
| Western grouping only | `run_a3f1007f58cf4c70` | Indian and locale grouping fail | rejected |
| forbidden test edit | `run_e6d6853299034b7f` | hidden, scope and test-tampering fail | rejected |

The base and all seven semantic partial fixes passed all 132 upstream number
tests. The independent 16-check oracle uses values not copied from the issue or
benchmark test patch and covers dot, comma and Arabic decimal symbols, Western,
Indian and narrow-space grouping, signs, significant internal zeroes,
one- through three-zero suffixes, malformed inputs, non-strict compatibility
and Decimal scale. The immutable Git checkout omits generated CLDR data, so the
registered checks use `/babel/babel` data from the pinned image while a
source-binding assertion proves that `parse_decimal` comes from `/workspace`.
The
[Babel research admission report](../reports/docker-gate/research-babel-strict-grouped-decimal-trailing-zeroes.json)
records every patch, manifest, result and provenance hash from clean harness
commit `313af714...`. This gate made zero model/API calls.

## Ninth research task admission

`sqlglot-duckdb-ignore-nulls-modifier-order` comes from SWE-rebench leaderboard
instance `tobymao__sqlglot-7187`, SQLGlot issue #7179 and PR #7187. It is the
first hard `core-cross-repo` held-out task, pinned to base commit
`0e8d0824c40ac46c5e7275180cf2eaae6810f805` and evaluator image
`sha256:43c43d77e3bed15361140767e3f3fd84811e0bad5b58f6afcba83f79b8e58303`.
PatchLoop keeps the exact accepted three-file production diff and excludes the
benchmark test patch. The public localization therefore matches the accepted
patch and is disclosed as high contamination risk.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_f6a17eb337ac486b`, `run_e3395c116cb747ae`, `run_f8633ed259ec4c3c` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_7724db84e8d44a66` | regression pass, hidden fail | rejected |
| parser only | `run_1a90d9dfea954ad5` | generator/order policy fail | rejected |
| generator only | `run_8aecaee9e8dc4742` | trailing parse fail | rejected |
| global order change | `run_5b43cf766610458e` | dialect isolation fail | rejected |
| IGNORE only | `run_3b4dd9eb77954b7c` | symmetric RESPECT behavior fail | rejected |
| missing DuckDB policy | `run_effcc359b41947fc` | dialect suffix generation fail | rejected |
| missing shared generator policy | `run_d2125ae9d3ef40f7` | generator integration fail | rejected |
| missing `HAVING MAX` policy | `run_93483d6a5b6f4a7d` | BigQuery modifier-chain guard fail | rejected |
| forbidden test edit | `run_7dce9a09b23f47ab` | hidden, scope and test-tampering fail | rejected |

The base and all seven semantic partial implementations passed all 39 upstream
DuckDB tests. The independently authored 21-check oracle binds submitted modules
to `/workspace`; checks `IGNORE NULLS` and `RESPECT NULLS` across FIRST_VALUE,
LAST_VALUE, NTH_VALUE, LAG and LEAD; preserves offsets, defaults, named windows,
frames and AST placement; and guards BigQuery `HAVING MAX` / `ORDER BY` / `LIMIT`
ordering. The hardened extension uses different identifiers, clauses and values
from the benchmark test patch and is a targeted guard, not an exhaustive claim
over every SQLGlot dialect. The
[SQLGlot research admission report](../reports/docker-gate/research-sqlglot-duckdb-ignore-nulls-modifier-order.json)
records every patch, manifest, result and provenance hash from clean harness
commit `89f47025...`. This gate made zero model/API calls.

## Tenth research task admission

`pdm-target-project-options-loading` comes from SWE-rebench leaderboard instance
`pdm-project__pdm-3759`, PDM issue #3756 and PR #3759. It is the first hard
`core-same-repo` held-out task, pinned to base commit
`e96d535bb1bd64ac21575cf3490d64f737c6a668` and evaluator image
`sha256:7a012a5bfd460d638b74d3de84426cd1fa2141aec3914c4f9171071491f5ac93`.
The development PDM #2781 task changes interpreter candidate selection in
`src/pdm/project/core.py`; this task changes CLI bootstrap ordering in
`src/pdm/core.py`, so their solution lineages are distinct.

The benchmark PR test mocked `parse_args` and put `-p` before the subcommand,
an order rejected by PDM's real subcommand parser. Its production patch also
scanned raw arguments before parsing. PatchLoop therefore uses the PDM
maintainer's immediate follow-up, normalized onto the benchmark base, as the
hardened one-file reference. The exact benchmark production hunk remains a
known-bad patch.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened maintainer-follow-up reference | `run_dc888b1a81b94a6a`, `run_5de9431b97a24932`, `run_a2436ff595514516` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_c208dfd11cdc41ad` | regression pass, hidden fail | rejected |
| exact benchmark PR extractor | `run_9f8eb00272e8407f` | attached/repeated/environment precedence fail | rejected |
| caller fallback when target has no option | `run_852bbd813c5b4c5c` | target isolation fail | rejected |
| caller options injected after selection | `run_081e6a8b166d4535` | regression and target isolation fail | rejected |
| environment-only selection | `run_46fcaf6a87324578` | CLI selection forms fail | rejected |
| ignore explicit object | `run_eab9fa34934d457d` | regression and object precedence fail | rejected |
| inject without reparse | `run_1d1c3454dd604b62` | configured options have no parsed effect | rejected |
| install command only | `run_473206223a554407` | cross-command behavior fail | rejected |
| project selection without injection | `run_f03af3d7aee34e6c` | regression and configured-option behavior fail | rejected |
| separated short form only | `run_26aada063fef4f5d` | long/attached/repeated forms fail | rejected |
| forbidden test edit | `run_386caf37ef904569` | hidden, scope and test-tampering fail | rejected |

The registered public file reports 63 passing regressions after explicitly
deselecting one node that attempts an external package install under the
mandatory network-disabled evaluator. The benchmark metadata separately
declares one F2P and 63 P2P nodes. The independent 11-check oracle binds imports
to `/workspace/src`; exercises separated and attached short/long forms,
repeat-last-wins, `PDM_PROJECT`, explicit-object precedence, global isolation,
multiple commands and no caller fallback; and preserves normal caller-project
behavior. The
[PDM target-project research admission report](../reports/docker-gate/research-pdm-target-project-options-loading.json)
records every patch, manifest, result and provenance hash from clean harness
commit `ad25a8a...`. This gate made zero model/API calls.

## Eleventh research task admission

`anyio-extensionless-entrypoint-worker-main` comes from SWE-rebench leaderboard
instance `agronholm__anyio-1134`, AnyIO issue #1027 and PR #1134. It is the
second hard `core-same-repo` held-out task, pinned to base commit
`01b8d02381ba95ba11241c1ec361e908fe05b8be` and evaluator image
`sha256:d7997027864d2bfb32d649e7e544381f5d1b161df8f1682c719d222d66489dc0`.
The development AnyIO #1121 task changes interrupted pytest runner cleanup in
`src/anyio/_backends/_asyncio.py`; this task changes process-worker reconstruction
of an extensionless entrypoint in `src/anyio/to_process.py`. Their trigger,
failure mechanism and solution lineage are distinct.

The benchmark gold also changes a changelog and an unrelated documentation
dependency marker, while its test patch changes `tests/test_to_process.py`.
PatchLoop keeps the exact accepted production hunk only. No semantic hardening
or later follow-up was substituted.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_195b5bb706d8474c`, `run_cc99d8a8a0714a45`, `run_61da03d9899b4bad` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_c3ef90631f9549b4` | regression pass, hidden fail | rejected |
| only `__main__` alias | `run_0068d719bf2c412c` | multiprocessing alias missing | rejected |
| metadata dropped | `run_84374942f4c44310` | module name/file contract fail | rejected |
| entrypoint executed twice | `run_9f849b88babc4de1` | exactly-once contract fail | rejected |
| empty main module | `run_1b74ccf7e065445d` | entrypoint globals missing | rejected |
| dictionary used as module alias | `run_d88cdcf779fa44d8` | module identity/type fail | rejected |
| run-path result not copied | `run_7062a43e83664327` | callable/global lookup fail | rejected |
| extensionless-only fallback | `run_ee7d3cff08a64b60` | unknown-suffix compatibility fail | rejected |
| unnamed run path | `run_dffecd32ca814d8d` | multiprocessing module name fail | rejected |
| `run_name="__main__"` | `run_cc5a0510264e407e` | main-guard recursion; regression and hidden fail | rejected |
| forbidden test edit | `run_61eae9117ae04a94` | hidden, scope and test-tampering fail | rejected |

The unmodified base and eight non-recursive semantic partials passed all 36
upstream process-pool tests while failing the independent 11-check oracle. The
oracle launches real extensionless entrypoints through AnyIO's worker path,
binds imports to `/workspace/src`, covers asyncio and trio, an unknown suffix,
path spaces, `__main__` / `__mp_main__` identity, module metadata, exactly-once
loading, worker reuse, ordinary `.py` compatibility and initialization-error
propagation. It observes behavior rather than requiring `runpy` or `ModuleType`.
The
[AnyIO process-worker research admission report](../reports/docker-gate/research-anyio-extensionless-entrypoint-worker-main.json)
records every patch, manifest, result and provenance hash from clean harness
commit `9dfc60dd...`. This gate made zero model/API calls. All runs used a
network-disabled, read-only Docker boundary. The external evaluator image has no
configured user and therefore ran as Docker's default root user; the limitation
is disclosed rather than attributed to the native image's non-root smoke.

## Twelfth research task admission

`param-shared-rx-fanout-cache` comes from SWE-rebench leaderboard instance
`holoviz__param-1117`, Param issue #1116 and PR #1117. It is the second hard
`core-cross-repo` held-out task, pinned to base commit
`833c8f05f7a47fa1476620307ef7fd447c45e6fb` and evaluator image
`sha256:c10bc0ad51b00c59ed8fa4366ee722c38e83dfaa620a7cc229f78489ccbaf010`.
PatchLoop keeps the exact accepted production hunk in `param/reactive.py` and
excludes the benchmark test patch. The public issue, accepted patch and one-file
localization are all available upstream, so contamination risk remains high.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_abd2492639524050`, `run_6371e12b93324023`, `run_314c93a4a1f24577` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_16f15bd5874c4c75` | regression pass, hidden fail | rejected |
| missing shared clone link | `run_972670209bdf4d59` | hidden shared-source fail | rejected |
| synchronous sharing only | `run_552269843cd84065` | hidden async/generator fail | rejected |
| async result not awaited | `run_9bffaeffa42345bb` | hidden coroutine fan-out fail | rejected |
| generator detection omitted | `run_13241124090d4297` | regression and hidden generator fail | rejected |
| wrong shared pointer | `run_cb2d851f8f9e4b31` | regression and hidden isolation fail | rejected |
| self-method guard omitted | `run_be453108ce604ba8` | hidden accessor-divergence fail | rejected |
| shared-method guard omitted | `run_d653e11cc58f4928` | regression and hidden accessor-divergence fail | rejected |
| stale shared current value | `run_ba0d5de8cd66404e` | regression and hidden invalidation fail | rejected |
| forbidden test edit | `run_21905bc5bce74b3e` | hidden, scope and test-tampering fail | rejected |

The base checkout passed all 94 upstream reactive regressions, with seven
skips, while failing the private ten-check oracle. Four
semantic partials also preserved the visible suite but failed hidden
acceptance; the other four failed both regression and hidden checks. The
independent oracle binds submitted imports to `/workspace` and covers
synchronous, coroutine and generator fan-out, nested sharing, independent
graphs, repeated invalidation, property and method accessors, consumer
isolation, and source error recovery. The
[Param reactive fan-out research admission report](../reports/docker-gate/research-param-shared-rx-fanout-cache.json)
records every patch, manifest, result and provenance hash from clean harness
commit `4d73605a...`. This gate made zero model/API calls. All runs enforced
network denial and a read-only submitted workspace; the image has no configured
user and therefore ran as Docker's default root user.

## Thirteenth research task admission

`hf-hub-custom-tqdm-class-contract` comes from SWE-rebench leaderboard instance
`huggingface__huggingface_hub-4056`, Hugging Face Hub issue #4050 and PR #4056.
It is the third hard `core-same-repo` held-out task, pinned to base
`6983a4d3d2bdcbd09c6ea08acae64cdf83ccb2e4` and evaluator image
`sha256:cbfae263dff792cc7c763057905869c548bf37733352ff999b3d7d4278c87677`.
PatchLoop keeps the exact two-file accepted production patch and excludes the
benchmark test patch. Contamination risk remains high because the public issue,
patch and localization are available upstream.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_91a8053743aa45ce`, `run_8b0127ad2395461b`, `run_006387b2578e4ae6` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_ec70609f8e1248e6` | regression pass, hidden fail | rejected |
| combined foreign-only policy | `run_16d062dbc74f4a01` | hidden snapshot-HF-policy fail | rejected |
| file context only | `run_53188d82a1014206` | hidden snapshot path fail | rejected |
| exact HF class only | `run_479fb08d999645f3` | hidden HF-subclass fail | rejected |
| force custom `disable=False` | `run_4816ec4e8aa04ef4` | hidden constructor-ownership fail | rejected |
| drop all HF policy | `run_6e2a878491334888` | hidden HF group/log fail | rejected |
| snapshot path only | `run_d14dd4bad8e9406f` | hidden file path fail | rejected |
| strip only `name` | `run_5068ed072e8744ca` | hidden `disable` ownership fail | rejected |
| unguarded `issubclass` | `run_79d02f9f0ad84027` | hidden callable/partial fail | rejected |
| treat every upstream subclass as HF | `run_8d432cc577e34d66` | hidden foreign-subclass fail | rejected |
| forbidden test edit | `run_10f9c5a6702c4be2` | hidden, scope and test-tampering fail | rejected |

The base passed all 17 tests present in the frozen upstream file and failed nine
of 15 hidden cases. The benchmark declares 19 P2P nodes because its excluded
test patch introduces two extra nodes that already pass on the base; the
executed and declared counts are not conflated. The oracle binds imports to
`/workspace` and exercises strict custom classes, a foreign upstream-tqdm
subclass, function and partial factories, existing bars, fully mocked file and
snapshot downloads, aggregation, and HF subclass group/log/TQDM_POSITION policy.

Adversarial review before the clean commit combined two individually rejected
partials and demonstrated an actual false positive in the original 11-case
oracle: the shared file context was correct, but snapshot construction discarded
HF-owned policy. PatchLoop added snapshot callable and HF-policy observations,
retained the escaping union as a known-bad patch, and reran the full matrix from
clean commit `962668e8...`. The
[Hugging Face progress-policy admission report](../reports/docker-gate/research-hf-hub-custom-tqdm-class-contract.json)
binds all 14 run manifests, results, provenance records and patch hashes. The
gate made zero model/API calls and used a network-disabled, read-only submitted
workspace. The image has no configured user and ran as Docker's default root
user.

## Fourteenth research task admission

`mtplx-mixed-content-tool-call-stream` comes from SWE-rebench leaderboard
instance `youssofal__mtplx-21`, MTPLX issue #20 and PR #21. It is the third hard
`core-cross-repo` held-out task, pinned to base commit
`c06cc13286e86d9ff3d2e3b991eba327549c534b` and evaluator image
`sha256:32510a901064f5d405f3d4313a4556d924c94e72b2b0993296a43f04de83370e`.
The accepted source patch fixes mixed preamble handling but also matches
lookalike marker stems and can silently discard non-whitespace residue. PatchLoop
therefore retains it as a known-bad and uses a one-file hardened reference with
an exact `<tool_call>` delimiter and stream-local residue enforcement.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened reference | `run_236767f9815b41e9`, `run_1e751bd099b44d82`, `run_647176898cdb411e` | full success ×3 | 3/3 success, `official=true` |
| no-op | `run_9a04e61629c74a27` | regression pass, hidden fail | rejected |
| content lock removed only | `run_7e3a2597aa464ab3` | mixed-stream state fail | rejected |
| chunk-start marker only | `run_c8402fc708b043ec` | arbitrary chunk-boundary fail | rejected |
| current-chunk search only | `run_58f5c4143d9b43e4` | cross-chunk marker fail | rejected |
| initial-buffer search, preamble dropped | `run_4b088912a14741a1` | preamble preservation fail | rejected |
| case-sensitive scan | `run_54eb40b2aa2b4ad1` | mixed-case marker fail | rejected |
| no partial-tail retention | `run_75d42a5562464f21` | marker split fail | rejected |
| one-character tail only | `run_8977994330c94642` | longer marker prefix fail | rejected |
| trailing policy relaxed | `run_b564f13cb67146e2` | residue rejection fail | rejected |
| exact accepted upstream source patch | `run_7a98e3bcbf5c4e17` | delimiter and residue hardening fail | rejected |
| forbidden test edit | `run_89f4d3e5fd28425a` | hidden, scope and test-tampering fail | rejected |

The base/no-op run passed all 55 registered CPU/mock regressions and failed the
21-case independent oracle. Three collected session tests are explicitly
deselected because the benchmark image lacks the MLX runtime. All official runs
used a network-disabled, read-only submitted workspace and made zero model/API
calls. The image has no configured user and ran as Docker's default root user.

The first clean-gate attempt exposed that a normal clone did not advertise the
frozen base tree. PatchLoop now validates a lowercase 40-hex revision and, only
after checkout failure, fetches that exact SHA into `FETCH_HEAD`, rechecks a
detached `HEAD`, and rejects unavailable or mismatched revisions. Success,
invalid-SHA and fetch-failure tests cover this path. The official matrix was then
run from clean harness commit `82a0c23b...`. The
[MTPLX streaming admission report](../reports/docker-gate/research-mtplx-mixed-content-tool-call-stream.json)
binds all 14 patch, manifest, result and provenance hashes.

## Fifteenth research task admission

`fusesoc-retained-parse-error-diagnostics` comes from SWE-rebench leaderboard
instance `olofk__fusesoc-776_interface`, FuseSoC issue #761 and PR #776. It is
the fourth hard `core-cross-repo` held-out task, pinned to base commit
`d2e6e720222f57cb66d6c303a326d336c582aade` and evaluator image
`sha256:1e971791d4ce192eae296747d46dff477cb2ce2c47e08b2ed9d0108ee5a85ad9`.
The exact three-file production reference retains every parse failure while
continuing valid-core discovery, forwards the current list through `Fusesoc`
and appends every path and parser message to the existing missing-core
diagnostic.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_1930d4d388214a39`, `run_ecc6b25d878941dd`, `run_41a5e6e0c3a9460f` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_27a35b3567fc4b75` | visible pass, hidden fail | rejected |
| manager-only retention | `run_fd337d9d5db34b19` | wrapper/CLI fail | rejected |
| wrapper-only exposure | `run_058153b57a3f4135` | manager retention fail | rejected |
| missing CLI propagation | `run_7e8f97cfc9e44546` | final diagnostic fail | rejected |
| last error only | `run_1b70b4fca4ad411c` | accumulation fail | rejected |
| class-shared errors | `run_a55d1e200c5e4163` | instance isolation fail | rejected |
| hard stop on parse error | `run_6df53dc5f3fe4326` | valid-core continuation fail | rejected |
| import errors misclassified | `run_b5bf8f2a76794047` | non-parse handling fail | rejected |
| CLI first error only | `run_e150bdb76e554d24` | complete diagnostic fail | rejected |
| forbidden test edit | `run_03d995290fee481d` | hidden, scope and test-tampering fail | rejected |

The visible file collects 14 base tests. The network-dependent `test_export`
and the lockfile-writing `test_lockfile_no_file_create` are explicitly
deselected under the network-none, read-only boundary; the remaining 12 pass
with the image's testbed environment on `PATH`. The independent ten-case
oracle binds all three production imports to `/workspace` and checks
multi-error accumulation, valid-core continuation, instance isolation, live
wrapper forwarding, complete CLI diagnostics and unchanged `ImportError`
handling. Base/no-op and all eight semantic partials failed hidden acceptance
only; the forbidden edit additionally failed scope and tampering.

All 13 official cases ran from clean harness staging commit
`da3105d30f0c7eb6fec65650200aedac7eb12b13` with Docker networking disabled
and read-only root and submitted filesystems. The image has no configured
`User` and ran as Docker's default root user. The public task hash is
`sha256:2dd38ab34abc7ab53c0487c2d5b19dbda5b303fe2d04bf04474cc5bafef6ba31`
and the private task hash is
`sha256:e5db4a13d05518abd3a2be50c99ed8aa9536168896c27f52a4947c6773e7b66d`.
The [FuseSoC diagnostic admission report](../reports/docker-gate/research-fusesoc-retained-parse-error-diagnostics.json)
binds the run manifests, results, provenance records and patch hashes. Its
SHA-256 is
`cef87dda16402d874b28264fcbed5bba2acf07736800c5fd297d812112081918`.

## Sixteenth research task admission

`tox-dotted-version-factor-base-python` comes from SWE-rebench leaderboard
instance `tox-dev__tox-3846`, tox issue #3845 and PR #3846, plus follow-up
regression issue #3850 and PR #3851. It is the fourth hard
`core-same-repo` held-out task, pinned to base commit
`ae05f2a33ccfe52ff22ac578ec6c8eb9f750ce4a` and evaluator image
`sha256:269a32558d3aeac5f9e9b6fc451302667b83a85f260f0b915babe1838b50b3bc`.
The benchmark patch recognizes bare `2.N` and `3.N` factors inside compound
environment names. Its accepted release immediately regressed names containing
multiple Python-like factors because extraction raised before
`ignore_base_python_conflict` could apply. PatchLoop therefore combines the
accepted #3846 grammar and #3851 conflict-policy production changes as its
hardened reference and retains each PR in isolation as a known-bad partial.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| hardened #3846 + #3851 reference | `run_41553bac68ee4214`, `run_6917e86f2f2a4a20`, `run_0fd0206fb8144eb9` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_4bd98e35f36c4fe7` | visible pass, hidden fail | rejected |
| exact #3846 only | `run_a64d4e9fd59c4f6f` | follow-up conflict policy fail | rejected |
| exact #3851 only | `run_a4d76dfa461c420e` | dotted-factor grammar fail | rejected |
| major restriction only | `run_cf5d23ef8f1047e4` | compound factor fail | rejected |
| explicit factors only | `run_2ffd9b9ee3ad4931` | classic-factor regression | regression and hidden fail |
| first match wins | `run_0274332691db4949` | ambiguity detection fail | regression and hidden fail |
| ignore all validation conflicts | `run_b17cf94c4e404256` | older single-factor contract fail | regression and hidden fail |
| default-only ignore handling | `run_8b68477a7bc542dc` | validation path fail | rejected |
| validation-only ignore handling | `run_0499c984ec814e1c` | default path fail | rejected |
| threaded suffix stripped | `run_60fb1826103d45bf` | free-threaded factor fail | rejected |
| dotted major range too broad | `run_7d153b8ec0e44c95` | non-Python major guard fail | regression and hidden fail |
| forbidden test edit | `run_4efaa4b1bbe549f6` | hidden, scope and test-tampering fail | rejected |

The private oracle collects 17 cases from eight functions and binds the Python
API to submitted source. It covers compound factor positions, free-threaded
suffixes, classic factors, whole-name CPython/PyPy normalization, rejection of
major versions 4 and above, ambiguity diagnostics, both ignore-policy entry
points and the older single-factor override contract. It deliberately does not
require compound `qa-pypy-3.10`, which the accepted grammar splits into two
recognized factors.

The registered visible check covers 101 of 110 declared P2P nodes. Nine
deterministic environment-incompatible nodes are deselected; because one pytest
node prefix also removes two healthy siblings, those exact cases run in a
second invocation. The observed total is therefore 99 + 2 passing cases.

All 15 official runs came from clean harness commit
`678d30a50ae27cb48623c1fbe5bc04bb65d34bad`. The
[tox dotted-factor admission report](../reports/docker-gate/research-tox-dotted-version-factor-base-python.json)
binds patch, manifest, result and provenance hashes and has SHA-256
`sha256:216ccfd1f9017ca499c9902ac857a2e6d4ebc0dca1aeb1aff04e9af396485fe6`.
The gate made zero model/API calls and is deterministic
evaluator evidence, not live-model agent performance or a core campaign result.
The external image has no configured `User` and ran as Docker's default root
user under the network-disabled, read-only evaluator boundary.

## Seventeenth research task admission

`dagster-subset-partition-definition-selection` comes from SWE-rebench
leaderboard instance `dagster-io__dagster-33605`, Dagster issue #33584 and
PR #33605. It is the fifth hard `core-cross-repo` held-out task, pinned to
base commit `f8430dc7bf76bfab4f026165e5c5f821104298df` and evaluator image
`sha256:98a0b69301022cba2ac7520a8ab1891c2a490cf4ec4ba889d6ce36a29f40831b`.
The exact two-file production reference makes the `AssetsDefinition`
partition result depend on selected asset and asset-check keys, then delegates
the execution context to that selection-aware property.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_1927909d6cd241e7`, `run_bd7f5b11e51d4202`, `run_c66f90c1fc4242cc` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_2a20d874bedf450b` | 28 visible pass, hidden fail | rejected |
| always unpartitioned | `run_d8c2b3eb40814ba8` | selected partition and visible regression fail | regression and hidden fail |
| assets definition only | `run_7ea661da98c748f2` | execution-context delegation fail | rejected |
| check asset-key filter | `run_fb0bd8300f514af9` | selected check-key semantics fail | rejected |
| execution context only | `run_2682f33ade874bd9` | selection-aware definition fail | rejected |
| first selected definition | `run_2204c73911354106` | incompatible-definition conflict fail | rejected |
| selected assets only | `run_91a3c33dfdbc4958` | selected check partition fail | rejected |
| selected checks only | `run_55ba57333f1740ec` | selected asset partition fail | rejected |
| unfiltered check specs | `run_2a7f765456c44ab0` | unselected check isolation fail | rejected |
| forbidden test edit | `run_2b6c0ba491ee4d86` | hidden, scope and test-tampering fail | rejected |

The complete base-resident visible module passed all 28 declared P2P nodes on
each reference run. The independently authored private oracle contains nine
tests covering selected and unselected assets and checks, compatible
deduplication, real conflicts and execution-context delegation. The
`task-private-v2` spec binds the hidden artifact by content hash. Visible tests
and the hidden oracle remain on read-only mounts; each check copies only the
submitted Dagster production package into a fresh writable `/tmp` import root
and asserts submitted-source binding. Base/no-op and all eight semantic
partials were rejected, and the forbidden edit additionally failed scope and
test-tampering enforcement.

All 13 official cases ran from clean harness staging commit
`26f28cf11d53f3b0e17b2a4663d0ce68afe63b27` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[Dagster partition-selection admission report](../reports/docker-gate/research-dagster-subset-partition-definition-selection.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:2d95aa36990b8cd475476a0992b0db7a8d9259d5c7a21d35c99ea3a6c551d012`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Eighteenth research task admission

`kubeflow-exit-handler-after-dependencies` comes from SWE-rebench leaderboard
instance `kubeflow__pipelines-13112`, Kubeflow Pipelines issue #10722 and
PR #13112. It is the sixth hard `core-cross-repo` held-out task, pinned to
base commit `98f5b7a300ee52d6c530b429558b718ade9fdb7a` and evaluator image
`sha256:842b24c98e1b2c1145b8826b90a95e0634a3520cd523b3d3ae6940201ec2e79a`.
The exact two-file production reference broadens the public
`PipelineTask.after` contract to supported `ExitHandler` groups and makes the
compiler distinguish task, group, missing and ambiguous dependency names.
The benchmark test patch remains evaluator-only.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_7876f396980a4c55`, `run_e2930e730d104a3c`, `run_f4c2707cc64e4a63` | full success ×3 | 3/3 success, `official=true` |
| base/no-op | `run_28d458248adb4cca` | 277 visible pass, hidden fail | rejected |
| compiler resolution only | `run_9c0ab4f5a208424a` | public validation fail | rejected |
| accept any task group | `run_fb281c4593234662` | non-exit group rejection fail | rejected |
| retain only first dependency | `run_f4445927f042437d` | mixed dependency preservation fail | regression and hidden fail |
| group-only resolution | `run_61a35efc95b34a2a` | ordinary task dependency fail | regression and hidden fail |
| public validation only | `run_030d1c1ffa3c4e0b` | compiler group resolution fail | rejected |
| resolve group as exit task | `run_a3d0b17e1e624efe` | group boundary and final-status fail | rejected |
| prefer task on collision | `run_9b25341374b54dfe` | ambiguous-name rejection fail | rejected |
| leak unknown-name key error | `run_d48f210c19244f82` | clear missing dependency error fail | rejected |
| forbidden test edit | `run_2da8391ec73948e4` | hidden, scope and test-tampering fail | rejected |

The complete base-resident `compiler_test.py` and `pipeline_task_test.py`
surface passed 277 tests plus 15 subtests on each reference run. The frozen
benchmark declares 278 P2P nodes because its test patch adds one preservation
P2P test; after excluding that evaluator-only addition, the base-resident P2P
declaration is exactly 277. The same patch adds all seven F2P tests.

The independently authored private oracle contains 11 tests covering
submitted-source binding and ten semantic boundaries: single, mixed and
chained group dependencies; unsupported and arbitrary inputs; missing and
ambiguous names; nested-context rejection; and final-status attribution. The
`task-private-v2` spec binds the oracle by content hash. Visible tests and the
hidden oracle remain on read-only mounts while each check copies only the
submitted KFP production package into a fresh writable `/tmp` import root.

All 13 official cases ran from clean harness staging commit
`5e7b019e60b4d76f67e48bafe6fd1a3b309fe313` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[Kubeflow ExitHandler admission report](../reports/docker-gate/research-kubeflow-exit-handler-after-dependencies.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:c7998d064949dd5a67f05c15ff7d426ef1051f74fea7bb03e37f91c7d1d5084c`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Nineteenth research task admission

`loguru-post-2038-local-timezone-fallback` comes from the frozen SWE-rebench
leaderboard aggregate `test` row 209, instance `Delgan__loguru-1297`, Loguru
issue #1291 and PR #1297. It is the fifth hard `core-same-repo` held-out task,
pinned to base commit `e310e2029102b5d63a679a2b64501c045aa86336` and
evaluator image
`sha256:8d899d1147cf88bc088afe57fc5299fdcf2fafe6a1e30ef26825577e8953362f`.
The reference is the exact accepted `loguru/_datetime.py` production hunk;
the benchmark changelog hunk and test patch remain evaluator-only.

| Patch | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference | `run_76b8e870024a49ec`, `run_44fcae6e680445ed`, `run_f3de06b5c7d24af7` | full success ×3 | 3/3 success, `official=true` |
| equivalent `utcfromtimestamp` solution | `run_9c5e228c646442a3` | implementation-independent full success | accepted |
| base/no-op | `run_5643e3746f804cb7` | 43 visible pass, hidden fail | rejected |
| always use fallback | `run_cc840d2e13634aa3` | valid platform metadata preservation fail | regression and hidden fail |
| catch all local-time exceptions | `run_cb02eb1400664bb8` | unsupported exception propagation fail | rejected |
| clamp invalid offset | `run_1d2ab550b6824215` | derived offset fail | rejected |
| fixed derived-looking fallback | `run_c6e7472411484011` | multi-profile derivation fail | rejected |
| reverse fallback offset | `run_197650ce0f014d54` | offset direction fail | rejected |
| discard fallback zone | `run_40744cf912f047ce` | zone-name preservation fail | rejected |
| use UTC on invalid offset | `run_2b1157c21b434842` | local offset derivation fail | rejected |
| catch wrong local-time errors | `run_18d9696bbefb454f` | supported range-error recovery fail | rejected |
| catch wrong timezone error | `run_9ca3c4bc27184551` | invalid offset recovery fail | rejected |
| forbidden test edit | `run_c3e433e0ac98456f` | hidden, scope and test-tampering fail | rejected |

Every reference run passed all 43 base-resident `test_datetime.py` cases and
all 11 independently authored hidden cases. The frozen benchmark separately
declares 34 P2P and four F2P nodes; the executed full base test module and
declared benchmark subsets are reported without conflating their counts.

The hidden oracle collects 11 subprocess cases across five test functions.
It preserves valid negative, zero and positive platform offsets; exercises
invalid offsets, supported range errors and each missing-field boundary; and
propagates an unsupported `RuntimeError`. Positive, negative and date-rollover
fallback profiles use different offsets and zone names while keeping wall
time, UTC conversion and timestamp internally consistent. The clock double
supports valid `now(tz=...)`, `utcfromtimestamp()`, `astimezone()` and
`combine()` paths; the positive equivalent run proves the oracle is not tied
to the accepted reference's exact conversion call. The `task-private-v2` spec
binds the oracle by content hash, and both visible and hidden tests remain on
read-only mounts while submitted production source is copied to a fresh
writable import root.

All 15 official cases ran from clean harness staging commit
`8c5084eee3a44a44e207345950a9ffb45b23e4b1` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[Loguru timezone-fallback admission report](../reports/docker-gate/research-loguru-post-2038-local-timezone-fallback.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:044655debc7255549e8ba49cdfc339c6a0d04f2fdab3b983017efcbc7c38ffbc`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Twentieth research task admission

`pyfakefs-file-wrapper-io-capabilities` comes from the frozen SWE-rebench
leaderboard aggregate `test` row 653, instance `pytest-dev__pyfakefs-1269`,
pyfakefs issue #1265 and PR #1269. It is the sixth, medium
`core-same-repo` held-out task, paired one-to-one with the pyfakefs
memory-development task while using a distinct base, production file, failure
pattern and solution lineage.

| Patch group | Run | Expected boundary | Observed |
| --- | --- | --- | --- |
| exact production reference ×3 | `run_b9902d125f9a4a9e`, `run_41bba6a0e480483c`, `run_d0a0277614f04b49` | full success | 3/3 success, `official=true` |
| dynamic-interface equivalent | `run_1bf5034e9a2a48fb` | implementation-independent full success | accepted |
| base/no-op | `run_6b26a5042d6048dc` | visible pass, hidden fail | rejected |
| nine semantic partials | nine content-addressed runs in the report | capability and guard boundaries | all rejected |
| forbidden test edit | `run_722a1d4381a74127` | hidden, scope and tampering fail | rejected by all three |

Each reference and equivalent run passed 431 visible tests with 161 skips
(592 collected) and all 29 independently authored hidden cases. Base/no-op
preserved the same visible result but failed 12 hidden boundary cases. The
semantic corpus covers constant, mirrored, inverted, primary-mode-only and
backing-buffer capability answers; missing callable methods; and methods that
do not control internal guards.

All 15 official cases ran from clean harness staging commit
`b50b4314aa7fd209737db46f15b38aee056bbd80` with Docker networking disabled
and read-only root and submitted filesystems. The external image has no
configured `User` and ran as Docker's default root user. The
[pyfakefs capability admission report](../reports/docker-gate/research-pyfakefs-file-wrapper-io-capabilities.json)
binds every patch, manifest, result and provenance hash and has SHA-256
`sha256:49f92f1ceab905d086d23820f0af581706ffaa8bd3e923d4cc972cac914e252e`.
The gate made zero model/API calls and is deterministic evaluator admission
evidence, not live-model agent performance, memory improvement or a core
campaign result.

## Recovery evidence

Both automated E2E and a CLI-derived run were exercised. The run was suspended immediately after the
durable patch checkpoint, resumed, reached the hidden evaluator and retained exactly one `PatchApplied`
event. Checkpoint/worktree hash corruption is separately rejected by test.

## Dataset freeze evidence

`patchloop dataset audit` completed successfully with `complete=true`, `research_ready=true`,
`stress_ready=true`, `freeze_eligible=true`, no errors and no freeze blockers. The frozen manifest
contains five calibration fixtures and 20 admitted research tasks and has SHA-256
`sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`.

The `public-contract-structure-v1` selector used no private oracle, reference patch or model result.
It selected:

| Archetype | Task |
| --- | --- |
| widest allowed change surface | `fusesoc-retained-parse-error-diagnostics` |
| narrowest remaining mutation surface | `anyio-extensionless-entrypoint-worker-main` |
| longest remaining registered visible check | `pyfakefs-file-wrapper-io-capabilities` |

The frozen schedule has SHA-256
`sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`.
It deterministically expands to 30 derived stress rows: context reset and worker restart each use
persistent-state on/off arms with two repetitions per task, and synthetic test timeout uses the
on arm with two repetitions per task. The baseline source is the core no-memory lane, and all stress
rows are excluded from core metrics. This is schedule-registration evidence only; no stress row or
live-model request was executed by this gate.

## First paid live-pilot evidence

On 2026-07-28, the approved Babel #1042 development-validation execution hash
`sha256:e078a32eff4ab1b0a7c02a7aca6c97115e968bb57bb9e618b42d69fa943f6513`
reached `ready=true` on clean harness commit
`636d0cf973203f2e0521fe41ec4675562c34ccbd` and ran exactly one schedule row.
Run `run_c6f13dd9a1a1472d` persisted 113 monotonic events, 23 checkpoints, the approved plan,
hash-chained campaign journal, terminal result and immutable qualification artifact.

The attempt cost `$0.34025875`: 73,730 input tokens, 73,670 cache-write input tokens and 7,326
output tokens across 20 model and 22 tool calls. All eight failed mutations used an OpenAI-style
`*** Begin Patch` envelope while the constrained gateway accepted only raw Git unified diff.
The next-turn context exposed only `CONTRACT_ERROR`, not the actionable `git apply` error, so the
agent repeated the rejected mutation until the total-token budget was exceeded. No submitted patch
or evaluator verdict exists.

The immutable qualification artifact is `qualified=false`. Its only failed deterministic check was
the original public/private scan: all 41 matches were false positives already disclosed in the
public contract—20 `.patchloop-hidden` forbidden-path markers and 21 occurrences of the hidden-check
name embedded in the public task ID. A separate forensic count found zero API-key, reference-hash,
`private.yaml` or `reference.patch` matches. The historical trace and qualification are retained
unchanged; corrected tool feedback and scanner logic require a fresh commit, execution hash,
preflight and explicit paid approval.

For diagnosis only, the first rejected model candidate was converted from its marker envelope to a
raw Git diff without changing the proposed one-line code edit. The resulting patch has SHA-256
`sha256:4c49b6edd0603f2e56c04c18e83fdecb3a6a5868ab40bffca198504951b01606`
and diff hash
`sha256:5992cb41eb18d9924dcea456fead9bc414489500b88b9371114bdfcf1f8ef743`.
Official Docker evaluator run `run_4299e6b326de4c1c` passed hidden acceptance, all registered
number regressions, scope, dependency, test-tampering and public-API policy in 4,078 ms with zero
model calls. This format-only counterfactual isolates the gateway grammar as the immediate failure
cause; it is not an agent submission or a pilot success. The checked-in
[live-pilot evidence record](../reports/live-pilot/dev-validation-live-pilot-20260728.json)
binds the local raw files, immutable qualification and diagnostic evaluator result by SHA-256.

## Second paid live-pilot and recount evidence

After the r1 tool feedback, leakage filtering, execution ownership and source-evidence fixes were
committed, execution hash
`sha256:c7fe89287ed3310885f548954917c810b699a54ea420b3a7551d9863ebd839a3`
was separately approved for exactly one r2 row with a $2 cap. The run used clean harness commit
`34673def916401efb97bb4bd02dec9dd927db36e` and produced
`run_de8f2a2846044c01`. It cost `$0.328036875`: 74,868 input tokens, 74,811
cache-write input tokens and 6,274 output tokens across 19 model and 22 tool calls. Cumulative
r1+r2 spend is `$0.668295625`.

The r2 run preserved 111 monotonic events and 23 checkpoints with zero infrastructure or
qualification errors. Its immutable `trace-qualification-v1` artifact is `qualified=true`:
trace integrity and leakage passed, private match count was zero, usage reconciled and the
source-evidence hash is
`sha256:84079a25b6b3cdc84df440e8e5a943aaa462eafb161b1fc487f221cc97f0b451`.
This does **not** mean the pilot passed its acceptance gate. No submitted patch or evaluator verdict
exists and `evaluation_reached=false`; at that checkpoint the development-campaign consumer
rejected this run and the first 12-run campaign remained locked. Later primary r2 evidence and the
subsequent campaign are documented in D-048 above.

The model emitted nine `apply_patch` candidates, seven of them byte-distinct. Eight reached the
gateway and all eight failed with `corrupt patch`; the ninth was produced in the response that
crossed the token budget before tool execution. Every candidate declared seven old and seven new
lines in its hunk header while its body contained six old and six new lines. The candidates changed
line offsets and code variants in response to visible errors, but never repaired this manual count.
Model event 51 proposed the same tuple-membership code edit as the r1 official-passing
counterfactual. Its exact raw patch has SHA-256
`sha256:f041469f1d938452c6e25c54aa1e6b816247be0525920184a77be493f7111695`.
Strict `git apply --check` rejects that file; `git apply --check --recount` accepts it and leaves the
workspace unchanged. This is parser/interoperability evidence, not an agent submission, evaluator
result, pilot success or repetition.

The corrective contract applies `--recount` only to the agent-visible forward apply and the reverse
rollback of the same raw patch. The raw input/hash, hunk body, context, path and deterministic
policies remain unchanged, and hidden evaluator application stays strict. Policy rejection must
restore the exact pre-call diff hash. Reverse failure, restoration mismatch or untracked agent
workspace state is a recovery error; new-file, rename/copy, binary and metadata-only patches remain
rejected. Regression tests cover the r2-style 7/7-versus-6/6 patch, non-empty baseline rollback,
same-action replay without duplicate `PatchApplied`, untracked/recovery guards and fail-closed
rollback. The checked-in
[r2 evidence record](../reports/live-pilot/dev-validation-live-pilot-20260728-r2.json)
and [portable candidate](../reports/live-pilot/artifacts/run_de8f2a2846044c01-recount-candidate.patch)
preserve this claims boundary. The r2 record intentionally stops before the separately approved r3
execution.

The corrective worktree collected 306 tests: 304 passed in the restricted test environment and the
two Docker-only sandbox tests were skipped because that environment could not see the daemon.
Running `tests/test_sandbox.py` on the host with a repository-local ignored pytest temp directory
passed all nine tests, including the two Docker isolation checks. Full Ruff and `git diff --check`
also passed. These are harness regression results, not live-model task evidence.

## Third paid live-pilot and accepted gate

The r3 harness correction was committed at
`eeeeba6aa68e9d58677e2d8218381f79285f5545`. Execution hash
`sha256:03c57fb3dd0182e63645e346311ee2a46c1284d9770857240b2011b666b8bde6`
was approved for one Babel #1042 row with a $2 cap and was consumed exactly once. Experiment
`dev-validation-live-pilot-20260728-r3` completed without retry, infrastructure error,
qualification error or not-started row. Run `run_3cb86f8d70094a11` cost `$0.16056875`:
43,963 input, 43,930 cache-write input and 1,547 output tokens across 11 model and 13 tool calls.
The measured cumulative r1+r2+r3 spend is `$0.828864375`.

The agent-visible gateway accepted one raw model patch with hash
`sha256:b17fefa202127323a1eae6a95c9d9dca0a60d2cb8ac8c138c2722c1fb0c2f333`.
Its hunk declared 7/7 lines around a 6/6 body, so this is direct provider evidence that the scoped
recount compatibility path worked. The resulting Git diff and official evaluator submission both
hash to
`sha256:5992cb41eb18d9924dcea456fead9bc414489500b88b9371114bdfcf1f8ef743`.
It changes one line in `babel/numbers.py`. Hidden acceptance, registered regression, scope,
dependency, test-tampering and public-API checks all passed; the persisted result records
`official=true`, `scope_compliant_success=true` and `outcome_kind=resolved`.

The trace contains 72 contiguous events, 15 checkpoints, exactly one `PatchApplied`, no tool
failure and one terminal `RunCompleted`. Qualification independently reconciled the 11 model and
13 tool calls, found zero private matches, verified the approved plan and Docker provenance and
recorded `qualified=true`, `evaluation_reached=true`. Its qualification hash is
`sha256:5bc11b4087061921a415d94caeb0ac8370e39013f1d94a531130256fd3101811`;
recalculation of the current plan/manifest/events/checkpoints/result/artifact inventory matches the
recorded source evidence hash
`sha256:f4726a1d6c2abfdf859c92135ae345dffb2075aaa9d5a7f0fc4fb7b1b0259322`.
The four-row campaign journal hash chain and qualification hash were also recomputed from their
serialized content. One campaign-file portability defect was found during this audit: the r3
`CampaignCompleted.result_hash`
`sha256:d9214929019e839a46715c55326f8725dc005d844fdc1e97ad50bb2bf2736f8d`
hashes the intended LF serialization, while Windows `Path.write_text` persisted CRLF bytes with
hash
`sha256:ccc8d50f9f47c72ce56f6192558f9c6790ff24cb4a2aea5ee39d779bda4e1664`.
Normalizing those exact bytes to LF reproduces the journal value. The raw result and journal remain
unchanged; future runs write the exact bytes that were hashed. This defect does not alter the
model response, evaluator verdict or qualification, whose `source_evidence_hash` separately
includes the raw persisted run result.

The checked-in
[r3 evidence record](../reports/live-pilot/dev-validation-live-pilot-20260728-r3.json),
[raw applied model patch](../reports/live-pilot/artifacts/run_3cb86f8d70094a11-applied-model-candidate.patch)
and [final submitted patch](../reports/live-pilot/artifacts/run_3cb86f8d70094a11-submitted.patch)
separate the provider tool argument from the final evaluator input and bind the ignored raw
artifacts by SHA-256. This is an accepted single-task live pilot. It unlocked the pilot prerequisite
under the then-current v1 contract, but it does not unlock the current tool-v2/context-v5 pilot
gate. The later separately approved v4 primary mini pilot unlocked only the already-consumed v4
campaign; a new accepted v5 pilot is still required. Neither single-task pilot is a 12-run result or
evidence that memory improves performance.

## Mini model-candidate r1/r2 evidence

D-031 prompt-token telemetry was exercised in a separate model-candidate lane that cannot satisfy
the current primary campaign prerequisite. Terminal r1 `run_d4fea5e7198b4abc` used
`gpt-5.4-mini-2026-03-17`, medium effort and a 90,000-token run budget. It preserved exact
request-count telemetry but ended before evaluation when legacy text `DONE` attempted an invalid
phase transition. The run cost a calculated `$0.07745325` and remains an immutable agent failure.

The corrected v2 suite was committed at
`ff33d18a520de6fd8949ce9d873e26241b4382ae`. Its exact execution hash
`sha256:fc2649790241f9623ea259a05957a38d1063472a9f17998e9e489b5b3fad21ca`
was approved for one row with a $2 cap and consumed exactly once. Experiment
`dev-validation-gpt54mini-pilot-20260729-r2` completed 1/1 rows with no infrastructure,
qualification or not-started entry. Run `run_4a9737ec91964dca` used 58,695 input and 7,543
output tokens, including 6,501 reasoning tokens, across 10 model and 13 tool calls. Its calculated
list-price cost is `$0.07796475`; the actual invoice or shared-traffic incentive was not verified.

The v2 submission order was exercised end to end. One patch was applied at event 35, the
current-diff visible check passed at 55, a complete `get_diff` followed at 61, the model received
that diff at 64/65 and called `finish_task` at 66. Review, submission attempt, acceptance and DONE
were recorded at 67, 68, 70 and 71, with `finish_task` success at 69 and no later mutation. The
evaluator receipt binds the final
submitted diff
`sha256:6df7ac37bd5d31d5e5dc55bb20eb76fecb1941b694171ee8be80ee9af968c29e`
to the run manifest, result and provenance. The 74-event, 14-checkpoint trace passed all 22
`trace-qualification-v2` checks. Its qualification hash is
`sha256:88c763f2617d4b40c0f4c50229831d1dcdbf0477d7ae05aa99c4241538d10a43`;
recalculation of current durable evidence matches source hash
`sha256:468ff2df25cb24ef1152e32388b191b77fb529873dc8790155f3055a55503250`.
The four-row campaign journal hash chain and exact experiment-result byte hash also match.

This trace qualification is not task success. The official evaluator reported aggregate hidden
acceptance failure while regression, scope and safety passed, so
`scope_compliant_success=false` and `outcome_kind=task_failure`. The submitted change removed
grouping symbols before deciding whether the input differed only by trailing zeroes. That loses
the grouping/separator structure which the public task explicitly requires strict mode to
preserve. No private assertion, input or check identifier is included in the tracked evidence.

The first model patch attempt was rejected during preparation when a non-Git marker remained
after the diff; it never reached the evaluator.
On the following stateless request, PatchLoop preserved its content hash and structured error but
did not restore the 1,326-byte candidate body. With `store=false`, no previous provider response
and no agent-visible CAS-read tool, exact retry continuity was not guaranteed. The separately
submitted candidate contained the public-contract defect described above. This trace does not
prove that the missing body caused that defect or hidden failure, nor that the rejected candidate
would have passed. All ten input-token pre-counts exactly matched provider usage, every response
was completed with truncation disabled and no incomplete reason, so provider prompt truncation
was not observed. The PatchLoop context-selection gap remains distinct from API delivery integrity.

The checked-in
[mini r2 evidence record](../reports/live-pilot/dev-validation-gpt54mini-pilot-20260729-r2.json),
[applied model argument](../reports/live-pilot/artifacts/run_4a9737ec91964dca-applied-model-candidate.patch)
and [final submitted task-failure diff](../reports/live-pilot/artifacts/run_4a9737ec91964dca-submitted.patch)
bind the portable bytes and local-only evidence hashes without bundling provider payloads or
private evaluator output. At the r2 checkpoint, the mini lane's calculated cumulative cost was
`$0.155418` and all five paid pilot runs totaled `$0.984282375`. R2 validates telemetry, the normal
v2 submission path, evaluator
receipt and qualification, but it is not an accepted pilot and cannot unlock the primary
development campaign gate.

## 2026-07-29 D-037 rejected-patch retry continuity - offline evidence

New non-replay manifests use `tool_schema_version=v2` and
`context_policy_version=phase-evidence-v3`. A rejected model-originated `apply_patch` now stores
full candidate and result descriptors, revalidates both CAS objects and the canonical input hash,
and places exact candidate bytes/hash plus the structured rejection in the first next request.
The block expires after that model turn and is selected from the full event history rather than
the 12-event rendering window. Candidate bytes are never passed through semantic result
truncation.

The live-token guard counts that full request. If it and the complete response allowance exceed
the remaining run budget, it persists the request, appends `ModelGenerationBlocked` with
`generation_started=false`, and terminates with
`MODEL_GENERATION_BUDGET_EXCEEDED` without a second Responses generation call. Qualification v2
adds `rejected_patch_retry_context` only for v3 manifests and independently rehashes the candidate,
result and request. Missing/hash-only/wrong-reason/tampered/stale blocks fail; a v3 trace with no
rejection passes the conditional contract but does not satisfy the r3 diagnostic's exercise
requirement. The qualifier recomputes remaining budget from preceding model usage and binds the
complete block payload to both terminal `RunFailed` and `RunResult.terminal_error`; fabricated
remaining budget or terminal error identity fails. Historical phase-evidence-v2 qualification and
source evidence remain unchanged.

The terminal `experiments/dev-validation-gpt54mini-d037-r3.yaml` added a hash-bound
`experiment-diagnostic-v1` requirement without changing generic qualification. Its consumer stores
only sanitized counts/sequences and requires evaluator arrival, one or more retry episodes, exact
equality between observed and verified episode counts, and no failed source sequence. A zero-episode
qualified run that reached the evaluator is `TraceExerciseInconclusive`; evaluator non-arrival,
missing, duplicate, malformed or partially verified evidence is `TraceExerciseFailed`. Removing the
diagnostic block changes the execution hash and an old approval is rejected before runner or journal
construction. Report output keeps both states separate from `trace_qualification_failure`.

### D-037 r3 terminal provider evidence

Execution hash
`sha256:c33a50abe48b554c37d95de4833d1d17ede816f4d128b9adc22e88c010e138e6`
was consumed exactly once by `run_e90f7c52aa134182` at harness commit
`11a83c2cdff06978dc961e7b3b3c0caada3b386e`. The run used 8 model calls and
12 tool calls, all `search_files` or `read_file`. Its 57 events and 13 checkpoints contain no
`PatchPrepared`, `PatchApplied`, submission or evaluator event.

All eight request pre-counts matched provider input usage. Total usage was 54,851 input and
6,079 output tokens, including 5,535 reasoning tokens, for 60,930/90,000 tokens and a calculated
list-price cost of `$0.06849375`. At model event 55, requested and reported input were both 6,943.
The response then used exactly 4,096 output tokens, of which 3,989 were reasoning tokens, and
returned `status=incomplete`, `reason=max_output_tokens` with no complete tool call. This is
per-call output-ceiling evidence, not provider input truncation or total run-budget exhaustion.

Trace qualification passed 21 of 22 checks. Leakage and all aggregate private-boundary checks
passed; `prompt_token_integrity` failed at event 55 because the response was incomplete.
`evaluation_reached=false`. The conditional D-037 feature itself reported zero rejected
candidates, zero retry episodes, zero verified episodes and no failed source sequence. The suite
diagnostic is therefore `failed/qualification_not_passed`, not `inconclusive`. The run neither
validates nor falsifies rejected-patch rehydration and cannot unlock the primary development
campaign gate.

The checked-in
[mini D-037 r3 evidence record](../reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r3.json)
binds the experiment result, journal, approved plan, qualification, manifest, result, provenance,
failure record and terminal request/response objects by SHA-256 without bundling raw provider or
private evaluator payloads. Through r3, the three mini runs totaled `$0.22391175` and the six paid
pilots totaled `$1.052776125` at configured list prices. The r4 section below supersedes these
cumulative totals. Invoice charges and free daily usage treatment remain unverified.

### D-037 r4 corrective contract and terminal provider evidence

`experiments/dev-validation-gpt54mini-d037-r4.yaml` keeps the dated
mini snapshot, medium/default settings, task, condition, repetition and $2 cap fixed, while binding
`max_output_tokens=25,000` and `max_total_tokens=120,000` together under
`d037-rejected-patch-retry-v2`. The pair follows the initial reasoning/output-space recommendation
in the official
[reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning)
and remains below the
[model snapshot's published maximum output](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
Partial 4,096/120,000 or 25,000/90,000 contracts are rejected; historical mini and Terra contracts
remain accepted for their immutable evidence. Post-run qualification reparses and rehashes the
complete canonical approved-plan suite and compares its diagnostic/model/output/budget contract
with the run manifest. It also rehashes the raw schedule and recomputes the execution hash from the
suite, dataset, tasks, Git commit, Docker images, SDK state and pilot-qualification hash. Profile
omission, v1 substitution, partial pairs, arbitrary copied hashes and input tampering fail.

The preflight reserves `$0.6525` at the largest configured token price for one run, below the $2
cap. This is a conservative authorization reserve, not predicted or measured spend. The change
does not add automatic retry after an incomplete provider response because a naive next loop could
move the immediate-next-request boundary past the rejected patch. A future exact-retry policy would
need its own original-request identity, logical-turn/attempt correlation, usage persistence,
crash-ambiguity and qualification-pairing contract.

After full offline verification, execution hash
`sha256:bbb6dbdcab1c7561c868ae4cc40478d6e3401c5900feb59b8ea09ef38d9156a1`
was consumed exactly once by `run_826c1c7fb3d242c2` at harness commit
`c820a5e6f7b18697fded15bfa8097297253c54b6`. The append-only journal has four valid
hash-chained rows, and `CampaignCompleted.result_hash` exactly matches the 8,891 persisted result
bytes. Suite, schedule, execution plan, manifest and approved execution hash were independently
recomputed and match.

The run produced 88 events, 17 checkpoints, 13 model calls and 16 tool calls. Tool activity was
five searches, eight reads, one patch, one registered check and one diff. The patch was applied
once, the visible check passed and the run reached REVIEW. No submission lifecycle or evaluator
event exists. All 13 generated responses were completed with truncation disabled; every exact
input pre-count matched provider usage. Usage was 84,082 input and 7,355 output tokens, including
6,660 reasoning tokens, for 91,437/120,000 tokens and `$0.096159` calculated list-price cost.

The 14th logical request was exact-counted at 8,583 input tokens. With 28,563 total tokens
remaining, reserving the complete 25,000-token response allowance required 33,583 and exceeded the
budget by 5,020. PatchLoop therefore persisted event 86
`MODEL_GENERATION_BUDGET_EXCEEDED` with `generation_started=false` and made no provider generation
call. This is not input truncation, provider incomplete output or recurrence of r3's per-call
output ceiling.

Trace qualification passed 21 of 22 checks. Its only failure is named
`prompt_token_integrity`, but `failed_event_sequences=[]`: all generated-call telemetry matched.
The actual failing predicate is `terminal_generation_block_valid=false`. The v3 terminal-block
validator is retry-specific and requires a rejected candidate binding; this generic REVIEW budget
block had `retry_context_present=false`. D-037 evidence reports zero rejected candidates, retry
episodes and verified retries with no failed source sequence. The diagnostic is consequently
`failed/qualification_not_passed`, evaluator arrival is false, and the run neither validates nor
falsifies rejected-patch rehydration.

The checked-in
[mini D-037 r4 evidence record](../reports/live-pilot/dev-validation-gpt54mini-d037-20260729-r4.json)
binds the aggregate result, journal, approved plan, qualification, manifest, result, provenance,
failure record, patch intent/candidate and terminal request evidence by SHA-256. Only the
agent-generated public-source candidate patch is bundled; it was not submitted or accepted. The
four-mini subtotal through r4 was `$0.32007075`. Terminal r5 raised the mini subtotal to
`$0.45570375`; controlled r6 raises it to `$0.62150025`. Terminal primary r1 later raises the mini
subtotal to `$0.77412075`; the ten paid pilots then totaled `$1.602985125` at configured list
prices. Corrective primary r2 later brought eleven paid pilots to
`$1.652716875`; v4 pilot `run_d7207fbb06184dd3` brings twelve paid pilots to `$1.740790125`.
The first 12-run campaign brings all 24 paid attempts to `$3.133982625`; the v4 12-run campaign
brings 36 paid run attempts to `$4.981546875`. Invoice charges and free daily usage treatment
remain unverified.

Executed evidence:

```text
.venv\Scripts\python.exe -m pytest tests/test_trace_qualification.py -q
68 passed

.venv\Scripts\python.exe -m pytest tests/test_live_pilot_evidence.py -q
21 passed

.venv\Scripts\python.exe -m pytest tests/test_experiments.py -q
49 passed

.venv\Scripts\python.exe -m pytest -q
484 passed, 2 skipped

.venv\Scripts\ruff.exe check patchloop tests
All checks passed

git diff --check
passed
```

The two skips are Docker sandbox tests whose explicit reason was `Docker daemon unavailable` in
that offline execution environment. Those commands made no OpenAI generation or paid API call.
The r3 and r4 provider runs above are separate immutable evidence and neither executed a hidden
evaluator campaign, stress row, memory-development run or core run.

### D-041 r5 diagnostic contract decision

R4 supplies the sizing evidence for a new, separately identified r5 diagnostic profile v3. The
runtime rule remains strict: an exact request input and the complete 25,000-token response
allowance must both fit before a generation starts. The diagnostic-only total budget is 200,000,
derived before execution from the preserved r4 prefix and three tail reservations:

```text
91,437 + 3 × (10,031 + 25,000) = 196,530
196,530 rounded up = 200,000
```

Here 10,031 is the largest exact input observed among r4's completed generation requests. At the
configured maximum token rate, the existing conservative preflight formula gives
`(200,000 + 25,000) × $4.50/M = $1.0125`, below the unchanged $2 cap. This is authorization
reserve arithmetic, not measured r5 usage or invoice evidence. It is also a planning reserve rather
than a guarantee that a future candidate-bearing retry request cannot exceed the observed maximum.

New exact-request no-generation event payloads use `model-generation-block-v1`. Qualification may accept a
generic versioned block as internally consistent terminal trace evidence when its request,
recomputed budget, no-generation state and terminal error agree, even if no retry candidate is
present. Such a block does not create a rejected candidate, retry episode or D-037 gate pass.
Historical unversioned retry blocks remain readable, while r4's unversioned generic block and
21/22 qualification remain immutable.

R5 does not inject a synthetic rejection, alter runtime reservation semantics or automatically
retry an incomplete/inconclusive run. If the agent reaches the evaluator without a rejected
mutation, the diagnostic is inconclusive and terminal. No r5 provider call, measured usage,
evaluator verdict or D-037 pass is claimed in this section.

The D-041 offline implementation was verified without an OpenAI generation:

```text
.venv\Scripts\python.exe -m pytest tests/test_agent_runtime.py tests/test_experiments.py tests/test_trace_qualification.py -q
191 passed

.venv\Scripts\python.exe -m pytest -q
504 passed, 2 skipped

.venv\Scripts\ruff.exe check patchloop tests
All checks passed

git diff --check
passed
```

The tests cover zero-model-call and post-model generic blocks, request/budget/retry-mode/terminal
tampering, historical unversioned retry readability, r4 immutable evidence, the exact r5
25,000/200,000 suite pair and partial-contract rejection.

Direct read-only requalification against the preserved local source evidence also returned the
original artifacts unchanged:

```text
run_4a9737ec91964dca  sha256:88c763f2617d4b40c0f4c50229831d1dcdbf0477d7ae05aa99c4241538d10a43  qualified=true   22/22
run_e90f7c52aa134182 sha256:59c389c5fbc730e4f7b6e06bf221d238832e47b609a43030d8f566996ce98885  qualified=false  21/22
run_826c1c7fb3d242c2 sha256:84747b5ee19fec786792313471247202875d68f02752ea68f4078fbe5fc311f4  qualified=false  21/22
```

The compatibility rule ignores only the historical neutral
`binding_required=false` / `binding_valid=true` detail-shape pair. Recomputed check outcomes and
all other fields must still match; a non-neutral change remains an immutable-artifact error.

### D-043 controlled diagnostic offline and live evidence

The terminal r5 result made another opportunistic paid rerun inappropriate: it reached the
evaluator successfully but naturally produced zero rejected mutations. D-043 therefore introduces
the new `d037-rejected-patch-retry-v4` profile and
`controlled-reject-first-prepared-patch@trigger_after=1` manifest fault. It is not part of the
public `inject-fault` aliases or the frozen stress schedule.

The gateway rejects the first patch only after `patch-mutation-intent-v1` preparation proves a raw
Git diff against tracked regular targets is applicable to the current state and produces a
non-empty expected diff. It records one `CONTROLLED_DIAGNOSTIC_REJECTION` result before postimage
write. Tests prove the worktree remains at the prepared baseline, invalid patches do not consume
the trigger, the same action replays the durable rejection, a new action can apply the patch, and
fresh recovery after either `ToolCalled` or `PatchPrepared` closes the action as rejected without
`PatchApplied`. A separate checkpoint-boundary E2E terminates after the rejection result is durable
but before the next checkpoint, then proves resume reuses that exact result without recomputation
or duplicate mutation.

An offline full agent loop independently proves that the first next request contains the exact
candidate bytes, content hash and structured rejection, while the following request clears the
one-turn retry block. Qualification reconstructs the candidate/result CAS and request body and
adds `controlled_diagnostic_boundary`: exactly one controlled rejection, exactly one verified
controlled failure immediately adjacent to its `PatchPrepared`, zero `PatchApplied` events for
that action and no failed controlled sequence.
The approved-plan check additionally requires profile v4 to map exactly to the controlled
manifest fault. Profile/fault mismatch fails qualification.

The final offline regression collected 531 tests and completed with 529 passed and 2 expected
skips. Ruff and `git diff --check` also passed. Corruption tests prove a malformed declaration,
duplicate declaration, preceding `PatchPrepared` or event interleaved before the controlled failure
fails closed instead of consuming or reinjecting the diagnostic fault.

The offline contract was then committed as
`1333ab968e2f144b632c0cb5ca341ebd30e0ca4e` and approved once with execution hash
`sha256:d6a756dc69a7cf6e024d541b64a458a940ec41bdfeb3c403a3f01c539660e67b`.
`run_73f5aaf7328a4ea5` produced one adjacent controlled rejection at event 88, zero
`PatchApplied` for that action, one fully verified retry, evaluator arrival and official
hidden/regression/scope/safety pass. Qualification recomputation passed 23/23 with hash
`sha256:cd3dedfdfd19e246755952daf20779eb5cc85c2ff26f7709dd8aeca8ebbb2c6a`.
All 19 provider requests were completed and their exact input pre-count matched reported usage:
138,262 input + 13,800 output token, calculated cost `$0.1657965`. The four-event journal chain and
persisted result hash were independently rechecked. The portable aggregate is
`reports/live-pilot/dev-validation-gpt54mini-d037-20260730-r6.json`.

This validates the D-037 harness branch under one deliberate intervention. It does not estimate
natural rejection frequency or recovery rate, and it is not evidence of memory benefit or primary
campaign quality. The consumed suite/hash/run are immutable and must not be rerun.

### D-058 self-validation Docker isolation and offline smoke evidence

On 2026-07-31 the repository-free `patchloop-sandbox:py312` image was rebuilt from the current
Dockerfile and PID-1 probe runner against the pinned Python 3.12 base digest. Docker Desktop 4.83.0
with Engine 29.6.2 reported the resulting image identity as:

```text
sha256:268495717da1396e3413ce6695063c9516202b4e38cb8042f2f181420b64e9c1
```

The three real-container E2E tests passed. They exercised network denial, non-root/read-only
execution without a forwarded host secret, and the probe-specific conjunction of cleared proxy
variables, masked Git metadata, absent evaluator paths, read-only workspace and no network.
An independent labeled-container query after the run returned no residual probe container.

The full repository regression then completed in the same Docker-active host environment:

```text
704 collected
702 passed
2 skipped
```

Both skips are Windows symlink-capability paths; no Docker test was skipped. Repository-wide Ruff,
probe-runner compilation and `git diff --check` also pass.

The cost-free mock run `run_36f90bda91b94d42` separately exercised the v3/v6 agent lifecycle
through the official Docker evaluator. It completed six model turns and six tool calls, recorded
one current-diff structured review, and passed hidden, regression, scope and safety verification.
Recomputed `self_validation_lifecycle` evidence passed with an untruncated review body, valid final
submission binding, no post-review validation and no failed source sequence. The historical
`task-public-v1` smoke task has no registered probe profile, so this run correctly recorded zero
probe calls; actual probe execution isolation is evidenced by the real-container E2E above rather
than attributed to this run.

The run used no provider tokens and cost `$0`. Its overall live-campaign qualification is
intentionally false because it is a mock run without a live OpenAI provider, frozen model/campaign
provenance or an approved execution plan. D-058 therefore closes only the Docker isolation and
offline lifecycle gate. OpenAI v3/v6 start/resume remains fail-closed until a separate suite,
execution hash, cost review and explicit approval are introduced.

### D-059 profile-bearing offline agent probe evidence

D-059 adds one infrastructure-only `task-public-v2` package at
`fixtures/task-packages/self-validation-csv-quoted-newline`. Its identity is
`csv-quoted-newline@2`, with registered profile `quoted-newline-case`. It deliberately reuses the
small calibration issue to make harness behavior deterministic, but lives outside `tasks/` and is
absent from `data/dataset-manifest.yaml`. It is not a sixth calibration task or a
memory-development, held-out, core or headline task. The checked package hashes are:

```text
public  sha256:e72110791ac062f719a26c5b3d68d32152a5d82ede75a9971f667138f9bde926
private sha256:c1727483c0a496cde1765a55204b922ca7874973b937a2d9658121b5c938099c
```

The final cost-free CLI smoke `run_7e3c5af2ce8d498a` exercised the whole agent lifecycle against
the real clean probe image
`sha256:268495717da1396e3413ce6695063c9516202b4e38cb8042f2f181420b64e9c1`.
It used seven model calls and seven tool calls. Registered probe event 33 passed, returned exact
stdout `probe-ok\n`, recorded `authoritative=false`, and bound the expected image identity.
The subsequent same-diff review cited event 33 in both targeted validation and requirement
evidence, retained `deterministic_correctness_claimed=false`, and was presented untruncated to
`finish_task`.

Submission and evaluation completed. Official hidden, regression, scope and safety verdicts all
passed. Recomputed `self_validation_lifecycle` recorded one probe call/one verified probe, one
review/one verified review, no failed source sequences, a valid probe-manifest binding, valid final
submission binding and no post-review validation. Model cost was `$0`; no OpenAI request occurred.

The final repository-wide regression on this source collected 708 tests: 706 passed and the same two
Windows symlink-capability paths skipped. No Docker test skipped. Ruff, probe-runner compilation and
`git diff --check` passed. The frozen dataset audit retained
`sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`,
25 tasks and zero candidates.

This closes profile selection, real probe execution, review citation and evaluator arrival only for
the offline fixture. Overall qualification remains intentionally false at 19/26 because the run is
mock/non-campaign and lacks live provider, frozen campaign and approved execution provenance; the
campaign-oriented private-boundary heuristic also detects deterministic fixture/reference overlap.
The dedicated public-boundary E2E assertion and lifecycle check pass, but D-059 must not be described
as full live trace qualification, memory benefit or task-performance evidence. OpenAI v3/v6
start/resume remains fail-closed.

## Open gates

`patchloop doctor` now passes with authenticated `gh`, WSL2, Docker Desktop and the pinned evaluator
image; `official_evaluation_ready=true`. The dataset freeze is complete. Corrective primary r2 is
accepted immutable evidence, and the first 12-run campaign completed without infrastructure or
qualification errors, but evaluator arrival was 0/12. That campaign is preserved as investigation
loop evidence rather than a no-memory performance baseline or memory-index source.

D-048 tool-v2/context-v4 investigation continuity is offline-complete and v4 provider pilot
`run_d7207fbb06184dd3` passed the official evaluator and qualification 25/25. The D-051 v4 campaign
also completed 12/12 without infrastructure or qualification error, but nine exact-request budget
failures and three hidden task failures produced SCRR 0/12. It is immutable diagnostic evidence, not
a valid baseline. D-052 has now completed the token-aware corrective-tail and future 250,000-token
contract offline under `phase-evidence-v5`; it made no provider call. A leak-safe
maintainer-assisted proposal now deduplicates the two tox repetitions and holds the unresolved
Loguru source. Memory admission is deferred. D-060's small memory-development no-memory budget
pilot has now completed once and is immutable diagnostic evidence. D-062 was then consumed exactly
once under its approved 900k corrective execution hash, but only the HF row ran before an original
qualification failure halted the campaign; the two remaining rows were not started. The Babel+Moto
high-budget panel has already completed 2/2 and is immutable. D-062 cannot be rerun or continued.
D-063 completed the versioned saturation-context offline gate without a provider call. D-064 then
contracted and consumed one separately approved single pilot; that run is immutable and no later live
run is approved. No usable no-memory baseline or 96-run core campaign has been executed.

The context-reset trigger, persistent-state-off arm and stress matrix runner/report remain
unimplemented. The production stress injector still uses cooperative suspension, while an isolated
subprocess E2E has exercised actual process termination and fresh-interpreter stale-`RUNNING`
reclaim. The timeout path remains synthetic on the first registered visible check. No stress
schedule row or 96-run core campaign has been executed. Rejected mutating-tool input rehydration
has offline qualification and one controlled live exercise, but no natural recovery-rate evidence.

## D-060 diagnosis and consumed D-062 evidence

The consumed D-060 experiment remains bound to execution hash
`sha256:61a7208bd6ee1a45b08511407d0c8c0658976685245a11d422077efdf9bdef4f`.
The read-only budget derivation reproduced all three terminal rows without changing the source JSON:

- HF Hub `run_d20c9757bdef4942`: 438,483 tokens, 21/40 model calls, 43/100 tool
  calls, total-token binding, exact-request deficit 5,171 and maximum v5 same-prefix minimum 658,739.
- PDM `run_4352391174814d1d`: 153,702 tokens and no binding budget dimension.
- pyfakefs `run_6b4f13316e714785`: 252,066 tokens and no binding budget dimension.

D-062 added a read-only `budget-pressure-v1` derivation and a separate corrective suite. Its approved
execution hash was
`sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`, consumed exactly once
by experiment `dev-no-memory-corrective-pilot-20260731-r1`. Only HF Hub
`run_0ccfc8fd359a4785` reached terminal state. Original trace qualification failed and the runner
fail-closed with `QualificationFailureHalt`, leaving PDM and pyfakefs not-started. The original
campaign gate is false.

The HF run recorded 33 completed model responses, 875,908 total tokens and `$0.8408853` calculated
cost before exact-request budget admission blocked the next provider call. Seven `apply_patch`
candidates all failed preview, so `PatchPrepared`, `PatchApplied`, evaluator arrival and SCRR
observation are all absent. Six semantic replays did activate gateway saturation, but the v7 context
continued advertising read/search; 30 such calls were durably blocked without dispatch. This is live
failure evidence for saturation-context integration and raw-diff reliability, not a no-memory model
performance baseline.

The original experiment result, hash-chained campaign journal and original qualification artifacts are
immutable. Independent replay identified a v5-vs-v6/v7 nominal-reserve drift in the qualifier.
Append-only correction `qcor_8b6ff812...4870b6` is bound to correction hash
`sha256:a240256fe26eed6277b6668a985e2a20df6a94125cf7e7e813f25c3d4975961c`, corrected
qualification hash `sha256:803460fb5703c5d6423bd125f0b32b4e6d690114712367b5884ccdfad96e2b12` and clean
harness commit `b35bb91caf8a28313f305bd5507d0a4fba9079e8`. The original two failed checks become an
empty corrected failed-check list and corrected trace integrity passes. Exact repeated creation left
the correction file SHA-256
`sha256:fc6c469a989a7109d0d6b0ac8f609171aba87cdf8c3df543dd25bc75916d49c9` unchanged. This does not modify the canonical
qualification, original false campaign gate or failed task outcome. The suite, experiment ID and
execution hash must not be rerun.

After the correction implementation, the full repository collection was 798 tests: 791 passed and
seven environment-dependent cases skipped; Ruff and `git diff --check` passed.
The next gate was not a D-062 continuation. It was an offline `phase-evidence-v8` contract that makes
six-replay saturation visible in the authoritative context/phase contract while preserving historical
v7 rendering and qualification. D-063 below records that gate's completion; a new single-task suite
still requires its own clean execution hash, explicit cost cap and separate live approval.

## D-063 phase-evidence-v8 offline evidence

D-063 keeps `SYSTEM_PROMPT_V5` and `TOOL_SCHEMAS_V4` fixed and introduces an offline-only
`tool v4 / phase-evidence-v8` pair. `phase-contract-v3.read_search_policy` records the active mutation
epoch, semantic replay count, threshold 6, ordered tail/saturation reasons and read/search admission.
`context-build-evidence-v8` and five `ContextBuilt` mirrors bind the same state. Saturation-only removes
read/search while retaining a registered probe; a strict token/model/tool tail removes the probe too.
Only successful `PatchApplied` advances the epoch and resets the replay count.

`corrective-runtime-contract-v2` binds the unchanged prompt/tools to the V8 context version, and
`trace-source-evidence-v8` separates new source semantics from V7. The V8-only
`saturation_context_contract` independently recomputes epoch, replay count, tail reasons and resulting
action filtering from the durable prefix. Existing `investigation_evidence` remains responsible for the
full context rebuild and tool-result presentation CAS binding.

The first runner integration test exposed and then fixed a qualifier gap: a real semantic replay is a
`ToolReplayed` presentation event, but the initial independent checker accepted only
`ToolSucceeded`/`ToolFailed`. The final E2E forces six replays, raises a real `SystemExit`, resumes with a
new runner, verifies that the first resumed context removes read/search, applies a patch, verifies that
the next context reopens them at replay count zero, completes the mock evaluator path and
passes `saturation_context_contract`.

Historical compatibility evidence includes a clean-checkout golden hash for a representative minimal
V7 rendered context (`sha256:93a131b...9ec8e`) and context evidence
(`sha256:c5a00dec...c8c79`). The local immutable D-062 source evidence also still recalculates to
`sha256:53148b2b42e82ddcb6083b1b317df3c7f8598972ed61fac0f69c65c5acff4351`.
No OpenAI request, live suite, execution approval or model cost was created by D-063. A future pilot
requires a new purpose and a separately approved hash/cost cap; D-062 remains non-resumable.

Final executable evidence: the six directly related test modules completed with 377 passed and two
environment-dependent skips. The repository-wide run collected 822 tests and completed with 815 passed
and seven environment-dependent skips in 403.33 seconds. Repository-wide Ruff and `git diff --check`
passed. The D-062 source evidence hash was recalculated after the final qualifier change and remained
exactly `sha256:53148b2b42e82ddcb6083b1b317df3c7f8598972ed61fac0f69c65c5acff4351`.

## D-064 exact V8 live-pilot contract evidence

D-064 adds a new `memory-development-no-memory-saturation-pilot` purpose rather than reopening or
continuing D-062. Its checked-in suite fixes one HF Hub task, one `no_memory` repetition,
`gpt-5.4-mini-2026-03-17` medium/standard/default, tool v4/context v8/runtime contract v2,
40 model calls, 100 tool calls, 900,000 total tokens, 1,800 seconds and 25,000 output tokens per call.
The deterministic worst-case reserve is `$4.1625` under the dated official price snapshot and the
suite cap is `$5`.

Generic V8 remains mock-only and experiment-free. The exact D-064 exception requires the OpenAI
provider, frozen HF task, public review contract and new saturation purpose. At `AgentRunner.start` and
`resume`, a runtime-version-only plan is insufficient: the persisted approved plan must also match the
suite, task/private identity, schedule row, model, budget, memory, fault, pricing, image, SDK, harness
commit and public review contract through the same independent comparison used by qualification.

The `v8-saturation-context-v1` diagnostic now uses the common hash-bound
`experiment-diagnostic-result-v1` envelope and is deliberately independent of evaluator arrival.
A structurally qualified trace can therefore classify the natural saturation/reset branch as pass,
inconclusive or fail, while the separate completion gate still requires official evaluator arrival.
Task success is not required, and the one-row result cannot enter comparison headlines or failure-memory
admission.

At the contract-implementation gate, no provider request, live execution capability or model cost was
created by the checked-in files and tests. The later execution remained a separate hash-and-cost gate.

Final offline executable evidence: the repository-wide run collected 837 tests and completed with
830 passed and seven environment-dependent skips in 405.1 seconds. The exact approved-plan integration
also exercised `qualify_run(persist=False)` and passed its public review, runtime-v2, execution-plan and
pricing-at-start checks while intentionally failing overall qualification because no synthetic terminal
trace was fabricated. Repository-wide Ruff and `git diff --check` passed after the final change.

## D-065 consumed D-064 live result and immutable seal

The user-approved execution hash
`sha256:dcade27f9f89efd6c349db58cbe732c0c81f1bbaf3bbb05e6c14b4ca62f2b85c` was consumed exactly once
for experiment `dev-no-memory-saturation-v8-pilot-20260801-r1` at harness commit
`c542142c4e4530bd7e9dca28a5efc2cebc11a7f9`. The single run was
`run_45e3edc434d749f7`. The raw result file hashes to
`sha256:7f9568274488d0b8ddd5b0b7269e6e177df9939260a3872d4006873a951849ac`; the journal file hashes to
`sha256:f4b245b4f7e6811364756c5dbd216071d2ed57e115ed436d8744721ed68efc24` and its final
`CampaignCompleted` event hash is
`sha256:a9dd243b67fcf92af8ace1f95b188aedc58df6a89e9bf448c1769c010f4aea26`. The canonical execution-plan
hash is `sha256:297261447db53b3c7a19fdc18a0bbda8326f04b4b6ab01d52c2c969ed66400c3`; the plan file's distinct
byte hash is `sha256:e8c8c6a431dca0306f4b373ed9dbb5cdb144d35a0e583da3c5faccbe727da51b`.

Trace qualification passed 30/30 with leakage scan pass and qualification hash
`sha256:94cba6063bac69a28f97172f75bc0c86f566c9824b53bad6f226c3f7dbe46722`. The independent
`v8-saturation-context-v1` diagnostic passed: context sequence 101 removed read/search after natural
saturation, a patch was applied at sequence 106, and context sequence 110 reopened investigation after
the mutation-epoch reset. There were no infrastructure, qualification or diagnostic errors.

The completion gate nevertheless failed. All 40 provider responses completed with truncation disabled
and exact input/total telemetry matched 40/40, but 14 `review_task` calls were rejected. Thirteen cited
an incomplete set of current-diff presented evidence; the final attempt cited a current diff after the
passing check had fallen out of the presented result window. The run exhausted its 40-model-call limit
before generation 41, submission or evaluator arrival. It used 618,370 input tokens including 50,688
cached, 41,003 output tokens including 30,444 reasoning, 64 tool calls and 320,219 ms. Total usage was
659,373 tokens and deterministic list-price cost was `$0.6140766`. Remaining headroom was 240,627 tokens,
36 tool calls and 1,479,781 ms, so model calls—not the total-token ceiling—were the binding dimension.

This establishes only the live V8 policy exercise. It does not establish correctness of the unsubmitted
27-addition/4-deletion diff, task success, SCRR, a no-memory baseline, memory benefit or a core budget.
The sanitized portable record is
[`reports/live-pilot/dev-no-memory-saturation-v8-pilot-20260801-r1.json`](../reports/live-pilot/dev-no-memory-saturation-v8-pilot-20260801-r1.json);
raw provider bodies, private task data and hidden evaluator payloads remain local-only. The exact
experiment ID is now source-level immutable even in a clean clone, and the result/journal already block
duplicate execution locally. D-064 is not rerun. The next gate is an offline current-diff review-evidence
presentation correction before any separately versioned live completion proposal.

Post-run source sealing and portable-evidence verification collected 839 tests: 832 passed and seven
environment-dependent tests skipped in 506.1 seconds. The directly affected experiment and evidence
modules passed 152/152. Repository-wide Ruff and `git diff --check` also passed. No additional provider
request was made while producing or verifying this seal.

## D-066 phase-evidence-v9 correction — offline gate complete

D-066 adds an opt-in `phase-evidence-v9` path without modifying the consumed D-064 suite, run or V8
artifacts. The V9 request carries `review-evidence-v1`: required passing checks and the final current-diff
`get_diff` are rendered from durable artifacts outside the 12-event recent window, deduplicated by
sequence and included in the exact tool execution context. `SYSTEM_PROMPT_V6` names this top-level block
as the only review citation authority and explicitly excludes investigation-ledger navigation sequences.

The production-equivalent offline selector is `review_evidence_validation=True` with the mock provider
and no experiment context. Replay, arbitrary providers, experiment-bearing manifests and mixed
validation modes fail closed. The only live V9 selector remains the exact D-067 review-evidence purpose
with the OpenAI provider and its separately approved execution plan.

The gateway verifies the pinned diff, latest mutation, required check set, final-diff sequence and exact
citable ordering. Invalid citations return public `review-citation-error-v1` details containing the
current citable and passing-validation sequences rather than an unstructured stale-ID error. The runner
counts failed `review_task` calls only after the latest successful patch and stops before another model
generation when three failures occur in that epoch; a later successful patch resets the count.

Provenance is versioned as `corrective-runtime-contract-v3`, `context-build-evidence-v9` and
`trace-source-evidence-v9`. Qualification adds `review_evidence_context_contract`, which rebuilds the
current mutation, check and diff anchors from durable events and verifies request/evidence/ContextBuilt
mirrors plus artifact CAS. Historical V8 rendering remains on its existing schema and is not reclassified.

The focused regression collected 504 tests: 502 passed and two existing capability-dependent tests
skipped. Repository-wide pytest collected 879 tests: 872 passed and seven environment-dependent tests
skipped. Ruff and `git diff --check` passed. This closes only the D-066 offline gate: no execution hash,
provider request, cost, live campaign task result or SCRR observation was created. The mock/no-experiment
E2E reaches the evaluator and passes the V9-specific review, saturation, self-validation and public-review
contracts, but whole-run `qualified` intentionally remains false because live campaign, approved-plan,
Docker-provenance and official-evaluator gates do not apply to that offline selector.

## D-067 V9 completion pilot — consumed live result

The checked-in suite `dev-no-memory-review-evidence-v9-pilot-20260801-r1` fixes one frozen HF Hub task,
one `no_memory` repetition, `gpt-5.4-mini-2026-03-17` medium/standard/default, v4/v9/runtime-v3,
60 model calls, 100 tool calls, 1,200,000 total tokens, 1,800 seconds and 25,000 output tokens per call.
At the dated standard rate, the deterministic conservative reserve is `$5.5125` and the suite cap is
`$6`. The purpose is tuning-only and its completion gate excludes task success, comparison eligibility
and memory admission.

Approved execution hash
`sha256:f1b7d78243af8c87e3ec83f9373312f171073e0713a23fbc51c909fac0be6982` was consumed exactly once at
source harness `db144051f7f3d5049498971593df548697789dcf`. Run `run_4c77b1102e224785` reached the
official evaluator with 332,204 input + 12,550 output = 344,754 tokens, 21/60 model calls, 36/100 tool
calls, 121,894 ms and calculated cost `$0.2880024`. No budget dimension bound. Regression, scope and
safety passed, while hidden acceptance failed; the outcome is `task_failure` and SCRR remains false.

The original completion gate remains false: terminal/evaluator/official counts are 1/1, but qualified
runs are 0/1 with one qualification error. Original qualification hash
`sha256:8840382b824dc27015e82d2949d39ada06c8169efe0fdcda3b219c3a1dece59e` passed 32/33; only
`submission_lifecycle.complete_source_in_context` was false. Its file bytes remain
`sha256:1e3558eeee6ab505fe313a3f75ab4ae958e85876010321b74500c8c7a3464d2c`. The result, journal and
false gate are immutable, and the consumed hash is not reusable.

## D-068 V9 pinned-diff qualification correction — append-only complete

The common submission qualifier now recognizes a V9 final `get_diff` pinned outside recent events only
after independently validating request CAS, source descriptor/path/size/hash/bytes, exact integer
sequences, current-diff identity, untruncated content and exactly one nested and top-level presentation.
Non-object source JSON, float/bool sequence aliases, missing/duplicate anchors and independent sidecar
tampering fail closed. Parameterized regression preserves the historical V1-V8 recent-event-only rule.

Correction `qcor_51b72504161eddf250e872cc533dbfc5a315c377971e8a6f19a74a380fe3c032`, created by clean harness
`24fc92b9bbca5b1b9714a5a1f20d0dfbbc01205a`, binds the original qualification and unchanged source
evidence hash `sha256:2096b9a6114dc767aabd5e2d35d89077c91993a8cad6c42eeae99e223539f572`.
Its correction hash is `sha256:836b013bccbdbcc7d0eecde24248b86eff353d1adef281f07b215c3ded65f0ed` and corrected qualification
hash is `sha256:1bff6db36a32104c2417c6aef65e8dcda50e00e71b451c51d78ae8df75df954c`. Corrected trace
qualification passes 33/33 while retaining `task_failure` and memory ineligibility. The tracked writer
regression verifies content-addressed idempotency; the canonical qualification bytes remained unchanged.

Portable evidence is checked in at
`reports/live-pilot/dev-no-memory-review-evidence-v9-pilot-20260801-r1.json`. Local immutable hashes
include experiment result `sha256:71bb203ae2ffaf3deeaa9523273410c83bb477a0574b99279242c2e764caf96d`, journal
`sha256:62e22e068fc08d1de91c8c9d78c9e94b6b2dd75cc1a216b75b5dc7ee916050c0`, final journal event
`sha256:e2ae51f8cad76dcd7a3a54365184858d2a471d51024164ffe734a0ad2902230a`, execution-plan file
`sha256:d7d5497c1d1a464c7962bc89fea73c693e26801db3e25ed24fce2858f4eaa532`, run result
`sha256:e3f4a855ae1d53bcf3381cfe1bc35167503e2774dd80308e929ce2184bcafe8b` and correction file
`sha256:2a78f098a0d5ff9782fd5e4385a1b56b2b23623475554f0f2c295cc2b99fba71`.

The current repository-wide regression collected 925 tests: 918 passed and seven environment-dependent
tests skipped. Ruff and `git diff --check` passed. No provider call or added cost occurred while fixing
the qualifier, creating the correction or sealing this report. Corrected trace integrity does not change
the hidden failure, `task_failure`, SCRR=false, original campaign gate, comparison exclusion, memory
admission or core status. The next gate is leak-safe, public-evidence-only analysis of the
hidden-acceptance task failure and requirement coverage, not a budget increase or a rerun.

## D-070 V10 live-pilot contract and consumed-result evidence

D-070 introduced a new one-row purpose rather than reusing D-067. The checked-in suite fixes
HF Hub/no-memory ×1, `gpt-5.4-mini-2026-03-17` medium/standard/default, tool v5/context V10/runtime-v4,
60 model calls, 100 tool calls, 1,200,000 total tokens, 1,800 seconds, 25,000 output tokens and a $6 cap.
The execution plan binds the V2 public-review sidecar, prompt/tool hashes, frozen task/image/dataset,
pricing, SDK, schedule and clean harness commit. Its post-run gate requires official evaluator arrival and
non-vacuous evidence from all five V10 coverage checks while recording task success separately.

Offline validation collected 988 tests: 981 passed and seven environment-dependent tests skipped. Ruff
and `git diff --check` passed before execution. The host no-call preflight then confirmed the pinned image,
SDK 2.47.0, API-key presence without exposing its value, clean Git and pricing freshness.

Execution hash `sha256:cc361c4fa569085b0268a419ec86a7a91ec87719206d604227d2cb45a9c46914`
was consumed exactly once by `run_6cc69fc1170c4a44`. All 28 provider responses completed with exact
input/total token telemetry, truncation disabled, `store=false` and no previous-response dependency. Usage
was 611,450 input tokens including 58,880 cached, 56,103 output including 44,831 reasoning, 50 tool calls,
353,004 ms and `$0.671307` at the recorded list rates. The run retained 32 model calls, 50 tool calls,
532,447 tokens and 1,446,996 ms; no budget dimension bound.

The first V10 review was a valid partial review: seven of eight targets were verified and
`cov-92159184a168` remained unresolved. Its corrective read requested lines 1407–1478 although the public
anchor `def get_hf_file_metadata(` was at line 1401. A later search found the anchor but did not create the
required same-diff read evidence. Three subsequent review calls cited unrelated sequence 169 against an
authoritative empty allowed-sequence list and were rejected. The run ended with `SubmissionProtocolError`
before submission or evaluator arrival. Qualification passed 30/34 checks; only the four positive coverage
lifecycle checks failed. This is incomplete lifecycle evidence, not trace/CAS corruption.

Zero-model postmortem `run_c07bb2e439a74380` evaluated the exact diff hash
`sha256:5735b7125d464b00824c2e10f6eff0eab801db1c31277f9173ed49495d00404f`. Regression,
scope and safety passed, but hidden acceptance failed. This derived result does not rewrite the live run,
gate, qualification or SCRR. The live experiment and authorization hash are hard-immutable and will not be
rerun. The sanitized evidence seal is
`reports/live-pilot/dev-no-memory-coverage-review-v10-pilot-20260802-r1.json`. It is not a no-memory
baseline, memory source or core result; the next gate is offline structured rejection feedback and
exact-anchor recovery E2E.

The post-run source seal completed with 991 tests collected: 984 passed and seven environment-dependent
tests skipped. Ruff and `git diff --check` passed. Sealing, hard-immutability validation and the no-model
postmortem added no provider call or model cost.

## D-071 V11 structured rejection recovery — offline gate complete

D-071 leaves the consumed D-070 V10 run, false gate, qualification and no-model postmortem immutable.
It adds a separate offline-only tool-v6/context-v11/runtime-v5 path whose
`coverage-citation-error-v1` names the rejected public target, parent requirement,
submitted/allowed/invalid event sequences and the exact public path+anchor or visible-check IDs needed
for recovery. Private task data, hidden assertions, reference patches and evaluator feedback are not
inputs to this structure.

`coverage-rejection-feedback-v1` is rebuilt from durable source input/result CAS, the public review
mapping and the exact request/model response that declared the rejected call. The same request/response
tool-call binding applies to fresh recovery evidence, refreshed diff, clearing review and a clearing
mutation. A mutation may clear feedback only through one exact
`ToolCalled -> PatchPrepared(intent CAS) -> ToolSucceeded -> PatchApplied` chain. Partial review,
orphan success, missing response declarations, forged CAS/mirrors and duplicate mutation fail closed.

The designated first rejection crosses a real stale-RUNNING reclaim. Only state-store checkpoint
bookkeeping may occur between that durable failure and the fresh runner's first request. A stale retry
may create a second rejection on the reclaimed worker; later contexts then carry the newest unresolved
feedback and the same worker may complete recovery. Passing-validation targets may cite multiple fresh
results, including multiple tool calls from one model response; runtime and qualifier bind every cited
call/result independently before accepting the refreshed diff and complete review.

Executable evidence includes three positive boundaries: exact-anchor restart recovery, two rejections
with one restart and same-worker completion, and a two-check batched validation recovery. Each reaches
the separate local evaluator without a duplicate patch. The tamper corpus covers source/recovery/clearing
request and response CAS, worker claims, stale feedback, old-worker activity across the restart boundary,
target mapping/key-order handling, result bytes, prepared-patch intent, orphan events and duplicate
mutation.

Final validation results:

- `tests/test_coverage_rejection_v11.py`: 7 passed.
- V11/V10/trace-qualification/viewer focused bundle: 43 passed.
- Repository-wide pytest: 999 collected, 992 passed and seven environment-dependent skips in 525.1
  seconds.
- Repository-wide Ruff, Python compileall and `git diff --check`: passed.

No `.env` credential was loaded, no provider request was made, no live execution hash or cost approval
was created, and added model cost was zero. This proves only the offline public recovery protocol and
trace-integrity boundary. It is not SCRR, a no-memory baseline, memory admission, a live-model recovery
rate or core-campaign evidence.

## D-072 V11 live-readiness contract — offline implementation only

D-072 first separates D-071 code by responsibility without changing its public semantics:

- `patchloop/agent/coverage_rejection.py` owns V11 structured feedback reconstruction previously hosted
  in `patchloop.agent.context`.
- `patchloop/evals/coverage_rejection.py` owns V11 independent recovery reconstruction previously hosted
  in `patchloop.evals.qualification`.
- The original modules preserve their import surface. No tool/context/schema version, canonical artifact
  shape or qualification check ID is changed, and D-070/D-071 evidence is not rewritten.

The new checked-in suite
`experiments/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.yaml` fixes exact purpose
`memory-development-no-memory-coverage-rejection-pilot`, one HF Hub/no-memory row,
`gpt-5.4-mini-2026-03-17` medium/standard/default, v6/v11/runtime-v5,
60 model/100 tool/1,200,000 token/1,800 seconds, output 25,000, reserve `$5.5125` and cap `$6`.
Generic V11 remains mock/no-experiment only; only this exact purpose and OpenAI provider form the exact
live exception.

The offline result contract separates integrity from whether a natural rejection occurs. Zero rejection
can leave the recovery check integrity-valid with `exercise_status=inconclusive` and
`exercise_reason=rejection_not_observed`. If any rejection occurs, all observed
`coverage-citation-error-v1` source and subsequent public recovery/refreshed-diff/clearing CAS bindings
must verify; any failed sequence makes the readiness gate false. The gate does not require task success and
always leaves comparison-denominator and memory-admission eligibility false. Live hard restart is outside
this row and remains a separate follow-up fault exercise.

This subsection records the D-072 offline implementation stage, not its later live result. The source suite contains
`live_cost_approved=false`, `approved_execution_hash=null` and `pilot_run_id=null`. No clean-host preflight,
real-runtime persisted execution plan/hash, user invocation approval, provider request, live result or cost
evidence was claimed at that stage. The preflight unit test computes a synthetic execution hash and exercises the
approval branch only under a fake environment and temporary root; it leaves no usable live capability.

Final offline verification on 2026-08-02 produced:

- D-072-focused matrix: 322 collected, 321 passed/1 environment-dependent skipped, 0 failed.
- Repository-wide matrix: 1,022 collected, 1,015 passed/7 environment-dependent skipped, 0 failed.
- Ruff, Python compileall and `git diff --check`: passed.
- API/network/provider calls and model cost: 0; clean-host/persisted execution hash and user approval: none.

The live-shaped tests use in-memory Responses doubles. D-070 remains immutable; SCRR, no-memory baseline,
memory admission and core campaign remain closed.

## D-073 D-072 live-result evidence seal

After the offline contract closed, a clean-host no-call preflight produced execution hash
`sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d`. The user explicitly
approved that exact hash for one `gpt-5.4-mini-2026-03-17` D-072 V11 live-readiness invocation with a `$6`
cap. It was consumed exactly once and is not reusable.

The immutable experiment result records:

| Field | Observed value |
| --- | --- |
| Run | `run_e2132144a8774b05` |
| Terminal / infrastructure / qualification errors | true / 0 / 0 |
| Completion gate | `v11-coverage-rejection-live-pilot-gate-v1`, passed |
| Official evaluator | reached |
| Trace qualification | 36/36 passed |
| Coverage rejection diagnostic | `inconclusive/rejection_not_observed`; rejection count 0 |
| Official verdicts | hidden fail; regression/scope/safety pass |
| Outcome / SCRR | `task_failure` / false |
| Usage | 797,862 input + 64,465 output = 862,327 token; 35 model calls; 57 tool calls; 369,385ms |
| Calculated model cost | `$0.841833` |
| Budget binding | none |
| Rejected-patch retry | 17 rejected candidates, 17 verified retry episodes, no failed source sequence |
| Saturation / mutation | 17 saturated contexts; one post-saturation `PatchApplied` |

The completion gate is true because it measures official evaluator arrival, qualified trace and public coverage
lifecycle; task success is deliberately not a gate requirement. Hidden acceptance failure therefore remains the
authoritative task outcome. Similarly, 17 rejected-patch retries are mutation-preview candidate failures, not
`coverage-citation-error-v1` review rejections. They do not change the structured coverage rejection count of 0 or
turn the recovery diagnostic into a pass. Saturation and one applied patch also do not establish fresh-worker
recovery.

D-073 adds the experiment ID to the hard-immutable consumed set and binds its approved execution hash/run to
sanitized portable evidence at
`reports/live-pilot/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json`. It does not alter the original
result, hash-chained journal, qualification, failure record or campaign gate. This run and hash are not rerun, and
the row remains ineligible for comparison, memory admission, a no-memory baseline or the core campaign. Live
provider hard kill/reclaim is still unmeasured. D-073 sealing made no provider request and added zero model cost;
the only provider activity described here is the single approved D-072 invocation.

Post-run source-seal verification collected 375 focused tests: 374 passed and one environment-dependent test
was skipped. The repository-wide matrix collected 1,025 tests: 1,018 passed and seven environment-dependent
tests were skipped. Ruff, Python compileall and `git diff --check` also passed. These are D-073 seal-integrity
checks, not another live invocation or evidence that the hidden task was solved.

## D-074 retrospective evidence boundary

D-074 adds no provider run, test result, performance measurement or new task outcome. It is a read-only
consistency decision over the existing evidence:

- D-055 established that the generic V2/V5 agent can complete two development-validation tasks through the
  official evaluator; it did not freeze a comparison budget.
- D-060 established that two resource-stratified rows reached the evaluator and hidden-failed while only HF
  Hub was budget-confounded.
- D-067 reached the official evaluator without budget binding and remains a hidden task failure. Its
  append-only qualification correction does not create a need for hidden-failure-driven tuning.
- D-070 exposed a diagnostic V10 submission-feedback failure, D-071 closed that feedback path offline, and
  D-072 showed one V11 live readiness row could reach the evaluator. These exact HF Hub V10/V11 artifacts
  remain diagnostic-only and are not baseline prerequisites.

The evidence therefore supports stopping the same-task corrective loop. Generic development/core remains
tool V2/context V5 without the task-specific coverage sidecar. At this D-074 decision point, the
`21/50/250,000/900` templates were stale and could not be executed as-is. The next evidence-producing step,
after a separate configuration decision, is one small diverse development readiness panel on the exact
intended generic tuple and budget.
Its gate separates process readiness from correctness: every row must be terminal, qualified, reach the
official evaluator and avoid infrastructure/qualification/diagnostic/budget confounds, while hidden/SCRR
success remains an outcome rather than a prerequisite. Passing that gate permits tuple freeze and a fresh
no-memory baseline; it does not permit task-specific hidden tuning. Live hard restart remains a separate
reliability evidence gap.

## D-075 offline contract evidence boundary

D-075 produces source and executable offline contract evidence, not a live result. The checked-in exact suite
selects ordered Babel, Moto, pyfakefs and HF Hub rows, `no_memory` once each, the dated mini snapshot at
medium/standard/default, `SYSTEM_PROMPT_V3`, tool V2/context V5, transport retry 0, output 25,000 and
40/100/850,000/1,800 per-run limits. The source authorization reserve is `$15.75` under a `$16` cap.

Tests cover exact task/order/role/model/runtime/retry/budget drift, mixed-role preflight, no-sidecar manifests,
execution-plan and paid start/resume comparators, qualification reconstruction, official evaluator completion,
zero-success gate acceptance, each confound rejection and report/memory exclusion. Historical completion and
V11 suite hashes remain unchanged because the optional retry field is omitted from their serialization.

No source toggle, approved execution hash, run ID, provider response, measured usage/cost, task outcome or SCRR
belongs to D-075 offline evidence. The suite hash is source identity only. At that point a clean-host no-call
preflight could produce a commit/environment-bound execution hash for user review, but it was not authority to
call the provider. D-076 below records the later separately approved invocation. Its gate failed, so the
comparison tuple, no-memory baseline, failure-memory admission and core campaign remain closed. A changed final
budget/runtime/harness commit requires its own readiness evidence rather than promotion of D-075.

Final offline verification on 2026-08-02 ran repository-wide `pytest -q` to exit 0 with seven
environment-dependent skips after the formatting-only diff cleanup. Focused runtime recovery, exact gate binding,
positive qualification/tamper tests, Ruff, Python compileall and `git diff --check` also passed. No provider or
network request was made by this verification.

## D-076 D-075 live readiness result seal

The user approved execution hash
`sha256:1709a9e9911f980aafe28cdd9fe9ed486367c134e2dc9e465c88e01f9462bd66` for exactly one
four-row D-075 invocation under the `$16` cap. The source harness commit was
`2c075abedf58cd8a2ec0d928d8e7ebb0ba9acd1a`. The result raw SHA-256 is
`sha256:ba2670e8f1bb79e0af9cf56d02841014cc3e66d58db85b114459776af277d30d`; the journal file
SHA-256 is `sha256:bbb86164dfa6fa3ff047df0d2dc025e5a63dd44b79564a84ba325e508cadc511`, and its final event
hash is `sha256:deedc716e88fb7c0d47c5d041fefd7c0430b45e67164d5e13b7239eec57d817e`. The execution-plan
canonical semantic hash is `sha256:b754f1ffab7ed436c5dcaa7b159570c68c7abcda58acf756d28d458655d35a59`;
the raw plan-file SHA-256 is `sha256:9c4b2ffe838ee175489369896208f394928eb702a36ed52537841ef9f4629cb6`.

| Task | Run | Outcome | Evaluator | Binding budget | Tokens | Model/tool calls | Cost |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| HF Hub | `run_466f7fb5275646e4` | `agent_failure` | not run | total token; exact deficit 9,586 | 809,867 | 37/67 | `$0.782049` |
| Babel | `run_00d5fc0a8d914df4` | resolved/SCRR | official pass | none | 58,718 | 7/8 | `$0.0559485` |
| Moto | `run_96817acf84c046fc` | resolved/SCRR | official pass | none | 115,809 | 11/15 | `$0.12862425` |
| pyfakefs | `run_7e10fe04319c4771` | `agent_failure` | not run | 40 model calls | 724,430 | 40/52 | `$0.797415` |

Every row's persisted result matches the campaign-embedded row. Qualification passed 26/26, 27/27, 27/27
and 26/26 respectively, and the 490-file evidence index reconciles all referenced hashes. Total usage is
1,580,179 input + 128,645 output = 1,708,824 token, 95 model and 142 tool calls, with calculated cost
`$1.76403675` exactly reconciling to recorded prices.

The immutable `generic-baseline-readiness-gate-v1` result is false: 4/4 terminal and qualified, 2/4 evaluator
reached/official, zero infrastructure/qualification/diagnostic errors and two budget-terminal rows. The report
keeps `analysis_ready=false`, ordinary metrics empty, and 2/4 SCRR diagnostic-only. Neither this result nor its
append-only seal opens comparison, memory admission, a no-memory baseline or core. The portable sanitized record
is `reports/live-pilot/generic-baseline-readiness-v2v5-20260802-r1.json`; raw provider bodies, secrets, private
task specifications, hidden assertions and reference patches are excluded.

D-076 seal verification selected 51 D-075/generic tests and all 51 passed. Repository-wide pytest collected
1,089 tests: 1,082 passed and seven environment-dependent tests were skipped. Ruff, Python compileall and
`git diff --check` passed. These checks made no provider request and added zero model cost; they validate the
source seal, not another readiness run or a changed original outcome.

## D-077 budget-only successor source/offline evidence boundary

D-077 declares the new exact successor `generic-baseline-readiness-v2v5-20260802-r2`. It preserves D-075's
ordered Babel/Moto/pyfakefs/HF Hub rows, dataset roles, `no_memory` repetition 1,
`gpt-5.4-mini-2026-03-17` medium/standard/default, `SYSTEM_PROMPT_V3`, tool V2/context V5, SDK retry 0,
output 25,000, tool 100, wall 1,800 seconds, absent sidecar and fault-free policy. Only model calls 40→50 and
total tokens 850,000→1,200,000 change. D-075's source, approved hash, four runs, raw/portable evidence and false
gate remain immutable and are not D-077 evidence.

The official rate was rechecked at 2026-08-02T13:11:37Z. The resulting conservative authorization reserve is
`$5.5125` per run and `$22.05` for four rows under a `$23` cap. These are source authorization bounds, not
measured usage, expected cost or invoice data.

At this source-contract point no provider call, execution hash, user cost approval, run ID, measured token/cost,
live qualification, evaluator receipt, SCRR or readiness gate outcome exists for D-077. Focused readiness tests
and the repository-wide matrix passed; the latter collected 1,095 tests with 1,088 passed and seven
environment-dependent skips. Ruff, Python compileall and `git diff --check` also passed. These are executable
offline contract facts with zero provider call and zero added model cost, not a clean-host preflight or live gate.
A clean no-call preflight must next bind the exact commit, package/image/evaluator, SDK,
pricing, randomized schedule and prompt/tool/retry. The resulting hash and maximum `$23` then require separate
explicit user approval before one live invocation. Comparison, memory admission, no-memory baseline and core
remain closed throughout this source stage.

## D-078 D-077 live budget-only readiness result seal

The user approved execution hash
`sha256:de73e622fcaa4cec85191cceb01efdb0d27cc6a5a6b8f05c7cd4844df50763f5` for one D-077
four-row invocation under the `$23` cap. The source harness commit was
`4a2596e43398af094f1f17bcb0cb1a7945cb7058`. Recomputed source identities match the persisted plan:

- suite: `sha256:ce1881bf3e4d2012c03e6ff043546d9720a0202131deda658bc5750df581fc0c`
- schedule: `sha256:44d868a753898029ed7205e438db07660c7542906592f1aa831e48c3ed41a38e`
- result file: `sha256:22385cf6efd9b54de960cfe5b55c812ba74d3275ac9496f7db16fd0cb727e5fe`
- journal file: `sha256:91f162be3099661535e0621918e67d32f64c6cf2ccc147040fa386e79796e66e`
- journal final event: `sha256:0a65f0bd0e20caa4f1cedd41433a63f53c6aa2a965ee256531a0d71777ba4b62`
- raw plan file: `sha256:473ad3ad2f6b708d0d71fceb335fc6d0588ed3676ef71e44ccd9340c702181ed`

The ten-event campaign journal is contiguous and its hash chain validates. CampaignCompleted binds the result
hash above. SQLite state, per-run manifest/result, experiment rows, event-derived usage, independent budget
pressure, qualifications and three evaluator receipts agree byte-semantically.

| Task | Run | Outcome | Evaluator | Binding budget | Tokens | Model/tool calls | Cost |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| HF Hub | `run_d5155046063644ad` | hidden task failure | official completed | none | 804,527 | 43/96 | `$0.7844715` |
| Babel | `run_48cfb695d0be4c7d` | hidden task failure | official completed | none | 41,410 | 6/6 | `$0.04153125` |
| Moto | `run_4896f998af9644b2` | resolved/SCRR | official completed | none | 339,307 | 26/33 | `$0.35209275` |
| pyfakefs | `run_415695539ad24658` | agent failure | not run | 50 model calls | 812,840 | 50/84 | `$1.00017` |

Qualification passed 27/27, 27/27, 27/27 and 26/26 respectively; every trace integrity and leakage flag is
true. Total usage is 1,816,830 input + 181,254 output = 1,998,084 token, 125 model and 219 tool calls, with
calculated cost `$2.1782655`. All 125 provider responses completed and exact requested-input telemetry matched.

The immutable `generic-baseline-readiness-gate-v1` result is false: 4/4 terminal and qualified, 3/4 official
evaluator, zero infrastructure/qualification/diagnostic errors and one model-call budget terminal. The report
keeps `analysis_ready=false`, ordinary metrics empty and 1/4 SCRR diagnostic-only. The portable sanitized record
is `reports/live-pilot/generic-baseline-readiness-v2v5-20260802-r2.json`; raw provider bodies, secrets, private
task specifications, hidden assertions and reference patches are excluded. D-078 adds the r2 experiment ID to
the consumed hard-immutable set. It does not rerun the panel, change the original gate, freeze a no-memory
baseline, admit memory or authorize another budget increase.

D-078 seal verification selected 11 D-077/generic tests and all passed. Repository-wide pytest collected
1,099 tests: 1,092 passed and seven environment-dependent tests were skipped. Ruff, Python compileall, JSON
parsing and `git diff --check` passed. These checks made no provider request and added zero model cost; they
validate the immutable guard and sanitized record, not another readiness run or a changed task outcome.

## D-079 workflow-completion probe source/offline evidence boundary

D-079 adds a separate source identity for the public process question left by D-078: can the exact pyfakefs
generic V2/V5 workflow reach the official evaluator when model/tool call counters are observed but do not censor
admission? It does not alter or combine D-077's consumed hash, four runs, false gate or D-078 seal.

The checked-in contract fixes purpose `workflow-completion-probe`, experiment ID
`pyfakefs-workflow-completion-probe-v2v5-20260803-r1`, one frozen pyfakefs task, `no_memory` repetition 1,
the dated mini medium/standard/default, prompt V3, tool V2/context V5, SDK retry 0 and output 25,000. Runtime schema
`workflow-completion-runtime-contract-v1` selects policy `model-tool-observability-only-v1`: model/tool limits are
`null`, while count and usage telemetry remain required. Total-token 3,000,000, wall 7,200 seconds and the existing
exact-request, cost, loop, state/idempotency, constrained-tool, Docker/network/evaluator guards remain active.

The source conservative authorization reserve is `$13.6125` under a `$14` cap. It is not measured spend. Official
standard pricing was reverified at 2026-08-02T16:35:25Z as `$0.75/M` input, `$0.075/M` cached input and `$4.50/M`
output. Pricing freshness must still be checked again at the clean no-call preflight boundary.

At this source/offline stage the evidence ledger intentionally records:

```text
provider calls = 0
execution hash = absent
user cost approval = absent
run ID/result = absent
measured usage/cost = absent
live qualification/evaluator receipt = absent
workflow-completion-probe-gate-v1 outcome = absent
SCRR/task outcome = absent
```

The source/config and offline contract tests are not provider capability or execution authority. Repository-wide
verification collected 1,182 tests: 1,175 passed and seven environment-dependent tests skipped. Ruff, compileall
and `git diff --check` also passed; provider calls and model cost were zero. The clean commit identity remains to be
created before preflight.
Next, a clean no-call preflight must bind task/package/image/evaluator, SDK, prompt/tool/runtime, schedule, fresh
pricing and the harness commit. Only a separate explicit approval of that exact hash and maximum `$14` may authorize
one invocation. The row remains calibration-only and excluded from baseline, comparison, memory admission and core
regardless of hidden outcome. Any approved live result belongs to a later D-080 append-only evidence seal.

## D-080 D-079 live result and append-only gate-summary correction seal

The approved D-079 execution hash
`sha256:70bc29196115cc6b201a30587d6974d3a05607345d447cb3a9144b0920c09791` was consumed exactly
once at source harness commit `66fefde373f75729eef0e68fecc2f56a9bb1c174`. Exact identities are:

- suite: `sha256:0683bebba0363b3535bfb5024dae2516705fa21c393ac78e841be52634ba85aa`
- schedule: `sha256:8f1bd5502ff4fb3b73625b9a8e066c596f751aa9e4d7699455547b7a8ba40522`
- execution-plan semantic artifact: `sha256:cd4eb385743093dc55f03987d079564630cb9f03c2ea86defd7c1f8321b1856a`
- experiment result file: `sha256:c9f85ac52b0b3933625966c2bd6af1f6b57bdc974f2c141aa74bd21a2700ee28`
- campaign journal file: `sha256:b134a467e04c6b03559dd0b0ea0db379a1d480ccaa4a4cdcbea2596fb056fe84`
- journal final event: `sha256:48c1ada3aed7cc0dfa05bfc0a6a3f04a061e97dbf1edcf712bfc18ab6d446b1c`
- qualification file/hash: `sha256:4d7a15f9984394b6ab798f78e391c6b0d5632bc0e6d4d4c9c4876eb5028c8168` /
  `sha256:0368ef128ac6bb22ec4b15bac0ad6f77d73869c1f4d82c8537defd67aaa99d82`
- qualification source evidence: `sha256:5efce76a94abfe48bcce9f63283cd0459fd9606c4a05d4c008430d52437b5928`
- submitted diff: `sha256:3da446ede6cd014c0c2b7d292f340c14bc0779d5f875f60df96a0d5242da675c`

Run `run_606349c2c56342d4` reached a terminal result, passed trace qualification 28/28 and completed the
official evaluator. It used 1,663,819 input + 126,888 output = 1,790,707 token, 84 model calls, 119 tool calls,
856,559ms and usage-derived list-price cost `$1.81747785`. All 84 responses completed, exact input/total token
telemetry matched and no previous-response dependency was used. Remaining headroom was 1,209,293 token and
6,343,441ms; model/tool headroom is null because the counters were observability-only. Binding dimension, blocked
tools, exact-request blocks, budget terminals and terminal-loop failures were all absent.

The submitted one-file diff changed `pyfakefs/fake_os.py` by +20/-1 with no dependency, test-file or public-API
change. Registered regression, scope and safety passed, while hidden acceptance failed. Therefore workflow
completion was observed but task outcome is `task_failure`, scope-compliant success/SCRR are false. Public trace
diagnostics record 73/84 model and 104/119 tool calls in REPRODUCE, 41 semantic replays, three rejected candidates
with three verified retry episodes, two prepared/applied patches, one passing registered check, final diff review
and one accepted submission. No hidden assertion or reference patch content was used for this analysis.

The immutable original gate is false only because `call_guard_contract_passed=false`; every other process
predicate is true. The full qualification artifact independently records one
`disabled_call_guard_contract` check with pass true, null model/tool limits, valid runtime contract and zero
forbidden generation/tail or context/admission failure. The historical terminal summary omitted raw checks while
the gate consumer searched that omitted collection. This is
`qualification-summary-projection-mismatch`, not a runtime or trace violation.

Append-only correction
`gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861` has semantic body hash
`sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`. The digest equivalence makes the
ID commit to the source identities above, correction harness commit
`7e40e27446bcf011f700c219a96983e5670422f4`, projection contract, exact mismatch cause, exact original gate,
exact corrected gate and claims boundary as one semantic body. Both gate payloads use
`workflow-completion-probe-gate-v1`: the append-only corrected payload records
`call_guard_contract_passed=true` and `passed=true`, but it does not replace or mutate the original false payload.

The forward producer emits only a sanitized `qualification-gate-check-projection-v1` object under
`gate_checks.disabled_call_guard_contract`. The consumer requires the outer key set to contain exactly that one
ID and the inner key set to contain exactly `schema_version`, `check_id`, `check_count` and `passed`; it then checks
the exact schema/ID, strict integer count 1 and boolean true. Missing, duplicate, extra, relabelled or malformed
fields fail closed. In particular, `check_count=true`, `1.0` and `"1"` are rejected rather than accepted through
Python truthiness or equality coercion.

The portable sanitized seal is
`reports/live-pilot/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.json`. Its portable correction manifest is
`reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json`, 4,591 bytes with SHA-256
`sha256:45a73a5000befa4f4d0ccbde739c686778f25a77cafe245a1529c35671bda3dd`. The manifest uses outer schema
`workflow-completion-gate-summary-correction-manifest-v1` and semantic body schema
`workflow-completion-gate-summary-correction-v2`. It excludes provider bodies, private task/evaluator content,
hidden assertions and reference patches. D-080 adds no provider call and `$0` model cost. Final verification passed
331 focused tests; repository-wide collection was 1,162 with 1,155 passed and 7 environment-dependent skipped.
Ruff, Python compileall, JSON parse and `git diff --check` also passed. The cumulative usage-derived list-price ledger
through D-080 is 55 unique paid runs and `$15.072655275`; this is not an invoice or free-tier claim.

The claims boundary states `original_artifacts_modified=false`, `original_gate_replaced=false`,
`task_outcome_changed=false`, task success/SCRR false, calibration-only true and comparison/memory/core false. Thus
the corrected process gate does not change task failure, SCRR, `analysis_ready=false` or calibration-only status.
Comparison denominator, no-memory baseline, memory admission and core remain closed. Automatic rerun, original
artifact rewrite and hidden-driven tuning are not authorized. The next decision is to verify the projection fix
offline and choose a condition-neutral baseline budget from public completion evidence without treating this
single 84-call trajectory as the frozen population budget.

## D-081 source evidence and D-082 measured-result boundary

D-081 adds source identity `generic-baseline-readiness-v2v5-20260803-r3` and content-addressed derivation
`reports/live-pilot/artifacts/d081-condition-neutral-budget-candidate.json`. It does not modify or combine the
consumed D-075/D-077/D-079/D-080 executions, results, original gates or D-080 append-only correction.
The derivation file SHA is
`sha256:6f871c13aee71043c20c54c72a93667600462e8369483e9354507a94d0063193`.

The exact panel keeps ordered Babel, Moto, pyfakefs and HF Hub, their original development roles, `no_memory`
repetition 1, seed `20260723`, dated mini medium/standard/default, `SYSTEM_PROMPT_V3`, tool V2/context V5,
SDK retry 0 and output 25,000. Model/tool limits are null under
`model-tool-observability-only-v1`; telemetry remains required while count-based admission is absent. Retained
run limits are total token 2,400,000 and wall 1,800 seconds plus the existing exact-request, cost, loop,
state/idempotency, constrained-tool, Docker/network/evaluator guards.

The derivation artifact selects evaluator-complete public process rows without using task success or private
outcomes. Its maximum trajectory is D-079 pyfakefs at 1,790,707 token, 84 model calls and 856,559ms.

```text
1,790,707 + (84 * 2,000) + 25,000 = 1,983,707
1,983,707 * 1.2 = 2,380,448.4
round_up(2,380,448.4, 100,000) = 2,400,000

856.559 * 2 = 1,713.118 seconds
round_up(1,713.118, 300) = 1,800 seconds
```

The source binding names `generic-baseline-runtime-contract-v2`,
`generic-baseline-runtime-evidence-v2`, `generic-baseline-readiness-gate-v2`, and exact-one
`qualification-gate-check-projection-v1` check `disabled_call_guard_contract` for every row. These new names
preserve historical v1 meaning. Repository-wide offline verification collected 1,204 tests and completed with
1,197 passed and seven environment-dependent skips. Ruff, Python compileall and `git diff --check` also passed.
The focused coverage includes an exact D-081 wall-clock block, budget-identity tamper rejection, approved-preflight
to start-manifest binding and malformed gate projections. No provider request was made by this verification.

Official standard pricing was recorded at 2026-08-03T01:08:49Z as `$0.75/M` input, `$0.075/M` cached input and
`$4.50/M` output. The conservative source authorization arithmetic is
`(2,400,000 + 25,000) * $4.50/M = $10.9125` per run, `$43.65` for four rows, cap `$44`.
These are not measured cost or an invoice.

After that source gate, D-081 ran exactly once from clean commit
`b4c79242bb0a94eed50530116205323e78c7d21a` under approved execution hash
`sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`. The predeclared
process gate passed without changing its predicate:

```text
terminal runs = 4 / 4
trace-qualified runs = 4 / 4
official evaluator completed = 4 / 4
disabled-call guard projections = exact 1 / 1 on every row
infrastructure / qualification / diagnostic errors = 0 / 0 / 0
budget-terminal / terminal-loop failures = 0 / 0
generic-baseline-readiness-gate-v2 = passed
task success = 1 / 4, Babel only
hidden task failure = 3 / 4, HF Hub + Moto + pyfakefs
regression / scope / safety pass = 4 / 4 each
comparison budget frozen = false
no-memory baseline/memory admission/core unlocked = false
```

Measured usage is 111 model calls, 175 tool calls and 1,929,316 tokens. At the frozen standard rates the calculated
model cost is `$1.79426325`, below the `$44` authorization cap. It is not evidence of the billed invoice or
free-tier charge. All 111 requests completed; 111/111 exact input counts matched provider usage, truncation was
disabled and `store=false`. Three natural rejected-patch retry episodes were verified 3/3. The trace contains 50
loop observations, 39 from pyfakefs, but no terminal loop failure.

The immutable evidence identities are:

```text
suite semantic hash = sha256:2be237b6b4b9fc0c63be841716f7fa271cd14e97e287041f8667e88eb48e5075
suite YAML byte SHA = sha256:3d357bac2b5033231c7e0349a99291e842c16792ef753122a9ddb5e7c3f529dc
schedule semantic hash = sha256:2d6b5487b99474c96d038356fb15a60f5733c6e976f90f270692a1ebf1a63b69
approved plan semantic hash = sha256:8aecde2488e1823508acdd0c8f4a33a631f011ba6689e5b848091574c522d72e
execution plan file SHA = sha256:8fbb85715bfa6d53e33317a5328fcff2404c12be4354f3eaad63e20184bc6407
source derivation SHA = sha256:6f871c13aee71043c20c54c72a93667600462e8369483e9354507a94d0063193
raw result SHA = sha256:f8a2cd25916290ae02e46b484519cc01dedbe50097326085524a88bb9b324f83
journal file SHA = sha256:52626ba6d7e61bc293ce327f4bf190e3b4118b20a2efe4d9de09d8186ce6afdd
pre-completion journal hash = sha256:b62f805c783a1a26b95794a6febc999cf629f4175d422add8d29c80c364a0fd4
final journal event hash = sha256:f5537479c3c1e8c150f9cbfec5238d99c882eff537006773af8d9ddf9f78c254
portable report path = reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json
portable report SHA = sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2
```

D-082 creates the sanitized portable seal without another provider call or model cost: 0 and `$0`. Final
repository verification collected 1,214 tests and passed 1,207 with seven environment-dependent skips; focused
D-082 verification passed 8/8.

D-081/D-082 are calibration-only. Process-gate success proves workflow readiness for this exact tuple, not hidden
perfection, a no-memory performance baseline, memory benefit, recovery under injected faults, held-out/core
readiness or a population estimate. The 1/4 task success cannot authorize task-specific tuning or automatic rerun.
The same ceiling across 96 core runs has theoretical reserve `$1,047.60`, conflicting with the original `$150`
cap, so a separate predeclared budget/scale/freeze decision remains required.

## D-083 offline condition-neutral comparison-budget freeze evidence

D-083 derives a policy from exact D-081 r3 public process evidence without modifying D-081/D-082. The selected
source value is the pyfakefs observed-prefix minimum 1,303,223. Hidden acceptance, task success and the D-080
historical minimum 1,815,619 are not selection inputs; D-080 is explicitly outside this evidence scope.

```text
observed-prefix minimum = 1,303,223
headroom multiplier = 1.2
unrounded = 1,563,867.6
rounding unit = 100,000
frozen total-token ceiling = 1,600,000

model-call limit = null
tool-call limit = null
wall-clock limit = 1,800 seconds
max output tokens = 25,000
SDK transport retries = 0
```

At the frozen worst configured rate, reserve is `$7.3125` per run, `$87.75` for 12 runs, `$131.625` for
18 runs and `$702` for 96 runs. These are authorization bounds, not measured spend, billed invoice or free-tier
claims. Existing `$20` and `$150` caps remain unchanged, so source templates stay fail closed.

```text
artifact path = reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json
artifact SHA = sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88
comparison_budget_policy_frozen = true
runtime_support_implemented = false
manifest_support_implemented = false
qualification_support_implemented = false
live_execution_authorized = false
comparison_denominator_eligible = false
no_memory_baseline_unlocked = false
memory_admission_unlocked = false
core_campaign_unlocked = false
analysis_ready = false
provider calls = 0
model cost = $0
```

Until the next offline execution-plan runtime-evidence, RunManifest and qualification gate passes, this evidence is
a policy decision rather than an executable campaign contract. Historical D-081/D-082 remain immutable
calibration-only evidence and completion is not guaranteed. Final verification collected 1,238 tests: 1,231 passed,
seven environment-dependent tests skipped; focused artifact tests passed 9/9 and experiment contract tests 245/245.

## D-086 exact D-085 measured-result and correction seal

```text
experiment = dev-validation-condition-neutral-v2v5-pilot-20260803-r1
source commit = 629b9fdd9f69d1522cf565a06ae9679abe3f60a7
execution hash = sha256:7163f6c44aa5b7790d35546be37781248d6575eac60986b2610f2e21c35348a0
run = run_c355405d826641b9
original readiness gate = passed
official evaluator = reached
hidden/regression/scope/safety = pass/pass/pass/pass
qualification = 28/28
input/output/total tokens = 69,701 / 3,500 / 73,201
model/tool calls = 8 / 9
wall clock = 50,769ms
usage-derived list price = $0.06802575
result SHA = sha256:e0c3c4c67adc8c157a5030c9a93e3fd106d6b7a12f596253ddf10582fe74b80a
journal SHA = sha256:4c114059fad069526d95786c392b7ea36724443b7231b4426bb097ee0c2199c8
final event SHA = sha256:93853c6367459bcae004789a9a2710c6be518078b21041ece0b160d9843e5a8b
qualification SHA = sha256:11bda7b2f31bae453f21c4718fdcb4563a74e173e621fd8035f1ab8aa64f1293
source evidence SHA = sha256:41d9b862fe5042b4838c53cd80c3318dc55dc5f0bd892962fecc20caba0b2105
```

The original result's `budget-pressure-error-v1` is preserved. Exact-ID read-only recomputation derives token
headroom 1,526,799, wall headroom 1,749,231ms and binding `none`; the correction does not rewrite or replace the
passed gate. The portable evidence is
`reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json`
(`sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464`) and the correction manifest is
`reports/live-pilot/artifacts/d086-condition-neutral-comparison-pilot-budget-pressure-correction.json`
(`sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4`). Final verification is `focused 64/64; repository-wide 1,416 collected, 1,409 passed/7 skipped; Ruff/compileall/JSON/git-diff checks passed; seal provider calls/model cost 0/$0`.

D-085 is now hard-consumed. The result is single-row workflow-readiness calibration and one observed task success,
not a no-memory baseline, comparison denominator, memory admission/index, core result or analysis-ready dataset.
No provider call or added model cost belongs to the D-086 seal work itself. At D-086 time the next candidate was a
separate `$88` 12-run cap decision; D-087 supersedes that forward choice without rewriting D-086.

## D-087 campaign-local accrued-spend source evidence

D-087 keeps the exact D-083/D-084 per-run tuple (`null/null/1,600,000/1,800`, output 25,000) while replacing the
unexecuted historical `$20` campaign template with a new exact source identity. Public D-081 r3 process costs derive
the policy without task-success or private-evaluator inputs:

```text
12-run mean projection = $5.38278975
12-run empirical max envelope = $14.36724
full next-run reserve = $7.3125
cap basis = $21.67974
campaign-local hard cap = $25
12-run worst-rate disclosure = $87.75
```

A row is admitted only when `accrued + $7.3125 <= $25`. The reservation journal is hash chained and fsynced. An
exact plan/journal/run/policy one-use capability is atomically consumed in SQLite before the provider boundary.
Before another row can start, prior terminal qualification, source evidence and result bytes are reloaded and token
usage is repriced with integer nano-USD fixed rates; displayed model cost is not trusted. With the SQLite anchor
preserved, marker deletion, journal reset, alternate runner roots and rehashed lower settlements are rejected.

This is a local campaign control, not an external billing ledger. Live resume remains disabled, and the implementation
does not claim protection against rollback or deletion of the entire local database and journal together. The `$25`
cap does not guarantee 12/12 completion; an unavailable full reserve marks the current and remaining rows
`not_started` and makes the readiness gate false.

```text
suite path = experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml
suite SHA = sha256:44de6899656c96830d3a0aa3326777848c5d632ef903eccc166839fa1caeaf79
artifact path = reports/live-pilot/artifacts/d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json
artifact SHA = sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe
focused verification = 68/68
repository verification = 1,472 collected; 1,465 passed; 7 skipped
provider calls = 0
model cost = $0
```

Clean preflight, candidate/approved execution hash, live campaign, no-memory baseline, comparison denominator,
memory admission/index and core remain closed. A later provider invocation still requires a clean committed source,
fresh no-call preflight and separate approval of the exact hash with maximum `$25` authority.

## D-088 immutable D-087 measured-result evidence

The exact execution hash
`sha256:0dd8ca1d0632398fed25ca28fbce89b97b0bf2137be163ed19a09fbf2d7f470d` was consumed once from clean
commit `7eee5fa1837d30e6177c46119885035f2b1d976f`. The original result records 12/12 terminal and qualified,
11/12 official evaluator, zero infrastructure/qualification/diagnostic/not-started/terminal-loop confounds, and one
budget-terminal AnyIO repetition. Outcomes are 1 resolved, 10 task failure and 1 agent failure. The 11 evaluated rows
all pass regression, scope and safety.

```text
result SHA = sha256:f3380aa466d5a2025562bb299e0bfc341135e5b2e77a634c80a87d796f1cbe40
journal SHA = sha256:14c6248d83738883486233a2f2516f3b975ef861ae10ba2f78d6d14d4b3f6fcd
journal final event = sha256:253f543528cb472b282dd29fbde9b21a7cdd5eca34f5be9882ab7cdea29f4358
plan semantic hash = sha256:66246391a30be5743c9c0de890249f2b4216dfd9ad61aa3e79b459cc9a82de07
plan file SHA = sha256:45aabeac18fd6648904a8d18a7c311da5277a4cc4bb5a057d74bd3222d624aaa
input/output/total token = 4,844,335 / 385,595 / 5,229,930
model/tool/input-precount = 340 / 547 / 341
list-price accrued = $5.36842875
campaign cap / maximum committed / held = $25 / $12.31149825 / $0
portable report = reports/live-pilot/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json
portable report SHA = sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269
```

All 340 provider responses completed with exact input/total telemetry, truncation disabled, `store=false` and no
previous-response dependency. The extra input pre-count belongs to the generation blocked before provider start.
The 50-event journal chain, 12 durable settlements, 12 SQLite one-use consumptions and all persisted qualifications
reconcile exactly. The original readiness gate remains false and the experiment is hard-consumed. D-088 adds no
provider call or model cost and does not establish a baseline, denominator, memory admission/index or core authority.
Final verification passed focused 74/74 and repository-wide 1,471 of 1,478 collected tests with seven
environment-dependent skips; Ruff, compileall, JSON parsing and `git diff --check` also passed.

## D-089 AnyIO budget-only readiness source evidence

D-089 binds the exact D-087 process-confounded row without changing D-087/D-088 bytes. The failed run
`run_4613c65b2a254349` used 1,578,208 tokens and had 21,792 left; the next exact 14,080-token input plus 25,000
output allowance required 39,080, leaving a 17,288 deficit. The probe therefore uses a new one-row experiment and
raises only the comparable per-run total-token knob from 1.6M to 2.0M.

```text
experiment = anyio-workflow-completion-budget-only-v2v5-20260804-r1
task = anyio-interrupt-runner-cleanup
condition / repetitions = no_memory / 1
model = gpt-5.4-mini-2026-03-17 medium standard default
prompt / tool / context = SYSTEM_PROMPT_V3 / v2 / phase-evidence-v5
budget = null model calls / null tool calls / 2,000,000 tokens / 1,800 seconds
max output = 25,000
same-prefix minimum / headroom = 1,617,288 / 382,712 tokens
worst-rate reserve / source cap = $9.1125 / $10
source artifact = reports/live-pilot/artifacts/d089-anyio-budget-only-readiness-probe-source-gate.json
source artifact SHA = sha256:19eca850799e9549eef1d8b383d0c3461aa2b9a2e5471d67fe599cb373ea4555
provider calls / model cost = 0 / $0
```

The readiness predicate requires terminal, qualified and official evaluator completion plus zero process confounds;
it does not require hidden acceptance, task success or SCRR. D-089 is not yet executed or consumed. Clean no-call
preflight, exact candidate hash and separate max-`$10` user approval remain pending. No-memory baseline, comparison
denominator, memory admission/index and core remain closed.

Final offline verification passed the 228-test focused D-089/historical contract set and 1,522 of 1,529
repository-wide tests; the other seven were environment-dependent skips. Ruff, compileall, JSON parsing and
`git diff --check` passed. This verification made no provider call and added `$0` model cost.
