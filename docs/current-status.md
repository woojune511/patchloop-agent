# Current status — 2026-08-09

## Current checkpoint

D-132 is the current offline-source-qualified D-130 external-activation implementation gate:

- ID/body `d132_ae224ab320e74bf871b74b0c9df23f88c5de170dfd26e7724aa234f29b2b0ba7`;
  file `sha256:059f672967aeed4b9f07db7249e887b92c3ad999ba96c61a8605e3d67f064bd0`,
  27,244 bytes.
- Source commit `ccf898d869342a9d5da42a1fef2c00e593fe91b4`, tree
  `0bab1f4c64f89070de9cedeeadc62b36668c3f72`, sole parent
  `4a40971b4e155683c49bbd6bcadc7468514ef84c`; status
  `D132_D130_EXTERNAL_ACTIVATION_IMPLEMENTATION_OFFLINE_SOURCE_QUALIFIED_FRESH_ACTIVATION_REQUIRED`.

The predecessor chain is materialized: D-131 gate
`d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`, D-130 local receipt
`d130approval_03c8c824f0d74122b8233df9810897b898c29b3bf907dd1a5cfd364f5026e010` at commit
`6987246b438fa6e6e711fa3b254aaf75ac4c2a66`, and armed intent
`d130intent_4cd20c7a8bbd20751b2f6a7b4a0d13de16d7aa5a41b6bf20648dedb414b6a153` at commit
`4a40971b4e155683c49bbd6bcadc7468514ef84c`. Receipt and intent are local admission, not activation.

D-132 binds the activation receipt-only child, ordered Docker/pricing/preflight attempt-first transitions,
durable action-started markers, terminal commits and final gate. The builder invoked no future writer/helper.
Focused tests passed 15/15; selected regression passed 170/170 including focused, so counts are not additive.

## Historical D-129 terminal

D-129 is terminally sequence-blocked because one approved public pricing-docs open preceded its required
machine receipt and durable attempt. Underlying HTTP/redirect/content counts are unknown; no canonical capture
or retroactive attempt exists. Receipt
`d129approval_0d505214f607b0f2a2536e1b754750131bc4b6dab2995d24a12554d63090fb42` is consumed and terminal
`d129sequenceblock_b5fc90e29ed2ca7febda54a2e63e4f5a0606703e0e93a997fab719d33797f5c8` has status
`D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED`. Docker/SDK/runtime/hash/cost/A-C stayed zero; do not retry,
resume or repair D-129. Exact tuples remain in `docs/09-evidence.md` and machine artifacts.

## Manual readiness boundary

The user's daemon-unavailable/rc 1 then 29.6.2 linux/amd64/rc 0/no-auto-start observations are self-attested,
were not independently observed by D-129 through D-132 and are not future-fresh.

## Current priority: four-run A/C readiness

The checked-in plan fixes Moto A, Moto C, Babel C and Babel A once. C receives the exact D-110 three-rule
bundle; model, prompt, tools, policy and ceilings otherwise match A. This is readiness work, not held-out
efficacy evidence, and there is still no supported live command.

## Closed authority

D-126 is sealed blocked; D-127/D-128 are terminal-blocked and D-129 preserves a procedural incident only.
D-130/D-131 are immutable predecessors. The pre-D-132 activation request/challenge was received but explicitly
said it was not activation; it is unexercised and non-reusable after the D-132 topology change. No D-132
activation receipt, phase attempt/started/terminal, final gate or external action exists. Official-docs/network,
pricing, Docker/SDK/credential, provider/evaluator/agent, runtime memory/retrieval, execution hash/candidate,
cost and A/C remain unauthorized and at D-132 source-preparation count zero.

The deferred D-121 candidate
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`
was never authorized and is not a fixed-bundle prerequisite.

## Next gate

After the exact gate-add/10-active-docs evidence commit is complete, request a fresh exact D-132-qualified
activation quoting its gate/evidence tuple plus the D-131 gate, D-130 receipt, D-130 intent and both commits.
That approval may first create an activation receipt-only commit. Each later phase must create and commit its
attempt before an action-started marker and helper call; terminal transitions must be committed before the next
phase. Started-without-terminal and orphan/blocked phases are consumed and not retried. No activation is
currently approved; hash/candidate, cost and A/C remain separate later gates.
