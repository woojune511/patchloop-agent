# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-131 local-admission implementation — fresh exact approval required

- Gate `reports/live-pilot/artifacts/d131-d130-local-admission-successor-offline-source-gate.json`:
  ID `d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`;
  body `sha256:849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`;
  file `sha256:8dfcd275b3e66113bc92df64e33bcf14f80c101cba2e40246d42b61f22dac048`,
  14,516 bytes.
- Source commit `9cd736c0221bba17375c3b7ddce02e5214fc21fe`; status
  `D131_D130_LOCAL_ADMISSION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_APPROVAL_REQUIRED`.

The new-only gate exact-binds the D-130 gate/evidence predecessor, D-131 source and loaded modules. It qualifies
append-only/new-only receipt and intent writers, orphan/collision/idempotence rejection, receipt-only and
intent-only commit topology, and a challenge that quotes the D-131 gate, receipt, intent and both commits.
Focused tests passed 15/15 and the selected D-127–D-131/docs bundle passed 107/107; overlapping selections are
not additive.

The gate builder invoked no future writer or challenge and created no receipt or intent. It made no official-
docs/network, credential, Docker or SDK observation. The prior D-130 Stage 1 approval was received but not
exercised and is non-reusable after the D-131 topology change. A fresh exact D-131-qualified local-admission
approval is required; the challenge produced afterward will not itself be activation.

## D-130 offline successor — historical predecessor

- Gate `reports/live-pilot/artifacts/d130-d129-external-sequence-block-successor-offline-source-gate.json`:
  ID `d130_443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db`;
  file `sha256:6d580dd979dc77659efed07291264c4ea2a16dca02d9070a32928e9fbefff468`, 17,416 bytes;
  evidence commit `d6079e55fd1c4745b05c2e345228b1a66d0a3df4`.

It binds the D-129 incident chain with zero D-130 external lookup. Its later Stage 1 approval was not exercised,
created no receipt/intent and is non-reusable after D-131 changed the topology.

## D-129 external sequence — terminal blocked

- Offline gate ID `d129_fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c`;
  evidence commit `70f9955dca8d873f91d622505f7afe7f3cfec59e`.
- Receipt ID `d129approval_0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42`;
  receipt-only commit `3fdfaa79a93df1e709eb9c01fdea9c4646cf0ad9`.
- Terminal ID `d129sequenceblock_b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8`;
  status `D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED`.

User approval preceded one public official-docs tool open, but receipt/attempt did not. Underlying HTTP and
returned-content counts are unknown; no canonical replay entity was retained or used as pricing evidence.
No attempt was backfilled. Docker, image mutation, SDK, canonical pricing, provider/evaluator/agent, memory,
hash/candidate, cost and A/C all stayed zero. The receipt is consumed; retry/resume/repair remain false.

## Historical blocked chain

- D-128 receipt/attempt/terminal are immutable. Its exact no-start phase made three read-only Docker calls,
  all rc 1, and stopped on `already-running-docker-desktop-linux-daemon-unavailable` with zero mutation.
- D-127 made six read-only Docker calls and stopped on
  `preexisting-container-auto-restart-state-unverified`; its receipt is consumed.
- D-126 remains `D126_AC_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED`.
- D-125 and earlier exact tuples remain in their canonical artifacts and Git history. D-121 is deferred.

## Next evidence boundary

Obtain fresh exact D-131-qualified D-130 local-admission approval quoting the D-131 gate tuple, 14,516 bytes and
the local evidence commit that tracks this gate. It may create only a receipt-only commit, durable
`ARMED_WAITING_EXACT_ACTIVATION` intent-only commit and activation challenge. No official-docs/network,
Docker, SDK or credential observation belongs to local admission. A separate exact activation must quote the
D-131 gate, receipt, intent and both commits before any external observation; live/hash/candidate/cost/A-C
authority stays closed.
