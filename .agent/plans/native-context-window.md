# Native context-window lifecycle — implementation plan

Status: all three phases implemented and locally verified, 2026-09-13.
Final phase 3: `C:\pt\validation\native-compact-runner-final-20260913`; 44 new tests,
109 compatibility cases, 1,803 full-suite PASS/four Docker skips, Ruff and mock PASS.
The opt-in pilot packet is prepared at `C:\pt\analyses\native-compaction-pilot-design-20260913`:
T=60000, one new mini/medium/v2 run, proposed shared $2 conditional budget. Its exact
execution approval is still missing; this is neither a default nor an optimal T claim.

Earlier layer receipts (superseded implementation status, immutable evidence):
Phase 2 receipt: `C:\pt\validation\native-compact-adapter-20260913`;
60 adapter tests/9.586s plus 100 compact/transport regressions/30.395s PASS.
Full 1,759 PASS/four real-Docker opt-in skips, longest worker 362.932s; Ruff PASS.
Mock `run_dev_702e01bb86114453` reaches isolated acceptance PASS in 4.628s (cost zero).
One old compact response revalidates without altering any of its 23 ordered items.
Shared validation/transport/cost and durable response handoff are implemented;
scheduler/window activation/ledger were not yet connected at that earlier layer.
Receipt: `C:\pt\validation\native-window-20260913`; 138 focused tests/61.77s,
1,699 full-suite PASS/four Docker opt-in skips, longest worker 382.43s, Ruff PASS.
65 saved input replays preserve evidence; opt-in mock reaches isolated evaluation.
Design authority baseline: `240f89c72cc47c2ddbabae5ea31247d0915eccdd`; native runtime
`sha256:565b95609b8fc0015ac6523d52875d2ba7b2cf240f23be5183ebbd5b48229659`.

## 1. 목적과 범위

전체 기록을 지우는 대신, 보존용 기록과 모델의 현재 작업 창을 분리한다.
기본 모드는 그대로 두고 새 run의 opt-in `native-window-v1`에서 검증한다.
추가 planning tool, 메모 작성 의무, model 교체, tool mask 변경은 하지 않는다.
`store=false`, encrypted continuation, exact replacement, 40 model / 100 tool /
4 accepted mutation / 1,800초 및 기존 생성 출력·비용 admission을 유지한다.

두 문제는 별개다.

- 상태 설명 누적: 기존 65개 요청 분석의 byte 감소 상한은 31.47~37.53%다.
  이는 안전한 최종 절감률이나 token·품질 개선의 증거가 아니다.
- 개별 암호문 길이 거부: B2 tail 증가의 99.14%는 새 item 하나였다.
  현재 상태 교체나 압축이 같은 현상의 재발을 막는다고 주장하지 않는다.

근거는 `C:\pt\analyses\native-input-audit-20260913\result.md`와 기존
`compaction-live-20260912`, `compaction-snapshot-live-20260913`이다.
정상 checkpoint의 compact는 성공했으나 기존 메시지 22개를 전부 유지했다.
따라서 compact만 추가해 상태 누적까지 해결할 수는 없다.

## 2. 하나의 run, 별도의 작업 창

기존 journal/CAS는 모든 turn input, 공개 관찰, encrypted continuation,
mutation/check 결과를 원본 그대로 보존한다. 새 database나 cross-run memory는 없다.
Gateway의 관찰·mutation admission·현재 PASS 권한도 계속 이 기록과 현재 파일에 둔다.
Compaction 결과로 소스 관찰이나 검사 성공을 새로 인정하지 않는다.

모델 입력의 관리 단위만 다음으로 나눈다.

| 부분 | 수명과 규칙 |
|---|---|
| 고정 seed | 첫 window의 system/초기 state/단일 user task, 이후에는 compact의 전체 output. 해당 window 안에서 불변 |
| 공개 역사 evidence | 교체될 snapshot에만 있는 실제 관찰과 compact 뒤 명시적으로 복구한 공개 이력. 동일 사실은 한 번, 과거 권한은 현재 권한 아님 |
| 새 native 교환 | seed 이후 reasoning/call/output의 원문·ID·순서 유지. 병렬 batch 전부 포함 |
| 현재 snapshot | 전체 최신 공개 상태 하나. 이전 snapshot의 현재성 설명만 교체 |

