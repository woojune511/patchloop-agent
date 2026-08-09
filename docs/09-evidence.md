# Evidence index

Canonical machine artifacts under `reports/` are authoritative. Historical narrative is archived at
`docs/archive/snapshots/d121/09-evidence.full.md`.

## D-136 fixed-pricing successor — fresh activation required

- Gate `reports/live-pilot/artifacts/d136-d135-fixed-pricing-successor-offline-source-gate.json`:
  ID/body `d136_aef9768fcc24b48df09034d14aefcd02b1812531fe77bf56ca1601ac4e5e00fd`;
  file `sha256:c9e00304383839c656b6a2753fefee459fb14934dec8dfabcf4f39f44a34a53b`,
  23,767 bytes.
- Source commit `96916ac481ac8beced2db0be9022607e0705e018`, tree
  `7e0a07eed6e780265a5d73cab008a0fabe935fe1`, sole parent
  `98f4560e718145bc7465732c1a3d2f5a4ea8d786`; status
  `D136_D135_FIXED_PRICING_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED`.
- The exact gate-add/10-active-doc evidence commit is the direct child of the source; the post-commit validator
  reports its commit/tree/parent/blob tuple.

The gate binds the D-135 terminal bytes/commit and predecessor-gate topology. The new helper uses explicit
`try/finally` close semantics without importing the sealed D-127 helper or consumed D-132 runner. Focused tests
passed 29/29; the selected relevant set passed 102/102 with focused included, so counts are not additive. No
D-136 activation receipt, attempt, action-started marker, pricing evidence or terminal was created, and external
actions are 0.

## D-135 consumed-incident procedural terminal — sealed

- Terminal `reports/live-pilot/artifacts/d135-d132-pricing-consumed-incident-procedural-terminal.json`:
  ID/body `d135pricingincident_7684c346db32bac34404137a0839c852ce00209ded9d0f9aa444a0a73d519f75`;
  file `sha256:ac0f8a6a8d3282f14d3d6b5ab8176e0fe4f64a8bb509e4cd1380ca6a76b2438a`,
  22,084 bytes; blob `8efce4a2508cddd32b59d9be92f3eb65517b1552`.
- Terminal-only commit `98f4560e718145bc7465732c1a3d2f5a4ea8d786`, tree
  `901c123f425733ee77e5c8db926ffa4f98edd431`, sole parent
  `e0a26f0134b811fca2cd76d3d8a69ec2a484cabb`.

The terminal preserves consumed/no-retry and unknown/unretained observations. It is not canonical pricing
evidence and does not infer or backfill an HTTP exchange or response.

## D-135 ambiguous-gate correction — historical source gate

- Gate `reports/live-pilot/artifacts/d135-d134-ambiguous-gate-correction-offline-source-gate.json`:
  ID/body `d135_7e67561d187cfb44440790052a95fc8b95a4006fe886e0f7c3dce9bae437e8c6`;
  file `sha256:37639f8327d1f29a5ce2321c0f2ba79e3ada7821c1bac1995770faea5237cce0`,
  22,922 bytes.
- Source commit `ca50402aa8d3965ea384563262c713c6090d2ecf`; status
  `D135_D134_AMBIGUOUS_GATE_CORRECTION_OFFLINE_SOURCE_QUALIFIED_TERMINALIZATION_APPROVAL_REQUIRED`.
- The gate-add/10-active-doc evidence commit is the direct child of the source commit; use the post-commit
  validator for its exact commit/tree/parent/blob tuple.

The gate exact-binds the D-132 pricing attempt/marker, D-134 source, preserved ambiguous gate and its
preservation-only commit. It treats the D-134 recorded status and next-gate text as invalid and
non-authoritative, omits the ambiguous numeric GET-count claim and qualified only the now-sealed D-135
procedural-terminal writer. Focused tests passed 15/15; selected regression passed 85/85 with focused included,
so counts are not additive. Source/gate preparation made zero external calls.

