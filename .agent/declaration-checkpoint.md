# Frozen post-search declaration comparison

`diagnostics.declaration_sampler` prepares, validates, collects and inspects a
four-response diagnostic. It reuses the existing `decision_sampler` cost/transport
collector. It changes no normal runtime defaults or prompt/tool schemas.

## Supported checkpoint

The source is an exact, hash-bound dev-train public task, journal and envelope from
the same runtime. Only the second model request after one successful initial batch
of 1–4 `search_files` actions is supported. It must use segmented-v1, ordinary
protected-v1 inspection, per-call-v1 cost admission, default segment boundaries,
probe-policy none, and a verified prepared source. No edit/check/probe/finish is
replayed. Missing source, mismatched counts, uncertain prior billing or corrupt
encrypted continuation fails before credentials or a provider are accessed.

The preparer copies the exact prefix through search admission into new diagnostic
journals. Inherited dispatch/usage events are historical evidence, not new calls.
The first plan, notes, original model input and opaque continuation are retained.
Only the already requested public searches execute against the clean prepared source,
in their recorded completion order. The source run is never appended or resumed.

A uses the original search result. B uses the generic rule in
[declaration context](declaration-context.md). Both pass through the ordinary gateway,
source ledger, counters, context projection and native input builder. A must match
the saved canonical state and request exactly. B may change only source-derived
fields, result fingerprints, delivery references and returned documentation.
Budgets, task/diff/checks, plan/notes, horizon, continuation, original calls, prompt,
tools and segment stay fixed. A model's original interpretation is not reset.

Stored body strings are retained exactly. CAS sorts dictionary keys; both arms use
the same saved native-item key order and the pinned builder's tool-schema order.
The identity claim is about saved requests and body strings, not uncaptured HTTP bytes.

## Collection and limits

`prepare --source <source.json> --output <new-external-root> --proposed-cap-usd <cap>`
builds an immutable packet with exact source/implementation/artifact/request hashes.
The source JSON contains `root`, `run_id`, `journal_hash`, `envelope_hash`,
`public_path` and `public_hash`. `validate --packet ... --packet-hash ...` rechecks
identities and the A request without reexecuting searches or reading credentials.

`collect --packet ... --packet-hash ... --grant <grant.json>` accepts the shared
`Approval` fields: packet hash, sampler hash, fresh external result root, exact root
`.env`, positive invocation cap, pricing hash and execution-date price review.
Preparation/proposed cost is not authority to spend. Live code/task/runtime must be
tracked and clean. No Docker startup/image/preflight is needed for this diagnostic.

The fixed order is A1 → B1 → B2 → A2, two independent next responses per arm.
Each response begins from its own frozen A/B request; no sampled response is chained.
The source model and effort are fixed, with a 25,000 output ceiling and 60,000 input
bound. Each pair reserves its full input/output bound, and actual input is counted
immediately before dispatch. The shared collector uses zero SDK retries and stops
all remaining cells on count/provider/billing/continuation uncertainty. No retry,
resume, correction, replacement or extra sample is available. `inspect --result ...`
reports an interrupted/unknown receipt without issuing another call.

Selected tools are never executed. Existing source-budget values remain identical
model input in A/B; a separate new ledger owns actual diagnostic spending. Anonymous
public decisions can be reviewed before arm/cost metadata. Acceptance and safety
remain NOT_RUN; all results are official=false and claim_eligible=false.

## Interpretation

This measures the immediate public question/action proposed after supplemental
documentation. If a response selects a read, its eventual edit is unmeasured. It
does not establish completed verification, task acceptance, the cause of the original
plan, or a general success rate. A consistent difference is a reason to consider a
separate bounded rollout; it does not change defaults automatically.
