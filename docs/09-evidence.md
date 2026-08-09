# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-129 external sequence — terminal blocked

- Offline gate `reports/live-pilot/artifacts/d129-d128-terminal-successor-offline-source-gate.json`:
  ID `d129_fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c`;
  body `sha256:fa5412dd269ba6d4f502220fe1655d6f84b746eff6fa95633691464d6e29243c`;
  file `sha256:fd57c187d1f260952b581e60f7d0ff98243f3b4ef172c9a6d6669b3e84968512`, 18,678 bytes.
- Incident source commit `d42334312c4752cbe9f4aa039c22b8ed51b8b66b`, sole child of D-129 evidence commit
  `70f9955dca8d873f91d622505f7afe7f3cfec59e`.
- Receipt `reports/live-pilot/artifacts/d129-terminal-successor-external-no-call-approval-receipt.json`:
  ID `d129approval_0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42`;
  body `sha256:0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42`;
  file `sha256:820c67d9c5f75cda89aa52f3252295a08ba0ee385e61e6a8ac83cd0637a23885`, 12,014 bytes.
- Receipt-only commit `3fdfaa79a93df1e709eb9c01fdea9c4646cf0ad9`, sole child of incident source.
- Terminal `reports/live-pilot/artifacts/d129-external-no-call-sequence-observed-blocked.json`:
  ID `d129sequenceblock_b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8`;
  body `sha256:b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8`;
  file `sha256:fbb7fac37555ea4d8a2de0d5947fdffe74e3b716b359e2a23834ed6689bd732d`,
  13,118 bytes; status `D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED`.

User approval preceded one public official-docs tool open, but receipt/attempt did not. Underlying HTTP and
returned-content counts are unknown; no canonical replay entity was retained or used as pricing evidence.
No attempt was backfilled. Docker, image mutation, SDK, canonical pricing, provider/evaluator/agent, memory,
hash/candidate, cost and A/C all stayed zero. The receipt is consumed; retry/resume/repair remain false.

Focused sequence tests passed 12/12. The selected D-127/D-128/D-129/docs regression bundle passed 79/79;
focused and selected counts are not additive where node sets overlap.

## Historical blocked chain

- D-128 receipt/attempt/terminal are immutable. Its exact no-start phase made three read-only Docker calls,
  all rc 1, and stopped on `already-running-docker-desktop-linux-daemon-unavailable` with zero mutation.
- D-127 made six read-only Docker calls and stopped on
  `preexisting-container-auto-restart-state-unverified`; its receipt is consumed.
- D-126 remains `D126_AC_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED`.
- D-125 and earlier exact tuples remain in their canonical artifacts and Git history. D-121 is deferred.

## Next evidence boundary

D-130 must exact-bind the D-129 gate, receipt, terminal and commit topology without external calls. Its first
admission may create only a receipt-only commit and durable armed-intent-only commit. A separate exact activation
must quote those tuples before any external observation; live/hash/candidate/cost/A-C authority stays closed.
