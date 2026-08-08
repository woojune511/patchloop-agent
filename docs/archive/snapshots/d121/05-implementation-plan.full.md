# Implementation Plan

상태: **Implementation baseline active**  
현재 milestone: **D-121 preparation 완료. Exact no-start Docker readiness와 실행 승인 후보를 봉인했으며,
actual successor run은 별도 exact candidate triple 승인 전까지 닫혀 있음**

### Current D-121 preparation

| Artifact | ID | Semantic body SHA | File SHA | Bytes |
| --- | --- | --- | --- | ---: |
| Preparation approval receipt | `d121preparationapproval_0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79` | `sha256:0f0627d6cdc6e63cd5d73eff66646406b7bbd1c64affb43fc35e0fa701b6fc79` | `sha256:5a5592c2fff7deae63c50482d109c0d8e79ff4016fb96aaa8cb5a7b442d83606` | 14,662 |
| No-start readiness preflight | `d121readiness_8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12` | `sha256:8d1bbf95e3bb8fbe9717a0f3620cdd9985091d0695aff69622d92d046ad6be12` | `sha256:3423bf9af71d9b69579115d65a2b67d2bdb39363748e40a9cb78bdd461ad94e6` | 32,423 |
| Execution authorization candidate | `d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` | `sha256:b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` | `sha256:0e8ea35d4fda06ecfba180150062b873ada5b11dd98df7bd0416c557777db1c5` | 11,046 |
| Authorization source gate | `d121_711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592` | `sha256:711b9c8e738128d3d03b42c3287bf57418e02348b12a2c10707e9ce5ba1fe592` | `sha256:e9c05396e10770c4290b2e57235f32da6fe3997afcd3fdb109c3697cea773b50` | 15,514 |

No-start readiness는 Docker 8 commands/create 1/start·run·exec·probe 0, opaque source access/read 0,
residual container 0으로 끝났다. 이는 Docker configuration realization만 검증하며 runtime hash-only isolation,
trusted cutoff, record projection isolation과 independence는 모두 false다. Actual successor run은 unauthorized/count 0이고
retrieval, runtime injection, agent/provider/evaluator와 core는 closed다. D-121 focused는 47/47, D-119+D-121은
82/82 통과했다. D-120 test의 7 failures는 D-121 output path가 생성되기 전이라는 historical assertion이 실제 D-121
준비 뒤 더는 성립하지 않아 발생한 예상 결과다. D-120을 고치거나 D-121 product regression으로 분류하지 않는다.

다음 gate는 위 execution candidate ID/body/file SHA를 별도 메시지로 정확히 승인하는 것이다. 범위는 정확히 한 번의
fresh two-session hash-only run이며 D-119 retry/resume/repair, retrieval 또는 core를 허용하지 않는다.

### Historical context: D-119 and D-120

D-119는 exact one-use 실행 승인을 소비했지만 첫 번째 isolation session의 cleanup 검증에서 멈췄다. Durable journal에는
`ExecutionClaimed → ImageIdentityVerified → IsolationSessionStarted → ExecutionFailed` 네 event만 있으며, probe 결과는
증거 파일에 봉인되지 않았다. 따라서 상태는 `PARTIAL_CONSUMED_FAILED`, probe 결과는 `UNSEALED_UNKNOWN`이다. 같은
D-119 실행을 retry·resume·repair하지 않으며, 성공이나 실패 어느 쪽의 probe 결과도 주장하지 않는다.

D-120은 D-119 receipt, preflight, 4-record journal, 세 implementation file과 세 미생성 completion output을 exact bytes로
다시 결속했다. D-119 파일을 고치거나 실행하지 않았고, Docker·network·opaque source read도 수행하지 않았다. 생성된
preflight/candidate/source gate는 D-121의 새 구현, offline test, container를 시작하지 않는 exact readiness preflight와
execution-authorization candidate 준비만 제안한다. Exact D-120 candidate 승인을 받더라도 실제 D-121 Docker 실행과
opaque source read는 열리지 않으며, 별도의 exact D-121 candidate 승인이 필요하다. Trusted cutoff anchor, technical
completion, record projection isolation과 independence는 계속 false이고 matcher/retrieval/agent/core도 closed다.

선행 D-118은 두 revision-pinned opaque source를 hash로 결속했지만 trusted pre-D-116 anchor를 확보하지 못해
`BLOCKED_INSUFFICIENT_PREEXISTENCE`로 남는다. D-119의 미완료 실행이나 D-120 candidate는 이 결론을 올리지 않는다.

Historical D-117은 exact D-116 candidate 승인과 action hash를 좁게 소비해 **protocol candidate만** 만들었다. 실제 source
pool을 이름 붙이거나 issue를 읽지 않았고, pool manifest·member, blind packet, selector/adjudicator 결과와 independent
positive는 모두 0이다. 향후 pool은 public-development 전용이어야 하며 held-out task·issue·result와
private/hidden/reference/patch/trace/evaluator lineage를 포함하거나 읽을 수 없다. Exact source bytes와 membership
manifest 또는 exhaustive rule은 D-116 cutoff보다 먼저 신뢰 가능한 외부 anchor에 결속돼야 하며, issue `created_at`,
filesystem mtime, Git timestamp 또는 현재 fetch/hash만으로는 preexistence를 인정하지 않는다.

D-117 receipt/preflight/candidate/source gate의 exact ID/body/file SHA와 크기는 각각
`d117approval_f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
`sha256:f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
`sha256:40ea64548634353a12b48f8bcabce941df47e16f9b27d892722d55fcda1e5e13`, 10,096 bytes,
`d117preflight_34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
`sha256:34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
`sha256:6682f4f2870cdb34e6ee766333c95ac58a406a7d4e4086d6086752650869c305`, 29,919 bytes,
`d117blindprotocolcandidate_27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
`sha256:27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
`sha256:d10bbe5b3b65050868a1202cd1af9f130c89bbe43ceccf9359af145cac96cda7`, 7,999 bytes,
`d117_750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
`sha256:750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
`sha256:a439fc936b5b594c043b4ea90cd57bb676e79004cf4de8794b83f3af15fb13e3`, 16,813 bytes다.
D-117 focused 25/25와 D-116+D-117 연속 46/46이 통과했다. 이는 repository-wide suite 통과 주장이 아니다.

Role contract는 current conversation actor, grammar observer와 same-checkout subagent를 blind role에서 제외하고,
read-only allowlist mount를 가진 별도 process/container/VM identity를 요구한다. 이 격리는 process input visibility를
제한할 뿐 사람의 사전 지식을 cryptographically 배제하지 않는다. 격리·preexistence·chain-of-custody 중 하나라도
증명하지 못하면 append-only로 `post_hoc=true`, `independent=false`가 된다.

직전 D-116은 exact D-115 승인을 좁게 소비해 `issue.title`, `issue.description`, `repository.language`만 투영하는
Python-only public-applicability contract를 만들었다. CPython 3.12 `re` 문법, canonicalization, token·문장·절 경계,
negation, tuple 선택, contradiction 우선순위, evidence span 좌표·정렬, `SELECT`/`ABSTAIN`과 contract-error 경계를
byte-addressed contract로 고정했다. 그러나 matcher evaluator/classifier와 calibration executor는 만들지 않았고
matcher/classifier/calibration도 한 번도 실행하지 않았다. 현재 10개 public YAML 중 8개가 prospective panel이고
2개는 bootstrap fixture로 제외된다.
Pyfakefs/HF Hub 두 source anchor는 grammar 작성에 사용된 in-sample/non-independent conformance case이며, blind
independent positive는 0개다. 따라서 true relevance, three-class calibration과 policy readiness는 확립되지 않았다.

D-116 receipt/preflight/candidate/source gate의 exact ID/body/file SHA와 크기는 각각
`d116approval_016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
`sha256:016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
`sha256:86c4e279df6c3d4b6ea02719375f76370d76fb795d642f2d10211e878662ba77`, 12,014 bytes,
`d116preflight_e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
`sha256:e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
`sha256:fc2602a385242204ab9ae274ea6c73a83bd00a00eace88c7f310a57b5d4655f5`, 76,157 bytes,
`d116classsignalcandidate_0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
`sha256:0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
`sha256:8299f3d400bd9412a8b7100305a0eb57f1d5b4ea78a39d8e5edad6cd5a2b15ca`, 8,017 bytes,
`d116_e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
`sha256:e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
`sha256:f03bc7806d8401b9ac9f3d9e47df7b0ef19b16a04380bed1c9cb1d105e52320d`, 19,859 bytes다.
Focused 21/21이 통과했다. D-116의 exact next gate는 D-117 protocol candidate에 한해 소비됐으며 실제 pool 수집
권한으로 확대되지 않았다.

D-114는 exact D-113 candidate 승인을 받아 기존 D-112를 rewrite하지 않는 append-only successor validator와
correction evidence를 정확히 한 번 만들었다. Receipt/gate ID/body/file SHA는
`d114approval_20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
`sha256:20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
`sha256:1f494579e70d9e8a7f0d28439578afc3b3aa77c7735ac8bc4e81627cab70793b`, 10,493 bytes와
`d114_8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
`sha256:8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
`sha256:c336004f12f187ab0bfb7946204f877c088703d25e809a8e79e9ec84d374be11`, 15,686 bytes다. Exact
payload/key equality, paired rehash와 chronology 거부, `sealed-historical`/`current-input` 분리, snapshot/model 없이
9개 row를 재계산하는 portable path가 구현됐고 focused 35/35가 통과했다. D-112와 index bytes는 unchanged다.

D-115 preflight/candidate/source gate의 exact ID/body/file SHA와 크기는 각각
`d115preflight_c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
`sha256:c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
`sha256:91908b43eb581b09249f8285e5f1d09389092c5b40c1c794b9ab139667c86bad`, 59,725 bytes,
`d115scoredecisioncandidate_91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
`sha256:91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
`sha256:1fd424eab88c60a9d8480e756642b2c70b03afd03dd777e27bf36a3ea428df7a`, 6,839 bytes,
`d115_ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
`sha256:ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
`sha256:67f62c23e9f5e14fe9cd1d075b2c6f679764c18644837914b0031348c4a21b72`, 13,730 bytes다. Focused
19/19이 통과했다.

Current rows에서는 failure-class/validation이 모두 0이고 같은 probe의 phase/language가 entry마다 같아, threshold만
낮추거나 현재 component의 nonnegative weight만 바꿔 Moto hypothesized group을 top으로 만들면서 Babel을
no-match로 유지할 수 없다. 따라서 corrected policy는 선택하지 않았다. Conditional tuple
`0.25 semantic + 0.40 class + 0.15 phase + 0.10 language + 0.10 validation`, threshold `0.60`은 독립적인
abstaining public classifier가 존재한다고 가정한 **비권위적 counterfactual**일 뿐이다. 그 가정 아래 Moto
IMPLEMENT hypothesized score `0.6530721018133969`, Babel top `0.3156332814131685`, Moto REPRODUCE
`0.503072101813397`, phase delta 약 `0.15`가 나오지만 runtime classifier나 true relevance는 관찰되지 않았다.

D-114/D-115의 offline 판정은 D-116의 exact source로 보존된다. D-117까지 source pool/issue read, role session,
matcher/classifier/calibration implementation·execution, model/embedding load, retrieval, runtime injection,
agent/provider/evaluator/network-capable call은 모두 0이고 added model cost는 `$0`다. Network 0은
source-path/self-attested claim이며 OS-level socket 차단·계측 증거가 아니다. Score policy·threshold·rank,
entry/index/marker, retrieval/runtime injection과 core는 unchanged/closed다.

D-111 preflight는 exact D-110 frozen index를 다시 검증하고 `moto-query-scanned-count`/`IMPLEMENT`,
`babel-strict-grouped-decimal-trailing-zeroes`/`IMPLEMENT`, `moto-query-scanned-count`/`REPRODUCE` 세 public probe만
결속했다. Private/hidden/reference/known-bad patch는 읽지 않았다. Preflight ID/body SHA는
`d111preflight_ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`/
`sha256:ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`, 13,085-byte file SHA는
`sha256:fed699e068c52e2dd929b654a65369aee3499d6d69c5a38c14dcee808ff57387`다.

