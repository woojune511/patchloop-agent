# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. PatchLoop에서 작업하는 coding agent는 구현 전에 이 문서와 현재 milestone 문서를 읽어야 한다.

## Mission

재현 가능한 평가 기반 위에서 single coding agent를 실행하고, trace-driven failure memory와 recovery 정책의 효과를 공정하게 비교한다.

Repo Maintainer와 Draft PR은 데모다. 평가 harness와 실제 실험 결과가 제품의 핵심이다.

## Current state

- 현재 milestone은 `D-121 exact D-120-bound hash-only isolation successor preparation materialized and one fresh
  two-session execution authorization candidate sealed; actual successor run, trusted cutoff, projection isolation,
  independence, matcher, retrieval, agent and core remain closed`다. Exact D-120 candidate 승인은 D-121의 new-only
  module/script/test, offline tests, container를 시작하지 않는 Docker readiness와 execution-authorization candidate
  준비에 한해 소비됐다. Approval receipt는
  `reports/memory-development/d121-isolation-successor-preparation-approval-receipt.json`, receipt/body ID
  `d121preparationapproval_0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79`/
  `sha256:0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79`, 14,662-byte file SHA
  `sha256:5a5592c2fff7deae63c50482d109c0d8e79ff4016fb96aaa8cb5a7b442d83606`다. Readiness는
  `reports/memory-development/d121-isolation-successor-readiness-preflight.json`, readiness/body ID
  `d121readiness_8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12`/
  `sha256:8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12`, 32,423-byte file SHA
  `sha256:3423bf9af71d9b69579115d65a2b67d2bdb39363748e40a9cb78bdd461ad94e6`다. Candidate는
  `reports/memory-development/d121-isolation-successor-execution-authorization-candidate.json`, candidate/body ID
  `d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`/
  `sha256:b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`, 11,046-byte file SHA
  `sha256:0e8ea35d4fda06ecfba180150062b873ada5b11dd98df7bd0416c557777db1c5`다. Source gate는
  `reports/memory-development/d121-isolation-successor-authorization-source-gate.json`, gate/body ID
  `d121_711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592`/
  `sha256:711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592`, 15,514-byte file SHA
  `sha256:e9c05396e10770c4290b2e57235f32da6fe3997afcd3fdb109c3697cea773b50`다.
  No-start readiness는 synthetic nonopaque sentinel 하나로 Docker command 8회와 `create` 1회만 수행했고
  start/run/exec, probe execution, opaque source filesystem access/read, record parse/read와 residual container는 모두
  0이다. Created-state inspect에서 configuration realization만 확인하고 container를 제거했다. 따라서
  `docker_configuration_realization_verified=true`지만 `hash_only_isolation_profile_verified=false`, actual run
  unauthorized/count 0, `trusted_cutoff_anchor_verified=false`, `record_projection_isolation_verified=false`,
  `independent=false`다. D-121 focused 47/47과 D-119+D-121 82/82가 통과했다. D-121 materialization 뒤 D-120
  focused의 historical successor-path absent-state assertion 7개가 실패하는 것은 예상된 post-successor 결과이며
  D-120 fix나 product regression이 아니다. Next gate는 exact D-121 execution candidate ID/body/file SHA의 별도
  승인으로 정확히 한 번의 fresh two-session hash-only successor run만 허용한다. D-119 retry/resume/repair가 아니며
  automatic retry, retrieval/runtime injection, agent/provider/evaluator 또는 core/analysis를 열지 않는다.
- Historical D-120 state: `D-120 exact D-119 partial consumed failure sealed and D-121 cleanup-successor preparation
  authorized while D-119 retry, trusted cutoff, independence, matcher, retrieval, agent and core remained closed`다.
  D-120은 D-119 immutable receipt/preflight/journal을 읽어 `PARTIAL_CONSUMED_FAILED`와 `UNSEALED_UNKNOWN`을
  append-only로 봉인했다. Preflight/candidate/source gate ID/body/file SHA는 각각
  `d120preflight_cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/
  `sha256:cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/
  `sha256:6ec5ff207fdf24cb8baab733b9db096ece3d1fe1ba0ba5c6c644ac6c20ccd5ea`, 21,101 bytes,
  `d120cleanupcandidate_86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/
  `sha256:86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/
  `sha256:f4f985e6574ead218ffea4813d234c1b5c35cdf60e109de5bbe0849dd25127d8`, 10,464 bytes,
  `d120_8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/
  `sha256:8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/
  `sha256:cd4fe9024bfb1b44e9e762412e442f3c2958085629b15e19f7a9423aefa3581b`, 12,140 bytes다.
  D-120의 cleanup output-representation diagnosis는 source-consistent/self-attested이고 portable root-cause proof가
  아니다. Exact D-120 candidate 승인은 이후 D-121 preparation에 한 번 소비됐고 D-119
  mutation/retry/resume/repair나 successor execution 권한으로 확대되지 않았다.
- Historical D-119 state: `D-119 exact cutoff/isolation execution was claimed once and ended
  PARTIAL_CONSUMED_FAILED during cleanup evidence validation; the probe outcome remains UNSEALED_UNKNOWN`이다. Approval
  receipt는 `reports/memory-development/d119-cutoff-isolation-approval-receipt.json`, receipt/body ID
  `d119approval_671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce`/
  `sha256:671af8d6e7cbd44ef0793c1bf1bf53f3f5f8e3fcbfd26e04906cb4abdea50cce`, 5,299-byte file SHA
  `sha256:625cd6487fffe50b2429e011c67da222ec0da020dbf62d65a911fa83da3f550c`다. Preflight는
  `reports/memory-development/d119-cutoff-isolation-preflight.json`, preflight/body ID
  `d119preflight_85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1`/
  `sha256:85dcbc49bec53797904f080d0e6922b521a9f6f232902e122895090e5f886dd1`, 11,229-byte file SHA
  `sha256:57f59fc29054276947851abdfe3dbf0040fe10cef5624946e66dc84a698fb18a`다. Four-record journal
  `reports/memory-development/d119-isolation-execution.jsonl`은 head
  `sha256:4bd08521b13431251449d79cb2847a93fc947cf2ce6e6b319e71f728cc74bd46`, 2,075-byte file SHA
  `sha256:fadda3b86b2ad954a1d233b0dbf11d67b8a9a86f3db6704eab555eec5f2a4950`이며
  `ExecutionClaimed`, `ImageIdentityVerified`, 첫 `IsolationSessionStarted`, `ExecutionFailed`만 기록한다. Probe result,
  cleanup detail, completed session과 D-119 evidence/gate는 없고 automatic retry도 금지됐다. 따라서 이 실패를 source,
  task, container removal 또는 isolation failure로 재분류하지 않는다.
- Historical D-118 state: `D-118 exact D-117-bound external public-development source bytes sealed with
  BLOCKED_INSUFFICIENT_PREEXISTENCE; trusted cutoff, technical isolation, independence, execution readiness,
  matcher, retrieval, agent run and core remain closed`다. Exact D-117 candidate triple을 다시 제시한 사용자의 좁은
  승인에 따라, D-118은 SWE-bench `f5351ee8c6663736817027db3ad03fe662cb5bb8` dev와 SWE-Gym
  `26a6eae79ae9cb6d4307c3cc99c126fbf23cb3f0` train의 revision-pinned source-level metadata와 opaque 파일만
  결속했다. Approval receipt는
  `reports/memory-development/d118-external-source-evidence-approval-receipt.json`, receipt/body ID
  `d118approval_2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`/
  `sha256:2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`, 4,199-byte file SHA
  `sha256:0adb87887b42a19aa8d1b9be3ca5268801666bbecb2cf94b4664e3df1dba8344`다. Preflight는
  `reports/memory-development/d118-external-source-evidence-preflight.json`, preflight/body ID
  `d118preflight_1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`/
  `sha256:1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`, 17,476-byte file SHA
  `sha256:4f4bff33cbf55e841f86da0a30fc67885f9302fa2f149dde040a3d85a2c4c0b3`다. Evidence pack은
  `reports/memory-development/d118-external-source-evidence-pack.json`, pack/body ID
  `d118evidencepack_e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`/
  `sha256:e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`, 25,451-byte file SHA
  `sha256:318d4f58276283e6e6ae6c45c4afe50af5bca6b6937ffa841b8b791a0357c6b1`다. Source gate는
  `reports/memory-development/d118-external-source-evidence-source-gate.json`, gate/body ID
  `d118_cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`/
  `sha256:cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`, 17,748-byte file SHA
  `sha256:0f01a2b315f9c32c34b8c2400af6f22a1c4f2538b2538f8597f2ab0b8d57c343`다.
  두 source의 `.gitattributes`, `README.md`, opaque parquet를 합친 6개 bound file은 45,036,395 bytes다. Opaque
  payload는 SWE-bench dev 1,382,594 bytes/
  `sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b`와 SWE-Gym train
  43,644,473 bytes/`sha256:60569cea74bb281f7a5579467436a2bc1932c6e0c5f2f7fa0d084392abd9ad97`다.
  D-118은 파일을 hash했지만 record container를 parse하거나 issue/task record, prose, label, hint, patch, test,
  oracle field를 읽지 않았다. Provider의 revision·split/member count·tree binding·GPG badge 관찰은
  source-level web research에 대한 self-attested claim이며 bound input에서 signature/tree proof를 재구축한 portable
  evidence가 아니다. Git/provider date와 current download/hash도 trusted pre-D-116 timestamp로 승격하지 않았다.
  따라서 disposition은 `BLOCKED_INSUFFICIENT_PREEXISTENCE`이고 `trusted_cutoff_anchor_verified=false`,
  `technical_isolation_verified=false`, `independent=false`, `eligible_for_independent_calibration=false`,
  `execution_authorization_candidate_ready=false`다. Isolation session과 independent positive는 0이고 issue labeling,
  matcher/classifier/calibration, score/ranking mutation, retrieval/runtime injection, agent/provider/evaluator call과
  core/analysis campaign도 모두 0/false다. 기본 `sealed-historical` validation은 raw snapshot 없이 봉인된 pack을
  재검증하고, opt-in `current-object`는 ignored local object를 read-only rehash한다. 어느 mode도 preexistence나
  independence를 올리지 않는다. D-117+D-118 focused 검사는 48/48 통과했지만 repository-wide suite 통과로 확대하지
  않는다. 당시 다음 단계는 exact snapshot과 membership rule을 함께 묶는 trusted pre-D-116 external anchor와 실행된
  isolation evidence를 확보하는 것이었다. 이후 D-119가 한 번 시작됐지만 cleanup evidence validator 단계에서
  `PARTIAL_CONSUMED_FAILED`로 종료됐고 trusted cutoff나 independence는 성립하지 않았다.
- Historical D-117 state: `D-117 exact D-116-bound grammar-blind preexisting public-control acquisition protocol sealed;
  no pool was identified, read, acquired, frozen or reviewed while matcher, calibration, retrieval, runtime injection,
  agent run and core remain closed`다. 사용자가 exact D-116 candidate triple을 별도 메시지에서 다시 제시해 승인한
  범위대로, D-117은 public-development control만을 대상으로 하는 future acquisition protocol과 D-118 authorization
  candidate를 **계약과 계획으로만** 봉인했다. Held-out task issue/result, private/hidden/reference/patch/trace/evaluator
  evidence는 pool membership과 read에서 제외한다. Approval receipt는
  `reports/memory-development/d117-blind-control-acquisition-protocol-approval-receipt.json`, receipt/body ID
  `d117approval_f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
  `sha256:f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`, 10,096-byte file SHA
  `sha256:40ea64548634353a12b48f8bcabce941df47e16f9b27d892722d55fcda1e5e13`다. Preflight는
  `reports/memory-development/d117-blind-control-acquisition-protocol-preflight.json`, preflight/body ID
  `d117preflight_34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
  `sha256:34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`, 29,919-byte file SHA
  `sha256:6682f4f2870cdb34e6ee766333c95ac58a406a7d4e4086d6086752650869c305`다. Candidate는
  `reports/memory-development/d117-blind-control-acquisition-protocol-authorization-candidate.json`, candidate/body ID
  `d117blindprotocolcandidate_27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
  `sha256:27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`, 7,999-byte file SHA
  `sha256:d10bbe5b3b65050868a1202cd1af9f130c89bbe43ceccf9359af145cac96cda7`다. Source gate는
  `reports/memory-development/d117-blind-control-acquisition-protocol-source-gate.json`, gate/body ID
  `d117_750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
  `sha256:750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`, 16,813-byte file SHA
  `sha256:a439fc936b5b594c043b4ea90cd57bb676e79004cf4de8794b83f3af15fb13e3`다.
  Protocol은 provenance verifier, pool assembler, blinding broker, selector A/B, adjudicator, independence auditor와
  future matcher evaluator의 input visibility를 분리한다. 현재 process/agent와 D-116 grammar observer, 같은 checkout
  subagent 또는 prompt-only blinding은 blind role 자격이 없다. Selector A/B와 adjudicator에는 opaque public
  title·description·language와 exact D-105 rubric만 주고, 서로의 결과를 보기 전에 first-pass 결과를 봉인하도록 했다.
  Pre-D-116 source bytes·membership·trusted cutoff 또는 technical isolation을 증명하지 못한 record는 보존하되
  `post_hoc=true`, `independent=false`, independent calibration ineligible로 강등한다.
  실제 external source triple은 공급되지 않았다. Source pool identified/read/acquired/frozen은 false/0이고 pool
  manifest/member, role/isolation session, blind packet, selector/adjudication result, independent control/positive도 모두
  0이다. Matcher evaluator/classifier/calibration implementation과 execution, model/embedding load, retrieval/runtime
  injection, agent/provider/evaluator/network-capable call도 모두 0이며 added model cost는 `$0`다. D-116+D-117 focused
  검사는 46/46 통과했지만 repository-wide suite 통과로 확대하지 않는다. OS-level socket 차단은 실행·검증하지 않았다.
  당시 next gate는 exact D-117 candidate triple뿐 아니라 exact external pre-D-116 source snapshot, pre-D-116 membership
  manifest 또는 exhaustive rule, trusted cutoff anchor, isolation profile triple을 별도로 제시해 D-118의
  **one isolated public-development pool acquisition execution-authorization candidate 준비만** 승인하는 것이다. 이
  gate의 exact code는
  `exact-d117-candidate-triple-plus-external-source-membership-cutoff-and-isolation-triples-d118-execution-authorization-candidate-approval`이다.
  이 승인은 actual pool acquisition/review, unapproved issue read, matcher/classifier/calibration 구현·실행, score/ranking
  변경, retrieval/runtime injection, agent/provider/evaluator/network call 또는 core/analysis campaign을 허용하지 않는다.
  이 exact 승인은 이후 D-118의 source-level opaque evidence materialization에 한 번 결속됐으며 actual pool
  acquisition, record read, blind review 또는 matcher 실행 권한으로 확대되지 않았다.
- Historical D-116 state: `D-116 exact D-115-bound public-only applicability-signal grammar and prospective calibration
  contract sealed; calibration blocked on grammar-blind independent positives while score policy, retrieval, runtime
  injection, agent run and core remain closed`다. 사용자가 exact D-115 candidate triple을 별도 메시지에서 다시
  제시해 승인한 범위대로, D-116은 public `dev-train`/`dev-validation`의 `public.yaml`만 읽어 deterministic
  SELECT/ABSTAIN 입력·결과 schema, evidence-span 규칙과 frozen matcher grammar를 **계약과 계획으로만** 봉인했다.
  Approval receipt는 `reports/memory-development/d116-public-failure-class-signal-approval-receipt.json`, receipt/body
  ID `d116approval_016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
  `sha256:016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`, 12,014-byte file SHA
  `sha256:86c4e279df6c3d4b6ea02719375f76370d76fb795d642f2d10211e878662ba77`다. Preflight는
  `reports/memory-development/d116-public-failure-class-signal-preflight.json`, preflight/body ID
  `d116preflight_e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
  `sha256:e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`, 76,157-byte file SHA
  `sha256:fc2602a385242204ab9ae274ea6c73a83bd00a00eace88c7f310a57b5d4655f5`다. Candidate는
  `reports/memory-development/d116-public-failure-class-signal-calibration-candidate.json`, candidate/body ID
  `d116classsignalcandidate_0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
  `sha256:0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`, 8,017-byte file SHA
  `sha256:8299f3d400bd9412a8b7100305a0eb57f1d5b4ea78a39d8e5edad6cd5a2b15ca`다. Source gate는
  `reports/memory-development/d116-public-failure-class-signal-source-gate.json`, gate/body ID
  `d116_e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
  `sha256:e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`, 19,859-byte file SHA
  `sha256:f03bc7806d8401b9ac9f3d9e47df7b0ef19b16a04380bed1c9cb1d105e52320d`다.
  Public inventory는 10개이고 prospective eligible 8개, bootstrap exclusion 2개다. Pyfakefs와 HF Hub 두 source
  anchor는 contract authoring과 겹쳐 independent evidence로 세지 않으며, tox public prose는 세 번째 group의 필수
  S3 shared-error-boundary를 명시하지 않아 source-anchor SELECT가 아니라 ABSTAIN expectation이다. 현재 panel은
  non-blind이고 세 group 모두 blind independent positive가 없어 independent positive count는 0이다. 12개 synthetic
  conformance case는 실행되지 않은 사전 계획이며 calibration 또는 독립 evidence가 아니다. Matcher evaluator,
  classifier와 calibration은 구현·실행하지 않았고 task-level signal result도 0이다. Focused 검사는 21/21 통과했지만
  repository-wide suite 통과로 확대하지 않는다. Model/embedding load, retrieval, runtime injection,
  agent/provider/evaluator/network-capable call은 모두 0이고 added model cost는 `$0`다. OS socket 차단은 검증하지
  않았다.
  당시 next gate는 exact D-116 candidate ID/body/file SHA를 별도 사용자 메시지에서 다시 제시해 D-117의
  **grammar-blind preexisting byte-frozen public pool acquisition protocol candidate** 준비만 승인하는 것이다. Pool
  assembler와 selector/adjudicator는 matcher grammar·hash·output을 보지 못하도록 분리하고, selector/adjudicator에는
  D-105 applicability rubric만 제공해야 한다. 이 격리를 증명할 수 없으면 control은 `post-hoc` 및
  `independent=false`로 기록한다. 그 승인도 grammar 변경, matcher/classifier/calibration 실행, score policy 수정,
  retrieval, runtime injection, agent/provider/evaluator call 또는 core/analysis campaign을 허용하지 않는다.
  `three_class_calibrated=false`, `independent_generalization_validated=false`, `true_relevance_established=false`,
  `corrected_policy_selected=false`, `retrieval_ready=false`, core/analysis false/closed였다. 이 exact 승인은 이후
  D-117에서 protocol-only candidate 준비에 한 번 결속됐으며 actual pool acquisition 또는 review 권한으로 확대되지 않았다.
