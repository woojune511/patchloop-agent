# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-138 SDK no-call successor — source-qualified only

- Gate `reports/live-pilot/artifacts/d138-d137-sdk-blocked-no-call-successor-offline-source-gate.json`:
  ID/body `d138_fb8eb1890fc6b9723e9c1e7651eaccc6881a94ab277e94b16a8f6ef2fae41e1f`;
  file `sha256:ea77b4a9d387ab649f21ed7c3dd35b2095e6143514b20604b1d9c16fffe804fb`,
  17,533 bytes; blob `65b6ca1e3968a1539005a5e815c855c937bbf5b8`.
- Source commit `f1f821cd57feb8e1405929ff949e82892e3de6f9`, tree
  `b493d9c36a8cdcee646e5773ffe81353bf1d5c8a`, sole parent
  `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01`; its diff is exactly four added implementation paths.
- The gate-add/10-active-doc evidence commit is the source's direct child; the post-commit validator reports its
  exact tuple without embedding a self-referential commit hash here.

The gate replay-validates the complete D-137 chain and qualifies only the future one-use SDK successor contract.
Injected-mock focused tests passed 168/168. No D-138 receipt, attempt, marker, terminal or preservation artifact
exists; preparation observed no environment/credential presence or value, SDK, endpoint, network or Docker state.

## D-137 Docker READY then SDK BLOCKED — consumed

- Gate commit `0f69783ea7ab6d55d76071f43b2cd1c32da673f2`; receipt-only commit
  `f18b5d28c1584ad6db02f53ccfd953e8a599c04c`; Docker-attempt-only commit
  `06f32a2874f1a52eccece6129b97b4cb12aee45e`.
- Docker ACTION_STARTED `reports/live-pilot/artifacts/d137-docker-no-call-preflight-action-started.json` and READY
  terminal `reports/live-pilot/artifacts/d137-docker-no-call-preflight-terminal.json` were added together by
  commit `06e57c54b4fe09f3145b8b59e51a0e391108d52a`, tree
  `180c38200f02f85d053dc37b1c76d3b8343dd6ca`, sole parent `06f32a2874f1a52eccece6129b97b4cb12aee45e`.
- SDK-attempt-only commit `6886edfcee1159530dde2f8569956e6ace657624`, tree
  `086b0f3856c77261ebf537067ad958c7e283a9a4`, is that transition's sole child.
- SDK ACTION_STARTED `reports/live-pilot/artifacts/d137-sdk-no-call-preflight-action-started.json`:
  ID/body `d137sdkstarted_aae9b054b6c8d07454d2996f3104c5ed7ee05ef78d13056306651c1b605dd17b`;
  file `sha256:8e8cc3e2706d99054315863ccbfb00cfd69bebbce7e52c2405e4b91b2f4bcfd1`, 2,521 bytes.
- SDK BLOCKED terminal `reports/live-pilot/artifacts/d137-sdk-no-call-preflight-terminal.json`:
  ID/body `d137sdk_84be6f103e7e9cf624da94959b3fba94ad561ba5e721b6768a3b43c781c66c3e`;
  file `sha256:3c071545593e37adf760314e3dd6077c74adc0e8422f34a041249c017d53b31c`, 5,335 bytes.
- Exact SDK transition commit `8aa0ebf09b51b5ca6fc6cee90a7136cfb95a8a01`, tree
  `bc30a0534d5a30822127d0fb6e459bd0fb6a6a31`, sole parent `6886edfcee1159530dde2f8569956e6ace657624`.

Docker used eight bounded read-only commands, reached READY and mutated nothing. SDK checked three membership
bits, found `OPENAI_API_KEY` absent, and performed zero value/`.env` read, SDK import/probe, transport dispatch
or network call. D-137 is consumed and cannot be retried, resumed, repaired or backfilled.

## D-136 fixed-pricing successor — succeeded and consumed