Candidate ID/body SHA는
`d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`/
`sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`, 6,465-byte file SHA는
`sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6`다. Source gate ID/body SHA는
`d111_348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/
`sha256:348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`, 3,308-byte file SHA는
`sha256:d550cb048e417965e482c64682df4a1b91b90067f66b36e370912f5a8d759c16`다.

Read-only audit에서 natural public query의 selective score 상한은 완전한 semantic match를 가정해도 `0.65`로
고정 threshold `0.72`보다 낮았다. Legacy structured renderer는 D-105 exact model-facing bytes와 세 entry 모두
불일치했고 query encoder도 pinned snapshot의 local-only load를 강제하지 않았다. D-111 candidate는 이 결함을
숨기거나 threshold를 바꾸지 않고 기록했다. 이후 사용자가 exact candidate triple을 별도 승인해 D-112 local
diagnostic을 한 번 실행했다. Local pinned model load/batch encode는 1/1이고 9개 score row가 생성됐지만
retrieval/runtime injection/agent/provider/evaluator/core 실행은 모두 0/false다. D-112 focused 11/11과
D-111/공용 memory 회귀 13/13이 통과했다.

Historical D-110은 사용자가 같은 메시지에서 다시 제시한 D-109 candidate ID/body/file SHA와 freeze 1회라는 좁은 범위만
승인 receipt에 결속했다. Approval receipt ID/body/file SHA는
`d110approval_cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`/
`sha256:cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`/
`sha256:f409c6296b1f87d8cb151fcc1866d263f3e74aa9341c46ab49ea3b4fef66a97c`이고 파일은 3,495 bytes,
`recorded_at=2026-08-06T12:42:48Z`다. Self-attested receipt이므로 reviewer identity 인증이나 cryptographic
signature 증명으로 해석하지 않는다.

One-use execution은 `2026-08-06T13:54:43.725943Z`에 시작했다. Pre-state의 55,644-byte index에서 정확히
다섯 pointer(`/frozen`, `/frozen_at`, `/authority/index_freeze_authorized`,
`/authority/memory_index_frozen`, `/content_hash`)만 바꿨다. Post-state는 55,687 bytes/file SHA
`sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0`, content hash
`sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56`,
`frozen_at=2026-08-06T13:54:43.725943Z`다. 72-byte marker file SHA는
`sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561`이다. Runtime과 portable D-110
index/marker가 일치하며 D-106 portable unfrozen index는 55,644 bytes/file SHA
`sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`로 unchanged다.

Append-only journal은 8 records, head
`sha256:03d8bcbf57230aa9bfd5ce4e81fa2890bb36c2f5f9e4e51c9e64b3a8c09313e1`, 9,481-byte file SHA
`sha256:f06cfa9037f09720675d3c0edd7e19516144bd46375aaa86679c5b1f6923b1e2`다. Freeze receipt ID/body/file
SHA는 `d110freezereceipt_b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`/
`sha256:b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`/
`sha256:a2aeaa0985cb1bf9ced5bdfd43c5bc473a73e5ac93bf7660ca717e3eb9285702`, 5,986 bytes,
`recorded_at=2026-08-06T13:54:43.782123Z`다. Completion gate ID/body/file
SHA는 `d110_bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`/
`sha256:bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`/
`sha256:79578db09955dab2a22b015ba5210baec28e7d30b9cac818b1f2c6d6eac782cd`이고 파일은 7,754 bytes,
`recorded_at=2026-08-06T13:54:43.793637Z`다.

Commit은 staged index fsync + same-filesystem `os.replace`, 그 뒤 marker exclusive binary create + fsync 순서의
per-file commit이다. Cooperative lock은 D-110 executor끼리만 조정하며 global two-file atomic transaction이나
arbitrary external writer exclusion은 주장하지 않는다. Partial/ambiguous state는 fail closed하고 retry/rollback하지
않는다. Pre-mutation focused 17/17과 post-freeze focused 17/17(256.5초)이 각각 통과했으며 D-110
related/full-suite 집계는 pending이다. Provider/evaluator call과 added model cost는 0/0/`$0`다. Frozen은 true지만 retrieval readiness와
실험 승인, runtime injection, core와 analysis는 false/closed다. 다음 gate는 retrieval 실행이 아니라 별도
retrieval-readiness authorization candidate 준비다.

Historical D-109는 D-108 completion gate와 D-107 portable validation을 exact hash로 재검증하고 runtime index가
55,644-byte D-106 portable index와 byte-identical이며 `FROZEN` marker가 없음을 read-only로 확인했다.
Preflight ID/body/file SHA는
`d109preflight_a7519ddeae6000c3e0fc8f368b6316ddf1d405ab77badbc8eeade12bbfbc4b34`/
`sha256:a7519ddeae6000c3e0fc8f368b6316ddf1d405ab77badbc8eeade12bbfbc4b34`/
`sha256:569a4b071c9c36d436eb2972346d618ece3c748bd92fcfa9c06b12c482625999`다.

Freeze candidate ID/body/file SHA는
`d109freezecandidate_480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`/
`sha256:480d2aa8657fd143397fcfc71f252b8a8e3c0988d3950b5671089cf6dc8b8d46`/
`sha256:ae8a8c6e58b058720943bae9088da2cf242168a70f654006557dd84c84d4e580`다. Gate ID/body/file SHA는
`d109_e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef`/
`sha256:e37e716aceb0a322820eada8b83d8a309e06052f6060c986f6025c61b7d999ef`/
`sha256:0953687473bd25f48ad52bdc78c577d6a4daa4947b019fcd65809e7548c4f949`다. Focused 8/8과
D-105~D-109/memory 관련 회귀 95/95가 통과했다. Repository-wide full suite는 1,937 passed, 7 skipped,
failure 0이며 1,920.65초에 완료됐다.
D-109 당시 일반 `진행해줘`는 candidate 승인이 아니므로 actual freeze와 이후 단계는 false였다. 당시 다음
gate는 사용자가 exact candidate triple을 다시 입력하는 별도 승인이었다.

Historical D-108 실행은 exact D-107 source gate와 token-count plan을 다시 검증하고, 사용자가 승인한 baseline과
with-memory count call만 순서대로 수행했다. 승인 확인서는
`reports/memory-development/d108-provider-token-count-approval-receipt.json`, ID/body SHA
`d108approval_dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`/
`sha256:dbe0873a16902f36a5094e963360f77d414973e29dec5fca5bab7a17c1ff3af3`, 2,768-byte file SHA
`sha256:20442ff99a50fe6b79b7f155559816e98b3cf79523fb55e17627480de95f7b31`다. 이 receipt는
self-attested이며 reviewer identity 인증이나 cryptographic signature 증명이 아니다.

Baseline request의 provider count는 2,193 input token, exact D-105 whole-entry bundle을 넣은 with-memory request는
2,895 input token이었다. 차이 702 token은 사전 고정한 최대 2,000 token 이하이므로
`provider_exact_budget_validated=true`다. Provider input-token count/generation call은 2/0, SDK transport retry는
0, automatic retry는 false다. API key는 artifact에 저장하지 않았고 evaluator call은 0회이며 실제 billing 또는
free-tier 적용 여부는 주장하지 않는다. Provider receipt는
`reports/memory-development/d108-provider-token-count-receipt.json`, ID/body SHA
`d107countreceipt_80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`/
`sha256:80447f354d982620b1c849a32abcd276c40428721c8948f6aef5671a11176946`, 1,800-byte file SHA
`sha256:43ce5dc5260a9f67e05f695a68a7dbf840ef3743f7ba7858583e9e74fb07d474`다. Append-only journal은
`reports/memory-development/d108-provider-token-count-execution.jsonl`, 6 records, head
`sha256:84905f7a334ec349a2c979e6cfb68c9c67a23dda9219f1fc8036f9d2e78f5eaf`, 6,124-byte file SHA
`sha256:01f96bc62f4a1f1d692328e2e7e71e8456a2976b772a70cf0bd66ab1b07227cd`다.

D-108 completion gate는 `reports/memory-development/d108-provider-token-count-completion-gate.json`, gate/body ID
`d108_c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`/
`sha256:c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86`, 4,794-byte file SHA
`sha256:5f57e29caa3a3c940c280a69fbed3abe3d8daba4b4542e039355443df931d7bc`다. Exact budget 검증으로
`index_freeze_authorization_candidate_ready=true`가 됐지만 `index_freeze_authorized=false`,
`memory_index_frozen=false`, retrieval/runtime injection/core/analysis는 계속 false/closed다. D-108 focused
검사는 offline 8개와 checked-in artifact 2개를 합해 10/10 통과했고, D-105~D-108/memory 관련 회귀는
87/87 통과했다. Repository-wide full suite는 1,929 passed, 7 skipped, failure 0이며 1,235.51초에
완료됐다. Ruff, compileall과 `git diff --check`도 통과했다. 다음 gate는 exact D-108 completion
gate에 대한 별도의 명시적 index-freeze 승인이다.

Historical D-107은 D-106 gate와 portable index를 외부 고정 ID·파일 크기·SHA로 확인하고 stored vector만으로
55,644-byte index를 offline 재구성했다. 검증 보고서는
`reports/memory-development/d107-portable-index-validation.json`, ID/body SHA
`d107portable_8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`/
`sha256:8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785`, 3,146-byte file SHA
`sha256:a6e71de1eea4a311d790e14a25dc9e507e1a2107176a7d0967ac074f9e50f259`다. Runtime-equivalent request plan은
`reports/memory-development/d107-provider-token-count-plan.json`, ID/body SHA
`d107plan_7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`/
`sha256:7ace0e204f367fc857bfbc1ddaa1bbdc58dd9ff3c9272f9d9c7e2b7241160ee6`, 10,143-byte file SHA
`sha256:2a3d817d14d500863d56d5446010866a6feb2361eb684c3575400020bc31a085`다. Source gate ID/body SHA는
`d107_4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`/
`sha256:4bc473796fd4564bb4d4cc9bf975ea9e41addb4fda620135e6ae4d6a21e645d4`, 4,175-byte file SHA
`sha256:b3e24975062e379ec94c77187570b392026bacdcc855adedb00943467aaf09f2`다. D-107 자체 provider/evaluator
call과 added model cost는 0/0/`$0`였고 당시 실제 count, freeze, retrieval과 core는 닫혀 있었다. Focused
13/13과 D-099~D-107/memory/qualification 관련 363/363이 통과했다. Repository-wide full-order는 1,926
collected 중 1,918 passed/7 environment-dependent skipped/기존 order-dependent D-093 WAL/SHM invariant 1
failed였고, 그 exact test는 fresh isolated process에서 1/1 통과했다. 이를 D-107 failure나 fix 또는 전체
통과로 합산하지 않는다.

Historical D-106은 exact D-105 gate를 참조한 사용자의 좁은 승인을 self-attested receipt로 기록했다. Exact model revision의
safetensors runtime file 10개를 hash로 검증하고 CPU/local-files-only에서 fresh load와 encode를 두 번 수행했다.
세 D-105 render는 218/220/207 token으로 max sequence 256 안에 들어가며 `(3, 384)` float32 finite normalized
vector를 만들었다. 새 builder는 D-104 source 하나당이 아니라 승인된 semantic group 하나당 entry 하나를 만들고,
D-105 render bytes 자체를 embedding input으로 사용한다. Content-derived index
`idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064`는 3 entry/3 vector를 포함하지만
`frozen=false`다. AnyIO/Loguru hold group, legacy failure별 builder와 legacy renderer는 사용하지 않았다.
Provider/evaluator call 0/0, added model API cost `$0`이며 다음 gate 전에는 freeze/retrieval/core를 실행하지 않는다.
D-106 focused와 memory regression 17/17, related 97/97, repository-wide 1,906 passed/7 environment-dependent
skipped/failure 0을 확인했다.

Historical D-105는 ASCII/LF/NFKC-required whole-entry renderer로 1,191/1,164/1,161-byte text 세 개를 만들었다. 2,000-token
policy는 same-full-request provider input-token delta로 정의하고 `chars/4` 추정치를 사용하지 않는다. D-105는
provider를 호출하지 않았으므로 exact token validation은 false다. `all-MiniLM-L6-v2`의 full commit을 candidate에
고정했지만 snapshot/download/file/vector verification은 하지 않았다. 다음 gate는 exact D-105 gate approval,
locked embedding snapshot preflight와 group-aware builder다.

Historical D-103 receipt/seal과 이전 chain은 immutable하다. D-104는 seal의 admitted template 3개를 strict source wrapper로
그대로 투영했고 hold 2개는 만들지 않았다. 아직 index가 없으므로 mandatory `MemoryEntry.index_version`을 임의로
채우지 않는다. D-104가 만든 actual `MemoryEntry`, rendered memory, embedding과 index count는 0이다. Historical
index state는 inspect하거나 수정하지 않았다. D-105도 actual `MemoryEntry`, embedding과 index를 만들지 않았고
index build/freeze, retrieval, core와 analysis를 계속 닫아 둔다.

Historical D-100은 expected-tail CAS와 hash chain으로 semantic-group decision을 append하고 complete 5-group decision만
template preview로 projection한다. Candidate approve는 D-099 exact rule hash를 요구하고 hold approve는 거부한다.
승인 group 하나당 template 하나이며 실제 index version, embedding과 freeze state는 없다. Source gate는 actual
human decision 0, admitted rule 0, preview entry 0을 결속한다. 다음 gate는 사용자가 exact group/fingerprint/rule
hash에 대해 명시한 결정을 기록하고 portable admission seal을 만드는 것이다.

D-099은 exact 9 source를 pyfakefs, HF Hub, AnyIO, Loguru, tox의 5개 group으로 분할한다. Candidate는
3 group/6 source, hold는 2 group/3 source이며 admitted rule은 0이다. 9개 portable submitted patch와 74개
selected public-event reference를 D-098 seal 및 CAS에 결속하고, clean machine portable validation과 explicit
source-machine raw rebuild를 분리한다. 이 proposal은 기존 failure별 review history나 index builder의 입력이 아니다.
다음 gate는 group-level append-only human decision과 group-aware consumer다.

D-098은 source commit `67fa85e47c5cf39c0ee03ad69d9d31f9fdd11ac3`과 consumed execution hash
`sha256:1a5aaccc4f95f71d285e0e0a9c8ccb27f82e235fbff465ef30f095401fde25f4`의 12-row 결과를
read-only로 재검증한다. 12/12 terminal·qualified·cost-settled, 11 official evaluator와 1 canonical pre-provider
budget terminal, 2 resolved/9 task failure/1 agent failure를 그대로 봉인한다. Exact development SCRR 2/12는
baseline 관찰값이지 held-out 또는 memory 효과가 아니다. Official task failure 9개만 review queue에 들어가고
budget terminal과 success는 제외된다. `memory_review_eligible=true`지만 `memory_admission_unlocked=false`다.
다음 gate는 public evidence review·semantic dedup·leak scan이고 index/core를 자동으로 열지 않는다.

Historical D-097은 `dev-no-memory-condition-neutral-3000k-20260805-r1`에 frozen memory-development 6개 task를 source
order대로 `no_memory` 각 2회 배치한다. D-096 source identity와 deterministic expanded schedule은 서로 다른
hash로 고정한다. Exact D-096 tuple은 runtime contract/evidence v2와 plan/manifest/start/resume/qualification에
결속하고, historical D-083/D-084 v1은 그대로 보존한다. Full-schedule policy는 첫 provider call 전에 하나의
fsync된 `FullScheduleCostReserved` event로 exact 12 rows, row별 `$13.6125`와 `$163.35` full reserve를 결속한다.
같은 plan/CAS/journal을 각 row 전에 재검증하고 terminal row마다 deterministic settlement를 기록한다. Prospective
campaign-scoped source cap은 `$164`다. D-097은 per-row atomic SQLite consumption을 구현하지 않으며 live resume은
disabled다. Cost journal은 duplicate paid-call prevention을 주장하지 않고 기존 one-use execution hash가
authorization을 단일 sequential invocation으로 제한할 뿐이다.
Historical `$150` project cap과 사용자 승인 상태는 변경하지 않는다. Task success와 hidden acceptance는
campaign source predicate가 아니며, live result와 memory/core authority는 여전히 닫혀 있다.

Historical D-092는 D-081 r3, D-085/D-086, D-087, D-089에서 18-run·8-task·4,079개의 public event를 replay했다.
Repeated-rejection `N=3..10`과 relative-context `{2,4,8} × {8,16,32 calls}` 후보 중 zero false stop,
3-task coverage, token 또는 wall suffix 20%와 leave-one-task-out를 모두 통과한 후보는 0개다. Absolute 90k
ceiling은 D-089 한 task만 잡는 post-hoc sensitivity이므로 admission 대상이 아니다. D-092가 선택했던 immediate
denominator binding 방향은 D-093이 readiness-stage misclassification으로 정정했다. Final verification은 focused 20/20과
repository-wide sharded 1,559 collected 중 1,552 passed/7 environment-dependent skipped를 통과했다.

D-091은 D-087 r2와 D-089의 public event metadata를 재집계했다. D-089은 `PatchApplied` seq 103 이후 68 model/96
tool call과 1,772,530 token을 사용했지만 추가 `PatchApplied` event는 없었고 check pass 0/6, rejected apply 14였다. Retry source
context와 qualification은 통과했으므로 confirmed harness defect는 아니지만, 더 큰 token ceiling이 completion을
보장한다는 증거도 아니다. 다음 단계는 cross-task offline evidence로 generic fail-fast/context ceiling의 필요성을
결정하는 것이며 live budget freeze가 아니다. Final verification은 focused 238/238, repository-wide sharded
1,539 collected 중 1,532 passed/7 environment-dependent skipped다.

2026-08-05 구현 스냅샷:

| 영역 | 상태 | 현재 evidence |
| --- | --- | --- |
| Phase 1 evaluator | done (local + Docker) | Reference 통과, 6종 bad patch 거부, `official=true` |
| Phase 2 agent | done (offline + Docker evaluator) | 3 task × mock/replay 6개 공식 run, 전체 trace와 valid patch 생성 |
| Phase 3 state machine | generic V2/V5 baseline 유지; historical V1-V11 보존 | V10/V11과 exact HF sidecar는 retired diagnostic-only; generic dev/core에 promotion·copy·expansion 없음 |
| Phase 4 recovery | done (offline hard-kill) | OS lock/atomic claim, postimage-write 중단 reconciliation, fresh interpreter resume와 9개 submission boundary에서 duplicate mutation/lifecycle 0 |
| Phase 5 memory | D-120 cleanup-correction candidate pending exact approval | D-119는 `PARTIAL_CONSUMED_FAILED`/`UNSEALED_UNKNOWN`로 소비돼 retry 없음; D-120은 D-119를 수정하지 않고 D-121 구현·offline test·no-start readiness·별도 실행 승인 후보만 제안; trusted cutoff/independence false, record/matcher/retrieval/agent/core 0/closed |
| Phase 6 evaluation | D-098 exact no-memory baseline result sealed | 12/12 denominator complete, SCRR 2/12, review candidates 9; admission/index/core/comparative analysis closed |
| Phase 7 viewer/GitHub | viewer implemented, external GitHub gate pending | Lifecycle critical-path route test 통과, 실제 Draft PR 미실행 |

Calibration fixture gate는 5/5로 완료됐다. 세 smoke task와
`duration-minute-boundary`, `csv-final-record-flush`는 evaluator, sandbox와 authoring workflow를
검증하는 fixture다. 뒤의 두 package가 물리적으로 `dev-train` 아래에 있어도 memory source나
research task로 보지 않는다. 현재 admitted research task는 20/20이며 memory-development
task admission은 6/6, development-validation은 2/2, core-same-repo와 core-cross-repo는
각각 6/6과 6/6이다. Dataset manifest에는 calibration 5개와 admitted research 20개,
총 25개 package가 등록돼 있다. FuseSoC #776, AnyIO #1134와 pyfakefs #1269가 public
contract 구조만으로 stress sentinel에 선정됐고 30-run schedule과 함께 machine audit를
통과했다. Dataset은 `frozen`이며 `research_ready=true`, `stress_ready=true`,
`complete=true`다.

`done`은 해당 코드 경로와 executable evidence를 뜻한다. Docker evaluator와 offline agent
smoke, 스무 research admission과 dataset freeze는 2026-07-28까지 통과했다. 동결된
stress schedule은 아직 실행되지 않았다. 두 Live OpenAI 12-run development campaign은
diagnostic으로 완료됐지만 usable no-memory baseline과 96-run core campaign은 완료되지
않았으며 `docs/08-limitations.md`에서 별도로 추적한다.

D-074는 D-069~D-072의 historical code와 evidence를 삭제하지 않는다. V10/V11 및 task-specific
HF Hub sidecar는 `retired diagnostic-only`로 유지하며 generic baseline의 readiness 선행조건에서
제외한다. D-075는 generic V2/V5, `SYSTEM_PROMPT_V3`, SDK transport retry 0과
40/100/850,000/1,800초를 exact four-task readiness 후보로 고정했고 승인 hash
`sha256:1709a9e9911f980aafe28cdd9fe9ed486367c134e2dc9e465c88e01f9462bd66`로 정확히 한 번
실행됐다. 4/4 terminal·qualified와 error 0에도 evaluator 도달은 2/4였다. HF Hub는 total-token,
pyfakefs는 model-call guard에 걸렸으므로 readiness gate는 false다. D-076은 이 결과를 append-only로
seal하며 D-075를 재실행하지 않는다. 850k는 comparison budget으로 동결되지 않았고 baseline,
memory admission과 core는 계속 닫혀 있다.

D-077은 이 두 public budget confound에만 condition-neutral headroom을 주는 새 exact successor
`generic-baseline-readiness-v2v5-20260802-r2`를 선택한다. Task/order/model/prompt/tool V2/context V5,
retry 0, output 25,000, tool 100과 wall 1,800초는 그대로 두고 model call만 50, total token만
1,200,000으로 바꾼다. 2026-08-02T13:11:37Z 공식 rate 재확인 기준 reserve는 four-row `$22.05`,
cap은 `$23`이다. 이후 clean hash가 승인되어 정확히 한 번 실행됐고, 4/4 terminal·qualified와 error
0에도 evaluator 도달은 3/4라 gate는 false였다. Pyfakefs만 50 model call에서 종료됐고 token/tool/wall은
bind하지 않았다. D-078은 raw artifact를 바꾸지 않고 이 결과를 seal하며 자동 재실행이나 budget 증가를
승인하지 않는다.

D-079는 D-078의 hidden outcome을 고치거나 four-row gate를 재실행하지 않는다. Public trace에서 남은
model-call admission confound만 분리하기 위해 pyfakefs 한 task를
`pyfakefs-workflow-completion-probe-v2v5-20260803-r1`로 선택한다. Model/tool call budget은 `null`로
두고 관찰만 하되 3,000,000 total token, 7,200초 wall, output 25,000과 기존 exact-request, loop,
sandbox/evaluator/cost guard를 유지한다. `$13.6125` reserve와 `$14` cap은 authorization bound일 뿐
현재 측정 비용이 아니다. 이 probe는 calibration-only이며 gate가 통과해도 comparison budget을 동결하거나
no-memory baseline, memory admission 또는 core를 열지 않는다.

D-080은 그 exact probe의 live result를 봉인한다. `run_606349c2c56342d4`는 84 model/119 tool call 뒤
official evaluator에 도달했고 budget confound는 없었지만 hidden task failure였다. Historical original
gate false는 qualification-summary projection mismatch 때문이며 correction
`gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`의 derived process gate만
true다. Semantic body hash는 `sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`,
correction harness commit은 `7e40e27446bcf011f700c219a96983e5670422f4`다. Original artifact와 task
outcome은 바꾸지 않는다. Final verification은 focused 331 passed, repository-wide 1,162 collected 중 1,155
passed/7 environment-dependent skipped였고 Ruff, Python compileall, JSON parse와 `git diff --check`를 통과했다.
Provider call은 0이며 추가 model cost는 `$0`이다.

D-081은 D-080 single-row 관찰을 frozen population budget으로 승격하지 않고 public process usage로
condition-neutral 후보를 만들었다. D-082에서 clean commit
`b4c79242bb0a94eed50530116205323e78c7d21a`와 승인 execution hash
`sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`로 r3를 정확히 한 번
실행했다. 4/4 terminal·qualified·official evaluator와 gate v2 pass, confound 0을 기록했지만 task success는
Babel 1/4이고 세 row는 hidden failure다. Regression/scope/safety는 4/4 통과했다. 총 111 model/175 tool,
1,929,316 token과 계산 비용 `$1.79426325`를 사용했다. D-081/D-082는 calibration-only이고
baseline/memory/core를 열지 않는다. 동일 ceiling의 96-run reserve `$1,047.60`과 원래 `$150` cap의
충돌은 별도 decision으로 해결한다. D-075/D-077/D-079/D-080은 immutable하다.

D-083은 exact D-081 r3 pyfakefs observed-prefix minimum 1,303,223에 20% headroom을 적용한
1,563,867.6을 100,000 단위로 올림해 per-run total token 1,600,000을 동결한다. Model/tool call은
`null`/`null`, wall은 1,800초, output은 25,000, SDK transport retry는 0이다. Completion guarantee는
아니며 D-080 historical minimum 1,815,619와 hidden outcome은 derivation scope 밖이다. Reserve는
`$7.3125`/run, `$87.75`/12, `$131.625`/18, `$702`/96이고 기존 `$20`/`$150` cap은 유지된다.
따라서 runtime/manifest/qualification support와 live execution, baseline, memory admission, core는 다음
gate까지 fail closed다.

D-084는 그 pending runtime support를 provider 호출 없이 구현한다.
`condition-neutral-comparison-runtime-contract-v1`을 execution plan/hash에 넣고 exact
`RunManifest`에서 start 전에 재구성한다. Runner는
`condition-neutral-comparison-runtime-evidence-v1`을 content-addressed `RunStarted` artifact로 남기며
resume에서도 descriptor와 bytes를 다시 검증한다. Budget diagnostic은 exact registered profile만 받고,
no-memory trace qualifier는 approved plan, runtime CAS와 disabled-call observability contract를 독립
검증한다. Core 네 condition은 동일 tuple의 plan/manifest/start-resume 구조만 지원한다. Memory index와
condition별 terminal qualification, 기존 cost-cap conflict가 남아 live execution, baseline, denominator,
memory admission과 core는 계속 닫혀 있다.

### D-087 accrued-spend source gate

D-086이 workflow readiness를 확인했으므로 historical `$20 → $88` 양자택일은 폐기한다. 대신 새 exact
campaign ID에서 per-run resource ceiling과 campaign-local list-price cap을 분리한다. D-081 r3 public
usage의 mean 12-run projection은 `$5.38278975`, max-run envelope은 `$14.36724`다. Envelope에 1회 전체
reserve `$7.3125`를 더한 `$21.67974`를 `$5` 단위로 올려 hard cap `$25`를 선택한다. 이는 task success나
hidden outcome을 사용한 선택이 아니다.

각 row는 `accrued_nano_usd + 7,312,500,000 <= 25,000,000,000`일 때만 시작한다. Reservation은
`RunCostReserved`로 provider boundary 전에 fsync하고, terminal usage token에서 재계산한 비용을
`RunCostSettled`로 기록한다. 부족하면 `CostReserveUnavailable` 뒤 current/remaining row가
`not_started`가 된다. `$87.75` 12-run theoretical bound는 disclosure로 남고 `$25`가 completion을
보장하지는 않는다. Exact one-use capability와 SQLite atomic consumption이 runner/provider 진입 전에
reservation을 소비한다. 다음 row는 prior qualification/source/result를 다시 로드해 token-derived nano-USD
settlement를 검증한 뒤에만 열린다. Preserved SQLite anchor 아래 marker 삭제, journal reset, alternate root와
lower-settlement rehash는 거부한다. Campaign resume은 external/request-level durable billing reservation 전까지
금지한다.

다음 executable gate는 새 source commit의 clean no-call preflight다. Fresh official price, Docker image,
SDK, D-086 pilot admission과 exact cost-policy hash를 검증해 candidate execution hash를 만들되 provider는
호출하지 않는다. 그 뒤에만 exact hash와 최대 `$25`에 대한 별도 사용자 승인을 요청한다. Campaign result가
sealed되기 전에는 no-memory baseline, comparison denominator, memory admission/review/index와 core를 열지 않는다.
Source/offline gate verification은 focused 68/68, repository-wide 1,472 collected 중 1,465 passed/7 skipped다.
Artifact SHA는 `sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe`이며 provider call/cost는 0/$0다.

## 1. Sequencing rule

다음 phase는 현재 phase의 exit gate가 executable evidence로 통과한 뒤 시작한다. 현재
read-only trace viewer는 pilot 진단을 위한 선행 도구다. Condition comparison dashboard와
GitHub 연동은 Phase 6의 core experiment가 재현된 뒤에만 시작한다.

```text
Evaluation foundation
  → Minimal agent
  → Structured state machine
  → Persistence and recovery
  → Failure memory
  → Core evaluation
  → Viewer and GitHub demo