- Historical D-115 state: `D-115 exact D-114-bound public-only score-policy decision candidate sealed; threshold/weight-only
  correction rejected while policy mutation, retrieval, runtime injection, agent run and core remain closed`다.
  D-115는 exact D-114 successor evidence와 D-112의 public score row 9개만 사용해 현행 scorer를 offline으로
  감사했다. Preflight는 `reports/memory-development/d115-score-policy-decision-preflight.json`, preflight/body ID
  `d115preflight_c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
  `sha256:c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`, 59,725-byte file SHA
  `sha256:91908b43eb581b09249f8285e5f1d09389092c5b40c1c794b9ab139667c86bad`다. Candidate는
  `reports/memory-development/d115-score-policy-decision-candidate.json`, candidate/body ID
  `d115scoredecisioncandidate_91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
  `sha256:91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`, 6,839-byte file SHA
  `sha256:1fd424eab88c60a9d8480e756642b2c70b03afd03dd777e27bf36a3ea428df7a`다. Source gate는
  `reports/memory-development/d115-score-policy-decision-source-gate.json`, gate/body ID
  `d115_ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
  `sha256:ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`, 13,730-byte file SHA
  `sha256:67f62c23e9f5e14fe9cd1d075b2c6f679764c18644837914b0031348c4a21b72`다.
  Threshold만 낮춰 Moto의 어떤 memory라도 선택하면 최고 Moto score `0.3541890713468577`보다 threshold가 낮거나
  같아야 하지만 Babel no-match를 보존하려면 최고 Babel score `0.39188659397843584`보다 높아야 하므로 가능한
  분리 구간이 없다. 또한 failure-class와 validation component가 모두 0이고 probe 내부 phase/language가 같아,
  현재 관측 feature에 대한 nonnegative weight 변경만으로는 Moto 가설 group을 1위로 만들 수 없다. 따라서
  `decision_status=policy-mutation-deferred`, `corrected_policy_selected=false`다. Weight
  `0.25/0.40/0.15/0.10/0.10`, threshold `0.60` tuple은 독립적인 deterministic public taxonomy classifier가
  explicit abstention을 제공한다고 가정한 **counterfactual-only, non-runtime, non-authoritative** 진단이며 선택된
  policy나 implementation-ready 결과가 아니다. Private/hidden/reference/known-bad, raw trace/patch와 held-out result는
  읽지 않았고 model load/encode, retrieval/injection, agent/provider/evaluator/network-capable call은 모두 0이며
  protected input fingerprint는 전후 같다. OS socket 차단은 검증하지 않았다.
  당시 next gate는 exact D-115 candidate ID/body/file SHA를 별도 사용자 메시지에서 다시 제시해 D-116의
  public-only abstaining failure-class signal contract/calibration candidate 준비만 승인하는 것이었다. 이 exact
  승인은 이후 D-116에서 한 번 결속됐다. D-115 종료 시
  `exact_candidate_user_approval_received=false`, `public_failure_class_signal_contract_authorized=false`,
  `score_policy_correction_authorized=false`, `retrieval_ready=false`, runtime injection/agent run 0,
  core/analysis false/closed다.
- Historical D-114 state: `D-114 exact D-113-bound append-only successor validator correction completed; strict
  sealed-historical replay passed while the original D-112 evidence and score policy remained unchanged`다. 사용자가
  exact D-113 candidate triple과 좁은 실행 범위를 별도 메시지에서 다시 제시해 새 module/script/test와 append-only
  receipt/gate 생성 1회만 승인했다. Receipt는
  `reports/memory-development/d114-d112-validator-correction-receipt.json`, receipt/body ID
  `d114approval_20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
  `sha256:20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`, 10,493-byte file SHA
  `sha256:1f494579e70d9e8a7f0d28439578afc3b3aa77c7735ac8bc4e81627cab70793b`다. Completion gate는
  `reports/memory-development/d114-d112-validator-correction-gate.json`, gate/body ID
  `d114_8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
  `sha256:8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`, 15,686-byte file SHA
  `sha256:c336004f12f187ab0bfb7946204f877c088703d25e809a8e79e9ec84d374be11`다. Successor는 D-112
  receipt/gate의 exact root/body/claim key set과 full expected payload, paired binding과
  `approval <= execution <= completion` chronology를 강제하고 fully rehashed unknown/unchecked field와 paired
  receipt/gate rehash를 거부한다. `sealed-historical`과 opt-in `current-input` mode를 분리했으며 evidence 생성에는
  sealed mode만 실행했다. Sealed mode는 local snapshot과 installed embedding dependency를 요구하지 않고 checked-in
  frozen index, gate vector와 exact public spec으로 score row 9개를 재계산했다. Query embedding semantic fidelity를
  다시 측정하거나 model을 encode하지 않았고 current-input mode도 correction evidence에서는 실행하지 않았다.
  D-112 실행-bound 파일과 receipt/gate/index/marker는 수정·재실행되지 않았으며 protected/implementation fingerprint가
  각각 전후 같다. Model load/encode, retrieval/injection, agent/provider/evaluator call은 모두 0이고 added model cost는
  `$0`다. Approval은 self-attested이고 one-use는 repository-local cooperative claim일 뿐 global/cross-clone exclusion,
  authenticated identity 또는 cryptographic signature가 아니다. OS socket 차단도 검증하지 않았으며 negative tamper
  probe는 materialization 자체가 아니라 별도 test에서 검증했다. D-114는 original D-112 guarantee나 score/ranking을
  소급 변경하지 않았고 score policy, retrieval, runtime injection, agent와 core authority는 계속 닫아 두었다.
- Historical D-113 state: `D-113 exact D-112 evidence and five validator gaps sealed in an offline append-only
  correction authorization candidate; correction implementation, score policy, retrieval, runtime injection and core
  remain closed`다. 일반적인 `진행해줘`는 D-114 correction 권한으로 확대하지 않고 D-113 candidate 생성까지만
  사용했다. Preflight는 `reports/memory-development/d113-d112-validator-correction-preflight.json`, preflight/body ID
  `d113preflight_13b1f266a3f84121bf160dedbc459581a6243247261d991a3bb81aefd6dd2375`/
  `sha256:13b1f266a3f84121bf160dedbc459581a6243247261d991a3bb81aefd6dd2375`, 8,270-byte file SHA
  `sha256:f2053137c80a9429251651201f61df942d9e448d0ddf2dab0faf2366bcfbf505`다. Exact authorization
  candidate는 `reports/memory-development/d113-validator-correction-authorization-candidate.json`, candidate/body
  SHA `d113validatorcandidate_373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732`/
  `sha256:373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732`, 5,963-byte file SHA
  `sha256:4b576b6b7edbb7ebf9813e8c4ac35fae7af88992dc4dac3a28a181f79aa6e8a9`다. Source gate는
  `reports/memory-development/d113-validator-correction-source-gate.json`, gate/body ID
  `d113_0cbf14cc933ba33374f7a5b5db2800e62d6e6d1456f2b6eb48facfa35ace568c`/
  `sha256:0cbf14cc933ba33374f7a5b5db2800e62d6e6d1456f2b6eb48facfa35ace568c`, 3,133-byte file SHA
  `sha256:a69677ddfe7875322e4a27d9f7c3b6086e4fa7350ac9f3f68381fe460dc28d54`다. D-113은 exact
  D-112 receipt/gate와 실행-bound module/script/test, portable frozen index/marker와 D-106 unfrozen index를
  source hash에 결속했고 build 전후 보호된 fingerprint가 같다. Stable finding은
  `skip-current-not-portable`, `receipt-validator-not-exact`, `timestamp-chronology-not-enforced`,
  `one-use-repository-local-only`, `network-zero-not-socket-instrumented` 다섯 개다. 실제 checked-in D-112
  chronology는 정상이며 이 finding은 D-112 score나 execution result를 뒤집지 않는다. D-113 builder는 D-112
  validator/replay, snapshot/model file, embedding load/encode, retrieval/injection, agent/provider/evaluator/network를
  호출하지 않았고 added model cost는 `$0`다. Focused 18/18이 통과했다. D-111~D-113 연속 회귀는 기존 D-112의
  반복 snapshot 검증 때문에 5분 제한에서 7개 진행 후 timeout됐으므로 통과로 보고하지 않는다. Future D-114는
  별도 새 module/script/test와 append-only receipt/gate만 만들도록 candidate가 제한한다. D-112 실행-bound 파일과
  receipt/gate/index/marker mutation, score/threshold/rank 변경, retrieval/runtime injection/agent/core는 허용하지 않는다.
  `validator_correction_authorized=false`, `validator_correction_implemented=false`,
  `score_policy_correction_authorized=false`, retrieval/core/analysis는 false/closed다. 다음 gate는 exact D-113
  candidate ID/body/file SHA의 별도 사용자 승인이다.
- Historical D-112 state: `D-112 exact D-111-bound one-use local scoring diagnostic completed; observed selective
  no-match and mismatched positive ranking sealed while score correction, retrieval, runtime injection and core remain
  closed`다. 사용자가 exact D-111 candidate ID/body/file SHA를 별도 메시지에서 다시 제시해 D-112 local
  read-only scoring diagnostic의 구현과 1회 실행만 승인했다. 이 self-attested 승인과 one-use claim은
  `reports/memory-development/d112-retrieval-readiness-probe-receipt.json`에 기록했다. Receipt ID/body SHA는
  `d112probereceipt_ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257`/
  `sha256:ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257`, 13,835-byte file SHA는
  `sha256:74fcd761cac65a9cab26529076b7cde60eaa14a1faf40475e680f526e00ba1d1`이며 execution claim은
  `2026-08-06T17:16:20.878831Z`다. Receipt의 exclusive create/fsync가 one-use 소비 지점이며 hard kill이나
  실패 뒤에도 자동 retry/rollback하지 않는다. 별도 journal이나 frozen index authority mutation은 만들지 않았다.
  Completion gate는 `reports/memory-development/d112-retrieval-readiness-completion-gate.json`, gate/body ID
  `d112_3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6`/
  `sha256:3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6`, 77,591-byte file SHA
  `sha256:a7e691ae43c60405cbb10cd27caf3055eabaa96bb7fa6f2a02142d97aa903951`, `recorded_at`은
  `2026-08-06T17:18:33.876453Z`다. Exact input fingerprint는
  `sha256:d54454b2693e231c0ef50c94b20d75d58f00a885dfae98d3b6b190665f9d2e17`이고 pre/post가 같다.
  Pinned `sentence-transformers/all-MiniLM-L6-v2` revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`을 CPU/local-files-only/library-offline로 정확히 한 번 load하고,
  Moto/IMPLEMENT, Babel/IMPLEMENT, Moto/REPRODUCE를 순서대로 한 batch에서 정확히 한 번 encode했다. Shape/dtype은
  `(3, 384)`/float32이고 finite normalized다. Full query vector와 float32 SHA를 gate에 저장해 validator는 모델을
  다시 실행하지 않고 frozen entry vector에서 9개 score row를 재계산한다. Moto 두 row의 vector SHA는
  `sha256:e0b7d19299cdc988cfa46ac3fb2ba3fe79673558a7a6d3968794224424c48331`로 같고 phase score delta는 entry마다
  `0.15`다. Babel vector SHA는
  `sha256:72914c111db65c339521e62e4b45d1fc6e236e809dc91af3e1025021050e1715`다.
  세 probe 최고 점수는 각각 `0.3541890713468577`, `0.39188659397843584`, `0.20418907134685768`로 모두
  threshold `0.72` 미만이다. 세 top group은 모두 `exception-origin-state-conflation`이며 Moto positive 가설의
  `platform-emulation-matrix-gap`과 일치하지 않았다. 이는 diagnostic 관찰이지 execution failure, memory benefit,
  negative transfer 또는 agent defect 판정이 아니다. Focused 11/11과 D-111/공용 memory 관련 회귀 13/13이
  통과했다. Repository-wide full suite와 D-106~D-110 전체 회귀는 이번 checkpoint에서 실행하지 않았다.
  Local embedding load/encode는 1/1이지만 provider/evaluator/agent/retrieval call은 0/0/0/0, runtime injection과
  returned memory text는 0, added model cost는 `$0`다. OS-level socket 차단은 검증하지 않았으므로
  library-offline/local-files-only evidence로만 주장한다. `retrieval_ready=false`,
  `retrieval_experiment_authorized=false`, `score_policy_correction_authorized=false`, raw/four-condition/core/analysis는
  false/closed다. Post-execution audit에서 두 validator gap을 확인했다. 첫째,
  `--skip-current-input-verification`도 `_input_state()`를 먼저 호출해 local 91MB snapshot과 exact dependency를
  요구하므로 clean-clone portable mode가 아니다. 둘째, receipt validator는 exact expected payload 전체를 rebuild해
  비교하지 않아 fully rehashed unknown field와 일부 unchecked claim field를 fail closed하지 못한다. Actual artifact의
  timestamp 순서는 정상이나 chronology도 validator가 강제하지 않는다. One-use는 receipt path의 repository-local
  cooperative claim이며 global ledger, authenticated signature 또는 pre-claim clone 병렬 실행 배제가 아니다. Default
  loader의 network call 0도 source-path/self-attested evidence이지 socket instrumentation 증명이 아니다. 실행에 결속된
  module/script/test와 gate를 조용히 고치거나 다시 쓰지 않는다. Gate가 기록한 next gate는 offline score-policy
  decision candidate지만, 실제 다음 우선순위는 별도 append-only validator-correction candidate다. 어느 문구도 policy
  수정, retrieval, runtime injection, agent run 또는 core 실행 권한이 아니다.
- Historical D-111 state: `D-111 frozen-index retrieval-readiness gaps audited and exact one-use local scoring diagnostic
  authorization candidate sealed; approval, retrieval, embedding, runtime injection and core remain closed`다.
  D-110 portable completion gate와 frozen index/marker, 변경되지 않은 D-106 unfrozen index를 exact bytes로 다시
  검증하고, 현재 D-110에 결속된 legacy `patchloop/memory/retrieval.py`는 수정하지 않았다.
  Preflight는 `reports/memory-development/d111-frozen-index-retrieval-readiness-preflight.json`, ID/body SHA
  `d111preflight_ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`/
  `sha256:ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`, 13,085-byte file SHA
  `sha256:fed699e068c52e2dd929b654a65369aee3499d6d69c5a38c14dcee808ff57387`다.
  Exact authorization candidate는
  `reports/memory-development/d111-retrieval-readiness-authorization-candidate.json`, candidate/body SHA
  `d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`/
  `sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`, 6,465-byte file SHA
  `sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6`다. Source gate는
  `reports/memory-development/d111-retrieval-readiness-authorization-source-gate.json`, gate/body SHA
  `d111_348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/
  `sha256:348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`, 3,308-byte file SHA
  `sha256:d550cb048e417965e482c64682df4a1b91b90067f66b36e370912f5a8d759c16`다.
  Leak-safe probe plan은 public dev-validation의 Moto/IMPLEMENT, Babel/IMPLEMENT, Moto/REPRODUCE 세 입력만
  결속한다. Private, hidden, reference와 known-bad patch는 읽지 않았다. 현재 scorer에서는 자연어 query의
  failure-class score와 세 entry의 validation score가 모두 0이므로, IMPLEMENT/Python에서 semantic score가
  완벽해도 최대 `0.65 < 0.72`다. 또한 legacy structured renderer는 세 entry 모두 exact D-105
  `model_facing_text` bytes와 다르고 query encoder는 D-106 locked snapshot의 local-only load를 강제하지 않는다.
  따라서 `legacy_runtime_retrieval_ready=false`, `selective_scoring_non_degenerate=false`, `raw_trace_ready=false`,
  `four_condition_retrieval_ready=false`다. D-111 focused 8/8과 관련 retrieval/memory 회귀 7/7이 통과했다.
  D-111 자체 retrieval/query embedding/provider/evaluator call은 0/0/0/0, runtime memory injection 0, 추가 model
  cost `$0`다. 당시 next gate였던 exact candidate triple 승인은 D-112에서 별도 메시지로 받아 한 번 소비됐다.
- Historical D-110 state: `D-110 exact D-109-bound one-use index freeze completed; frozen evidence sealed while retrieval,
  runtime memory injection and core remain closed`다. 사용자가 같은 메시지에서 exact D-109 candidate ID/body/file
  SHA를 다시 제시해 freeze 1회만 승인했고, 이 승인은
  `reports/memory-development/d110-exact-index-freeze-approval-receipt.json`에 기록했다. Approval receipt ID/body
  SHA는 `d110approval_cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`/
  `sha256:cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`, 3,495-byte file SHA는
  `sha256:f409c6296b1f87d8cb151fcc1866d263f3e74aa9341c46ab49ea3b4fef66a97c`이며 `recorded_at`은
  `2026-08-06T12:42:48Z`다. 이는 self-attested approval일 뿐 reviewer identity 인증이나 cryptographic
  signature 증명이 아니다.
  One-use execution은 `2026-08-06T13:54:43.725943Z`에 시작해 exact pre-state를 다시 확인한 뒤
  `/frozen`, `/frozen_at`, `/authority/index_freeze_authorized`, `/authority/memory_index_frozen`,
  `/content_hash` 다섯 pointer만 바꿨다. Post-freeze runtime index는 55,687 bytes/file SHA
  `sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0`, content hash
  `sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56`이고 `frozen=true`,
  `frozen_at=2026-08-06T13:54:43.725943Z`다. 72-byte `FROZEN` marker file SHA는
  `sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561`이며 runtime directory에는
  `FROZEN`과 `index.json`만 있다. Portable D-110 frozen index/marker는 runtime bytes와 같고, D-106 portable
  unfrozen index는 55,644 bytes/file SHA
  `sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`로 unchanged다.
  Append-only journal은 `reports/memory-development/d110-index-freeze-execution.jsonl`, 8 records, head
  `sha256:03d8bcbf57230aa9bfd5ce4e81fa2890bb36c2f5f9e4e51c9e64b3a8c09313e1`, 9,481-byte file SHA
  `sha256:f06cfa9037f09720675d3c0edd7e19516144bd46375aaa86679c5b1f6923b1e2`다. Freeze receipt는
  `reports/memory-development/d110-index-freeze-receipt.json`, ID/body SHA
  `d110freezereceipt_b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`/
  `sha256:b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`, 5,986-byte file SHA
  `sha256:a2aeaa0985cb1bf9ced5bdfd43c5bc473a73e5ac93bf7660ca717e3eb9285702`, `recorded_at`은
  `2026-08-06T13:54:43.782123Z`다. Completion gate는
  `reports/memory-development/d110-index-freeze-completion-gate.json`, gate/body ID
  `d110_bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`/
  `sha256:bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`, 7,754-byte file SHA
  `sha256:79578db09955dab2a22b015ba5210baec28e7d30b9cac818b1f2c6d6eac782cd`, `recorded_at`은
  `2026-08-06T13:54:43.793637Z`다.
  Commit 의미는 index staged-file fsync와 same-filesystem `os.replace` 뒤 marker를 exclusive binary create/fsync한
  **ordered per-file commit**이다. D-110 cooperative executor lock만 같은 executor끼리 조정하며, 두 파일의 global
  atomic transaction이나 임의 external writer 배제를 주장하지 않는다. Partial/ambiguous state는 fail closed하고
  automatic retry와 rollback은 하지 않는다. One-use journal capability는 소비됐다. Pre-mutation focused 17/17과
  post-freeze focused 17/17(256.5초)이 각각 통과했으며 D-110 related/full-suite 집계는 아직 없다.
  Provider/evaluator call과 added model cost는 0/0/`$0`다. `retrieval_ready=false`,
  `retrieval_experiment_authorized=false`, runtime memory
  injection count 0, core/analysis false/closed다. 다음 gate는 별도 **retrieval-readiness authorization candidate**를
  준비하는 것뿐이며 retrieval 실행, runtime injection 또는 core campaign 승인이 아니다.
- Historical D-109 state: `D-109 exact runtime pre-freeze state observed and content-addressed freeze authorization
  candidate sealed; explicit candidate approval, actual freeze, retrieval and core remain closed`다. D-108 completion
  gate와 D-107 portable validation을 exact ID/body/file SHA로 다시 확인하고, runtime
  `.patchloop/memory/indexes/idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064/index.json`이
  55,644-byte portable D-106 index와 byte-for-byte 같으며 file SHA
  `sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`, content hash
  `sha256:86dbd991fa411bc43a8ec65927630fe8ad3365a1a41d9a6eafdeb036d9aab3fd`임을 read-only로 확인했다.
  Runtime directory에는 `index.json` 하나만 있고 `FROZEN` marker는 없다. Preflight는
  `reports/memory-development/d109-runtime-index-freeze-preflight.json`, ID/body SHA
  `d109preflight_a7519ddeae6000c3e0fc8f368b6316ddf1d405ab77badbc8eeade12bbfbc4b34`/
  `sha256:a7519ddeae6000c3e0fc8f368b6316ddf1d405ab77badbc8eeade12bbfbc4b34`, 2,895-byte file SHA
  `sha256:569a4b071c9c36d436eb2972346d618ece3c748bd92fcfa9c06b12c482625999`다. Exact freeze candidate는
  `reports/memory-development/d109-index-freeze-authorization-candidate.json`, candidate/body SHA
  `d109freezecandidate_480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`/
  `sha256:480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`, 5,910-byte file SHA
  `sha256:ae8a8c6e58b058720943bae9088da2cf242168a70f654006557dd84c84d4e580`다. Candidate는 exact
  pre-state와 one-use freeze mutation whitelist만 정의하며 approval receipt가 필요하다. Source gate는
  `reports/memory-development/d109-index-freeze-authorization-source-gate.json`, gate/body ID
  `d109_e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef`/
  `sha256:e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef`, 3,485-byte file SHA
  `sha256:0953687473bd25f48ad52bdc78c577d6a4daa4947b019fcd65809e7548c4f949`다. D-109 focused 8/8과
  D-105~D-109/memory 관련 회귀 95/95가 통과했다. Repository-wide full suite는 1,937 passed, 7 skipped,
  failure 0이며 1,920.65초에 완료됐다. `exact_candidate_user_approval_received=false`, freeze
  execution/authorization, actual frozen state,
  retrieval/runtime injection, core와 analysis는 모두 false/closed이고 provider/evaluator call과 added model cost는
  0/0/`$0`다. 당시 다음 gate는 exact D-109 candidate ID/body/file SHA에 대한 사용자의 별도 승인이었다.
- Historical D-108 state: `D-108 exact two provider input-token counts completed and 2,000-token delta policy validated;
  explicit freeze authorization, retrieval and core remain closed`다. D-107 source gate를 즉시 선행 참조한 사용자의
  좁은 승인은 `reports/memory-development/d108-provider-token-count-approval-receipt.json`에 기록했다. Receipt
  ID/body SHA는 `d108approval_dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`/
  `sha256:dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`, 2,768-byte file SHA는
  `sha256:20442ff99a50fe6b79b7f155559816e98b3cf79523fb55e17627480de95f7b31`다. 이는 self-attested
  approval이며 reviewer identity 인증이나 cryptographic signature를 증명하지 않는다.
  승인 범위대로 `POST /v1/responses/input_tokens`를 baseline, with-memory 순서로 정확히 두 번 호출했다.
  Baseline은 2,193 input token, with-memory는 2,895 input token이었고 exact whole-entry memory bundle의 증분은
  702 token으로 사전 고정한 최대 2,000 token 이하라 `provider_exact_budget_validated=true`다. Provider
  input-token count/generation call은 2/0, SDK transport retry와 automatic retry는 0/false이며 evaluator call도
  0회다. Billing 또는 free-tier 적용 여부는 주장하지 않는다. Append-only execution journal은
  `reports/memory-development/d108-provider-token-count-execution.jsonl`, 6 records, head
  `sha256:84905f7a334ec349a2c979e6cfb68c9c67a23dda9219f1fc8036f9d2e78f5eaf`, 6,124-byte file SHA
  `sha256:01f96bc62f4a1f1d692328e2e7e71e8456a2976b772a70cf0bd66ab1b07227cd`다. Provider receipt는
  `reports/memory-development/d108-provider-token-count-receipt.json`, ID/body SHA
  `d107countreceipt_80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`/
  `sha256:80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`, 1,800-byte file SHA
  `sha256:43ce5dc5260a9f67e05f695a68a7dbf840ef3743f7ba7858583e9e74fb07d474`다. Completion gate는
  `reports/memory-development/d108-provider-token-count-completion-gate.json`, gate/body ID
  `d108_c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`/
  `sha256:c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`, 4,794-byte file SHA
  `sha256:5f57e29caa3a3c940c280a69fbed3abe3d8daba4b4542e039355443df931d7bc`다. Exact token budget가
  통과해 `index_freeze_authorization_candidate_ready=true`지만 실제 freeze authorization, `FROZEN` marker,
  retrieval/runtime injection, core와 analysis는 계속 false/closed다. D-108 focused 검사는 offline 8개와
  checked-in artifact 2개를 합해 10/10 통과했고, D-105~D-108/memory 관련 회귀는 87/87 통과했다.
  Repository-wide full suite는 1,929 passed, 7 skipped, failure 0이며 1,235.51초에 완료됐다. Ruff,
  compileall과 `git diff --check`도 통과했다. 다음 gate는 exact D-108 completion gate에 대한 별도의 명시적
  index-freeze 승인이다.
- Historical D-107 state: `D-107 D-106 portable index offline rebuild verified and exact two-request provider
  token-count execution plan sealed without calls`다. Exact D-106 gate와 portable index를 외부 고정 ID·파일
  크기·SHA로 다시 확인하고 저장된 vector로 index 전체를 offline 재구성했다. 재구성한 canonical bytes는
  55,644-byte portable index와 정확히 같았으며 runtime `.patchloop` index, embedding model과 provider는 사용하지
  않았다. Portable 검증 결과는 `reports/memory-development/d107-portable-index-validation.json`, ID/body SHA
  `d107portable_8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`/
  `sha256:8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`, 3,146-byte file SHA
  `sha256:a6e71de1eea4a311d790e14a25dc9e507e1a2107176a7d0967ac074f9e50f259`다. 실제 runtime tuple로 만든
  baseline/with-memory request는 `/selected_memory`만 JSON `null`과 exact D-105 3,528-byte bundle로 다르다.
  계획은 `reports/memory-development/d107-provider-token-count-plan.json`, ID/body SHA
  `d107plan_7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`/
  `sha256:7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`, 10,143-byte file SHA
  `sha256:2a3d817d14d500863d56d5446010866a6feb2361eb684c3575400020bc31a085`다. Source gate는
  `reports/memory-development/d107-portable-index-token-count-source-gate.json`, gate/body ID
  `d107_4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`/
  `sha256:4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`, 4,175-byte file SHA
  `sha256:b3e24975062e379ec94c77187570b392026bacdcc855adedb00943467aaf09f2`다. D-107 자체 provider/evaluator
  call과 added model cost는 0/0/`$0`였고 당시 actual count와 delta, freeze candidate/authorization, retrieval과
  core는 닫혀 있었다. D-107 focused는 13/13, D-099~D-107/memory/qualification 관련 검사는 363/363이
  통과했다. Repository-wide full-order는 1,926 collected 중 1,918 passed/7 environment-dependent skipped/기존
  order-dependent D-093 WAL/SHM invariant 1 failed였고, 그 exact test는 fresh isolated process에서 1/1
  통과했다. 이를 D-107 failure나 fix 또는 전체 통과로 합산하지 않는다.
- Historical D-106 state: `D-106 pinned embedding snapshot verified and exact three-group deterministic unfrozen index
  built; freeze, retrieval, provider token validation, core and analysis remain closed`다. 사용자는 exact D-105 gate
  ID/body/file SHA를 즉시 선행 참조하는 방식으로 pinned snapshot download/preflight, group-aware builder 구현과
  승인 group 3개의 actual unfrozen index 1개 생성을 명시적으로 승인했다. Self-attested receipt는
  `reports/memory-development/d106-exact-index-build-approval-receipt.json`, ID/body SHA
  `d106receipt_28da7f1882e9cae0811959a70bea3db26ed2067fbe956114efaa8abf8762027a`/
  `sha256:28da7f1882e9cae0811959a70bea3db26ed2067fbe956114efaa8abf8762027a`, 2,321-byte file SHA
  `sha256:e71ece9cbdb8662389233e3f6acdc6bc051e0a15a29cef8d604c14ad2c7fa97b`다. 이는 reviewer identity나
  cryptographic signature를 증명하지 않는다. Exact revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`에서 safetensors runtime file 10개만 내려받았고 90,868,376-byte
  `model.safetensors`는 upstream LFS SHA-256
  `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`와 일치했다. Snapshot manifest SHA는
  `sha256:e497d8dad53f09ddc8b9fcc9b81e3ff778e002e120ab4254c72993d8611959cb`다. CPU/local-files-only와 library
  offline mode로 fresh model load 2회와 encode 2회를 수행했고 세 D-105 whole-entry render는 218/220/207
  WordPiece token으로 model max 256 안에 들어 truncation 없이 `(3, 384)` float32 finite normalized vector를
  만들었다. 두 fresh load의 vector bytes는 current host에서 일치했다. Portable preflight는
  `reports/memory-development/d106-locked-embedding-snapshot-preflight.json`, ID/body SHA
  `d106preflight_11779604716a48bc714f4d759c01c035a5c4c7cfe7d0c3bdd2f2191a1f4e3b2a`/
  `sha256:11779604716a48bc714f4d759c01c035a5c4c7cfe7d0c3bdd2f2191a1f4e3b2a`, 9,351-byte file SHA
  `sha256:4a1b8e56dd986d8e793dca554b778e837cf182723cbb46ea8fb17863955d4ca4`다. OS-level socket 차단은
  검증하지 않았으므로 library offline/local-only evidence로만 주장한다.
  새 builder는 legacy failure별 builder나 `entry_embedding_text()`를 호출하지 않고 exact D-104 source 3개와
  exact D-105 render bytes를 같은 순서로 소비한다. Pyfakefs/HF Hub/tox 의미 group마다 `MemoryEntry`와 vector
  하나씩 만들고 AnyIO/Loguru hold group은 제외한다. Content-derived index ID는
  `idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064`다. Portable index는
  `reports/memory-development/artifacts/d106/` 아래 55,644-byte file SHA
  `sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`이고 runtime exact copy는
  `.patchloop/memory/indexes/<index-id>/index.json`이다. `FROZEN` marker는 없고 explicit-path retrieval과 legacy
  freeze도 later gate 없이는 fail closed한다. Completion gate는
  `reports/memory-development/d106-locked-group-index-gate.json`, gate/body ID
  `d106_fc2eeb0800e72d4aa0f7331110baf46caaa848879306454a4e0e6476e8fbe9a8`/
  `sha256:fc2eeb0800e72d4aa0f7331110baf46caaa848879306454a4e0e6476e8fbe9a8`, 8,709-byte file SHA
  `sha256:3ac34d27b4eab1facbeb86adb1e37de8927fa312f9e2b68a03e8f39c19008ea7`다. D-106 focused와 memory
  regression은 17/17, D-104~D-106/memory/CLI related는 97/97 pass다. Repository-wide는 1,913 collected 중
  1,906 passed/7 environment-dependent skipped/failure 0이다. Ruff, compileall, exact gate rebuild와
  `git diff --check`도 pass다. Provider/evaluator call과 added model cost는 0/0/`$0`다. Actual
  MemoryEntry/embedding/index count는 3/3/1이지만 `frozen=false`, provider exact token delta, retrieval/runtime
  injection, core, analysis, memory effect와 negative transfer는 false다. 다음 gate는 provider exact token-delta,
  portable index validation과 별도의 explicit freeze authorization이며 그 전에는 freeze/retrieval/core를 실행하지 않는다.
