# Current limitations

This file separates implemented behavior from the remaining 12-week campaign work.

## Implemented and measured locally

- Five audited `mini-data-utils` calibration fixtures with independent snapshot hashes
- Reviewed reference and known-bad evaluator paths for every calibration fixture
- Official Linux Docker evaluator smoke: three references accepted, 14 known-bad patches rejected
- Docker network denial, non-root UID, read-only workspace and host-secret non-forwarding checks
- Official Docker-evaluated offline agent smoke: three tasks under both mock and content-hashed replay,
  six of six runs accepted with complete persisted usage and trace evidence
- Duration-minute boundary and CSV EOF-finalization fixture references accepted, with four known-bad
  patches rejected per task by the pinned Docker evaluator
- First SWE-rebench-derived research task admitted: Loguru #1451, with an immutable official image,
  three reference passes, 20 upstream regressions, one base hidden failure and five known-bad rejections
- Second research task admitted: AnyIO #1121, with three hardened-reference passes, 20/20 hidden
  stability runs, 32 P2P regressions, one base hidden failure and five known-bad rejections. Its
  independent oracle rejects a source-equivalent normalization of the original benchmark fix because a
  later upstream incident exposed an expected-outcome lifecycle regression.
- Third research task admitted: tox #3810, with three reference passes, 29 P2P regressions, six
  independent hidden checks, one base hidden failure and five known-bad rejections. Its oracle preserves
  both cross-section empty-substitution and earlier same-section fallback semantics.
- Fourth research task admitted: Hugging Face Hub #3180, with three reference passes, 15 P2P
  regressions, eight independent hidden checks, one base hidden failure and six known-bad rejections.
  Its oracle binds imports to submitted source and limits the allowed public API change to the exact
  endpoint-aware signature delta.
- Fifth research task admitted: PDM #2781, with three normalized production-reference passes,
  36 base-checkout regressions, ten independent hidden checks, one base hidden failure, six semantic
  known-bad rejections and one scope/test-tampering rejection. The benchmark declares 37 P2P nodes
  because one passing parameter exists only in its test patch.
- Sixth research task admitted: pyfakefs #991, with three normalized production-reference passes,
  all 517 declared P2P regressions, 12 independent hidden checks and one base hidden failure. Seven
  semantic partial fixes and one scope/test-tampering patch were rejected. The task is medium, not
  hard; its strength is a clean network-disabled evaluator boundary and broad regression surface.
- Seventh research task admitted: Moto #7208 as development-validation only, with three normalized
  production-reference passes, 182 selected regressions, nine independent hidden checks and one base
  hidden failure. Six semantic partial fixes and one scope/test-tampering patch were rejected. Nine
  endpoint tests outside the benchmark P2P declaration are explicitly deselected; all 173 logical
  P2P nodes expand to 179 network-independent passing cases.
- Eighth research task admitted: Babel #1042 as development-validation only, with three exact
  production-reference passes, all 132 upstream number tests, 16 independent hidden checks and one
  base hidden failure. Seven semantic partial fixes and one scope/test-tampering patch were rejected.
  The task is medium, not hard. Its pinned-image CLDR overlay is explicit and submitted-source binding
  prevents evaluation against the image's baked production module.
- Ninth research task admitted: SQLGlot #7187 as the first core-cross-repo held-out task, with three
  exact production-reference passes, all 39 upstream DuckDB tests, 21 independent hidden checks and
  one base hidden failure. Seven semantic partial implementations and one scope/test-tampering patch
  were rejected. Its hardened oracle covers both NULL modifiers across five value-window functions
  and a representative BigQuery modifier-chain negative-transfer guard. This is deterministic
  evaluator admission evidence, not a live-model core result.
- Tenth research task admitted: PDM #3759 as the first core-same-repo held-out task, with three
  hardened-reference passes, 63 network-independent upstream regressions, 11 independent hidden checks
  and one base hidden failure. The exact benchmark production patch and eight other semantic partials
  were rejected, as was one scope/test-tampering edit. One declared P2P node that attempts an external
  install is explicitly deselected. This is deterministic evaluator admission evidence, not a
  live-model core result.
- Eleventh research task admitted: AnyIO #1134 as the second core-same-repo held-out task, with
  three exact-production-reference passes, all 36 upstream process regressions, 11 independent
  hidden checks and one base hidden failure. Nine semantic partial implementations were rejected,
  as was one scope/test-tampering edit. Its worker bootstrap lineage is distinct from the AnyIO
  #1121 development task. This is deterministic evaluator admission evidence, not a live-model
  core result.