```

## Current dataset gate — completed

목표: Calibration과 research evidence를 분리하고, benchmark/upstream provenance가 있는 20개
research task를 admission한다.

### Ordered work items

1. Dataset manifest에 5개 calibration fixture를 등록하고 headline exclusion을 검증한다.
2. SWE 계열 benchmark instance와 실제 upstream issue/PR에서 Python coding 후보를 수집한다.
3. 각 후보를 constrained tool, registered check, submitted patch와 separate hidden evaluator
   계약으로 변환한다.
4. Base/no-op로 visible pass와 hidden fail을 확인하고, reference를 pinned Docker image에서 3회
   실행하며 세 개 이상의 representative bad patch를 거부한 evidence hash를 등록한다.
5. Memory-development 6, development-validation 2, same-repo core 6, cross-repo core 6을 채운다.
6. Admitted research task 중 Terminal-Bench 2.1 pattern을 적용할 sentinel 세 개를 동결한다.
7. 원본 benchmark 호환성 run은 external acceptance lane에 남기고 core aggregate와 분리한다.

2026-07-28 현재 1~6번은 executable admission과 machine-audit evidence로 완료됐다.
7번 external acceptance lane은 frozen core dataset과 분리된 후속 작업이다. Live 경로는
D-041 r5, D-043 controlled r6, D-045 primary r1과 D-047 call-budget hardening을 거쳐
corrective primary r2 `run_afd5080a77a34995`의 official evaluator와 qualification
23/23 통과까지 진행됐다. 이어 실행한 `dev-no-memory-20260728`은 12/12 terminal trace를
만들었지만 evaluator 도달 0/12라 성능 baseline으로 사용할 수 없다. D-048은 그 trace에서
확인된 repeated search/read와 investigation-state loss를 condition-neutral하게 닫는다.
새 development-validation v4 pilot `run_d7207fbb06184dd3`은 official evaluator와
`investigation_evidence`·`investigation_lifecycle`을 포함한 qualification 25/25를
통과했다. 이 pilot에 결속된 `dev-no-memory-v4-20260730-r1`도 exact pilot commit의
detached worktree에서 별도 승인 hash로 정확히 한 번 실행됐다. 12/12 terminal·qualified,
evaluator 3/12지만 SCRR은 0/12다. 아홉 run의 strict exact-request budget exhaustion 때문에
usable no-memory baseline은 아직 없다. D-052에서 token-aware corrective tail과 future
250,000-token contract를 offline 검증했다. 세 task failure의 structured review proposal은
두 semantic group으로 검증됐지만, budget-confounded baseline에서 memory를 먼저 승인하지
않기로 했다. D-054는 실행되지 않은 250k single pilot을 supersede하고 Babel control과 Moto
harder completion probe의 600,000-token no-memory completion panel을 별도 계약으로 고정했다.
그 panel은 exact hash 승인 아래 한 번 실행돼 scope-compliant success 2/2와 qualification을 통과했다.
D-060의 memory-development 3-task budget pilot도 exact hash로 한 번 실행됐다. HF Hub만
total-token budget에 막혔고 PDM/pyfakefs는 evaluator에 도달한 task failure였다. 후속 D-062
v4/v7 900k corrective pilot은 승인 hash
`sha256:464a6eca2597698ca35caa4d7c97173f1af792daec042c36d81b5b8189ae4031`로 정확히 한 번
소비됐지만 HF Hub `run_0ccfc8fd359a4785` 뒤 original qualification failure로 중단됐다.
나머지 두 row는 시작되지 않았고 original gate는 false다. 이 trace는 saturation이 context에
반영되지 않은 gap과 일곱 patch preview failure를 보여주므로 baseline으로 쓰지 않는다.
D-063 `phase-evidence-v8`은 이 gap만 mock/offline에서 닫았고 historical v7 rendering과 D-062
source hash를 보존했다. D-064는 기존 purpose를 완화하지 않는 exact single-task live pilot
계약을 별도 purpose와 runtime v2로 구현한 뒤 승인 hash
`sha256:dcade27f9f89efd6c349db58cbe732c0c81f1bbaf3bbb05e6c14b4ca62f2b85c`로 정확히 한 번
실행했다. Live V8 diagnostic은 통과했지만 completion gate는 evaluator 전에 false로 끝났다.
다음 변경 D-066은 provider 호출 없이 REVIEW evidence-loop correction을 V9으로 구현했다.
Current-diff passing check와 final diff를 recent-event window 밖에 pin하고 exact citable sequence,
structured rejection과 active-epoch three-rejection guard를 추가했다. 집중·전체 회귀는
통과했으며 D-064는 재실행하지 않는다. D-067은 60 model/100 tool/1,200,000 token/1,800초
상한의 별도 승인 hash로 정확히 한 번 실행됐다. Official evaluator에 도달했으나 hidden
acceptance가 실패했고 budget은 bind하지 않았다. D-068은 V9 pinned diff qualification만
append-only로 정정했으며 original result와 campaign gate를 바꾸지 않는다. D-069는 이 실패의
공개 requirement coverage 분석에서 드러난 broad-quantifier gap만 별도 V10 offline contract로
다룬다. Maintainer-authored target별 current-diff inspection 또는 passing visible validation을
요구하고, partial review는 보존하되 REVIEW에서 IMPLEMENT로 되돌리며 exact target coverage가
완료되기 전 submission을 막는다. D-067은 재실행하지 않고 V1-V9 artifact도 재해석하지 않는다.

D-062 original result, journal과 qualification artifact는 immutable하다. 후속 독립 분석은
qualification failure에서 v5-vs-v6/v7 nominal-reserve drift를 분리했다. Append-only
correction `qcor_8b6ff812...4870b6`는 corrected trace qualification을 통과했지만 original
qualification, false campaign gate와 task outcome은 변경하지 않는다.

동결 evidence:

- Manifest:
  `sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`
- Stress schedule:
  `sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`
- Sentinel: `fusesoc-retained-parse-error-diagnostics`,
  `anyio-extensionless-entrypoint-worker-main`,
  `pyfakefs-file-wrapper-io-capabilities`
- Schedule: 세 task 모두 context reset과 worker restart를 persistent state on/off로 2회씩,
  synthetic test timeout을 persistent state on으로 2회씩 실행하는 총 30개 derived run.
  Fault-free baseline은 core no-memory run이며 stress 결과는 core aggregate에 포함하지 않는다.

### Exit gate — passed

- Calibration은 정확히 5개이며 memory/core/headline에서 거부된다.
- Research role은 정확히 20개이고 easy task가 없으며 현재보다 낮은 품질 기준으로 수를 채우지
  않는다.
- 모든 research task가 immutable source provenance, base visible pass/private hidden fail,
  official reference 3회 pass와 세 개 이상 bad-patch rejection evidence를 가진다.
- Same-repo repository coverage와 cross-repo disjointness, solution-lineage uniqueness가
  machine audit를 통과한다.
- 세 sentinel과 fault schedule이 freeze되고 `include_in_core_metrics=false`다.

## Current result seal — D-086 measured condition-neutral pilot

목표: exact D-085 invocation의 raw result와 passed readiness gate를 append-only로 봉인하고, original
budget-pressure selector gap을 raw evidence rewrite 없이 좁게 정정한다. Provider 재호출은 없다.

### Ordered work items

1. **완료:** Execution hash `sha256:7163f6c44aa5b7790d35546be37781248d6575eac60986b2610f2e21c35348a0`,
   commit `629b9fdd9f69d1522cf565a06ae9679abe3f60a7`, run `run_c355405d826641b9`의 exact identity를 고정한다.
2. **완료:** Original readiness gate의 terminal/qualified/official evaluator 1/1과 error/terminal-loop/budget-terminal
   0, qualification 28/28과 hidden/regression/scope/safety pass를 raw state에서 재검증한다.
3. **완료:** Usage 69,701 input + 3,500 output = 73,201 token, 8 model/9 tool call, 50,769ms와 calculated
   `$0.06802575`를 result/events/rate에서 reconcile한다.
4. **완료:** Original `budget-pressure-error-v1`을 immutable하게 보존하고, exact D-085 selector만 추가한
   read-only recomputation으로 token/wall headroom 1,526,799/1,749,231ms와 binding `none`을 append-only
   correction에 기록한다.
5. **완료:** D-085 experiment ID를 hard-consumed set에 넣어 local raw result/journal이 없어도 provider 전에
   재실행을 차단한다.
6. **진행:** Sanitized portable seal과 correction manifest를 content hash로 봉인한다. Paths/SHA는
   `reports/live-pilot/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.json` /
   `sha256:520ae8408c4e090a2c66a0ed3b2c5c29738762eec1b4f7d87b9452e551635464`,
   `reports/live-pilot/artifacts/d086-condition-neutral-comparison-pilot-budget-pressure-correction.json` /
   `sha256:bd42c50b7da2400eea8e340358e92ff2605a9fde8d866d3fdff1c9695b95aeb4`다.
7. **진행:** Raw reconciliation, journal chain, durable qualification recomputation, exact selector, immutability,
   leak scan과 full regression을 닫는다. Final evidence는 `focused 64/64; repository-wide 1,416 collected, 1,409 passed/7 skipped; Ruff/compileall/JSON/git-diff checks passed; seal provider calls/model cost 0/$0`이다.
8. **대기:** D-086 seal 이후에도 별도 decision 전에는 12-run cap을 `$20 → $88`로 변경하지 않는다.
9. **대기:** Cap을 채택할 때만 `pilot_run_id`, 새 clean campaign source commit, fresh pricing/preflight/hash와
   별도 사용자 비용 승인을 준비한다.

### Gate status — measured readiness passed; performance and paid campaign authority closed

- D-085 exact workflow는 끝까지 실행됐고 한 Babel task도 성공했다.
- Single-row result이므로 no-memory baseline이나 success-rate estimate가 아니다.
- Comparison denominator, memory admission/review/index, core와 `analysis_ready`는 계속 닫혀 있다.
- Original D-085 source artifact/decision과 raw result/gate는 immutable하다.
- Actual invoice 또는 free-tier charge는 주장하지 않는다.

## Historical source gate — D-085 exact condition-neutral comparison pilot

목표: 12-run no-memory collection 전에 D-083/D-084 exact tuple의 최소 one-row pilot이 plan/manifest/start-resume/
qualification/evaluator lifecycle을 exercise할 수 있도록 source contract를 닫는다. Provider는 호출하지 않는다.

### Ordered work items

1. **완료:** Exact ID `dev-validation-condition-neutral-v2v5-pilot-20260803-r1`, frozen Babel task,
   `no_memory` 1회와 D-083/D-084 tuple만 nullable count를 허용하도록 suite/manifest selector를 고정한다.
2. **완료:** Execution plan/hash, D-084 runtime contract/evidence, start/resume와 paid boundary를 같은 identity로
   결속하고 arbitrary/near-match pilot을 거부한다.
3. **완료:** Trace qualifier가 runtime CAS, disabled-call observability, pricing freshness와 no-memory boundary를
   독립 검증하도록 한다.
4. **완료:** `condition-neutral-comparison-pilot-readiness-gate-v1`이 terminal/qualified/official evaluator 1/1,
   exact disabled-call-guard pass와 budget/terminal-loop를 포함한 process confound 0을 요구하되 task
   success/SCRR는 요구하지 않도록 한다.
5. **완료:** Source/offline artifact
   `reports/live-pilot/artifacts/d085-condition-neutral-comparison-pilot-source-gate.json`을 봉인한다.
6. **완료:** Source commit 뒤 clean Docker host에서 fresh official pricing으로 no-call preflight를 수행했다.
7. **완료:** Candidate execution hash와 최대 `$8`를 별도 승인받아 정확히 한 번 실행했다.
8. **대기:** Qualified pilot 뒤 12-run `$20 → $88` cap을 별도로 결정하고 새 hash/승인을 준비한다.
9. **완료:** Pilot과 campaign source를 별도 clean commit으로 유지하고 raw commit equality가 아닌 D-083/D-084
   semantic exact tuple과 qualified readiness를 검증한다. Task success를 제외한 canonical admission hash를
   future campaign execution plan/hash에 결속하고 persisted qualification을 durable state에서 read-only
   재계산하는 exact consumer를 구현·검증한다.

### Historical gate status — source/offline implementation and single approved invocation consumed

- Worst-rate reserve `$7.3125`, source cap `$8`의 exact approval은 D-086이 봉인한 invocation에서 소비됐다.
- Pilot success predicate는 workflow readiness이며 hidden success나 SCRR가 아니다.
- Historical source artifact 자체에는 preflight/hash/live result를 소급 기록하지 않는다.
- Baseline, denominator, memory review/index, core와 `analysis_ready`는 계속 닫혀 있다.
- Exact `dev-no-memory-v5-20260730-r1` pilot-admission consumer와 qualified pilot evidence는 존재하지만 cap 변경,
  새 campaign preflight/hash/승인과 paid execution authority는 없다.
- Final offline verification은 focused 153/153, repository-wide 1,392 collected 중 1,385 passed/7 skipped다.
  Artifact SHA는 `sha256:8b60cb2e62a6259db29527a600712e95b36390a1c07da9fb66e6f1d7d16f51d2`이다.

## Historical offline runtime gate — D-084 condition-neutral comparison binding

목표: D-083 exact tuple을 source config에서 execution plan/hash, `RunManifest`, durable start/resume evidence,
budget diagnostic과 independent no-memory qualification까지 동일 identity로 연결한다. Provider 실행이나
memory/core 결과를 만들지 않는다.

### Ordered work items

1. **완료:** Exact future dev/core tuple만
   `condition-neutral-comparison-runtime-contract-v1`을 선택하고 purpose, ordered memory conditions,
   model/mode/retry/output, budget, memory allowance, V2/V5, prompt/tool hash, D-083 descriptor와 harness commit을
   execution hash에 결속한다.
2. **완료:** Nullable count의 exact D-084 profile을 `RunManifest`에 허용하되 partial null, purpose, condition,
   model, retry, output, budget, fault와 public-review sidecar drift를 거부한다. Historical 200k/250k,
   D-081 2.4M과 D-079 3M profile은 소급 변경하지 않는다.
3. **완료:** Runner start가 `condition-neutral-comparison-runtime-evidence-v1` bytes와 full CAS descriptor를
   `RunStarted`에 남기고 resume가 descriptor·bytes·expected document를 재검증하도록 한다.
4. **완료:** Budget diagnostic과 no-memory trace qualifier가 exact profile, approved plan,
   `comparison_runtime_contract`, `disabled_call_guard_contract`, pricing freshness와 no-memory boundary를
   독립 검증하도록 한다.
5. **완료:** Core 네 memory condition의 plan/manifest/offline start-resume 구조가 같은 budget을 받도록 하되,
   index identity가 hash-bound되기 전 preflight와 paid-call boundary를 fail closed한다.
6. **대기:** Frozen memory index와 raw/structured/selective condition별 leak-safe terminal qualification을
   구현·검증한다. 이 gate 전에는 96-run core를 실행하거나 qualified로 표현하지 않는다.
7. **완료:** Append-only artifact
   `reports/live-pilot/artifacts/d084-condition-neutral-comparison-runtime-gate.json`에 offline boundary를
   기록한다. Provider call/model cost는 0/$0이고 승인 execution hash는 없다.
   Final verification은 focused D-084 68/68과 repository-wide 1,304 collected 중 1,297 passed/7
   environment-dependent skipped다. Artifact SHA는
   `sha256:e7fb7b7e7e9dad3e6b31fb781f09151b940bf226bdd5876e5e75e472ff24b701`이다.

### Gate status — offline runtime support implemented; execution gates closed

- D-083 artifact SHA와 exact tuple은 immutable하게 유지된다.
- No-memory trace qualification support는 구현됐지만 실제 baseline run/result는 아직 없다.
- Core는 structural support만 있고 frozen-index identity binding과 memory-condition terminal qualification이
  없다. `CORE_MEMORY_RUNTIME_BINDING_PENDING`과 paid-call 거부를 유지한다.
- 기존 `$20`/`$150` cap 충돌, fresh clean preflight, exact execution hash와 사용자 비용 승인이 남아 있다.
- `analysis_ready=false`, comparison denominator, memory admission과 core closure는 유지된다.

## Historical offline freeze gate — D-083 condition-neutral comparison-budget policy

목표: Exact D-081 r3 public process evidence에서 hidden outcome을 사용하지 않고 동일 per-run comparison
budget policy만 append-only로 동결한다. 이 gate는 실행, baseline admission 또는 memory/core 권한이 아니다.

### Ordered work items

1. **완료:** Source scope를 exact D-081 r3로 제한하고 pyfakefs observed-prefix minimum 1,303,223을
   결속한다. D-080 historical minimum 1,815,619는 scope 밖이다.
2. **완료:** `1,303,223 * 1.2 = 1,563,867.6`을 100,000 단위로 올림해 1,600,000 total token을
   선택한다. Frozen pair는 model/tool `null`/`null`, wall 1,800초, output 25,000, retry 0이다.
3. **완료:** Worst-rate reserve `$7.3125`/run, `$87.75`/12, `$131.625`/18, `$702`/96을 기록하고
   기존 `$20`/`$150` cap을 변경하지 않는다.
4. **완료:** `comparison_budget_policy_frozen=true`와 live execution, comparison denominator, no-memory
   baseline, memory admission, core false를 분리한다. Completion guarantee와 hidden-driven tuning은 없다.
5. **완료:** Future dev/core source template과 `ExperimentSuite` selector를 exact frozen tuple로 맞추고,
   기존 `$20`/`$150` cap 때문에 preflight가 fail closed하는지 검증한다. Historical 250k와 D-081 2.4M
   계약은 그대로 보존한다.
6. **후속 완료:** D-084가 execution-plan runtime contract/evidence, RunManifest, budget diagnostic과
   no-memory qualification support를 별도 offline gate로 구현했다. D-083 자체 bytes와 당시 pending claim은
   수정하지 않는다.
7. **완료:** Append-only artifact
   `reports/live-pilot/artifacts/d083-condition-neutral-comparison-budget-freeze.json`을
   `sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88`로 봉인한다.

### Gate status — policy frozen; execution gates closed

- D-083 implementation은 provider call 0, model cost `$0`이다.
- D-081/D-082는 immutable calibration-only evidence이고 denominator에 들어가지 않는다.
- 기존 `$20`/`$150` cost cap, `analysis_ready=false`, no-memory baseline, memory admission과 core closure는
  유지된다.
- Final verification은 1,238 collected 중 1,231 passed/7 environment-dependent skipped, focused artifact
  9/9와 experiment contract 245/245다.
- 후속 D-084가 runtime support를 offline에서 닫았지만 paid/live/baseline/memory/core authority는 만들지 않는다.

## Historical result-seal gate — D-082 D-081 measured workflow readiness

목표: D-081의 exact r3 execution과 predeclared process gate를 immutable하게 봉인하고 workflow completion과
hidden correctness를 분리한다. Hidden failure를 agent 구현 실패나 재튜닝 권한으로 해석하지 않는다.

### Ordered work items

1. **완료:** Commit `b4c79242bb0a94eed50530116205323e78c7d21a`, execution hash
   `sha256:446b60568795c585856468064fa1aa11a9d85a8e8806e6c71b3b19ab1aa12579`, exact suite/schedule과
   four run identity를 고정한다.
2. **완료:** 4/4 terminal·qualified·official evaluator, exact-one disabled-call projection과 gate v2 pass를
   보존한다. Infrastructure/qualification/diagnostic/budget-terminal/terminal-loop confound는 0이다.
3. **완료:** Babel 1/4 success, HF Hub/Moto/pyfakefs hidden failure와 regression/scope/safety 4/4 pass를
   함께 기록한다. Task success는 gate predicate가 아니다.
4. **완료:** 111 model/175 tool, 1,929,316 token, 계산 비용 `$1.79426325`, 111/111 completed/exact request,
   truncation disabled, `store=false`, retry recovery 3/3, loop observation 50(pyfakefs 39)을 기록한다.
5. **완료:** Raw result/journal/final-event hash를 각각
   `sha256:f8a2cd25916290ae02e46b484519cc01dedbe50097326085524a88bb9b324f83`,
   `sha256:52626ba6d7e61bc293ce327f4bf190e3b4118b20a2efe4d9de09d8186ce6afdd`,
   `sha256:f5537479c3c1e8c150f9cbfec5238d99c882eff537006773af8d9ddf9f78c254`로 고정한다.
6. **완료:** Portable report path는
   `reports/live-pilot/generic-baseline-readiness-v2v5-20260803-r3.json`이다. Content hash는
   `sha256:2a8f650e73e01aed9d629290627999232ec6aebd1769d2179bc22f084ddbede2`다.
7. **완료:** D-082 documentation seal은 repository-wide 1,214 collected 중 1,207 passed/7
   environment-dependent skipped와 focused D-082 8/8을 통과했다. Seal 자체는 provider call 0,
   model cost `$0`이다.
8. **후속 결정:** `$1,047.60` theoretical 96-run reserve와 `$150` cap 충돌을 해결하기 전 comparison
   budget, no-memory baseline, memory admission 또는 core를 열지 않는다.

### Gate status — measured process gate passed; calibration exclusions remain

- D-081 실행은 정확히 한 번 완료됐고 계산 비용은 `$1.79426325`다. D-082 seal의 추가 provider call과
  model cost는 0/$0이다. 계산 비용은 billed invoice/free-tier charge 주장이 아니다.
- D-081/D-082는 calibration-only이고 `analysis_ready=false`, comparison denominator, no-memory baseline,
  memory admission과 core를 열지 않는다.
- 1/4 task success와 3 hidden failure는 descriptive outcome일 뿐 task-specific tuning이나 automatic rerun을
  승인하지 않는다.
- D-075/D-077/D-079/D-080 source, consumed identity, raw/portable artifact, original/derived gate는 immutable하다.

## Historical result-seal gate — D-080 D-079 live completion and projection correction

목표: D-079의 정확히 한 번 실행된 결과를 재실행하거나 원 artifact를 수정하지 않고 봉인한다. 실제
workflow completion, hidden task outcome과 gate aggregation defect를 분리하고, 앞으로 같은 exact-one
qualifier check를 안전하게 전달하는 sanitized projection을 검증한다.

### Ordered work items

1. **완료:** Execution hash
   `sha256:70bc29196115cc6b201a30587d6974d3a05607345d447cb3a9144b0920c09791`, source commit
   `66fefde373f75729eef0e68fecc2f56a9bb1c174`, run `run_606349c2c56342d4`와 raw result,
   journal, qualification, submitted diff identity를 hash-bound로 고정한다.
2. **완료:** Workflow completion과 task correctness를 분리한다. Run은 terminal·qualified·official
   evaluator에 도달했고 budget binding은 없지만 hidden acceptance 실패로 task outcome은
   `task_failure`/SCRR false다.
3. **완료:** Original gate false와 `call_guard_contract_passed=false`를 immutable하게 보존한다. Full
   qualification의 `disabled_call_guard_contract`는 실제로 exact 1/1 pass였으므로 false 원인을
   `qualification-summary-projection-mismatch`로 분류한다.
4. **완료:** Append-only correction
   `gcor_6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`를 raw result와
   qualification file/hash/source-evidence hash, correction harness commit
   `7e40e27446bcf011f700c219a96983e5670422f4`, cause, exact original/corrected gate와 claims boundary에
   결속한다. Semantic body hash는
   `sha256:6552d8277d70fba7f296b0aee837a8f497be8384cce7fea4521cb39de1e19861`다. Corrected gate true는
   process completion만 정정하며 original gate나 task outcome을 대체하지 않는다. Portable manifest는
   `reports/live-pilot/artifacts/d080-workflow-completion-gate-summary-correction.json`이다.
5. **완료:** Terminal qualification summary는 full checks를 campaign result에 복사하지
   않고 `qualification-gate-check-projection-v1`의 `schema_version`, `check_id`, `check_count`, `passed`만
   투영한다. Consumer는 outer key exact-one과 inner exact key set, exact schema/ID, strict integer count 1과
   boolean true를 요구해 absence, duplicate, extra, bool/float/string count, wrong ID/type과 tamper를 fail
   closed한다.
6. **완료:** Focused projection/tamper tests는 331 passed다. Repository-wide regression은 1,162 collected 중
   1,155 passed/7 environment-dependent skipped이고 Ruff, Python compileall, sanitized JSON parse와
   `git diff --check`도 통과했다.
7. **완료:** D-080 seal 작성과 검증은 provider call 0, 추가 model cost `$0`이다. 같은 D-079 ID/hash/run을
   재사용하거나 재실행하지 않는다.
8. **후속 결정:** Public completion evidence로 condition-neutral comparison budget 후보를 정하되, 한
   pyfakefs trajectory의 84-call 관찰값을 그대로 frozen population budget으로 승격하지 않는다.

### Gate status — derived process gate passed; task correctness failed

- Actual usage는 84 model/119 tool, 1,790,707 token, 856,559ms, `$1.81747785`다.
- Headroom은 token 1,209,293과 wall 6,343,441ms이고 budget terminal/blocked tool은 0이다.
- Durable qualification은 28/28이며 call-guard contract는 1/1 pass다.
- Original gate false는 immutable하고 derived corrected gate만 true다.
- Calibration-only, `analysis_ready=false`, comparison denominator, no-memory baseline, memory admission과
  core는 계속 닫혀 있다.

## Historical workflow-completion source gate — D-079 bounded pyfakefs probe

목표: D-078의 pyfakefs trace에서 유일하게 남은 model-call admission confound를 hidden correctness와
분리해 측정한다. Four-row readiness를 다시 돌리거나 hidden 결과에 맞춰 prompt/tool/context를 tuning하지
않고, exact 한 row에서 call-count censorship 없이 기존 workflow가 official evaluator까지 완료되는지를
관찰한다.

### Ordered work items

1. **고정:** purpose `workflow-completion-probe`, experiment ID
   `pyfakefs-workflow-completion-probe-v2v5-20260803-r1`, exact task
   `tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml`, `no_memory`, repetition 1을 사용한다.
2. **고정:** model/reasoning/tier, `SYSTEM_PROMPT_V3`, tool v2/context `phase-evidence-v5`, SDK retry 0,
   output 25,000, sidecar absent와 fault none을 유지한다.
3. **고정:** model/tool call limits는 `null`이고 `model-tool-observability-only-v1` 아래 사용량만 기록한다.
   Total token 3,000,000, wall 7,200초, exact-request token admission, loop, phase/idempotency,
   constrained-tool, Docker/network/evaluator와 cost guard는 계속 fail closed한다.
4. **완료:** `workflow-completion-runtime-contract-v1`과 trace evidence를 execution hash,
   manifest, runner start/resume 및 qualification에서 독립 결속하고, call-limit drift나 retained-guard
   완화를 거부한다.
5. **완료:** `workflow-completion-probe-gate-v1`은 1/1 exact identity, terminal, qualified,
   official evaluator와 zero infrastructure/qualification/diagnostic error, retained-guard integrity 및
   disabled-call-guard contract를 요구한다. Hidden acceptance와 SCRR는 gate predicate가 아니다.
6. **완료:** 당시 focused와 repository-wide offline regression은 1,182 collected, 1,175 passed/7
   environment-dependent skipped, Ruff, compileall과 `git diff --check`를 통과했다. Tracked source/docs를
   clean commit으로 만드는 source 단계에는 provider call, execution hash, 사용자 승인, run/result,
   measured usage/cost 또는 gate outcome이 없었다.
7. **승인 전 금지:** Clean no-call preflight에서 task/package/image/evaluator, SDK, fresh official pricing,
   exact prompt/tool/runtime와 randomized schedule을 결속한다. `$13.6125` reserve와 `$14` cap은
   authorization bound이며, 생성된 exact hash와 최대 `$14`에 대한 별도 명시적 승인 전에는 provider를
   호출하지 않는다.
8. **완료:** 승인 뒤 exact 한 row를 한 번 실행했다. Pass는 call-count censorship 없이 evaluator에
   도달했다는 뜻이고 correctness, memory effect 또는 fair comparison budget을 뜻하지 않는다. Failure도
   자동 재실행이나 task-specific tuning을 승인하지 않는다.
9. **완료:** Live 결과를 original artifact를 바꾸지 않는 별도 D-080 append-only seal로 기록한다.

### Gate status — historical source/offline closure; live result is sealed by D-080

- D-079는 calibration-only이며 `analysis_ready=false`, comparison denominator, no-memory baseline,
  memory admission과 core는 닫혀 있다.
- D-078의 r2 suite/hash/four runs/result/false gate와 consumed-ID guard는 immutable하다.
- Source config나 offline test pass는 provider capability, execution authority, measured completion 또는
  SCRR evidence가 아니다.
- `LoopDetected` event가 존재한다는 사실만으로 실패하지 않는다. Loop-control integrity가 통과하고
  retained guard 안에서 terminal/evaluator lifecycle이 완성되는지를 판정한다.
- Official standard pricing은 2026-08-02T16:35:25Z에 `$0.75/M` input, `$0.075/M` cached input,
  `$4.50/M` output으로 재확인했다. Offline verification의 provider call과 model cost는 0이다.

## Historical baseline-readiness gate — D-077 budget-only generic V2/V5 successor

목표: D-075에서 실제로 관찰된 HF Hub total-token과 pyfakefs model-call confound에만 동일한 headroom을
적용하고, 다른 model-facing/evaluator 변수를 고정한 새 four-row panel로 process readiness를 다시
판정한다. 이는 D-075를 재개하거나 hidden outcome에 맞춰 agent를 tuning하는 작업이 아니다.

### Ordered work items

1. **고정:** 새 ID `generic-baseline-readiness-v2v5-20260802-r2`, 기존 Babel/Moto/pyfakefs/HF Hub
   order와 dataset role, `no_memory` repetition 1을 사용한다.
2. **고정:** model/reasoning/tier, `SYSTEM_PROMPT_V3`, tool v2/context V5, SDK retry 0, output 25,000,
   tool 100, wall 1,800초, sidecar absent와 fault none을 D-075와 동일하게 유지한다.
3. **고정:** 변경은 model call 40→50과 total token 850,000→1,200,000뿐이다. 다른 drift가 있으면
   budget-only label을 버리고 별도 tuple로 versioning한다.
4. **완료:** Suite loader, execution plan, manifest, start/resume와 qualifier가 새 ID와 budget,
   exact task/runtime/package/image/evaluator/harness identity를 독립 재계산하고 tamper를 fail closed한다.
5. **완료:** Gate/report는 기존 `generic-baseline-readiness-gate-v1`과
   `analysis-report-v2`를 유지하고, 4/4 terminal·qualified·official evaluator 및 모든 confound 0을
   요구하되 task success는 요구하지 않는다. Calibration-only와 comparison/memory/core exclusion을
   유지한다.
6. **완료:** Offline executable gate를 통과한 tracked source/docs를 clean commit으로 만든다. 그 뒤
   `.env` 값을 출력하거나 provider를 호출하지 않는 preflight에서 Docker, pinned image/evaluator,
   SDK와 72시간 이내 pricing을 결속한 새 execution hash를 만든다.
7. **승인 전 금지:** 2026-08-02T13:11:37Z 공식 rate 기준 run당 `$5.5125`, four-row `$22.05`,
   cap `$23`은 authorization bound다. Exact hash와 최대 `$23`에 대한 명시적 사용자 승인 전에는
   provider call을 수행하지 않는다.
8. **완료:** 승인 hash로 새 suite를 정확히 한 번 실행하고 partial row 재실행 없이 original gate를
   판정했다. D-078 append-only decision/evidence seal이 결과를 기록한다.
9. Gate pass 뒤에도 comparison tuple/no-memory baseline은 별도 freeze decision 전까지 시작하지 않는다.
   Live hard restart/reclaim은 별도 reliability suite로 남긴다.

### Gate status — live gate failed; D-078 append-only seal

- D-075 r1 ID/hash/run/result/false gate와 consumed guard는 immutable하다.
- D-077 approval hash는 정확히 한 번 소비됐고 r2 experiment ID와 네 run은 immutable하다.
- 4/4 terminal·qualified, 3/4 official evaluator, error 0, budget-terminal 1로 original gate는 false다.
- HF Hub/Babel은 hidden fail, Moto는 SCRR, pyfakefs는 50 model-call guard로 evaluator 전에 끝났다.
- 총 1,998,084 token, 125 model/219 tool call과 `$2.1782655`를 사용했다.
- Readiness candidate ceiling은 completion guarantee나 frozen comparison budget이 아니었고,
  diagnostic 1/4 SCRR는 baseline 또는 memory-effect evidence가 아니다.
- Focused readiness matrix와 repository-wide 1,095-test 회귀가 통과했고 1,088 passed/7
  environment-dependent skipped였다. Ruff, compileall과 `git diff --check`도 통과했으며 provider call과
  model cost는 0이다.
- D-078 seal verification은 focused 11 passed와 repository-wide 1,099 collected,
  1,092 passed/7 environment-dependent skipped를 기록했다. Ruff, compileall, JSON parse와
  `git diff --check`도 통과했고 추가 provider call/model cost는 0이다.

## Historical baseline-readiness gate — D-075 exact generic V2/V5 contract

목표: D-074의 semantic rollback을 지키면서 generic V2/V5 runtime을 네 개의 diverse development
task에서 한 번 검증한다. Process readiness와 hidden correctness를 분리하고, 이 panel이 통과한 뒤에만
별도 comparison tuple/no-memory baseline freeze를 결정한다.

### Ordered work items

1. **완료:** exact suite ID와 ordered Babel/Moto/pyfakefs/HF Hub task를 사전 선언한다. 두
   development-validation role과 두 memory-development role을 원래 split 그대로 검증한다.
2. **완료:** model/reasoning/service tier, `SYSTEM_PROMPT_V3`, tool v2/context v5,
   `transport_max_retries=0`, output 25,000과 40/100/850k/1,800초를
   `generic-baseline-runtime-contract-v1` plan과 `generic-baseline-runtime-evidence-v1` trace CAS에
   서로 다른 representation으로 결속한다.
3. **완료:** suite, generated manifest, execution plan, start/resume와 qualification에서 task/order,
   prompt/tool hash, retry, budget, dataset/image/evaluator/harness identity drift를 fail closed한다.
4. **완료:** `generic-baseline-readiness-gate-v1`이 4/4 terminal·qualified·official evaluator
   completion과 infrastructure/qualification/diagnostic/budget confound 0을 요구하고 task success는
   요구하지 않도록 고정한다.
5. **완료:** 이 purpose를 calibration-only로 report에서 제외하고 comparison denominator와 memory
   admission을 항상 false로 둔다. Historical suite는 retry field를 serialize하지 않아 기존 hash와
   adapter behavior를 보존한다.
6. **완료:** clean commit에서 pricing freshness와 Docker/evaluator/task package를 no-call preflight로
   재검증하고 exact execution hash를 만든다. 이것은 실행 권한이 아니다.
7. **완료:** 사용자가 exact hash와 최대 `$16` invocation을 별도 승인해 four-row live panel을 정확히
   한 번 실행했다. Experiment ID, hash와 실패 row를 재실행하지 않는다.
8. **완료:** Hidden outcome에 맞춘 tuning 없이 panel을 검토했다. 네 row는 terminal·qualified였지만
   HF Hub total-token과 pyfakefs model-call confound 때문에 evaluator 도달이 2/4이고 gate는 false다.
   Babel과 Moto의 성공 및 descriptive 2/4 SCRR는 calibration-only로 보존한다.
9. Live hard restart는 별도 reliability suite/hash/approval로 다루며 baseline readiness blocker로
   두지 않는다.
10. **다음:** Budget-confound public evidence로 condition-neutral tuple을 새 decision/config에서
    선택한다. 50 model/100 tool/1,200,000 token/1,800초가 현재 evidence-based candidate지만
    completion guarantee나 승인값은 아니다. 채택 시 새 exact hash와 four-row readiness panel을
    별도로 승인·실행하고, 그 gate가 통과한 뒤에만 comparison tuple/no-memory baseline을 동결한다.

### Offline contract gate — passed; D-075 live readiness gate — failed

- Historical D-069~D-073 evidence와 immutable guards가 byte/history 관점에서 보존된다.
- Generic dev/core는 V2/V5이고 HF Hub V2 sidecar 또는 V10/V11 selector를 사용하지 않는다.
- 기존 21/50/250k template은 실행 불가 상태로 명확히 표시된다.
- Exact generic tuple과 diverse readiness panel, transport retry와 task-success-independent
  no-confound acceptance가 executable offline evidence로 통과한다.
- Clean-host preflight와 one-time provider four-row result는 확보됐다. 실제 비용은 `$1.76403675`이고
  original gate는 4/4 terminal·qualified, 2/4 evaluator, budget-terminal 2로 false다.
- Readiness live gate가 통과하기 전 어떤 candidate ceiling도 comparison budget으로 표현하거나 baseline을 시작하지
  않는다.
- Hidden failure에 따른 task-specific adaptive tuning 없이 별도 baseline freeze decision을 만든다.
- Live hard-restart 미실행은 별도 limitation으로 남지만 baseline 진행을 막지 않는다.

## Historical evidence-seal gate — D-073 D-072 live result closure

목표: 정확히 한 번 승인·소비된 D-072 live result를 raw artifact 변경 없이 hard-immutable set과
portable evidence에 seal한다. Readiness gate pass, recovery occurrence와 task correctness를 분리해
기록하고, structured rejection 0을 recovery success로 승격하지 않는다. Live hard restart는 별도 후속
fault exercise이며 이 closure는 baseline, memory admission 또는 core를 열지 않는다.

### Frozen sequence

| Order | Status | Work item | Acceptance evidence |
| ---: | --- | --- | --- |
| 1 | implemented, live contract exercised | `experiment-v2` explicit purpose와 exact suite shape | Wrong task/role/repetition/model/budget contract reject |
| 2 | implemented, r3 host accepted; clean-machine reproduction pending | Canonical task/private hash/digest environment preflight, durable approved plan과 live capability | Unapproved/hash mismatch/dirty Git/wrong package/private/image/stale price reject |
| 3 | implemented, interrupted-run recovery pending | Paid call 전 fsync하는 hash-chained campaign journal | Existing journal이 hard-crash 뒤 새 schedule 시작을 차단; 자동 resume은 미구현 |
| 4 | implemented, legacy artifacts preserved | Source-evidence-bound `trace-qualification-v1`/`v2`와 sanitized failure linkage | v1 artifact byte stability, v2 runtime/lifecycle/provenance binding |
| 5 | historical v1 evidence only | Babel #1042 `no_memory` r3 pilot | `run_3cb86f8d70094a11`, `evaluation_reached=true`, official SCRR pass; current v2 gate에는 부적격 |
| 6 | completed; task acceptance failed | Corrected v2 mini model-candidate diagnostic 1회, $2 cap | `run_4a9737ec91964dca`: telemetry, submission/evaluator lifecycle과 qualification pass; hidden acceptance fail |
| 7 | done (offline) | `phase-evidence-v3` rejected mutating-tool argument의 bounded next-turn rehydration과 qualification check | Exact candidate/reason, tamper/stale/v2 compatibility, generation-before-budget guard와 full regression 통과 |
| 8 | terminal inconclusive | R5 mini model-candidate diagnostic 1회, 새 hash/승인 | `run_0ad8676d42614fbf`: official task와 qualification pass, rejected/retry 0; 자동 재실행 금지 |
| 8a | completed (offline) | D-037 controlled diagnostic offline contract | V4 profile, first prepared candidate one-shot rejection, crash-safe no-mutation, exact next request, fail-closed qualifier와 529 passed/2 skipped broad regression |
| 8b | completed; immutable | Controlled r6 provider diagnostic 1회, $2 cap | `run_73f5aaf7328a4ea5`: controlled/verified retry 1/1, rejected action mutation 0, evaluator·official task·qualification pass |
| 9 | terminal failure; immutable | Fault-free mini development-validation campaign pilot r1 1회, $2 cap | `run_6993722014bf4e3b`: 20/20 telemetry, patch/check/final diff/REVIEW 완료; call budget 때문에 submission·evaluator 없음, qualification 21/22 |
| 9a | completed (offline) | Submission tail-call과 deterministic call/tool/wall next-generation terminal contract | 전체 조건 21-call, v2 세 reason·strict counter/duration/actor/terminal binding, tamper·historical non-reinterpretation, 21번째 허용/22번째 차단과 fully qualified agent-failure trace |
| 9b | completed; immutable | 새 r2 experiment/hash의 corrective fault-free pilot 1회, $2 cap | `run_afd5080a77a34995`: official evaluator와 qualification 23/23 통과 |
| 10 | completed; diagnostic only | Memory-development 6 task × 2회, `no_memory`, $20 cap | 12/12 qualified agent failure, evaluator 0/12; baseline·memory index source로 자동 채택하지 않음 |
| 10a | completed (offline) | D-048 durable investigation ledger, semantic replay와 corrective-tail admission | v1-v3 compatibility, CAS tamper fail-closed, recovery·qualifier 재계산과 full regression 607 passed/3 skipped |
| 10b | completed; immutable | 새 v4 development-validation pilot 1회, $2 cap | `run_d7207fbb06184dd3`: official evaluator, qualification 25/25, investigation evidence/lifecycle pass |
| 10c | completed; diagnostic only | 새 ID의 memory-development 6 task × 2회, `no_memory`, $20 cap | 12/12 terminal·qualified, evaluator 3/12, SCRR 0/12; 9 budget-confounded agent failure + 3 hidden task failure |
| 11a | completed (offline), no provider call | D-052 `phase-evidence-v5` token projection과 future 250,000-token contract | Pre/post-generation 5/4-turn projection, equality cutoff, read/search-only admission block, strict exact-request guard와 historical non-reinterpretation 검증 |
| 11b | proposal validated; admission deferred | Append-only failure review와 memory build | Budget-confounded 9개 제외; task failure 3개를 public evidence만으로 두 group에 결속. Tox 2회는 candidate rule 1개, Loguru는 causal uncertainty로 hold; no-memory completion 전에는 human approval/index build를 진행하지 않음 |
| 11c | completed; immutable live evidence | D-054/D-055 high-budget no-memory completion panel | Babel+Moto scope-compliant success 2/2, qualification 25/25·completion/headroom pass, budget error 0, `$0.15682575`; exact hash와 experiment ID 재실행 금지 |
| 11d | completed | Clean preflight와 separate live approval | Commit `59621ec`, Docker digest, SDK 2.47.0과 exact execution hash를 결속해 두 run을 한 번 실행 |
| 11e | completed; immutable diagnostic | 작은 memory-development no-memory budget pilot | 승인 hash `sha256:61a720...bdef4f`로 3/3 terminal·qualified. HF Hub만 token-bound, PDM/pyfakefs는 official hidden task failure, SCRR 0/3; baseline·memory index source로 사용하지 않고 재실행 금지 |
| 11f | completed (offline + Docker), live use not approved | D-056/D-057 opt-in tool v3/context v6 self-validation | Public-v2 profile + dedicated clean-image optional `run_probe`, current-diff `review_task`, v3 submission/source qualification, recovery와 v1-v5 byte-stability; 실제 Docker isolation E2E 3/3과 mock official-evaluator smoke 통과, 별도 승인 전 live/campaign 금지 |
| 11g | completed (offline), live use not approved | D-059 profile-bearing full agent probe lifecycle | Dataset 밖 `csv-quoted-newline@2` fixture에서 mock agent가 registered probe를 clean Docker image로 실행하고 그 event를 same-diff review에 인용한 뒤 official evaluator까지 완료; 전체 live qualification은 의도적으로 false |
| 11h | consumed once; original gate false; immutable | D-062 corrective no-memory pilot | 승인 hash `sha256:464a6...4031`; HF `run_0ccfc8fd359a4785`만 terminal 후 `QualificationFailureHalt`, PDM/pyfakefs not-started. 33 completed calls, 875,908 tokens, `$0.8408853`, exact-budget block, patch/evaluator 0; baseline·memory/core 제외, 재실행 금지 |
| 11i | completed (offline), no provider call | D-063 phase-evidence-v8 saturation-context correction | Six-replay saturation을 다음 context의 authoritative allowed actions에 반영하고 historical v7 rendering을 보존. Mock-only manifest, crash/resume reset E2E, independent saturation qualification과 representative v7 golden 통과 |
| 11j | consumed once; diagnostic pass; completion false; immutable | Separate V8 single live pilot | `run_45e3edc434d749f7`: qualification 30/30, saturation seq 101→patch seq 106→reset seq 110 pass. 14 review rejection 뒤 model calls 40/40에서 evaluator 전 종료; 659,373 tokens, 64 tools, `$0.6140766`; baseline·memory/core 제외, 재실행 금지 |
| 11k | completed (offline); no provider call | D-066 phase-evidence-v9 review-evidence correction | `review_evidence_validation=True` mock/no-experiment selector; passing current-diff checks와 final diff를 12-event window 밖에 pin, exact citable list와 `review-citation-error-v1`, active mutation epoch당 3회 rejection terminal guard, independent `review_evidence_context_contract`; focused 502 passed/2 skipped, full 872 passed/7 skipped, V8 semantics 보존 |
| 11l | consumed once; evaluator reached; original gate false; immutable | D-067 separate V9 completion pilot | `run_4c77b1102e224785`: 344,754 tokens, 21 model/36 tool, `$0.2880024`; no budget bind, official evaluator reached, hidden fail과 `task_failure`; original qualification 32/33, comparison·memory/core 제외, 재실행 금지 |
| 11m | completed (offline); no provider call | D-068 append-only V9 qualification correction | V9 pinned final diff를 request/source CAS와 exact integer sequence로 검증하고 float/bool/duplicate/sidecar tamper를 거부; `qcor_51b725...3c032` corrected qualification 33/33, original qualification/gate/outcome/SCRR 불변; current full 918 passed/7 skipped |
| 11n | completed (offline); no provider call | D-069 V10 public-coverage review gate | `public-review-contract-v2`, tool v5/context v10/runtime v4, Git-base anchor provenance, CAS-bound inspection/visible-check evidence, `task-review-v3`, partial REVIEW→IMPLEMENT, finish/recovery/qualification tamper gate; 971 collected, 964 passed/7 skipped, mock/no-experiment only, D-067/V1-V9 immutable |
| 11o | consumed once; original gate false; immutable | D-070 exact V10 single-task live pilot | `run_6cc69fc1170c4a44`: 28/28 completed exact-token responses, 667,553 tokens, 50 tools, `$0.671307`, no budget bind. Valid partial review 7/8 뒤 missing anchor와 unrelated citation 3회로 evaluator 전 agent failure; qualification 30/34. No-model `run_c07bb2e439a74380`도 exact diff hidden fail; baseline·memory/core 제외, 재실행 금지 |
| 11p | completed (offline); no provider call | D-071 structured coverage-rejection recovery correction | Exact v6/v11/runtime-v5; target-specific feedback, model request/response tool-call CAS와 active worker-claim mirror, first-rejection restart, same-worker second rejection/latest-feedback recovery, exact-anchor and batched multi-check evidence, refreshed diff→complete review→finish/evaluator E2E, dedicated qualifier/tamper and single-mutation assertions pass. D-070 raw artifact/qualification immutable; baseline·memory/core 제외 |
| 11q | consumed once; readiness pass; recovery inconclusive; immutable | D-072 V11 live-readiness contract and exact one-row invocation | Context/qualifier V11 helper 분리와 exact contract 뒤 hash `sha256:12fb0f...080d`를 한 번 소비. `run_e2132144a8774b05`: official evaluator, qualification 36/36, gate true; coverage rejection 0으로 recovery inconclusive, hidden fail/SCRR false. 862,327 tokens, 35 model/57 tool, `$0.841833`, no budget bind; 재실행·comparison·memory/core 금지 |
| 11r | completed; append-only seal; no provider call | D-073 consumed-ID hard seal and portable evidence | D-072 experiment ID를 hard-immutable set에 추가하고 승인 hash/run과 sanitized evidence를 `reports/live-pilot/dev-no-memory-coverage-rejection-v11-pilot-20260802-r1.json`에 결속. Raw result/journal/qualification/gate 불변; 17 rejected-patch retries와 saturation 17은 coverage rejection recovery가 아님. Focused 374 passed/1 skipped, full 1,018 passed/7 skipped; D-073 추가 model cost 0 |

D-063 final offline evidence는 관련 묶음 377 passed/2 skipped, repository 전체 822 collected,
815 passed/7 environment-dependent skipped, Ruff와 `git diff --check` 통과다. 실제 runner
`ToolReplayed` presentation을 qualifier가 처음 누락한 integration failure를 수정한 뒤 같은
crash/resume E2E와 전체 회귀를 다시 통과했다. D-062 source hash는
`sha256:53148b2b42e82ddcb6083b1b317df3c7f8598972ed61fac0f69c65c5acff4351`로
불변이며 provider call은 없었다.

D-064 exact live-contract 변경 뒤 repository 전체는 837 tests를 수집해 830 passed/7
environment-dependent skipped로 완료했다. 이후 exact execution hash를 한 번 소비한 live run은
618,370 input, 41,003 output, 총 659,373 token과 `$0.6140766`을 기록했다. 40 provider response는
모두 completed이고 input/total telemetry도 40/40 일치했다. V8 diagnostic과 trace integrity는
통과했지만 completion gate는 false다. 이 결과와 별개로 source-level consumed-ID seal과 portable
sanitized evidence를 회귀 테스트하며, task correctness나 memory 효과는 주장하지 않는다.
Post-run seal 전체 회귀는 839 collected, 832 passed/7 environment-dependent skipped로 통과했고
Ruff와 `git diff --check`도 통과했다.

D-066 당시 source change의 집중 회귀는 504 collected, 502 passed/2 skipped였고
repository-wide regression은 879 collected, 872 passed/7 environment-dependent skipped다.
D-068 correction source는 repository-wide 925 collected, 918 passed/7
environment-dependent skipped, Ruff와 `git diff --check`를 통과했다. Correction 생성·검증
중 provider call은 없었다. D-069는 뒤이어 requirement coverage를 public evidence만으로
표현하는 leak-safe V10 offline gate를 구현했다. Git-base anchor provenance, event/result CAS
semantic equality, canonical target rows, partial-review correction, finish recovery와 non-vacuous
qualification tamper를 포함한 repository-wide 회귀는 971 collected, 964 passed/7
environment-dependent skipped로 통과했고 Ruff와 `git diff --check`도 통과했다. Provider call은
없었다. 이 완료는 budget 증액, paid V10 run, memory admission 또는 core campaign을 자동으로 열지
않는다.

D-071 final offline evidence는 focused V11 7/7, V11/V10/qualification/viewer 묶음 43/43과
repository-wide 999 collected, 992 passed/7 environment-dependent skipped를 기록했다. Ruff,
Python compileall과 `git diff --check`도 통과했다. Provider call, execution hash 또는 model cost는
생성하지 않았고 D-070 artifact와 false gate는 그대로다.

D-072 offline contract는 위 D-071 수치를 새 source 변경의 회귀 수치로 재사용하지 않았다. 해당 work item은
`patchloop.agent.coverage_rejection`/`patchloop.evals.coverage_rejection` 의미 보존 분리와 exact
one-row suite·selector·qualification/report gate의 offline contract를 먼저 닫았다. Checked-in config의
`live_cost_approved=false`, `approved_execution_hash=null`, `pilot_run_id=null`은 source config 단독으로
실행 권한이 없다는 의미다. Offline test는 fake environment와 temporary root에서 synthetic hash와
approval branch만 검증했다. Final offline verification은
focused 322 collected, 321 passed/1 environment-dependent skipped와 repository 전체 1,022 collected,
1,015 passed/7 environment-dependent skipped를 기록했고 Ruff, Python compileall과
`git diff --check`도 통과했다.

이후 clean-host no-call preflight와 사용자 승인으로 execution hash
`sha256:12fb0fb8a02ffe464555bd23125fae18deb6e52e6b6448a482243c036cce080d`를 한 번 소비했다.
`run_e2132144a8774b05`는 797,862 input + 64,465 output = 862,327 token, 35 model call, 57 tool call,
369,385ms와 `$0.841833`을 기록했고 어떤 budget dimension도 bind하지 않았다. Official evaluator와
qualification 36/36, readiness gate는 통과했지만 structured coverage rejection이 0이라 recovery는
`inconclusive/rejection_not_observed`다. Regression/scope/safety pass와 hidden fail로 outcome은
`task_failure`, SCRR=false다. Rejected-patch retry 17/17, saturated context 17개와 post-saturation
`PatchApplied` 1회는 별도 runtime 진단이며 coverage rejection recovery를 증명하지 않는다.
D-073은 이 result/journal/qualification/gate를 수정하지 않고 consumed ID를 hard-immutable set에
추가하며 승인 hash/run과 portable evidence를
seal한다. D-072 suite/hash/run은 재실행하지 않으며 live hard restart와 memory/core는 자동으로 열리지
않는다. D-073 과정의 provider call과 추가 model cost는 0이다.

Order 9a의 final offline evidence는 571 collected, 569 passed/2 skipped, repository-wide
Ruff와 `git diff --check` 통과다. 이 gate에서는 provider call을 실행하지 않았다.

Order 11f의 D-056 당시 evidence는 Docker Desktop 4.83.0 / Engine 29.6.2에서 당시 source로
다시 빌드한 `patchloop-sandbox:py312`
`sha256:268495717da1396e3413ce6695063c9516202b4e38cb8042f2f181420b64e9c1`,
실제 격리 container E2E 3/3과 704 collected, 702 passed/2 skipped의 repository-wide
regression이다. 두 skip은 현재 Windows 환경에서 symlink/junction 생성 권한을 사용할 수
없어 건너뛴 fail-closed path test이고 Docker skip은 0이다. 비용 없는 mock smoke
`run_36f90bda91b94d42`는 official hidden/regression/scope/safety와
`self_validation_lifecycle`을 통과했다. 이 v1 task에는 probe profile이 없어
`probe_call_count=0`이고, 실제 probe 실행 경계는 위 Docker E2E가 검증했다. Ruff와
`git diff --check`도 통과했으며 provider call은 실행하지 않았다.

위 Order 11f 수치와 image는 D-061 전 historical evidence다. D-061은 exact-ID create와
pre-start `.Image` equality, trusted-parent/untrusted-child seccomp 경계를 추가했다.
현재 `patchloop-sandbox:py312`
`sha256:1144b4be9927ac5882401185c326003383630eac9db84102ee3d71c06e261cac`로
host Docker E2E 5/5를 통과했다. 그중 kernel test는 Python audit hook이 없는
subinterpreter에서 process spawn과 trusted-parent signal이 모두 `EPERM`인지 확인한다.
전체 회귀는 731 collected, 724 passed/7 environment skipped이고, 다섯 Docker skip은
sandboxed test context에서 daemon을 사용할 수 없어서 host에서 별도로 실행한 항목이다.

Order 11f acceptance는 다음 논리곱이다.

```text
tool_schema_version=v3 AND context_policy_version=phase-evidence-v6 are explicit opt-in
AND LocalSandbox cannot execute agent-authored probe code
AND only task-public-v2 registered profiles can invoke a probe
AND task evaluator images are never used for agent-authored probes
AND AST/audit early rejection is not treated as the hard security boundary
AND trusted-parent seccomp denies child fork/clone/exec and parent signal/trace
AND mutable tag precheck, immutable-ID create and pre-start container image verification pass
AND dedicated-image digest and exact Docker policy are manifest/trace bound
AND Docker probe is readonly/networkless/proxyless/secretless and leaves no repository file
AND probe is optional and never substitutes for registered checks
AND review_task cites current-diff public evidence visible in its exact request
AND finish_task sees the same-diff untruncated canonical review body
AND later same-diff validation invalidates the prior review
AND private/hidden/reference/evaluator evidence never enters probe or review context
AND crash/recovery creates no duplicate probe, review or submission lifecycle
AND qualification/source-evidence tamper tests and v1-v5 historical stability pass
```

Order 11g의 추가 evidence는 비용 없는 final CLI run `run_7e3c5af2ce8d498a`다. Agent는
7 model/7 tool call로 registered `quoted-newline-case`를 선택했고, probe event 33의
`probe-ok` stdout과 exact clean-image binding을 review의 targeted validation과 requirement
evidence에 인용했다. 제출 뒤 official hidden/regression/scope/safety와 전용
`self_validation_lifecycle`이 통과했다. 전체 suite는 708 collected, 706 passed/2 Windows
symlink-capability skipped이고 Docker skip은 0이다. 동결 dataset audit은 기존 manifest
hash와 25 task/candidate 0을 그대로 유지한다. Mock/non-campaign run의 전체 qualification은
19/26으로 false이므로 live provider qualification이나 public/private campaign leak gate가
통과했다고 표현하지 않는다.

이 gate는 구현·offline evidence만 닫으며 paid/live 실행을 승인하지 않는다. 통과 뒤에도
future v3/v6 pilot은 frozen comparison budget과 섞지 않은 별도 suite, clean hash, 비용
검토와 명시적 승인이 필요하다. 기존 D-055 다음 provisional 3-task no-memory panel은
v2/v5 계약을 유지하며 D-056 때문에 암묵적으로 재작성하지 않는다.

Order 8의 첫 provider attempt에 사용한 terminal suite는
`experiments/dev-validation-gpt54mini-d037-r3.yaml`이다. Corrective attempt는
`experiments/dev-validation-gpt54mini-d037-r4.yaml`로 분리했다. 승인 hash에는
`experiment-diagnostic-v1` 요구가 포함된다. Post-run gate는
`evaluation_reached=true`, `retry_episode_count >= 1`,
`verified_retry_count == retry_episode_count`, `failed_source_failure_sequences == []`를
요구한다. Evaluator에 도달했지만 rejection이 발생하지 않으면 일반 qualification이나 task
outcome을 실패로 바꾸지 않고 diagnostic `inconclusive`로 종료한다. Evaluator 미도달은
diagnostic failure다.

승인 execution hash
`sha256:c33a50abe48b554c37d95de4833d1d17ede816f4d128b9adc22e88c010e138e6`는
r3 `run_e90f7c52aa134182`에서 정확히 한 번 사용됐다. 8 model call의 input pre-count는
모두 provider usage와 일치했지만 event 55가 per-call 4,096 output token을 모두 사용하고
`incomplete/max_output_tokens`로 끝났다. 전체 사용량은 60,930/90,000 token이고
mutation·rejected candidate·submission·evaluator는 0이다. Qualification은
`prompt_token_integrity` 한 항목만 실패했고 suite diagnostic은
`failed/qualification_not_passed`다. 이 결과는 D-037을 검증하거나 반증하지 않으며 r3를
재실행하지 않는다.

Corrective r4는 official
[reasoning guide](https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning)의
초기 권고에 따라 per-call 25,000 token과
전체 120,000-token budget을 `d037-rejected-patch-retry-v2` profile에 함께 고정한다.
2026-07-29 suite rate로 계산한 conservative preflight reserve는 `$0.6525`로 $2 cap
아래다. 일부만 바꾼 suite는 schema validation과 post-run approved-plan qualification에서
거부한다. Post-run qualifier는 schedule과 Git/Docker/SDK/pilot-qualification 입력을
포함한 execution hash도 다시 계산한다. Historical mini 4,096/90,000과 Terra/core
계약은 유지한다. Published
[mini model limits](https://developers.openai.com/api/docs/models/gpt-5.4-mini)의
128,000 max output 안에서 선택한 값이다.
단순 incomplete-response `continue`는
`ModelCalled` 경계가 rejected candidate의 immediate-next-request 계약을 무효화할 수 있으므로
도입하지 않는다. Provider retry를 나중에 추가한다면 original request artifact identity,
logical-turn/attempt correlation, 최대 횟수, crash ambiguity와 qualification pairing을
별도 hash-bound 계약으로 구현한다. R4 suite는 full regression을 통과한 뒤 clean
execution hash
`sha256:bbb6dbdcab1c7561c868ae4cc40478d6e3401c5900feb59b8ea09ef38d9156a1`로
정확히 한 번 실행됐다. `run_826c1c7fb3d242c2`의 13개 generation은 모두 completed이고
input pre-count도 13/13 일치했다. Patch 1회, visible check pass와 final diff 뒤
`REVIEW`에 도달했지만 14번째 request의 exact input 8,583 + output allowance 25,000이
남은 28,563 token을 5,020 초과해 provider generation 전에
`MODEL_GENERATION_BUDGET_EXCEEDED`로 끝났다. 제출·evaluator·rejected candidate·retry
episode는 0이다.

Qualification은 21/22다. 유일한 failed check `prompt_token_integrity`에는 mismatched
model event가 없으며, 실패 원인은 retry candidate가 없는 generic terminal budget block을
현재 `phase-evidence-v3` validator가 valid terminal block으로 인정하지 않는 점이다.
따라서 r4는 r3의 incomplete-response confounder를 제거했지만 D-037을 검증하거나 반증하지
않는다. R4 suite/run은 재실행하지 않는다.

D-041은 Order 8의 후속 r5를 `d037-rejected-patch-retry-v3`로 고정한다. Runtime의 strict
exact-input + full 25,000 response reservation 의미는 바꾸지 않고 diagnostic-only total을
200,000으로 둔다.

```text
91,437 r4 prefix
+ 3 × (10,031 largest observed exact input + 25,000 allowance)
= 196,530
→ rounded frozen budget 200,000
```

새로 생성되는 exact-request terminal block만 `model-generation-block-v1` payload를 사용한다. Request,
recomputed budget와 terminal result가 결속된 versioned generic block은 retry candidate가
없어도 valid trace evidence지만 D-037 episode나 gate pass는 아니다. Historical unversioned
r4는 qualification 21/22로 그대로 보존하며, historical unversioned retry block은 읽기
호환한다. R5는 synthetic rejection, runtime semantic change와 automatic retry를 추가하지
않는다. Evaluator에 도달했지만 zero-episode이면 inconclusive로 끝내고 자동 재실행하지
않는다. Conservative authorization reserve는
`(200,000 + 25,000) × $4.50/M = $1.0125`로 $2 cap 아래다. 이 계약은 targeted 191 test,
full 504 passed/2 skipped와 Ruff로 통과했다. Order 8은 새 experiment/hash 승인 아래 실제
retry predicate를 요구했지만, 아래 r5는 zero-episode로 terminal inconclusive가 됐다.

R5는 clean harness commit `a323bfe4bde46cb0e797a2c8eefacad3c2e8d7d1`과 승인
execution hash
`sha256:97249f05deda8e59118fdac0dd6f62f44c18b086ecb16bface2cc4d0f41a3a12`로
정확히 한 번 실행됐다. `run_0ad8676d42614fbf`의 18개 generation은 모두 completed이고
input pre-count와 provider usage가 18/18 일치했다. 121,366 input + 9,913 output token,
계산상 `$0.135633`을 사용했으며 official hidden/regression/scope/safety verdict와
`trace-qualification-v2` 23/23을 통과했다. 그러나 rejected candidate, retry episode와
verified retry가 모두 0이어서 suite diagnostic은
`inconclusive/retry_episode_not_observed`다. 이는 task나 generic qualification 실패가
아니며 D-037을 검증하거나 반증하지 않는다. D-041 계약대로 r5는 자동 재실행하지 않는다.
Order 8의 live observation은 terminal이다. Order 8a의 controlled disposition과 broad
regression 뒤 r6는 commit `1333ab968e2f144b632c0cb5ca341ebd30e0ca4e`, execution hash
`sha256:d6a756dc69a7cf6e024d541b64a458a940ec41bdfeb3c403a3f01c539660e67b`로 정확히 한 번
실행됐다. `run_73f5aaf7328a4ea5`는 19/19 exact input telemetry와 completed response,
controlled rejection 1회, verified retry 1회, rejected action mutation 0회, official
hidden/regression/scope/safety와 qualification 23/23을 통과했다. 138,262 input + 13,800
output token, 계산상 `$0.1657965`를 사용했다. 이 controlled result는 자연 error recovery
rate나 memory 효과를 측정하지 않는다. D-045는 Order 9와 이후 primary campaign을 dated
mini snapshot으로 전환했다. 승인된 Order 9 r1은 patch/check/final diff/REVIEW까지 진행했지만
20번째 model call 뒤 `finish_task` turn이 없어 terminal failure가 됐다. 별도 postmortem
evaluator의 patch success는 원 run outcome을 바꾸지 않는다. Order 9a가 offline evidence를
통과해 future primary/development/core의 총 model-call 상한은 21회로 동결됐다. 이는
`finish_task` 전용 reserve가 아니며 모든 memory 조건에 동일하다. Order 9b r2는 한 번
실행돼 accepted pilot이 됐고, Order 10의 첫 12-run은 investigation-loop diagnostic으로
보존한다. Order 10b의 새 v4 pilot도 accepted됐으며 Order 10c의 별도 12-run v4 campaign은
terminal diagnostic으로 완료됐다. Runtime policy를 바꾸기 전에는 새 paid gate를 열지 않는다.

Memory-development와 core future live suite는 `gpt-5.4-mini-2026-03-17`, reasoning
`medium`, mode `standard`, service tier `default`, 25,000 max output token,
`21 model call / 50 tool call / 250,000 total token / 900초`를 고정한다.
D-031 telemetry의 historical development-validation provider pilot r1~r3는
`gpt-5.4-mini-2026-03-17`, medium, default tier, per-call output 4,096과 run total
90,000 token을 허용한다. Corrective r4만 diagnostic profile v2와 함께 25,000/120,000
pair를 허용하고, 후속 r5 profile v3와 controlled r6 profile v4만 25,000/200,000 pair와
`model-generation-block-v1`을 허용한다. 이 historical diagnostic lane은 primary pilot
purpose를 충족하지 않는다. Dataset hash는
`sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`다.

Preflight는 frozen dataset role/hash, manifest의 canonical task path, public/private hash와
base commit, task별 digest-pinned environment/observed Docker image, clean Git commit, SDK와
API key 존재 여부, custom base URL 부재, 72시간 price age, official rate와 budget reserve를
검사한다. Checked-in config는 승인 권한을 갖지 않는다. `--approve-live-cost`와 preflight가
출력한 exact `--approved-execution-hash`를 실제 실행 invocation에 다시 제공해야 한다.
Paid runner는 승인된 execution plan을 durable하게 저장한 뒤에만 capability를 받는다.
Campaign과 row start journal event는 model call 전에 append, flush, fsync되므로 hard crash 뒤
같은 experiment를 자동으로 다시 시작하지 않는다. 중단된 journal의 자동 resume은 후속
work item이다.

Qualification은 필수 event의 content-addressed artifact reference와 usage/cache 불변식을
검사하고, plan/manifest/events/checkpoints/result/artifact inventory를
`source_evidence_hash`로 결속한다. Development campaign preflight, human review와 index
build는 현재 source hash를 다시 검증한다.

D-031 이후 새 live trace는 exact logical Responses request와 context-policy omission/truncation
evidence를 `ContextBuilt` CAS artifact에 보존한다. 각 turn은 input-token count endpoint의
exact count와 생성 응답 `usage.input_tokens`를 대조하고 `truncation=disabled`, completed
status, incomplete reason 없음과 total/reasoning token 불변식을 qualification에서 검사한다.
기존 r1~r3는 새 telemetry가 없는 immutable legacy evidence이며 새 필드를 소급 생성하지 않는다.

### 2026-07-29 model-candidate pilot corrective gate

`run_d4fea5e7198b4abc`는 mini dated snapshot, medium, 90,000-token 계약으로 실행돼
exact prompt-token telemetry를 남겼지만 `VERIFY → DONE` 전이 오류로 evaluator 전에
끝났다. 이 terminal run과 qualification은 수정하지 않는다.

당시 D-033 harness change는 새 non-replay manifest를 `tool_schema_version=v2`와
`context_policy_version=phase-evidence-v2`로 생성했다. D-037 이후의 새 non-replay
manifest는 tool v2를 유지하고 context만 `phase-evidence-v3`로 올린다. Current worktree diff에 결합된
최신 visible check, 그 뒤의 `get_diff`, complete/untruncated result가 다음 request에
포함됐다는 evidence와 `finish_task`를 제출 gate로 사용한다. 두 번의 recoverable
submission rejection, 세 번째 `premature-stop`, 성공 뒤 phase 전이, structured patch
error, advisory repeat signal, current-diff checkpoint와 viewer lifecycle을 offline test로
검증했다. 기존 v1 replay와 r1~r3 및 mini r1 trace는 그대로 유지한다.

이 corrective gate는 clean harness commit
`ff33d18a520de6fd8949ce9d873e26241b4382ae`, 별도 승인 execution hash
`sha256:fc2649790241f9623ea259a05957a38d1063472a9f17998e9e489b5b3fad21ca`로
정확히 한 번 live 재검증했다. R2 `run_4a9737ec91964dca`는 final check, complete diff,
structured `finish_task`, evaluator receipt와 `trace-qualification-v2` 22/22 check를
통과했다. 10번의 input-token pre-count도 provider usage와 모두 일치했고 truncation이나
incomplete response는 없었다.

그러나 official hidden acceptance가 실패해 task success는 아니다. 첫 patch는 잘못 붙은
marker 때문에 거부됐는데, `store=false`/provider-state 미사용인 다음 request는 그 patch의
content hash와 structured error만 포함하고 raw candidate body는 복원하지 않았다. 따라서
stateless retry continuity는 보장되지 않았다. 이후 제출된 별도 candidate에는 공개
계약만으로 확인 가능한 grouping/separator 제거 결함이 있었다. Trace는 body 누락이 hidden
failure를 일으켰다거나 첫 candidate가 통과했을 것이라는 반사실을 증명하지 않는다.
Provider prompt cut은 관찰되지 않았고, 별도로 PatchLoop context-selection gap은 남는다.
Terminal r1/r2 suite와 run은 재사용하지 않는다. 당시 다음 paid 실행 전에 rejected mutation
candidate의 bounded/hash-bound body와 rejection reason을 다음 turn에 함께 제공하고 이를
offline qualification과 suite-specific machine gate로 고정한다. 이후 새 experiment ID,
clean hash와 별도 사용자 승인을 받아 mini diagnostic을 다시 실행한다. Mini 결과는
성공하더라도 당시 Terra pilot 선행 gate를 대신하지 않는다. D-045 이후에도 이 historical
diagnostic purpose는 새 primary mini pilot purpose를 대신하지 않는다.

그 후 commit `11a83c2cdff06978dc961e7b3b3c0caada3b386e`와 execution hash
`sha256:c33a50abe48b554c37d95de4833d1d17ede816f4d128b9adc22e88c010e138e6`로
r3를 한 번 실행했다. `run_e90f7c52aa134182`는 54,851 input + 6,079 output token과
계산상 `$0.06849375`를 기록했지만, 여덟 번째 response가 4,096-token cap에서
incomplete가 되어 patch나 evaluator에 도달하지 못했다. Input pre-count 8/8 일치로
provider input truncation은 관찰되지 않았다. Rejected patch가 0개이므로 D-037 exercise도
0개이며 `qualification_not_passed` diagnostic failure다. Terminal r3 suite와 run도
재사용하지 않는다.

그 뒤 commit `c820a5e6f7b18697fded15bfa8097297253c54b6`와 execution hash
`sha256:bbb6dbdcab1c7561c868ae4cc40478d6e3401c5900feb59b8ea09ef38d9156a1`로
r4를 한 번 실행했다. `run_826c1c7fb3d242c2`는 84,082 input + 7,355 output token과
계산상 `$0.096159`를 기록했다. 13개 response는 모두 completed였고 token count도
일치했지만, `REVIEW`에서 다음 generation을 위한 33,583-token reservation이 남은
28,563 token보다 커 provider 전에 차단됐다. Patch는 한 번 적용되고 visible check도
통과했으나 submission/evaluator/retry episode는 0이다. Terminal r4 suite와 run도
재사용하지 않는다.

후속 r5는 위 r4 prefix와 세 tail reservation에서 산출한 200,000-token budget,
25,000-token per-call allowance와 `$1.0125` conservative reserve를 사용해 clean
commit/execution hash와 별도 사용자 승인 아래 정확히 한 번 실행됐다.
`run_0ad8676d42614fbf`는 evaluator에 도달했지만 natural rejection이 발생하지 않아
inconclusive로 보존됐고 automatic retry하지 않는다.

2026-07-30T22:25:47Z에 다시 확인한 `gpt-5.4-mini` standard rate는 1M token당 input $0.75,
cached input $0.075, output $4.50이며 별도 cache-write rate는 게시되지 않았다. 90,000-token
pilot은 exact input과 full 4,096-token response allowance가 남은 budget 안에 없으면
generation을 시작하지 않는다. Preflight의 $0.423432 reserve는 strict 90,000-token
runtime bound에 한 번의 4,096-token output allowance를 최고 rate로 더한 운영상 안전
margin이다. Historical D-045 primary contract의 run reserve는 25,000/200,000에서
`$1.0125`, 12-run은 `$12.15`, 96-run은 `$97.20`이었다. D-052 comparison draft의 frozen
repository-rate reserve는 25,000/250,000에서 run당 `$1.2375`, 12-run `$14.85`, 96-run
`$118.80`이었다. D-054 completion calibration은 25,000/600,000에서 run당 `$2.8125`,
두 run `$5.625`, suite cap `$6`를 사용했다. 실제 두 run은 `$0.15682575`였고 D-055 시점까지
measured list-price 합은 `$5.138372625`였다. 아직 freeze되지 않은
12-run/core reserve는 이 D-055 시점 승인 합계에 넣지 않는다. Reserve는 spend나 invoice
prediction이 아니며 project-wide `$150` cap은 machine-enforced가 아니다. Runner는
suite별 `cost_limit_usd`만 강제한다.

### Historical evidence preserved; D-054 completion live gate passed

- 관련 unit/integration test와 Ruff가 통과한다.
- Approval 없는 `--preflight-only`가 API call 없이 execution hash와 blocker를 출력한다.
- 실제 환경에서 approval을 포함한 preflight가 `ready=true`다.
- 사용자가 $2 pilot을 별도로 승인한 뒤 historical r3가 `trace-qualification-v1`과
  `evaluation_reached=true` 당시 acceptance를 함께 통과했다.
- Consumed primary r2와 첫 12-run campaign은 immutable inspection 전용이다. 새
  tool-v2/context-v4 pilot `run_d7207fbb06184dd3`은 같은 primary mini model/budget과 새
  runtime-contract hash에서 official evaluator와 `trace-qualification-v2` 25/25,
  `investigation_evidence`·`investigation_lifecycle`을 통과했다. 자연 rejected-patch
  retry 1/1도 관찰됐지만 semantic replay와 tail admission block은 각각 0회였다.
  이 run ID만 새 campaign의 `pilot_run_id`로 사용한다. Pilot task success는 12-run
  baseline이나 memory 효과와 별도 outcome으로 보고한다.
- 새 12-run v4 campaign은 exact pilot commit의 clean detached worktree와 별도 $20 승인으로
  정확히 한 번 실행됐다. Execution hash
  `sha256:9befd0bf8b2eb7dbc25999786713581b4b6c95f2ad45df56e2f098a9252e5bac`는
  소비됐고 재사용하지 않는다.
- Campaign은 infrastructure/qualification/diagnostic error 없이 12/12 terminal이었다.
  144/144 executed request의 input count가 provider usage와 일치했고 semantic replay 26회를
  관찰했지만 tail admission block은 0회였다.
- SCRR 0/12, evaluator 3/12다. 아홉 exact-request budget failure는 memory rule과 baseline에서
  제외하고, hidden acceptance에 실패한 세 task failure만 두 semantic group으로 provisional
  review한다. Human review와 deduplication 전에는 index를 build/freeze하지 않는다.
- D-052는 `phase-evidence-v5`, 25,000 per-call output과 250,000 total-token budget을
  future suite에 고정했다. `requested_input_tokens` 우선/`None` fallback, 관찰 input
  최댓값 + 최대 positive consecutive growth, generation 전/후 5/4 turn,
  `remaining_tokens <= reserved_tokens` 경계와 read/search-only
  `token_tail_reserved` admission을 offline에서 검증했다. 이 cutoff는 nominal policy이며
  strict exact-request + full output guard와 completion non-guarantee는 유지한다.
- V5 schema는 `investigation-policy-v2`, `investigation-ledger-v2`,
  `investigation-tail-policy-v2`, `context-build-evidence-v5`,
  `tool-admission-blocked-v2`, `trace-source-evidence-v5`이고 qualification envelope은
  계속 `trace-qualification-v2`다. 이 change에서 provider call은 없었다.
- 21/200,000 계약으로 소비된
  `dev-validation-gpt54mini-campaign-20260730-r2`, `dev-no-memory-20260728`,
  `dev-validation-gpt54mini-investigation-v4-20260730-r1`,
  `dev-no-memory-v4-20260730-r1`은 immutable historical evidence다.
- Future template은 `experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml`,
  `experiments/dev-no-memory-v5.template.yaml`, `experiments/core.template.yaml`이다.
  Development template의 `pilot_run_id`는 아직 `null`이고 core embedding revision은
  freeze 전 marker이므로 둘 다 실행 gate를 열지 않는다.
- 세 task failure의 `memory-review-proposal-v1`은 campaign/source/patch hash와 함께
  leak-safe validation을 통과했다. Tox 두 repetition은 exception-origin state conflation
  candidate 하나로 deduplicate했고, Loguru source는 공개 증거만으로 acceptance 원인을
  특정할 수 없어 hold했다. Producer는 `maintainer-assisted`이며 PatchLoop agent의 automatic
  post-run self-review evidence가 아니다. 이 proposal은 human review history나 memory
  index도 아니다.
- D-054에서 memory admission을 의도적으로 뒤로 미뤘다. 실행되지 않은
  `dev-validation-gpt54mini-token-tail-v5-20260730-r1`은
  `superseded-unexecuted`이며 preflight가 실행을 거부한다.
- `experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml`은 승인된 exact hash로
  한 번 실행된 immutable evidence다. Babel과 Moto는 각각 8/11 model call,
  65,652/106,597 input token으로 official evaluator의 scope-compliant success와
  qualification 25/25를 통과했다.
- `no-memory-completion-gate-v1`은 두 run 모두 terminal·qualified이고 official evaluator에
  도달하며 infrastructure/qualification/budget terminal이 0일 때만 통과한다. Hidden/SCRR
  성공은 별도 결과이고 gate 필수조건이 아니다. 두 run 모두 480k token, 32 model call,
  80 tool call, 1,440초 안이면 후속 fair-budget 검토 입력이 된다. 이는 freeze의
  필요조건일 뿐 충분조건이 아니다.
- 다음 work item은 이 두-task 결과를 직접 일반화하지 않고, memory-development의 작은
  no-memory 표본에서 후보 budget과 completion을 새 suite/hash/승인으로 검증하는 것이다.
  Memory human admission과 group-aware builder는 그 baseline 결과 뒤에 재개한다.
- Hard-crash journal을 안전하게 inspect/resume하는 절차는 아직 exit gate를 통과하지 않았다.

2026-07-28 첫 paid pilot `run_c6f13dd9a1a1472d`는 ready preflight 뒤 `$0.34025875`를
사용했다. 20 model call과 22 tool call 동안 agent가 `*** Begin Patch` envelope를 반복해
mutation 8회가 거부됐고, input 73,730 + output 7,326 token으로 80,000-token budget을
넘겨 submission 전에 종료됐다. Evaluator는 실행되지 않았고 qualification은 false다.
Agent failure와 별개로 qualification의 유일한 failed check는 leak scanner였다. 41 match는
API key가 아니라 공개 contract의 `.patchloop-hidden` marker
20건과 public task ID에 포함된 hidden-check 문자열 21건이었다. 기존 trace와 qualification은
수정하지 않으며, failed-tool feedback과 patch-format 안내 및 공개 marker filtering을
고친 새 commit/hash에서 별도 승인된 pilot로 exit gate를 다시 평가한다. 첫 model
candidate를 내용 변경 없이 raw Git diff로 변환한 사후 진단 patch
`sha256:4c49b6edd0603f2e56c04c18e83fdecb3a6a5868ab40bffca198504951b01606`는
official evaluator run `run_4299e6b326de4c1c`에서 모든 verdict를 통과했다. 이 run은
format-only counterfactual evidence이며 agent success나 pilot repetition으로 집계하지
않는다. 이 문단은 첫 Terra r1 당시의 경계를 설명한다. 이후 첫 12-run campaign은
실행됐지만 evaluator 도달 0/12의 D-048 diagnostic evidence로만 보존한다.

두 번째 paid pilot `run_de8f2a2846044c01`은 별도 승인 hash
`sha256:c7fe89287ed3310885f548954917c810b699a54ea420b3a7551d9863ebd839a3`로
정확히 한 번 실행됐고 `$0.328036875`를 사용했다. 19 model call과 22 tool call,
111 event와 23 checkpoint가 보존됐으며 leakage match는 0이다. Trace qualification
artifact 자체는 `qualified=true`지만 `evaluation_reached=false`이므로 pilot acceptance는
실패한다. Agent가 낸 아홉 patch candidate(고유 7개)는 모두 hunk header에 old/new 7줄을
선언하고 실제 body는 6줄만 포함했다. 실행된 여덟 mutation은 `corrupt patch`로 거부됐고
evaluator는 실행되지 않았다. 선택한 원문 patch
`sha256:f041469f1d938452c6e25c54aa1e6b816247be0525920184a77be493f7111695`는
strict `git apply --check`에서 실패하고 `--recount` check에서 workspace 변경 없이
통과한다. 이 parser diagnostic도 agent success나 repetition으로 집계하지 않는다.

r3 corrective gate는 agent-visible forward와 policy rollback에만 hunk recount를
적용했다. Raw input hash는 유지하고 body/context/path/policy는 strict하게 검사한다.
Policy reject 뒤 pre-call diff hash 복원, duplicate `PatchApplied` 방지와 zero-untracked
checkpoint/recovery를 executable test로 고정했다. Hidden evaluator는 strict하게 유지했다.

세 번째 paid pilot은 clean harness commit
`eeeeba6aa68e9d58677e2d8218381f79285f5545`와 별도 승인 execution hash
`sha256:03c57fb3dd0182e63645e346311ee2a46c1284d9770857240b2011b666b8bde6`로
정확히 한 번 실행됐다. `run_3cb86f8d70094a11`은 11 model call, 13 tool call,
43,963 input token과 1,547 output token에 `$0.16056875`를 사용했다. Recount gateway로
한 번의 `PatchApplied`를 만든 뒤 `babel/numbers.py` 한 줄만 바꾼 submitted patch를
제출했다. Official evaluator의 hidden, regression, scope와 safety가 모두 pass했고
`scope_compliant_success=true`, `outcome_kind=resolved`다. Qualification은 72개 연속 event,
15개 checkpoint, leakage 0, reconciled usage와 `evaluation_reached=true`를 검증했으며
qualification hash는
`sha256:5bc11b4087061921a415d94caeb0ac8370e39013f1d94a531130256fd3101811`,
현재 source evidence hash는
`sha256:f4726a1d6c2abfdf859c92135ae345dffb2075aaa9d5a7f0fc4fb7b1b0259322`다.
이 evidence는 당시 v1 pilot gate만 통과했으며, 현재 v5 pilot gate에는 재사용하지 않는다.
이후 실행된 첫 12-run campaign은 v4 이전 diagnostic으로 보존한다. 별도 v4 pilot과
12-run campaign도 D-049/D-051에서 한 번씩 소비됐지만 usable baseline을 만들지 못한
immutable diagnostic evidence다. 새 v5 pilot은 아직 실행하지 않았다.

## Phase 1. Evaluation Foundation

목표: Agent 없이도 submitted patch를 공정하게 판정하는 evaluator를 만든다.

### Ordered work items

| ID | Status | Work item | Depends on | Acceptance evidence |
| --- | --- | --- | --- | --- |
| P1.1 | done | Python package/CLI/test scaffold | 없음 | Offline unit test와 lint command 실행 |
| P1.2 | done | Public/private task Pydantic schema와 loader | P1.1 | Valid fixture load, path traversal reject |
| P1.3 | done | Audited sample Python repository와 patch fixtures | P1.2 | Reference와 6종 bad patch 보유 |
| P1.4 | done | Immutable checkout/workspace manager | P1.2 | Snapshot에서 매 run clean Git workspace 생성 |
| P1.5 | done | Docker sandbox policy와 registered check runner | P1.3, P1.4 | network 차단, non-root, read-only mount, host secret 비전달 검사 통과 |
| P1.6 | done | Hidden/visible test runner 분리 | P1.5 | Hidden asset는 evaluator workspace에 제출 후 복사 |
| P1.7 | done | Scope/dependency/tampering verifier | P1.3 | Known-bad patch별 expected boundary 거부 |
| P1.8 | done | Run manifest, verifier result, artifact writer | P1.2 | Schema-valid JSON과 SHA-256 object 저장 |
| P1.9 | done (local + Docker) | `patchloop eval-task` end-to-end | P1.6~P1.8 | Reference 성공, bad fixture 전체 실패, Docker 결과 `official=true` |

### Exit gate

```bash
patchloop eval-task tasks/dev/task_001
```

- Reference patch는 SCRR 구성 verdict가 모두 pass다.
- No-op, regression, forbidden path, dependency, tampering fixture는 의도한 verifier에서 fail한다.
- 두 번 실행해 verdict가 동일하고, manifest가 허용된 변동(timestamp/run ID)을 제외하면 재현 가능하다.
- Hidden content가 agent-visible workspace와 output에 없다.

## Phase 2. Minimal Coding Agent

목표: 제한된 tool로 간단한 task를 제출하고 완전한 trace를 남긴다.

### Work items

- Provider-neutral model adapter와 deterministic mock/replay adapter
- `search_files`, `read_file`, `apply_patch`, `run_check`, `get_diff`
- Structured `finish_task` orchestrator action과 current-diff submission gate
- Tool schema/policy gateway와 action identity
- Basic ReAct loop와 stop/budget policy
- Model/tool event logging과 usage accounting
- Agent submission을 Phase 1 evaluator로 전달하는 end-to-end path

### Exit gate

- Mock/replay agent로 offline smoke run이 가능하다.
- 간단한 task에서 valid patch를 제출한다.
- 모든 model/tool call과 failure가 ordered event로 저장된다.
- Budget 초과와 invalid tool argument가 구조화된 failure로 종료된다.

## Phase 3. Structured State Machine

목표: 실행을 evidence-gated phase로 만든다.

### Work items

- `INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE`
- 허용된 backward transition과 invalid transition guard
- Phase별 required artifact schema
- Context builder와 remaining-budget section
- Runner-owned durable checkpoint와 agent-visible `finish_task` orchestrator action

### Exit gate

- Evidence 없이 phase를 건너뛸 수 없다.
- `VERIFY` 실패 후 `IMPLEMENT`로 돌아갈 수 있다.
- `DONE`과 evaluator outcome이 명확히 분리된다.
- 모든 phase artifact가 contract를 만족한다.

## Phase 4. Persistence and Recovery

목표: Context 또는 worker가 사라져도 중복 mutation 없이 작업을 재개한다.

### Work items

- Append-only event store와 monotonic sequence
- Durable checkpoint와 artifact store
- Stable action ID/input hash, patch idempotency
- Recovery reconciliation과 worker resume
- Context-reset, worker-restart fault injector
- Duplicate/repeated-work metrics

### Exit gate

- `PatchApplied` 직후 worker를 종료해도 동일 run ID로 재개한다.
- Patch와 완료 action을 중복 적용하지 않는다.
- Corrupt checkpoint/hash mismatch는 안전하게 fail한다.
- 정상/장애 run 모두 evaluator 결과까지 연결된다.

현재 executable evidence는 두 층이다. 기존 fault injector는 첫 durable patch checkpoint
또는 submission lifecycle event 뒤 cooperative `suspended` resume을 검증한다. 별도
subprocess E2E는 v2 raw patch와 pre/post intent가 durable해진 뒤 single-file smoke patch의
유일한 atomic postimage replacement와 outcome persistence 사이에서 실제 worker를 강제
종료한다. 살아 있는 동안 두 번째 process의 claim은 run을 변경하지 않고 거부되며, 종료 뒤
세 번째 fresh interpreter가 stale `RUNNING`을 같은 run ID로 reclaim한다. Recovery는 이미
적용된 patch를 다시 적용하지 않고 evaluator 성공까지 완료하며
`ToolCalled(apply_patch)=1`, `PatchApplied=1`을 보존한다. Multi-file partial을 포함한
pre/post/mixed/unknown-state, CAS tamper, policy rollback과 corrupt checkpoint는 별도 unit
test로 fail-closed를 확인했다.

Evaluator manifest/result/provenance와 verifier stdout은 atomic write와 CAS로 보존하고,
완전한 hash-bound evaluation receipt가 있을 때만 fresh process가 evaluator를 재실행하지
않는다. Receipt 이후 terminal finalize가 중단돼도 같은 evaluator 결과를 재사용하며,
failure classification을 포함한 terminal event/result/status는 한 SQLite transaction으로
닫힌다.

이로써 offline/local Phase 4 exit gate는 통과했다. OpenAI live run resume, 중단된 paid
campaign journal resume, frozen 30-run stress schedule의 process supervisor와
`persistent_state=off` arm은 별도 미구현 범위이며 이 결과로 완료됐다고 주장하지 않는다.

## Phase 5. Failure Taxonomy and Memory

목표: Development trace를 solution이 아닌 일반화 가능한 remediation rule로 변환한다.

### Work items

- Cause/symptom/evidence 기반 failure schema
- Timeout, forbidden path, repeated action 등의 deterministic classifier
- Human review queue와 audit state
- Versioned structured memory store
- Raw trace renderer와 structured renderer
- Metadata filter, semantic retrieval, rerank, threshold, token budget
- Memory index build/freeze command

### Exit gate

- Admitted `memory-development` task의 failure에서 reviewed memory entry를 생성한다.
- Calibration과 external acceptance trace는 memory source에서 거부한다.
- Reference patch·hidden test·정답 code가 memory에 포함되지 않는다.
- 관련 memory가 없을 때 empty retrieval을 반환한다.
- Frozen index의 content hash가 held-out run manifest에 기록된다.

## Phase 6. Core Evaluation

목표: 네 memory 조건을 고정된 harness와 예산에서 비교한다.

### Work items

- Experiment config와 condition matrix runner
- Seeded execution order와 repetition
- Same-repo/cross-repo split audit
- Calibration/external/stress headline exclusion audit
- SCRR, 비용, recovery, memory metric
- Paired comparison과 bootstrap confidence interval
- Task-level JSON/CSV와 analysis report
- Success/failure flip trace selection

### Exit gate

- No Memory, Raw Trace, Structured, Selective Structured를 같은 task/budget으로 실행한다.
- 12개 core held-out task를 condition당 두 번 실행해 96개 core run을 만든다.
- 세 sentinel stress 결과를 core aggregate와 분리한다.
- Raw result에서 report를 다시 생성할 수 있다.
- Task-level matrix와 confidence interval이 생성된다.
- Matrix가 불완전하거나 qualification-failed이면 `analysis_ready=false` diagnostic만 만들고
  headline, paired CI와 flip 결과를 억제한다.
- 모든 headline 수치가 raw row와 run artifact로 추적된다.
- Negative 또는 inconclusive 결과도 변경 없이 보고한다.

## Phase 7. Viewer and GitHub Demo

목표: 핵심 evidence를 빠르게 검토할 수 있게 하고 portfolio demo를 완성한다. 현재는
run trace 진단 subset만 구현됐고 comparison/dashboard 및 GitHub demo는 pending이다.

### Minimal viewer

- Implemented: Run list와 task/condition/status/cost
- Implemented: critical path, collapsed model turns와 raw event payload
- Implemented: Patch diff, checkpoint history와 raw verifier result
- Implemented: Retrieved memory event 표시
- Pending: structured failure-record view와 no-match summary
- Pending: Condition comparison과 task heatmap

### GitHub demo

- Issue import
- Audited result를 바탕으로 Draft PR 생성
- PR body에 patch, verifier summary, run/report provenance 연결

### Exit gate

- 대표 성공과 실패 run을 source event까지 추적할 수 있다.
- Viewer가 private test content와 secret을 노출하지 않는다.
- README의 demo 명령이 clean setup에서 재현된다.

## 2. Cross-phase definition of done

각 work item은 다음을 포함한다.

- Domain contract와 validation error
- Happy path unit test
- 대표 policy/error path test
- 필요한 integration test 또는 fixture
- Offline/mock 실행 경로
- Provenance/event/artifact evidence
- 관련 docs와 CLI help 갱신

테스트 통과만으로 완료하지 않는다. Boundary, reproducibility, failure observability도 acceptance에 포함한다.

## 3. Planned repository shape

필요해질 때만 디렉터리를 만든다. 빈 scaffolding을 한 번에 생성하지 않는다.

```text
patchloop/
├── agent/
├── models/
├── tools/
├── sandbox/
├── state/
├── verifier/
├── failures/
├── memory/
├── evals/
└── api/                  # Phase 7
tasks/
├── smoke/
├── dev/
├── heldout/
└── stress/
tests/
├── unit/
├── integration/
└── recovery/
experiments/
├── configs/
└── results/              # generated, retention policy 필요
ui/                       # Phase 7
```

## 4. Handoff template

Agent가 work item을 넘길 때 다음을 기록한다.

```text
Work item:
Implemented:
Contracts changed:
Commands run and results:
Artifacts/evidence:
Known limitations:
Next unblocked item:
```

## Historical result seal — D-088 D-087 no-memory readiness attempt

1. **완료:** exact D-087 hash를 clean commit에서 한 번 실행하고 12/12 terminal·qualified·settled를 수집했다.
2. **완료:** raw result/journal/plan, 12 qualification, 340 provider response와 341 input pre-count를 독립
   재검증했다.
3. **완료:** `$5.36842875` accrued, `$12.31149825` maximum committed, 12 reserve/settle와 held 0으로
   `$25` campaign cap이 non-binding임을 확인했다.
4. **완료:** AnyIO repetition 2의 1.6M per-run token ceiling 한 건을 exact readiness confound로 분리했다.
5. **완료:** portable D-088 seal과 local-evidence-independent hard-consumed guard를 구현했다.
   Final verification은 focused 74/74, repository-wide 1,478 collected 중 1,471 passed/7 skipped이며
   Ruff, compileall, JSON parse와 `git diff --check`를 통과했다.
6. **닫힘:** 11/12 official evaluator이므로 no-memory baseline, denominator, memory review/admission/index,
   core와 analysis는 열지 않는다.
7. **다음 decision:** 동일 model/prompt/tool/context에서 per-run total-token policy만 바꾸는 별도
   condition-neutral readiness successor가 필요한지 결정한다. 이 decision 자체는 실행 권한이 아니며 새 ID,
   clean source, no-call preflight, execution hash와 비용 승인이 필요하다.

## Historical source gate — D-094 high-headroom diverse readiness panel

목표: D-093의 candidate를 재현 가능한 exact source contract로 만들되 provider 실행 권한은 계속 닫아 둔다.

1. **완료:** `generic-high-headroom-readiness-v2v5-20260804-r1`에 AnyIO, pyfakefs, HF Hub를 이 순서로 각
   1회 `no_memory` 배치한다.
2. **완료:** mini snapshot medium/standard/default, retry 0, prompt V3, tool v2, context v5와
   `null/null/3M/3,600s`, output 25k tuple을 exact experiment ID에 결속한다.
3. **완료:** 2026-08-04T14:47:00Z standard pricing으로 `$13.6125`/run, `$40.8375`/suite와 `$41`
   source cap을 기록한다.
4. **완료:** readiness를 3/3 terminal·qualified·accepted submission·official evaluator와 telemetry/process
   integrity로 정의하고 task success, hidden acceptance와 SCRR은 predicate에서 분리한다.
5. **닫힘:** source/offline 단계에는 preflight, execution hash, user approval, provider/evaluator call, baseline,
   denominator, memory admission/index와 core authority가 없다.
6. **후속 완료:** clean source commit의 no-call preflight와 max-`$41` exact-hash 승인은 D-095에서 한 번
   소비된 live invocation에만 속한다.
7. **검증:** focused 56/56과 repository-wide two-shard 1,627 collected 중 1,620 passed/7
   environment-dependent skipped, Ruff, compileall, exact rebuild, JSON/hash와 `git diff --check`가 통과했다.

## Historical result seal — D-095 D-094 measured high-headroom readiness

1. **완료:** source commit `82fbb33f20cabb57a151db871782345c6cafa3f0`에서 approved execution hash
   `sha256:ae54b9cc14e3bcb80cbead61a003012cec4dbd0e8a205917b3cefdeaf0c11d75`를 정확히 한 번
   소비했다.
2. **완료:** AnyIO `run_9fd10f7feeee4df5`, pyfakefs `run_7449597e84b94446`, HF Hub
   `run_9566c0367bd24f52`가 모두 terminal·trace-qualified·accepted submission·official evaluator에 도달했다.
3. **완료:** Persisted qualification 3개와 read-only recomputation, 84/84 qualification check, 63/63
   completed/exact-token/truncation-disabled/`store=false` response와 previous-response dependency 0을 확인했다.
4. **완료:** Budget, infrastructure, qualification, diagnostic, terminal-loop와 call-budget confound 0으로 exact
   workflow-readiness gate가 통과했다.
5. **관측:** 세 run은 모두 hidden fail, regression/scope/safety pass인 `task_failure`다. Task success와 SCRR은
   0/3이며 readiness predicate와 분리해 보존한다.
6. **봉인:** Raw result와 8-event journal, execution plan, 세 qualification과 public trace aggregate를 leak-safe
   portable report에 content-address하고 experiment ID를 hard-consumed로 만든다. Seal 자체 provider/evaluator
   call과 added model cost는 0/0/`$0`이다.
7. **닫힘:** 이 selected one-repetition panel은 calibration-only다. No-memory baseline, success-rate estimate,
   comparison denominator/resource freeze, memory review/admission/index, core, analysis와 hidden-driven tuning은
   열지 않는다.
8. **다음 decision:** 별도 offline gate에서 condition-neutral resource policy와 baseline admission을 결정한다.
   D-094 hash/run을 재사용하거나 자동 successor를 실행하지 않는다.
9. **검증:** focused/relevant 303/303과 repository-wide split 1,637 collected 중 1,630 passed/7
   environment-dependent skipped가 통과했다. File shard의 유일한 D-092 WAL/SHM order-sensitive invariant는
   isolated process에서 통과했다. Ruff, compileall, exact rebuild, JSON/hash와 `git diff --check`도 통과했다.

## Historical offline gate — D-096 condition-neutral resource policy and no-memory admission

1. **완료:** future comparison policy를 mini medium/standard/default, retry 0, prompt V3, tool v2,
   context v5, output 25k, memory allowance 2k와 `null/null/3M/3,600s`로 exact freeze했다. 네 memory
   condition에 동일하게 적용하는 prospective policy이며 finite safety ceiling이지 completion guarantee가 아니다.
2. **완료:** frozen memory-development 6개 task를 Loguru, AnyIO, tox, HF Hub, PDM, pyfakefs 순서로
   `no_memory` 각 2회 배치하고 seed `20260723`, expected row 12를 admission contract로 고정했다. 각
   `public.yaml` exact bytes/file SHA는 frozen manifest의 `public_spec_hash`와 일치해야 한다.
3. **완료:** Campaign admission은 12/12 terminal·qualified·cost-settled, persisted qualification read-only exact
   match, exact runtime/no-memory binding과 complete telemetry를 요구한다. Not-started, infrastructure,
   qualification, diagnostic, duplicate/replacement, unknown-terminal, model/tool-call-budget-block count는 0이어야
   하고 issued response는 전부 `completed`여야 한다. Terminal은
   accepted submission + completed official evaluator의 `resolved|task_failure` branch 또는 actor/CAS/pre-call/
   no-provider-after가 확인된 canonical token/wall budget `agent_failure` branch 중 exact-one이어야 한다. Task
   success와 hidden acceptance는 이 predicate가 아니며, official-evaluator task failure만 후속 leak-safe review
   대상 memory candidate가 될 수 있다.
4. **보존:** D-083/D-084 v1 runtime contract/evidence와 historical result는 수정하지 않는다. D-096이 선택한
   runtime contract/evidence v2는 아직 구현되지 않았고 D-087/D-095를 소급 baseline으로 admission하지 않는다.
5. **비용 blocker:** Conservative reserve는 `$13.6125`/run, `$163.35`/12 run이다. 현재 project cap `$150`보다
   `$13.35` 크므로 최소 정수 cap `$164` 이상의 별도 non-censoring cost policy가 정해지기 전
   `NO_MEMORY_AUTHORIZATION_CAP_PENDING`으로 fail closed한다. Rate와 reserve는 exact-bound D-094 pricing
   artifact block에서 직접 읽어 공식 formula로 재도출한다.
6. **열림:** Resource-policy freeze, baseline-admission contract와 future no-memory source authoring만 열린다.
7. **닫힘:** New suite/runtime binding, no-call preflight, execution hash, 사용자 비용 승인, provider/evaluator call,
   baseline result, comparison denominator, memory review/admission/index, core와 analysis는 모두 닫혀 있다.
8. **다음 gate:** Runtime v2를 execution plan·RunManifest·content-addressed start/resume·qualification에 결속하고
   새 exact 12-row successor suite와 non-censoring campaign cost policy를 작성한다. 그 뒤 clean no-call preflight,
   fresh pricing, 새 experiment ID/hash와 별도 사용자 승인이 필요하다.
9. **검증:** Focused D-096 contract 26/26과 관련 D-083~D-096 contract 178/178이 통과했다. Repository-wide
   1,663건은 1,656 pass/7 environment-dependent skip이며, shard 순서에 민감한 D-092 WAL/SHM invariant 1건은
   독립 프로세스에서 통과했다. Parsed exact artifact rebuild, 19,031-byte file SHA
   `sha256:5c032cff1045a39d1d8d9757205a920b1cd1cfd948c7c4e3e5b526ae6744661d`와 `git diff --check`도 통과했다.

## Current offline source gate — D-097 exact no-memory runtime-v2 successor

1. **완료:** 새 exact ID `dev-no-memory-condition-neutral-3000k-20260805-r1`에 Loguru, AnyIO, tox,
   HF Hub, PDM, pyfakefs를 이 source order로 `no_memory` 각 2회, seed `20260723`에 배치한다. Suite file은
   2,741 bytes, `sha256:7b3c217388e86a2760694e98031b7ac974c8c450075e3433ee977e35b344abb0`다. D-096
   source-identity hash `sha256:e399114a6ea516821a30104a612f7222c0caf3f88def7b5d7472d15f7cc4c27b`와
   shuffle 뒤 expanded schedule hash `sha256:dff4f38db99bcbc878e917a6c76e10a6c244701d2a8eb5ea4b43daf427a305ba`를
   별도 identity로 보존한다.
2. **완료:** D-096 profile의 mini model/prompt/tool/context/output/memory와
   `null/null/3M/3,600s`를 `condition-neutral-comparison-runtime-contract-v2`와 runtime evidence v2로
   versioning한다. Exact successor ID만 v2 selector에 들어가며 v1 global constant나 historical
   manifest/result/qualification은 수정하지 않는다.
3. **완료:** Runtime v2와 D-096 policy/admission CAS를 execution plan/hash, `RunManifest`, paid boundary,
   content-addressed `RunStarted`, fresh start/resume와 trace qualification에서 exact 재구성하도록 한다.
   Source artifact builder 자체는 runtime verifier가 아니며 executable tests가 이 wiring을 검증한다. Post-run
   reconciliation은 `CampaignCompleted`와 persisted result hash를 다시 결속하고 rehashed foreign/duplicate terminal
   event를 거부한다. 이는 evidence integrity이지 duplicate paid-call prevention 주장이 아니다.
4. **완료:** `campaign-list-price-full-schedule-reserve-v1`은 첫 provider call 전에 하나의 fsync된
   `FullScheduleCostReserved` event로 exact 12 rows, row별 `$13.6125`와 `$163.35` full reserve를 함께 결속한다.
   같은 plan/CAS/journal은 각 row 전에 재검증되고 terminal row마다 deterministic settlement가 기록된다.
   Prospective campaign-scoped source cap은 `$164`이고 cost censoring이나 cost 사유 `not_started`를 허용하지
   않는다. D-097은 per-row atomic SQLite capability를 구현하지 않고 live resume을 disabled로 유지한다. Cost
   journal은 duplicate paid-call prevention을 주장하지 않으며 기존 one-use execution hash가 authorization을
   단일 sequential invocation으로 제한할 뿐이다. 이는 completion guarantee,
   invoice/free-tier claim, historical project cap `$150` 변경 또는 사용자 예외 승인이 아니다.
5. **완료:** Baseline completion source predicate의 runtime output은
   `condition-neutral-no-memory-baseline-admission-gate-v2`다. Exact 12 terminal/qualified/cost-settled row와 두
   disjoint terminal branch를 요구한다. Official branch는 completed evaluator의 `resolved|task_failure`, budget branch는
   canonical pre-call total-token/wall `agent_failure`다. Task success·hidden acceptance·SCRR는 gate가 아니고
   budget/infrastructure failure는 memory candidate가 아니다. Future denominator gate가 통과하면 campaign-level
   `memory_review_eligible=true`가 되고 review candidate pool은 official task failure로만 제한된다. 별도
   review/dedup/leak gate 전에는 `memory_admission_unlocked=false`다.
6. **보존:** D-083/D-084 v1, D-087 cost source/result, D-095 readiness와 D-096 decision은 append-only
   historical evidence다. 새 suite는 어느 historical run도 v2 baseline row로 소급 승격하지 않는다.
7. **닫힘:** Source YAML은 `live_cost_approved=false`, `approved_execution_hash=null`, `pilot_run_id=null`이다.
   실제 clean preflight, candidate/approved hash, `$164`와 `$150` campaign exception 승인, provider/evaluator
   call, run/result, denominator, memory review/admission/index, core와 analysis는 모두 false다. Canonical blocker는
   `NO_MEMORY_CLEAN_PREFLIGHT_AND_164_USD_APPROVAL_PENDING`이다.
8. **다음 gate:** 이 change를 clean commit으로 봉인한 뒤 dataset/task/environment, Docker/evaluator image,
   SDK와 fresh official pricing을 다시 확인하는 no-call preflight만 수행한다. Preflight는 provider/evaluator를
   호출하지 않으며 exact candidate hash와 최대 `$164` 별도 승인 전에는 live 실행하지 않는다.
9. **검증:** Source artifact는
   `reports/live-pilot/artifacts/d097-condition-neutral-baseline-source-gate.json`, semantic body SHA
   `sha256:05d952065136a45914e2fb3c44edcbb553732c9f33484c5412b9135062c6481b`, 21,029-byte file SHA
   `sha256:21ed073ad1fbe1985e7a46cabebbfdc836baa303c4434e0777152c1d2d88a777`다. D-097 focused 65/65와
   D-084~D-097 관련 회귀 354/354가 통과했다. Repository-wide single run은 1,728 collected 중
   1,720 passed/7 skipped/1 failed, 655.4초다. 유일한 failure는 D-092 raw replay WAL/SHM order-dependent invariant고
   exact test는 즉시 isolated 1/1로 통과했다. 이를 monolithic 1,721/7로 보고하지 않는다. Ruff, compileall, exact
   rebuild와 `git diff --check`도 통과했다. D-097 source 단계의 provider/evaluator call과 added model cost는
   0/0/`$0`이다.

## Current group-admission mechanism — D-100

1. **완료:** Exact D-099 proposal file/body, 5 group fingerprint와 candidate 3개의 normalized rule hash를 source
   gate에 결속한다.
2. **완료:** `record-d100-decision`은 caller-provided action ID, explicit expected tail, global previous hash와
   group별 supersedes hash를 사용한다. 같은 action/input retry는 idempotent하고 stale tail과 action conflict는
   append 전에 거부한다.
3. **완료:** Canonical JSONL decision은 cross-process writer lock 안에서 append한 뒤 flush/fsync하고 전체 chain을
   다시 검증한다. Noncanonical/blank/partial-tail/reordered/hash-inconsistent chain과 leak-shaped reviewer/rationale는
   fail closed하며 decision과 descriptor는 동일 byte snapshot에서 계산한다.
4. **완료:** Candidate의 `approve`는 D-099 exact proposed-rule hash를 결속한다. Hold approve는 불가능하고 rule을
   바꾸려면 decision correction이 아니라 새 proposal revision이 필요하다.
5. **완료:** Effective decision이 5 group을 exact cover할 때만 one-approved-group-one-template preview를 만든다.
   Rule field는 verbatim, member order를 보존하며 source 수를 validation으로 과장하지 않고
   `validation_count=0`으로 둔다.
6. **완료:** Preview는 target schema만 지시하며 실제 `MemoryEntry.index_version`, embedding, frozen/index field가
   없다. 기존 failure별 review/build/freeze path를 import하거나 호출하지 않는다.
7. **닫힘:** User의 구현 요청은 group별 human approval이 아니다. Production decision journal, admission seal,
   admitted rule, preview entry와 index는 0/none이고 core/analysis도 닫혀 있다.
8. **산출물:** `reports/memory-development/d100-group-review-projector-source-gate.json`, semantic body SHA
   `sha256:5ac180b32fef27d5937c1447e39f01bafda65ce6b5a3eef1992a7da45cab9b2b`, 5,048-byte file SHA
   `sha256:866bad69dad24dd908339330f27a24a388e64b453e6dc403363836292ea24e47`다.
9. **다음 gate:** Exact group/fingerprint/rule hash와 journal tail을 제시한 뒤 사용자의 명시적 결정을 기록하고,
   complete decision chain과 preview를 exact head/count, journal file SHA와 explicit approval receipt를 가진 별도
   portable admission seal로 봉인한다. Index build/freeze는 그 뒤다.
10. **검증:** Focused 28/28과 related 154/154가 통과했다. Final repository-wide는 1,784 collected 중
    1,776 passed/7 environment-dependent skipped/1 failed다. 유일한 historical D-092 WAL/SHM order-dependent
    invariant는 isolated 1/1 통과했으며 D-100 pass/fix로 합산하지 않는다. Ruff, compileall, exact rebuild와
    `git diff --check`도 통과했다. D-077 pricing-freshness test는 test clock만 historical start instant로 고정했고
    production runtime/qualifier와 historical evidence는 바꾸지 않았다.

## Historical public review proposal — D-099

1. **완료:** D-098 exact candidate 9개와 PDM resolved 2개, AnyIO canonical budget terminal 1개의 12-row
   population partition을 다시 검증한다.
2. **완료:** Public task, agent-visible inspection artifact, submitted patch, registered visible-check summary,
   diff/review/submission lifecycle metadata와 generic task-failure outcome만 검토 근거로 사용한다. Qualification,
   source-evidence와 failure-record hash는 opaque integrity binding이지 causal evidence가 아니다.
3. **완료:** 9 source를 5 semantic group으로 exact partition한다. Pyfakefs/HF Hub/tox 3 group·6 source는
   candidate proposal, AnyIO/Loguru 2 group·3 source는 hold다. Hold에는 proposed rule을 넣지 않고 unresolved
   reason과 next review action만 둔다.
4. **완료:** 9개 submitted patch를 portable public artifact로 복사하고 D-098의 exact patch SHA/bytes와 결속한다.
   74개 selected event ref는 safe event-type allowlist, event hash와 content-addressed artifact로 raw snapshot에서
   검증한다.
5. **완료:** Portable validator는 `.patchloop` 없이 D-098 report, frozen dataset manifest와 public spec, patch
   copy, proposal self hash, group algebra와 leak scan을 검증한다. Raw mode는 명시적으로 요청해야 하며 copied
   SQLite/WAL만 사용하고 원본 DB/WAL/SHM fingerprint를 보존한다.
6. **닫힘:** Candidate proposal은 MemoryEntry가 아니다. Human admission pending, admitted rule 0, review history 0,
   `memory_admission_unlocked=false`, index/core/analysis closed다. 기존 failure별 `memory review/build` 경로에
   연결하지 않는다.
7. **산출물:** Semantic body SHA는
   `sha256:63c74999242f6217f2a81c9c2dc22d618d2be137948580f93401341c4ea49574`, 77,942-byte
   file SHA는 `sha256:24e34b02a66fc132d333bb51614a10786d38bc188b5550432a5f21f435f21493`다.
8. **다음 gate:** Semantic-group 단위 append-only human approval/rejection contract와 이 proposal을 직접 소비하는
   group-aware builder를 구현한다. 이를 완료하기 전 existing per-failure review history를 쓰거나 index를 만들지 않는다.
9. **검증:** D-099 focused 13/13과 historical memory/D-097/D-098 related 126/126이 통과했다. Repository-wide
   1,756 collected 중 1,749 passed/7 environment-dependent skipped/failure 0이며 Ruff, compileall, exact rebuild와
   `git diff --check`도 통과했다. Historical D-092 order-dependent issue가 이번에 재발하지 않았지만 D-099 fix로
   해석하지 않는다.

## Historical measured baseline seal — D-098 exact D-097 result

1. **완료:** Exact source commit과 one-use execution hash의 raw result, 39-event journal, plan, 12 persisted
   qualification과 per-run artifact hash를 read-only로 재검증한다. Original runtime artifact는 수정하지 않는다.
2. **완료:** Baseline-admission gate는 12/12 terminal·qualified·cost-settled, 11 official branch와 1 canonical
   pre-provider budget branch exact-one으로 통과했다. Infrastructure/qualification/diagnostic/cost-censor error는 0이다.
3. **측정:** Outcome은 2 resolved, 9 task failure, 1 agent failure다. SCRR 2/12와 task-first mean 1/6은 exact
   development baseline 관찰값이며 held-out·memory effect·CI가 아니다.
4. **측정:** 10,492,742 input + 881,967 output token, 613 model/964 tool call, 7,258,662ms와 usage-derived
   standard list-price `$11.838408`을 기록했다. 613/613 response는 completed이고 input telemetry가 일치했다.
5. **완료:** Official task failure 9개만 `memory-review-candidate-set-v1`에 넣고 resolved 2개와 AnyIO budget
   terminal을 제외한다. Failure record 10개를 candidate 10개로 오해하지 않는다.
6. **닫힘:** Candidate rule 0, review/dedup/leak scan false, `memory_admission_unlocked=false`, index/core/analysis
   closed다. Exact experiment ID/hash는 hard-consumed하며 자동 재실행하지 않는다.
7. **산출물:** Portable seal semantic body SHA는
   `sha256:e35cab52597c3ec6e884f074f9acf346dec65301e22d11edc2de56db7be9eacf`, 117,209-byte file SHA는
   `sha256:ad87fa8c540552da62d964a430c29b032097b5cabbe78f0102c23cf36330b2dc`다.
8. **다음 gate:** 9개 source를 public evidence만으로 review하고 semantic group으로 dedup한 뒤 leak scan을
   통과한 proposal을 만든다. Proposal validation은 human approval이나 memory index build가 아니다.

## Historical Phase 5 gate — D-101 review packet and admission mechanism

1. **완료:** D-099/D-100 exact binding과 machine JSON bytes를 유지하면서, 5개 항목을 쉬운 한국어로 설명하는
   사람용 Markdown을 생성했다. 사용자는 내부 이름, hash나 영문 상태명 없이 번호별 한글 선택과 이유만 답한다.
2. **완료:** Complete non-synthetic journal과 head/count/file SHA를 요구하는 candidate builder/validator를
   구현했다.
3. **완료:** Exact candidate ID/body/file SHA를 요구하는 self-attested approval receipt와 live-journal-bound
   seal을 구현했다.
4. **완료:** Candidate/receipt/seal은 exclusive create와 exact retry만 허용하고 기존 다른 bytes를 overwrite하지
   않는다.
5. **완료:** 한글 Markdown은 12,872 bytes와
   `sha256:9fc8e51dc867d66672b7c5334402bafdc27759914df88df09d506a5832d479c5`다. 갱신된 source gate는
   3,807 bytes, file SHA
   `sha256:987cded0f469370f3f9c5542c8353f7153429d7b3743df9af003f2f594b3a275`, semantic body SHA
   `sha256:26838ab1e8097e47f53e712ce11d0d8a603cd4dd3dff408792f77f7d164fe4f9`다. Machine JSON과
   D-099/D-100 의미 및 hash는 변경하지 않았다.
6. **닫힘:** 사용자 선택과 production human decision은 0이다. Journal, candidate, receipt와 seal은 생성하지
   않았고 admitted rule도 0이며 memory admission/index/core/analysis는 닫혀 있다.
7. **다음 gate:** 사용자가 1번부터 5번까지 각 항목의 허용된 한글 선택과 이유를 명시한다. 일반적인
   `진행해줘`는 선택으로 해석하지 않으며, 번호별 답변이 없으면 production journal에 아무 row도 append하지
   않는다.

## Historical Phase 5 gate — D-102 recorded decisions and candidate

1. **완료:** 사용자가 한글 문서를 검토한 뒤 1·2·5번은 `기억에 추가`, 3·4번은 `나중에 결정`으로
   명시적으로 확정했다. 시스템이 공개 근거에 기반한 이유를 연결했으므로 5개 row는 모두
   `reviewer_kind=maintainer_assisted`다.
2. **완료:** Journal은
   `reports/memory-development/d102-maintainer-assisted-group-decisions.jsonl`, record 5/correction 0, head
   `sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469`, 7,829-byte file SHA
   `sha256:5c46e6b6a49e436794c1b118f96a9d05caa48a4cd4199e9791ec2ec4499327e3`다.
3. **완료:** Exact head/count/file SHA를 외부 입력으로 다시 제공해
   `reports/memory-development/d102-maintainer-assisted-admission-candidate.json`을 만들었다. Candidate ID는
   `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, body SHA는
   `sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, 31,148-byte file SHA는
   `sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`다.
4. **측정:** Effective decisions는 approve 3/reject 0/continue-hold 2이고 candidate 안 preview entry는 3개다.
   Preview는 projection-only이며 admitted MemoryEntry가 아니다.
5. **완료:** Portable gate는
   `reports/memory-development/d102-maintainer-assisted-decision-candidate-gate.json`, semantic body SHA
   `sha256:27e6b50c156e2c590e4225302534c5fedca67596eae2c831d03d3a4810c11732`, 5,453-byte file SHA
   `sha256:e8ff1cdecdb7b107593f43f0b68b564abab34668558a0bb367296e16fbcca373`이며 focused tests 6/6과
   D-097~D-102/memory/contracts/CLI/qualification related tests 405/405가 통과했다. D-099~D-101 artifact/hash는
   변경하지 않았다. Repository-wide는 1,816 collected 중 1,809 passed/7 environment-dependent skipped/failure
   0이다.
6. **닫힘:** Exact candidate approval receipt와 seal은 absent, admitted rule은 0이다. 두 continue-hold가 남아
   full group review도 finalized가 아니다. Source authoring, index build/freeze, core와 analysis는 닫혀 있다.
7. **경계:** D-102는 provider/evaluator call 0/0, added model cost `$0`이다. Memory benefit, negative transfer,
   hidden cause 또는 agent architecture defect를 증명하지 않는다.
8. **다음 gate:** 사용자가 위 candidate ID/body SHA/file SHA를 별도 메시지에서 정확히 다시 승인한다. 현재
   다섯 group 선택 승인을 candidate snapshot 승인으로 재사용하지 않는다.

## Historical Phase 5 gate — D-103 exact approval and narrow admission seal

1. **완료:** 사용자가 candidate ID
   `d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, body SHA
   `sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d`, file SHA
   `sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457`를 별도 메시지에서 정확히
   다시 입력해 승인했다.