- Historical D-105 state: `D-105 deterministic three-rule model-facing render and prospective embedding/index-build
  authorization source gate complete; provider token validation, embedding snapshot verification, actual index,
  retrieval and core remain closed`다. D-104의 exact unindexed source 세 개를 source order 그대로 읽어 model에
  보여 줄 ASCII/LF text 세 개를 만들었다. 입력은 이미 NFKC여야 하며 renderer가 임의로 normalize하지 않는다.
  Field 순서와 label, list 형식, trailing LF, entry separator를 고정하고 whole-entry만 허용하며 provenance와
  local path는 model-facing text에서 제외한다. Render file은
  `reports/memory-development/rendered/d105/` 아래 1,191/1,164/1,161 bytes 세 개다. Ordered render-set hash는
  `sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667`, 세 entry를
  `\n\n---\n\n`로 결합한 canonical bundle은 3,528 bytes/file SHA
  `sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf`다. 2,000-token
  policy는 문자 수를 4로 나눈 추정치가 아니라 canonical context의 `/selected_memory`만 JSON `null`에서 exact
  whole-entry bundle로 바뀌는 동일 full request의 `responses.input_tokens.count` 차이로 검증하도록 고정했다.
  Context deep diff와 context-slot normalization 뒤 request equality도 필요하다. D-105에서는 provider call을 하지 않았으므로 exact
  delta receipt는 없고 `provider_exact_budget_validated=false`다. Embedding authorization candidate는
  `sentence-transformers/all-MiniLM-L6-v2` revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, normalized embedding, `trust_remote_code=false`로
  고정했지만 model snapshot을 download/import하지 않았고 snapshot file hash, 384-dimension float32 vector를
  검증하지 않았다. Group-aware index-build plan과 authorization candidate만 true이며 user approval receipt,
  actual build authorization, runtime `MemoryEntry`, embedding과 D-105-created index count는 0/false다. Index
  build/freeze, retrieval, runtime injection, core, analysis, memory effect와 negative-transfer claim도 false다.
  Exact predecessor rebuild 중 inherited D-099 validator가 public submitted patch bytes를 integrity/leak scan용으로
  읽지만 이를 render에 복사하거나 새 rule 의미 작성에 사용하지 않는다. `patchloop.memory` package 초기화는 legacy
  retrieval/store module을 간접 import하지만 D-105 path는 그 API를 호출하거나 historical index를 inspect/modify하지
  않는다.
  Portable gate는
  `reports/memory-development/d105-renderer-embedding-index-authorization-gate.json`, gate/body ID
  `d105_0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`/
  `sha256:0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`, 12,368-byte file SHA
  `sha256:db6303f3de834b3c36493f2863dcc5be3ca697490d18df15c86a18e7ee7b17eb`다. 현재 확정된
  executable evidence는 focused 47/47, related 550/550다. Repository-wide는 1,900 collected 중 1,892
  passed/7 environment-dependent skipped/1 failed다. 유일한 failure는 기존 order-dependent
  `tests/test_d092_policy_replay_raw.py::test_d092_raw_public_replay_exactly_rebuilds_portable_manifest`의 SQLite
  WAL/SHM before/after invariant이며 exact test는 fresh isolated process에서 1/1 통과했다. 이를 D-105 failure나
  fix로 합산하지 않는다. D-105 provider/evaluator call과 added model cost는 0/0/`$0`다. 다음
  gate는 exact D-105 gate에 대한 명시적 승인, locked embedding snapshot preflight와 group-aware builder이며,
  그 전에는 index를 만들거나 core를 실행하지 않는다.
- Historical D-104 state: `D-104 exact three-rule unindexed source materialization complete; source schema/provenance/leak
  validation passed while render/index/retrieval/core remain closed`다. D-103 seal의 admitted entry 3개만 의미
  원천으로 사용해 `unindexed-memory-entry-source-d104-v1` 원본 3개를 만들었다. Trace나 patch를 다시
  요약하지 않았고 D-100 template과 group fingerprint, decision hash, ordered source run/failure/evidence ID,
  template hash를 그대로 보존한다. Source collection ID는
  `d104collection_4017131c10c127f47b8ea68ff2d8c3c3265c2f6cb11c1b175dd52c23882bd399`, ordered source-set
  hash는 `sha256:1168c8c9cfcaa3671f42391436bfff713c90f01baec468e5ef2509ddb95dbad2`다. Exact source는
  `reports/memory-development/sources/d104/` 아래 세 파일이다. Pyfakefs source는 5,188 bytes/file SHA
  `sha256:8a139248e3e53e3a563366c6a2f9ad213a6a164831bd3cef2a3e5b6cb37008e8`, HF Hub source는 5,333
  bytes/`sha256:87b1b751634d8c34ef125042e472807828a7820064f25e413a51d0755b5b51da`, tox source는 5,416
  bytes/`sha256:d5b22f7c2ca75a271cf60cd52eb9089f2fd54bec99f5c9a75d09c311e0311505`다. AnyIO와 Loguru hold
  group은 source 0개로 유지한다. Portable gate는
  `reports/memory-development/d104-three-rule-source-materialization-gate.json`, gate/body ID
  `d104_61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11`/
  `sha256:61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11`, 12,705-byte file SHA
  `sha256:8eeb26d6f5e0ff22658501afe54bd8cebe35896dc18b60f8f73355ec53190dd0`다. D-104는 mandatory
  `MemoryEntry.index_version`을 꾸며내지 않는다. 따라서 D-104가 만든 actual indexed `MemoryEntry`, rendered
  memory, embedding과 index count는 모두 0이고 index build/freeze, retrieval, core와 analysis는 false다.
  Historical index state는 inspect하거나 수정하지 않았다. Inherited D-099 validator가 tracked public submitted
  patch copy의 integrity는 재검증했지만 D-104 source에 patch/raw trace를 복사하거나 patch body에서 새 의미를
  작성하지 않았다. Raw SQLite/event/search-read artifact, private/hidden/reference/evaluator/provider body는 읽지
  않았다. Verification은 focused 30/30, D-097~D-104/memory/contracts/CLI/qualification related 530/530이다.
  Repository-wide는 1,853 collected 중 1,845 passed/7 environment-dependent skipped/1 failed다. 유일한 failure는
  기존 order-dependent D-093 SQLite WAL/SHM before/after invariant이며 exact test는 fresh isolated process에서
  1/1 통과했다. 이를 D-104 failure나 fix로 합산하지 않는다. D-104 provider/evaluator call과 added model cost는
  0/0/`$0`다. 다음 gate는 deterministic model-facing renderer와
  2,000-token policy를 고정하고 pinned embedding/index-build authorization을 별도로 준비하는 것이며, 자동 index
  build나 core 실행이 아니다.
- Historical D-103 state: `D-103 exact candidate approval receipt and live-journal-bound admission seal recorded; three
  reviewed rule templates admitted for source materialization only, while two groups remain on hold and index/core
  remain closed`다. 사용자는 candidate ID
  `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, semantic body SHA
  `sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, file SHA
  `sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`를 별도 메시지에서 정확히
  다시 입력해 후보 묶음을 승인했다. Approval receipt는
  `reports/memory-development/d103-exact-candidate-approval-receipt.json`, ID
  `d101receipt_23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, semantic body SHA
  `sha256:23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, 6,245-byte file SHA
  `sha256:dad12cf181fee8e113d9da703795eb8ccb4a16be6014218ea923a919d0695031`다. 이 receipt는
  `approver_kind=human`인 self-attestation일 뿐 reviewer identity 인증이나 cryptographic signature가 아니다.
  Live D-102 journal bytes와 candidate/receipt를 다시 검증한 admission seal은
  `reports/memory-development/d103-maintainer-assisted-admission-seal.json`, ID
  `d101seal_3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, semantic body SHA
  `sha256:3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, 19,357-byte file SHA
  `sha256:af1e6ea8811445f26d542f34500d1a7b3919392bef00c98b71f4c26ded236e8e`다. Seal은 1·2·5번의
  rule template 3개만 admission하고 3·4번 hold 2개를 그대로 보존한다. 따라서 full five-group review는
  finalized가 아니며 D-103 checkpoint의 unindexed source record count는 0이다. Memory source authoring만
  unlocked이고 index build/freeze, core와 analysis는 false다. Portable D-103 gate는
  `reports/memory-development/d103-exact-candidate-admission-gate.json`, semantic body SHA
  `sha256:4a542cd571ffc0b94b6f95e106fd2371425dd66f82cfa6091cc602905036fb1f`, 5,315-byte file SHA
  `sha256:4602a579d7c11dd300e2f9bede38e8a6d7bf21c78a8fbfc255550b7d86f3d354`다. Verification은 focused
  7/7, D-097~D-103/memory/contracts/qualification related 497/497, repository-wide 1,823 collected 중
  1,816 passed/7 environment-dependent skipped/failure 0이다. D-103 provider/evaluator call과 added model cost는
  0/0/`$0`다. 당시 다음 gate는 admitted template 3개를 strict unindexed source wrapper로 materialize하고 leak
  scan과 schema/provenance validation을 통과시키는 것이었으며, 이 작업도 index build/freeze나 core를 자동으로
  열지 않는다.
- Historical D-102 state: `D-102 exact maintainer-assisted five-group decision journal and externally anchored admission
  candidate recorded; exact candidate approval receipt, seal, admitted memory, index and core remain closed`다.
  사용자는 한글 검토 문서를 확인한 뒤 1·2·5번은 `기억에 추가`, 3·4번은 `나중에 결정`으로 명시적으로
  확정했다. 시스템이 공개 근거에서 정리한 이유를 연결했으므로 5개 record는 모두
  `reviewer_kind=maintainer_assisted`이고 사용자가 직접 기술적 rationale를 작성했다고 주장하지 않는다.
  Authoritative journal은
  `reports/memory-development/d102-maintainer-assisted-group-decisions.jsonl`, 5 records/correction 0,
  head `sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469`, 7,829-byte
  file SHA `sha256:5c46e6b6a49e436794c1b118f96a9d05caa48a4cd4199e9791ec2ec4499327e3`다.
  Exact journal head/count/file SHA를 외부 입력으로 다시 고정해
  `reports/memory-development/d102-maintainer-assisted-admission-candidate.json`을 만들었다. Candidate ID는
  `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, semantic body
  SHA는 `sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, file은
  31,148 bytes/`sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`다.
  Candidate는 approve 3/reject 0/continue-hold 2와 projection-only preview entry 3개를 포함하지만 admission이
  아니다. D-102 portable gate는
  `reports/memory-development/d102-maintainer-assisted-decision-candidate-gate.json`, semantic body SHA
  `sha256:27e6b50c156e2c590e4225302534c5fedca67596eae2c831d03d3a4810c11732`, 5,453-byte file SHA
  `sha256:e8ff1cdecdb7b107593f43f0b68b564abab34668558a0bb367296e16fbcca373`다. Focused verification은
  6/6, D-097~D-102/memory/contracts/CLI/qualification related verification은 405/405 pass다. Repository-wide는
  1,816 collected 중 1,809 passed/7 environment-dependent skipped/failure 0이다. Receipt와 seal은 absent,
  admitted memory rule은 0이고 두 hold가 남아 full group review도
  finalized가 아니다. Memory source authoring, index build/freeze, core와 analysis는 모두 closed다. D-102는
  provider/evaluator call 0/0, added model cost `$0`이며 성능 향상, negative transfer, hidden cause 또는 agent
  defect에 대한 evidence가 아니다. D-099~D-101 artifact와 hash는 unchanged다. 다음 gate는 사용자가 위 exact
  candidate ID/body SHA/file SHA를 별도 메시지에서 다시 명시해 승인하는 것이다. 그 전에는 receipt나 seal을
  만들지 않는다.