첫 window에서도 이 규칙을 적용한다. 압축 후부터 적용하면 압축 seed 안에 이미
쌓인 옛 상태는 다시 제거할 수 없기 때문이다. 최초 초기 state와 compact 내부에
보존된 state는 historical seed이며, 우리가 만드는 post-seed current view는 하나다.
새 user 메시지나 실행한 적 없는 function_call_output을 만들지 않는다.

기존 `single-user-append-only-state-v3`는 default에서 그대로 유지한다.
새 serializer/validator는 `single-user-managed-window-v1`로 분리하고,
전체 이전 input이 prefix라는 조건 대신 seed 불변·native 교환 순서·evidence 보존·
최신 state hash를 검증한다. 현재 state는 seed의 임의 메시지를 재해석하지 않고
명시적으로 결속한 최신 view에서 읽는다. `public_task`는 run 전체에서 불변이다.

새 window metadata는 window ID, seed artifact/hash, 이전 input hash,
마지막 반영 decision/batch ID, current-state/evidence-inventory hash,
선택적인 compaction receipt를 갖는다. 완성된 model-input CAS는 기존처럼 별도
기록한다. 거대한 별도 transcript 복제나 in-memory 상태만으로의 복원은 피한다.

## 3. Snapshot 교체와 공개 evidence 보존

기존 진단의 latest-state projection과 source resolver를 범용 순수 함수로 추출한다.
Runtime이 `diagnostics`를 import하지 않게 하고, 기존 진단은 같은 helper를 재사용한다.
이동 전후 기존 진단 packet의 역사적 bytes는 수정하지 않는다.

- 교체 대상은 우리가 만든, seed 밖의 인식된 snapshot뿐이다.
  provider 반환 window와 native 교환은 snapshot처럼 삭제하지 않는다.
- 현재 budget/gate/tools/check currency, full diff, 살아 있는 notes, correction은
  최신 snapshot만 권한을 가진다. 필드 누락은 삭제이며 과거 값 상속이 아니다.
- 삭제 대상에만 있는 complete source line, mutation/check/probe receipt와
  공개 observation의 고유 버전은 quoted historical evidence로 먼저 보존한다.
  action/input/diff/file identity와 최초 관찰 순서를 유지한다.
- Source identity는 path + raw-file hash + inclusive line + LF 본문이다.
  겹치는 동일 범위는 병합하고, 미관찰 gap·CRLF/raw hash 차이·alias dependency는
  기존 의미를 유지한다. workspace를 자동으로 읽어 보충하지 않는다.
- 알려진 mutable control만 만료 대상으로 분류한다. 알 수 없는 공개 observation은
  보수적으로 보존한다. 모든 dict를 임의의 prose summary로 바꾸지 않는다.
- 해소된 질문, 만료된 note 해석, 소비된 correction을 새 메모/지시로 복구하지 않는다.
  현재 공개 task·실패·완료 조건과 살아 있는 notes는 그대로 제공한다.

Byte 절약을 위해 도구 결과와 소스 본문을 매 turn 다시 펼치지 않는다.
현재 source/delivery reference는 **현재 window에 실제로 들어 있는** native 또는
quoted public evidence를 대상으로만 만든다. 불충분하면 이미 관찰한 필요한 본문을
inline으로 제공한다. 보존 창 밖 CAS에만 있는 ID나 암호문을 본문 delivery로 부르지 않는다.
현재 24,000자 working-set 선택과 최신 batch 전체 전달은 바꾸지 않는다.
누적 역사 evidence에 새로운 lossy cap을 추가하지 않는다.

동등성 검사는 source facts, 공개 exchange 버전, harness observation 버전,
현재 state, native 순서를 각각 비교한다. 옛 observation이 native output에도 있다는
것은 필드 이름만으로 판단하지 않는다. 입증되지 않으면 그대로 보존한다.

## 4. 정상 경계에서만 선택적인 compaction

