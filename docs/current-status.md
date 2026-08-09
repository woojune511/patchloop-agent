# Current status — 2026-08-10

## Current checkpoint

D-136 is the current fixed-pricing successor offline source-qualification gate:

- Gate ID/body `d136_aef9768fcc24b48df09034d14aefcd02b1812531fe77bf56ca1601ac4e5e00fd`;
  file `sha256:c9e00304383839c656b6a2753fefee459fb14934dec8dfabcf4f39f44a34a53b`,
  23,767 bytes.
- Source commit `96916ac481ac8beced2db0be9022607e0705e018`, tree
  `7e0a07eed6e780265a5d73cab008a0fabe935fe1`, sole parent
  `98f4560e718145bc7465732c1a3d2f5a4ea8d786`; status
  `D136_D135_FIXED_PRICING_SUCCESSOR_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED`.

The exact gate+10-active-doc evidence commit is the direct child of that source and is reported by the
post-commit validator. D-136 exact-binds the D-135 terminal and predecessor-gate topology. Its new helper keeps
the exact URL, unauthenticated request, redirect, decoded-size and replay boundaries while replacing response
context-manager use with explicit `try/finally` close semantics. Focused tests passed 29/29; the selected
relevant set passed 102/102 including focused, so counts are not additive.

## Consumed D-132 pricing incident

D-132 activation and its pricing attempt are consumed and cannot be retried, resumed, repaired or backfilled.
Application-level unauthenticated `client.send` returned a `Response` once. Underlying HTTP request count and
completion are unknown; canonical response status, headers, body and redirect accounting are unretained.
Completed/replayable canonical pricing evidence count is 0, no canonical evidence artifact exists, and replay
bytes are 0.

D-133 preserved the action-started marker at `a10033b6abd7155ebaa5c66c13627ad3ea738566`.
D-134's ambiguous gate is preserved by sole-child commit `9dc450a747537634e89fe2ade824685f8b5a52d6`,
but its qualification status and terminalization authority are invalid. D-135 then sealed the corrected
procedural terminal as the sole artifact in commit `98f4560e718145bc7465732c1a3d2f5a4ea8d786`; this did not create
canonical pricing evidence or reopen D-132.

## Historical D-129 terminal

D-129 remains terminally sequence-blocked because a docs open preceded its receipt/attempt. It has no canonical
capture or retroactive attempt and is never retried or repaired; exact tuples are in `docs/09-evidence.md`.

## Manual readiness boundary

D-132 machine evidence recorded Docker 29.6.2 linux/amd64 and both exact images READY from six read-only rc-0
calls, with zero pulls or mutations. That observation is historical and not future-fresh. The user's
no-auto-start statement remains self-attested and was not independently verified.

## Experiment direction: four-run A/C readiness

The checked-in plan fixes Moto A, Moto C, Babel C and Babel A once. C receives the exact D-110 three-rule
bundle; model, prompt, tools, policy and ceilings otherwise match A. This is readiness work, not held-out
efficacy evidence, and there is still no supported live command.

## Closed authority

D-126 through D-131 are immutable blocked or local predecessors. D-132 activation is consumed at the pricing
marker boundary, D-134's gate is preservation-only, and the D-135 terminal is incident preservation only.
D-136 created no activation receipt, attempt, action-started marker, pricing evidence or terminal. Its offline
preparation made zero official-docs/network/pricing, Docker/SDK/credential, provider/evaluator/agent and
memory/retrieval calls. Execution hash/candidate, cost and A/C remain unauthorized and absent.

The deferred D-121 candidate
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`
was never authorized and is not a fixed-bundle prerequisite.

## Next gate

After the gate+docs evidence commit, request one fresh exact D-136 pricing activation quoting the gate tuple,
source commit/tree and evidence-commit tuple. The qualified future sequence requires receipt-only then
attempt-only commits, an fsynced action-started marker immediately before helper dispatch, and either a
marker+pricing-terminal success commit or marker-only preservation after failure. Any post-marker failure
consumes the activation and forbids retry. A successful pricing terminal does not authorize Docker/SDK
preflight; that requires a later offline successor and separate approval. Hash/candidate, cost and A/C remain
separate closed gates.
