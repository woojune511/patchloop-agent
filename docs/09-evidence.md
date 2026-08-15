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
- Contract R11 at `reports/heldout-ac/artifacts/heldout-ac-contract-source-qualification-r11.json` is 22,246 bytes;
  file/content/source are `sha256:8373844f7d548ecfa98d32ea712d7626cd4e1f6ced021af9c1253f3af08be42f`/
  `sha256:140c747effd5621cc33ba2d2a0187774332fa31b50b978f4791039bb05f06755`/
  `sha256:c7a7bcbb6ee605b1630733bdcbf88e4e42cfe97a354372a1f51fa45661f2dca7`.
- Binding R11 at `reports/heldout-ac/artifacts/heldout-ac-binding-adapter-source-qualification-r11.json` is 6,353
  bytes; file/content/source are `sha256:9176a0671133985e3b01cfe540ab55a6a014e1db4a1a117602a7d774518ba7f8`/
  `sha256:5d2b92fe34be90aabda0f2fc3fd90ff6136c5e794e362299b33f35f707aee762`/
  `sha256:567358425e9508d358609775413568201d2161dabde99f5a8c60ca2cbe8ab202`.
- Materialization R7 at `reports/heldout-ac/artifacts/heldout-ac-task-pricing-materialization-r7.json` is 53,250
  bytes; file/content/source are `sha256:7b9bb78b89e18e067476cdf172214fb4588d3f96b68427f6f8eb49761d801425`/
  `sha256:2a32a034dc89a43e0d20a9dc82959d0574c82c0915a6f105f31291d7af962be4`/
  `sha256:7f2218a7a9e3fcafdc2a1746b292ec539eeeb05994101ba0f1680616226160a8`.
- Execution R8 at `reports/heldout-ac/artifacts/heldout-ac-execution-source-qualification-r8.json` is 20,256 bytes;
  file/content/evaluator-source are `sha256:c8e7cc989d9730c0b9671b973dd8c79d58a39b425d3975bfc729832e9a49dfeb`/
  `sha256:23d0c31bcc00a8b66dd7ab6518dffa3afacb6cbbad284a5ab4d995349098fd27`/
  `sha256:7de36eb66c8015de4253264f322d39b0cfd3cfef9c248da188fc1a88838fc4c6`.
- Preflight/dispatcher R16 at `reports/heldout-ac/artifacts/heldout-ac-preflight-source-qualification-r16.json` is
  25,319 bytes; file/content/evaluator-source are
  `sha256:033fd414cfc0b2499171e91a8b0e9e82e823f452520dfe42f54c1c9e8469e1f5`/
  `sha256:a15c6c0ade8bd9bb1f57cacd07ec6dbfcbb84bfc1b622b642bb4f332873b6742`/
  `sha256:bbc790eb53fbc7883a454d963ccc2e6195e4f73f160f162c814aec2efade92ad`. These five qualification artifacts
  themselves made no candidate, approval, observation or spend; the later R16 candidate and campaign consumed the
  chain as recorded below.
- The immediately preceding R10/R10/R6/R7/R15 zero-authority chain remains append-only. Its exact content hashes are
  `sha256:c0412709...7a32`, `sha256:27283c8a...c17626`, `sha256:61f65a54...e419fb`,
  `sha256:783b757d...77e80a` and `sha256:f0e100d4...6809c`; it is superseded, not rewritten.

## Consumed held-out predecessors

- R7 candidate `sha256:2f51935b...b2afa` consumed `$252`/`$275` and sealed 0 settled/1 unsettled/47 not-started
  after CRLF/LF qualification-byte drift. Its index content/file is
  `sha256:0a421d5baf26abd6fa1092dd6c2c6a5f064950be53ba9a2a3f5fd93b7e639157`/
  `sha256:dd50a53a1c19e1214a575c3b37b82400b8961bf9a38e72f39a2aa87b3390b906` (7,854 bytes).