- Twelfth research task admitted: Param #1117 as the second core-cross-repo held-out task, with
  three exact-production-reference passes, all 94 upstream reactive regressions, ten independent
  hidden checks and one base hidden failure. Eight semantic partial implementations and one
  scope/test-tampering edit were rejected. Its digest-pinned evaluator image is
  `sha256:c10bc0ad51b00c59ed8fa4366ee722c38e83dfaa620a7cc229f78489ccbaf010`.
  This is deterministic evaluator admission evidence, not a live-model core result.
- Thirteenth research task admitted: Hugging Face Hub #4056 as the third core-same-repo held-out
  task, with three exact-production-reference passes, 17 base-resident upstream regressions,
  15 independent hidden cases and one base hidden failure. Nine semantic partial implementations
  and one scope/test-tampering edit were rejected. Two of the benchmark's 19 declared P2P nodes
  exist only in the excluded benchmark test patch, so the executed and declared counts are
  reported separately. An adversarial pre-gate review found and closed a combined-partial oracle
  escape before admission. This is deterministic evaluator evidence, not a live-model core result.
- Fourteenth research task admitted: MTPLX #21 as the third core-cross-repo held-out task, with
  three hardened-reference passes, 55 base-resident OpenAI bridge regressions, 21 independent
  hidden cases and one base hidden failure. Nine semantic implementations, including the exact
  upstream accepted source patch, were rejected, as was one scope/test-tampering edit. The hardened
  oracle requires an exact `<tool_call>` delimiter, preserves lookalike tags as content and rejects
  non-whitespace residue beside or between streamed calls. This is deterministic evaluator admission
  evidence, not a live-model core result.
- Fifteenth research task admitted: FuseSoC #776 as the fourth core-cross-repo held-out task, with
  three exact-production-reference passes, 12 selected base-resident regressions, ten independent
  hidden cases and one base/no-op hidden failure. Eight semantic partial implementations were
  rejected by hidden acceptance, and one forbidden test edit was rejected by hidden, scope and
  test-tampering checks. The visible suite collects 14 tests but explicitly deselects one
  network-dependent export test and one lockfile test incompatible with the read-only submitted
  filesystem. This is deterministic evaluator admission evidence, not a live-model core result.
- Sixteenth research task admitted: tox #3846 with follow-up #3851 as the fourth core-same-repo
  held-out task, with three hardened-reference passes, 101 selected visible regressions and
  17 independent hidden cases across eight test functions. Base/no-op and ten semantic partials,
  including each accepted PR in isolation, were rejected; one forbidden test edit was rejected by
  hidden, scope and test-tampering checks. The visible surface is 99 passing cases plus two explicitly
  re-included healthy siblings out of 110 declared P2P nodes. This is deterministic evaluator
  admission evidence, not a live-model core result.
- Seventeenth research task admitted: Dagster #33605 as the fifth core-cross-repo held-out task,
  with three exact-production-reference passes, all 28 base-resident visible regressions and nine
  independently authored hidden tests. Base/no-op and all eight semantic partials were rejected;
  one forbidden test edit was rejected by hidden, scope and test-tampering checks. The
  `task-private-v2` content hash binds the hidden oracle, and both visible tests and the hidden
  oracle remain on read-only mounts while submitted production source is copied to a fresh
  writable import root. All 13 official cases made zero model/API calls. This is deterministic
  evaluator admission evidence, not live-model agent performance or a core campaign result.
- Eighteenth research task admitted: Kubeflow Pipelines #13112 as the sixth core-cross-repo
  held-out task, with three exact-production-reference passes, all 277 base-resident visible tests,
  15 subtests and 11 independently authored hidden tests. Base/no-op and all eight semantic partials
  were rejected; one forbidden test edit was rejected by hidden, scope and test-tampering checks.
  The frozen benchmark declares 278 P2P nodes because its test patch adds one preservation P2P case;
  the base-resident declared P2P surface is therefore exactly 277. The `task-private-v2` content
  hash binds the hidden oracle, and both visible tests and the hidden oracle remain on read-only
  mounts while submitted production source is copied to a fresh writable import root. All 13
  official cases ran from clean staging commit
  `5e7b019e60b4d76f67e48bafe6fd1a3b309fe313` and made zero model/API calls. This is deterministic
  evaluator admission evidence, not live-model agent performance or a core campaign result.
- Nineteenth research task admitted: Loguru #1297 as the fifth core-same-repo held-out task, with
  three exact-production-reference passes, all 43 base-resident visible tests and 11 independently
  authored hidden cases across five test functions. An implementation-independent
  `utcfromtimestamp()` solution also passed. Base/no-op and all nine semantic partials were rejected;
  one forbidden test edit was rejected by hidden, scope and test-tampering checks. Three
  deterministic, internally consistent fallback profiles cover positive, negative and
  date-rollover-derived offsets so a fixed derived-looking offset or zone cannot satisfy the oracle.
  All 15 official cases ran from clean staging commit
  `8c5084eee3a44a44e207345950a9ffb45b23e4b1` and made zero model/API calls. This is
  deterministic evaluator admission evidence, not live-model agent performance or a core campaign
  result.