2. **완료:** Self-attested receipt는
   `reports/memory-development/d103-exact-candidate-approval-receipt.json`, ID
   `d101receipt_23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, body SHA
   `sha256:23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a`, 6,245-byte file SHA
   `sha256:dad12cf181fee8e113d9da703795eb8ccb4a16be6014218ea923a919d0695031`다. Identity 인증과 signature
   verification은 false다.
3. **완료:** Live journal, candidate와 receipt를 exact 재검증한 seal은
   `reports/memory-development/d103-maintainer-assisted-admission-seal.json`, ID
   `d101seal_3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, body SHA
   `sha256:3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e`, 19,357-byte file SHA
   `sha256:af1e6ea8811445f26d542f34500d1a7b3919392bef00c98b71f4c26ded236e8e`다.
4. **측정:** Admitted rule template는 1·2·5번의 3개, open hold는 3·4번의 2개다. Full five-group review는
   finalized가 아니고 D-103 checkpoint의 unindexed source record count는 0이다.
5. **완료:** Portable gate는
   `reports/memory-development/d103-exact-candidate-admission-gate.json`, semantic body SHA
   `sha256:4a542cd571ffc0b94b6f95e106fd2371425dd66f82cfa6091cc602905036fb1f`, 5,315-byte file SHA
   `sha256:4602a579d7c11dd300e2f9bede38e8a6d7bf21c78a8fbfc255550b7d86f3d354`다.