- R11 candidate `sha256:f48a0de...a6b0` consumed `$252`/`$275` and sealed 2 settled/1 observed-unsettled/
  45 not-started: `$0.15699525` settled, `$0.41801625` observed-started. Historical `CONTRACT_ERROR` is preserved;
  successor diagnosis is `EVALUATOR_CONTROL_CONTRACT_COLLISION`, with zero agent-visible marker matches. Its index
  content/file is `sha256:ff66718e1fa403baf0978de1b0e43625aac0a046117e85c5f42fb0cc4312db9b`/
  `sha256:1badf8a78ba142f9868a3b9e836fa83df7beb0248f9c5e745fd205fd0185f48c` (18,525 bytes).
- R14 candidate `sha256:67475f57...307fd` consumed `$57.60`/`$60` and sealed 0 settled/1 observed-unsettled/
  47 not-started at `$0.126342`. Historical `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` is preserved; successor
  diagnosis is `TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH`. Exact final/content/journal hashes are
  `sha256:77a8a129...ed34`/`sha256:1860badb...6619`/`sha256:8f436552...30a6`; index file/content is
  `sha256:21cda8f9...cd7b`/`sha256:1b602c19...5341` (12,856 bytes).

All are append-only attribution only: zero runtime calls/cost, no retry/resume, no official
analysis and no memory claim.

## R15 held-out live inconclusive campaign

Candidate `sha256:e11ece5552e2f574ee334ec98a93a9929732df7592096bcd0478717dfd64f8bc` at commit/tree
`2571a7a31bb0071bf1d984ea5e6ff852c1713b13`/`e6d3f6ded652c33eb105c2ee3a24e1dbcdc5a635` consumed one exact
48-row `$57.60`/`$60` approval. It sealed 2 settled, 1 observed-unsettled and 45 not-started. Settled cost was
`$0.2002335`, observed-unsettled cost was `$0.9118785`, and total observed-started cost was `$1.112112`.

The third row reached a typed `MODEL_GENERATION_BUDGET_EXCEEDED` terminal. Its persisted result intentionally exposed
only sanitized `AGENT_SUBMISSION_FAILED`/`agent`, while exact `ModelGenerationBlocked` and `RunFailed` events carried
the binding details. Historical campaign reason `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` remains unchanged;
post-runtime attribution is `TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH`. The successor makes V2
qualification version-aware and does not reauthenticate, reclassify, settle or resume R15.

The exact final-file/content/journal triple is
`sha256:6cd811c27ec8533a034f95a40893780a2e90a0b5f1d35ad0a2db950691414269`/
`sha256:d6e78bd93e74aad332e93b24a7d5cacfab397978a52bfea82d59da251eeb05a8`/
`sha256:5459d339d2afc3d309e5c747edcaf0823df0e65fa3618e95c61b3776893be4bb`.
Append-only index `reports/heldout-ac/artifacts/heldout-ac-r15-campaign-inconclusive-r1.json` is 12,209 bytes;
file/content are `sha256:7aaca2be0797ea36f12e125dc85dd582bdc5f63ad5afd7449cc2d2cf77d46c54`/
`sha256:85b211c637eeff05805c8bef1ba3790a6beab8cef98a8680c48fa74f496a56eb`. It added zero runtime calls and `$0`;
retry, resume, official analysis and memory claims remain closed.

## R16 held-out complete matrix

Candidate `sha256:24044c1ed525458446f1c97d94f52331082d74051f5c6d680da995ea9aa48813` at commit/tree
`d82291d9332894a4e0b0fc0618e3464bfc9a77e6`/`827eb2a0640be0ccb816affde8ff7fa2b148e0b4` consumed one exact
48-row `$57.60`/`$60` approval. Its no-call preflight file is 66,841 bytes with
`sha256:0e9b927cdd64413e926f5d4ca478895d9a0e4097ed785042ee5602a680552c4c`.

The campaign completed 48 settled rows, 0 observed-unsettled, 0 not-started and 0 confounded for `$27.24465825`.
It recorded 15 resolved, 14 task failures and 19 typed agent failures, with no retry/replacement/resume. Exact runtime
bindings are:

- plan `sha256:e8e9ae072eaf7c68798572c1ae124cff90bcc67a33fc4a872c19b00d7478bf94` (83,599 bytes);
- journal `sha256:40668bfa7b1b2142c952f2a83d12fd50aa0dbadf4d984e7c88b23c5378d33669` (122,930 bytes),
  99 events ending `CampaignCompleted` at `sha256:c7ddea5ffe5411433849668c7bc54fad57d8b2fb4a9836563c769d573d989e52`;