- Twentieth research task admitted: pyfakefs #1269 as the sixth core-same-repo held-out task, with
  three exact-production-reference passes over 431 visible passes, 161 skips and 29 independently
  authored hidden cases per run. An implementation-independent dynamic capability interface also
  passed. Base/no-op, all nine semantic partials and one forbidden test edit were rejected; the
  forbidden edit also failed scope and test-tampering checks. All 15 official cases ran from clean
  staging commit `b50b4314aa7fd209737db46f15b38aee056bbd80` and made zero model/API
  calls. This completes the 20-task research role target but is deterministic evaluator evidence,
  not live-model agent performance or a core campaign result.
- Cooperative checkpoint fault recovery plus real subprocess kill/fresh-interpreter reclaim after
  a single-file smoke patch's only atomic postimage replacement and before outcome persistence,
  with active-owner exclusion and duplicate-mutation assertions
- One-run offline experiment and raw-derived report
- Unit/integration/recovery/viewer route tests
- Frozen 25-package dataset manifest with 5/5 calibration, 20/20 research roles, three selected
  stress sentinels and a deterministically expanded 30-run schedule. `patchloop dataset audit`
  reports `complete=true` with no freeze blockers.
- One paid Babel #1042 development-validation pilot,
  `run_c6f13dd9a1a1472d`, executed through the approved Responses API path and preserved a stable
  run ID, 113 events, 23 checkpoints, usage and terminal failure. It cost `$0.34025875` for
  73,730 input, 73,670 cache-write input and 7,326 output tokens across 20 model and 22 tool calls.
  It did not submit a patch or reach the evaluator and is not a qualified or successful pilot.
- A zero-model-call counterfactual diagnostic converted the first rejected model candidate's
  envelope to raw Git diff without changing its code edit. Patch
  `sha256:4c49b6edd0603f2e56c04c18e83fdecb3a6a5868ab40bffca198504951b01606`
  passed every official Docker verdict in evaluator run `run_4299e6b326de4c1c`. This isolates the
  tool-contract failure but is not counted as an agent submission, pilot success or repetition.
- A second paid Babel #1042 pilot, `run_de8f2a2846044c01`, cost `$0.328036875` for
  74,868 input, 74,811 cache-write input and 6,274 output tokens across 19 model and 22 tool calls.
  Its 111 events, 23 checkpoints, zero-match leakage scan and usage integrity produced a
  `qualified=true` trace artifact, but no patch was submitted and the evaluator was not reached.
  r2 pilot acceptance therefore remains false. All nine model patch candidates declared 7/7 hunk
  lines while containing 6/6; eight executed mutations failed before evaluation.
- A third separately approved Babel #1042 pilot, `run_3cb86f8d70094a11`, cost `$0.16056875`
  for 43,963 input, 43,930 cache-write input and 1,547 output tokens across 11 model and 13 tool
  calls. Its one submitted patch changed one line in `babel/numbers.py`; the official hidden,
  regression, scope and safety verdicts all passed. Its 72 events, 15 checkpoints, zero private
  matches and reconciled usage produced a qualified, accepted trace.
- A separate model-candidate pilot, `run_d4fea5e7198b4abc`, used
  `gpt-5.4-mini-2026-03-17`, medium effort and the strict 90,000-token budget. It cost
  `$0.07745325` for 66,287 input and 6,164 output tokens across 16 model and 25 tool calls.
  Prompt-token integrity, leakage, usage and trace qualification passed, but
  `evaluation_reached=false`: legacy text `DONE` attempted an invalid `VERIFY → DONE`
  transition after the required final-review order was lost. It is an immutable agent failure,
  not accepted-pilot or model-quality evidence.
- Its separately approved v2 corrective retry, `run_4a9737ec91964dca`, cost `$0.07796475`
  for 58,695 input and 7,543 output tokens across 10 model and 13 tool calls. All ten request
  pre-counts matched provider usage; responses were completed with truncation disabled. The run
  followed current-diff check, complete diff review, `finish_task`, evaluator receipt and
  `trace-qualification-v2`, but hidden acceptance failed while regression, scope and safety
  passed. It is an immutable qualified task failure, not an accepted pilot. Its stateless retry
  also retained the first rejected patch's hash/error without restoring its body, so D-037
  was not satisfied by that run. The v3 repair and hash-bound diagnostic consumer are offline-tested.
