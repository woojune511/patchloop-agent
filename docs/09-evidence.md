# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## R10 contract-hardening successor (offline-qualified)

R8/v11/R10 preserves the R7 schedule, treatment, budget and cost tuple while adding API-free strict scalar,
duplicate-key, paid import-closure, runtime evidence and completion/journal checks. R7/R9 and candidate
`sha256:8b962b80...bf6c` are immutable but superseded unexecuted. No R8 preflight, candidate, provider, evaluator,
Docker or agent run has occurred.

Artifact `reports/live-pilot/artifacts/evaluator-v2-ac-successor-offline-source-qualification-r10.json` has
content/file `sha256:66bd54bc...a88b25`/`sha256:09b0d966...6d18b` (20,843 bytes), binding evaluator source
`sha256:6c6594b4...12bcb1`, successor/base suites `sha256:0c42c3a5...7d71f2`/`sha256:924e21e5...d52e77`.
Two offline builder invocations preserved bytes/mtime and recorded zero provider/evaluator/Docker/agent calls and
`execution_authorized=false`.

## R9 runtime-evidence correction and superseded R7 candidate

R9 (content/file `sha256:aeb41b81...f366`/`sha256:6d59aaae...eb22`) recorded zero provider, evaluator, Docker
and agent calls. Its R7 candidate `sha256:8b962b80...bf6c` also made no runtime call and created no paid authority;
contract hardening superseded it before execution.

## R6 sealed runtime-evidence qualification failure

The approved R6 candidate `sha256:c800f36b...e5d61` is sealed `inconclusive`. Moto A/no-memory run
`run_7c835a6aa5c2411f` resolved with hidden/regression/scope/safety PASS and an authenticated evaluator-v2 receipt,
but runtime evidence recorded `model-tool-observability-only-v1` while qualification required
`model-tool-bounded-enforcement-v1`. Its failed raw checks were `ac_fixed_runtime_contract` and
`bounded_call_guard_contract`; no model/tool budget or tail block occurred. The row used 144,240 input plus 13,648
output tokens, 14 model calls, 15 tool calls and `$0.169596`. Moto C and Babel C/A were not started.

Checked-in index `reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r6-evidence.json` has
content/file `sha256:241f4218...12a6`/`sha256:b84a2783...59d7` (7,218 bytes). It binds journal
`sha256:c733655c...e327`, final result `sha256:2379bcab...f7f`, qualification `sha256:a3bfd90b...8d4c`, runtime
contract evidence `sha256:62b05190...880e` and receipt `sha256:027e2d03...39d0`. R6 is consumed and cannot retry,
resume, repair or transfer approval to R7.

## R5 sealed post-evaluator qualification failure

The approved R5 candidate `sha256:b8d156c6...a1627` is sealed `inconclusive`. Moto A/no-memory run
`run_2007cde54b464938` resolved with hidden/regression/scope/safety PASS and an authenticated evaluator-v2 receipt,
but post-evaluator qualification incorrectly required the legacy null-call/aggregate-only profile. Its only failed
raw checks were `disabled_call_guard_contract` and `frozen_model_contract`; there were no model/tool budget or tail
blocks. The row used 173,193 input plus 14,031 output tokens, 16 model calls, 21 tool calls and `$0.19303425`.
Moto C and Babel C/A were not started after `QualificationFailureHalt`.

Checked-in index `reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r5-evidence.json` has
content/file `sha256:01775e68...655`/`sha256:fa49986e...832c` (6,605 bytes). It binds journal
`sha256:4ea90b63...9c7d` (9 events), prepared/final result `sha256:1edd9e78...f9f` (44,710 bytes), trace
qualification `sha256:07b49db7...b18` and receipt `sha256:85a344ee...f22d`. R5 is consumed and cannot retry,
resume, repair or transfer approval to R6.

## R4 sealed provider-before-dispatch terminal and R6 predecessor

R6 qualification is the immutable source gate for R4. Candidate `sha256:be4ea2e4...8d7124` consumed its approval,
then sealed `inconclusive` before provider dispatch because paid-plan revalidation selected the legacy budget; cost
was `$0` and three rows did not start. Index
`reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r4-evidence.json` binds the exact source,
plan, journal and result hashes. R4 cannot retry, resume or transfer approval.

## R5 qualification and R3 sealed readiness attempt

The checked-in runtime index is
`reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260813-r3-evidence.json`. It binds execution
`sha256:c6506a33...374a2a`, schedule `sha256:bae5cd50...dd83`, cost control `sha256:d161820f...dc15`, external
journal `sha256:cff6c0e7...4f69` and result `sha256:d94b0a29...edecf`; raw artifacts remain under `.patchloop`.

R3 is canonically `SEALED`/`inconclusive`: Moto A/no-memory resolved with all four verdicts and typed safety PASS,
receipt `sha256:14e16e95...8418`, and `$0.10254975`; Moto C/structured ended `agent_failure` before evaluator at
2,963,919/3,000,000 tokens and `$3.374763`; Babel C/A were not started. Total settled cost is `$3.47731275`.
No retry/replacement, held-out A/C or B/D ran. Complete-matrix analysis and memory-effect authority are false.

The preceding R2 attempt is separately sealed at `$0`; R3 neither repairs nor replaces it.

## Historical V/D predecessors — compact index

- V23 passed Docker and both typed frames, then `diagnostic_result_invalid` produced `ERROR(child_checker_error)`;
  accounting is unknown and retry/resume is false.
- V24 is an offline fixture for v22 order loss, not the discarded V23 input. V25 is an unused superseded gate.
  V3-V22 exact errors, source-only corrections and observation limits remain in `reports/`; none is current authority.
- D-142 gate `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914` is source-qualified,
  unactivated and deferred after 170/170 mocked tests. D-141 and D-129-D-140 are consumed; D-121 is deferred.
- Evaluator-v2 commit `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6` is a predecessor. Current R10/R8, superseded R9/R7 and sealed
  R6/R5/R3 supersede its no-live-result boundary without changing historical bytes.

Exact tuples remain canonical in `reports/`, Git and the D-121 archive; predecessors cannot retry or backfill.