- prepared file/content `sha256:c459886b3b65215623e4a9320f6ffe5a5f8216dda66e35d91f4bf84fdc43db2f`/
  `sha256:61d791264549833b5e0ec07bdd1cf68f3289e9ca374518c70e29a1d350c6dff6` (1,202,867 bytes);
- final file/content `sha256:6a6203c049e838675925a519a8d2bd7933823779b7c5cbee850d6e18a1bbd91f`/
  `sha256:2e7466eba5c5cbd9e8fcbc5fae655972b78c9854ff83e9c906881337f7f985e4` (1,203,484 bytes).

Authenticated completion is `sha256:954ccd1ead1e826fcd07c435303f1b8c859b58ee3c742b1580ec94c675d88a95`;
the official analysis envelope is `sha256:7cd2e7657b2b7d878c5874f9a1e29f0aa5dea58fe8a135c9706ee903c7ccc260`.
No-memory succeeded 8/24 at `$12.380361`; structured succeeded 7/24 at `$14.86429725`; C-minus-A is `-1/24`.
The deterministic descriptive stability interval is `[-1/4, 1/6]`, sign-flip sensitivity is `p=1`, benefit flips
are 3/24 and negative-transfer flips 4/24. Same-repo effect is 0 and cross-repo effect `-1/12`. Causal/general
memory-benefit and broad-generalization authority are false.

Append-only index `reports/heldout-ac/artifacts/heldout-ac-r16-campaign-complete-r1.json` is 10,375 bytes;
file/content are `sha256:999fa9e42f010b03b96013d089f662ad3f50b1c5c6469b2aa8ddb901c522391e`/
`sha256:945e8e9ff1df60a255d20fb406ca7b7ab20ca16a3b50da5cbce12f2fb38a6521`. It independently revalidated exact
source/runtime bytes and the matrix summary, added zero runtime calls and `$0`, and grants no rerun or future authority.

## R8 complete development-readiness matrix

Candidate `sha256:60c679083ad7b995918e2ba5de79843be8b03ce0511b67eb859da437f16cff9e` bound source
commit `a4f00f8565c840588b120d91e730427bb51166b5`, Moto A/C + Babel C/A, `$15.30` reserve and `$18` cap. Four
receipt-qualified rows passed all verdicts for `$0.3664215`; no retry occurred. Final/journal hashes are
`sha256:8dbcb60a...cc2878`/`sha256:f05dc041...0446a`. The original completion adapter misread valid v2 rows as
unclassified; append-only strict index `reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json`
has content/file `sha256:0ef31d2b...aade83`/`sha256:5035421a...b7c62c` (19,557 bytes) and recomputes 4/4 success.

| Task | A tokens/cost | C tokens/cost | C minus A |
| --- | ---: | ---: | ---: |
| Moto | 121,601 / `$0.1086345` | 83,604 / `$0.07001175` | -37,997 / `-$0.03862275` |
| Babel | 108,534 / `$0.115158` | 72,493 / `$0.07261725` | -36,041 / `-$0.04254075` |

Both conditions resolved both tasks. These two one-repetition development pairs authorize descriptive analysis only;
memory-effect, retrieval, held-out, core and B/D authority are false. R8 is consumed.

## Compact historical index

- Development R3-R6 are sealed inconclusive. R3 settled `$3.47731275`; R4 stopped before provider dispatch at `$0`;
  R5/R6 each observed one qualified Moto A before distinct runtime-contract mismatches. Their exact candidates,
  results and index hashes remain in `reports/live-pilot/`; none may retry, repair or transfer approval.
- R10 source qualification content/file is `sha256:66bd54bc...a88b25`/`sha256:09b0d966...6d18b`; R9 and its
  unexecuted candidate are superseded. Post-run correction source requires a new identity before future execution.
- V23 ended `ERROR(child_checker_error/diagnostic_result_invalid)`; V24/V25 are offline/superseded evidence.
  D-142 is source-qualified, unactivated and deferred; D-129-D-141 are consumed. Exact historical tuples remain in
  machine artifacts, Git and the D-121 archive and cannot be backfilled.