- The separately approved D-037 r3 `run_e90f7c52aa134182` cost `$0.06849375` for
  54,851 input and 6,079 output tokens across 8 model and 12 search/read tool calls. All eight
  input pre-counts matched provider usage, but event 55 used the full 4,096-token response
  allowance, including 3,989 reasoning tokens, and returned
  `incomplete/max_output_tokens`. It made no mutation, rejected patch, submission or evaluator
  run. Qualification passed 21/22 checks and failed only `prompt_token_integrity`; the D-037
  feature had zero retry episodes, so the diagnostic failed `qualification_not_passed`. This is
  immutable provider-path failure evidence, not prompt truncation, total run-budget exhaustion,
  D-037 validation/falsification or model task-quality evidence.
- The separately approved D-037 r4 `run_826c1c7fb3d242c2` cost `$0.096159` for
  84,082 input and 7,355 output tokens across 13 model and 16 tool calls. All 13 generations
  completed with exact input-count matches and truncation disabled. One patch was applied, one
  visible check passed and the run reached REVIEW, but the next exact request needed
  8,583 input + 25,000 response allowance with only 28,563 total tokens remaining. The local
  guard stopped before provider generation, submission or evaluation. Qualification passed 21/22;
  the failed `prompt_token_integrity` result is a retry-specific terminal-block contract mismatch,
  not token mismatch. Rejected candidate and retry episode counts were zero, so r4 removes r3's
  per-call output-ceiling confounder but still does not validate or falsify D-037.
- The separately approved r5 `run_0ad8676d42614fbf` executed D-041's strict 25,000/200,000
  profile once. All 18 generations completed, all exact input counts matched provider usage,
  and the run used 121,366 input plus 9,913 output tokens for `$0.135633`. Its one-file,
  one-line replacement passed official hidden, regression, scope and safety evaluation, and
  `trace-qualification-v2` passed 23/23. No mutation was rejected, so rejected candidate,
  retry episode and verified retry counts are all zero. The D-037 diagnostic is therefore
  terminal `inconclusive/retry_episode_not_observed`: this is task-success and trace-integrity
  evidence, not D-037 validation or falsification. It will not be rerun automatically.

## Implemented gates with remaining external campaign work

- OpenAI Responses adapter is contract-tested with a fake client and has two Terra failure traces,
  one accepted historical Terra live pilot, four mini model-candidate failure traces and one
  official mini task success with an inconclusive D-037 diagnostic, plus one controlled mini
  diagnostic pass.
  The accepted
  pilot is one development-validation task, not a development/core campaign result.
- `experiment-v2` now distinguishes offline smoke, Babel development-validation live pilot,
  memory-development no-memory campaign and core purpose. The live templates fix the pilot to
  `no_memory` × 1 with a $2 cap and the six development tasks to `no_memory` × 2 = 12 runs with a
  $20 cap. D-045 fixes future primary runs to `gpt-5.4-mini-2026-03-17`,
  25,000 per-call output, 21 model calls and 200,000 run-total tokens. All historical Terra
  pilot IDs, the consumed mini diagnostic suites and primary r1 remain readable but
  preflight-blocked. Primary r1 has now run once and is terminal immutable evidence, not an
  accepted pilot or completed experiment.
- Primary r1 `run_6993722014bf4e3b` used 20 model calls and 30 tool calls, with 131,266 input and
  12,038 output tokens for a calculated `$0.1526205`. All 20 responses completed, input pre-counts
  matched provider usage and truncation was disabled. It applied a one-line patch, passed the
  registered check, read the complete final diff and entered `REVIEW`, then hit
  `model_call_budget_exhausted` before `finish_task`; evaluator status is `not_run`.
  Qualification is 21/22 solely because that deterministic call-budget terminal block is not a
  versioned valid ending. A separate no-model Docker postmortem found that the exact final patch
  passes hidden/regression/scope/safety, but this does not retroactively submit or resolve the run.
- D-047 completed the offline successor contract. Exact-token reservation keeps
  `model-generation-block-v1`; next-generation model/tool/wall counter exhaustion uses strict
  `model-generation-block-v2` with durable counter/duration recomputation, reason priority,
  budget-guard actor, request/terminal/result binding and tamper rejection. Future
  primary/development/core conditions share the same total 21-call cap; it is not a privileged
  `finish_task` reserve. Corrective primary r2 `run_afd5080a77a34995` ran once and passed the
  official evaluator and qualification 23/23. The following first 12-run campaign completed but
  reached the evaluator 0/12, so both consumed suites are immutable and the campaign is diagnostic
  rather than a no-memory performance baseline.
