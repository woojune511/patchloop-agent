# Evidence index

Machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## Held-out A/C preregistration

- Preregistration: content `sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74`;
  file `sha256:f6d9d015329823f3f888aac5f15296b2ddefda9e45b5d5501b8d94587bb11d8f` (31,338 bytes). It freezes
  48 rows and `$252`/`$275` planning cost but grants no authority.
- Suite: content `sha256:1d023e8837e99889d76acf6f3a2d970261cb7aa4b3e978c84cef2ef5cf517aaa`; file
  `sha256:27157e26881cc277a9026e51d22a6f21fbf5bbb8f6c1c09eaa89aec607e52534` (13,348 bytes). Plan: content
  `sha256:b2058c48de3f2b4d13df872d7fd19a325c3a76ffb5ef24974310409100cb8885`; file
  `sha256:901f898d7f6f81b00e8840160b3efde2cc4fb7d8f4625c6188ea7235de264695` (2,466 bytes).
- Budget amendment content/file is `sha256:9df732d5bf8d5c754ea47084e5dbf9c490f78882bcc9fbc6b0c5d2e2b8bf220d`/
  `sha256:a2532b466c55659c72e6602a37a6a6114ad42d90c5fd78502ad976f9384f9e53` (7,248 bytes). It binds development
  evidence only, equal 1M/100k/1.1M token limits and `$57.60`/`$60`, with all runtime authority false.
- Contract R10 at `reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r10.json` is 22,080 bytes;
  file/content/source are `sha256:3e98b35ebae9b7d4a50a23e4f984fdf4be213702cb296c55394ef1e8ceb361e0`/
  `sha256:c04127095d998ee345e4449f897de5b5c6666c75ade6f12d2784e59254b97a32`/
  `sha256:30ad36dca70f12ed10b27585c1a33751dabd687f7da72075e089f5a5481334fd`.
- Binding R10 at `reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r10.json` is 6,376
  bytes; file/content/source are `sha256:376e94d84b7bdb5f0a2ec507fcc12e2016fbd718817e05a913c86824bc3e2ef4`/
  `sha256:27283c8a1d1075a9e22f395eed0d845069531e230d30aab2aeda75dc76c17626`/
  `sha256:3f01c1817a42daf35081926481c808887422d15e331138e90134069cdc17ba07`.
- Materialization R6 at `reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r6.json` is 53,250
  bytes; file/content/source are `sha256:1a3568e372c9b3af1e384addfb3b5d8351138625072b3af95ccc6290bed3d975`/
  `sha256:61f65a54891ef60c07c1edbadd67040cdf5d31e21e4c6e1d3ac97d7f94e419fb`/
  `sha256:7135f82bebfee3b635cd67347fee258be57fa2ef15cce09e3df838897c197131`.
- Execution R7 at `reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r7.json` is 20,007 bytes;
  file/content/evaluator-source are `sha256:4202aa19b148e9e3567cb79c3b928fe0bfeb08a2b2d980f46e9899ff6489e7f1`/
  `sha256:783b757d07b76d943899ff3a2d66d1033fc84b44026e4472f263495f9877e80a`/
  `sha256:c06109120a7b9f5821755a89aae42ff6e1e734470707913882414282773d5f83`.
- Preflight/dispatcher R15 at `reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r15.json` is
  24,713 bytes; file/content/evaluator-source are
  `sha256:0ed3be6f51213867acc4f27560f87ae33103e5ee60deb237affe942a7ebd6cbc`/
  `sha256:f0e100d44f713cde134882025481b0038bfb0b4d880f4192e0558dc806e6809c`/
  `sha256:d04b90cc92c8888b1e21f6911b201511180230e62db055d5dd5bb4cb3fbac95c`. This R10/R10/R6/R7/R15 chain is
  source-qualified only and made no candidate, approval, observation or spend.

## R7 held-out live inconclusive campaign

Candidate `sha256:2f51935b...b2afa` at commit `f6a1bda` consumed one 48-row `$252`/`$275` approval. Row 1
(Loguru/structured) resolved with four PASS verdicts; usage was 44,009 input, 7,388 output, 6 model/6 tool calls and
`$0.06625275` token-derived but unsettled cost. Its qualified trace used 393 CRLFs (12,868 bytes,
`sha256:06819ea6...f95`) while the adapter required LF bytes (12,475 bytes, `sha256:91a3fbd1...fee5`), sealing
0 settled/1 unsettled/47 not-started and no analysis. Journal/final file hashes are `sha256:8e196881...7472`/
`sha256:70657e66...8e04`. The checked-in index content/file is
`sha256:0a421d5baf26abd6fa1092dd6c2c6a5f064950be53ba9a2a3f5fd93b7e639157`/
`sha256:dd50a53a1c19e1214a575c3b37b82400b8961bf9a38e72f39a2aa87b3390b906` (7,854 bytes); it is not an A/C result.