- Historical D-101 state: `D-101 exact five-group review packet and candidate -> explicit receipt -> live-journal-bound
  admission seal mechanism implemented offline; production decisions, candidate, receipt, seal, index and core remain
  closed`다. D-101은 D-099 proposal과 D-100 source gate를 exact bytes/hash로 다시 검증하고, 5개 검토 항목을
  같은 순서로 보여 주는 기계 판독용 JSON과 사람용 Markdown 문서를 만들었다. 사람용 Markdown은 쉬운 한국어로
  작성됐으며 내부 group ID, hash, 영문 상태명을 노출하지 않는다. 사용자는 문서의 1~5번 항목에 대해
  `기억에 추가`, `사용하지 않음`, `나중에 결정` 중 허용된 한국어 선택과 이유를 답한다. 3번과 4번은 근거가
  더 필요하므로 `사용하지 않음` 또는 `나중에 결정`만 선택할 수 있다. 어떤 선택도 미리 고르거나 권고하지 않는다.
  일반적인 `진행해줘` 요청은 이 선택이나 exact candidate approval이 아니다. Future
  candidate는 complete non-synthetic D-100 journal과 caller가 외부에서 고정한 head/count/file SHA를 모두 요구하고,
  canonical journal 전체와 effective decisions, non-indexing D-100 preview를 포함한다. Receipt는 candidate ID,
  semantic body SHA와 file SHA를 사용자가 명시적으로 다시 입력해야 하며 self-attested일 뿐 reviewer identity나
  cryptographic signature를 증명하지 않는다. Seal은 exact candidate/receipt와 현재 live journal bytes가 계속
  일치할 때만 생성된다. 승인 entry가 있으면 memory source authoring만 열 수 있지만 index build/freeze와 core는
  계속 false다. Checked-in packet은
  `reports/memory-development/d101-five-group-review-packet.json`과 `.md`다. 기계 판독용 JSON은 한글화 전과
  byte-for-byte 동일하며 JSON semantic body SHA는
  `sha256:bd78712747b1718ed8c9c4f67324bd8f11f564c76c041d3108843b2da0224947`, JSON file은 17,494 bytes/
  `sha256:e7d4acf48dbcac1e366964fc2ed8ceb924d9907f2cb2ddeed94a23ef816c93ef`다. 한글 Markdown은 12,872 bytes/
  `sha256:9fc8e51dc867d66672b7c5334402bafdc27759914df88df09d506a5832d479c5`다. Source gate는
  `reports/memory-development/d101-group-admission-source-gate.json`, semantic body SHA
  `sha256:26838ab1e8097e47f53e712ce11d0d8a603cd4dd3dff408792f77f7d164fe4f9`, 3,807-byte file SHA
  `sha256:987cded0f469370f3f9c5542c8353f7153429d7b3743df9af003f2f594b3a275`다. Production human decision,
  candidate, receipt, seal과 admitted rule은 모두 0/absent이고 admission/index/core/analysis는 closed다. D-101
  자체 provider/evaluator call과 added model cost는 0/0/`$0`다. 한글화 focused verification은 26/26,
  related verification은 399/399 pass이며 repository-wide는 1,810 collected 중 1,803 passed/7
  environment-dependent skipped/failure 0이다. 관련 회귀에서 D-081 historical pricing freshness가 실제 시간의
  72-hour 경계를 넘은 문제는 test clock만 해당 suite의 pricing timestamp로 고정했다. Production qualifier,
  suite와 historical artifact는 바꾸지 않았고 이를 D-101 product/runtime fix로 주장하지 않는다. 다음 gate는
  사용자가 한글 문서의 1~5번 항목을 검토한 뒤 허용된 한국어 선택과 이유를 각각 제공하는 것이며, 그 전에는
  production journal을 쓰지 않는다.
- Historical D-100 implementation details: `D-100 exact D-099-bound append-only semantic-group decision journal and non-indexing
  MemoryEntry preview mechanism implemented offline; production human decisions, admission seal, index, core and
  analysis remain closed`다. 새 `memory-group-review-decision-d100-v1`은 exact D-099 proposal file/body identity,
  group ID/fingerprint와 candidate의 normalized proposed-rule hash를 결속한다. Global contiguous sequence와
  previous hash, group별 exact supersedes hash, caller-provided action ID/input hash, explicit expected-tail CAS,
  cross-process sidecar lock, canonical JSONL append와 flush/fsync를 요구한다. 같은 action ID와 같은 입력의
  retry는 append 없이 기존 record를 반환하고 다른 입력 재사용, stale tail, noncanonical/blank/partial-tail/
  reordered/hash-inconsistent chain과 leak-shaped rationale를 fail closed한다. Proposal validation과 사용 bytes,
  journal decision과 descriptor는 각각 하나의 immutable snapshot에 결속한다. Candidate만 exact rule을 approve할 수 있고 hold는
  `continue_hold|reject`만 가능하며 rule 수정은 journal이 아니라 새 proposal이 필요하다. Complete 5-group
  decision chain만 `memory-entry-preview-d100-v1`으로 projection할 수 있다. 승인 group 하나당 template 하나를
  만들고 D-099 member order, failure/evidence provenance와 rule field를 보존하며 `validation_count=0`이다. Preview는
  실제 `MemoryEntry`가 아니므로 `index_version`, embedding과 frozen state를 갖지 않는다. Existing failure별
  review/build/freeze path는 호출하거나 연결하지 않는다. Portable source gate는
  `reports/memory-development/d100-group-review-projector-source-gate.json`, semantic body SHA는
  `sha256:5ac180b32fef27d5937c1447e39f01bafda65ce6b5a3eef1992a7da45cab9b2b`, 5,048-byte file SHA는
  `sha256:866bad69dad24dd908339330f27a24a388e64b453e6dc403363836292ea24e47`다. 이 source gate는
  production human decision 0, admitted rule/preview entry 0/0, admission/index/core false와 provider/evaluator
  call 0/0, added cost `$0`을 결속한다. 사용자의 일반적인 구현 진행 요청을 5개 group의 실제 human decision으로
  해석하지 않았으므로 authoritative decision journal은 만들지 않았다. 다음 gate는 exact group/fingerprint/rule
  hash에 대한 명시적 human decision과 그 결과의 externally anchored portable admission seal이다. Reviewer kind는
  `human|maintainer_assisted|synthetic` self-attestation일 뿐 인증 서명이 아니다. Standalone chain은 whole-row suffix
  삭제나 완전 재해시 rewrite를 감지할 수 없으므로 future seal은 explicit expected head/count와 file SHA를 결속해야 한다.
  Current verification은 D-100 focused 28/28과 D-099/historical-memory/CLI/contracts/D-097/D-098 related 154/154다.
  Final exact tree의 repository-wide run은 1,784 collected 중 1,776 passed/7 environment-dependent skipped/1
  failed다. 유일한 failure는 pre-existing/order-dependent
  `tests/test_d092_policy_replay_raw.py::test_d092_raw_public_replay_exactly_rebuilds_portable_manifest`의 WAL/SHM
  before/after invariant이며 fresh isolated process에서 1/1 통과했다. 이를 D-100 pass나 수정으로 합산하지 않는다.
  Ruff, compileall, exact 5,048-byte source rebuild와 `git diff --check`도 통과했다. 초기 full run은 historical
  D-077 positive qualification test가 실행 당시 wall clock과
  2026-08-02 pricing timestamp의 72-hour freshness 경계를 넘어 1건 실패했다. Production qualifier, suite YAML,
  pricing timestamp와 historical artifact는 그대로 두고 그 test의 clock만 historical start instant로 고정했으며,
  isolated 1/1과 이후 full run에서 통과했다. 이를 D-100 product/runtime fix나 historical result 변경으로 합산하지 않는다.
- Historical D-099 milestone은 `D-099 D-098 public-evidence memory review and semantic deduplication proposal sealed;
  group admission, review history, index, core and comparative analysis remain closed`다. D-098의 official
  task-failure candidate 9개를 public task, agent-visible search/read artifact, submitted patch, registered
  visible-check summary, diff/review/submission lifecycle metadata와 generic task-failure outcome만으로 검토했다.
  Exact partition은 pyfakefs 2, HF Hub 2, AnyIO 1, Loguru 2, tox 2의 5개 semantic group이다. Pyfakefs,
  HF Hub와 tox의 3 group/6 source는 candidate rule proposal이고 AnyIO 1과 Loguru 2의 2 group/3 source는
  reusable rule의 일반화 경계가 미확정이라 hold다. Loguru 제출 patch의 secondary diagnostic-formatting defect는
  public code에서 구체적으로 보이지만 broader formatter rule은 hold하며, AnyIO도 cancellation/owner-lifecycle
  risk가 보이지만 단일 eligible run만으로 일반 rule을 승인하지 않는다. 이는 exact hidden cause나 agent architecture
  defect를 확정한 분류가 아니다. PDM resolved 2개와 canonical pre-provider AnyIO budget terminal 1개를 포함한
  12-row partition도 exact 검증한다. Proposal은
  `reports/memory-development/d099-public-evidence-review-dedup-proposal.json`, semantic body SHA는
  `sha256:63c74999242f6217f2a81c9c2dc22d618d2be137948580f93401341c4ea49574`, 77,942-byte file SHA는
  `sha256:24e34b02a66fc132d333bb51614a10786d38bc188b5550432a5f21f435f21493`다. 9개 submitted
  task-failure patch는 별도 portable public artifact로 복사해 D-098 SHA와 결속했고 74개 selected public event
  reference는 event hash와 CAS로 raw snapshot에서 검증했다. Portable validator는 `.patchloop` 없이 D-098 seal,
  frozen manifest와 public spec, patch copy, group algebra, self hash와 leak scan을 검증한다. Explicit raw mode는
  copied SQLite/WAL만 읽고 원본 DB/WAL/SHM byte·mtime fingerprint 불변을 요구한다. 기존
  `memory-review-proposal-v1`, `review_failure`와 failure별 index builder는 변경하거나 호출하지 않는다. 따라서
  `human_admission_status=pending`, admitted rule 0, review history 0이고
  `memory_admission_unlocked=false`, memory index/core/comparative analysis는 닫혀 있다. D-099 자체
  index/history 상태는 D-099 proposal에 한정된 주장이다. 기존 historical unfrozen memory artifact의 존재를
  부정하거나 이를 D-099 index로 승격하지 않으며, D-099은 그 artifact를 수정하지 않았다. D-099 자체
  provider/evaluator call과 added model cost는 0/0/`$0`이다. 다음 gate는 semantic-group 단위 append-only human
  decision과 group-aware proposal consumer이며 자동 admission이나 현재 failure별 builder 사용이 아니다. Final
  verification은 D-099 focused 13/13, historical memory/D-097/D-098 related 126/126, Ruff, compileall, exact
  77,942-byte rebuild와 `git diff --check`가 통과했다. Repository-wide 1,756 collected 중 1,749 passed/7
  environment-dependent skipped이고 failure는 0이다. Historical D-092 order-dependent WAL/SHM failure는 이번
  full-order run에서 재발하지 않았지만 D-099 수정이나 원인 해결로 주장하지 않는다.
- Historical D-098 milestone은 `D-098 D-097 measured no-memory baseline result sealed; exact development denominator and
  memory review eligibility observed, while admission, index, core and comparative analysis remain closed`다.
  Exact experiment `dev-no-memory-condition-neutral-3000k-20260805-r1`은 source commit
  `67fa85e47c5cf39c0ee03ad69d9d31f9fdd11ac3`과 승인 execution hash
  `sha256:1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4`로 정확히 한 번
  실행됐다. 12/12 row가 terminal·qualified·cost-settled이고 final
  `condition-neutral-no-memory-baseline-admission-gate-v2`가 통과했다. Terminal branch는 11 official evaluator와
  1 canonical pre-provider total-token budget block으로 exact-one이며 결과는 2 resolved, 9 task failure,
  1 agent failure다. Exact development SCRR는 2/12이고 PDM만 2/2 성공했다. 이는 held-out 성능이나 memory
  효과가 아니다. 총 사용량은 10,492,742 input + 881,967 output = 11,374,709 token, 613 model/964 tool call,
  7,258,662ms이며 usage-derived standard list-price 계산은 `$11.838408`이다. Invoice/free-tier charge 주장이
  아니다. 613/613 issued response는 completed이고 exact input telemetry, truncation disabled, `store=false`,
  previous-response dependency 0을 확인했다. AnyIO r1은 2,964,853 token 뒤 다음 exact request에 26,231 token이
  부족해 provider call 전에 차단됐으며 memory candidate가 아니다. Official task failure 9개만
  `memory_review_eligible` candidate이고 success 2개와 budget terminal은 제외된다. Portable append-only seal은
  `reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json`, semantic body SHA는
  `sha256:e35cab52597c3ec6e884f074f9acf346dec65301e22d11edc2de56db7be9eacf`, 117,209-byte file SHA는
  `sha256:ad87fa8c540552da62d964a430c29b032097b5cabbe78f0102c23cf36330b2dc`다. Raw result/journal/qualification은
  수정하지 않았고 exact experiment ID는 hard-consumed다. `comparison_denominator_eligible=true`와
  `memory_review_eligible=true`만 열렸으며 `memory_admission_unlocked=false`, memory index/core/comparative
  analysis는 닫혀 있다. D-098 seal 자체 provider/evaluator call과 added model cost는 0/0/`$0`이다. 다음 gate는
  9개 public-evidence candidate의 review·semantic dedup·leak scan이며 자동 rule admission이나 index build가 아니다.
  Builder는 copied SQLite/WAL snapshot에서 qualification/source evidence를 재계산하고 원본 DB/WAL/SHM의
  byte·mtime fingerprint 불변을 검증한다. Canonical `sealed_at`과 budget manifest/result/provenance exact binding도
  fail closed한다. Final verification은 D-096~D-098 focused 106/106, related seal/experiment/qualification 438/438,
  Ruff, compileall, exact 117,209-byte rebuild와 `git diff --check` pass다. Repository-wide 1,743 collected 중
  1,735 passed/7 environment-dependent skipped이고 기존 D-092 WAL/SHM order-dependent invariant 1건만 full-order에서
  실패했으며 동일 test는 fresh isolated process에서 1/1 통과했다. 이를 D-098 pass나 수정으로 합산하지 않는다.
- Historical D-097 milestone은 `D-097 exact condition-neutral 3M no-memory successor source, runtime-v2 binding and
  campaign-scoped full-schedule reserve implemented offline; clean preflight, execution hash, approval, live result,
  memory and core authority remain closed`다. Exact suite는
  `dev-no-memory-condition-neutral-3000k-20260805-r1`이며 file identity는 2,741 bytes,
  `sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0`다. Frozen memory-development의 Loguru, AnyIO, tox,
  HF Hub, PDM, pyfakefs를 이 source order로 `no_memory` 각 2회, seed `20260723`에 배치한다. D-096의
  source-identity hash `sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b`는
  pre-shuffle task/condition/repetition/seed contract이고, 실제 deterministic expanded order의 별도 hash는
  `sha256:dff4f38db99bcbc878e917a6c76e10a6c244701d2a8eb5ea4b43daf427a305ba`다. 두 hash를
  같은 의미로 사용하지 않는다. Runtime tuple은 exact D-096 profile
  `gpt54mini-v2v5-condition-neutral-3000k-v1`: `gpt-5.4-mini-2026-03-17`
  medium/standard/default, retry 0, `SYSTEM_PROMPT_V3`, tool v2/context `phase-evidence-v5`, output 25,000,
  memory allowance 2,000과 `null/null/3,000,000/3,600`이다. 새
  `condition-neutral-comparison-runtime-contract-v2`와 `condition-neutral-comparison-runtime-evidence-v2`는
  exact successor ID에만 선택되고 execution plan/hash, `RunManifest`, content-addressed `RunStarted`,
  fresh start/resume와 qualification에서 D-096 resource-policy/admission CAS를 재검증한다. D-083/D-084의
  1.6M runtime-v1과 모든 historical suite/result/qualification은 수정하거나 v2로 재해석하지 않는다.
  Campaign cost policy는 `campaign-list-price-full-schedule-reserve-v1`이다. 첫 provider call 전에 하나의 fsync된
  `FullScheduleCostReserved` event가 12-row schedule과 row별 `$13.6125`, full reserve `$163.35`를 결속하고,
  같은 plan/CAS/journal을 각 row 전에 다시 검증하며 terminal row마다 deterministic settlement를 기록한다.
  Prospective campaign-scoped source cap은 `$164`다. 이는 per-row atomic SQLite capability/consumption,
  historical project cap `$150` 변경, 사용자 예외 승인 또는 expected invoice/free-tier claim이 아니다. Live resume은
  disabled다. D-097 cost journal 자체는 duplicate paid-call prevention을 주장하지 않으며, 기존 one-use execution
  hash가 authorization을 단일 sequential campaign invocation으로 제한할 뿐이다. Post-run reconciliation은
  `CampaignCompleted`와 persisted result를 다시 결속하고 rehashed foreign/duplicate terminal event를 거부하지만,
  이는 evidence-integrity 검증이지 이미 발생한 paid call 방지 주장이 아니다. Exact clean-commit preflight
  hash와 최대 `$164`, `$150` 예외에 대한
  별도 사용자 승인이 여전히 필요하며 blocker는
  `NO_MEMORY_CLEAN_PREFLIGHT_AND_164_USD_APPROVAL_PENDING`이다. Baseline terminal은 completed official evaluator의
  `resolved|task_failure` branch 또는 canonical pre-call total-token/wall budget `agent_failure` branch 중
  exact-one이어야 하며 runtime completion output은
  `condition-neutral-no-memory-baseline-admission-gate-v2`다. 두 branch 모두 denominator row지만
  budget/infrastructure failure는 memory candidate가
  아니고 task success·hidden acceptance·SCRR는 source completion predicate가 아니다. Future 12-row denominator
  gate가 통과하면 campaign-level `memory_review_eligible=true`가 된다. Review candidate pool은 그중
  official-evaluator task failure로만 제한되고 budget/infrastructure failure는 제외된다. 이 상태도 automatic
  admission이 아니며 별도 review/dedup/leak gate 전에는 `memory_admission_unlocked=false`다. 현재 source 단계에서는
  두 값 모두 false/closed다. Source artifact는
  `reports/live-pilot/artifacts/d097-condition-neutral-baseline-source-gate.json`이며 semantic body SHA는
  `sha256:05d952065136a45914e2fb3c44edcbb553732c9f33484c5412b9135062c6481b`, file SHA는
  `sha256:21ed073ad1fbe1985e7a46cabebbfdc836baa303c4434e0777152c1d2d88a777`, size는 21,029 bytes다.
  Builder 자체는 runtime verifier가 아니며 별도 executable test가 source/runtime/qualification/final-seal wiring을
  검증한다. D-097 focused 65/65와 D-084~D-097 관련 회귀 354/354가 통과했다. Repository-wide single run은
  1,728 collected 중 1,720 passed/7 skipped/1 failed로 655.4초에 끝났다. 유일한 failure는 pre-existing/order-dependent
  `tests/test_d092_policy_replay_raw.py::test_d092_raw_public_replay_exactly_rebuilds_portable_manifest`의 WAL/SHM
  before/after invariant였고 exact test는 즉시 isolated 1/1로 통과했다. 따라서 이를 monolithic 1,721 pass/7 skip으로
  보고하지 않는다. Ruff, compileall, exact source rebuild와 `git diff --check`도 통과했다.
  Source 단계의 provider/evaluator call과 added model cost는 0/0/`$0`이다. Clean no-call preflight,
  candidate/approved execution hash, live run/result, completed denominator, memory review/admission/index, core와
  analysis는 모두 닫혀 있고 자동 실행하지 않는다.
- Historical D-096 milestone은 `D-096 prospective condition-neutral resource policy and exact no-memory baseline admission
  contract frozen offline; runtime v2, successor suite, live result, memory and core authority remain closed`다.
  Future comparison의 exact profile은 `gpt54mini-v2v5-condition-neutral-3000k-v1`이며 모든 memory condition에
  `gpt-5.4-mini-2026-03-17` medium/standard/default, SDK transport retry 0, `SYSTEM_PROMPT_V3`, tool v2,
  context `phase-evidence-v5`, output 25,000, memory allowance 2,000과 model/tool call `null`, total token
  3,000,000, wall 3,600초를 동일하게 적용한다. 이 budget은 비교 target이 아닌 finite safety ceiling이며
  completion guarantee가 아니다. D-083/D-084의 1.6M/runtime-v1 계약은 historical run에 그대로 유효하고
  수정되지 않는다. 새 `condition-neutral-comparison-runtime-contract-v2`와 runtime evidence v2는 이름만
  prospectively 선택됐으며 아직 execution plan, `RunManifest`, start/resume와 qualification에 구현되지 않았다.
  No-memory admission은 frozen memory-development의 Loguru, AnyIO, tox, HF Hub, PDM, pyfakefs 여섯 task를
  각 2회, `no_memory`, seed `20260723`으로 실행하는 exact 12-row schedule
  `memory-development-no-memory-12-row-v1`만 고정한다. Historical 1.6M template은 schedule carrier일 뿐이며
  새 3M successor suite가 필요하다. Builder는 D-094 source artifact의 exact pricing block에서 rate와 reserve를
  재도출하고, 여섯 `public.yaml` 각각의 bytes/file SHA가 frozen dataset manifest의 `public_spec_hash`와 일치하는지
  검증한다. Official-evaluator row와 canonical pre-call total-token/wall budget-terminal row는 disjoint·exhaustive
  terminal class이며, issued response는 모두 `completed`여야 한다. Task success와 hidden outcome은 admission 또는 policy 선택 조건이 아니고,
  D-087/D-095도 소급 baseline row로 승격하지 않는다. D-096이 연 것은 comparison policy freeze,
  baseline-admission contract와 future source authoring뿐이다. New suite, live execution/result, completed
  denominator, memory review/admission/index, core와 analysis는 계속 닫혀 있다. Worst-rate reserve는
  `$13.6125`/run, `$163.35`/12 run인데 기존 project cap `$150`보다 `$13.35` 크므로 campaign cost policy와
  cap conflict가 `NO_MEMORY_AUTHORIZATION_CAP_PENDING`으로 남는다. Artifact는
  `reports/live-pilot/artifacts/d096-condition-neutral-resource-policy-baseline-admission.json`, semantic body SHA는
  `sha256:2e9360d92db5224d181fe8f18254da3850f324b33b24f3833633589085e3b75d`, file SHA는
  `sha256:5c032cff1045a39d1d8d9757205a920b1cd1cfd948c7c4e3e5b526ae6744661d`, size는 19,031 bytes다.
  D-096 provider/evaluator call과 added model cost는 0/0/`$0`이다. Focused 26/26과 관련 계약 178/178이
  통과했다. Repository-wide 1,663건 중 1,656건은 통과하고 7건은 environment-dependent skip이며, shard에서
  순서 의존으로 실패한 D-092 WAL/SHM invariant 1건은 독립 프로세스에서 통과했다. Parsed exact rebuild와
  `git diff --check`도 통과했다. 다음 gate는 runtime v2 binding, 새 exact
  12-row suite, non-censoring cost policy/cap resolution과 clean no-call preflight를 구현하는 별도 source gate다.