- The terminal `dev-validation-gpt54mini-d037-r3.yaml` suite bound
  `experiment-diagnostic-v1` to its consumed execution hash. Its post-run consumer separates generic
  qualification from a `passed`, `inconclusive` or `failed` retry exercise, requires evaluator
  arrival for pass, and stores only sanitized counts/sequences. R3 validated the consumer's
  failure path but did not exercise a rejected-patch retry.
- A no-call preflight checks frozen dataset identity/role, canonical task package path,
  public/private spec hash, digest-pinned environment and observed Docker identity, clean Git
  commit, OpenAI SDK and API-key presence without the value, absence of a custom base URL,
  primary mini snapshot/medium/standard/default settings, 72-hour official pricing and budget reserve. Paid
  authorization is invocation-only and bound to its execution hash. A live capability is issued
  only after the approved plan is durably persisted. All twelve paid-pilot host preflights reached
  `ready=true`; the v4 pilot and later v4 development campaign each consumed their own distinct
  clean execution hash and approval once. Both are now immutable.
- The campaign journal is append-only and hash-chained. The first `CampaignStarted`
  exclusive-creates ownership, and each stable-ID `RunStarted` is fsynced before the corresponding
  model-call scope. A concurrent loser stops before authorization, while a hard crash leaves a guard
  that blocks automatic schedule replay. All twelve paid pilots and both completed 12-run
  campaigns produced completed hash-chained journals. Automatic resume from an interrupted journal
  is not implemented.
- Paid execution uses the approved plan's normalized suite snapshot rather than reloading the
  source path. Task package and run-manifest task/model/budget/environment identities are checked
  against the plan before `RunStarted`; replacement tests stop before the model runner.
- Legacy `trace-qualification-v1` remains byte-stable for old runs. New
  `trace-qualification-v2` additionally checks approved-plan binding, required content-addressed artifact
  references, event/checkpoint/result integrity, usage reconciliation, public/private leakage and
  pilot tool-loop evidence. Its `source_evidence_hash` binds plan, manifest, events, checkpoints,
  result and agent-visible artifact inventory and is recalculated at development-campaign
  preflight and review/index admission. Only
  qualified memory-development failures are eligible for append-only human review; classifier
  output omits hidden check IDs. The first live qualification artifact is immutable and
  `qualified=false`: evaluation was not reached, and its original leakage scan also counted 41
  publicly disclosed marker occurrences. A forensic rescan found zero API-key, reference-hash,
  `private.yaml` or `reference.patch` matches; the scanner contract was corrected without rewriting
  the historical artifact. The second artifact is `qualified=true`, but the pilot acceptance
  consumer separately rejects it because `evaluation_reached=false`. The third artifact is
  `qualified=true`, has `evaluation_reached=true`, and its official hidden/regression/scope/safety
  verdicts all pass. It is historical v1 evidence and cannot unlock the corrected v2 campaign.
- Cache usage enforces `cached + cache-write <= input`, and a malformed billed function-call
  response preserves usage/cost before terminating as agent failure. These are contract-tested
  paths, not paid-provider evidence.
- Reports mark incomplete, qualification-failed or required-trace-exercise-excluded matrices
  `analysis_ready=false`, keep
  available-case rows only as diagnostics and suppress headline, paired comparison/CI and flip
  results. The one-row accepted pilot is not a memory-comparison matrix.
- Failed started attempts retain run ID, usage including cached/cache-write tokens, calculated cost
  and terminal outcome. Historical Terra r1 and r2 exercised this path; historical Terra r3
  `run_3cb86f8d70094a11` exercised the resolved official-success path.
- Agent-visible patch application now recounts only hunk line totals and leaves the raw input/hash,
  body, context, path and deterministic policies unchanged. Policy rollback must restore the exact
  pre-call diff and zero-untracked state; rollback failure terminates as recovery error. New-file,
  rename/copy, binary and metadata-only patches remain unsupported, while the evaluator stays
  strict. Historical Terra r3 `run_3cb86f8d70094a11` reached evaluation through this corrected
  path; this remains one pilot, not a campaign-level reliability result.
- v2 patch mutation now writes raw patch and pre/post image intent CAS before touching the target,
  performs all-target preflight followed by atomic postimage replace/delete, atomically closes
  action outcome plus `PatchApplied`, and includes nested recovery artifacts in source evidence.
  Unit tests cover pre, post, multi-file mixed/partial, unknown, tampered and policy-rejected
  states. A local subprocess E2E kills the owning process after a single-file smoke patch's only
  atomic postimage replacement but before outcome persistence; a fresh interpreter reclaims stale
  `RUNNING`, avoids a second apply and reaches evaluator success.
- Evaluator manifest/result/provenance, submitted patch and verifier evidence use atomic/CAS-backed
  writes. A hash-bound receipt permits evaluator reuse after a crash before terminal commit, while
  terminal failure/result/status/event are committed together. This is local integrity and recovery
  evidence, not protection against an attacker able to rewrite the database and every artifact.
