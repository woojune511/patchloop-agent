# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## V14 manual-restart successor — source-qualified only

- Source/tree `d42acfc4d62350e692725f33d1be4b0a53f47b93`/`658bfae5bad5652a7f34e74ddc759ff16664badf`
  is the exact four-addition child of `dffb5298918a55cf863635b63cae4a3dc794d42a`; contract
  `ncpcontract_e7e0330cd94e691bdfe033476dd32a17711117092a620600e7ab47bbf1c8d74e` binds v13 terminal.
- Qualification `sha256:66b1f0cf406c5344b76a22cd883d48841cadbb4a058b3c7f78db8f4779b4f816`, file
  `sha256:b3aa811ebbf2f92767a67815646e45bfbcc158cf06f65abfdb61bc113f8d0abd`, 5,711 bytes is the sole addition at
  `0bc0fbe3a2447b102738d239c421585d44182165`. Tests pass 7/7.
- State `ncpstate_cda6ab57afae766cc7b2e26ce9b5ef40e984dd652177457b94da2550a22b2555`, content hash
  `sha256:cda6ab57afae766cc7b2e26ce9b5ef40e984dd652177457b94da2550a22b2555`, file
  `sha256:4541cfdd304d65e5047663ec3f73f59a1a68ca59f397fe4bc86f7e42621bd119`, 908 bytes is the sole addition at
  `d4467c0`.

State observation/mutation is 0, `.env` unreported and reusable false. Approval/attempt are absent; the next gate is
the exact v14 approval statement and grants no execution.

## V13 framed successor — consumed BLOCKED

Source `5bcffb29248d6de60eef34f6893c23f17ea70d3c`, contract
`ncpcontract_11d85bf3b90518afa163c265433eb1a2ed2c1ce2a12a51c3db828a2ea097c047` and qualification
`sha256:b536ebfab36cd17cf37d8dcb6b5ccd61fc46d048fc06aa573cd85035739b6298` led through state/approval to lifecycle commit
`d9fb103b7be464f3ff1aaf73ef31097eb9815239` and terminal
`ncpterminal_bf8a4b5e32ae56db30084c5d68d8ff77566a96538540c18520a929b3fd9170fe`.
It is `BLOCKED(docker_not_ready)`: eight Docker reads and zero mutation/`.env`/SDK/network/provider activity;
accounting complete, unknown activity false and retry closed. Exact intermediate IDs/hashes remain in `reports/`.

## V12 preflight lifecycle — consumed ERROR

Source/qualification are `0518f294ea73890aa0387a57121167c5a01f7947` and
`sha256:e96858f63e4e45e74ec9219e8653dbe276ebcd37384bcfa8762535ee771a6c41`. Exact four-artifact commit
`770b661e52646e0e309162121f14ff92f7f2568d` terminates as
`ncpterminal_9a4fc25df858faad01f4ec7872ca7d4cb31a4515f719fbabb2a20fc4cc55b13b` /
`ERROR(child_checker_error/child_output_invalid)`: Docker passed 8 reads, but no typed child result exists. Accounting
is complete; forbidden activity is 0 and retry is false. Exact ledger IDs remain in `reports/`.

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
- D-138/D-139/D-140 transitions `9f31d330190aa83768077b17c3cde47eb86c639d`,
  `ba3af19a5cada8e49c29f514ad56c299639dc452` and `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2`
  are missing-key BLOCKED with three checks and zero value/`.env`/child/SDK/network activity.
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
