# Work Item 82 validation — 2026-09-01

Recorded offline validation and candidate preparation only. This grants no paid authority, provider acceptance,
agent-performance claim, historical retry or resume. Work Item 83 requires fresh exact user approval.

## Implemented scope

- R24 candidate-v33: V25 control/V27 treatment, three rows each, unchanged AnyIO-v5/model/image/no-memory/budget/evaluator.
- Exact live manifest registry plus `candidate-bound-pre-count-request-admission-v1` on both arms, before count/create.
- Actual public-task/model initial request assembly through production context, Lean projector and adapter. Its
  pre-action prefix is synthetic: this does not predict future run/event bytes, token counts or post-count budgets.
- Rehearsal stops before the first count SDK call. Its typed one-use receipt never grants live transport authority.
- Separate public smoke fake-provider correction and review paths for both V25 and V27; no AnyIO trajectory is inferred.
- Live preflight verifies the stored qualification read-only, without rerunning synthetic qualification mocks.

## Mechanical friction discovered offline

The first two V25 dynamic smoke cases stopped at an empty-argument schema: frozen `get_diff`/`finish_task` omit
`required`, whereas V27's original local validator requires an explicit array. This is not the R23 nonempty-read defect.
The shared R24 gate projects `required=[]` only onto a validation copy of closed, propertyless objects. Wire bytes,
frozen V25/V27 definitions and the frozen V27 validator stay unchanged. Nonempty missing requirements, malformed
required values and open empty objects still fail before SDK dispatch. Both versions' correction/review cases then passed.

The [OpenAI strict-mode contract](https://developers.openai.com/api/docs/guides/function-calling#strict-mode)
requires closed objects and required fields. [JSON Schema required semantics](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.5.3)
equate absence with an empty array; on a closed object with no properties both accept only `{}`. This equivalence
does not establish vendor acceptance. No model-facing repair or task-specific policy was introduced.

## Final commands and observed results

118 related regression/audit tests passed with `.p82reg1`:

```powershell
uv run --offline --frozen pytest -o 'addopts=' -q -p no:cacheprovider --tb=short --basetemp=.p82reg1 `
  tests/test_provider_schema_admission.py tests/test_provider_count_accounting.py `
  tests/test_provider_schema_runner.py tests/test_workflow_plan_contract_compatibility_runner.py `
  tests/test_workflow_r21_reliability_successor.py tests/test_workflow_r21_reliability_runner.py `
  tests/test_workflow_plan_admission_feedback_successor.py tests/test_workflow_plan_admission_feedback_runner.py `
  tests/test_workflow_bounded_request_context_runner.py tests/test_rapid_batch_driver.py tests/test_rapid_cli.py `
  tests/test_rapid_r23_halted_audit.py tests/test_rapid_r22_prestart_stop.py
```

48 current integration/artifact/documentation tests passed with `.p82final1`, after artifact materialization:

```powershell
uv run --offline --frozen pytest -o 'addopts=' -q -p no:cacheprovider --tb=short --basetemp=.p82final1 `
  tests/test_rapid_public_development_v27.py tests/test_provider_request_gate_runner.py `
  tests/test_rapid_public_development_v27_qualification.py tests/test_documentation_structure.py
uv run --offline --frozen ruff check patchloop tests scripts
git diff --check
```

Changed-file Ruff formatting check passed for 14 Python files. Global pre-existing formatting debt was not rewritten.
Before freezing, the qualification's complete no-call path was exercised twice in memory with
`candidate_created=false`/`rehearsal_created=false`. Three artifact-dependent tests were then unskipped and passed.
Historical current-source builders were not weakened or regenerated after integration; preservation is checked by
the new binding, not by changing old qualification hashes.

## Materialization

`build_rapid_public_development_v33_candidate.py` ran once. `run_rapid_public_development_v33.py --mode rehearse`
ran twice, as did `build_rapid_public_development_v27_qualification.py`. The two persisted receipt reconstructions
and the two qualification outputs respectively matched byte-for-byte. Candidate-bound runtime/script/test sources
were not edited after candidate freeze; only documentation was finalized.
Exact artifact tuples are in `docs/09-evidence.md` and the machine artifacts it names.

Six public initial requests reached their pre-count boundaries with zero SDK calls. The separate isolated mock
qualified one image-inspect adapter invocation, six real row starts, six pre-count gates and six generation gates.
Its synthetic settled terminals are not agent/evaluator outcomes. No real Docker, provider, evaluator, visible-check,
network or cost activity occurred in artifact generation; related offline regressions can use local smoke fixtures.
Official documentation lookup is not an experiment/provider call.

39 reviewed source identities recover exactly after removal of marked additive integration blocks. Nine predecessor
artifacts plus frozen V27 qualification/review bytes match their original hashes. No historical artifact was rewritten.
The production R24 result bundle and image-attempt receipt do not exist. No production approved plan was issued.

## Authority and next action

Execution hash: `sha256:a4a8e75dfa0f1ae1365ef991b48cf18bd61f3dd717cf8d4d1bedff392236592e`.
Reserve/cap: `$7.20`/`$7.50`, six rows, one exact local-image identity check. Image pull/build/tag/remove/prune is excluded.
Provider/Docker/evaluator execution remains unapproved. R23 and all prior consumed campaigns stay closed.