- New non-replay runs use tool schema v2 with context policy v4. The inherited submission contract binds latest visible-check success and
  final diff review to the exact current worktree hash, exposes a structured `finish_task`, delays
  phase transitions until tool success and makes two premature submissions recoverable. It also
  records review/submission lifecycle, structured patch-error stages, advisory repeat signals and
  current-diff checkpoint state. V4 additionally reconstructs a bounded investigation ledger from
  verified read/search CAS, semantic-replays exact or fully covered inspections without filesystem
  dispatch before the corrective tail, and closes all otherwise valid read/search admission at
  that tail, including requests that would have been semantic replays. Mini model-candidate
  r2 validated the final check/review/submission/evaluator
  path live, but its rejected-patch retry request omitted the candidate body and its submitted
  patch failed hidden acceptance. D-037 now restores exact rejected candidate/reason bytes on the
  first next request and qualifies them against CAS; this repair has offline evidence and one
  controlled provider exercise, but no natural-rejection rate evidence. The accepted v4 pilot
  later exercised one natural rejected-patch retry and verified 10/10 investigation ledgers, but
  semantic replay and tail admission block were each observed zero times. Those two branches
  therefore remain offline-only evidence, and one successful pilot is not a no-memory baseline,
  memory-benefit result or core reliability estimate.
  Existing v1/v2 traces and replays are not rewritten.
- v2 `finish_task` now freezes exact submitted bytes in CAS before acceptance, binds that artifact
  through `SubmissionAccepted`, evaluator input and `RunResult`, and reconciles nine tested crash
  boundaries without duplicate lifecycle or DONE transition. Mini r2 exercised the normal live
  path; crash-boundary recovery remains offline evidence.
- The no-memory development preflight rejects a pilot unless qualification v2 records the same
  primary mini model, 25,000/200,000 budget, harness commit, tool/context versions and exact
  runtime-contract hash.
  Historical model-candidate mini r2 validated much of the corrected v2 lifecycle at lower
  list-price exposure, but it could not populate the primary `pilot_run_id` and exposed the D-037
  retry-context gap. Corrective primary r2 later populated the consumed campaign, which finished
  12/12 without evaluator arrival. The v4 campaign was bound to qualified pilot
  `run_d7207fbb06184dd3` and later completed 12/12 with evaluator arrival 3/12 but SCRR 0/12.
  Offline context and investigation hardening plus the suite-specific machine gate are complete;
  terminal mini r3 failed on its per-call output ceiling before exercising the retry. Corrective r4
  bound `max_output_tokens=25,000` and `max_total_tokens=120,000` under a new diagnostic profile
  and then ran once. All responses completed, but the REVIEW request was blocked by total-budget
  reservation before submission or evaluation. The historical r4 trace has an unversioned generic
  block and therefore remains 21/22 even when all completed token telemetry matches.
  D-041 fixed the r5 contract at strict 25,000/200,000 and versioned newly emitted exact-request
  generic terminal blocks as `model-generation-block-v1`; the old r4 result remains 21/22. R5
  then passed official task evaluation and trace qualification but had zero retry episodes, so
  the D-037 diagnostic is inconclusive. D-043 then introduced a separately versioned controlled
  r6 diagnostic: it rejects the first preflight-valid prepared patch before mutation and requires
  exact next-request recovery plus evaluator arrival. The single approved r6 provider run passed
  that gate, official task evaluation and trace qualification. This proves the harness branch for
  one controlled intervention, not natural model-error recovery frequency, recovery rate, memory
  benefit or primary campaign quality. The fault-free primary r1 then exposed the call-budget
  lifecycle above. D-047 and D-048 offline contracts are now frozen. Corrective primary r2 and the
  fresh context-v4 pilot both ran and passed. The separate 12-run v4 no-memory campaign then ran
  once with its own clean hash and approval. It produced nine exact-request budget failures and
  three hidden task failures, so the next gate is offline token-aware-tail and structured-review
  work, not another live campaign.
- `model-generation-block-v2` covers admission to the next provider generation. A model response
  whose measured duration itself crosses the wall limit and a later call inside the same
  multi-tool response that encounters the tool cap still terminate through the older
  post-consumption/mid-batch `ContractError` path. Those paths need a separately versioned
  post-consumption contract before they can be claimed as v2 terminal evidence.
- The official `patchloop evaluate` CLI recomputes the full preflight and execution hash before
  issuing live capability. The lower-level host-trusted
  `issue_live_execution_authorization()` helper does not independently reconstruct the entire
  suite/task/environment/schedule plan. Direct Python callers are therefore outside the paid CLI
  enforcement claim until that internal API is hardened.
