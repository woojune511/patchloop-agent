# Evidence index

This document links to canonical machine artifacts. It does not duplicate the full historical narrative,
which is preserved at `docs/archive/snapshots/d121/09-evidence.full.md`.

## D-125 A/C runtime-finalization source qualification

- Artifact: `reports/live-pilot/artifacts/d125-ac-runtime-finalization-offline-source-gate.json`
- Gate ID: `d125_ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539`
- Semantic body SHA: `sha256:ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539`
- File SHA: `sha256:9bc5f6e618f31312dc5026a807eabf478e47c05893cca72c71328378b593856e`
- File bytes: `13820`
- Status: `D125_AC_RUNTIME_FINALIZATION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED`

Canonical sources and tests:

- Qualification: `patchloop/evals/d125_ac_runtime_finalization_qualification.py`
- Builder: `scripts/build_d125_ac_runtime_finalization_qualification.py`
- Runtime: `patchloop/evals/runner.py`, `patchloop/agent/runner.py`, `patchloop/state/store.py`
- Tests: `tests/test_d125_ac_runtime_finalization_qualification.py`,
  `tests/test_ac_row_start_consumption.py`, `tests/test_ac_campaign_finalization.py`

D-125 binds exact sealed-historical D-124. It qualifies repository-local SQLite consumption plus a durable
row-start marker before paid execution, and mocked recovery around prepared-result fsync, result publication
and `CampaignCompleted` append. Recovery is idempotent and never reruns a row.

Gate tests passed 23/23 and D-124+D-125 passed 37/37. Row attestation 147 and finalization union 136 are
distinct within each set but overlap each other, so they are not added. Cross-store/global/cross-clone and
noncooperative-swap protection, actual kill and torn-write/power-loss durability remain unverified.

D-125 made zero provider/evaluator/agent/Docker/retrieval calls and added $0. It executed no reservation,
produced no result and created no hash or candidate. The next exact-D-125 approval can cover only clean source,
fresh pricing and no-call environment preflight; candidate creation remains separately gated.

## D-124 historical settlement-reconciliation correction

- Artifact: `reports/live-pilot/artifacts/d124-ac-cost-settlement-reconciliation-correction-source-gate.json`
- Status: `D124_AC_SETTLEMENT_RECONCILIATION_CORRECTED_EXECUTION_CANDIDATE_BLOCKED`

D-124 prospectively corrected final settlement reconciliation and is now validated only with
`scripts/build_d124_ac_settlement_reconciliation_correction.py --validate-sealed-historical`.

## D-123 historical A/C cost/completion source seal

- Artifact: `reports/live-pilot/artifacts/d123-ac-cost-completion-offline-source-gate.json`
- Gate ID: `d123_13fe44a6cc188de29dc38876fb60d114c8a777f8d05ad8b9db833b3d33cf4112`
- Semantic body SHA: `sha256:13fe44a6cc188de29dc38876fb60d114c8a777f8d05ad8b9db833b3d33cf4112`
- File SHA: `sha256:fab1543644ffefb9e4cda24d73207d3d9f66c07a5a1e006dec27a22699778e17`
- File bytes: `20953`
- Status: `D123_AC_COST_COMPLETION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED`

Canonical sources and tests:

- R2 plan: `experiments/ac-structured-pilot-v2.plan.yaml`
- R2 suite: `experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml`
- Runtime source: `patchloop/evals/runner.py`, `patchloop/agent/runner.py`
- Qualification: `patchloop/evals/d123_ac_cost_completion_qualification.py`
- Tests: `tests/test_ac_fixed_bundle_cost_completion.py`,
  `tests/test_d123_ac_cost_completion_qualification.py`

D-123 binds the exact D-122 predecessor and R1 bytes, then seals the R2 four-row cost control and completion
source. Its artifact remains immutable. Post-seal audit identified the emitter integration defect corrected by
D-124; D-123 is therefore historical rather than current source qualification. Validate it only with
`scripts/build_d123_ac_cost_completion_qualification.py --validate-sealed-historical`.

## D-122 historical A/C source qualification predecessor

- Artifact: `reports/live-pilot/artifacts/d122-ac-fixed-bundle-offline-qualification-source-gate.json`
- Status: `D122_OFFLINE_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED`

D-122 seals R1 A-null/C-exact fixed-bundle delivery and condition-aware qualification. It made no live calls,
candidate or execution hash. Validate only with
`scripts/build_d122_ac_fixed_bundle_qualification.py --validate-sealed-historical`.

## Historical/deferred D-121 preparation

The canonical receipt, preflight, candidate and gate are under `reports/memory-development/`. Eight no-start
Docker commands and one create verified configuration only; runtime isolation and successor execution remain
false. The exact deferred candidate identity appears in `docs/current-status.md` and its artifact.

## No-memory baseline

- Result: `reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json`
- Source/runtime gate: D-096/D-097 artifacts under `reports/live-pilot/artifacts/`

D-098 sealed 12/12 scheduled terminal rows, 11 official-evaluator rows, 2 resolved task pairs, 613 completed
provider responses, 11.375M tokens and usage-derived `$11.838408`. The missing evaluator row is an AnyIO
pre-provider token-budget agent failure. These figures are development evidence only.

## Structured-memory chain

| Stage | Canonical artifact | Establishes |
| --- | --- | --- |
| Admission | `reports/memory-development/d103-maintainer-assisted-admission-seal.json` | Three approved groups |
| Sources | `reports/memory-development/d104-three-rule-source-materialization-gate.json` | Exact generalized entries |
| Rendering | `reports/memory-development/d105-renderer-embedding-index-authorization-gate.json` | Exact leak-scanned model-facing text |
| Index build | `reports/memory-development/d106-locked-group-index-gate.json` | Unfrozen group-aware index |
| Token count | `reports/memory-development/d108-provider-token-count-completion-gate.json` | 2,193 vs 2,895 input tokens, +702 |
| Freeze | `reports/memory-development/d110-index-freeze-completion-gate.json` | Exact frozen three-entry index |
| Diagnostic | `reports/memory-development/d112-retrieval-readiness-completion-gate.json` | 9 local score rows, all no-match |
| Validator correction | `reports/memory-development/d114-d112-validator-correction-gate.json` | Portable sealed-historical replay |
| Policy decision | `reports/memory-development/d115-score-policy-decision-source-gate.json` | Threshold/weight-only correction deferred |

None of these artifacts records runtime memory injection or a memory-conditioned agent outcome.

## Deferred applicability/isolation chain

- D-116: deterministic public-applicability contract, no classifier execution
- D-117: grammar-blind acquisition protocol, no pool acquisition/review
- D-118: opaque source bytes, blocked on preexistence/cutoff/isolation
- D-119: partial consumed isolation attempt, probe outcome unknown
- D-120: append-only failure seal and successor preparation candidate
- D-121: no-start successor preparation, actual run unauthorized

These artifacts remain valid but are off the immediate fixed-bundle A/C critical path.

## Historical documentation snapshot

The exact pre-reorganization active documents are under `docs/archive/snapshots/d121/`. See
`docs/archive/snapshots/d121/snapshot-manifest.json` for original paths, byte sizes and SHA-256 values.

The snapshot is historical evidence, not current authority. Its source worktree was dirty relative to HEAD;
the manifest records that limitation explicitly.
