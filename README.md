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
D-126 sealed clean-source, pricing and no-call environment observations, but five blockers keep it BLOCKED
before execution-hash or candidate creation.

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
- D-124/D-125 are historical settlement/finalization predecessors; their local/mock limits remain.
- D-126 binds source commit `68b7c8b0779a33443a4a4e5ae423e3c64e0e1d22`, fresh official pricing and
  a no-call observation. Docker used 12 read-only commands, including 6 daemon reads and zero workloads;
  the SDK probe made zero network calls.
- D-121 remains a deferred historical no-start isolation lane.
- D-126 has no executed reservation, result, candidate or execution hash. Provider, evaluator, agent,
  retrieval and injection counts and cost are zero; every A/C outcome remains unmeasured.

Machine-readable evidence is indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --extra dev
uv run pytest -q tests/test_d126_clean_source_pricing_no_call_preflight.py
uv run python scripts/build_d126_clean_source_pricing_no_call_preflight.py --validate-post-commit
uv run python scripts/build_d125_ac_runtime_finalization_qualification.py --validate-sealed-historical
uv run python scripts/build_d124_ac_settlement_reconciliation_correction.py --validate-sealed-historical
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

CLI availability does not imply authorization. The next approval may only resolve all five D-126 blockers,
close the non-replayable pricing-provenance gap and repeat an exact no-call preflight. A ready successor still
requires separate exact-gate approval before hash/candidate preparation and later live approval.

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
offline-qualified, no-call-preflight observed and BLOCKED before candidate creation and live authority.