- Memory build/retrieval/freeze contracts exist; a real reviewed index still requires append-only
  review, deduplication and an exact embedding revision. The first 12-run traces remain diagnostic:
  evaluator arrival was 0/12 while repeated and already-covered inspections were also observed.
  That co-occurrence motivated D-048 but does not prove causality. The v4 campaign exercised
  semantic replay 26 times and reached the evaluator on 3/12 rows, but the tail admission block was
  never exercised and nine rows hit strict exact-request budget exhaustion. Its 0/12 SCRR is
  therefore not a usable no-memory performance baseline. The three hidden task failures are only
  provisional review candidates; the nine budget-confounded failures are excluded. Calibration
  traces are not eligible.
- GitHub adapters exist; no Issue was imported and no Draft PR was created in this session.
- HTMX is pinned from a CDN; fully offline viewer packaging would require vendoring the BSD asset.
- Digest-pinned external SWE-rebench evaluator images currently inherit the image's configured user.
  The AnyIO #1134, Param #1117, Hugging Face Hub #4056, MTPLX #21, FuseSoC #776, tox #3846,
  Dagster #33605, Kubeflow Pipelines #13112, Loguru #1297 and pyfakefs #1269 images have no
  configured `User` and
  therefore ran
  as Docker's default root user.
  Network denial, a read-only root filesystem and a read-only submitted workspace were enforced,
  but uniform non-root execution for arbitrary external images is not yet implemented. The native
  PatchLoop image's non-root isolation smoke does not prove this property for external images.
- Historical evaluator results expose only an opaque `submitted_patch_artifact_id`. New v2
  lifecycle evidence carries the complete public CAS artifact metadata and qualification verifies
  its bytes, diff hash, evaluator input and result ID. A global standalone ID catalog remains
  unimplemented for legacy artifacts.
- Tracked admission reports bind each raw `manifest.json`, `result.json` and `provenance.json` by
  SHA-256, but those per-run files currently remain under the ignored local `.patchloop/artifacts`
  store. A clean checkout can validate the report and rerun the deterministic gate, but cannot rehash
  the original raw run files until a portable evidence bundle is exported. This limitation applies
  to the existing admission-report family and must be closed before claiming clean-checkout raw
  evidence inspection.
- The checked-in live-pilot evidence records likewise bind the local plans, journals, trace
  qualifications and model candidates by SHA-256 but do not bundle all ignored raw bytes. A clean
  checkout can inspect the normalized claims boundaries and rehash the portable candidate patches,
  but cannot independently rehash the complete original runs until a secret-scrubbed portable
  evidence export exists.
- The historical Terra r3 journal for `run_3cb86f8d70094a11` is internally hash-chain valid, but
  its `CampaignCompleted.result_hash` hashes the LF result serialization while Windows persisted
  the experiment file with CRLF bytes. The qualification remains valid because its source evidence
  separately hashes the raw persisted run result. The original bytes are preserved and the runner
  now writes the exact UTF-8 bytes it hashes; this correction applies to future campaigns, not
  retroactively to that run.
- The historical Terra r3 usage wall clock is not reconstructible by simply summing model/tool event
  durations. Internal orchestration and evaluator setup contribute additional time, while
  `RunCompleted.duration_ms` covers a different evaluator-wrapper interval. Token/call/cost
  reconciliation is exact; wall-clock component attribution needs a clearer timing schema.
- `RunManifest.harness_git_commit` records the harness `HEAD` but not a full dirty-tree hash.
  The new live-suite preflight rejects a dirty worktree before execution; older admission gates used
  manually verified clean staging commits and are not retroactively covered by that enforcement.

## Dataset freeze and two diagnostic campaigns completed; valid baseline/core still pending

- The calibration fixture set is complete at 5/5, but it is excluded from memory, core metrics and
  portfolio performance headlines.
- The dataset manifest contains 25 packages: five calibration fixtures and 20 admitted research tasks.
  All research role targets are filled: memory-development 6/6, development-validation 2/2,
  same-repo core 6/6 and cross-repo core 6/6. It is frozen at
  `sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`;
  the machine audit reports `research_ready=true`, `stress_ready=true` and `complete=true`.
- The Terminal-Bench-inspired stress contract selects FuseSoC #776, AnyIO #1134 and pyfakefs #1269
  from public task structure only. Its 30-run schedule is frozen at
  `sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`
  and remains excluded from core metrics. None of those 30 runs has been executed.
- The frozen schedule is a preregistered contract, not proof that the stress runtime is complete.
  The after-model-call-10 context-reset trigger, the `persistent_state=off` arm and a stress
  matrix runner/report are not implemented.
