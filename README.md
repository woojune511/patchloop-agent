# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair. The agent
is the product; hidden evaluation, recovery state and cross-run memory evidence are supporting layers.

## Current direction

A/B/C/D is deferred. Held-out R16's A/C difference is `-1/24`, not causal/general. Rapid R1-R24 are immutable
`official=false`; their completion/cost signals establish neither quality nor generalization. Exact current evidence
and limitations are in `docs/current-status.md` and `docs/09-evidence.md`.

## Implemented path

- INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW with constrained tools, append-only recovery and accounting
- Separate hidden evaluator with receipt-bound v2, opaque controls and authenticated completion
- Audited A-null/C-D110 design; candidate-bound schedule/runtime/cost and exact historical replay

Evaluator-v1 still assigns literal safety PASS. Historical authority is consumed; no pull, paid/B/D authority or
general memory claim exists. R22 candidate-v30 was stopped before batch start over an image-inspection count mismatch.
R23 halted after two settled rows for `$0.16285425`. R24 then halted after 3/6 settled rows for `$0.927549`; none reached
the evaluator and no V25/V27 comparison follows. Both are consumed and cannot retry/resume. Next offline work is in
`docs/current-status.md`.

## Offline quickstart

```powershell
$docsBasetemp = Join-Path (Get-Location) ('.pd-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
uv run --offline --frozen pytest -q -p no:cacheprovider --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

실행 trace는 provider/Docker 호출 없이 localhost에서 볼 수 있다.

```powershell
uv run --offline patchloop serve --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000`은 task, 토큰·비용, LLM 입출력, tool 호출과 task 결과만 표시한다.
qualification, checkpoint와 evaluator-private 원문은 이 화면에 투영하지 않는다.

Checks make no paid call. Execution needs qualified admission/runtime, a candidate, no-call output and exact approval.
Use `docs/00-index.md`; history lives under `docs/archive/`.
