# Implementation plan

Status: active fast-track roadmap. Historical milestone plans remain under `docs/archive/snapshots/d121/`.

## Sequencing rule

Preserve observed attempts, but do not consume unchanged source or configuration. Local no-call readiness may be
retried up to three times for transient pre-provider failures. Provider execution still requires an exact execution
hash, fixed schedule, hard cost cap and one explicit campaign approval.

## Preserved foundation

D-098 is a development baseline; D-110 froze three entries and D-112/D-115 left selective retrieval unready.
`fixed-d110-bundle-v1` keeps A null and C exact-three. D-129-D-141, D-142 and V1-V25 remain historical evidence;
none is relabeled as evaluator-v2 live evidence.

## Work item 1 — evaluator correctness v2

Status: implemented and locally verified.

Task-bound projections, typed safety evidence, fail-closed four-verdict aggregation, authority-gated runner,
receipt, persistence, qualification and completion adapters are tested with v1 byte goldens. This is not yet a
live evaluator result or a production-security claim.

## Work item 2 — successor A/C qualification

Status: committed and locally validated.

The successor binds evaluator-v2 source/tests, Moto/Babel tasks and images, runtime tuple, exact four-row schedule
and unchanged treatment: A null, C exact-three. Drift fails before provider execution.

## Work item 3 — reusable fast preflight

Status: implementation and local regression validation in progress.

Replace the V-per-attempt lifecycle with one supported command that:

- validates the qualified evaluator-v2 and A/C source identities;
- loads only `OPENAI_API_KEY` from an explicitly selected repository `.env` without rendering its value;
- performs bounded Docker/SDK no-call readiness checks;
- emits a sanitized in-memory attempt summary and retries only transient pre-provider failures, at most three times;
- emits one candidate execution hash when all non-cost gates pass.

Completed attempt summaries remain immutable. The command never performs a provider, evaluator or agent call.
Schema/semantics changes require a new version; ordinary attempts do not.

## Work item 4 — one campaign approval

Status: blocked on a READY fast preflight.

Refresh official pricing and bind the four-row reserve, `$55` hard cap, source commit, evaluator-v2 qualification,
schedule and execution hash. Ask once for paid execution of that exact campaign. The approval expires when any bound
field changes and does not authorize held-out, B/D or unrelated execution.

## Work item 5 — four-run A/C readiness

Status: blocked on work items 3-4.

Run Moto A, Moto C, Babel C and Babel A once in fresh workspaces. Each row must be terminal, trace-qualified,
cost-settled and receipt-qualified under evaluator v2 with consistent hidden/regression/scope/safety verdicts.

Campaign rows are single-attempt. Any infrastructure or outcome-bearing row failure makes the panel inconclusive.
If another readiness panel is needed, start a new four-row panel with the same frozen treatment and disclose both.

Output is descriptive workflow/direction/cost evidence, not a causal, held-out or transfer claim.

## Work item 6 — preregistered held-out A/C

Status: planned target only.

After valid readiness, freeze task identities, repetitions, metrics, exclusions, analysis and stop rules before
viewing held-out outcomes. The target is 12 tasks × A/C × at least two repetitions = at least 48 rows. Moto/Babel
results must not tune the fixed bundle or held-out policy.

## Work item 7 — B/D and the full comparison

Status: deferred.

- B/raw-trace needs portable source selection, redaction and equal-budget truncation.
- D/selective needs independent applicability labels and a frozen score/rerank/threshold policy.
- If designed after held-out A/C is unblinded, B/D use a separate fresh held-out panel.

No readiness or held-out A/C result automatically unlocks B, D or a full A/B/C/D campaign.
