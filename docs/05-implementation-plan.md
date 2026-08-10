# Implementation plan

상태: active roadmap only. The cumulative D-001–D-121 plan is archived at
`docs/archive/snapshots/d121/05-implementation-plan.full.md`.

## Sequencing rule

Finish one evidence boundary before opening the next. Offline implementation does not authorize Docker,
provider, evaluator or paid execution. A failed one-use claim is preserved and not silently repaired.

## Current objective

D-136 pricing, D-137 Docker/SDK and D-138 SDK no-call phases are consumed. D-138 ended missing-key BLOCKED.
D-139 successor source qualification is complete; next request only a fresh exact D-139 SDK activation.
Hash/candidate, cost and execution remain separate.

## Completed foundation

- The four-run A/C plan and compact active-document structure are materialized; the D-121 snapshot preserves
  earlier detail.
- `fixed-d110-bundle-v1` binds exact D-105/D-110 inputs, renders A null and C three entries on every request,
  and exposes no retrieval, provenance, vector or raw-trace content.
- Offline tests cover request/CAS/context replay, tamper, leak, token, fresh-workspace and no-call boundaries.
- D-122 through D-135 are immutable predecessors. D-132 is consumed without canonical response evidence and
  D-135 closes it procedurally without backfill.
- D-136 completed its exact receipt/attempt/marker/terminal sequence. Its replayable terminal records one public
  GET, HTTP 200, zero redirects and 3,735 bytes with provider/evaluator/agent calls and cost 0.
- D-137 completed Docker READY then SDK missing-key BLOCKED transitions with no Docker mutation, credential value
  read, SDK import/probe, dispatch or network call; both phases are consumed.
- D-138 completed receipt, attempt and ACTION_STARTED+BLOCKED at
  `9f31d330190aa83768077b17c3cde47eb86c639d`. It found the key-presence bit false after three membership
  checks; value/`.env`, child, SDK import/probe, dispatch and network counts were 0. It is consumed.
- D-139 source `f5625be6cf98b5f8824a0d6a5068f1cf03e94d98` and gate
  `d139_09f2e9dfe0ee333a2683c058b772b92f025708c4bcc6b7f1eb89c007ed8df7f8` qualify only the fresh successor
  contract. Fully mocked focused tests passed 168/168; no D-139 runtime artifact or external observation exists.
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

Status: D-136 through D-138 consumed; D-139 SDK successor source-qualified; fresh exact activation required.

The D-132 pricing marker consumed its activation/attempt. Application-level send returned once, but HTTP and
response fields remain unknown/unretained and completed/replayable canonical pricing evidence count is 0.
D-134's ambiguous gate is
preservation-only.

D-135 removes that ambiguity and its terminal-only commit preserves the incident. D-136 then completed one
bounded official public capture under a new fixed helper. Its success terminal is replayable pricing evidence,
not Docker/SDK readiness or downstream execution authority.

D-137 used a receipt, separate Docker/SDK attempts and fsynced markers. Docker became READY after bounded
read-only observations; SDK became BLOCKED when `OPENAI_API_KEY` presence was false. Its value, `.env`, import,
probe, dispatch and network counts were 0. Neither phase may be retried.

D-138 used that contract once, found `OPENAI_API_KEY` absent and committed a BLOCKED terminal. Exactly three
membership checks and zero value/`.env`/child/import/probe/dispatch/network activity were recorded. It cannot be
reopened.

D-139 requires a new receipt-only commit, SDK-attempt-only commit and fsynced marker before three membership-only
checks. The parent uses inherited-environment repository-venv Python `-E -s -B`; eligible SDK validation runs in
one bounded `env={}` child with fixed nonsecret placeholder, no ambient forwarding and zero transport dispatch.
Its audit hook starts after CPython/site startup, so pre-bootstrap network absence is not claimed. Commit a
READY/BLOCKED terminal, or marker only after failure, then stop for a separate offline successor.

## Work item 7 — execution hash and candidate

Status: unauthorized. No D-139 terminal exists; even a future D-139 READY terminal grants no such authority.

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