- The CLI `worker-kill-after-patch` injector still cooperatively suspends after a durable patch
  checkpoint; the actual process termination is currently exercised by the isolated subprocess
  E2E rather than a production stress supervisor.
- Offline mock/replay resume accepts a free-lock stale `RUNNING` run, but direct OpenAI resume and
  interrupted paid campaign journal resume remain intentionally blocked. The OS lock/SQLite claim
  implementation is local-filesystem oriented and has not been validated as a distributed lease.
- The existing timeout injector synthesizes one timeout on the first registered visible check.
  It does not yet reproduce a real environment hang or specifically target a full-suite check.
- The six `python-tabulate` rows remain candidate inventory in `data/oss-candidate-ledger.csv`; none is
  an admitted research task.
- No Terminal-Bench original or constrained coding adaptation has passed PatchLoop admission. Any future
  original benchmark run is external acceptance evidence, not a core result.
- No 96-run OpenAI campaign, campaign-level cost comparison, negative-transfer review or live-model cross-repo
  result exists.
- Three capped Terra Babel live pilots were executed. r1 and r2 failed acceptance; r3
  `run_3cb86f8d70094a11` passed official SCRR and trace qualification. Their cumulative cost is
  `$0.828864375`. All three use the legacy v1 runtime. Their 2026-07-28 configured rates were
  $2.50/M input, $0.25/M cached input, $3.125/M cache-write input and $15/M output, and only the
  `gpt-5.6-terra` alias was recorded. D-045 preserves these facts but supersedes Terra for future
  runs; the completed tool-v2/context-v4 pilot uses the dated mini primary contract.
- The exact request artifact, input-token-count reconciliation and explicit
  `truncation=disabled` telemetry in D-031 were implemented after r1-r3. Those immutable Terra
  traces do not contain the new fields. Mini run `run_d4fea5e7198b4abc` exercised and passed the
  `prompt-token-integrity-v1` qualification branch but did not reach evaluation.
- Three historical one-run mini suites pinned `gpt-5.4-mini-2026-03-17`, medium effort,
  4,096 per-call / 90,000 total tokens and a $2 cap. Terminal r1 failed the submission lifecycle
  before evaluation and did not change the then-current Terra memory-development or core comparison
  contract. D-045 later changed only future primary runs. Terminal r2 reached evaluation and
  qualified but failed task acceptance and exposed a
  rejected-patch continuity gap. Terminal r3 then failed on
  `incomplete/max_output_tokens` before mutation or evaluation. None of the three exact
  experiments may be rerun. A fourth terminal suite r4 pinned 25,000/120,000 under profile v2 and
  consumed its own clean execution hash once. It raised the static response allowance rather than
  automatically retrying an incomplete response. All 13 generations completed, but the next
  REVIEW turn was locally blocked because exact input plus the full 25,000 allowance exceeded the
  remaining total budget. Exact provider retry would require a separately versioned
  original-request/logical-turn/crash-recovery contract. D-041 fixes the next diagnostic at
  profile v3, strict 25,000/200,000 and `model-generation-block-v1` without changing runtime
  reservation semantics. R4 removes the observed output-ceiling confounder but produced no
  rejected mutation or diagnostic pass. Evaluator arrival with zero retry episodes remains
  `inconclusive`; r4 did not reach the evaluator and is `failed`. R5 reached the evaluator,
  passed the task and generic qualification, and produced exactly this zero-episode inconclusive
  result. It has no synthetic rejection or automatic retry, so the result is terminal rather than
  a reason to spend again.
  The controlled r6 result validates one deliberate retry branch but does not satisfy the
  fault-free primary mini pilot purpose. Including terminal primary r1, the historical seven mini
  runs' calculated list-price total was `$0.77412075`. Corrective primary r2 and v4 pilot
  `run_d7207fbb06184dd3` bring twelve paid pilots to `$1.740790125`; adding the first 12-run
  campaign gives 24 paid run attempts and `$3.133982625`. The v4 12-run campaign adds
  `$1.84756425`, for 36 paid run attempts and `$4.981546875`. These are usage-based estimates, not
  verified invoice charges.
- PatchLoop preflights this function-tool run at official list prices. The account UI reports
  possible complimentary shared-traffic usage, but applicability to this exact function-tool
  invocation and invoice treatment has not been verified. `model_cost_usd` is therefore a
  deterministic list-price estimate, not invoice evidence; any incentive must be checked
  separately in the Usage and Costs dashboards.
- The six scripted offline runs validate harness plumbing, not model capability or memory effectiveness.
  No portfolio performance claim about a live model should be made from them.

These are deliberate hard gates. The repository rejects an incomplete core experiment manifest instead of
silently lowering the design or fabricating missing results.