- Historical D-095 milestone은 `D-095 D-094 measured result sealed; exact three-row workflow readiness passed,
  task success/SCRR 0/3, and no baseline, denominator, memory, or core authority`다. Exact experiment
  `generic-high-headroom-readiness-v2v5-20260804-r1`은 source commit
  `82fbb33f20cabb57a151db871782345c6cafa3f0`과 승인 execution hash
  `sha256:ae54b9cc14e3bcb80cbead61a003012cec4dbd0e8a205917b3cefdeaf0c11d75`로 정확히 한 번
  실행됐다. AnyIO, pyfakefs, HF Hub 세 row 모두 terminal·trace-qualified·accepted submission·official
  evaluator에 도달했고 infrastructure/qualification/diagnostic/budget/terminal-loop confound는 0이므로
  `generic-high-headroom-readiness-gate-v1`은 3/3 통과했다. 세 row 모두 regression/scope/safety는
  통과했지만 hidden acceptance가 실패해 task success와 SCRR은 0/3이다. 총 사용량은 63 model/119 tool
  call, 957,052 input + 48,805 output = 1,005,857 token, 계산상 고정 list-price 비용은
  `$0.9374115`다. 이는 billed invoice나 free-tier charge 주장이 아니다. Portable append-only seal은
  `reports/live-pilot/generic-high-headroom-readiness-v2v5-20260804-r1.json`, semantic body SHA는
  `sha256:79fe3312222896beec28070b5a77e36ffc7854a00c983a70f90cbe37ac2bb99f`, file SHA는
  `sha256:62ef705c992fcdb3e6e6b648e8376c4d5fdbff2534bd5b0a37158b99b4b3f95e`다. Raw result,
  journal, qualification과 evaluator result는 수정하지 않았고 exact experiment ID는 static hard-consumed라
  재실행하지 않는다. 이 결과는 workflow-completion calibration일 뿐 no-memory performance baseline,
  comparison denominator, resource-policy sufficiency, memory review/admission/index 또는 core campaign을
  열지 않으며 hidden-driven tuning이나 자동 재실행도 승인하지 않는다. D-095 seal 자체 provider/evaluator
  call과 추가 model cost는 0/0/`$0`이다. Final verification은 focused/relevant 303/303과 repository-wide
  split 1,637 collected 중 1,630 passed/7 environment-dependent skipped를 통과했다. Single-process full run은
  실패 없이 79%에서 10분 orchestration timeout에 도달했다. File shard 1은 644 passed/1 skipped, file shard
  2는 D-092 WAL/SHM order-sensitive invariant 한 건 외 985 passed/6 skipped였고 그 invariant는 같은 current
  tree의 isolated process에서 통과했다. Historical pricing fixture는 fixed-time으로 만들어 shard 안에서
  통과했다. Ruff, compileall, exact rebuild, JSON/hash와 `git diff --check`도 통과했다.
- Historical D-094 milestone은 `D-094 exact three-task high-headroom readiness source/offline gate complete; no clean preflight,
  execution hash, approval, provider execution, baseline, denominator, memory, or core authority`다. Exact suite
  `generic-high-headroom-readiness-v2v5-20260804-r1`은 frozen memory-development의 AnyIO, pyfakefs, HF Hub를
  이 순서로 `no_memory` 각 1회 배치한다. Runtime은 `gpt-5.4-mini-2026-03-17`
  medium/standard/default, SDK transport retry 0, `SYSTEM_PROMPT_V3`, tool v2/context `phase-evidence-v5`,
  output 25,000, memory allowance 2,000과 model/tool call `null`, total token 3,000,000, wall 3,600초를 exact
  experiment ID, execution plan, `RunManifest`, content-addressed `RunStarted`, start/resume, qualification과 budget
  diagnostic에 결속한다. 새 schema는 `generic-high-headroom-readiness-runtime-contract-v1`,
  `generic-high-headroom-readiness-runtime-evidence-v1`, `generic-high-headroom-readiness-gate-v1`이다. Readiness는
  3/3 terminal·qualified·accepted submission·official evaluator, persisted qualification과 read-only recomputation
  exact match, exact input/completed response/truncation-disabled telemetry와 infrastructure/qualification/diagnostic/
  budget-terminal/terminal-loop/model-or-tool-call-budget confound 0을 요구한다. Task success, hidden acceptance와
  SCRR은 gate 조건이 아니다. 2026-08-04T14:47:00Z official standard rate로 worst reserve는 `$13.6125`/run,
  `$40.8375`/suite이고 source cap은 `$41`이다. Source artifact는
  `reports/live-pilot/artifacts/d094-high-headroom-readiness-source-gate.json`, semantic body SHA는
  `sha256:ab7be9ad2448d1016b88d451e271330844fc11d8fd4b890f08142618446ff929`, file SHA는
  `sha256:6887936ec141496e35e3a9d3bd6c34cf04cf02d1849bf80208677151a692c6ed`다. D-094 자체
  provider/evaluator call과 added model cost는 0/0/$0이다. Final verification은 focused 56/56,
  repository-wide two-shard 1,627 collected 중 1,620 passed/7 environment-dependent skipped이며 Ruff,
  compileall, exact rebuild, JSON/hash와 `git diff --check`가 통과했다. 다음 gate는 이 milestone을 clean commit으로 봉인한 뒤
  Docker/evaluator/dataset/SDK/pricing을 다시 확인하는 no-call preflight다. 그 preflight가 만든 one-use candidate
  hash와 최대 `$41`의 별도 사용자 승인 전에는 provider를 호출하지 않는다.
- Historical D-093 milestone은 `D-093 append-only readiness-stage budget outcome correction complete; D-092 replay result and
  raw outcomes preserved; no runtime, live, baseline, denominator, memory, or core authority`다. D-092가 tested
  repeated-rejection/context-growth policy를 모두 기각하고 current runtime을 유지한 결론은 그대로 유효하다.
  다만 workflow가 official evaluator까지 도달하는지 확인하는 readiness 단계에서 resource ceiling에 걸린 row를
  comparison의 `agent_failure`로 미리 확정한 것은 stage-purpose misclassification이었다. D-093은 D-092 artifact와
  두 AnyIO `RunResult.outcome_kind=agent_failure`를 byte-for-byte 그대로 보존하면서 analytical disposition만
  `readiness_inconclusive` / `budget_confounded`로 정정한다. Historical exact run의 자동 재실행은 허용하지 않고,
  comparison disposition은 explicit content-addressed resource-policy freeze 전까지 pending이다. 다음 gate는
  AnyIO·pyfakefs·HF Hub의 small diverse high-headroom no-memory completion panel을 준비하는 별도 source gate다.
  D-088/D-090 portable seal이 두 raw outcome과 공개 usage를 exact hash로 뒷받침한다. 3,000,000 token은
  `1,956,109 × 1.5`를 100,000 단위로, 3,600초는 `1,628,695ms × 2`를 600초 단위로 올림한 값이다.
  이 값과 model/tool call limit `null`은 현재 candidate일 뿐 freeze나 실행 승인이 아니며 fresh
  pricing, clean source, no-call preflight, new execution hash와 별도 비용 승인이 필요하다. Portable correction은
  `reports/live-pilot/artifacts/d093-readiness-budget-outcome-correction.json`, semantic body SHA는
  `sha256:3a5790e57252132387b803681339e00032c62f7026a81d9acbd9f4598fc64ccd`, file SHA는
  `sha256:df8a35d7818dba3055ee4bb34519bd39abdc97d4d6add178d3d41b0521273941`다. D-093 자체
  provider/evaluator call과 추가 model cost는 0/0/$0이다. Final verification은 focused 32/32,
  repository-wide sharded 1,571 collected 중 1,564 passed/7 environment-dependent skipped이며 Ruff,
  compileall, exact rebuild, JSON/hash와 `git diff --check`가 통과했다.
- Historical D-092 milestone은 `D-092 offline public stall-policy replay complete; retain current runtime policy and classify
  qualified budget terminals as agent failure; no runtime, live, baseline, denominator, memory, or core authority`다.
  Primary panel은 D-081 r3 4개, D-085/D-086 pilot 1개, D-087 12개와 D-089 1개로 구성된 18-run·8-task,
  4,079-event no-memory V2/V5 public trajectory다. Model/prompt/tool/context/memory condition은 같지만 harness
  commit과 total-token ceiling은 다르므로 process-policy replay일 뿐 causal performance comparison이나 baseline
  denominator가 아니다. Simulator는 durable `manifest_json`과 public `event_json`만 SQLite
  `mode=ro&immutable=1`·`query_only`로 읽고 private assertion, hidden/reference/candidate patch, result JSON,
  qualification detail과 model/tool artifact body를 읽지 않는다. Repeated-rejection `N=3..10`은 모두 D-089을
  intercept하는 구간에서 later public progress가 있는 run도 잘랐고, relative-context
  `{2,4,8} × {8,16,32 calls}` 역시 모든 candidate에 false stop이 있거나 cross-task/leave-one-task-out
  generality가 없었다. 90,000-character absolute ceiling만 D-089 하나에서 false stop 0이지만 post-hoc
  single-task sensitivity이고 admission scope 밖이다. 따라서 exact decision은
  `retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure`다. 이는 runtime guard를 추가하거나
  historical outcome을 바꾸지 않으며, selected outcome rule의 four-condition plan·RunManifest·qualification·report
  binding은 다음 offline denominator-admission gate로 남는다. Portable artifact는
  `reports/live-pilot/artifacts/d092-public-policy-replay-decision.json`, semantic body SHA는
  `sha256:6fde1253a7ba92a2cb60b09f05bc070849c1f868e96cc00870cf03eff62782ec`, file SHA는
  `sha256:541b890e2b123a5431060e23dcf4544fce3f7b810cb8cb1a560fbcc245b3fe22`다. D-092 자체 provider/evaluator
  call과 추가 model cost는 0/0/$0이며 live execution, comparison denominator, no-memory baseline, memory
  review/admission/index와 core는 계속 닫혀 있다. Final verification은 focused 20/20, repository-wide sharded
  1,559 collected 중 1,552 passed/7 environment-dependent skipped이며 Ruff, compileall, JSON/hash와
  `git diff --check`가 통과했다.
- Historical D-091 milestone은 `D-091 offline AnyIO public-trajectory audit complete; qualified runtime, repeated invalid-patch
  non-convergence and budget terminal separated; no rerun, budget, baseline, memory, or core authority`다. D-087
  AnyIO repetition 2 `run_4613c65b2a254349`와 D-089 `run_e444de1bb20a4325`의 public task, portable seal,
  manifest/qualification과 durable event metadata만 비교했다. Private assertion, hidden/reference/candidate patch
  body와 model/tool artifact body는 분석에 사용하지 않았다. D-087은 93 model/139 tool call, 1,578,208 token,
  1,222,996ms였고 D-089은 더 적은 79/121 call로 1,956,109 token과 1,628,695ms를 사용했다. D-089은 유일한
  `PatchApplied` seq 103 뒤 68 model call, 96 tool call과 1,772,530 token을 소비했지만 추가 `PatchApplied` event는 0이며
  14개 apply candidate가 거부됐다. 마지막 실패 visible check seq 391 뒤에도 863,211 token, 27 model call,
  32 tool call, 9개 rejected patch와 861,196ms를 사용했고 mutation/check/get_diff/finish는 0이었다. 두 run의
  visible check는 합계 14/14 실행됐지만 pass는 0이다. Retry rehydration은 D-087 20/20, D-089 15/15이고
  failed source sequence는 0이며 qualification은 각각 28/28과 27/27이다. 따라서 직접 terminal trigger는
  total-token guard지만 budget 부족이 completion root cause라는 주장은 성립하지 않는다. 별도 동일 task D-087
  repetition 1은 534,853 token에서 evaluator에 도달했으므로 process variance도 크다; 그 task/hidden outcome은
  분석에 사용하지 않았다. Classification은 `qualified-process-nonconvergence-ending-in-budget-terminal`이며
  harness defect는 관측되지 않았지만 ruled out도 아니다. 2.4M/3M은 관측 prefix의 token threshold만 넘기고
  171,305ms wall headroom은 그대로이므로 completion guarantee가 아니다. Artifact는
  `reports/live-pilot/artifacts/d091-anyio-public-trajectory-audit.json`, SHA는
  `sha256:74b6b229520d3358e7fbd33faad3b0be532405bbe5711a35c4d064114ba8e9a7`이다. D-087/D-089은 immutable하고
  D-091 자체 provider/evaluator call과 model cost는 0/0/$0이다. 다음 gate는 repeated-invalid-patch와 context
  growth를 유지·generic fail-fast·generic ceiling 중에서 offline public cross-task evidence로 결정하는 것이며
  새 live execution과 budget freeze는 열리지 않는다. Final verification은 focused 238/238, repository-wide
  sharded 1,539 collected 중 1,532 passed/7 environment-dependent skipped이며 Ruff, compileall, JSON/hash와
  `git diff --check`가 통과했다.
- Historical D-090 milestone은 `D-089 measured result sealed; exact one-row workflow remained qualified but stopped at
  the 2M total-token guard before submission/evaluator; no rerun, baseline, memory, or core authority`다. Exact
  execution hash `sha256:dafb1182bc77a80a19384406a528997d608dc935201df63e7fdc1ef5aad471c3`는 clean source
  commit `7f3e6debb2a67f4b108c4422fa4cf51ebfea994f`에서 정확히 한 번 소비됐고 run은
  `run_e444de1bb20a4325`다. Run은 terminal·qualified 27/27이지만 1,737,041 input + 219,068 output =
  1,956,109 token 뒤 남은 43,891 token으로 exact input 33,804와 output allowance 25,000을 함께 예약하지
  못했다. Deficit은 14,913이고 same-prefix next-call minimum은 2,014,913이다. 따라서 evaluator/official은
  0/1, budget-terminal 1이며 readiness gate는 false다. Wall headroom은 171,305ms여서 binding dimension은
  total token뿐이다. 79/79 response는 completed이고 exact token telemetry, truncation disabled, `store=false`,
  previous-response dependency 0을 보존했다. 계산 비용은 `$2.28858675`이며 승인 cap `$10` 안이다. Raw result
  SHA는 `sha256:60dccc5e58e53accba3c2c68d241fc0d79bf1752f0fea8866c30de1594065b55`, journal final hash는
  `sha256:ea7f5fb5d6e39f80bf5b2c374959ea0bc4e6f9a3fb10affd969cb80528e7042c`다. Portable seal은
  `reports/live-pilot/anyio-workflow-completion-budget-only-v2v5-20260804-r1.json`, SHA는
  `sha256:06006c95454618b7adcea305465fa63611d2043c70aaa3e1df2de9a3f5a192f1`다. D-089 ID는
  workflow-completion consumed set에 들어가 clean machine에서도 재실행을 차단한다. Seal 자체 provider
  call/model cost는 0/$0이고 no-memory baseline, comparison denominator, memory review/admission/index와 core는
  계속 닫혀 있다. Final seal verification은 focused 232/232, repository-wide sharded 1,533 collected 중
  1,526 passed/7 environment-dependent skipped이며 final D-090 report/plan/manifest retest 4/4, Ruff, compileall,
  JSON parse와 `git diff --check`를 통과했다.
- Historical D-089 source milestone은 `AnyIO budget-only readiness probe source/offline gate complete; no clean preflight,
  approval, provider execution, baseline, memory admission/index, or core authority`다. Exact source는
  `experiments/anyio-workflow-completion-budget-only-v2v5-20260804-r1.yaml`이고 D-087에서 evaluator 전에
  total-token guard로 종료한 AnyIO repetition 2만 새 experiment에서 한 번 다시 관찰한다. D-087
  `run_4613c65b2a254349`는 1,578,208 token 뒤 남은 21,792 token으로 exact input 14,080과 output
  allowance 25,000을 함께 예약하지 못했으며 same-prefix minimum은 1,617,288이다. 새 profile은
  `gpt-5.4-mini-2026-03-17` medium/standard/default, retry 0, `SYSTEM_PROMPT_V3`, tool v2/context
  `phase-evidence-v5`, no-memory, output 25,000, model/tool call `null`, wall 1,800초를 유지하고 per-run
  total-token ceiling만 1,600,000에서 2,000,000으로 바꾼다. 새 suite identity, purpose, schedule과 cost
  fields는 별도이며 “budget-only”는 per-run agent/model/runtime knob 비교에만 적용한다. Worst-rate reserve는
  `(2,000,000 + 25,000) * $4.50/M = $9.1125`, source cap은 `$10`이다. 이는 예상 invoice나 free-tier
  charge가 아니다. Readiness는 1/1 terminal·qualified·official evaluator, exact disabled-call guard와
  infrastructure/qualification/diagnostic/budget/terminal-loop confound 0만 요구하고 task success, hidden
  acceptance, SCRR는 요구하지 않는다. D-087/D-088와 D-083 budget freeze는 byte-immutable이고 D-087은
  hard-consumed다. Source artifact는
  `reports/live-pilot/artifacts/d089-anyio-budget-only-readiness-probe-source-gate.json`이다. Clean source
  commit에서 fresh no-call preflight가 만든 exact candidate hash와 최대 `$10`의 별도 사용자 승인 전에는
  provider를 호출하지 않는다. Source 단계의 provider call/model cost는 0/$0이며 no-memory baseline,
  comparison denominator, memory review/admission/index와 core는 계속 닫혀 있다. Final offline verification은
  focused 228/228과 repository-wide 1,529 collected 중 1,522 passed/7 skipped이고 source artifact SHA는
  `sha256:19eca850799e9549eef1d8b383d0c3461aa2b9a2e5471d67fe599cb373ea4555`다.
- Evaluator, constrained offline agent, state/recovery, memory, experiment/report와 viewer의
  implementation baseline이 존재한다.
