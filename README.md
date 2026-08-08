# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for studying whether structured
failure memory improves scope-compliant software repair. It keeps agent execution, hidden evaluation,
durable recovery state and cross-run memory evidence separate so that reliability work is not mislabeled
as memory-driven improvement.

## Current direction

The full A/B/C/D, 96-run campaign is deferred. The immediate target is a four-run development-validation
readiness panel with an exact, checked-in suite:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

`experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml` fixes the four rows, while
`experiments/ac-structured-pilot-v2.plan.yaml` preserves the design boundary. Fixed-bundle delivery,
condition-aware qualification, full-schedule cost reservation/settlement source and the complete-matrix
completion-gate source are implemented. D-125 is the historical local/mock finalization source predecessor.
D-126 remains the latest sealed gate. D-127 successor source implements the production-client correction,
replayable pricing capture and exact-identity Docker/no-call orchestration. Its append-only approval receipt
exists; static source admission and downstream evidence remain pending.

See `docs/current-status.md` for the current checkpoint and closed authority.

## Implemented product path

- Agent phases: INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE
- Constrained tools for literal search, bounded reads, tracked-file patching, registered checks, diff review
  and submission
- Stateless provider turns rebuilt from durable public state
- Append-only events, checkpoints, CAS artifacts and workspace/diff reconciliation
- Rejected-patch recovery and exact token/cost accounting
- Separate hidden evaluator for acceptance, regression, scope and safety
- Audited dataset registry with calibration, development, validation and held-out roles
- Human-reviewed structured memory sources, deterministic rendering and a frozen three-entry index
- Exact A-null/C-D110 manifests, request/CAS/context replay evidence and condition-aware trace qualification

## Evidence boundary

- D-098 completed the 12-row no-memory development baseline; 11 rows reached the official evaluator and
  2/12 were scope-compliant successes. This is development evidence, not a held-out performance claim.
- D-110 froze the approved three-entry memory index.
- D-112/D-115 showed that the current selective scorer cannot be repaired by threshold/weight changes alone.
- D-124/D-125 are historical local/mock predecessors. D-126 sealed clean source, fresh pricing and bounded
  no-call observation, but not readiness.
- D-121 remains a deferred historical no-start isolation lane.
- D-126 has no executed reservation, result, candidate or execution hash. Provider, evaluator, agent,
  retrieval and injection counts and cost are zero; every A/C outcome remains unmeasured.
- D-127 is pre-external: receipt recorded, static pending, API key absent and production calls zero.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d126_clean_source_pricing_no_call_preflight.py
uv run python scripts/build_d126_clean_source_pricing_no_call_preflight.py --validate-post-commit
uv run pytest -q tests/test_documentation_structure.py
git diff --check
```

These paths validate sealed local evidence only. There is intentionally no supported live A/C command.

## CLI surface

```powershell
uv run patchloop --help
uv run patchloop agent run --help
uv run patchloop experiment preflight --help
uv run patchloop experiment run --help
uv run patchloop report --help
```

CLI availability does not imply readiness. The approved D-127 scope stops at blocker remediation, official
pricing capture and a repeated no-call preflight. It currently stops before external activity because the
receipt exists, but static is pending and `OPENAI_API_KEY` is absent. A ready successor still requires
separate exact-gate approval before hash/candidate preparation and later live approval.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.

## One-line description

PatchLoop is a constrained, recoverable coding agent with a leakage-aware evaluation and failure-memory
pipeline whose exact four-run no-memory versus fixed-structured-memory runtime-finalization source path is
offline-qualified, whose D-126 preflight is sealed blocked, and whose D-127 successor remains pre-external.
