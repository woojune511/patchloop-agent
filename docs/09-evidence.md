# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-141 SDK no-call successor — source-qualified only

- Gate `reports/live-pilot/artifacts/d141-d140-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d141_51e825a474cc957f6fa20dea9ec5332c9b0defd7569dfe6f063f57f195636aab`;
  file `sha256:cc8de60111294a79ed5f29b24263d7e7fe303a8f9c0dd5c78858e63bc3caa642`,
  16,056 bytes; blob `db596c40161e6cdf194e73ecff5f9afe1baa320f`.
- Source commit `0ffe586760659542d7ecf7c94698a2f1e109e6b0`, tree
  `41d14e4d9778e52834e4e6636f1bcd35ce148876`, sole parent
  `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2`; its diff is exactly four added implementation paths.
- The gate-add/10-active-doc evidence commit is the source's direct child; the post-commit validator reports its
  exact tuple without embedding a self-referential commit hash here.

The gate replay-validates the complete D-140 chain and qualifies only the future one-use SDK successor contract.
Fully injected/mocked focused tests passed 170/170 and are reported separately from other checks. No D-141
receipt, attempt, marker, terminal or preservation artifact exists; preparation performed zero membership/value
or `.env` observation, credential mutation/provisioning, child launch, SDK inspection, endpoint/network or Docker
action.

## D-140 SDK no-call successor — BLOCKED and consumed

- Gate `reports/live-pilot/artifacts/d140-d139-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d140_7362f061555800354d23ea673ee4d71ea4aab9d26d7572d9359e4d3f6c1cbad1`; file
  `sha256:83c18fe5417e23d5dc31e4dfd736dc644c6a7c0959ebde8c659bfa447a395eb9`, 16,056 bytes;
  blob `b5c591aa20b31eed50a7227b06f76987d33a6265`; evidence commit
  `1b753ff153ab7c8085a8a270e952711166ade685`.
- Source commit `fbb184ea8be0ea90eb044c03dbab538ed0c1f643`, tree
  `45283ebbeb3a7b1b3417ffe1b271020c5f062aba`, sole parent
  `ba3af19a5cada8e49c29f514ad56c299639dc452`; its diff is exactly four added paths.
- Receipt `reports/live-pilot/artifacts/d140-sdk-no-call-successor-activation-receipt.json`: ID/body
  `d140approval_4ecbcd60b4aa32623565bbd25bacd69977395c14d3d194e79c87b962f4d86e68`; file
  `sha256:f5ee35890262be209083818df67889c81b436741cfe246a619ac01bd884b8248`, 9,720 bytes;
  blob `23c27a76773612e0de5fb75505f8822af7c1304c`; commit
  `6082c0603e5b2d10d35e5695ab0e36dee0ddf5d4`.
- Attempt `reports/live-pilot/artifacts/d140-sdk-no-call-successor-attempt-intent.json`: ID/body
  `d140sdkattempt_f3df55715bc07028071744c825863e71020ffaf1087752eeac36db5d6a368b67`; file
  `sha256:f1b46d18a6086238f00850c7b41104c9acf8c5952bbd00920ec2aa44a9728ef2`, 5,698 bytes;
  blob `a8e7f8e940ae7187d65d118f18694e057a5b6104`; commit
  `4af4eceaf50053f53ec73160542cccf003674214`.
- ACTION_STARTED `reports/live-pilot/artifacts/d140-sdk-no-call-successor-action-started.json`: ID/body
  `d140sdkstarted_1423d2b74692bb56c14203e04cc00c74bbe5eb37c237b9b6f395a1faef324c54`; file
  `sha256:f08126fca4773cdd215146c0bd39643ee81f95a8b49510c35b558db06c4f4d2a`, 5,679 bytes;
  blob `02e4e16e325a564ae0ef5c5690ba9e7d37e5c4fb`.
- BLOCKED terminal `reports/live-pilot/artifacts/d140-sdk-no-call-successor-terminal.json`: ID/body
  `d140sdk_f5dc33dcd6a0614ab4604b5cba44ad2f80a01091141ae750970de37c8f1a95ac`; file
  `sha256:9bd03952aa93e338122736dd093b275951e6e487737625cd444a02b308d9d4ec`, 8,962 bytes;
  blob `163a19818d175e6790716d1f8de1c51e6c4ddc97`.
- Exact STARTED+terminal commit `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2`, tree
  `a69986de21d23356ba431755ff7eb8ba3e0aa710`, sole parent
  `4af4eceaf50053f53ec73160542cccf003674214`.

The terminal recorded the key and routing bits as false/false/false at the presence stage after three membership
checks. Credential/environment value and `.env` reads, child launch, SDK import/probe, transport/network and
provider/evaluator/agent calls were 0. D-140 is consumed and cannot be retried, resumed, repaired or backfilled.

## Earlier consumed evidence — compact index

- D-137 Docker transition `06e57c54b4fe09f3145b8b59e51a0e391108d52a` is READY after eight read-only
  commands and zero mutation. SDK transition `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01` is BLOCKED after three
  membership checks found the key absent; value/`.env`/import/probe/dispatch/network counts were 0.
- D-138 SDK transition `9f31d330190aa83768077b17c3cde47eb86c639d` is BLOCKED after three membership
  checks found the key absent; value/`.env`/child/import/probe/dispatch/network counts were 0.
- D-139 SDK transition `ba3af19a5cada8e49c29f514ad56c299639dc452` is BLOCKED after three membership
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

Obtain a fresh exact D-141 activation quoting gate, source and evidence-commit tuples. It may create only a
receipt commit, then an SDK-attempt commit. The exact parent writes/fsyncs its marker before membership-only
checks; eligible SDK work runs only in the bounded `env={}` child with fixed placeholder, no ambient forwarding
and zero dispatch. Pre-bootstrap network absence is not claimed, and credential provisioning is a separate action
authorized by neither preparation nor activation; no credential value belongs in approval/chat. Commit
READY/BLOCKED terminal or, after failure, marker only; never retry. Any terminal requires a D-142 offline
successor and grants no provider/evaluator/agent, memory/retrieval, hash/candidate, cost or A/C authority.
