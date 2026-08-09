# Evidence index

This document links to canonical machine artifacts. It does not duplicate the full historical narrative,
which is preserved at `docs/archive/snapshots/d121/09-evidence.full.md`.

## D-128 offline terminal-successor source

- Gate `reports/live-pilot/artifacts/d128-d127-terminal-successor-offline-source-gate.json`:
  ID `d128_9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de`;
  body `sha256:9edb9d1396b2f572c3b1ade623c7c5f6fb3fdf083d17a71680e7f1041bfba7de`;
  file `sha256:2528aa018908958bdd35b4b6202c75be2b4ca72521d64bfed800284a015a739c`; 12,557 bytes.
- Status `D128_D127_TERMINAL_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED`; source commit
  `3b192e177b2da1302a030eb457ca96f7dae86611`.

Focused tests passed 12/12; the D-122/D-127/D-128 selected union passed 76/76 and includes those 12. The gate
created no approval receipt, external attempt, Docker/network/pricing/SDK/provider call, hash/candidate, cost or
A/C action. The gate does not embed its evidence commit; the commit containing gate/docs supplies that identity.
After user manual Docker start and no-auto-start attestation, exact approval must cite both; the agent must not
start Desktop or the daemon.

## D-127 terminal blocked Docker remediation

- Receipt `reports/live-pilot/artifacts/d127-d126-successor-blocker-remediation-no-call-preflight-approval-receipt.json`:
  ID `d127approval_3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21`;
  body `sha256:3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21`;
  file `sha256:ddea365e3a51c8283bde58bd349222288a45e8ea8bdb3d211ead0bb001df81f4`; 3,914 bytes.
- Status: `D127_D126_SUCCESSOR_BLOCKER_REMEDIATION_NO_CALL_APPROVAL_RECORDED`.
- Attempt `reports/live-pilot/artifacts/d127-docker-remediation-attempt-intent.json`:
  ID `d127dockerremediationattempt_2ebabbf2b9d1ace5c3dc552e8f7c2e2ad8c4f3699c5978e718e973b8112369aa`;
  body `sha256:2ebabbf2b9d1ace5c3dc552e8f7c2e2ad8c4f3699c5978e718e973b8112369aa`;
  file `sha256:2a1d5b01f5cf9a18e1e51db473c35e2003b9c875f2f8f7449d25d55df33328c2`; 4,246 bytes.
- Terminal `reports/live-pilot/artifacts/d127-exact-docker-remediation-observation.json`:
  ID `d127remediation_139037ff65b70cc08e24a69d2d6fd47fe04b7cc27bec8e97ebe9a7009179857f`;
  body `sha256:139037ff65b70cc08e24a69d2d6fd47fe04b7cc27bec8e97ebe9a7009179857f`;
  file `sha256:dc6639db851fb414325473eebf7e9b8ddd9fe15f54a3b0946b0bd82f99a530d3`; 10,139 bytes.
- Terminal status: `D127_EXACT_DOCKER_REMEDIATION_OBSERVED_BLOCKED`; source
  `cec335f345a56d544614fe0c9ec3e75cba78bf17`.

Static passed after an exact-key ephemeral loader imported only `OPENAI_API_KEY` from the local `.env`; the
value was not exposed or recorded. The terminal records six bounded read-only Docker CLI calls and blocker
`preexisting-container-auto-restart-state-unverified`. Desktop start, pulls/image-store mutation,
container/workload, pricing GET, preflight, gate, provider/evaluator/agent, memory, hash/candidate and cost are
zero or absent. The terminal is exact-idempotent for this receipt, so a changed environment requires a
separately approved successor. D-126 remains the latest sealed checkpoint.

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

D-126 binds commit `68b7c8b0779a33443a4a4e5ae423e3c64e0e1d22`, fresh dated-model prices and
unapproved $13.6125/$54.45/$55 planning math. Raw official bytes were not retained, so provenance is not fully
replayable. Twelve Docker reads included six daemon/image calls and zero workloads; the locked SDK probe made
zero network calls. The five blockers are
`docker-cli-observed-identity-awaits-separate-exact-approval`,
`docker-local-daemon-and-exact-images-readiness-failed`, `openai-api-key-presence-missing`,
`production-openai-client-official-base-url-not-explicit` and
`production-openai-client-trust-env-not-disabled`.

D-126 provider/evaluator/agent/retrieval/injection and cost are zero; hash/candidate flags are false. D-127
records the limited successor receipt and blocked remediation without modifying these sealed artifacts.

## Historical A/C source predecessors

D-122 through D-125 gates under `reports/live-pilot/artifacts/` preserve fixed delivery, cost/settlement and
local/mock finalization source history. They created no live authority; use their sealed-historical validators.

## Historical/deferred D-121 preparation

D-121 artifacts under `reports/memory-development/` verified no-start configuration only. Runtime isolation
and successor execution remain false; the deferred candidate ID appears only in `docs/current-status.md`.

## No-memory baseline

`reports/live-pilot/dev-no-memory-condition-neutral-3000k-20260805-r1.json` seals 12 terminal rows, 11
official-evaluator rows and 2 resolved task pairs. Its token/cost details are development evidence only.

## Structured-memory chain

D-103 through D-115 artifacts under `reports/memory-development/` preserve three-entry admission/render/freeze,
the +702 exact-pair count and failed selective-scoring diagnostics. None records runtime injection or a
memory-conditioned outcome.

## Deferred applicability/isolation chain

D-116 through D-121 retain the applicability, source, partial-isolation and no-start evidence under
`reports/memory-development/`. No classifier/successor run was authorized; this lane is off the A/C path.

## Historical documentation snapshot

The exact pre-reorganization active documents are under `docs/archive/snapshots/d121/`. See
`docs/archive/snapshots/d121/snapshot-manifest.json` for original paths, byte sizes and SHA-256 values.

The snapshot is historical evidence, not current authority. Its source worktree was dirty relative to HEAD;
the manifest records that limitation explicitly.