6. **검증:** Focused 7/7, D-097~D-103/memory/contracts/qualification related 497/497, repository-wide
   1,823 collected 중 1,816 passed/7 environment-dependent skipped/failure 0이다.
7. **권한:** Memory admission과 source authoring만 true다. Index build/built/frozen, core와 analysis는 false다.
   D-103 provider/evaluator call은 0/0이고 added model cost는 `$0`다.
8. **다음 gate:** 세 admitted template를 strict unindexed source wrapper로 materialize하고 leak scan과
   schema/provenance validation을 통과시킨다. 이 gate는 index build/freeze나 core를 자동으로 열지 않는다.

## Historical Phase 5 gate — D-104 exact unindexed source materialization

1. **완료:** D-103 gate/seal을 exact 재검증하고 admitted projected entry 3개만 source 의미 원천으로 사용했다.
   Trace나 submitted public patch를 다시 요약하지 않았다.
2. **완료:** Strict schema `unindexed-memory-entry-source-d104-v1`으로 exact source 3개를
   `reports/memory-development/sources/d104/`에 만들었다. Source collection ID는
   `d104collection_4017131c10c127f47b8ea68ff2d8c3c3265c2f6cb11c1b175dd52c23882bd399`다.
3. **측정:** Source file size/SHA는 5,188 bytes/
   `sha256:8a139248e3e53e3a563366c6a2f9ad213a6a164831bd3cef2a3e5b6cb37008e8`, 5,333 bytes/
   `sha256:87b1b751634d8c34ef125042e472807828a7820064f25e413a51d0755b5b51da`, 5,416 bytes/
   `sha256:d5b22f7c2ca75a271cf60cd52eb9089f2fd54bec99f5c9a75d09c311e0311505`다. Ordered source-set
   hash는 `sha256:1168c8c9cfcaa3671f42391436bfff713c90f01baec468e5ef2509ddb95dbad2`다.
