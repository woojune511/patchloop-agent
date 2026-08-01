# PatchLoop Agent Guide

이 파일은 repository 전체에 적용된다. PatchLoop에서 작업하는 coding agent는 구현 전에 이 문서와 현재 milestone 문서를 읽어야 한다.

## Mission

재현 가능한 평가 기반 위에서 single coding agent를 실행하고, trace-driven failure memory와 recovery 정책의 효과를 공정하게 비교한다.

Repo Maintainer와 Draft PR은 데모다. 평가 harness와 실제 실험 결과가 제품의 핵심이다.

## Current state

- Evaluator, constrained offline agent, state/recovery, memory, experiment/report와 viewer의
  implementation baseline이 존재한다.
- 현재 milestone은 `D-071 D-070 immutable live evidence sealed; structured
  coverage-rejection feedback offline correction pending`이다.
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
  D-071 evidence seal 회귀는 991 collected, 984 passed/7 environment-dependent skipped이며 Ruff와
  `git diff --check`도 통과했다. 이 seal 과정의 provider call과 추가 model cost는 0이다.
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