## R11 held-out live inconclusive campaign

Candidate `sha256:f48a0de27f8b3e46e627d957dfd714b395c94855587ccfc36e78028fa711a6b0` at commit/tree
`2f9f920eeb63a2704b387e78af74982b98f7136d`/`d67be34a7de21c4d4ebc8025e9d070887dd47cf0` consumed one 48-row
`$252`/`$275` approval. Its historical R11 source qualification content/file was
`sha256:13e3124c7f0ca0b3ed7afca68ea0f523f2eea4dc4c358cef37db29ac53d0b22b`/
`sha256:45b21684520968903ab57afc7a4e0d9f4e66022ad0752140d24b988ba0df747f` (19,359 bytes), evaluator source
`sha256:50b615250f566cd0cb580ab8f16a000d2c23105d10d5c6c9b9f36e0a2ff9ce3a`.

Loguru/structured resolved with four PASS verdicts and `$0.0972915`; Loguru/no-memory settled as hidden/safety FAIL
with `$0.05970375`. Its 14 marker redactions were evaluator-private; agent-visible event and patch matches were zero.
Dagster/no-memory completed agent submission but evaluator status was NOT_RUN; durable usage cost was `$0.261021`.
Historical runtime code is `CONTRACT_ERROR`; successor post-runtime diagnosis is
`EVALUATOR_CONTROL_CONTRACT_COLLISION`, not a task or memory-effect failure.

Append-only correction index `reports/heldout-ac/artifacts/heldout-ac-r11-campaign-inconclusive-r1.json` has
content/file `sha256:ff66718e1fa403baf0978de1b0e43625aac0a046117e85c5f42fb0cc4312db9b`/
`sha256:1badf8a78ba142f9868a3b9e836fa83df7beb0248f9c5e745fd205fd0185f48c` (18,525 bytes). It records 2 settled,
1 observed-unsettled and 45 not-started; settled cost is `$0.15699525` and total observed-started cost is
`$0.41801625`. Runtime bytes remain unchanged. Correction activity was zero calls and `$0`; no complete matrix,
official analysis, retry or memory claim is authorized.

## R14 held-out live inconclusive campaign

Candidate `sha256:67475f578338026bc0c66ff3904ef1adfaaae8a33e2cba824d0f88a5d57307fd` at commit/tree
`0fc8c1dbec71b292296d0ca5dd520c8b226fd1b6`/`3c37a307129f4dbebba9536dd44cac148be7a3cf` consumed one exact
48-row `$57.60`/`$60` approval. It sealed 0 settled, 1 observed-unsettled and 47 not-started with `$0.126342`
observed-started cost. The observed Loguru/structured row completed evaluation as hidden FAIL and carried an
authenticated trace-qualification-v2 budget of 1M input/100k output/1.1M total.

Historical reason `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` and phase `authentication` remain immutable. Deterministic
post-runtime attribution `TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH` records that completion compared the
candidate budget with the immutable suite's 4M/500k/4.5M tuple. It does not reauthenticate, settle, reclassify or
change the underlying task outcome. The exact final-file/content/journal triple is
`sha256:77a8a129f031041c447bc46ef8a29446bf1c39bae9ef9404cf1598f3f037ed34`/
`sha256:1860badbfc1d21b0ec244e44b04dc768b5c8530d7db179a2765c89312eec6619`/
`sha256:8f4365522e647f916dcfc17fb0c4a9101b4dab1c56051a31ac03209734ce30a6`.

Append-only index `reports/heldout-ac/artifacts/heldout-ac-r14-campaign-inconclusive-r1.json` is 12,856 bytes;
file/content are `sha256:21cda8f99aa835b196aa54cc6f7ad2483942f43d986fd935ce511a0d6974cd7b`/
`sha256:1b602c1900ddfbd6867c81818d48ee9ada72f0b2fb2503d5eb83db7faf0e5341`. It added zero provider/evaluator/
Docker/SDK/agent calls and `$0`; retry, resume, reauthentication, official analysis and memory claims remain closed.

## R8 complete development-readiness matrix

Candidate `sha256:60c679083ad7b995918e2ba5de79843be8b03ce0511b67eb859da437f16cff9e` bound source
commit `a4f00f8565c840588b120d91e730427bb51166b5`, Moto A/C + Babel C/A, `$15.30` reserve and `$18` cap. Its one
approval produced four resolved, evaluator-v2 receipt-qualified, trace-qualified and cost-settled rows with all
hidden/regression/scope/safety verdicts PASS; no row retried or was replaced. Total cost was `$0.3664215`.

