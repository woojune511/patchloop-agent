# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## V14 manual-restart successor — consumed ERROR

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
- Approval `ncpapproval_370ba1d7f36ba7ce82805f8919747800f9be22ebf93f4ea670c2c85beffd0924`, file
  `sha256:487ae7e9bbf81478ac8297971cdde9dd117c285cb9a9934e2b6b12045632c0b0`, 1,401 bytes is the sole addition at
  `540a882`.

The exact four-artifact lifecycle is committed at `e63f418`: authorization
`ncprunauthorization_3503359b4c95ca913793efdb93e5ea74d9b35708eeab261deef6f25464daed1f`, attempt
`ncpattempt_53b489aa63592c668529f3530f2af9c61a435c79ff40bcab5ec0aa1332a2267a`, ACTION_STARTED
`ncpstarted_8770a0f9ca64a06055fc6b7f004a56139ea420a45fff312fafa37099197965d1`, and terminal
`ncpterminal_d390b170b452fa9497f22bd46832330e3a9b4097b645c3a9094d8d424e801e5f`. Docker passed eight read-only
commands with zero mutation. One child launch returned, but no framed envelope was received; outcome is
`ERROR(child_checker_error/framed_output_invalid)`. Network/provider/evaluator/agent and credential-value metadata
counts are 0; raw child output was not persisted. Whole-terminal accounting is incomplete, unknown post-marker activity
is true and retry/resume is false. No cost or A/C authority exists.

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

- D-136 success `2378569536c2367a3186f575a7517e3de7282336` preserves one HTTP-200 GET; D-137 transitions
  `06e57c54b4fe09f3145b8b59e51a0e391108d52a`/`8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01` preserve Docker READY then
  missing-key BLOCKED. D-138-D-141 remain consumed zero-value/no-network successors indexed in `reports/`.
- D-132 has no canonical response. D-133-D-135 commits preserve the incident without reconstruction; D-129 is
  sequence-blocked and D-121 deferred. Exact tuples remain in `reports/`/Git and cannot retry or backfill.

## Evaluator and preflight predecessors — compact index

- Evaluator-v2 commit `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6` is qualified locally with no live result.
- V3 terminal `ncpterminal_1735b16d4317df06fece7506221da4ff1cd1c4e57a8fee6818b56907643e6320` is Docker-not-ready;
  V4 state is non-proof and V5 terminal `ncpterminal_a7e12f36e75259ae00fe657ea0a96fde0a9826f58d77ffb1a7f091fff6902089`
  is consumed checker error. Exact source/qualification tuples remain in `reports/`.

Exact v1-v5 source, contract, receipt, approval and ledger tuples remain canonical in `reports/` and Git history.
D-142/R2 are unchanged; no predecessor may be retried, resumed, repaired or backfilled.
