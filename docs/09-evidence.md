# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## V7 sanitized SDK parent integration — ERROR and consumed

- V6 predecessor source `1d99a7c0acf20ec961240f33f585553fd881dc02`, contract
  `ncpcontract_3c050730b5c573d395b9d8559d29532153ffa82ceacc51e91434de9fb4351918` and qualification
  `sha256:df0d68f6059d267260ec34fcd3d7714c406856ef1b22902412de3e74180e3bb2` remain unchanged.
- V7 source commit/tree `6f6ba8627238b9d926e8b2bfe8a877d64ff1d755`/
  `990bef7e12c1d485a33fd79b1ca8d9b6960426e8` directly follows `f48db03a12b3274c047a01e2cc626395812f1f53`
  and adds exactly four contract/runtime/builder/test paths.
- Contract `ncpcontract_5a078023a4730abb42e5f01cd9e525ffafbcdab690cccdabcddb61e4b7c29cbf` binds v6,
  the D-137 observer, isolated `-I -E -s -B` child, fixed environment and one-use lifecycle; all source live authority is false.
- Qualification artifact `evaluator-v2-sanitized-sdk-parent-integration-v7-source-qualification.json` has body
  `sha256:defaa75877c4d842ae41d3d2845f1f6a82df874a5ca6953c91b4b660cf86ca2c`, file
  `sha256:16419a67050098b590682cda657e22c6378bbeeb55148e802f1e5a0a820e49e2`, 5,124 bytes and commit
  `50a3149028b6531b0ef837af90057077d18a2c4a`.

Materialization and qualification made zero Docker/`.env`/SDK/network observation or mutation. State
`ncpstate_c664d973bcf4a5964bcd035c4d4f581c0ac7bc31c79ebb9d46850e6c2f429970` has file
`sha256:14e8563d2146accf73c7f0150a31707ba4f8a53d913113b4eacdba5c415a5a47`, 1,134 bytes and commit
`3040044b32cf043edc054fb13869a85a4b4b83fd`; it records only a non-reusable user report. Receipt
`ncpapprovalreceipt_5af0a296f10895a6f57f3ee394a516fa41110aa155279e2ee0d5ef0278f990c1` and approval
`ncpapproval_02415aa08a4359a2f810d31f40c9a6e9a041af655df4c931cb61ac4a09d292ff` are commit
`28f98c49d794377b4afbcf69acd1c39fb22d7c85`.

Attempt `ncpattempt_de2f13e06b77b975c9ef16e0ca75787fcb93a8272de4ee80262f79bf94c83e89`, marker
`ncpstarted_7a04080397aecad7d1f98e683f0c4c25198545d9347d181b3c9c94f2ba871d39` and terminal
`ncpterminal_a6ad48867773cc2614861cadfbece94c646fa2b7aef453facc7fd37fe4dd537c` are commit
`3cde67ba12390af328979d58b52551f1761f7cb3`. Docker was READY after 8 reads; exact key membership was true;
one child launch ended `diagnostic_runtime_import_error`. Dispatch/network/provider counts were 0, accounting was
complete, unknown activity false and retry/resume false. No credential value/hash/length or exception text was recorded.

## D-142 SDK no-call successor — source-qualified only

- Gate `reports/live-pilot/artifacts/d142-d141-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914`;
  file `sha256:83fa6e83a3b5827a07e3383f9dea6318b748813742b501a4aaf7b41c726a1e80`,
  16,298 bytes; blob `a2fcfcf97e8cdc1c7b8357b334211efab4b2dbf2`.
- Source commit `1370cf43c08cefb550b158a5d4172a60ac172470`, tree
  `7f7e7e25c79899eee6180ae45767492435003096`, sole parent
  `6405be40eb52d71fc9376065b553a04164543a4b`; its diff is exactly four added implementation paths.
- The gate-add/10-active-doc evidence commit is the source's direct child; the post-commit validator reports its
  exact tuple without embedding a self-referential commit hash here.

The gate replay-validates the complete D-141 chain and qualifies only the future one-use SDK successor contract.
Fully injected/mocked focused tests passed 170/170 and are reported separately from other checks. No D-142
receipt, attempt, marker, terminal or preservation artifact exists; preparation performed zero membership/value
or `.env` observation, credential mutation/provisioning, child launch, SDK inspection, endpoint/network or Docker
action.

Planning disposition is owned by `docs/current-status.md`; it does not alter this evidence state.

## D-141 SDK no-call successor — BLOCKED and consumed

- Gate/source/evidence commits are `d141_51e825a474cc957f6fa20dea9ec5332c9b0defd7569dfe6f063f57f195636aab`,
  `0ffe586760659542d7ecf7c94698a2f1e109e6b0` and `9b9ce197daa34db355274956fd5043ab3a0b3539`.
- Receipt/attempt/ACTION_STARTED/terminal IDs are `d141approval_e4f5bfc2324eb75194a84f45d42269910bc487101d7cd7b629289e60b7416c71`,
  `d141sdkattempt_5df0f4f15f3e98deebbb77d59ace047102f2da75ef1378875311d1a6be66e588`,
  `d141sdkstarted_549d1631211c3dfeb440989e9377cf6d697125eafd0309d68fe092f66ba61b57` and
  `d141sdk_c96ceb8eb274560b89e3688402a0c3576d6f09536c32d611600ac1386d4613ef`.
- Terminal commit `6405be40eb52d71fc9376065b553a04164543a4b` recorded false/false/false after three
  presence checks. Credential/environment value, `.env`, child, SDK, network and provider/evaluator/agent counts were 0.

D-141 is consumed and cannot be retried, resumed, repaired or backfilled. Exact file tuples remain in `reports/`.

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
