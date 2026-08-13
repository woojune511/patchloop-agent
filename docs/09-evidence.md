# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## V23 typed diagnostic activation -- consumed ERROR

Source/tree `733ddc3cc74928f1011c58455fad6b151bfd25ad`/`8b2de30d46c2ac6eda7a45d6d9c6351624a60f75`
is the exact five-addition child of `77eb86bf7049a468ade4176cd2eafb15b0f2c6e0`. Contract
`ncpcontract_dfdfed2c3e5fabd39f3518cfe9aeae648ad38f182acc2efd2c478bbb449ada0a` is file
`sha256:b362ba003973e1b44d910b426c876f415a02d1c7354689358d0f6dbf010765b7` (4,530 bytes). Sole-artifact
qualification commit `f1c469d60280b67b40a852863ddf36d94f0d6b8e` records content/file
`sha256:f196bac8434dc78d061273ca87bd301237604face9bc93edcf1635afb1678f26`/
`sha256:32a8c74166daf84d20cda8317d434481135a93056e063800bb553efd2f7ae2f4` (14,099 bytes).

Qualification launched no diagnostic/mock/live process. State commit `93cc1c260de6f854b0d45cd556eb3ff324103a61` adds only
`ncpstate_c1fae9c0980bf18f55da673fa2416b48150976561a194097b98f39af1c71ee9d`; content/file
`sha256:c1fae9c0980bf18f55da673fa2416b48150976561a194097b98f39af1c71ee9d`/
`sha256:1c03262f461e8f56e7dbf91bed49e3a7b5387c1082ff032734b2bfe18ae0a9ad` (919 bytes). It is self-attested
non-proof. Approval commit `5a8e11fc320409d59005763be359a457e5ea119f` adds only
`ncpapproval_40be479a1d430f6353e872597109a581f806c136f48dac2d7982576fa4544637`; content/file
`sha256:40be479a1d430f6353e872597109a581f806c136f48dac2d7982576fa4544637`/
`sha256:08b6920e83fcf236b73312f9ef53ef40301594e6d2aca240a3857fe0776e35b8` (1,486 bytes).

Evidence commit `26e9562` adds exactly four lifecycle artifacts. Authorization
`ncprunauthorization_b73eebd60137a7e5e25332f50aee08d7cd02df8b5db9044fbb022b0aa42c9ca3`, attempt
`ncpattempt_c9ee0c8c0fe8f282e164e505f64d8f8d99561035173965ea9c9768d04ba31765`, `ACTION_STARTED`
`ncpstarted_cba147a0d487c20cc61ef81aff6d586741c417ea18c9338f3a6cd6539081051d` and terminal
`ncpterminal_376d5f2278445847db1b0a122d844606623bf04271baea46ecf3fa3fe8d0d004` have file SHA/bytes respectively
`sha256:260266575ff0445084b1b2eed15fb2c6d79c6c01aff7f3853298a371ea5de5f4`/990,
`sha256:16ee83121240b564205d2e874238d16289701d71204ae1735598c903ecb4a84a`/686,
`sha256:db6297b773c4f67c4a8892603c3ab922f10afabed538fd704ccae770975401cd`/521 and
`sha256:1be21372e64dd33357d7d176c9b79b88a82d5bf047481bb7e312559bcaa76237`/18,273.

Docker passed 8 read-only calls; parent-to-supervisor and supervisor-to-worker each launched once, returned code 0
and produced valid typed frames. The worker result was `diagnostic_result_invalid`, yielding
`ERROR(child_checker_error)` with incomplete/unknown accounting. Raw output, exception metadata and credential
value/hash/length returns are 0; network/provider counts are unknown. Retry/resume is false.

## V22 typed diagnostic channel -- immutable predecessor

Source/tree `454627d0eaa38b30e3795e3b9f1fb29546ca115d`/`65fbfcf2e92e6766b20d5aca38fb4c14d6c1fa3f`
is the exact five-addition child of `e763a2ed4fbb14659fcba88eb2c7411ab25eec0c`. Contract
`ncpcontract_721423c64d9cf0d5f1d4c0e25c7d5e3a25daa1b2b8081e221bc8e73b82367ccd` is file
`sha256:7909868309b4073574a13b94ffc9694bd111a1758090e4d0f26e2f9a64e794d4` (6,672 bytes). Sole-artifact
qualification commit `f8857597a5858ff78faedee190b3e33b449fe2db` records content/file
`sha256:497e2f72e3850cb6f60b59af768bafe6342b266ab82f7ea15c6576a22b483d42`/
`sha256:271197e7f0ef42544a4c6de6db0d47607b6a8b8a8b3c83268ad909bd6ebca8ef` (12,513 bytes).

V22 rejects callback execution and type coercion, preserving inner incomplete/unknown accounting. Its fixed mock and
qualification remain transport/source evidence only; V23 does not rewrite them. D-142 is not the current gate.

## V20 dual-pipe activation — consumed ERROR

Source/tree `304da8e9e4fe0d730c184944006e4c76970c12f0`/`0f43651ed75142c48b29b42664dbf90b22a37291`
is the exact four-addition child of `05e2b19`. Contract
`ncpcontract_2c5d22d26c1ae017e8b78d0e99fe99d33b5916b8282a1c186f25fbd818f68102` has qualification
`sha256:6e6a58dcaa1f034ad6146e955bdcd9a289b4031ec261ed22d71fc5264f8fe90b`. State
`ncpstate_7931e548e99c34ba36b334bab032d7359701929cbb6866d8b713bc2c94b9d17b` and approval
`ncpapproval_4dc5670957a304fcbf4178479059a61217a528d008a5f4d70603269e11c0c49f` led to lifecycle `5cc6b96`.
Attempt `ncpattempt_ceb920acc4c49d71dfaf196f890f2d7ddb37b48b2c3cbad2d43892ecb2e2ab6a` ended at terminal
`ncpterminal_d528eb39f0e367fe8b38b81ae3a3ddbd627d9c9cefe6a84e8874523b7e488897`; terminal file
`sha256:6ddeabb4fb8f6632887382c9a5f9f1bf4f16dd721873d75af439b4b2e2c2c60b`, 22,558 bytes. Docker passed 8 reads;
the outer pipe returned nonempty at code 0 but the supervisor envelope was invalid. Recorded forbidden counts are 0,
raw output is absent, accounting is incomplete/unknown, outcome is `ERROR(child_checker_error)` and retry is false.

## V12-V18 framed predecessors — compact index

V12/V14/V16/V18 are consumed checker errors after Docker passed; their terminal details are respectively
`child_output_invalid`, `framed_output_invalid`, `framed_output_invalid` and `supervised_output_invalid`. V13 is a
consumed `BLOCKED(docker_not_ready)` lifecycle. V15 is source-qualified only and V16 is its separate activation.
Their exact source, qualification, state, approval, attempt, terminal and file tuples remain canonical in `reports/`;
no predecessor can retry and none grants cost or A/C authority.

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
