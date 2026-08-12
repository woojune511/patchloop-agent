# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## V10 state binder — source-qualified only

- Source/tree `3190923f97883e7df4bb53b9b8231c3598239fb1`/`d7f0723630b1e9a699775974aa222fdec4d88df5`
  is the exact four-addition child of `0c0f8065d99996b632c8a2f7e288d473fe7644c5`.
- Contract `ncpcontract_5365b5b57ad61a691232efb73c930656338e5137ba10fa80d4788c6b2c782539` binds
  exact v9 source/qualification and requires a fixed post-qualification statement citing v10 identities.
- Qualification body `sha256:e9e8d7425b300ad109ba38ceeda08e8e897cf596c03d381771351792eb761a6e`, file
  `sha256:269be5085e26b07d551768dc51c9be75c364d29427f601ac928f2c297ed55a25`, 5,381 bytes is commit
  `12e0927afdb651a07cc8e25abc0362d373ac48d0`.

Qualification observed no environment, Docker, `.env`, SDK or network. Exact statement binding later created
attestation `ncpattestation_0467a7aa45ba81596227189aca97ecdd5997a0f3719fed9c3bbcdf781fa526e3` and state
`ncpstate_cf5f91ae06c6c49dc988ec217a535301b5162208ed227186cb76b15be572abe5` at
`5ab4226bfc5017563b673375f9057fde39b1c38c`. File hashes are `sha256:2e95c2c73d7594259a4150325ea6e6ac963b1c1c5d7e4b972f972451c1d323fc` and
`sha256:adca442a20b7dbafa834b54888568c1e9ddfbe16f9c783458ad2917caa60b4e2`.
The state is self-attested non-proof, nonreusable, observation/mutation 0 and execution false; no approval/attempt exists.

## V7 consumed error — compact index

Source/contract/qualification are `6f6ba8627238b9d926e8b2bfe8a877d64ff1d755`,
`ncpcontract_5a078023a4730abb42e5f01cd9e525ffafbcdab690cccdabcddb61e4b7c29cbf` and
`sha256:defaa75877c4d842ae41d3d2845f1f6a82df874a5ca6953c91b4b660cf86ca2c`. Terminal
`ncpterminal_a6ad48867773cc2614861cadfbece94c646fa2b7aef453facc7fd37fe4dd537c` at
`3cde67ba12390af328979d58b52551f1761f7cb3` records Docker READY, exact-key membership and one child import error;
dispatch/network/provider were 0, accounting complete and retry/resume false. Exact chain tuples remain in `reports/`.

## D-142 SDK no-call successor — source-qualified only

- Gate `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914` binds source/tree
  `1370cf43c08cefb550b158a5d4172a60ac172470`/`7f7e7e25c79899eee6180ae45767492435003096`, the exact
  four-path child of D-141 terminal commit `6405be40eb52d71fc9376065b553a04164543a4b`.
- Injected/mocked tests passed 170/170. Receipt/attempt/marker/terminal and external observation are absent.
  Planning is deferred; exact file/blob tuples remain in the gate artifact and Git history.

## D-141 SDK no-call successor — BLOCKED and consumed

- Terminal `d141sdk_c96ceb8eb274560b89e3688402a0c3576d6f09536c32d611600ac1386d4613ef` at commit
  `6405be40eb52d71fc9376065b553a04164543a4b` recorded false/false/false after three checks; value, `.env`,
  child, SDK, network and provider counts were 0. It is consumed; exact chain tuples remain in `reports/`.

## Earlier consumed evidence — compact index

- D-137 Docker transition `06e57c54b4fe09f3145b8b59e51a0e391108d52a` is READY after eight read-only
  commands and zero mutation. SDK transition `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01` is BLOCKED after three
  membership checks found the key absent; value/`.env`/import/probe/dispatch/network counts were 0.
- D-138 SDK transition `9f31d330190aa83768077b17c3cde47eb86c639d` is BLOCKED after three membership
  checks found the key absent; value/`.env`/child/import/probe/dispatch/network counts were 0.
- D-139 SDK transition `ba3af19a5cada8e49c29f514ad56c299639dc452` is BLOCKED after three membership
  checks found the key absent; value/`.env`/child/import/probe/dispatch/network counts were 0.
- D-140 SDK transition `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2` is BLOCKED after false/false/false
  presence bits and three checks; value/`.env`/child/import/probe/dispatch/network/provider counts were 0.
- D-136 success commit `2378569536c2367a3186f575a7517e3de7282336` preserves one official public GET,
  HTTP 200, zero redirects and 3,735 replay bytes with provider/evaluator/agent and cost counts 0.
- D-132 has no canonical response evidence. D-133 marker commit
  `a10033b6abd7155ebaa5c66c13627ad3ea738566`, invalid D-134 gate commit
  `9dc450a747537634e89fe2ade824685f8b5a52d6` and D-135 procedural terminal commit
  `98f4560e718145bc7465732c1a3d2f5a4ea8d786` preserve that consumed incident without reconstruction.
- D-129 remains terminal sequence-blocked; D-121 is deferred. Exact older artifacts and tuples remain in
  `reports/`, the archived ledger and Git history. None may be retried, resumed, repaired or backfilled.

## Evaluator and preflight predecessors — compact index

- Evaluator-v2 commit `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6` binds qualification
  `sha256:18e7278f7e98988536de9b866fcb3e281c76a23404d252be1186ce9df97e7320`, evaluator source
  `sha256:a272b43ced99550dbb79b9c478d3f7161cb260b0451709b7ab141ba8d6f64943` and suite
  `sha256:bafa8212ce34efb36f2b96bb0508d99917544317a9671d93ad2b06a796672e6f`; it has no live result.
- V3 terminal `ncpterminal_1735b16d4317df06fece7506221da4ff1cd1c4e57a8fee6818b56907643e6320`
  consumed `BLOCKED(docker_not_ready)` after 8 Docker reads and zero `.env`/SDK/network/provider calls.
- V4 state `ncpstate_9f8c92448974e89bd7c244feff4df63c94a4a82e6f6e526c262f3cb43b9effef` is
  self-attested non-proof. V5 terminal `ncpterminal_a7e12f36e75259ae00fe657ea0a96fde0a9826f58d77ffb1a7f091fff6902089`
  consumed ERROR after Docker/key checks returned only `sdk_checker_error` with incomplete accounting.

Exact v1-v5 source, contract, receipt, approval and ledger tuples remain canonical in `reports/` and Git history.
D-142/R2 are unchanged; no predecessor may be retried, resumed, repaired or backfilled.
