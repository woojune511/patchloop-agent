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
- Historical contract/binding/materialization/execution/preflight seals remain append-only. Current contract R7 has
  content/file `sha256:27cfb3d91c326c1e767a6e63580941d48e14a7872783db39dbdacdd075f08ea5`/
  `sha256:fec1c4ea12fdd8399f989ad9b0dba02a22071604eb8fc431f821ae5900ed36fa` (20,544 bytes), source
  `sha256:cb478787f0845324b305c6208bc70ab29c81dc739c84eb03c0c757fbe2f05dbf`.
- Binding R8 content/file is `sha256:ac75004d98f647dbedf00819b93b40e85119c4c1deb244080f42c59dda48918c`/
  `sha256:4fa0dc9629a7fa2030c1af4f3831ecc169330360c6f0813d5778517723c39b13` (5,674 bytes); source
  `sha256:20eb314516985fd6aa8e7f1970fd754bb3c839607f5b73b55f526b305662118c`.
- Materialization R4 content/file is `sha256:7c6ecc31b471da83cf46ddb5a3fb687008e4a6648ae55485d0109e0d6114af58`/
  `sha256:37c5cb805e137e55f5b0a11b3a3235dc0514aa2a77938abfc6d74695113d5380` (52,056 bytes); source/task bindings
  `sha256:010b8c1fd2d46c58a56976fd1ce750f4640e54a8d38758beecbe3c75e896b888`/
  `sha256:10505056de7f4bd95a06f9c3a16414ce120442c485413e52d113c2aba4c5157f`. It retains R1's sole public price GET and
  `$0.75`/`$0.075`/`$4.50` prices; added GET count is zero.
- Execution R5 content/file is `sha256:b2d6307f9e94f4324faf3d11ade14845c8f8d22c645a694bb729f2e13d7e9b2e`/
  `sha256:e396b4e121c53f7aca27dad3283c035aaa077265f1c0065bed6c9124e5a05fcf` (16,921 bytes); evaluator source
  `sha256:2037b16643a44c5e2434d5147d6ebeb04bca5f65402d9ca8f37373694ab66c84`.
- Current preflight/dispatcher R13 content/file is
  `sha256:5bbb8e77d88684d1a67f7f40d5436d01d9ab1a0f6e286385e1e47959485eab61`/
  `sha256:f55cf62163b68f0a5d1d890a58b54dfa31f60ed90ac0da466bfe9b08e35b922f` (21,539 bytes); evaluator source/validation
  `sha256:103b13f61031cde96a74f6af09f86a5f3d4a550af3664d0279f1a9cdafcc8671`/
  `sha256:7e544db90de1bbff5acca45e8aaec6e9b1e18a34b05a4f388bdffa4503149698`. R12 and intermediate seals are preserved
  invalidated predecessors. R13 made no observation, candidate, plan, journal, call or spend.

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