- Gate evidence commit `5fad5756d2b40b5f72c0bbc38680120d780ef899`; activation receipt commit
  `1f9c62ac9309d087d1ef32a237b86ea11bf9d51e`; pricing attempt commit
  `5f419828c358ee9c5f68cdacf38b588705e71e2e`.
- ACTION_STARTED `reports/live-pilot/artifacts/d136-fixed-pricing-capture-action-started.json`:
  ID/body `d136pricingstarted_6f4847c856150b0d6bef6108d858ff332d3a1b2c95b0c9ea6bec80d024729fc1`;
  file `sha256:4c11a5e087759ecb2a57f5a64271000214469a35f952e8789cc68b297173cd0a`,
  2,387 bytes; blob `b6090028bb40a6dce721bb1a2c6126cb094537f4`.
- Terminal `reports/live-pilot/artifacts/d136-replayable-official-pricing-evidence.json`:
  ID/body `d136pricing_dbaa24227565316ef404fb1fc2967e2eb45600a92d7365b8fbbfd7d264881362`;
  file `sha256:7ce984e1b7f11bfe9aaaed8a4db38af22ab1299086c54ca20e090badc2d33bc0`,
  10,191 bytes; blob `ee61520b3325e7a4e2ab891aeccff1a92862a543`.
- Exact two-artifact success commit `2378569536c2367a3186f575a7517e3de7282336`, tree
  `c6253191e0a5d96fd6503ad9f9f4f6df91af13cc`, sole parent
  `5f419828c358ee9c5f68cdacf38b588705e71e2e`.

The terminal preserves one unauthenticated official public GET, HTTP 200, redirect count 0 and 3,735 decoded
replay bytes. Provider/evaluator/agent calls and cost reservation/spend are 0. The activation and phase are
consumed and never reused; the terminal grants no Docker/SDK, hash/candidate, cost or A/C authority.

## D-132 through D-135 consumed incident — compact index

- D-132 attempt `reports/live-pilot/artifacts/d130-official-pricing-capture-attempt-intent.json` is commit
  `30412b769b340f98000674f40de9102d1210507a`; D-133 marker
  `reports/live-pilot/artifacts/d130-official-pricing-capture-action-started.json` is marker-only commit
  `a10033b6abd7155ebaa5c66c13627ad3ea738566`.
- D-134 gate `reports/live-pilot/artifacts/d134-d132-pricing-consumed-incident-procedural-terminal-offline-source-gate.json`
  is preserved, invalid and non-authoritative by commit `9dc450a747537634e89fe2ade824685f8b5a52d6`.
- D-135 terminal `reports/live-pilot/artifacts/d135-d132-pricing-consumed-incident-procedural-terminal.json`:
  ID/body `d135pricingincident_7684c346db32bac34404137a0839c852ce00209ded9d0f9aa444a0a73d519f75`;
  file `sha256:ac0f8a6a8d3282f14d3d6b5ab8176e0fe4f64a8bb509e4cd1380ca6a76b2438a`,
  22,084 bytes; terminal-only commit `98f4560e718145bc7465732c1a3d2f5a4ea8d786`.

Application-level send returned one `Response`; HTTP completion and response fields remain unknown/unretained.
Canonical pricing evidence count and replay bytes are 0. Nothing in this chain permits reconstruction, retry,
resume, repair or backfill.

## Older predecessor index

D-131 receipt/intent are local admission only. D-129 is terminal sequence-blocked; D-127/D-128 remain terminal
blocked and D-126 observed blocked. Exact IDs and tuples remain in their canonical artifacts and Git history;
D-121 is deferred.

## Next evidence boundary

Obtain a fresh exact D-138 activation quoting gate, source and evidence-commit tuples. It may create only a
receipt commit, then an SDK-attempt commit. The exact parent writes/fsyncs its marker before membership-only
checks; eligible SDK work runs only in the bounded empty-environment child. Commit READY/BLOCKED terminal or,
after failure, marker only; never retry. Any terminal requires a separate offline successor and grants no
provider/evaluator/agent, memory/retrieval, hash/candidate, cost or A/C authority.
