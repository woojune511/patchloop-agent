# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## V19 dual-pipe successor — source-qualified only

Source/tree `91300324d0fd9ac83356204f03325cded4137f12`/`a31a395a29bf749631c877bf17bb85a5f817c79a`
is the exact five-addition child of `e52deab4`. Contract
`ncpcontract_85b051f1bc7a3d03fba136e3f85f50bd0fd3eca9f989e5252bddfeb99ced5fcf` binds the v18 terminal and
changes only parent/supervisor result transport to null stdio plus a bounded anonymous pipe. Sole qualification
commit `e54b399` records `sha256:1dc8eb6e484e56eb7bdbf8545fe5d40825a92ef864f46b94a5cf00bbdcf20c14`;
file `sha256:859219f58b3cf14c213fb6101b102166de1bebcb278a25155c4467ecbfa34af9`, 5,342 bytes. External observation,
mutation, state/approval/attempt/terminal and execution authority are 0.

## V18 supervised-frame activation — consumed ERROR

Source/tree `e4c76af0e101b1f9bc62ab2fde5ebc1c975f6f42`/`4efccdd2ccd06e10d78a7b90d037cb69dc5e5f27`
is the exact v17 activation child. Contract `ncpcontract_3f641a1b99490ee2db17339d7613a1debf79575e45cccecbc2f2128de1d45a5c`
has qualification `sha256:6f4825ef41eea63b6cc437ec2d3f06862b21d4a665c81880e82ee42bcf6b345d` at `50a4b28`.
State `ncpstate_dc0ca2031ee6bc274542bd6042f6e6b130e1ae476231c5e4bde1a361b5b26b26`/`749e359` and approval
`ncpapproval_8da57cdd99194cdc5d4af4e7c91ef1d31d4f12ea9d9d438ca05587755e57f094`/`99d2099` are nonreusable.
Lifecycle `490f1ed` records attempt `ncpattempt_9ee90622a86be952b924ec77c591b9b6f569d5383738ef6ed118810022a79a7b` and terminal
`ncpterminal_775512b68eac1b8f418c22a4ab30a450bf5ba8150f155f8bcbe4e5938acca516`; terminal file
`sha256:45f7d14859fd5cafde9ec551c5a8cb16a2b798f726ceffcab304c8321281e83f`, 19,255 bytes. Docker passed 8 stable
read-only calls; mutation/network/provider/credential metadata are 0. One supervisor child returned no envelope:
`ERROR(child_checker_error/supervised_output_invalid)`, incomplete/unknown accounting, raw output absent, retry false.

## V16 dedicated-frame activation — consumed ERROR

Contract `ncpcontract_e5ab4405de4e30a97c3524d157fbf74ad5757f61809c161bee07ede2dfc7564c` and qualification
`sha256:f2b3e1483bf67d00ea2b568986971454b7efeef1e0088f51fc1329077bffa091` led through nonreusable state/approval to
lifecycle `30c254d`. Attempt `ncpattempt_6ac263d18d68bbe764ac7b630bb5672f5e612add486d67af7f6a4b629328ada5`
ended at terminal `ncpterminal_db06f32f6223cdd227eb36b503b34ad6fc0eda817e563b21db9b896f8737c907`;
file `sha256:84b6c0d32a67d9d136b6fce98393e46a17f2321a28dc5b8562d6550b09f24ab5`, 19,089 bytes. Docker passed 8 reads,
then one child returned no envelope: `ERROR(child_checker_error/framed_output_invalid)`, forbidden counts 0,
accounting incomplete/unknown and retry false. Exact intermediate tuples remain in `reports/`.

## V15 dedicated-frame successor — source-qualified only

Source/tree `e962291bfea66980a66c7592e87ce5277b43b30a`/`082840944a46b2fc8d3b9f2df8afcc5d04b759ee`
is the exact five-addition child of `51bb6a6`; contract
`ncpcontract_ac6959d19db4d7a11ce199a32bde188fbfd515c7bdfcee9241d10ac164800f01` binds v14 without claiming
its unknown cause. Sole-artifact qualification commit `ac32e78` records
`sha256:0cdf9e0bb8ea981e7360bd7acd456c3b8aebfc6cf719aa2527e828ab7dc2f494`; file
`sha256:0112807f9a8bbe4831e7c9103859909c8266247ec0aaf551c2960978421b9708`, 4,755 bytes. External observation,
mutation and execution authority are 0; state/approval/attempt/terminal are absent. V16 is its separate wrapper.

## V14 manual-restart successor — consumed ERROR

Source/qualification/state/approval led to exact lifecycle commit `e63f418`: attempt
`ncpattempt_53b489aa63592c668529f3530f2af9c61a435c79ff40bcab5ec0aa1332a2267a` and terminal
`ncpterminal_d390b170b452fa9497f22bd46832330e3a9b4097b645c3a9094d8d424e801e5f`. Docker passed eight reads and
one child returned without an envelope. The result is `ERROR(child_checker_error/framed_output_invalid)` with recorded
forbidden counts 0, incomplete accounting, unknown activity true and retry false. Exact intermediate tuples remain in
`reports/`; no cost or A/C authority exists.

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