- Historical D-088 milestone은 `D-087 measured result sealed; 12/12 terminal and qualified but 11/12 official evaluator,
  readiness false, no baseline or memory authority`다. Exact D-087 experiment
  `dev-no-memory-condition-neutral-accrued-cap-20260804-r1`은 clean source commit
  `7eee5fa1837d30e6177c46119885035f2b1d976f`와 승인 execution hash
  `sha256:0dd8ca1d0632398fed25ca28fbce89b97b0bf2137be163ed19a09fbf2d7f470d`로 정확히 한 번
  실행됐다. 12/12 row가 terminal·trace-qualified·cost-settled에 도달했고 infrastructure,
  qualification, diagnostic, not-started와 terminal-loop confound는 0이다. 그러나 AnyIO repetition 2
  `run_4613c65b2a254349`가 1,578,208 token 사용 후 남은 21,792 token으로 exact next input 14,080과
  full output allowance 25,000을 함께 보장하지 못해 provider call 전에 차단됐다. 따라서 official evaluator는
  11/12이고 original `condition-neutral-no-memory-campaign-readiness-gate-v1`은 false다. 이 한 run은
  qualified 28/28이며 다른 11 run은 evaluator와 qualification 29/29에 도달했다. Outcome은 1 resolved
  (PDM repetition 2), 10 hidden task failure, 1 agent budget failure다. Evaluated 11 run은 모두
  regression/scope/safety를 통과했다. Task success는 readiness predicate가 아니며 관찰된 1/12는
  diagnostic일 뿐 성능 추정치가 아니다. 총 usage는 4,844,335 input + 385,595 output = 5,229,930 token,
  340 model/547 tool call, input pre-count 341회와 3,356,560ms다. 340/340 provider response는 completed,
  exact token telemetry 일치, truncation disabled, `store=false`, previous-response dependency 0이다.
  공식 고정 rate 재계산 비용은 `$5.36842875`이고 campaign cap `$25`, maximum committed
  `$12.31149825`, reserve/settle 12/12, held reserve 0, reserve-unavailable 0이므로 campaign spend cap은
  binding이 아니다. Result SHA는
  `sha256:f3380aa466d5a2025562bb299e0bfc341135e5b2e77a634c80a87d796f1cbe40`, journal SHA는
  `sha256:14c6248d83738883486233a2f2516f3b975ef861ae10ba2f78d6d14d4b3f6fcd`, final event SHA는
  `sha256:253f543528cb472b282dd29fbde9b21a7cdd5eca34f5be9882ab7cdea29f4358`다. Portable seal은
  `reports/live-pilot/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json`
  (`sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269`)이다. D-087 ID는
  local raw evidence 유무와 무관하게 hard-consumed이고 재실행하지 않는다. D-088 seal 자체의 provider
  call/model cost는 0/$0이다. Final verification은 focused 74/74, repository-wide 1,478 collected 중
  1,471 passed/7 environment-dependent skipped이며 Ruff, compileall, JSON parse와 `git diff --check`를
  통과했다. Readiness가 실패했으므로 no-memory baseline, comparison denominator,
  memory review/admission/index, core와 `analysis_ready`는 계속 닫혀 있다. 다음 후보는 model/prompt/tool/context나
  hidden outcome을 조정하지 않는 별도 budget-only condition-neutral successor decision이며 새 ID, clean source,
  no-call preflight, execution hash와 사용자 비용 승인이 필요하다.
- Historical D-087 source milestone은 `exact 12-run no-memory campaign-local list-price-accrual cap source/offline gate
  complete; $25 hard cap and full-next-run reservation bound; no clean preflight, approval, provider execution,
  baseline, memory admission/index, or core authority`다. 새 exact source는
  `experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml`이며 historical
  `dev-no-memory-v5-20260730-r1`/`$20` template은 byte-immutable `superseded-unexecuted`로 보존한다.
  D-081 r3의 public process cost만으로 12-run mean projection `$5.38278975`, max-run envelope
  `$14.36724`, envelope + full next-run reserve `$21.67974`를 계산해 `$5` 단위로 올린 campaign-local
  hard cap `$25`를 선택했다. Per-run token ceiling은 D-083/D-084의 1,600,000과 worst-rate reserve
  `$7.3125`를 유지하며 12-run theoretical upper bound `$87.75`도 그대로 공개한다. 다음 row는
  `accrued list-price cost + $7.3125 <= $25`일 때만 시작하고 equality는 허용한다. Reservation은
  nano-USD로 runner/provider boundary 전에 append-only journal에 fsync하고 terminal usage의 token count로
  settle한다. 각 row는 exact plan/journal/run/policy에 묶인 one-use capability를 받아 SQLite에서
  `BEGIN IMMEDIATE`로 먼저 소비된 뒤에만 provider 경계를 넘는다. 다음 row 전에는 prior terminal의
  qualification/source/result hash를 durable storage에서 다시 읽고 fixed nano-USD rate로 재계산한다.
  Preserved SQLite anchor 아래 marker 삭제, journal reset, alternate runner root와 rehashed lower settlement는
  모두 거부한다. Reserve가 부족하면 current/remaining row를 `not_started`로 남기며 completion gate는 false다.
  Exact D-087 cost-policy hash는 suite/execution plan/hash, `RunManifest`, start paid boundary와
  post-run `campaign_spend_cap_contract`에 결속된다. Campaign live resume은 plan을 재구성하기 전에
  experiment ID 수준에서 fail closed하며 request-level billing ledger가 생길 때까지 열지 않는다. Source artifact는
  `reports/live-pilot/artifacts/d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json`이고 SHA는
  `sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe`다. Final offline verification은
  focused 68/68, repository-wide 1,472 collected 중 1,465 passed/7 skipped이며 provider call/cost는 0/$0다.
  이 source는 12/12 completion을 보장하지 않고 invoice/free-tier/project-wide cap도 주장하지 않는다.
  외부/request-level billing ledger는 아직 없으므로 전체 local DB와 journal을 함께 rollback하는 공격까지
  막는다고 주장하지 않으며 exact D-087 live resume을 닫아 둔다.
  Clean no-call preflight와 새 candidate hash, 최대 `$25`의 별도 사용자 승인 전에는 provider를 호출하지
  않으며 no-memory baseline, comparison denominator, memory review/index와 core는 계속 닫혀 있다.
- Historical D-086 milestone은 `D-085 measured-result and append-only budget-pressure correction sealed; no baseline or
  campaign authority`다. Exact approved execution hash
  `sha256:7163f6c44aa5b7790d35546be37781248d6575eac60986b2610f2e21c35348a0`는 clean D-085 source commit
  `629b9fdd9f69d1522cf565a06ae9679abe3f60a7`에서 정확히 한 번 소비됐다. Babel run
  `run_c355405d826641b9`는 terminal·trace-qualified·official evaluator와 original
  `condition-neutral-comparison-pilot-readiness-gate-v1`을 통과했고 hidden/regression/scope/safety도 모두
  pass했다. 사용량은 69,701 input + 3,500 output = 73,201 token, 8 model/9 tool call, 50,769ms이며 공식
  고정 rate 계산 비용은 `$0.06802575`다. 이는 invoice/free-tier charge 주장이 아니다. Original result SHA는
  `sha256:e0c3c4c67adc8c157a5030c9a93e3fd106d6b7a12f596253ddf10582fe74b80a`, journal file SHA는
  `sha256:4c114059fad069526d95786c392b7ea36724443b7231b4426bb097ee0c2199c8`, final event SHA는
  `sha256:93853c6367459bcae004789a9a2710c6be518078b21041ece0b160d9843e5a8b`, qualification SHA는
  `sha256:11bda7b2f31bae453f21c4718fdcb4563a74e173e621fd8035f1ab8aa64f1293`다. Original run의
  `budget_pressure`만 exact D-085 purpose를 budget diagnostic selector가 빠뜨려 `budget-pressure-error-v1`을
  기록했다. Original result/gate는 immutable하고, narrow exact-selector correction은 token headroom
  1,526,799, wall headroom 1,749,231ms와 binding `none`을 append-only로 기록한다. Portable seal은
  `reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json`
  (`sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464`), correction artifact는
  `reports/live-pilot/artifacts/d086-condition-neutral-comparison-pilot-budget-pressure-correction.json`
  (`sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4`)이다. D-085 ID는 local result/journal 유무와 무관하게 hard-consumed다.
  Final verification은 `focused 64/64; repository-wide 1,416 collected, 1,409 passed/7 skipped; Ruff/compileall/JSON/git-diff checks passed; seal provider calls/model cost 0/$0`이다. 이 single-row result는 workflow readiness와 한 task
  success만 증명하며 no-memory baseline, comparison denominator, memory admission/index, core와
  `analysis_ready`는 열지 않는다. D-086 시점의 다음 후보는 12-run cap을 `$20 → $88`로 바꾸는 별도
  decision이었지만, 이 forward choice는 현재 D-087의 `$25` accrued-spend source가 supersede했다.
- Historical D-085 source milestone은 `exact condition-neutral comparison pilot source/offline gate complete; no clean preflight,
  approval or provider execution`이다. Exact pilot ID는
  `dev-validation-condition-neutral-v2v5-pilot-20260803-r1`이고 frozen Babel development-validation task를
  `no_memory`로 한 번 실행하는 계약만 준비한다. D-083/D-084의 mini medium/standard/default, retry 0,
  `SYSTEM_PROMPT_V3`, tool v2/context `phase-evidence-v5`, output 25,000, memory allowance 2,000과
  `null/null/1,600,000/1,800` tuple을 그대로 사용한다. Worst-rate reserve `$7.3125`, source cap `$8`이며
  task success/SCRR가 아닌 terminal·qualified·official evaluator, exact disabled-call-guard와
  infrastructure/qualification/diagnostic/budget/terminal-loop confound 0만 readiness predicate다.
  Source artifact는
  `reports/live-pilot/artifacts/d085-condition-neutral-comparison-pilot-source-gate.json`이다. Clean no-call
  preflight가 만든 candidate hash와 최대 `$8`의 별도 사용자 승인이 있기 전 provider를 호출하지 않는다.
  Pilot 결과 전에는 12-run cap을 `$20`에서 `$88`로 바꾸거나 memory review/index/core를 열지 않는다.
  Pilot과 future campaign은 별도 clean commit을 사용한다. Exact `dev-no-memory-v5-20260730-r1` consumer는
  raw commit equality 대신 D-083/D-084 semantic tuple과 네 qualification check를 검증하고
  persisted qualification을 durable state에서 read-only 재계산한 결과와 exact 비교하며
  `condition-neutral-comparison-pilot-admission-v1` canonical hash를 future campaign plan/hash와
  start/resume/post-run qualification에 결속한다. Task success는 admission 조건이 아니다. 이 offline
  consumer 자체는 cap 변경, 새 campaign hash/승인 또는 paid authority를 만들지 않는다.
  Final offline verification은 focused 153/153, repository-wide 1,385 passed/7 skipped이고 source artifact SHA는
  `sha256:8b60cb2e62a6259db29527a600712e95b36390a1c07da9fb66e6f1d7d16f51d2`이다.
- D-084 milestone은 `condition-neutral comparison runtime gate implemented offline; all live, baseline,
  memory-admission and core authority closed`다. D-083 exact tuple을
  `condition-neutral-comparison-runtime-contract-v1`, `RunManifest`, content-addressed `RunStarted`, start/resume,
  `condition-neutral-comparison-runtime-evidence-v1`, budget diagnostic과 no-memory qualification에 결속했다.
  Core 네 condition은 structural support만 있고
  `CORE_MEMORY_RUNTIME_BINDING_PENDING`으로 계속 닫혀 있다. D-084 artifact SHA는
  `sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701`이고 provider call/cost는 0/$0이다.
- Historical D-083 milestone은 `condition-neutral comparison-budget policy frozen offline; runtime support and
  all live authority remain closed`다. D-083은 exact D-081 r3 evidence만 사용해 model/tool call limit
  `null`/`null`, total token 1,600,000, wall 1,800초, output 25,000과 SDK transport retry 0을 future
  comparison의 동일 per-run resource policy로 동결한다. Public observed-prefix minimum은 D-081 r3
  pyfakefs의 1,303,223 token이며 `1,303,223 * 1.2 = 1,563,867.6`을 100,000 단위로 올림했다.
  이는 completion guarantee가 아니고 D-080 historical minimum 1,815,619는 이 exact-source derivation
  범위 밖이다. Worst-rate reserve는 `$7.3125`/run, `$87.75`/12 run, `$131.625`/18 run,
  `$702`/96 run이다. 기존 `$20` 12-run cap과 `$150` project cap은 변경되지 않아 source template은
  계속 fail closed다. `comparison_budget_policy_frozen=true`만 새로 기록하며 live execution,
  comparison denominator, no-memory baseline, memory admission과 core는 모두 false/closed다.
  Execution-plan runtime evidence, RunManifest와 qualification support는 다음 offline gate까지 pending이다.
  Append-only artifact path는
  `reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json`, SHA는
  `sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88`다. Hidden outcome은
  산식에 사용하지 않았고 D-081/D-082는 immutable calibration-only evidence로 남는다. D-083 구현의
  provider call과 model cost는 0/$0이다. Final verification은 repository-wide 1,238 collected 중
  1,231 passed/7 environment-dependent skipped, focused artifact 9/9와 experiment contract 245/245다.
  Historical D-082 milestone은 `D-081 condition-neutral four-row workflow readiness observed and
  measured result sealed; calibration-only, no baseline freeze`다. Exact experiment
  `generic-baseline-readiness-v2v5-20260803-r3`는 clean source commit
  `b4c79242bb0a94eed50530116205323e78c7d21a`와 승인 execution hash
  `sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`로 정확히 한 번
  실행됐다. D-075/D-077과 같은 Babel, Moto, pyfakefs, HF Hub task, `no_memory` 1회,
  `gpt-5.4-mini-2026-03-17` medium/standard/default, `SYSTEM_PROMPT_V3`, tool v2/context
  `phase-evidence-v5`, SDK transport retry 0, output 25,000을 유지했다. Model/tool call limit은
  `null`이고 total token 2,400,000과 wall 1,800초 및 exact-request, cost, loop, constrained-tool,
  Docker/network/evaluator guard는 계속 강제됐다. 네 row 모두 terminal·trace-qualified·official
  evaluator completion에 도달해 `generic-baseline-readiness-gate-v2`가 통과했고 infrastructure,
  qualification, diagnostic, budget-terminal과 terminal-loop confound는 모두 0이다. Babel만 SCRR이며
  HF Hub, Moto, pyfakefs는 hidden acceptance 실패다. 네 row 모두 regression/scope/safety는 통과했다.
  총 사용량은 111 model/175 tool call, 1,929,316 token이고 공식 고정 rate 계산 비용은
  `$1.79426325`다. 이는 billed invoice나 free-tier charge 주장이 아니다. 111/111 request는 completed,
  exact input telemetry 일치, truncation disabled와 `store=false`를 기록했다. Natural rejected-patch
  recovery는 3/3 verified이고 loop observation은 50회이며 그중 pyfakefs가 39회지만 terminal loop
  failure는 0이다. Raw result hash는
  `sha256:f8a2cd25916290ae02e46b484519cc01dedbe50097326085524a88bb9b324f83`, journal file hash는
  `sha256:52626ba6d7e61bc293ce327f4bf190e3b4118b20a2efe4d9de09d8186ce6afdd`, final event hash는
  `sha256:f5537479c3c1e8c150f9cbfec5238d99c882eff537006773af8d9ddf9f78c254`다. Portable report는
  `reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json`이고 content hash는
  `sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2`이다. D-082 seal 자체의
  provider call과 model cost는 0/$0이다.
  이 결과는 exact workflow readiness calibration일 뿐 comparison denominator, no-memory baseline,
  memory admission과 core를 열거나 comparison budget을 동결하지 않는다. Historical
  D-075/D-077/D-079/D-080 suite, hash, run, result, gate와 correction은 immutable하다. D-082 final
  documentation-seal verification은 repository-wide 1,214 collected 중 1,207 passed/7
  environment-dependent skipped와 focused D-082 8/8을 통과했다.
  Historical D-080 milestone은 `D-079 workflow completion observed; original gate projection defect sealed
  with an append-only derived correction; no baseline freeze`다. 승인 execution hash
  `sha256:70bc29196115cc6b201a30587d6974d3a05607345d447cb3a9144b0920c09791`로 D-079를 정확히
  한 번 실행한 `run_606349c2c56342d4`는 84 model/119 tool call, 1,790,707 token, 856,559ms와
  계산 비용 `$1.81747785`를 사용해 terminal·qualified·official evaluator에 도달했다. Token
  1,209,293과 wall 6,343,441ms가 남았고 budget binding은 없다. Regression/scope/safety는 통과했지만
  hidden acceptance가 실패해 `task_failure`/SCRR false다. Original gate false는 runtime/trace violation이
  아니라 terminal qualification summary producer가 raw checks를 생략하고 consumer가 그 collection을
  찾은 `qualification-summary-projection-mismatch`다. Original experiment result와 gate는 immutable하다.
  Append-only correction
  `gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`와 semantic body hash
  `sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`는 source identity,
  correction harness commit `7e40e27446bcf011f700c219a96983e5670422f4`, projection contract, exact
  cause, original gate, exact corrected gate와 claims boundary를 함께 결속한다. Corrected gate는 original과
  같은 `workflow-completion-probe-gate-v1` schema의 별도 append-only payload이며 original gate를 대체하지
  않는다. 새 terminal summary의 `qualification-gate-check-projection-v1`은 outer key exact-one과 inner
  `check_count/check_id/passed/schema_version` exact key set을 요구해 missing, duplicate, extra, wrong ID/type와
  malformed projection을 fail closed한다. `check_count`는 strict integer `1`만 허용하고 bool/float/string을
  거부한다. D-080 final verification은 focused 331 passed, repository-wide 1,162 collected 중 1,155 passed/7
  environment-dependent skipped, Ruff, Python compileall, JSON parse와 `git diff --check` pass다. Provider call은
  0이고 추가 model cost는 `$0`이다. D-079/D-080은 calibration-only이고 comparison denominator,
  no-memory baseline, memory admission과 core를 열지 않으며 자동 재실행·hidden-driven tuning을 승인하지
  않는다. Portable seal은 `reports/live-pilot/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.json`,
  correction manifest는 `reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json`에 있다.
  Historical D-079 source milestone은 `bounded pyfakefs workflow-completion probe source/offline contract`
  였다. Exact experiment ID는
  `pyfakefs-workflow-completion-probe-v2v5-20260803-r1`, purpose는
  `workflow-completion-probe`다. Frozen pyfakefs development task를 `no_memory`로 정확히 한 번 사용하고
  `gpt-5.4-mini-2026-03-17` medium/standard/default, `SYSTEM_PROMPT_V3`, tool v2/context
  `phase-evidence-v5`, SDK transport retry 0, output 25,000을 고정한다. Budget은 model/tool call을
  `null`로 두어 `model-tool-observability-only-v1` 아래 admission guard가 아니라 관찰값으로만 기록하고,
  total token 3,000,000과 wall 7,200초를 강제한다. Exact-request token, cost, loop, constrained-tool,
  Docker/network/evaluator guard도 유지한다. Runtime contract는
  `workflow-completion-runtime-contract-v1`, gate는 `workflow-completion-probe-gate-v1`이다.
  Conservative authorization reserve는 `$13.6125`, cap은 `$14`이며 당시 source/offline evidence는 provider
  call, execution hash, 사용자 비용 승인, run/result, measured usage/cost 또는 gate outcome을 만들지
  않았다. Clean commit의 no-call preflight와 exact hash·최대 `$14`에 대한 별도 명시적 승인 전에는
  live 실행하지 않았고, 이후 exact invocation과 결과는 위 D-080 seal에만 속한다. D-079는
  calibration-only이며 comparison denominator, no-memory baseline, memory admission과 core를 열지 않는다.
  Source/offline gate는 repository-wide 1,182 collected, 1,175 passed/7 environment-dependent skipped,
  Ruff, compileall과 `git diff --check`를 통과했다. 2026-08-02T16:35:25Z 공식 standard pricing도
  `$0.75/M` input, `$0.075/M` cached input, `$4.50/M` output으로 재확인했으며 provider call/model cost는 0이다.
  Historical D-078 milestone은 `failed D-077 budget-only readiness result sealed; no automatic rerun or
  hidden-driven tuning authorized`다. Exact predecessor
  `generic-baseline-readiness-v2v5-20260802-r2`는 D-075와 같은 Babel, Moto, pyfakefs, HF Hub
  task와 순서, `no_memory`, `gpt-5.4-mini-2026-03-17` medium/standard/default,
  `SYSTEM_PROMPT_V3`, tool v2/context `phase-evidence-v5`, SDK transport retry 0, output 25,000,
  tool 100과 wall 1,800초를 유지하고 budget만 model call 40→50과 total token
  850,000→1,200,000으로 바꾼다. 2026-08-02T13:11:37Z에 공식 rate를 다시 확인한 conservative
  reserve는 run당 `$5.5125`, four-row `$22.05`, suite cap `$23`이다. 승인 execution hash
  `sha256:de73e622fcaa4cec85191cceb01efdb0d27cc6a5a6b8f05c7cd4844df50763f5`는 정확히 한 번
  소비됐다. 4/4 terminal·qualified와 error 0에도 official evaluator는 3/4만 도달했다. HF Hub와
  Babel은 hidden acceptance 실패, Moto는 SCRR이고 pyfakefs `run_415695539ad24658`는 50 model
  call에서 evaluator 전에 종료됐다. Pyfakefs에는 387,160 token, 16 tool call, 1,100,745ms가
  남아 있어 binding dimension은 model call뿐이다. 따라서 original gate는 false다. 총 사용량은
  1,998,084 token, 125 model/219 tool call, 계산 비용 `$2.1782655`다. D-077은
  calibration-only이고 1/4 SCRR는 diagnostic일 뿐 comparison denominator, memory admission과
  core를 열지 않는다. R2 ID/hash/run/result는 immutable하며 재실행하지 않는다. D-078은 다음
  budget 증가나 prompt/tool/context tuning을 승인하지 않는다.
  D-078 seal verification은 focused 11 passed와 repository-wide 1,099 collected,
  1,092 passed/7 environment-dependent skipped를 기록했고 Ruff, compileall, JSON parse와
  `git diff --check`를 통과했다. Provider call과 추가 model cost는 0이다.
  Historical D-077 source-stage focused readiness matrix와 repository-wide 1,095-test 회귀는 통과했고
  1,088 passed/7 environment-dependent skipped였으며 Ruff, compileall과 `git diff --check`도
  통과했다. 그 source-stage evidence만의 provider call과 model cost는 0이었다.
  Historical D-075 checked-in exact suite
  `generic-baseline-readiness-v2v5-20260802-r1`은 Babel, Moto, pyfakefs와 HF Hub 네 development
  task를 `no_memory`로 각 1회, `gpt-5.4-mini-2026-03-17` medium/standard/default,
  `SYSTEM_PROMPT_V3`, tool v2/context `phase-evidence-v5`, SDK transport retry 0,
  40 model/100 tool/850,000 token/1,800초와 output 25,000으로 고정한다. Gate는 4/4
  terminal·qualified·official evaluator completion과 infrastructure/qualification/diagnostic/budget
  confound 0을 요구하지만 task success나 SCRR는 요구하지 않는다. Suite는 calibration-only이고
  comparison denominator와 memory admission을 열지 않는다. 850k는 readiness 후보 ceiling이지
  frozen comparison budget이 아니다. Final tuple이나 harness commit이 달라지면 새 readiness panel이
  필요하다. Source config와 no-call preflight는 live capability가 아니며
  clean execution hash와 최대 `$16` invocation에 대한 별도 사용자 승인이 필요했다. 승인 hash
  `sha256:1709a9e9911f980aafe28cdd9fe9ed486367c134e2dc9e465c88e01f9462bd66`는 정확히 한 번
  소비됐다. 네 row는 모두 terminal·qualified이고 error 0이었지만 Babel/Moto만 evaluator와 SCRR에
  도달했다. HF Hub는 809,867 token 뒤 exact-request total-token guard, pyfakefs는 40 model call 뒤
  call-budget guard에 걸려 evaluator 도달이 2/4였다. 따라서 original readiness gate는 false이고
  2/4 SCRR는 calibration-only diagnostic일 뿐 no-memory baseline이 아니다. 사용량은 1,708,824 token,
  95 model/142 tool call, 계산 비용 `$1.76403675`다. Experiment ID/hash/run/result는 immutable하며
  재실행하지 않는다. 당시 condition-neutral next candidate 50/100/1,200,000/1,800초는 이후 D-077로
  정확히 한 번 실행됐지만 completion하지 못했고 frozen comparison budget도 아니다. D-069~D-073의
  V10/V11 및 exact HF Hub sidecar lane은 계속 `retired diagnostic-only`이고 historical artifact와
  consumed-ID guard는 append-only로 보존한다. 당시 21/50/250,000/900 template은
  stale/unvalidated였고 D-083이 future source template의 budget policy만 supersede했다. Hidden failure는
  baseline freeze 전 task-specific tuning trigger가 아니고,
  live hard restart는 별도 reliability exercise다.
  D-060은 immutable diagnostic evidence다. HF Hub만 total-token budget에 bind했고 PDM과
  pyfakefs는 budget과 무관한 hidden task failure였다. 후속 corrective lane은
  `tool_schema_version=v4`/`phase-evidence-v7`, public issue checklist, persistent rejected-patch
  source snapshot, apply same-turn barrier/recovery와 six-replay evidence saturation을 사용한다.
  `corrective-runtime-contract-v1`은 prompt/tool schema hash, v4/v7 pair와 harness commit을
  execution hash·preflight·manifest·runner start/resume·qualification에 결속한다. Qualification은
  unique runner `RunStarted`의 full CAS descriptor와 bytes를 검증하고, 그 immutable 시각을
  기준으로 공식 가격 확인이 72시간 이내인지 재계산한다.
  Checked-in `dev-no-memory-corrective-pilot-20260731-r1`은 3 task 각 1회 no-memory,
  40 model/100 tool/900,000 token/1,800초, output 25,000, reserve `$12.4875`, cap `$13`인
  tuning-only suite다. 승인 execution hash
  `sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`로 정확히 한 번
  소비됐고 첫 HF Hub row `run_0ccfc8fd359a4785`만 terminal에 도달했다. 이 run은 33개
  completed model call과 875,908 token, 계산 비용 `$0.8408853`을 기록한 뒤 exact-request
  budget에서 차단됐다. 일곱 `apply_patch` candidate는 모두 preview에서 거부되어
  `PatchPrepared`/`PatchApplied`와 evaluator 도달은 0이다. Original qualification failure로
  campaign이 fail-closed해 PDM과 pyfakefs row는 시작되지 않았고 original gate는 false다.
  Result, journal과 original qualification artifact는 immutable하다. 후속 독립 분석은
  qualifier의 v5-vs-v6/v7 reserve-version drift를 분리했고 append-only correction
  `qcor_8b6ff812...4870b6`는 corrected trace qualification을 통과했다. 이 correction은
  original campaign gate나 task outcome을 바꾸지 않는다. Trace에는
  saturation이 context의 allowed action에 반영되지 않아 차단된 read/search 30회와 patch
  preview failure 7회가 관찰됐다. 이 결과는 SCRR/no-memory baseline, memory admission 또는
  core evidence가 아니며 D-062 suite/hash는 재실행하지 않는다.
  Rejected-patch retry context와 execution-hash-bound `experiment-diagnostic-v1` consumer는
  offline evidence를 통과했다. 승인된 mini D-037 r3는 provider에서 실행됐지만 rejected mutation이
  생기기 전에 per-call output allowance를 소진해 실제 retry는 아직 검증하지 못했다.
  Terminal r3 evidence와 원인은 보존됐다. r4는 official reasoning guidance에 맞춘
  25,000 per-call / 120,000 total token pair를 hash-bound profile v2로 분리해 full
  offline 검증 뒤 provider에서 정확히 한 번 실행했다. 모든 13개 generation은 completed였지만
  `REVIEW` turn 직전 남은 28,563 token으로 exact input 8,583 + response allowance 25,000을
  보장할 수 없어 local guard가 provider call 전에 종료했다. 제출·evaluator·retry episode는
  0개이고 D-037은 여전히 검증 또는 반증되지 않았다. 이 r4를 immutable evidence로 보존한다.
  D-041은 새 r5 profile v3에 strict exact-input + full 25,000 response reservation을 그대로
  유지하고 diagnostic-only total token budget을 200,000으로 고정한다. 이는 r4의 91,437-token
  prefix에 당시 최대 exact input 10,031과 25,000 allowance의 tail reservation 세 개를 더한
  196,530을 올림한 값이다. 새 `model-generation-block-v1` exact-request payload가 결속된
  generic terminal budget block은 retry 유무와 무관하게 valid trace evidence가 될 수 있지만 D-037 episode로
  세거나 gate를 열지는 않는다. Unversioned r4 qualification 21/22는 그대로 유지한다.
  Synthetic rejection, runtime reservation 의미 변경과 automatic retry는 도입하지 않는다.
  R5가 evaluator에 도달해도 rejection이 없으면 inconclusive로 보존하고 자동 재실행하지 않는다.
  이 계약은 2026-07-30 targeted 191-test, full 504-pass/2-skip와 Ruff evidence로 닫혔다.
  별도 승인된 r5 `run_0ad8676d42614fbf`는 18/18 exact input telemetry와 completed
  response, official hidden/regression/scope/safety pass, `trace-qualification-v2` 23/23을
  남겼다. 그러나 rejected candidate와 retry episode가 모두 0이어서 D-037 diagnostic은
  `retry_episode_not_observed`로 terminal inconclusive다. 계약대로 자동 재실행하지 않는다.
  D-043은 별도 r6/profile v4에서 첫 preflight-valid `PatchPrepared` candidate를 실제
  mutation 전에 정확히 한 번 거절하고 next-request exact rehydration을 검증하는 controlled
  diagnostic을 구현했다. Offline gateway, crash recovery, agent-loop와 qualification evidence
  및 529 passed/2 skipped broad regression 뒤, 승인된 r6 `run_73f5aaf7328a4ea5`가 provider에서
  정확히 한 번 실행됐다. Controlled rejection 1회와 verified retry 1회, rejected action
  `PatchApplied` 0회, evaluator 도달, official hidden/regression/scope/safety pass와
  `trace-qualification-v2` 23/23을 기록했다. 사용량은 138,262 input + 13,800 output token,
  계산상 `$0.1657965`다. 이는 D-037 harness branch의 live validation이며 자연 model-error
  recovery rate나 memory 효과가 아니다. 이 r6와 승인 hash는 immutable하게 보존하고 재실행하지
  않는다. D-045는 당시 이후의 pilot, memory-development와 core 비교 모델을
  `gpt-5.4-mini-2026-03-17`, medium/standard/default, 25,000 per-call output과 200,000
  run-total budget으로 통일했다. 이 historical budget은 아래 D-052가 future suite에
  대해서만 supersede한다. 승인된 fault-free primary r1 `run_6993722014bf4e3b`는
  20/20 exact input telemetry와 completed response, applied patch, visible check pass,
  final diff와 `REVIEW`를 남겼지만 model-call 20회를 모두 사용해 `finish_task` 전
  `model_call_budget_exhausted`로 끝났다. Evaluator는 실행되지 않았고 qualification은
  call-budget terminal block 계약 때문에 21/22다. Exact final patch는 별도 no-model
  postmortem evaluator에서 official hidden/regression/scope/safety를 모두 통과했지만 원 run의
  outcome을 바꾸지 않는다. R1 suite/hash/run은 재실행하지 않는다. D-047은 exact-token
  `model-generation-block-v1`을 유지하면서 next-generation admission의 model/tool/wall
  counter exhaustion을 strict `model-generation-block-v2`로 분리했다. Qualifier는 durable
  counter 재계산, `model → tool → wall` 우선순위, request CAS, actor와 terminal 결속,
  tamper와 unversioned generic 거부를 검증한다. 앞으로의 primary, memory-development와
  core는 모든 조건에 같은 총 21 model-call 상한을 사용하며 21번째 call은 `finish_task`
  전용 reserve가 아니다. Historical r1은 20-call로 그대로 남는다. Corrective r2
  `run_afd5080a77a34995`는 별도 승인 아래 실행되어 official evaluator와
  `trace-qualification-v2` 23/23을 통과했다. 이어 실행한 immutable 12-run
  `dev-no-memory-20260728`은 12/12 trace qualification을 통과했지만 모두 `REPRODUCE`에서
  call budget을 소진해 evaluator 도달 0/12였다. 이 결과는 memory baseline이 아니라
  stateless investigation-continuity failure evidence다.
