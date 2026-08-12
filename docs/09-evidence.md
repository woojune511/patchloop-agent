# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## V7 sanitized SDK parent integration — source-qualified only

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

Materialization and qualification made zero Docker/`.env`/SDK/network observation or mutation. No v7 state,
approval, attempt, marker or terminal exists; the next gate is fresh state plus a separate exact approval.

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

## Next evidence boundary

Evaluator-v2 commit `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6` preserves successor source qualification
`sha256:18e7278f7e98988536de9b866fcb3e281c76a23404d252be1186ce9df97e7320`, evaluator source
`sha256:a272b43ced99550dbb79b9c478d3f7161cb260b0451709b7ab141ba8d6f64943` and suite
`sha256:bafa8212ce34efb36f2b96bb0508d99917544317a9671d93ad2b06a796672e6f`.

V1 child `4a78745552ef8eab62ddfcdaeb3154de50fe79bf` is receipt-bound. Structural v2 source/tree
`d8652b2648f97788ae65a82e949d2b168e7ff4a9`/`373244b7b2a9e44d7e6dfe31deb59aef9030dd97` binds contract
`ncpcontract_68151531120dd61e5c6363f172a92144c75f7553de4d5fc902e5190b30770fbd`, qualification
`sha256:e903639750a961b60f879435a10be5e3f03f1809614e7686a8f8d854d2def309` and state
`ncpstate_80e1ab7955bab8d1b9bf83ae05a0aada373fa69dc11e9770bdde680256355582`.

Executable v3 source/tree `ce0628880107db2319816272cfa49adc7ea99667`/`fe08f400b9573f11470a021407c9298020a17ca2`
binds contract `ncpcontract_6e7fa7dac02b594d9f16c84b4d3036632a6f6a2214cd7cf8cbab7b559bd55f9d`, qualification
`sha256:385ac8521f86a4572bb9614af4c5730bb9856e63be3445ddb27521b492bd8079`, state
`ncpstate_105d0becd0a33fe453e6be83044b239263eb855c165da6f275d9e4591e54f317` and approval
`ncpapproval_37f2d23e133e0ea42a43c08134de51b2a61e2d5de2e4e23a1f9a324e92f6828f`. Attempt
`ncpattempt_26b65477c3ef1d4ed08adbfa06aba2d0adb9b06889169d09c19cab76396be7d9`, ACTION_STARTED
`ncpstarted_35873058f1becb38bb50feb7449d6065f2e705f99a00c5dc63a13b03bce489cb` and terminal
`ncpterminal_1735b16d4317df06fece7506221da4ff1cd1c4e57a8fee6818b56907643e6320` record consumed
`BLOCKED(docker_not_ready)`: Docker reads 8; start/pull/load/mutation, `.env`/SDK/network/provider/evaluator/agent/cost
are 0; accounting is complete and retry/resume false.

V4 state `ncpstate_9f8c92448974e89bd7c244feff4df63c94a4a82e6f6e526c262f3cb43b9effef` is self-attested non-proof. V5
source `3b80cf26983a1723f1f7b87561003ffc243d64a3`, contract `ncpcontract_858f2467550660dfbeeed28676d791a6fd72825a767afd631ce2d7f3574d9f84`
and qualification `sha256:fea077651d24ce9723f21e08758043516d41bba12090f201ffb0dfd5876a09d7` precede approval commit
`980e94d5a51d92152cf839651a12bbffce191f2c`: receipt `ncpapprovalreceipt_4efe85c7678acc56b53e8b37d2ec36473681fec775ae3f5dc63d85befdea6a11`,
approval `ncpapproval_3c94656fd82fd51bb2116973bbafef826b7f5431ed9716a1c645bd5c8a7171ad`.

Consumed commit/tree `3374e3452af2a615b5c3eb00e493354baabe9b09`/`c42e7d5b1223be3b21f9932b12aa855c377c24bf` binds attempt
`ncpattempt_005f1501ed93dc4cde97fa53a1718b6a90bdad18080eb88157bf7c713c5d6f26`, ACTION_STARTED
`ncpstarted_3ee33fa8017b77c134e908156e3b46da78a16f21149cc7f9c7571e765bcf44f3` and ERROR terminal
`ncpterminal_a7e12f36e75259ae00fe657ea0a96fde0a9826f58d77ffb1a7f091fff6902089`. Docker was READY after eight stable
read-only calls; exact images were present and container inventory empty. The isolated child read `.env` once,
found the exact key declared/nonempty and returned `sdk_checker_error` with no credential value/hash/length or
network/provider call. Terminal accounting is incomplete, post-marker activity is unknown, and retry/resume is false.
D-142/R2 and v1-v4 evidence remain unchanged.