## D-134 ambiguous gate — preserved, invalid and non-authoritative

- Source commit `44a461de923357f36cadc94eebd14d264a7366fc`.
- Gate `reports/live-pilot/artifacts/d134-d132-pricing-consumed-incident-procedural-terminal-offline-source-gate.json`:
  ID/body `d134_a6ec18615a853b34de104a4a89d0db1d43bea3cea12c1412033e260c50779889`;
  file `sha256:ed32146e25b0fbde90ea3e1bbc7f63badbc1be098f3b031c09321e914a0f9b3c`,
  18,882 bytes; blob `56fdd6d3336fc402af13bf4d3ac63d47d57805aa`.
- Preservation-only commit `9dc450a747537634e89fe2ade824685f8b5a52d6` is the sole child of the D-134 source.

The preserved bytes contain an ambiguous numeric GET-count claim. They are historical evidence only and cannot
authorize a D-134 terminal, pricing retry, response reconstruction or successor activation.

## D-132 pricing attempt and D-133 marker preservation — consumed

- Attempt `reports/live-pilot/artifacts/d130-official-pricing-capture-attempt-intent.json`:
  ID/body `d132d130officialpricingcaptureattempt_c518711e0a12b75a3ab81bbfd3e53eb3e13059d0f6fe4b3c4c1309e25924245f`;
  file `sha256:ba79ad9362bf14f0cdf8952d9297bea8fcd77fe36ab0eeff44e47e9047ec3f55`,
  18,137 bytes; commit `30412b769b340f98000674f40de9102d1210507a`.
- Marker `reports/live-pilot/artifacts/d130-official-pricing-capture-action-started.json`:
  ID/body `d132d130officialpricingcapturestarted_50876b05d4daa48d5f80bce7793f28ffb4f7909350661803dfa96f9a2e6dced7`;
  file `sha256:328c4fb5ae4d6e50308333e360f25fb88bc856bace7ba483f2eb7e2adde13328`,
  12,815 bytes; marker-only commit `a10033b6abd7155ebaa5c66c13627ad3ea738566`.

Application-level unauthenticated `client.send` returned one `Response`. Underlying HTTP request count/completion and
response status, headers, body and redirects are unknown/unretained. Completed/replayable canonical pricing
evidence count is 0, no canonical pricing artifact exists and retained replay bytes are 0. The activation and pricing
attempt are consumed; retry, resume, repair and terminal backfill are forbidden.

## D-131 local admission — immutable predecessor

- Gate ID `d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`;
  evidence commit `283b9124af38252f47a06cbb1a484807b5030be2`.
- Receipt ID `d130approval_03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010`;
  receipt-only commit `6987246b438fa6e6e711fa3b254aaf75ac4c2a66`.
- Intent ID `d130intent_4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153`;
  intent-only commit `4a40971b4e155683c49bbd6bcadc7468514ef84c`.

Receipt and intent are local-admission evidence, not reusable external activation.

## Older blocked chain

- D-130 offline gate ID `d130_443b0bc935ba6affd4a009dee780ae85ec1ecdc1e3ce62edcd566e12307c74db`;
  evidence commit `d6079e55fd1c4745b05c2e345228b1a66d0a3df4`.
- D-129 terminal ID `d129sequenceblock_b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8`;
  status `D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED`.
- D-127/D-128 remain terminal blocked; D-126 remains observed blocked. D-125 and earlier tuples remain in their
  canonical artifacts and Git history. D-121 is deferred.

## Next evidence boundary

After the D-136 gate+10-doc evidence commit, obtain a fresh exact D-136 activation quoting the gate tuple,
source commit/tree and evidence-commit tuple. It may create only the qualified
receipt/attempt/marker/capture sequence. A post-marker failure consumes the activation and permits only
marker-only preservation, never retry. A success terminal still grants no Docker/SDK preflight,
provider/evaluator/agent activity, memory/retrieval, hash/candidate, cost or A/C authority; those require later
distinct source qualification and approvals.