- Docker 공식 evaluator smoke와 calibration 5/5, SWE-style research admission 20/20을 완료했다.
  Memory-development lane은 6/6, development-validation lane은 2/2, core-same-repo lane은
  6/6, core-cross-repo lane은 6/6이다. 세 stress sentinel과 30-run fault schedule을
  machine audit한 뒤 dataset manifest를 동결했다. 앞선 두 Live OpenAI pilot은 terminal
  agent failure로 보존돼 있다. 세 번째 pilot `run_3cb86f8d70094a11`은 당시 v1 계약에서
  official hidden/regression/scope/safety verdict와 trace qualification을 통과한 historical
  accepted pilot이다. 이후 tool/context/submission lifecycle이 v2로 바뀌었으므로 이 run은
  현재 campaign gate를 열지 않는다. 별도 mini model-candidate r1
  `run_d4fea5e7198b4abc`는 evaluator 전에 실패했다. 새 v2 mini r2
  `run_4a9737ec91964dca`는 telemetry, submission lifecycle, evaluator receipt와
  `trace-qualification-v2`를 통과했지만 hidden acceptance가 실패한 immutable task
  failure다. 이 trace는 stateless retry context가 직전 rejected patch의 hash와 오류만
  보존하고 patch body는 복원하지 않는 gap도 드러냈다. 새 `phase-evidence-v3`는 exact
  candidate/reason next-request rehydration, CAS/request qualification과 structured
  no-generation budget event를 offline test로 검증했다. D-037 r3
  `run_e90f7c52aa134182`는 input pre-count 8/8 일치와 leakage pass를 보존했지만, event 55의
  응답이 `max_output_tokens=4096`에서 incomplete가 되어 evaluator 전에 terminal
  agent/qualification/diagnostic failure로 끝났다. Mutation과 rejected retry episode는
  0개이므로 이 run은 D-037을 검증하거나 반증하지 않으며 재실행하지 않는다. R4
  `run_826c1c7fb3d242c2`는 patch 1회와 visible check pass, final diff 뒤 `REVIEW`까지
  진행했고 13/13 exact token telemetry와 completed response를 남겼다. 그러나 14번째
  generation은 `MODEL_GENERATION_BUDGET_EXCEEDED`로 시작 전에 차단됐고 evaluator와
  rejected retry에는 도달하지 못했다. Qualification 21/22의 유일한 실패는 token mismatch가
  아니라 retry candidate가 없는 generic budget-block을 현재 v3 qualifier가 terminal-valid로
  보지 않는 계약 경계다. 이 run도 재실행하지 않는다.
  후속 r5는 25,000 per-call / 200,000 total의 profile v3와
  `model-generation-block-v1`만 새로 허용했다. 승인 hash
  `sha256:97249f05deda8e59118fdac0dd6f62f44c18b086ecb16bface2cc4d0f41a3a12`로
  provider에서 정확히 한 번 실행한 `run_0ad8676d42614fbf`는 official task success와
  qualified trace를 남겼지만 rejection이 없어 D-037에는 inconclusive다. 사용량은
  121,366 input + 9,913 output token, 계산상 `$0.135633`이며 재실행하지 않는다.
  실제 subprocess hard-kill 뒤 stale `RUNNING` reclaim은 offline test만 통과했다.
  새 `phase-evidence-v4`는 active mutation epoch의 search/read CAS를 매 turn
  `investigation-ledger-v1`로 재구성하고 nominal corrective tail 전에는 exact search와
  fully-covered read를 semantic replay한다. Tail에서는 semantic-replay 대상까지 모든
  valid read/search admission을 차단한다.
  기존 v1-v3 trace는 소급 재해석하지 않는다. 승인된 v4 pilot
  `run_d7207fbb06184dd3`은 official hidden/regression/scope/safety와 trace qualification
  25/25를 통과했다. 10/10 exact input telemetry, 자연 rejected-patch retry 1/1,
  81,719 input + 5,952 output token과 계산상 `$0.08807325`를 기록했다. 이 run은 v4
  ledger/context 재구성을 live로 검증했지만 semantic replay와 tail admission block은
  각각 0회라 해당 branch의 근거는 offline test다. 이 pilot에 결속된
  `dev-no-memory-v4-20260730-r1`은 exact pilot commit의 clean detached worktree에서
  execution hash
  `sha256:9befd0bf8b2eb7dbc25999786713581b4b6c95f2ad45df56e2f098a9252e5bac`로
  정확히 한 번 실행됐다. 12/12 terminal, infrastructure/qualification/diagnostic error
  0이지만 SCRR은 0/12다. 아홉 run은 exact next input과 full 25,000-token response
  allowance를 남은 total budget에 함께 예약하지 못해 evaluator 전에 agent failure가 됐고,
  세 run은 제출 뒤 regression/scope/safety를 통과했지만 hidden acceptance에 실패했다.
  144/144 executed request의 exact input count가 provider usage와 일치했고 semantic replay는
  26회였지만 tail admission block은 0회였다. 계산상 campaign 비용은 `$1.84756425`,
  전체 누적은 `$4.981546875`다. 이 campaign은 immutable diagnostic evidence이며 usable
  no-memory performance baseline이 아니고 재실행하지 않는다.
  D-052는 future non-replay runtime을 `phase-evidence-v5`로 올리고 모든 memory 조건의
  budget을 `21 model call / 50 tool call / 250,000 total token / 900초`, per-call output
  25,000으로 고정한다. Durable `ModelCalled` telemetry에서
  `requested_input_tokens`를 우선하고 그 값이 `None`일 때만 actual `input_tokens`로
  fallback한다. 관찰값이 invalid하면 fail closed한다. 다음 input은 관찰된 input의 최댓값에
  양의 consecutive growth 최댓값을 더해 예측하며, generation 전에는 5 turn, generation
  후에는 4 turn을 곱한다.
  `reserved_tokens = max_output_tokens + projected_next_input × projected_turns`이고
  `remaining_tokens <= reserved_tokens`이면 read/search만
  `token_tail_reserved`로 `ToolCalled`와 dispatch 전에 차단한다. Apply/check/diff/finish는
  계속 사용할 수 있다. 이 nominal cutoff는 완료 보장이 아니며 strict exact-request +
  full 25,000 response guard는 그대로다. 새 evidence schema는
  `investigation-policy-v2`, `investigation-ledger-v2`,
  `investigation-tail-policy-v2`, `context-build-evidence-v5`,
  `tool-admission-blocked-v2`, `trace-source-evidence-v5`이고 trace qualification은
  계속 `trace-qualification-v2`다. Historical 21/200,000 suite
  `dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`,
  `dev-validation-gpt54mini-investigation-v4-20260730-r1`,
  `dev-no-memory-v4-20260730-r1`은 immutable하며 재해석하거나 재실행하지 않는다.
  D-053 maintainer-assisted structured review proposal은 검증됐지만 human admission과
  index build는 의도적으로 보류한다. D-054는 실행되지 않은 250k single pilot을
  `superseded-unexecuted`로 보존하고, Babel+Moto 각 1회 `no_memory` completion panel을
  `40 model / 100 tool / 600,000 token / 1,800초`, per-call output 25,000, suite cap
  `$6`로 고정했다. 승인 hash
  `sha256:444cd7f2d00b3925a1227d1e9fc0436c68ba9700005b8416572c5fd654de1f78`로
  provider에서 정확히 한 번 실행한 D-055 campaign은 Babel
  `run_685c492e34f84fef`와 Moto `run_0814be408332479e` 모두 official hidden,
  regression, scope, safety와 `trace-qualification-v2` 25/25를 통과했다.
  Completion과 20% panel-headroom gate도 2/2 통과했고 budget/infrastructure/
  qualification error는 0이다. 사용량은 각각 65,652 input + 3,304 output,
  106,597 input + 2,838 output token이며 총 계산 비용은 `$0.15682575`다.
  19/19 request의 exact input count가 provider usage와 일치했고 모두 completed,
  truncation disabled, `store=false`, previous-response dependency 0이었다.
  Result hash는
  `sha256:a540ff52f271cd22c58ca561e559d9608ac50b99889a523f8a9a3d80cf8822ba`다.
  이 experiment ID와 approval hash는 immutable하며 재실행하지 않는다. 이 두 task의
  성공은 runtime completion ceiling 검증이지 memory 효과나 12-task baseline이 아니다.
  D-056/D-057 opt-in `tool_schema_version=v3` / `phase-evidence-v6` self-validation은
  D-058에서 실제 Docker isolation E2E 3/3과 전체 704-test regression
  702 passed/2 Windows symlink-capability skipped를 통과했다. 현재 source로 다시 빌드한
  clean probe image ID는
  `sha256:268495717da1396e3413ce6695063c9516202b4e38cb8042f2f181420b64e9c1`이다.
  비용 없는 mock smoke `run_36f90bda91b94d42`는 official hidden/regression/scope/safety와
  same-diff review lifecycle을 통과했다. Historical v1 task라 probe call은 0이고 실제
  probe isolation은 Docker E2E evidence다. 이 gate closure는 live OpenAI 실행이나
  memory/core 성능 evidence가 아니며 v3/v6 OpenAI start/resume은 계속 fail closed한다.
  D-059는 동결 dataset 밖의 infrastructure-only `task-public-v2`
  `fixtures/task-packages/self-validation-csv-quoted-newline`을 추가하고, 비용 없는 mock
  `run_7e3c5af2ce8d498a`에서 registered `quoted-newline-case` probe를 실제 clean image로
  실행했다. Probe event 33은 `probe-ok`를 기록했고 같은 diff의 review가 그 event를
  인용한 뒤 제출·official hidden/regression/scope/safety까지 통과했다.
  `self_validation_lifecycle`은 통과했지만 mock/non-campaign run의 전체 qualification은
  의도대로 false다. 전체 회귀는 708 collected, 706 passed/2 Windows
  symlink-capability skipped이고 동결 dataset은 25 task/candidate 0으로 변하지 않았다.
  따라서 profile 선택부터 review/evaluator까지의 offline lifecycle만 닫혔으며 live
  provider, leak-safe campaign qualification 또는 성능 개선 evidence로 사용하지 않는다.
  D-060은 승인 hash
  `sha256:61a7208bd6ee1a45b08511407d0c8c0658976685245a11d422077efdf9bdef4f`로
  정확히 한 번 실행됐다. 3/3 terminal·qualified이고 infrastructure/qualification error는
  없었지만 SCRR은 0/3이다. HF Hub `run_d20c9757bdef4942`만 438,483/480,000 token 뒤
  exact-request budget에 막혔다. PDM `run_4352391174814d1d`와 pyfakefs
  `run_6b4f13316e714785`는 각각 153,702와 252,066 token에서 official evaluator에 도달한
  non-budget task failure다. `patchloop budget` derivation은 HF exact deficit 5,171과 v5
  same-prefix minimum 658,739를 재계산하며 원 artifact를 변경하지 않는다.
  D-062 corrective suite의 offline 계약 뒤 승인 hash
  `sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`가 정확히 한 번
  소비됐다. HF Hub `run_0ccfc8fd359a4785` 하나만 실행된 뒤 original qualification
  failure가 campaign을 fail-closed했고 나머지 두 row는 not-started다. 900,000-token ceiling은
  completion guarantee가 아니었고 run은 875,908 token에서 exact-request budget에 막혔다.
  Original campaign artifacts와 false gate는 immutable하며 D-062를 계속하거나 재실행하지
  않는다. D-063 `phase-evidence-v8` offline gate는 같은 durable prefix의 saturation과 tail을
  `phase-contract-v3.read_search_policy`에 합성하고, mock-only manifest,
  `corrective-runtime-contract-v2`, `context-build-evidence-v8`, `trace-source-evidence-v8`과
  independent `saturation_context_contract`를 구현했다. Six-replay 직후 `SystemExit`을 일으킨
  crash/resume E2E에서 첫 resumed context의 read/search 제거, successful patch 뒤 count 0
  reset과 qualifier pass를 확인했다. Representative v7 rendered/evidence golden과 D-062 source
  hash `sha256:53148b2b42e82ddcb6083b1b317df3c7f8598972ed61fac0f69c65c5acff4351`은
  유지됐다. 관련 regression은 377 passed/2 skipped, 전체는 822 collected,
  815 passed/7 environment-dependent skipped였고 Ruff와 `git diff --check`도 통과했다.
  D-063은 provider call, live suite, approval hash 또는 비용 evidence가 아니다.
  D-064는 새 `memory-development-no-memory-saturation-pilot` purpose와 exact HF Hub 한 task,
  no-memory 1회, v4/v8/runtime-v2, 40 model/100 tool/900,000 token/1,800초, output 25,000,
  `$4.1625` reserve와 `$5` cap을 별도 suite로 고정한다. Qualification은 V8 trace integrity를,
  `v8-saturation-context-v1` diagnostic은 자연 saturation/read-search removal/post-patch reset을
  각각 판정한다. Generic V8은 mock/no-experiment이고 exact 새 purpose만 OpenAI exception이다.
  Runner start/resume는 runtime version만 보지 않고 approved plan의 task, schedule, model, budget,
  pricing, image, review와 harness identity 전체를 qualification과 같은 comparator로 재검증한다.
  D-064 final offline regression은 837 collected, 830 passed/7 environment-dependent skipped다.
  이후 승인 execution hash
  `sha256:dcade27f9f89efd6c349db58cbe732c0c81f1bbaf3bbb05e6c14b4ca62f2b85c`로 정확히 한 번
  실행된 `run_45e3edc434d749f7`은 trace qualification 30/30과 자연 saturation seq 101,
  post-saturation patch seq 106, reset context seq 110을 기록해 V8 diagnostic을 통과했다.
  그러나 `review_task` evidence가 14회 거절된 뒤 40/40 model-call 상한에서 제출·evaluator
  전에 끝났다. 사용량은 618,370 input + 41,003 output, 총 659,373 token, 64 tool call,
  계산 비용 `$0.6140766`이다. Completion gate는 false이고 comparison denominator와 memory
  admission도 false다. 이 suite/hash/run은 immutable하며 재실행하지 않는다. 다음 gate는
  current-diff passing-check와 diff evidence를 REVIEW context에 지속 제시하는 loop correction의
  offline 검증이다. Post-run immutable seal과 sanitized evidence 뒤 전체 회귀는 839 collected,
  832 passed/7 environment-dependent skipped이며 Ruff와 `git diff --check`도 통과했다. Memory
  admission과 96-run core campaign은 계속 보류한다.
  D-066은 historical V8을 바꾸지 않고 `phase-evidence-v9`, `SYSTEM_PROMPT_V6`,
  `review-evidence-v1`, `context-build-evidence-v9`, `trace-source-evidence-v9`와
  `corrective-runtime-contract-v3`를 별도 opt-in으로 추가한다. REVIEW에서는 current-diff
  passing check와 final `get_diff`를 recent-event window 밖에 pin하고 exact citable sequence를
  request/tool execution/qualification에 결속한다. Stale citation rejection은
  `review-citation-error-v1`로 허용 sequence를 반환하며 같은 mutation epoch의 세 번째
  `review_task` failure 뒤 추가 model generation을 막는다. 새 successful patch는 이 count를
  reset한다. Offline V9은 `review_evidence_validation=True`의 mock/no-experiment 조합만
  허용하고 replay, arbitrary provider, experiment/mixed mode는 fail closed한다. Live V9은
  exact D-067 purpose와 OpenAI selector만 허용한다. Qualifier는 pinned evidence와 CAS를
  독립 재구성한다. 집중 회귀는
  504 collected, 502 passed/2 skipped였고 repository-wide 회귀는 879 collected,
  872 passed/7 environment-dependent skipped로 통과했다. Ruff와 `git diff --check`도
  통과했으며 provider 호출은 없었다.
  D-067 `dev-no-memory-review-evidence-v9-pilot-20260801-r1`은 승인 execution hash
  `sha256:f1b7d78243af8c87e3ec83f9373312f171073e0713a23fbc51c909fac0be6982`로 정확히
  한 번 실행됐다. `run_4c77b1102e224785`는 344,754 token, 21/60 model call, 36/100 tool
  call과 `$0.2880024`를 사용해 official evaluator에 도달했다. Regression/scope/safety는
  통과했지만 hidden acceptance가 실패해 outcome은 `task_failure`, SCRR은 false다. Budget
  binding은 없었다. Original qualification과 false campaign gate는 immutable하다. D-068은
  V9 pinned `get_diff`를 recent-events 밖에서도 인정하도록 qualifier를 보정하고 append-only
  correction `qcor_51b72504161eddf250e872cc533dbfc5a315c377971e8a6f19a74a380fe3c032`로
  corrected trace qualification 33/33을 통과했다. 이 정정은 original artifact, hidden failure,
  task outcome, SCRR 또는 campaign gate를 바꾸지 않는다. D-067과 승인 hash는 재사용·재실행하지
  않으며 comparison denominator, memory admission과 core에서 제외한다.
  D-069는 broad quantified public requirement를 maintainer-authored
  `public-review-contract-v2.coverage_targets`로 분해하는 exact tool v5/context V10 offline
  gate다. Target evidence는 latest patch/current diff에 결속된 exact path+anchor inspection 또는
  advertised passing visible check만 허용한다. `review-evidence-v2`, `task-review-v3`,
  `public-review-coverage-v1`, `phase-contract-v4`, `context-build-evidence-v10`,
  `corrective-runtime-contract-v4`와 `trace-source-evidence-v10`은 모든 target의 exact-once
  판정과 parent roll-up을 결속한다. Partial review는 artifact로 보존한 뒤 `REVIEW → IMPLEMENT`로
  되돌리고, same-diff authoritative target이 모두 verified되기 전 `finish_task`를 거부한다.
  Inspection anchor는 mutable patch가 아니라 Git base revision에 존재해야 하고
  `public-review-base-provenance-v1` CAS가 start/resume/qualification/source hash에 결속된다.
  Check/read event metadata는 result artifact bytes와 독립 대조하며, reordered target input은 contract
  순서로 정규화하고 missing finish provenance, stale/relabelled evidence, vacuous terminal과 malformed
  self-validation lifecycle을 fail closed한다.
  Generic V10은 `coverage_review_validation=True`의 mock/no-experiment 전용이다. 유일한 live
  exception은 D-070의 exact `memory-development-no-memory-coverage-review-pilot` purpose와
  OpenAI provider, v5/v10/runtime-v4, V2 HF Hub sidecar를 함께 요구한다. Checked-in suite와
  no-call preflight는 provider 권한이 아니며 별도 clean execution hash와 비용 승인이 필요하다.
  이는 선언된 public review process coverage일 뿐 target set의
  완전성, hidden correctness, SCRR 또는 memory 효과를 증명하지 않는다. V1-V9와 D-067/D-068
  artifact는 immutable하고 D-067을 재실행하지 않는다. Offline acceptance는 971 collected,
  964 passed/7 environment-dependent skipped, Ruff와 `git diff --check`로 완료됐다. 이 완료는 다음
  paid/memory gate를 자동으로 열지 않는다. D-060과 D-067 experiment ID는 결과 파일 유무와
  무관하게 hard-immutable set에 포함되어 재실행되지 않는다. D-070 offline contract 회귀는
  988 collected, 981 passed/7 environment-dependent skipped, Ruff와 `git diff --check`를
  통과했고 provider call은 없었다. Host no-call preflight는 Docker와 pinned evaluator image,
  SDK 2.47.0, API-key presence, clean Git과 fresh official pricing을 통과했으며 남은 blocker는
  invocation cost approval과 exact execution-hash mismatch뿐이다.
  D-070 승인 execution hash
  `sha256:cc361c4fa569085b0268a419ec86a7a91ec87719206d604227d2cb45a9c46914`는
  정확히 한 번 소비됐다. `run_6cc69fc1170c4a44`는 28/28 completed response와 exact input/total
  token telemetry, 611,450 input + 56,103 output token, 50 tool call, 계산상 `$0.671307`을
  기록했다. Budget dimension은 bind하지 않았고 532,447 token과 32 model call이 남았다.
  첫 V10 review는 8 target 중 7개를 verified한 valid partial review였지만, agent는 1401행 anchor를
  1407행부터 읽어 놓친 뒤 unrelated sequence 169를 세 번 인용했다. Structured review가 세 번
  거부되어 submission protocol failure로 종료됐고 evaluator에는 도달하지 않았다. Qualification은
  30/34이며 네 coverage lifecycle check만 실패했다. 별도 no-model postmortem
  `run_c07bb2e439a74380`은 exact unsubmitted diff의 regression/scope/safety pass와 hidden fail을
  확인했지만 original run, gate와 SCRR을 바꾸지 않는다. D-070 experiment ID와 hash는
  hard-immutable이며 재실행하지 않는다. 이 결과는 baseline, memory admission 또는 core evidence가
  아니다. 다음 gate는 offending target/sequence/allowed evidence를 public structured error로
  반환하고 exact-anchor recovery E2E를 offline에서 검증하는 것이다.
  D-071 evidence seal 회귀는 999 collected, 992 passed/7 environment-dependent skipped이며 Ruff와
  `git diff --check`도 통과했다. 이 seal 과정의 provider call과 추가 model cost는 0이다.
  후속 D-071 offline correction은 historical V10을 바꾸지 않고 exact
  `tool_schema_version=v6` / `phase-evidence-v11`, `SYSTEM_PROMPT_V8`,
  `corrective-runtime-contract-v5`를 별도 opt-in으로 추가했다. Gateway는 잘못된
  coverage citation을 target/requirement, submitted/allowed/invalid sequence, public
  path+anchor 또는 registered check ID, mutation/diff identity를 담은
  `coverage-citation-error-v1`로 닫는다. Context builder는 source call/failure와
  prior model-request/response-declared tool call, input/result CAS를 검증해
  `coverage-rejection-feedback-v1`를 bounded recent-event window
  밖에 지속하고, 원 rejection을 먼저 완전 재검증한 뒤 exact feedback을 받은 complete
  후속 review나 실제 call/outcome/CAS에 결속된 새 mutation이 있을 때만 제거한다.
  V11 request CAS와 `ContextBuilt`는 active `worker-claim-evidence-v1`를 mirror하며 stale
  target citation만 반복한 review는 fresh target evidence 전까지 다시 거부한다. 첫 rejection의
  fresh-worker reclaim은 필수이고, 그 worker의 후속 stale rejection은 같은 claim에서 최신 feedback으로
  복구할 수 있다. 첫 failure와 fresh request 사이에는 state-store checkpoint만 허용하고 old-worker
  model/tool activity는 qualification에서 거부한다. 전용 mock E2E는 durable rejection 직후 `SystemExit`, fresh runner resume,
  two-rejection same-worker continuation, exact-anchor read와 batched multi-check evidence, refreshed diff,
  complete review, finish/evaluator까지 통과하며
  `PatchPrepared`/`PatchApplied` 1/1을 유지했다. Qualifier의
  `coverage_rejection_recovery_contract`는 rejection/result/context/first-restart claim, latest-feedback
  supersession, every fresh recovery call/result, refreshed final-diff CAS와
  duplicate mutation tamper를 독립 재구성한다. Generic V11은 mock/no-experiment
  전용이고 provider call·비용 evidence, SCRR, no-memory baseline, memory admission 또는
  core 결과가 아니다. D-070 ID/hash/run/original qualification은 immutable하다.
  D-072는 D-071의 큰 V11 helper를 의미 보존 방식으로
  `patchloop.agent.coverage_rejection`과 `patchloop.evals.coverage_rejection`에 분리하고,
  historical tool/context/schema, artifact bytes와 D-070 evidence를 바꾸지 않는다. 새 exact
  purpose `memory-development-no-memory-coverage-rejection-pilot`과 experiment ID
  `dev-no-memory-coverage-rejection-v11-pilot-20260802-r1`은 HF Hub 한 task, `no_memory` 1회,
  v6/v11/runtime-v5, 60 model/100 tool/1,200,000 token/1,800초, output 25,000,
  reserve `$5.5125`/cap `$6`로 고정된다. Generic V11은 계속 mock/no-experiment 전용이며
  이 exact purpose만 OpenAI exception이다. 자연 rejection이 0이면 trace integrity는
  통과할 수 있지만 recovery diagnostic은 `inconclusive/rejection_not_observed`다. 하나 이상이면
  관찰된 모든 structured public rejection과 source/recovery/clearing CAS가 검증돼야 하며 실패는
  gate를 닫는다. Live hard restart는 이 one-row pilot의 요구사항이 아니라 별도 후속 fault
  exercise다. Clean-host preflight 뒤 사용자 승인 execution hash
  `sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d`는 정확히 한 번
  소비됐고 재사용하지 않는다. `run_e2132144a8774b05`는 official evaluator와 trace qualification
  36/36에 도달해 readiness campaign gate를 통과했지만 structured coverage rejection은 0이라
  recovery diagnostic은 `inconclusive/rejection_not_observed`다. 별도 rejected-patch retry 17/17과
  saturated context 17개, post-saturation `PatchApplied` 1회를 검증했으나 이는 structured coverage
  rejection recovery나 live hard-restart evidence가 아니다. Run은 797,862 input + 64,465 output =
  862,327 token, 35 model call, 57 tool call, 369,385ms와 계산 비용 `$0.841833`을 기록했고 budget
  dimension은 bind하지 않았다. Regression/scope/safety는 통과했지만 hidden acceptance가 실패해
  outcome은 `task_failure`, SCRR은 false다. Result, journal, qualification과 campaign gate는
  immutable하며 suite/hash/run을 재실행하지 않는다. D-070도 immutable하고 D-072 row는 memory
  admission, comparison denominator와 core campaign에서 제외한다. D-072 final offline verification은
  focused 322 collected, 321 passed/1 environment-dependent skipped와 repository 전체 1,022 collected,
  1,015 passed/7 environment-dependent skipped로 완료됐으며, 이 historical offline 수치는 live run
  결과와 별개다. D-073은 consumed experiment ID를 hard-immutable set에 추가하고 sanitized portable
  evidence를 `reports/live-pilot/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json`에
  보존하는 append-only seal이다. D-073 focused 회귀는 375 collected, 374 passed/1
  environment-dependent skipped, 전체 회귀는 1,025 collected, 1,018 passed/7
  environment-dependent skipped였고 Ruff, Python compileall과 `git diff --check`도 통과했다.
  D-073 과정의 provider call과 추가 model cost는 0이다.