첫 구현은 standalone compact, 같은 mini snapshot, `service_tier=default`,
run당 최대 1회로 제한한다. 서버 자동 compaction, reasoning reset, 재압축 loop는 제외한다.
공식 문서에 따라 반환 output **전체와 순서를 그대로** 새 seed로 쓴다.
Opaque 내용의 의미 보존을 byte 검사로 증명했다고 말하지 않는다.
[OpenAI Docs: compaction](https://developers.openai.com/api/docs/guides/compaction)

`--context-policy native-window-v1`만으로는 API compact를 켜지 않는다.
별도 `--compact-at-input-tokens T`와 조건부 예약에 대한 명시적 acknowledgement가
있어야 scheduler를 켠다. T는 사전 실행 계약의 양수이며 모델 input limit보다 작다.
이번 설계에서 T를 97,810 또는 turn20에 맞춰 고정하지 않는다. 정확한 수치는
provider-free 요청 증가 replay를 보고 다음 live packet에서 정하며 실행 중 적응시키지 않는다.

Scheduler 순서:

1. 기존 provider/count 불확실성 검사를 먼저 통과한다. Pending decision/action,
   mutation reconciliation, 전체 병렬 batch와 repair-recheck를 먼저 끝낸다.
2. 끝난/중단된 run은 그대로 반환한다. 정상 action batch 완료 경계에서만 압축을
   고려한다. 미소비 protocol correction이나 reasoning-only incomplete가 있으면
   기존 correction 경로를 유지하고 사후 compact 복구를 시도하지 않는다.
3. Gateway의 projection과 완료 하한 B를 계산한다. 새 응답 자체가 불가능하면
   기존 horizon terminal로 끝낸다. 그렇지 않으면 정확한 후보 입력을 만든다.
4. 외부 CAS와 준비 boundary에 후보 입력·현재 state·schemas·반영된 exchange ID를
   고정한 뒤 기존 count endpoint로 계수한다. 정상 경로의 count 하나를 재사용하며,
   threshold 확인만을 위한 매 turn 추가 count는 만들지 않는다.
5. `I >= T`이고 후보가 승인된 input envelope 안에 있으며, 1회 allowance·시간·
   compact 비용 예약과 추가 model 1회를 소비한 뒤에도 B가 남으면 compact를 실행한다.
   낮은 예산 때문에 선택적 압축을 못 하는 것만으로 원래 가능한 action을 차단하지 않는다.
6. 응답 usage와 검증된 output을 receipt에 원자적으로 기록한 뒤 window를 전환한다.
   최신 공개 상태와 잔여 예산을 재투영하고 **새 입력 전체를 다시 count**한다.
   압축 전 count는 변경된 생성 요청의 count로 재사용하지 않는다.
7. 최종 input/tools/count가 결속된 `turn_started`를 기록하고 생성 admission을 한다.
   이미 반영된 이전 response/batch를 다시 append하거나 실행하지 않는다.

준비 boundary는 model decision이 아니다. 압축을 하지 않으면 그 후보가 최종 turn의
input이 되고, 압축을 하면 source boundary로만 남는다. Count 이벤트는 boundary ID와
request hash를 결속하고 최종 turn이 사용한 count ID를 명시한다. 완료된 같은 요청의
count는 resume에서 복구할 수 있지만, projection이나 tools를 바꾸면 새 count가 필요하다.
Count pending/실패는 기존 원칙대로 중단하며 count 대신 compact로 우회하지 않는다.

압축 시 공개 이력을 opaque item에만 맡기지 않는다. 기존에 명시적으로 전달된 공개
교환·source facts·harness receipt 중 반환 seed의 검증 가능한 공개 부분에 없는 것은
한 번의 quoted archive로 복구한다. Retained 공개 item은 원본과 대응시키고, 실제로
보존된 것은 중복 복사하지 않는다. 현재 선택된 source의 delivery와 alias를 이 archive에
다시 연결한다. 이를 매 turn 큰 reentry 문자열로 펼치지 않는다.
새 system 재진술이 필요하면 원래 계약과 동일한 내용을 한 번만 붙이며, seed 안의
동일 system이 이미 확인되면 추가하지 않는다. 최신 view가 exact public task를 명시한다.

단일 거대 encrypted item은 별도 미해결 경계다. 측정·hash·provider error는 보존하지만
문자수에서 토큰수/비용/안전 상한을 추정하지 않는다. 자르기, 누락, 25k 축소,
이전 checkpoint로 몰래 되돌리기, count 우회 생성, 실패 후 자동 재시도는 하지 않는다.
입력 한도를 넘거나 같은 per-field 오류가 나면 기존 terminal과 오류 증거를 보존한다.
압축 후에도 더 큰 window가 반환될 수 있으므로 실제 최종 count/admission이 권한이다.

## 5. 비용·실행 시간·복원 계약

Compact에는 `max_output_tokens`와 reasoning effort 인자가 없다. 생성의 25k 상한을
compact에 적용했다고 말하지 않는다. 정확한 model/rate/예약 근거를 envelope에 결속하고
기존 진단의 model-limit-based reservation을 재사용하되 endpoint가 보장하는 과금
상한이 아닌 **조건부 계획 예산**임을 표시한다. Count billing과 invoice 미확인은 별도다.
[OpenAI Docs: compact parameters](https://developers.openai.com/api/reference/python/resources/responses/methods/compact)

기존 `--max-cost-usd`를 자동 증액하지 않는다. 켜진 모드의 shared ledger에는 generation과
compact의 알려진 비용을 모두 넣는다. 조건부 예약을 받아들이지 않는 엄격한 과금 상한
요청에서는 compact를 dispatch하지 않는다. 가격·usage 불확실성, 예약 초과 또는 client
cleanup 불확실성은 뒤의 유료 호출과 남은 repetition을 중단한다.

Compact dispatch는 기존 40 model-call 예산 중 1회를 사용하되 tool action이나 accepted
mutation으로 세지 않는다. 결과에는 decision/compaction 호출 수를 분리해서 표시한다.
생성 호출을 위한 B가 남지 않으면 선택적인 compact를 하지 않는다. 전체 active deadline을
같이 쓰고 compact용 새 1,800초 timer를 만들지 않는다. Timeout 뒤 task 실행은 없다.

가장 작은 durable 전이는 준비 boundary, `compaction_started`, atomic receipt,
`context_window_activated`다. Receipt는 source input/seed/policy hash, output artifact와
item-order hash, 검증 상태, usage/accounting, response ID, active elapsed를 묶는다.
Usage를 확보했다면 output 계약 실패에도 남긴다. Journal에는 ciphertext 본문을 넣지 않는다.

| Crash 지점 | 재개 시 동작 |
|---|---|
| 준비/count 완료 뒤 compact dispatch 전 | 같은 준비 상태와 count를 복구; 아직 시작하지 않은 action만 진행 가능 |
| compact started 뒤 durable 결과 없음 | 재요청 없이 `PROVIDER_TIMEOUT_OR_UNKNOWN`; 이후 실행 없음 |
| usage만 durable, 검증된 window 없음 | 알려진 비용은 복구하되 window 생성은 재시도하지 않고 중단 |
| atomic receipt 뒤 activation 전 | receipt hash를 검증하고 같은 window를 한 번 활성화; compact 재호출 없음 |
| activation 뒤 최종 generation 전 | 저장된 새 seed·tail·snapshot/correction과 counters를 복구 |
| 최종 generation 응답 또는 tool batch 기록 도중 | 기존 decision replay/action reconciliation을 먼저 수행 |

Window 손상/부적합 output은 `PROVIDER_CONTINUATION_ERROR`, count 불확실성은 기존
count terminal, 비용은 `COST_CAP_REACHED`, deadline/B 부족은 `LIMIT_REACHED`를 사용한다.
새 terminal enum이나 run schema는 만들지 않는다. 이미 terminal인 run은 read-only로 반환한다.

Run request/envelope/model identity에는 context policy, T, 1회 한도, 예약/가격 계약과
acknowledgement를 결속한다. Tool 입력 schema·순서는 그대로지만 전달/복원 의미가
달라지므로 phase 1에서 tool-surface를 v37로 올렸고, phase 3에서는 v38로 올렸다.
현재 context policy, T/예약, 준비 입력의 계수와 압축 활성화·복원까지 결속한다.
기존 envelope/journal migration은 하지 않고 runtime 불일치 resume 거부를 유지한다.
새 모드의 문서화된 opt-in 외 default 동작은 바꾸지 않는다.

## 6. 구현 순서와 변경 위치

1. **순수 작업 창부터 — 구현됨:** `conversation.py`, `native_sources.py`, `model_state.py`에
   snapshot/archive 의미를 연결한다. 진단의 source/evidence helper를 runtime 쪽 작은
   module로 추출하고 기본 append 경로 bytes가 동일한지 고정한다. 얇은 CLI/request/
   runner 연결과 seed/이전 input/evidence 복원 검증을 포함한다. Compact 호출 없음.
2. **압축의 durable 어댑터 — 구현됨:** 기존 `compaction_state`의 validation/receipt,
   transport의 deadline/cleanup, `compaction_cost`의 예약 의미를 필요한 만큼 추출한다.
   새 agent framework나 일반적인 remote transaction framework를 만들지 않는다.
3. **압축 Runner 연결 — 구현·무호출 검증 완료:** prepared-input/count 경계, activation, shared ledger/counters,
   `_build_model_input`, `_load_active_model_input`, `_validate_recorded_continuations`,
   `_restore_counters`, `DevJournal.provider_usage`와 unresolved-work 검사를 갱신한다.
   Compaction receipt를 가짜 tool decision으로 기록하지 않는다.
4. **무호출 검증과 문서 — 완료, 실행 packet 준비됨/승인 대기:** opt-in/default, 실패와 resume을
   검증했다. 새 44개/기존 109개 집중 검사, Ruff, 전체 1,803 PASS/4 skip와 mock
   격리 평가를 통과했다. 이 완료만으로 paid 실행이나 default 채택을 하지 않는다.

각 변경에 contracts와 focused tests를 함께 넣는다. 3번은 v38로 연결하며,
`--compact-at-input-tokens T`와 `--accept-compaction-model-limit-reservation`을
별도로 요구한다. 다음은 검증 결과를 결속한 새 실행 packet이며, 이 구현 승인으로
압축 API 실행이나 default 채택이 승인되지는 않는다.

## 7. 완료 조건과 다음 live의 해석

- Snapshot: source facts/공개 교환/고유 receipts 보존, 현재 notes/correction/check
  currency 동일, helper 탐색 뒤 핵심 evidence 유지, no-op 재구성 동일.
- Reference: LF/CRLF, adjacent union/gap, backward mutation alias, 서로 다른 raw hash,
  archive 안에서의 delivery, 없는 ID와 미관찰 범위, inline fallback을 검사한다.
- Window: compact output 전체 불변, 전체 병렬 batch 정확히 한 번, source task 불변,
  stale snapshot의 PASS가 현재 PASS로 복귀하지 않음, unsupported output은 salvage 금지.
- Scheduler: threshold 경계와 run당 1회, no-op에는 count 추가 없음, compact 뒤 recount,
  후보 count와 최종 request hash 연결, model B/B+1 경계, completion 후 compact 없음.
- Recovery: 위 crash 표 전체, concurrent run lock, receipt 변조·window 손상,
  비용/시간/최신 exchange cursor 복구, terminal resume idempotency.
- Privacy: private spec/hidden path/reference patch/plaintext reasoning sentinel 없음.
  압축 응답에 허용되지 않은 plaintext가 있으면 그대로 저장하지 않고 계약 실패로 처리한다.
- 기존 65개 요청은 read-only fixture로 사용한다. 새 projection은 구성·byte 비교용이며
  기존 agent가 성공했을 것이라는 반사실적 성능 증거로 해석하지 않는다.
- Focused tests → Ruff → 외부 short temp root의 fast suite → mock smoke 순서.
  Mock은 repair/check/finish/isolated evaluation까지 도달시키되 live/품질 증거로 부르지 않는다.
  집중 검증 2분 목표와 실제 시간을 구분해 기록한다.

향후 live에서는 입력 구성의 정확성, 실제 token/byte 증가, compact 비용·시간,
도구 행동과 수정·검사·제출을 따로 평가한다. 표본이 줄거나 입력이 작아진 사실을
품질 향상으로 대신하지 않는다. 이번 설계는 거대 암호문 길이 문제의 해결 증거가 아니다.

기존 task package, `.env`, user-owned `AGENTS.md`, untracked 작업, 외부 run,
`reports/`, `experiments/`, `docs/archive/`는 수정하지 않는다. Docker 시작/pull/build,
provider/count/compact 실행과 추가 live row는 별도 정확한 승인 없이는 하지 않는다.
모든 결과는 `official=false`다.