4. **완료:** Template, template hash, group ID/fingerprint, decision hash, ordered source run/failure/evidence ID와
   dedup confidence를 seal과 exact 비교했다. `validation_count=0`이고 hold 2개 materialized count는 0이다.
5. **완료:** Exact allowlist와 강화된 non-echoing leak scan이 source text의 diff/code, private/hidden/reference,
   evaluator-only marker, credential, local path와 control/bidi/zero-width text를 거부한다.
6. **완료:** Portable gate는
   `reports/memory-development/d104-three-rule-source-materialization-gate.json`, gate ID
   `d104_61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11`, semantic body SHA
   `sha256:61e44eb5609c05c97b84602bbaa4eb7bff84dd33af227cef18592aa2b6a32c11`, 12,705-byte file SHA
   `sha256:8eeb26d6f5e0ff22658501afe54bd8cebe35896dc18b60f8f73355ec53190dd0`다.
7. **검증:** Focused 30/30, D-097~D-104/memory/contracts/CLI/qualification related 530/530이다. Repository-wide는
   1,853 collected 중 1,845 passed/7 environment-dependent skipped/1 failed다. 유일한 기존 order-dependent D-093
   SQLite WAL/SHM invariant는 fresh isolated process에서 1/1 통과했으며 D-104 failure나 fix로 합산하지 않는다.
