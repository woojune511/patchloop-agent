# Goal-grounded diagnostic stopping

Date: 2026-11-01. Status: implementation and local preparation; new paid run NOT_RUN.
Baseline: `9fb7055d7a6b8754deb837b4cd81c55ec0fdd4c9`.

## Problem and decision

The [last task8 diagnostic](2026-11-01-task8-expanded-budget-results.md) constructed,
executed and interpreted a new nine-case helper successfully. It then reported no
counterexample while retaining the original caller and other writer paths as
untested. Its public action basis treated completion of its own helper plan as the
reason to report. It did not explain whether the remaining original-caller gap
could change the public-task conclusion, or why an additional allowed observation
was not useful or feasible.

That is an unresolved stopping/scope-selection question, not proof of an agent
capability failure or premature normal submission. The diagnostic allowed a report
with limitations and did not offer normal checks or submission. The normal solver
has separate visible-check and delivery contracts. Resources remaining at the
decision do not guarantee that another model response, probe and final report
could fit; response times are uncertain.

Existing working-plan instructions already say that listing unknowns does not
justify stopping. They also preserve unresolved verification purposes. The model
did preserve these gaps rather than falsely claiming them closed. Adding the same
warning again would not distinguish the missing decision from honest disclosure.

Change the diagnostic terminal's existing justification semantics: ending is
assessed against the original public task and authorized review objective, not
merely against a self-selected helper plan. The intended observation is either a
material additional action or an evidence-grounded decision to stop. More probes
by themselves are not the objective.

## Minimal implementation

Only two descriptions in `diagnostics/counterexample_discovery.py:report_schema`
change: the `report_discovery` tool description and its already-required
`justification` field description. The justification must still ground the reported
expected/observed conclusion in public evidence. It now also asks for:

1. The most consequential remaining uncertainty and the smallest allowed
   observation that could change the conclusion, or why evidence already settles
   the authorized review objective.
2. Why further investigation is not useful or feasible, using current evidence or
   concrete input, tool, time or cost constraints.
3. Scope judged against the public task and authorized review, rather than merely
   against the model's chosen helper or plan. Listing a limitation alone is not a
   stopping reason.

The tool remains callable without a new probe. Its seven fields, types, nullability,
outcomes, 2,000-character justification limit, parser and execution availability are
unchanged. No semantic acceptance gate, required probe, new reasoning transcript,
field, budget or normal-solver prompt/finish rule is added. The supplied statement
is a concise public action rationale; its truth is not automatically certified.

The normal runtime hash remains
`sha256:4fdcc4fb9eb3d71ad81a5d929a0af689cecd876fbd39c212204d0c6343b608c7`.
Diagnostic implementation/request identities change and will be bound to the new
preparation. Closed plans and outcomes are not rewritten or silently upgraded.

## Prepared diagnostic question

Use the saved public request immediately after the executed task8 helper, before
the final reporting decision: source run `run_dev_62da82f8f7e34345`, input-count
start sequence 38, fixed candidate be082f27. Do not expose the actual later response
or report to the model. Keep the existing `probe_result` review active; do not
re-trigger the already-consumed `behavior_change` review.

Proposed fresh scope mirrors the resources displayed at that original decision:
dev-train8/pydicom1413, gpt-5.4-2026-03-05/xhigh, credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, one attempt, **USD1.5431895** new cap,
four model calls, ten actions including report, one new probe, 265 seconds,
60,000 input tokens and full 25,000-output reservation or stop. No patch mutation,
normal check, submission or independent evaluation. Count/transport/billing/recovery
uncertainty stops new calls without retry. Four maximum calls are not guaranteed
by that cost/time allocation. The numerical cap equals the old remaining balance;
it is a new allocation, not permission to reuse a closed one.

New preparation: `C:/pt/stop-review-20261101-v1/`.
Proposed result: `C:/pt/stop-review-run-20261101-v1/`, which must remain absent
until a fresh exact-scope authorization. Preparation and local mocks add no
provider count/generation, target execution or independent evaluation.

