# Implementation Plan

상태: **Implementation baseline active**  
현재 milestone: **tool-v2/context-v3 gpt-5.4-mini campaign-pilot preflight gate**

2026-07-30 구현 스냅샷:

| 영역 | 상태 | 현재 evidence |
| --- | --- | --- |
| Phase 1 evaluator | done (local + Docker) | Reference 통과, 6종 bad patch 거부, `official=true` |
| Phase 2 agent | done (offline + Docker evaluator) | 3 task × mock/replay 6개 공식 run, 전체 trace와 valid patch 생성 |
| Phase 3 state machine | tool v2/context v3 retry hardening offline-complete | Current-diff submission gate와 exact rejected-patch next-request rehydration, structured no-generation budget event 검증 |
| Phase 4 recovery | done (offline hard-kill) | OS lock/atomic claim, postimage-write 중단 reconciliation, fresh interpreter resume와 9개 submission boundary에서 duplicate mutation/lifecycle 0 |
| Phase 5 memory | qualification/review path implemented, live trace/index pending | Memory-development 6/6, development-validation 2/2 |
| Phase 6 evaluation | historical v1 pilot complete, D-037 r3/r4 failures·r5 inconclusive·r6 controlled pass 보존 | R6 `run_73f5aaf7328a4ea5`: controlled/verified retry 1/1, official task와 qualification 23/23 pass |
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
stress schedule은 아직 실행되지 않았고, Live OpenAI development campaign과 96-run core
campaign도 완료가 아니며 `docs/08-limitations.md`에서 별도로 추적한다.

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
7번 external acceptance lane은 frozen core dataset과 분리된 후속 작업이다. 현재 다음
단계는 완료된 D-041 r5 25,000/200,000 contract와 `model-generation-block-v1` generic
terminal qualification evidence → 새 experiment/hash의 별도 승인 → terminal r5
inconclusive 보존 → D-043 controlled r6 profile의 offline 구현 → 승인된 r6
`run_73f5aaf7328a4ea5`의 terminal diagnostic pass까지 진행됐다. 다음은 별도 clean
execution hash와 승인을 받아 D-045의 fault-free tool-v2/context-v3 mini campaign pilot을 수행하고,
그 pilot이 evaluator와 `trace-qualification-v2`를 통과한 뒤 여섯 memory-development
task의 12-run no-memory campaign을 시작한다.

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

## Current live trace gate — mini primary campaign contract frozen

목표: 각 paid invocation 전에 실행 계약과 비용 경계를 machine-check하고, 단일 pilot의 완전한
trace를 증명한 뒤에만 12-run development campaign을 연다.

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
| 9 | blocked on new hash/approval | Fault-free mini development-validation campaign pilot 1회, $2 cap | `gpt-5.4-mini-2026-03-17`, 25,000/200,000, runtime contract의 `trace-qualification-v2`, `evaluation_reached=true`; success 여부와 분리 |
| 10 | blocked on order 9 | Memory-development 6 task × 2회, `no_memory`, $20 cap | 12 terminal rows 또는 structured halt/not-started ledger |
| 11 | pending eligible failures | Append-only failure review와 memory build | Reviewed qualified failure만 index source로 수용 |

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
mini snapshot으로 전환했다. Order 9는 별도 fault-free mini hash와 승인 전에는 실행하지
않는다.

Memory-development와 core live suite는 `gpt-5.4-mini-2026-03-17`, reasoning `medium`, mode
`standard`, service tier `default`, 25,000 max output token과 200,000 run-total budget을
고정한다.
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
Terminal r1/r2 suite와 run은 재사용하지 않는다. 다음 paid 실행 전에 rejected mutation
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

2026-07-29T22:39:42Z에 다시 확인한 `gpt-5.4-mini` standard rate는 1M token당 input $0.75,
cached input $0.075, output $4.50이며 별도 cache-write rate는 게시되지 않았다. 90,000-token
pilot은 exact input과 full 4,096-token response allowance가 남은 budget 안에 없으면
generation을 시작하지 않는다. Preflight의 $0.423432 reserve는 strict 90,000-token
runtime bound에 한 번의 4,096-token output allowance를 최고 rate로 더한 운영상 안전
margin이다. D-045 primary contract의 run reserve는 25,000/200,000에서 `$1.0125`,
12-run은 `$12.15`, 96-run은 `$97.20`이다.

### Historical pilots preserved; current mini campaign pilot pending

- 관련 unit/integration test와 Ruff가 통과한다.
- Approval 없는 `--preflight-only`가 API call 없이 execution hash와 blocker를 출력한다.
- 실제 환경에서 approval을 포함한 preflight가 `ready=true`다.
- 사용자가 $2 pilot을 별도로 승인한 뒤 historical r3가 `trace-qualification-v1`과
  `evaluation_reached=true` 당시 acceptance를 함께 통과했다.
- 새 v2 development suite는 historical r3/r5/r6를 고정하지 않는다. 같은 primary mini
  model/budget, harness
  commit, tool/context runtime-contract hash의 `trace-qualification-v2` pilot이 새로
  evaluator에 도달하기 전에는 `pilot_run_id`를 비워 두고 preflight를 차단한다. Pilot
  task success는 이 harness acceptance와 별도 outcome으로 보고한다.
- 12-run campaign은 새 clean commit의 no-call preflight, exact execution hash 검토와 별도
  $20 승인 전에는 시작하지 않는다.
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
않는다. 12-run development result는 아직 없다.

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
이 evidence는 당시 v1 pilot gate만 통과했으며, 현재 v2 development campaign gate에는
재사용하지 않는다. 12-run development campaign은 아직 실행하지 않았다.

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