8. **경계:** D-104-created actual `MemoryEntry`, `index_version`, render, embedding과 index는 0/absent다. Legacy
   failure builder는 연결하지 않았고 historical index는 inspect/modify하지 않았다. Index build/freeze, retrieval,
   core와 analysis는 false다. Provider/evaluator call 0/0, added model cost `$0`다.
9. **다음 gate:** Deterministic model-facing renderer와 2,000-token policy를 고정하고 pinned embedding revision 및
   group-aware index-build authorization source gate를 구현한다. 자동 index build/core 실행은 하지 않는다.

## Historical Phase 5 gate — D-105 deterministic render and index-authorization candidate

1. **완료:** Exact D-104 gate와 ordered source set을 재검증하고 승인된 source 세 개만 renderer input으로
   사용했다. Hold 두 그룹과 raw trace/private/evaluator/provider body는 읽지 않았다. Inherited D-099 validator는
   public submitted patch bytes를 integrity/leak scan용으로 읽지만 render에 복사하거나 새 rule 의미 작성에 쓰지
   않았다. Package initialization은 legacy retrieval/store module을 간접 import하지만 해당 API를 호출하지 않았다.
2. **완료:** `model-facing-memory-render-d105-v1`은 이미 NFKC인 ASCII-subset UTF-8 input, LF, trailing LF,
   fixed field/list order, whole-entry-only와 fixed separator를 요구한다. Partial truncation과 provenance/local path의
   model text 포함을 금지한다.
3. **측정:** Checked-in render는 1,191/1,164/1,161 bytes다. Ordered render-set SHA는
   `sha256:7b72fc94642d996fad5a0b199719c56bfecc8a8fc1bbe42b2060aa18e21d2667`, canonical joined
   bundle은 3,528 bytes/SHA
   `sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf`다.
4. **완료:** Maximum 2,000-token policy를 canonical context의 `/selected_memory`만 JSON `null`에서 exact
   whole-entry bundle로 바꾼 same-full-request provider `input_tokens` delta로 정의했다. Context deep diff와 context
   slot normalization 뒤 request equality, header/separator 포함, 두 context/request hash를 future receipt에 요구한다.
   `chars/4`와 standalone local estimate는 authoritative evidence로 쓰지 않는다.
5. **미측정:** D-105 provider call은 0이므로 exact token-count receipt와 budget validation은 없다. 다음 provider
   receipt 전까지 `provider_exact_budget_validated=false`를 유지한다.
6. **후보 고정:** Embedding model은 `sentence-transformers/all-MiniLM-L6-v2`, revision
   `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, normalized embedding,
   `trust_remote_code=false`다. Exact `pyproject.toml`/`uv.lock`과 locked package version도 gate에 결속했다.
7. **미완료:** Model snapshot download/import, snapshot file hash, offline reload, expected 384-dimension float32 vector,
   locked dependency preflight와 actual group-aware builder는 검증하지 않았다.
8. **완료:** Prospective builder plan은 D-104 source 세 개를 exact order로 소비하고 one-entry-per-admitted-group,
   held-group rejection, deterministic index identity와 out-of-band provenance를 요구한다. Legacy failure별 builder는
   금지한다.
9. **완료:** Portable gate는
   `reports/memory-development/d105-renderer-embedding-index-authorization-gate.json`, gate/body ID
   `d105_0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`/
   `sha256:0f99c7d1cd1c371191073ead8d60636be9ea6040947d9c7f3522aba25bc3df70`, 12,368-byte file SHA
   `sha256:db6303f3de834b3c36493f2863dcc5be3ca697490d18df15c86a18e7ee7b17eb`다.
10. **검증:** Focused 47/47와 related 550/550가 통과했다. Repository-wide는 1,900 collected 중 1,892
    passed/7 environment-dependent skipped/1 failed다. 유일한 기존 order-dependent D-092 raw replay SQLite
    WAL/SHM invariant는 fresh isolated process에서 1/1 통과했으며 D-105 failure나 fix로 합산하지 않는다.
    D-105 provider/evaluator call 0/0, added model cost `$0`다.
11. **경계:** `index_build_authorization_candidate=true`는 실제 권한이 아니다. User approval receipt,
    `memory_index_build_authorized`, actual `MemoryEntry`, embedding/index, build/freeze, retrieval/runtime injection,
    core/analysis와 memory-effect/negative-transfer claim은 0/false다. Raw Trace condition도 D-105 범위가 아니다.
12. **다음 gate:** 사용자가 exact D-105 gate를 명시적으로 승인한 뒤 locked embedding snapshot preflight와 새
    group-aware builder를 구현한다. 이 세 조건 전에는 index build나 core execution을 시작하지 않는다.

## Historical Phase 5 gate — D-111 retrieval-readiness authorization candidate

1. **Exact source:** D-110 frozen index/marker와 D-106 unchanged source를 재검증하고 public dev-validation
   `Moto/IMPLEMENT`, `Babel/IMPLEMENT`, `Moto/REPRODUCE`만 결속했다. Private/hidden/reference/known-bad patch는
   읽지 않았다.
2. **Artifacts:** Preflight는 13,085 bytes, ID/body/file SHA
   `d111preflight_ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`/
   `sha256:ee48af2da2ab34bb252f11842fe34c734229ad193776fc97bdd34dc3849003f9`/
   `sha256:fed699e068c52e2dd929b654a65369aee3499d6d69c5a38c14dcee808ff57387`다. Candidate는 6,465 bytes,
   ID/body/file SHA
   `d111retrievalcandidate_bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`/
   `sha256:bfde5cfe1c75cd90e8d78a0960b6d5ac7986420016d805e75b9725abdb20fe7a`/
   `sha256:f91aa284cc7a2add2516f44b4397b29e3aee5caa4cf0f83ec7913e6e5d7899d6`다. Gate는 3,308 bytes,
   ID/body/file SHA
   `d111_348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/
   `sha256:348e6dd21ad0816a3c4dc1889f2d7a421c7e41194c48b2fe5c7120513f6b3524`/
   `sha256:d550cb048e417965e482c64682df4a1b91b90067f66b36e370912f5a8d759c16`다.
3. **Readiness gaps:** Natural public selective score의 최대값은 `0.65`로 threshold `0.72`보다 낮다. Legacy
   renderer는 D-105 exact render와 세 entry 모두 byte mismatch이고 pinned embedding snapshot의 local-only load도
   강제하지 않는다.
4. **검증과 경계:** Focused 8/8, related 7/7이 통과했다. Retrieval call, query embedding, runtime injection,
   provider/evaluator call과 core는 모두 0/false다. Candidate는 승인 receipt가 아니다.
5. **다음 gate:** 사용자가 exact D-111 candidate ID/body/file SHA를 별도 메시지에서 승인할 때만 pinned local
   snapshot과 frozen model-facing bytes를 쓰는 one-use local read-only scoring diagnostic을 고려한다. Automatic retry,
   runtime retrieval integration, memory injection, provider/evaluator와 core는 그 승인에도 포함되지 않는다.

## Historical Phase 5 gate — D-110 exact one-use index freeze

1. **승인 완료:** 사용자가 D-109 candidate ID/body/file SHA를 같은 메시지에서 정확히 다시 제시하고 exact index
   freeze 1회만 승인했다. Approval receipt는
   `reports/memory-development/d110-exact-index-freeze-approval-receipt.json`, ID/body SHA
   `d110approval_cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`/
   `sha256:cb0ab444a4c453fbf496e509891013163825c8b5c362204c43d37c7452d49e7b`, 3,495-byte file SHA
   `sha256:f409c6296b1f87d8cb151fcc1866d263f3e74aa9341c46ab49ea3b4fef66a97c`다. Recorded time은
   `2026-08-06T12:42:48Z`다. 이는 self-attested approval이며 identity authentication/signature evidence가 아니다.
2. **한 번만 실행:** `2026-08-06T13:54:43.725943Z`에 pre-state를 재검증하고 one-use journal capability를
   소비했다. Automatic retry와 rollback은 허용하지 않는다.
3. **정확한 변경:** Existing index에서 `/frozen`, `/frozen_at`, `/authority/index_freeze_authorized`,
   `/authority/memory_index_frozen`, `/content_hash`만 바꿨다. Post index는 55,687 bytes/file SHA
   `sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0`, content hash
   `sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56`다.
4. **Marker와 portable evidence:** Runtime과 D-110 portable marker는 72 bytes/file SHA
   `sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561`이고 frozen index bytes도
   서로 같다. D-106 portable unfrozen index는 55,644 bytes/file SHA
   `sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a`로 unchanged다.
5. **실행 기록:** Journal은 `reports/memory-development/d110-index-freeze-execution.jsonl`, 8 records, head
   `sha256:03d8bcbf57230aa9bfd5ce4e81fa2890bb36c2f5f9e4e51c9e64b3a8c09313e1`, 9,481-byte file SHA
   `sha256:f06cfa9037f09720675d3c0edd7e19516144bd46375aaa86679c5b1f6923b1e2`다.
6. **Receipt와 gate:** Freeze receipt ID/body/file SHA는
   `d110freezereceipt_b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`/
   `sha256:b8ca4f167c330011118edb33d8ad3f18a47a20e795f28e752d6cc87e84daa839`/
   `sha256:a2aeaa0985cb1bf9ced5bdfd43c5bc473a73e5ac93bf7660ca717e3eb9285702`, 5,986 bytes,
   recorded time `2026-08-06T13:54:43.782123Z`다. Completion gate ID/body/file SHA는
   `d110_bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`/
   `sha256:bc1cae7a2ebc5d6531d203ef4d7101762d7366c9e77814c3a4c772d353f0a736`/
   `sha256:79578db09955dab2a22b015ba5210baec28e7d30b9cac818b1f2c6d6eac782cd`이고 recorded time은
   `2026-08-06T13:54:43.793637Z`다.
7. **Commit 경계:** Index는 staged-file fsync 뒤 same-filesystem `os.replace`, marker는 그 뒤 exclusive binary
   create/fsync한다. 이는 ordered per-file commit이지 global two-file atomic transaction이 아니다. Cooperative
   lock은 D-110 executor끼리만 조정하며 arbitrary external writer를 배제한다고 주장하지 않는다. Partial 또는
   ambiguous state는 fail closed한다.
8. **검증:** Pre-mutation focused 17/17과 post-freeze focused 17/17(256.5초)이 각각 통과했다. D-110 related와
   repository-wide full-suite 결과는 아직 집계하지 않았으므로 주장하지 않는다.
9. **경계:** Provider/evaluator call 0/0, added model cost `$0`다. `memory_index_frozen=true`만 열렸고
   `retrieval_ready=false`, retrieval experiment authorization false, runtime injection 0, core와 analysis false다.
10. **다음 gate:** Separate retrieval-readiness authorization candidate를 offline으로 준비한다. 이 gate는 retrieval
    실행, runtime memory injection 또는 core campaign 권한이 아니다.

## Historical Phase 5 gate — D-112 exact one-use local scoring diagnostic

1. **승인:** 사용자가 exact D-111 candidate ID/body/file SHA를 별도 메시지에서 다시 제시하고 D-112 구현과 local
   read-only diagnostic 1회만 승인했다. Policy 수정, injection, agent run, retrieval experiment와 core는 제외했다.
2. **One-use claim:** `d112-retrieval-readiness-probe-receipt.json`을 model load 전에 exclusive create/fsync했다.
   Receipt ID/body/file SHA는
   `d112probereceipt_ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257`/
   `sha256:ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257`/
   `sha256:74fcd761cac65a9cab26529076b7cde60eaa14a1faf40475e680f526e00ba1d1`다. 실패해도 retry하지 않는다.
