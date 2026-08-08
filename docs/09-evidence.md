# Evidence index

This document links to canonical machine artifacts. It does not duplicate the full historical narrative,
which is preserved at `docs/archive/snapshots/d121/09-evidence.full.md`.

## D-126 clean-source/pricing/no-call preflight

- Receipt `reports/live-pilot/artifacts/d126-ac-clean-pricing-no-call-preflight-approval-receipt.json`:
  ID `d126approval_596fd109a08fefbfc7e3075fd89879015ef5c78c5caa72353c45bf3ccbec2ae0`;
  body `sha256:596fd109a08fefbfc7e3075fd89879015ef5c78c5caa72353c45bf3ccbec2ae0`;
  file `sha256:9e40c0da866d44af000127a09faab66aebd7afa7a1c981eb5b83a7976e179abe`; 2,672 bytes.
- Preflight `reports/live-pilot/artifacts/d126-ac-clean-pricing-no-call-readiness-preflight.json`:
  ID `d126preflight_c1412f3daa396daed456b92ffc84360afcd68780fd281fc99efc0d067b6fed04`;
  body `sha256:c1412f3daa396daed456b92ffc84360afcd68780fd281fc99efc0d067b6fed04`;
  file `sha256:0238f5fa1c62f0160d340cc14b9613b20fc805c54ddb059d02e4464625227a1a`; 20,814 bytes.
- Gate `reports/live-pilot/artifacts/d126-ac-clean-source-pricing-no-call-preflight-gate.json`:
  ID `d126_d2ab27d34a7b56e51ba21d1d6274707b13e8345de6feb3bc9719d047ca834c4d`;
  body `sha256:d2ab27d34a7b56e51ba21d1d6274707b13e8345de6feb3bc9719d047ca834c4d`;
  file `sha256:e08e8f7aad8f425c7069290a98ac04a5c471bc8c948e1a08121c962b5ba18696`; 3,078 bytes.
- Status: `D126_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED`.

D-126 binds source commit `68b7c8b0779a33443a4a4e5ae423e3c64e0e1d22`. One unauthenticated official
GET observed `gpt-5.4-mini-2026-03-17` and default-tier text prices of $0.75 input, $0.075 cached input and
$4.50 output per 1M tokens, with no cache-write rate and Responses support. It was fresh within 72 hours and
preserves $13.6125 row/$54.45 schedule/proposed $55 cap math without approving cost.

The observed facts and math are valid, but pricing provenance is not fully replayable: raw official response
bytes were not retained, and validation cannot independently rebind the recorded body SHA/byte count/ETag to
retained official bytes. The blocked artifacts remain immutable; a re-authorized successor must close this
audit finding before hash/candidate gating.

Two stable Docker snapshots used 12 commands: six configuration reads, six read-only daemon/image calls and
zero workload/mutating calls. The local OpenAI 2.47.0 SDK probe made zero network calls. The five blockers are
`docker-cli-observed-identity-awaits-separate-exact-approval`,
`docker-local-daemon-and-exact-images-readiness-failed`, `openai-api-key-presence-missing`,
`production-openai-client-official-base-url-not-explicit` and
`production-openai-client-trust-env-not-disabled`.

Source/builder/test: `patchloop/evals/d126_clean_source_pricing_no_call_preflight.py`,
`scripts/build_d126_clean_source_pricing_no_call_preflight.py`,
`tests/test_d126_clean_source_pricing_no_call_preflight.py`. Provider/evaluator/agent/retrieval/injection
counts and cost are zero; hash/candidate flags are false. The next approval is limited to resolving the five
blockers and pricing provenance, then repeating the no-call preflight.

## Historical A/C source predecessors

| Gate | Artifact | Current interpretation |
| --- | --- | --- |
| D-125 | `reports/live-pilot/artifacts/d125-ac-runtime-finalization-offline-source-gate.json` | Local row consumption and mocked finalization recovery |
| D-124 | `reports/live-pilot/artifacts/d124-ac-cost-settlement-reconciliation-correction-source-gate.json` | Settlement reconciliation correction |
| D-123 | `reports/live-pilot/artifacts/d123-ac-cost-completion-offline-source-gate.json` | R2 cost/completion source superseded by D-124 |
| D-122 | `reports/live-pilot/artifacts/d122-ac-fixed-bundle-offline-qualification-source-gate.json` | R1 A-null/C-exact delivery source |

All are immutable historical evidence and created no current live authority. D-125 remains repository-local
and mocked-process only; validate it with
`scripts/build_d125_ac_runtime_finalization_qualification.py --validate-sealed-historical`.

## Historical/deferred D-121 preparation

D-121 artifacts under `reports/memory-development/` verified no-start configuration only. Runtime isolation
and successor execution remain false; the deferred candidate ID appears only in `docs/current-status.md`.

## No-memory baseline

`reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json` seals 12 terminal rows, 11
official-evaluator rows and 2 resolved task pairs. Its token/cost details are development evidence only.

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

D-116 through D-121 retain the applicability, source, partial-isolation and no-start evidence under
`reports/memory-development/`. No classifier/successor run was authorized; this lane is off the A/C path.

## Historical documentation snapshot

The exact pre-reorganization active documents are under `docs/archive/snapshots/d121/`. See
`docs/archive/snapshots/d121/snapshot-manifest.json` for original paths, byte sizes and SHA-256 values.

The snapshot is historical evidence, not current authority. Its source worktree was dirty relative to HEAD;
the manifest records that limitation explicitly.