Public native calls/results are carried as historical evidence with their exact
identities and source-prefix binding. Opaque reasoning continuation is omitted
without inspection or decryption. Earlier current-diff probe results can support
references without being counted or executed again; no old gateway cache, check,
mutation or cost authority is imported. This is a reconstructed public diagnostic,
not exact continuation or a controlled causal estimate from the previous response.

## Evaluation and limits

Evaluate the actual decision and evidence, separately from the report's wording:

- A new action is useful only if it addresses a public-goal gap that could change
  the conclusion, preserves relevant input/caller/outcome conditions and actually
  executes. A repeated supported case or irrelevant broader search is not progress.
- A stop is justified by evidence that settles the review objective, a defensible
  lack of materiality, or a concrete applicability/resource constraint. A missing
  required public fixture may be such a constraint; a self-chosen helper boundary
  alone is not.
- A report may still have an unsupported rationale. The host continues to record
  it without certifying semantic sufficiency; operator public review can classify
  that termination as unsupported. Unknown applicability is not a demonstrated
  candidate defect. Exhaustive coverage and a mandatory second probe are not goals.

If the model merely restates limitations, this change has not established better
stopping. If it takes a grounded action or provides an adequate stop reason, that
supports this decision at this public checkpoint only. It does not establish a
normal-repair gain, causation across all combined context changes, or generalization.

## Local validation and prepared bindings

Repository validation is stored under `C:/pt/stop-review-local-20261101-v1/`:

- Focused: 27 PASS in 27.472 seconds. This covers exact description delivery,
  frozen request identity, unchanged fields/outcomes and reporting without a probe.
  The initial run exposed 16 stale warning-text expectations; the probe description
  was already identical before this change. Only that obsolete assertion was
  corrected, preserving all evidence/identity checks and the initial failure XML.
- Quick: 1,437 PASS, one platform symlink skip in 485.301 seconds, including
  isolated mock evaluation. No separate smoke repeat was needed.
- Ruff and `git diff --check`: PASS.

External preparation tests finished with all 30 distinct cases passing. The new
ten-case focus took 49.60 seconds. The broader inherited boundary sweep took
132.52 seconds (19 PASS, one stale timeout expectation); after correcting only
that test expectation from 350,000 to 190,000 milliseconds, the single case passed
in 9.38 seconds. The initial failure is retained, and the 19 passing cases were
not repeated. This broader sweep exceeded the two-minute focus target; both the
new focused set and the correction remained under it. No driver/request changed
for the correction. The immutable receipt is
`C:/pt/stop-review-20261101-v1/local-validation.json`,
`sha256:cf3c7ab6407495922faf1b462298061e131422b67b3701533d1c7159522efcd1`,
bound in CAS and `run_dev_stopreviewvalidation`. It covers a grounded new probe,
immediate reporting using saved evidence, rejection of stale/unbound evidence,
fresh accounting, action/probe limits and uncertainty stopping.

The prepared checkpoint is
`sha256:0c21b8823ec1edf221c9b0114baa8dea743a00905a08da5d7dd33b3ffe339fd6`;
the new request is
`sha256:a8a7bba7c100251ffdf539eb160b8792763ecd0308c5a2dc9512029b985199a5`.
The offline old-description request is
`sha256:3ef5ff6f48326c5f426b1b6f0ab92335f4b1ad8b54a2e62e55b4fce6c8436d07`.
Their public input matches at
`sha256:133e3877e11fbeb91333ec669396fa27923a9b5395fab1506fd8ec089ca257c8`;
only the two intended report descriptions differ. This structural comparison has
no model outcome and does not establish a causal benefit.

The source counted request is
`sha256:91efd2f08225a78f5810f2499acab1e88a2e7cb23b380ec2be6a6a4b05d22d98`.
Its public projection preserves seven messages and four native call/result items
as historical evidence. Two opaque reasoning continuation items are excluded by
type. The combined read-only evidence prefix contains 45 public events (38 from
the original checkpoint and seven local events), without the later response or
report. This keeps earlier completed probe references usable while all new run
usage, gateway actions and execution authority start fresh.
