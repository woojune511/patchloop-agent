# Work Item 80 validation checkpoint

Historical audit only. This records the completed 2026-08-31 gate before Work Item 81's separate review.
It grants no candidate, rehearsal, provider, Docker, evaluator or cost authority.

Lean V27 (`v28/phase-evidence-v37`) was offline-qualified for strict-compatible direct/anchored reads,
final-schema admission before count/generation, and durable failed/uncertain count accounting. Two qualification
builds were byte-identical. This was not observed provider acceptance. No candidate, rehearsal or external call was
added. Exact qualification and predecessor-delta identities remain in `docs/09-evidence.md`.

The focused command was:

```powershell
uv run --offline --frozen pytest -o addopts= -q `
  tests/test_provider_schema_admission.py tests/test_provider_count_accounting.py `
  tests/test_provider_schema_runner.py tests/test_provider_schema_qualification.py `
  --basetemp .p80focused1
uv run --offline --frozen python scripts/build_lean_harness_provider_schema_qualification.py --check-only
```

The builder compared two deterministic in-memory builds with zero external/check calls. Guarded runner tests used fake
count/create methods and synthetic check/evaluator results, not real task evaluation. The standalone predecessor,
legacy adapter and consumed artifacts stayed byte-identical; five shared-file predecessor bytes were recoverable in
memory through the exact reverse delta. No consumed candidate was rebuilt as new evidence.

The selected regression command additionally included `test_workflow_r21_reliability_{successor,runner}.py`,
`test_workflow_plan_contract_compatibility_runner.py`, `test_workflow_bounded_request_context_runner.py`,
`test_workflow_self_directed_exploration_{successor,runner}.py`, `test_workflow_semantic_progress_successor.py`,
`test_workflow_semantic_progress_epoch_parity.py`, `test_workflow_causal_plan_projection_successor.py`,
`test_workflow_causal_alternative_successor.py`, `test_lean_runtime.py`, `test_tool_gateway.py`,
`test_model_adapter.py`, `test_rapid_r23_halted_audit.py` and `test_rapid_r22_prestart_stop.py`.
These are explicit filenames, not a PowerShell brace-expansion command.

The first broad run had 296 passes and 16 `test_batch_image_authority.py` fixture setup errors: the fixtures tried to
rebuild frozen candidate-v32 and correctly rejected the successor source hash. Historical admission was not weakened.
The final successor suite excluded those candidate-building fixtures and audited exact stored bytes instead.
Final run: 312 selected tests passed with `--basetemp .p80g2`; documentation 10/10 passed with `.p80docs1`.
Scoped Ruff, all 14 changed Python files' formatting and `git diff --check` passed. Qualification stayed byte-identical.

The checkpoint's next gate was a separate V27 activation review, not candidate creation or execution. R23 was already
consumed and halted; no earlier approval could transfer. Work Item 81's current disposition is owned by
`docs/current-status.md`, not this historical note.
