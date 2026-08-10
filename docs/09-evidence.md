# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-140 SDK no-call successor — source-qualified only

- Gate `reports/live-pilot/artifacts/d140-d139-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d140_7362f061555800354d23ea673ee4d71ea4aab9d26d7572d9359e4d3f6c1cbad1`;
  file `sha256:83c18fe5417e23d5dc31e4dfd736dc644c6a7c0959ebde8c659bfa447a395eb9`,
  16,056 bytes; blob `b5c591aa20b31eed50a7227b06f76987d33a6265`.
- Source commit `fbb184ea8be0ea90eb044c03dbab538ed0c1f643`, tree
  `45283ebbeb3a7b1b3417ffe1b271020c5f062aba`, sole parent
  `ba3af19a5cada8e49c29f514ad56c299639dc452`; its diff is exactly four added implementation paths.
- The gate-add/10-active-doc evidence commit is the source's direct child; the post-commit validator reports its
  exact tuple without embedding a self-referential commit hash here.

The gate replay-validates the complete D-139 chain and qualifies only the future one-use SDK successor contract.
Fully injected/mocked focused tests passed 170/170 and are reported separately from other checks. No D-140
receipt, attempt, marker, terminal or preservation artifact exists; preparation performed zero membership/value
or `.env` observation, credential mutation/provisioning, child launch, SDK inspection, endpoint/network or Docker
action.

## D-139 SDK no-call successor — BLOCKED and consumed

- Gate `reports/live-pilot/artifacts/d139-d138-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d139_09f2e9dfe0ee333a2683c058b772b92f025708c4bcc6b7f1eb89c007ed8df7f8`; file
  `sha256:a374b0fd1685ea7df0ab4e343dee59cfac6dba0d7a58bf01e3e7b887f1d13584`, 15,565 bytes;
  blob `5a48b3e7447a450929aa52aa58a4e0fcbb352c15`; evidence commit
  `ab7b56beb63c99321f27b8712cec281ba0106c19`.
- Source commit `f5625be6cf98b5f8824a0d6a5068f1cf03e94d98`, tree
  `073f821ce8f800a9bbd4cf56c228f00804a8c55a`, sole parent
  `9f31d330190aa83768077b17c3cde47eb86c639d`; its diff is exactly four added paths.
- Receipt `reports/live-pilot/artifacts/d139-sdk-no-call-successor-activation-receipt.json`: ID/body
  `d139approval_72e254cf71d8fcad24e6069ee2fb68cd220a95b70229bbee4b4643392abc1c71`; file
  `sha256:2ff140262751144c78529eabd1ca34596c59634d526bba0bd068044a677965ca`, 9,270 bytes;
  blob `85c60ed8a271dbce2403549f07c21feb83e4342a`; commit
  `fdf2faa739723d9bf330f2d1b35eae1ad530e438`.
- Attempt `reports/live-pilot/artifacts/d139-sdk-no-call-successor-attempt-intent.json`: ID/body
  `d139sdkattempt_84ee2917e702d7ed58df00fdc84ae3f5e042b271e7551ab72012b886beb27021`; file
  `sha256:f8a96cd6f5b7a5242037f205b728f427ac87a38ee10ec7b46c98cc301e212b44`, 5,304 bytes;
  blob `23f60f466a90b33dad2d57719b4227f097ae71f5`; commit
  `d17324062acd030b198a2dc0f54e8937016de924`.
- ACTION_STARTED `reports/live-pilot/artifacts/d139-sdk-no-call-successor-action-started.json`: ID/body
  `d139sdkstarted_7ec011e8d177b404464534dfc238bc94a02dbd8c4e29f8a8fb2a518559d05fd2`; file
  `sha256:de1fefd49eef8fc653d4250e00c55d8bf953ca0b43437fce82e5b295fdae4d74`, 5,285 bytes;
  blob `1e336bb9c038ad026b7e0130f3074d6f4c233733`.
- BLOCKED terminal `reports/live-pilot/artifacts/d139-sdk-no-call-successor-terminal.json`: ID/body
  `d139sdk_4154a198d2b46e884ffe535f07dfb8a21df63c24e511873e503d1628004596e5`; file
  `sha256:f9f3f18d1df737f1a814baf31d7e5f09b2b0ea2e3bc408e57361d4fead419438`, 8,568 bytes;
  blob `87bcc88f6e50aedff4590501e0e718adeba58f36`.
- Exact STARTED+terminal commit `ba3af19a5cada8e49c29f514ad56c299639dc452`, tree
  `454e6b704ae2f758364d876642262081f2eb141f`, sole parent
  `d17324062acd030b198a2dc0f54e8937016de924`.

The terminal found `OPENAI_API_KEY` presence false after three membership checks. Credential/environment value
and `.env` reads, child launch, SDK import/probe, transport dispatch and network calls were 0. D-139 is consumed
and cannot be retried, resumed, repaired or backfilled.

## Earlier consumed evidence — compact index

- D-137 Docker transition `06e57c54b4fe09f3145b8b59e51a0e391108d52a` is READY after eight read-only
  commands and zero mutation. SDK transition `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01` is BLOCKED after three
  membership checks found the key absent; value/`.env`/import/probe/dispatch/network counts were 0.
- D-138 SDK transition `9f31d330190aa83768077b17c3cde47eb86c639d` is BLOCKED after three membership
  checks found the key absent; value/`.env`/child/import/probe/dispatch/network counts were 0.
- D-136 success commit `2378569536c2367a3186f575a7517e3de7282336` preserves one official public GET,
  HTTP 200, zero redirects and 3,735 replay bytes with provider/evaluator/agent and cost counts 0.
- D-132 has no canonical response evidence. D-133 marker commit
  `a10033b6abd7155ebaa5c66c13627ad3ea738566`, invalid D-134 gate commit
  `9dc450a747537634e89fe2ade824685f8b5a52d6` and D-135 procedural terminal commit
  `98f4560e718145bc7465732c1a3d2f5a4ea8d786` preserve that consumed incident without reconstruction.
- D-129 remains terminal sequence-blocked; D-121 is deferred. Exact older artifacts and tuples remain in
  `reports/`, the archived ledger and Git history. None may be retried, resumed, repaired or backfilled.

## Next evidence boundary

Obtain a fresh exact D-140 activation quoting gate, source and evidence-commit tuples. It may create only a
receipt commit, then an SDK-attempt commit. The exact parent writes/fsyncs its marker before membership-only
checks; eligible SDK work runs only in the bounded `env={}` child with fixed placeholder, no ambient forwarding
and zero dispatch. Pre-bootstrap network absence is not claimed, and credential provisioning is a separate,
unauthorized action. Commit READY/BLOCKED terminal or, after failure, marker only; never retry. Any terminal
requires a separate offline successor and grants no provider/evaluator/agent, memory/retrieval, hash/candidate,
cost or A/C authority.
