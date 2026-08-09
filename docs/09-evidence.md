# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-132 external-activation implementation — fresh exact activation required

- Gate `reports/live-pilot/artifacts/d132-d130-external-activation-successor-offline-source-gate.json`:
  ID/body `d132_ae224ab320e74bf871b74b0c9df23f88c5de170dfd26e7724aa234f29b2b0ba7`;
  file `sha256:059f672967aeed4b9f07db7249e887b92c3ad999ba96c61a8605e3d67f064bd0`,
  27,244 bytes.
- Source commit `ccf898d869342a9d5da42a1fef2c00e593fe91b4`; tree
  `0bab1f4c64f89070de9cedeeadc62b36668c3f72`; sole parent
  `4a40971b4e155683c49bbd6bcadc7468514ef84c`.
- Status `D132_D130_EXTERNAL_ACTIVATION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED`.

The new-only gate binds the exact G/R/I topology, source and loaded modules. It qualifies canonical activation
receipt creation, three ordered committed-attempt/action-started/terminal transitions, exact Docker no-start
scope, bounded replayable pricing, SDK/credential-presence no-call preflight and final READY/BLOCKED gates.
Focused tests passed 15/15; selected regression passed 170/170 with focused included, so counts are not
additive. The builder invoked no future writer/helper and created no future artifact or external observation.

The gate evidence tuple is the exact commit that adds this gate and modifies the canonical 10 active docs; use
the post-commit validator to obtain it. The pre-source request/challenge explicitly was not activation, remained
unexercised and became non-reusable after D-132.

## D-131 local admission — materialized predecessor

- Gate ID `d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`;
  evidence commit `283b9124af38252f47a06cbb1a484807b5030be2`.
- Receipt ID `d130approval_03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010`;
  file `sha256:01901a4f20a0231856e0326d2bc37283794b9cff998463707bc19b15d22731ba`,
  11,514 bytes; receipt-only commit `6987246b438fa6e6e711fa3b254aaf75ac4c2a66`.
- Intent ID `d130intent_4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153`;
  file `sha256:349d6680850374c1cee10e49f3319ef18bdd3640c48d075e999cbefac72c460c`,
  13,175 bytes; intent-only commit `4a40971b4e155683c49bbd6bcadc7468514ef84c`.

Receipt and intent are immutable local-admission evidence, not external activation.

## D-130 offline successor — historical predecessor

- Gate `reports/live-pilot/artifacts/d130-d129-external-sequence-block-successor-offline-source-gate.json`:
  ID `d130_443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db`;
  file `sha256:6d580dd979dc77659efed07291264c4ea2a16dca02d9070a32928e9fbefff468`, 17,416 bytes;
  evidence commit `d6079e55fd1c4745b05c2e345228b1a66d0a3df4`.

It binds the D-129 incident chain with zero D-130 external lookup. Its first Stage 1 approval was not exercised
and is non-reusable after D-131 changed the topology; the later D-131-qualified admission is indexed above.

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

After the D-132 gate+docs evidence commit, obtain fresh exact D-132-qualified activation quoting that gate and
evidence tuple plus the D-131 gate, D-130 receipt, D-130 intent and both artifact commit tuples. It may first
create the activation receipt-only commit; each external phase still requires its own committed attempt before
action. Started-without-terminal, orphan and blocked states are consumed. No current activation, activation
receipt, phase artifact or external action exists; live/hash/candidate/cost/A-C authority stays closed.
