# Implementation plan

상태: active roadmap only. The cumulative D-001–D-121 plan is archived at
`docs/archive/snapshots/d121/05-implementation-plan.full.md`.

## Sequencing rule

Finish one evidence boundary before opening the next. Offline implementation does not authorize Docker,
provider, evaluator or paid execution. A failed one-use claim is preserved and not silently repaired.

## Current objective

Stop after the D-128 terminal blocker. The consumed receipt cannot be retried. Wait for the user to verify the
Docker Desktop Linux daemon endpoint is reachable and provide a new exact successor approval. The agent must
not start the daemon; all later gates remain closed.

## Completed foundation

- The four-run A/C plan and compact active-document structure are materialized; the D-121 snapshot preserves
  earlier detail.
- `fixed-d110-bundle-v1` binds exact D-105/D-110 inputs, renders A null and C three entries on every request,
  and exposes no retrieval, provenance, vector or raw-trace content.
- Offline tests cover request/CAS/context replay, tamper, leak, token, fresh-workspace and no-call boundaries.
- D-122 through D-125 are historical predecessors; D-126 is the latest sealed blocked no-call preflight gate.
- The historical four-condition template and selective-retrieval authority remain unchanged and closed.

## Work item 5 — exact cost reservation and completion gate

Status: implemented in D-123, corrected/finalization-qualified by historical D-124/D-125; candidate BLOCKED.

- R2 reserves four row-bound worst cases before the first provider call: $13.6125 each, $54.45 total.
- The source enforces the proposed $55.00 hard cap, $0.55 slack and durable usage-derived settlement.
- The completion source requires one terminal, settled, qualified and officially evaluated result for each
  exact row and validates resolved/SCRR/four-verdict consistency.
- Missing, duplicate, retried, replaced, unsettled or schedule-mismatched rows remain inconclusive.

D-125 qualifies repository-local consumption and mocked finalization only, not global/cross-clone,
actual-kill or power-loss guarantees. No live action or cost occurred.

## Work item 6 — clean/pricing/no-call preflight

Status: D-126 sealed blocked; D-127 historical terminal blocked; D-128 external terminal blocked.

D-126 remains the latest sealed gate and D-127 remains an unchanged blocked predecessor. D-128 used source
`23038c16467a32c5b862f84e09797a298101f4e4` and receipt-only child
`4b2ef5a15e9c721c1c8fa1e73375a3bf061bda50`. After durable attempt intent, the exact CLI made three read-only
calls (`version`, Moto inspect, Babel inspect), all return code 1, and recorded blocker
`already-running-docker-desktop-linux-daemon-unavailable`.

Desktop/daemon start, image pull/mutation, container/workload, pricing GET, SDK attempt, gate, provider/
evaluator/agent, retrieval/injection, hash/candidate, cost and A/C counts remain zero. No downstream descendant
was created. The receipt is consumed; work item 6 can continue only through a newly approved successor.

## Work item 7 — execution hash and candidate

Status: unauthorized and separately gated after a ready repeated work-item-6 preflight.

Create neither identity until a later approval cites the exact ready gate and explicitly authorizes it.

## Work item 8 — separately approved execution

Status: unauthorized.

Only a later user message citing the exact candidate triple, execution hash and $55 cap may authorize one
four-row run. Execution stops without replacement if the matrix becomes incomplete. Results are descriptive
readiness evidence only.

## Decision after the four rows

Choose one of:

1. Injection path invalid — correct offline under a new version; do not rerun the same live plan.
2. Workflow valid but outcomes mixed/negative — preserve result and decide whether structured memory merits
   a held-out pilot.
3. Workflow valid and direction encouraging — pre-register a separate held-out A/C design and repetition count.

No outcome automatically unlocks B, D or the full four-condition campaign.

## Deferred lanes

- D-121 fresh hash-only isolation successor execution
- External blind-control acquisition and public applicability calibration
- Selective score-policy correction and runtime retrieval
- Raw-trace source/redaction/truncation
- Held-out A/C and full A/B/C/D campaigns
- Viewer/GitHub demo work that does not improve experimental evidence
