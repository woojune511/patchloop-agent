# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-139 SDK no-call successor — source-qualified only

- Gate `reports/live-pilot/artifacts/d139-d138-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d139_09f2e9dfe0ee333a2683c058b772b92f025708c4bcc6b7f1eb89c007ed8df7f8`;
  file `sha256:a374b0fd1685ea7df0ab4e343dee59cfac6dba0d7a58bf01e3e7b887f1d13584`,
  15,565 bytes; blob `5a48b3e7447a450929aa52aa58a4e0fcbb352c15`.
- Source commit `f5625be6cf98b5f8824a0d6a5068f1cf03e94d98`, tree
  `073f821ce8f800a9bbd4cf56c228f00804a8c55a`, sole parent
  `9f31d330190aa83768077b17c3cde47eb86c639d`; its diff is exactly four added implementation paths.
- The gate-add/10-active-doc evidence commit is the source's direct child; the post-commit validator reports its
  exact tuple without embedding a self-referential commit hash here.

The gate replay-validates the complete D-138 chain and qualifies only the future one-use SDK successor contract.
Fully injected/mocked focused tests passed 168/168 and are reported separately from other checks. No D-139
receipt, attempt, marker, terminal or preservation artifact exists; preparation performed zero membership/value
or `.env` observation, credential mutation, child launch, SDK inspection, endpoint/network or Docker action.

## D-138 SDK no-call successor — BLOCKED and consumed

- Gate evidence commit `e430ceed797d0f31d95b501a98ac8070d91cbd71`; receipt-only commit
  `d6c3a7f2a51fdbc9214cc45fb624e201b9577145`; SDK-attempt-only commit
  `7d41a5c4affd2f4c75c81c9f507d920d9e94df66`.
- Receipt `reports/live-pilot/artifacts/d138-sdk-no-call-successor-activation-receipt.json`: ID/body
  `d138approval_94180d3242411147303bd89058732b8ddf65f3640cb9ba328df52d91ece4eae3`; file
  `sha256:e1673424a26f1125b01a428ecaac8b85eeb356bc45da159027f6247f54a79e89`, 9,270 bytes;
  blob `4a53be3c8b64450974193f60799b9931c7fc7018`.
- Attempt `reports/live-pilot/artifacts/d138-sdk-no-call-successor-attempt-intent.json`: ID/body
  `d138sdkattempt_c597453d860a8a40d8ee3515c75dc4c553d8cd222203a2717e981370bdf4fe82`; file
  `sha256:8270e6ed99bffed2af1a1969a974701fa514f6e9b4ddd1fa8561e926a559f274`, 5,304 bytes;
  blob `7003c19f18be8cef5f9da5e7f4100ca6d4c46f38`.
- ACTION_STARTED `reports/live-pilot/artifacts/d138-sdk-no-call-successor-action-started.json`: ID/body
  `d138sdkstarted_0c536738ccae9dd7de803e0b494c8f316d91a58beff375599ee647bbd270b63d`; file
  `sha256:27257efd4281b34e717126b8c130e793d247700756a75f7f0c70c62f424548d3`, 5,285 bytes;
  blob `d81d5119db5c7ba3ad1c6ee3b5d14e306939539f`.
- BLOCKED terminal `reports/live-pilot/artifacts/d138-sdk-no-call-successor-terminal.json`: ID/body
  `d138sdk_d6af84f10b258bcf9fa9cdfded60c7aaac715d2b4a1e94d61704cae540f2a59d`; file
  `sha256:6dd6ae0bcde0f4179c9382b8b4db1bb57b7f5a4aed14f1ae055f631c572038ad`, 8,568 bytes;
  blob `b345eb206aa2b1193418d9d2cd32682cf3fc128c`.
- Exact STARTED+terminal commit `9f31d330190aa83768077b17c3cde47eb86c639d`, tree
  `9606b1bbd8f88619add3c1949b8d5949e525d4ce`, sole parent
  `7d41a5c4affd2f4c75c81c9f507d920d9e94df66`.

The terminal found `OPENAI_API_KEY` presence false after three membership checks. Credential/environment value
and `.env` reads, child launch, SDK import/probe, transport dispatch and network calls were 0. D-138 is consumed
and cannot be retried, resumed, repaired or backfilled.

## Earlier consumed evidence — compact index

- D-137 Docker transition `06e57c54b4fe09f3145b8b59e51a0e391108d52a` is READY after eight read-only
  commands and zero mutation. SDK transition `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01` is BLOCKED after three
  membership checks found the key absent; value/`.env`/import/probe/dispatch/network counts were 0.
- D-136 success commit `2378569536c2367a3186f575a7517e3de7282336` preserves one official public GET,
  HTTP 200, zero redirects and 3,735 replay bytes with provider/evaluator/agent and cost counts 0.
- D-132 has no canonical response evidence. D-133 marker commit
  `a10033b6abd7155ebaa5c66c13627ad3ea738566`, invalid D-134 gate commit
  `9dc450a747537634e89fe2ade824685f8b5a52d6` and D-135 procedural terminal commit
  `98f4560e718145bc7465732c1a3d2f5a4ea8d786` preserve that consumed incident without reconstruction.
- D-129 remains terminal sequence-blocked; D-121 is deferred. Exact older artifacts and tuples remain in
  `reports/`, the archived ledger and Git history. None may be retried, resumed, repaired or backfilled.

## Next evidence boundary

Obtain a fresh exact D-139 activation quoting gate, source and evidence-commit tuples. It may create only a
receipt commit, then an SDK-attempt commit. The exact parent writes/fsyncs its marker before membership-only
checks; eligible SDK work runs only in the bounded `env={}` child with fixed placeholder, no ambient forwarding
and zero dispatch. Pre-bootstrap network absence is not claimed. Commit READY/BLOCKED terminal or, after failure,
marker only; never retry. Any terminal requires a separate offline successor and grants no provider/evaluator/
agent, memory/retrieval, hash/candidate, cost or A/C authority.