- `docs/08-limitations.md`에 미완료라고 표시된 결과를 구현 또는 측정된 사실처럼 표현하지 않는다.
- 다음 dataset/campaign gate는 이전 gate의 executable evidence를 확인한 뒤 통과시킨다.

## Required reading

작업 유형에 따라 다음 문서를 읽는다.

| 작업 | 반드시 읽을 문서 |
| --- | --- |
| 모든 구현 | `README.md`, `docs/05-implementation-plan.md`, `docs/06-decisions.md` |
| task/evaluator/schema | `docs/03-contracts.md`, `docs/04-evaluation-protocol.md` |
| agent/tool/state | `docs/02-architecture.md`, `docs/03-contracts.md` |
| memory/retrieval | `docs/03-contracts.md`, `docs/04-evaluation-protocol.md` |
| report/UI | `docs/04-evaluation-protocol.md` |

## Non-negotiable invariants

1. **Evaluator first.** Agent prompt보다 task schema, hidden evaluator, Docker boundary를 먼저 구현한다.
2. **Public/private separation.** Private spec, hidden test, reference patch는 agent workspace·prompt·tool output에 노출하지 않는다.
3. **External run state.** Event, checkpoint, evaluator data를 대상 repository 안에 기록하거나 최종 patch에 포함하지 않는다.
4. **Constrained execution.** Agent는 task에 등록된 check만 실행한다. unrestricted shell을 agent tool로 제공하지 않는다.
5. **Append-only evidence.** 관찰된 과거 event를 수정하지 않는다. 정정은 새 event 또는 파생 artifact로 남긴다.
6. **Idempotent recovery.** Patch와 재개 가능한 tool action은 stable identity/hash를 가져야 하며, 복구 시 중복 실행을 감지한다.
7. **Deterministic primary grading.** 테스트·diff·dependency·API·safety처럼 코드로 판정 가능한 항목은 LLM 점수로 대체하지 않는다.
8. **Fair comparison.** Memory 실험에서는 model snapshot, prompt, tools, task, commit, image, budget, retry와 evaluator를 고정한다.
9. **No held-out tuning.** Held-out 실행 전에 split, threshold, scoring weight, memory index를 동결한다.
10. **No solution leakage.** Failure memory에 reference patch, 정답 코드 조각, hidden assertion을 저장하지 않는다.
11. **No invented results.** 실행 artifact가 없는 수치나 개선 주장을 README·리포트·이력서 문구에 쓰지 않는다.
12. **CLI-first scope.** Phase 6의 실험 결과가 나오기 전에는 dashboard나 전체 GitHub App을 우선하지 않는다.

## Implementation workflow

1. `docs/05-implementation-plan.md`에서 현재 phase의 가장 앞선 미완료 work item 하나를 선택한다.
2. 해당 item의 입력, 출력, failure mode, acceptance test를 확인한다.
3. 외부에 보이는 schema나 의미를 바꾸면 같은 change에서 계약 문서를 갱신한다.
4. 최소 단위 test부터 실행하고, 관련 통합 test를 실행한다.
5. diff에서 private data 노출, 대상 repo 내부 state, scope 확장을 확인한다.
6. 실제로 통과한 명령과 남은 검증을 handoff에 기록한다.

요구사항이 불명확할 때는 범위를 넓히지 않는다. [열린 질문](docs/06-decisions.md#open-questions)에서 이미 정한 임시 기본값이 있으면 그것을 사용하고, 의미 있는 계약 변경이 필요하면 결정을 기록한다.

## Definition of done

변경은 다음을 모두 만족해야 완료다.

- 지정된 work item의 acceptance criteria를 충족한다.
- 성공 경로와 대표 failure path가 test로 검증된다.
- public/private boundary를 깨지 않는다.
- 실행 결과가 stable ID, timestamp, hash 등 필요한 provenance를 남긴다.
- 실패를 삼키지 않고 구조화된 오류 또는 event로 남긴다.
- 관련 문서와 예제가 실제 동작과 일치한다.
- 재현에 필요한 명령과 환경 가정이 기록된다.

## Planned engineering defaults

확정 전까지 다음 기본값을 따른다.

- Python 3.12+, Typer, Pydantic v2, pytest, Ruff
- 명시적 domain model과 작은 adapter; 복잡한 agent framework는 사용하지 않음
- SQLite와 local filesystem으로 시작하고 저장소 인터페이스 뒤에 둠
- UTC timestamp, SHA-256 content hash, monotonic per-run sequence
- JSON/JSONL은 machine artifact, YAML은 사람이 작성하는 task/config에 사용
- 테스트는 network와 live model credential 없이 실행 가능해야 함

정확한 dependency와 명령은 `pyproject.toml`과 자동화가 생기면 그 파일을 기준으로 갱신한다.

## Expected repository boundaries

```text
patchloop/agent/       orchestration and phase policy
patchloop/tools/       constrained tool implementations
patchloop/sandbox/     process/container isolation
patchloop/state/       events, checkpoints, recovery
patchloop/verifier/    deterministic graders
patchloop/failures/    taxonomy and classification
patchloop/memory/      memory schema and retrieval
patchloop/evals/       experiment runner and metrics
tasks/                 audited public/private task fixtures
experiments/           immutable configs and generated results
docs/                  normative design documents
```

Generated run state와 evaluation artifact는 source tree의 tracked files와 섞지 않는다.