3. **Local execution:** Pinned snapshot CPU/local-files-only load 1회, ordered 3-query batch encode 1회, query row 3개,
   vector shape `(3, 384)`, dtype float32를 지켰다. Provider generation과 evaluator call은 없다.
4. **Observed scoring:** Moto/IMPLEMENT, Babel/IMPLEMENT, Moto/REPRODUCE의 top score는 각각
   `0.3541890713468577`, `0.39188659397843584`, `0.20418907134685768`이고 모두 0.72 미만이다. 세 top group은
   모두 `exception-origin-state-conflation`이다. Moto positive group 가설과 일치하지 않는다.
5. **Portable evidence:** Completion gate ID/body/file SHA는
   `d112_3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6`/
   `sha256:3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6`/
   `sha256:a7e691ae43c60405cbb10cd27caf3055eabaa96bb7fa6f2a02142d97aa903951`다. Full query vector가 있어
   validator는 model load 없이 score/rank를 재계산한다.
6. **검증:** Focused 11/11, D-111/공용 memory 회귀 13/13이 통과했다. Full suite와 D-106~D-110 전체 suite는
   실행하지 않았다.
7. **경계:** Retrieval, memory selection/text return/injection, agent/provider/evaluator는 0이고 index/threshold/score
   policy는 unchanged다. OS socket block은 검증하지 않았고 library offline/local-only만 증명한다.
8. **Post-execution audit:** Actual receipt/gate와 점수는 일치한다. 그러나 skip-input flag도 local snapshot을 읽고,
   receipt fully-rehashed unknown field를 엄격히 거부하지 못하며 chronology를 강제하지 않는다. One-use도
   repository-local cooperative claim이다.
9. **다음 gate:** Gate 내부에는 `separate-offline-score-policy-decision-candidate`가 기록됐지만, 구현 우선순위는
   execution-bound D-112를 rewrite하지 않는 별도 append-only validator-correction candidate다. 이 문구는 code fix,
   correction 실행, retrieval, runtime injection 또는 core 권한이 아니다.

## Historical Phase 5 gate — D-120 D-119 cleanup-correction authorization candidate

1. **D-119 상태를 그대로 봉인:** D-120은 exact D-119 approval receipt, preflight, 4-record journal과
   module/script/test를 다시 hash해 결속하고, D-119의 세 completion output이 여전히 없음을 확인했다. D-119 파일을
   rewrite, retry, resume 또는 repair하지 않았다. 상태는 `PARTIAL_CONSUMED_FAILED`, durable completed session은 0,
   sealed probe outcome은 0이고 결과는 `UNSEALED_UNKNOWN`이다.
2. **실패 해석의 한계:** D-119 journal은 첫 SWE-bench session 시작 뒤 `D119QualificationError`로 끝났다는 사실만
   증명한다. 현재 source와 운영자 관찰은 container 제거 뒤 `docker inspect`가 nonzero와 함께 빈 JSON 배열 표현을
   반환했는데 cleanup validator가 이를 거부한 상황과 일치한다. 하지만 raw command transcript와 probe result가 D-119
   journal에 없으므로 이는 source-consistent self-attested diagnosis이지 portable proof가 아니다. Probe 성공, source
   hash 실패 또는 Docker isolation 실패 어느 것도 확정하지 않는다.
3. **Exact D-120 artifacts:** Preflight는 21,101 bytes, ID/body/file SHA
   `d120preflight_cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/
   `sha256:cc3496328cf64c924c762d47a7f4926d23322991c29064e68ae6d376a8339310`/
   `sha256:6ec5ff207fdf24cb8baab733b9db096ece3d1fe1ba0ba5c6c644ac6c20ccd5ea`다. Candidate는
   10,464 bytes, ID/body/file SHA
   `d120cleanupcandidate_86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/
   `sha256:86d95b4b3cf0b49a20724b136075bfa9da281fce4dc6b20b6063a07bfcdd9b82`/
   `sha256:f4f985e6574ead218ffea4813d234c1b5c35cdf60e109de5bbe0849dd25127d8`다. Source gate는
   12,140 bytes, ID/body/file SHA
   `d120_8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/
   `sha256:8172bae0e2446e647edb8d03272cf5499a9faa8f92a1f26b8cd08b5a9dc6abbd`/
   `sha256:cd4fe9024bfb1b44e9e762412e442f3c2958085629b15e19f7a9423aefa3581b`다.
4. **D-120의 실행 경계:** D-120 materialization 중 Docker, network와 opaque Parquet source read는 0이다. D-120은
   D-121의 new-only module/script/test, offline test, container를 시작하지 않는 exact Docker readiness preflight와
   execution-authorization candidate 준비만 제안한다. Candidate 상태는 `awaiting-exact-user-approval`이고 actual D-121
   run은 승인하지 않는다.
5. **다음 gate:** 사용자가 위 D-120 candidate ID/body/file SHA를 별도 메시지에서 정확히 승인해야 D-121 구현·test·
   no-start readiness·execution-authorization candidate 준비를 시작할 수 있다. 그 승인을 받아도 container start,
   opaque source read와 D-121 run은 금지되며, 실제 실행에는 새 D-121 candidate triple에 대한 별도 exact 승인이 필요하다.
6. **검증과 닫힌 권한:** D-119+D-120 focused 검사는 76/76 통과했다. Repository-wide suite 통과로 확대하지 않는다.
   Trusted cutoff anchor, record projection isolation과 independence는 false다. Pool/record review, matcher/classifier/
   calibration, score/index mutation, retrieval/runtime injection, agent/provider/evaluator와 core/analysis는 0/closed다.

## Historical Phase 5 gate — D-119 consumed partial isolation execution

1. **승인 소비:** D-119는 exact execution tuple과 action hash
   `sha256:be673eec0b6cf5cde23db0f19c050d82867a1a4a497a28124f61ca47e24278c2`에 대한 one-use 승인을 소비했다.
   Approval receipt와 preflight는 각각 5,299/11,229 bytes이고, journal은 2,075 bytes의 4-record hash chain이다.
2. **실행 결과:** 첫 isolation session이 시작된 뒤 cleanup 검증에서 `ExecutionFailed`가 기록됐다. Completion gate,
   external-anchor evidence와 isolation evidence는 생성되지 않았다. 동일 D-119를 자동 재시도하지 않으며 이 partial
   state는 immutable historical evidence로 남긴다.
3. **판정 경계:** Durable completed session과 sealed probe outcome은 모두 0이므로
   `hash_only_isolation_profile_verified=false`다. D-118의 trusted cutoff 결손도 해소되지 않았고 independent control,
   record projection, matcher/retrieval/agent/core 권한은 열리지 않았다.

## Historical Phase 5 gate — D-118 external public-development source evidence

1. **승인 범위와 D-117 비소비:** 사용자는 exact D-117 candidate ID/body/file SHA를 다시 제시하고 공개 development
   benchmark metadata 조사, revision-pinned snapshot 다운로드와 membership/cutoff/isolation hash preflight만 승인했다.
   Issue/task record 읽기, labeling, matcher/classifier/calibration, retrieval, agent와 core는 승인하지 않았다. D-117이
   제안했던 후속 execution-authorization-candidate action은 `authorized=false`, `consumed=false`로 남아 있다.
2. **Exact artifacts:** Approval receipt는 4,199 bytes, ID/body/file SHA
   `d118approval_2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`/
   `sha256:2a7461b834374e4a34db8c02850501d0ad9e8416e7a4bf7f73613abef08713a2`/
   `sha256:0adb87887b42a19aa8d1b9be3ca5268801666bbecb2cf94b4664e3df1dba8344`다. Preflight는
   17,476 bytes, ID/body/file SHA
   `d118preflight_1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`/
   `sha256:1f11c66f174e5e475ef9d94df7810c568857f02a8164edf30287778276dab4b0`/
   `sha256:4f4bff33cbf55e841f86da0a30fc67885f9302fa2f149dde040a3d85a2c4c0b3`다. Evidence pack은
   25,451 bytes, ID/body/file SHA
   `d118evidencepack_e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`/
   `sha256:e40dad5ceac6dcfbb29d47bec3a548c44bdcbeba964e4e7a43818b76e8c62f10`/
   `sha256:318d4f58276283e6e6ae6c45c4afe50af5bca6b6937ffa841b8b791a0357c6b1`다. Source gate는
   17,748 bytes, ID/body/file SHA
   `d118_cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`/
   `sha256:cdd55277ad1dc1215a45aa3588e7862df3535b91b7274681fe0a8488abd3e707`/
   `sha256:0f01a2b315f9c32c34b8c2400af6f22a1c4f2538b2538f8597f2ab0b8d57c343`다.
3. **Opaque snapshot evidence:** SWE-bench dev revision
   `f5351ee8c6663736817027db3ad03fe662cb5bb8`과 SWE-Gym train revision
   `26a6eae79ae9cb6d4307c3cc99c126fbf23cb3f0`에서 `.gitattributes`, `README.md`, 단일 Parquet shard를
   각각 binary hash-only로 검증했다. 총 6개 파일, 45,036,395 bytes이며 Parquet footer/schema/row와 issue prose,
   label, patch, test 또는 oracle field는 읽지 않았다.
4. **우선순위는 admission이 아님:** `swe-bench-dev-f5351`은 더 작은 official development surface라는 이유로
   provisional priority 1로 기록했을 뿐이다. Source pool을 선택·획득·동결하거나 independent control로 편입하지
   않았고, 두 source 모두 `post_hoc=true`, `independent=false`, calibration 부적격이다.
5. **Fail-closed 이유:** Provider revision/tree/membership/GPG badge 관련 관찰은
   `source-level-web-research-self-attested`로 낮춰 기록했다. Bound input만으로 provider tree와 membership proof를
   재구성하지 못했고, exact snapshot과 exhaustive membership rule을 함께 D-116 cutoff 이전에 결속하는 trusted
   anchor도 없다. Isolation은 image digest와 실제 negative probe가 없는 계획뿐이므로 실행 증거가 아니다. 최종
   disposition은 `BLOCKED_INSUFFICIENT_PREEXISTENCE`이며 execution-authorization candidate는 준비되지 않았다.
6. **검증과 권한:** Focused D-117+D-118 검사는 48/48 통과했다. Repository-wide suite 통과로 확대하지 않는다.
   Issue/task record read, labeling/review, matcher/classifier/calibration, retrieval/runtime injection, agent/provider/
   evaluator call은 모두 0이고 core/analysis는 closed다. Added model cost는 `$0`다.
7. **다음 gate:** Trusted pre-D-116 anchor가 exact snapshot과 membership rule을 함께 결속하고, immutable isolation
   image에서 negative probe를 실제로 통과했다는 별도 증거가 필요하다. 그 전에는 D-118 execution-authorization
   candidate도 만들지 않으며 admission, review, matcher/calibration, retrieval, agent 또는 core를 실행하지 않는다.

## Historical Phase 5 gate — D-117 grammar-blind public-development control-acquisition protocol

1. **Exact approval과 좁은 범위:** 사용자가 exact D-116 candidate ID/body/file SHA를 별도 메시지에서 다시 제시해
   D-117 protocol candidate 준비만 승인했다. Receipt는 D-116 next-action hash
   `sha256:e368dcb794875064f605a341902b4c27be20fcb3ff9b86d65ca5fb66dbf35e55`도 결속한다. 이 승인은
   actual pool discovery/acquisition, public issue read, role session, review/label, matcher/classifier/calibration,
   policy/retrieval/agent/API/core 권한이 아니다.
2. **Exact artifacts:** Approval receipt는 10,096 bytes, ID/body/file SHA
   `d117approval_f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
   `sha256:f70a2ff210ae2df203591b9650177161ca71084da256e994539af09a48deeae9`/
   `sha256:40ea64548634353a12b48f8bcabce941df47e16f9b27d892722d55fcda1e5e13`다. Preflight는
   29,919 bytes, ID/body/file SHA
   `d117preflight_34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
   `sha256:34645da3c09db9d3ba288425b44e0e27f631e8b034a231abd7e113dbdeea5464`/
   `sha256:6682f4f2870cdb34e6ee766333c95ac58a406a7d4e4086d6086752650869c305`다. Candidate는
   7,999 bytes, ID/body/file SHA
   `d117blindprotocolcandidate_27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
   `sha256:27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae`/
   `sha256:d10bbe5b3b65050868a1202cd1af9f130c89bbe43ceccf9359af145cac96cda7`다. Source gate는
   16,813 bytes, ID/body/file SHA
   `d117_750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
   `sha256:750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589`/
   `sha256:a439fc936b5b594c043b4ea90cd57bb676e79004cf4de8794b83f3af15fb13e3`다.
3. **Preexistence와 split 경계:** Future pool은 public-development control만 허용하고 held-out task·issue·result와
   private/hidden/reference/patch/trace/evaluator lineage를 제외한다. Exact source bytes와 membership manifest 또는
   exhaustive rule은 D-116 cutoff `2026-08-07T06:22:51.021003Z`보다 먼저 신뢰 가능한 외부 anchor에 결속돼야 한다.
   `created_at`, mtime, Git timestamp 또는 현재 fetch/hash만으로는 이를 증명하지 못한다.
4. **Blind role과 한계:** Protocol author/current conversation actor, D-116 grammar observer와 same-checkout subagent는
   blind role에 부적합하다. Future assembler는 D-105/D-116을 보지 않고, selector A/B와 adjudicator는 opaque ID,
   canonical title/description/language와 exact D-105 rubric만 받는다. 기술적으로 격리된 process input은 증명할 수
   있지만 사람의 사전 지식 부재는 cryptographically 증명하지 않는다.
5. **Fallback과 미실행:** Preexistence, role isolation, first-pass seal, lineage 또는 chain-of-custody가 하나라도
   불완전하면 append-only로 `post_hoc=true`, `independent=false`가 된다. D-117은 pool을 이름 붙이거나 issue를
   읽지 않았고 manifest/member, role/isolation session, packet/result, independent control/positive가 모두 0이다.
6. **검증과 비용:** D-117 focused 25/25와 D-116+D-117 연속 46/46이 통과했다. Repository-wide suite는 이
   checkpoint에서 실행하지 않았다. Matcher/classifier/calibration implementation·execution, model/embedding load,
   retrieval/injection, agent/provider/evaluator/network-capable call은 모두 0이며 added model cost는 `$0`다. OS-level
   socket 차단/계측은 검증하지 않았다.
7. **다음 gate:** Candidate status는
   `protocol-sealed-no-pool-inspected-acquisition-and-independent-positives-still-blocked`, next-action hash는
   `sha256:362cf3f74c9d57ecc4238f4b7c024b470c8ad65038ee6a599581a1df82fc6c06`다. 다음에는 exact D-117
   candidate triple과 exact external public-development source/membership/cutoff/isolation triples를 함께 제시해
   D-118 **execution-authorization candidate 준비만** 별도 승인할 수 있다. 그 승인도 actual acquisition/review,
   matcher/calibration, retrieval/agent/core 실행 권한이 아니다.

## Historical Phase 5 gate — D-116 deterministic public-applicability contract

1. **Exact approval과 입력 경계:** D-115 candidate/action을 exact ID/body/file/action hash로 결속한 self-attested
   receipt만 소비했다. 입력은 public dev-train/dev-validation의 canonicalized issue title, description, language뿐이다.
   Task ID, path, repository identity, phase, trace/patch/test 결과, D-112 hypothesis, private/hidden/reference/known-bad와
   held-out 결과는 classifier input이 아니다.
2. **Exact artifacts:** Approval receipt는 12,014 bytes, ID/body/file SHA
   `d116approval_016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
   `sha256:016c99bd81a756f640cf10132eda196057cb3a50a59cf593d64e215dc4d47bcb`/
   `sha256:86c4e279df6c3d4b6ea02719375f76370d76fb795d642f2d10211e878662ba77`다. Preflight는
   76,157 bytes, ID/body/file SHA
   `d116preflight_e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
   `sha256:e9005e90895ea4554ea04b21b025ff1afc42076d4e08a7adef2b6476cbf06a3f`/
   `sha256:fc2602a385242204ab9ae274ea6c73a83bd00a00eace88c7f310a57b5d4655f5`다. Candidate는
   8,017 bytes, ID/body/file SHA
   `d116classsignalcandidate_0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
   `sha256:0b1b700af4ce2274cb9cb032ecf23c741ec9c41b0e86abbc06e96e18f91c74d4`/
   `sha256:8299f3d400bd9412a8b7100305a0eb57f1d5b4ea78a39d8e5edad6cd5a2b15ca`다. Source gate는
   19,859 bytes, ID/body/file SHA
   `d116_e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
   `sha256:e93b1d39428c3778dd1f55dd0ae1a6c7f4b2091f9b4a92c347f6b7b3c6a66c37`/
   `sha256:f03bc7806d8401b9ac9f3d9e47df7b0ef19b16a04380bed1c9cb1d105e52320d`다.
3. **Formal contract:** Taxonomy/input/result/abstention/predicate contract hash는 각각
   `sha256:910b02269b16d8277a48dfd0353724e06c5aea988874b9dcb89e062cd1508b45`,
   `sha256:24a0d5102b5066dd19b8cc9b68cf8d84bbb70b4f364e604ea804fab120a260b2`,
   `sha256:ae1536068aa28142e289feb97045bd289ca1dbf0df70a8d25777a9885df220d9`,
   `sha256:1ad0614589c555c285befb51f7e28e80f7b3e5c0f155116e05e08295bc09063c`,
   `sha256:c9e88df2d48ea1d089da11ec394fd41daa2d3e377b3058899e9f530b51548bf1`다. Grammar는
   CPython 3.12 stdlib regex, Python-only language, canonical input, token/sentence/clause segmentation, negation,
   deterministic tuple/evidence/result ordering, global contradiction과 explicit abstention을 고정한다.
4. **Panel과 calibration 경계:** Plan hash는
   `sha256:a53c25ad05eb3cbedadde5c22f0ad226db17e6713fc33f3d8fb6ea7c7a613c8a`다. 10개 public
   file 중 eligible 8개/fixture exclusion 2개다. Pyfakefs와 HF Hub source anchor 2개는 contract authoring에 사용된
   in-sample/non-independent case다. Tox는 S3 shared-error-boundary 문장이 없고 Moto D-112 hypothesis는 label이
   아니다. Blind independent positive는 0이고 `three_class_calibration_ready=false`,
   `calibration_execution_ready=false`, true relevance와 corrected policy도 false다.
5. **구현·실행하지 않은 것:** Formal grammar는 문서화·검증했지만 matcher evaluator/classifier나 calibration
   executor 함수는 만들지 않았고 matcher/classifier/calibration execution과 task-level signal result는 모두 0이다.
   Model/embedding load, retrieval,
   injection, agent/provider/evaluator/network-capable call path도 모두 0이며 `$0`다. Network 증거는
   source-path/self-attested이고 OS-level socket block/instrumentation은 false다. Focused 21/21이 통과했다.
6. **당시 다음 gate와 소비 범위:** Candidate status는
   `formal-matcher-contract-sealed-calibration-blocked-on-grammar-blind-preexisting-control-protocol-and-public-applicability-positives`다.
   Next-action hash `sha256:e368dcb794875064f605a341902b4c27be20fcb3ff9b86d65ca5fb66dbf35e55`의 D-117은
   `prepare-grammar-blind-preexisting-public-applicability-control-acquisition-protocol-candidate`만 제안한다. D-116 이전에
   존재한 exact pool membership/bytes/provenance를 고정하고, grammar·hash·output에서 격리된 pool assembler와
   D-105 rubric만 받는 selector/adjudicator를 요구한다. 현재 process/agent는 blind selector가 될 수 없다. Blinding을
   증명하지 못하면 control을 post-hoc/independent=false로 낮춘다. 이 exact gate는 이후 D-117 protocol candidate에
   한해 소비됐고 classifier/calibration 실행, score/index mutation, retrieval/injection, agent/API/network와
   core/analysis를 열지 않았다.

## Historical Phase 5 gate — D-114 append-only D-112 validator correction

1. **Exact approval:** 사용자가 D-113 candidate ID/body/file SHA를 별도 메시지에서 다시 제시하고 새
   module/script/test와 append-only receipt/gate 생성 1회만 승인했다. D-112 rewrite, score policy, retrieval,
   injection, agent run과 core는 제외했다.
2. **Artifacts:** Approval/correction receipt는 10,493 bytes, ID/body/file SHA
   `d114approval_20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
   `sha256:20d5025c5d72b156e8470812a0062da2d4d639aa2fa9848ef38da96a71112fd7`/
   `sha256:1f494579e70d9e8a7f0d28439578afc3b3aa77c7735ac8bc4e81627cab70793b`다. Completion gate는
   15,686 bytes, ID/body/file SHA
   `d114_8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
   `sha256:8f378245c6965d59cd5e589a67cea203e502553e19fa9391b11a667db09271fb`/
   `sha256:c336004f12f187ab0bfb7946204f877c088703d25e809a8e79e9ec84d374be11`다.
3. **Correction:** D-112 receipt/gate의 exact root/body/claim keys와 full expected payload equality, approval → execution
   → completion chronology, paired rehash rejection을 강제한다. `sealed-historical` path는 current snapshot과 exact
   installed dependency 없이 checked-in frozen index, gate vectors와 public spec으로 9개 row를 다시 계산한다.
   `current-input` path는 별도 opt-in이다.
4. **검증:** Focused 35/35가 통과했다. Protected D-112, D-110 frozen index/marker와 D-106 unfrozen index는
   materialization 전후 byte-identical이다. Correction evidence materialization은 1회다.
5. **경계:** Original D-112 guarantee나 실행 결과를 소급 변경하지 않는다. Model load/encode, retrieval, runtime
   injection, agent/provider/evaluator call은 모두 0이고 added model cost는 `$0`다. Network claim은
   source-path/self-attested이며 OS socket block은 검증하지 않았다. Policy/retrieval/core는 false/closed다.

## Historical Phase 5 gate — D-115 offline score-policy decision candidate

1. **Exact source:** D-114 strict successor evidence와 exact D-112 public score row 9개만 사용한다. Private, hidden,
   reference, known-bad, raw trace/patch와 held-out 결과는 읽지 않는다. D-112 hypothesis는 acceptance ground truth가
   아니며 observed matrix에는 저장된 component만 사용한다.
2. **Artifacts:** Preflight는 59,725 bytes, ID/body/file SHA
   `d115preflight_c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
   `sha256:c9af86f3dd2f5e68316cd36290fcadb1ca8b2cfbe5627d6c6a531246183ba12b`/
   `sha256:91908b43eb581b09249f8285e5f1d09389092c5b40c1c794b9ab139667c86bad`다. Candidate는 6,839
   bytes, ID/body/file SHA
   `d115scoredecisioncandidate_91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
   `sha256:91e3ef5af000fe830483012b5deee4eeb47f5a117fa5904d93d713b03f2308ec`/
   `sha256:1fd424eab88c60a9d8480e756642b2c70b03afd03dd777e27bf36a3ea428df7a`다. Source gate는 13,730
   bytes, ID/body/file SHA
   `d115_ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
   `sha256:ab5e8f0e9f57c5fb37f05137da5b6cf8ca6421856ade33616448023d39c4a805`/
   `sha256:67f62c23e9f5e14fe9cd1d075b2c6f679764c18644837914b0031348c4a21b72`다.
3. **Algebraic decision:** Current failure-class와 validation component는 9개 row 모두 0이고 phase/language는 같은
   probe 안에서 entry별로 같다. Moto hypothesized group은 rank 3/score `0.30430094253875567`, Moto observed top
   non-hypothesized group score는
   `0.3541890713468577`, Babel lowest/top은 `0.3514907443341587`/`0.39188659397843584`다. 따라서
   threshold-only separation interval은 없고 nonnegative current-feature weight 변경도 hypothesized group을 top으로
   만들 수 없다. Corrected policy는 선택하지 않았다.
4. **Conditional tuple boundary:** `{semantic: 0.25, failure_class: 0.40, phase: 0.15, language: 0.10,
   validation: 0.10}`, threshold `0.60`은 D-112의 public non-acceptance hypothesis로 임시 class signal을 꾸민
   counterfactual이다. 그때 Moto IMPLEMENT hypothesized/Babel top/Moto REPRODUCE hypothesized score는
   `0.6530721018133969`/`0.3156332814131685`/`0.503072101813397`, phase delta는
   `0.1499999999999999`다. Runtime classifier와 true relevance는 관찰되지 않았으므로 이 tuple은 policy 선택,
   구현 또는 acceptance evidence가 아니다.
5. **검증과 경계:** Focused 19/19이 통과했고 protected fingerprint는 build 전후 같다. Model load/encode,
   retrieval, runtime injection, agent/provider/evaluator call은 모두 0이며 added model cost는 `$0`다. Network 0은
   source-path/self-attested이고 OS-level socket block/instrumentation은 false다. Policy/threshold/ranking,
   memory/index/marker와 runtime path는 unchanged다. `score_policy_correction_authorized=false`,
   `retrieval_ready=false`, `core_campaign_unlocked=false`다.
6. **Historical next gate:** Exact D-115 candidate triple 승인은 이후 D-116 contract/plan materialization에 한해 한 번
   소비됐다. 그 승인은 score-policy mutation, retrieval, injection, agent/provider/evaluator, network, core 또는
   analysis campaign 권한으로 확대되지 않았다.