The immutable final/prepared result is `sha256:8dbcb60a...cc2878` (138,156 bytes); journal is
`sha256:f05dc041...0446a` (15 events, 21,654 bytes). The raw completion adapter accepted only
`trace-qualification-v1` and therefore misclassified four valid `trace-qualification-v2` rows as unclassified,
storing `passed=false`, `official_evaluator_runs=0` and `task_failures=-4`.

Final portable strict index
`reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json` has content/file
`sha256:0ef31d2b...aade83`/`sha256:5035421a...b7c62c` (19,557 bytes). It binds plan, hash-chained journal,
prepared/final result, durable results, qualifications and receipts. Offline recomputation yields 4 official v2
runs, 4 successes, 0 failures and 0 unclassified without rewriting runtime evidence or making any
provider/evaluator/Docker/agent call. Earlier correction indices remain append-only predecessors.

| Task | A tokens/cost | C tokens/cost | C minus A |
| --- | ---: | ---: | ---: |
| Moto | 121,601 / `$0.1086345` | 83,604 / `$0.07001175` | -37,997 / `-$0.03862275` |
| Babel | 108,534 / `$0.115158` | 72,493 / `$0.07261725` | -36,041 / `-$0.04254075` |

Both conditions resolved both tasks. These two one-repetition development pairs authorize descriptive analysis only;
memory-effect, retrieval, held-out, core and B/D authority are false. R8 is consumed.

## R10 source qualification and R9 predecessor

R10/v11/R8 preserved R7 schedule, treatment, budget and cost while adding strict scalar, duplicate-key, paid
import-closure and evidence checks. Artifact
`reports/live-pilot/artifacts/evaluator-v2-ac-successor-offline-source-qualification-r10.json` has content/file
`sha256:66bd54bc...a88b25`/`sha256:09b0d966...6d18b` (20,843 bytes), evaluator source
`sha256:6c6594b4...12bcb1` and successor/base suite `sha256:0c42c3a5...7d71f2`/`sha256:924e21e5...d52e77`.
It qualified the executed bytes; post-run correction source needs a new identity before future execution.

R9 content/file `sha256:aeb41b81...f366`/`sha256:6d59aaae...eb22` and R7 candidate
`sha256:8b962b80...bf6c` recorded zero provider/evaluator/Docker/agent calls. R7 is superseded unexecuted.

## Sealed R6, R5 and R4 attempts

- R6 candidate `sha256:c800f36b...e5d61`: Moto A `run_7c835a6aa5c2411f` resolved and passed evaluator v2,
  but runtime evidence wrote `model-tool-observability-only-v1` instead of required
  `model-tool-bounded-enforcement-v1`; Babel and Moto C did not start. Usage was 144,240 input + 13,648 output,
  14 model/15 tool calls and `$0.169596`. Index content/file is
  `sha256:241f4218...12a6`/`sha256:b84a2783...59d7` (7,218 bytes).
- R5 candidate `sha256:b8d156c6...a1627`: Moto A `run_2007cde54b464938` resolved and passed evaluator v2,
  but qualification required legacy null-call/aggregate-only limits; remaining rows did not start. Usage was
  173,193 input + 14,031 output, 16 model/21 tool calls and `$0.19303425`. Index content/file is
  `sha256:01775e68...655`/`sha256:fa49986e...832c` (6,605 bytes).
- R4 candidate `sha256:be4ea2e4...8d7124`: paid-plan revalidation selected the legacy budget, so Moto A
  terminated before provider dispatch at `$0` and three rows did not start. Its index is
  `reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r4-evidence.json`.

All are sealed `inconclusive`; none may retry, resume, repair or transfer approval.

## R3 readiness predecessor

Index `reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260813-r3-evidence.json` binds execution
`sha256:c6506a33...374a2a`, journal `sha256:cff6c0e7...4f69` and result `sha256:d94b0a29...edecf`. Moto A resolved
with typed v2 safety and cost `$0.10254975`; Moto C ended before evaluator at 2,963,919/3,000,000 tokens and
`$3.374763`; Babel C/A did not start. Total settled cost was `$3.47731275`. The matrix is `inconclusive`, with no
retry/replacement, held-out A/C or B/D activity.

## Compact historical index

- V23 passed Docker and both typed frames, then ended `ERROR(child_checker_error/diagnostic_result_invalid)`;
  V24 is an offline order-loss fixture and V25 an unused superseded gate.
- D-142 gate `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914` is source-qualified,
  unactivated and deferred after 170/170 mocked tests. D-129-D-141 are consumed.
- Evaluator-v2 commit `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6` is a predecessor. Exact historical tuples
  remain in `reports/`, Git and the D-121 archive and cannot be backfilled.
