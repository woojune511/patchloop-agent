# PatchLoop

> Trace-Driven Coding Agent Reliability Harness

PatchLoop는 Python coding agent의 model/tool call, patch, checkpoint와 hidden evaluator 결과를
재현 가능한 artifact로 보존하고, 실패 memory 표현이 held-out 성능과 비용에 미치는 영향을
비교하는 실험 harness다.

현재 저장소에는 evaluator-first MVP와 offline end-to-end 경로가 구현되어 있다. 2026-07-27 현재
세 smoke task를 mock과 content-hashed replay로 각각 실행한 6개 agent run이 고정된 Linux Docker
evaluator에서 모두 공식 통과했다. 쉬운 자체 task 다섯 개는 calibration fixture로만 남기고,
SWE-rebench 계열의 실제 Loguru, AnyIO, tox, Hugging Face Hub, PDM #2781과 pyfakefs #991
사례 여섯 개를 memory-development task로, Moto #7208과 Babel #1042를
development-validation task로, SQLGlot #7187과 Param #1117을 core-cross-repo task로,
PDM #3759, AnyIO #1134와 Hugging Face Hub #4056을 core-same-repo task로 admission했다.
실제 OpenAI 96-run campaign과 나머지 7개 research task는 아직 완료하지 않았다. 미실행 gate는
[Current limitations](docs/08-limitations.md)에 분리했다.

## 구현된 핵심 경로

```text
public.yaml → stateless context builder → model adapter
            → constrained tool gateway → append-only events/checkpoints
            → submitted patch → separate hidden evaluator
            → deterministic SCRR verdict → experiment/report/viewer
```

- Pydantic v2 public/private task, run, event, checkpoint, tool, verifier, failure, memory 계약
- Local smoke와 Docker 공식 backend (`--network none`, resource limits, read-only root)
- Reference/no-op/regression/forbidden/dependency/tampering/public-API patch evaluator
- Mock/replay/OpenAI Responses adapters; OpenAI adapter는 `store=false`, current-turn context를 사용
- Registered `search_files`, `read_file`, `apply_patch`, `run_check`, `get_diff` 도구만 허용
- SQLite WAL event/checkpoint/action store와 SHA-256 content-addressed artifact store
- `action_id + input_hash` idempotency, context reset과 worker-kill-derived run
- Dataset role이 `memory-development`인 reviewed failure 전용 structured/raw memory index
- Seeded experiment runner, task-level bootstrap CI, JSON/CSV/HTML report
- FastAPI/Jinja/HTMX trace viewer와 host-only `gh` Issue/Draft PR adapter
- Memory/core/headline에서 제외되는 content-addressed calibration fixture 5개
- SWE-rebench revision, upstream issue/PR/commit, upstream license evidence와 Docker digest를
  고정한 Loguru, AnyIO, tox, Hugging Face Hub, PDM #2781, pyfakefs #991, Moto #7208과
  Babel #1042, SQLGlot #7187, Param #1117, PDM #3759, AnyIO #1134와
  Hugging Face Hub #4056 research task
- Task별 base hidden failure, reference 3회와 최소 5종의 known-bad를 기록한 admission evidence
- 후속 upstream 회귀까지 판별해 원래 AnyIO benchmark fix를 거부하는 hardened reference/oracle
- 실제 CLI grammar와 project precedence를 어긴 PDM #3759 benchmark fix를 거부하고
  maintainer follow-up을 채택한 hardened reference/oracle
- 확장자 없는 entrypoint를 process worker에서 복원하는 AnyIO #1134 exact-production
  reference와 module identity·metadata·exactly-once를 판별하는 독립 oracle
- 공유 reactive source의 branch fan-out 재계산을 판별하는 Param #1117 exact-production
  reference와 sync·coroutine·generator cache lifetime을 검증하는 독립 oracle
- file/snapshot download의 caller-owned progress 정책과 Hub-owned subclass 정책을 분리하는
  Hugging Face Hub #4056 exact-production reference와 adversarial combined-partial oracle

성공은 agent의 `DONE`이 아니라 다음 evaluator 결과의 논리곱이다.

```text
hidden acceptance
AND regression
AND scope policy
AND safety policy
```

## 5분 offline quickstart

Python 3.12와 `uv`가 설치된 PowerShell에서 실행한다.

```powershell
uv sync --extra dev
uv run patchloop task validate tasks/smoke/csv-quoted-newline
uv run patchloop eval-task tasks/smoke/csv-quoted-newline `
  --patch tasks/smoke/csv-quoted-newline/reference.patch --backend local
uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock --memory no_memory
uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model replay:replays/smoke/csv-quoted-newline.jsonl --memory no_memory
uv run pytest -q
```

`replays/smoke/*.jsonl`은 public task 정보만으로 만든 deterministic offline fixture다. Replay run은
repository-relative source 경로와 content hash를 immutable manifest에 기록하며, live model 결과나
memory experiment evidence로 간주하지 않는다.

Offline experiment와 report도 API key 없이 재현된다.

```powershell
uv run patchloop evaluate --suite experiments/smoke.yaml
uv run patchloop report --experiment offline-smoke --output reports/offline-smoke
uv run patchloop serve
```

Viewer는 `http://127.0.0.1:8000`에서 run manifest, trace, patch, verifier 결과를 보여준다.

## CLI

```text
patchloop doctor
patchloop task validate <task-dir>
patchloop dataset audit
patchloop eval-task <task-dir> --patch <patch> [--backend local|docker]
patchloop run --task <public.yaml> --model <mock|openai|replay:path> --memory <condition>
patchloop resume --run-id <run-id>
patchloop memory build --split dev-train
patchloop memory freeze --index <index-id>
patchloop evaluate --suite <experiment.yaml>
patchloop inject-fault --run <baseline-run-id> --fault <type>
patchloop report --experiment <id> --output <directory>
patchloop github import-issue <url> --output <public.yaml>
patchloop github draft-pr --run-id <id> --repo <checkout>
patchloop serve
```

## Live/OpenAI와 공식 campaign gate

Responses API adapter는 host process에서만 API key를 읽고 container, checkpoint, event payload에
전달하지 않는다. `experiments/core.template.yaml`은 다음 조건을 모두 만족하지 않으면 validation에
실패한다.

- 정확히 12개 held-out task, 네 memory 조건, task당 2회
- frozen dataset manifest content hash와 role 검증
- exact embedding revision
- dated price estimate가 $150 상한 이하
- `live_cost_approved: true`라는 명시적 승인

OpenAI integration은 공식 [Responses API migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses),
[function calling guide](https://developers.openai.com/api/docs/guides/function-calling),
[GPT-5.6 Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra)의 계약을 따른다.

## 문서

1. [Agent instructions](AGENTS.md)
2. [Project spec](docs/01-project-spec.md)
3. [Architecture](docs/02-architecture.md)
4. [Contracts](docs/03-contracts.md)
5. [Evaluation protocol](docs/04-evaluation-protocol.md)
6. [Implementation plan](docs/05-implementation-plan.md)
7. [Decisions](docs/06-decisions.md)
8. [Reproduction guide](docs/07-reproduction.md)
9. [Current limitations](docs/08-limitations.md)
10. [Dataset card](data/DATASET_CARD.md)
11. [Latest implementation evidence](docs/09-evidence.md)

## 한 문장 설명

PatchLoop는 coding agent의 trace를 실패 memory와 deterministic regression evidence로 변환하여,
harness 변경이 성공률·비용·안전성·복구 능력에 미치는 영향을 고정 조건에서 측정한다.
