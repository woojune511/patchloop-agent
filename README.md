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
completion-gate source are implemented. D-125 adds repository-local row-start consumption and mocked
fault-boundary finalization recovery source. It is BLOCKED, not an execution candidate or live authority.

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
- D-124 is the historical settlement-reconciliation predecessor. D-125 qualifies repository-local at-most-once
  row consumption and mocked process-fault finalization recovery only.
- D-125 passed 23/23 and D-124+D-125 passed 37/37. Row attestation 147 and finalization union 136 overlap and
  are never added. None is a repository-wide or live result.
- D-121 remains a deferred historical no-start isolation lane.
- D-125 has no executed reservation, result, candidate or execution hash. Provider, evaluator, agent, Docker
  and retrieval calls and added model cost are all zero; runtime memory injection and every A/C outcome remain
  unmeasured.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d125_ac_runtime_finalization_qualification.py
uv run python scripts/build_d125_ac_runtime_finalization_qualification.py --validate
uv run python scripts/build_d124_ac_settlement_reconciliation_correction.py --validate-sealed-historical
uv run python scripts/build_d123_ac_cost_completion_qualification.py --validate-sealed-historical
uv run python scripts/build_d122_ac_fixed_bundle_qualification.py --validate-sealed-historical
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

CLI availability does not imply authorization. The next approval may authorize only clean-source sealing,
fresh pricing and a no-call Docker/SDK/credential/endpoint preflight bound to exact D-125. Execution-hash or
candidate creation requires another gate, followed by separate candidate-triple/hash/$55-cap approval.

## Documentation

- `docs/00-index.md` — authority and navigation
- `docs/current-status.md` — current checkpoint and next gate
- `docs/01-project-spec.md` — product scope
- `docs/02-architecture.md` — runtime architecture
- `docs/03-contracts.md` — contract map
- `docs/04-evaluation-protocol.md` — current evaluation design
- `docs/05-implementation-plan.md` — remaining sequence
- `docs/06-decisions.md` — effective decisions
- `docs/07-reproduction.md` — supported validation commands
- `docs/08-limitations.md` — unsupported claims
- `docs/09-evidence.md` — machine evidence index
- `docs/archive/` — historical narrative snapshots

## One-line description

PatchLoop is a constrained, recoverable coding agent with a leakage-aware evaluation and failure-memory
pipeline whose exact four-run no-memory versus fixed-structured-memory runtime-finalization source path is
offline-qualified and BLOCKED before candidate creation and live authority.
