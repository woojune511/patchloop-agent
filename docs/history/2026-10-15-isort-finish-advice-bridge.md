# isort I4: finish-advice removal execution bridge

Completed: 2026-10-16; started 2026-10-15. Inert transport, official=false.
Paid execution is not authorized. The
[frozen design](2026-10-15-isort-finish-advice-design.md), its external packet,
closed I1/I2/I3 records and default runtime remain unchanged. No credential,
provider metadata, input-count API or generation API was accessed. No isort
diagnostic, registered check or evaluator was executed.

## Implementation and preserved conditions

The separate `diagnostics/isort_finish_checkpoint.py`, `isort_finish_execution.py`,
`isort_finish_review.py` and `isort_finish_collection.py` implement I4. Existing
I1/I2/I3 files remain byte-identical. The same cost ledger, registered tool
admission, automatic repair recheck, terminal oracle, isolated evaluator and
provider-free guards are reused. I3's observation-retention function and C/R
algorithm are reused directly. No default runtime policy or new solver gate.

Before counting each request, the bridge assembles the ordinary I3-retention
input, then changes only the newest ready-state `completion_guidance.message`
and `next_action`. The latter becomes null; the finish recommendation clause is
deleted exactly as frozen. Both existing ready-message forms are supported;
suffixes, including informational references to `finish_task`, remain intact.
Unknown ready advice stops before another count or dispatch. Non-ready states
and all mutation/check/source advice remain unchanged.

`stage`, submission eligibility, tools and `finish_task` availability remain
unchanged, as do system completion instructions, the original plan and normal
model-authored updates, historical/native items and their order. No alternative
recommendation, edit/probe requirement, review prompt or repair hint is added.
The first full request must match the frozen I4 preview after normalizing only
displayed remaining seconds. Real deadlines are preserved.

Each assembly stores ordinary, retained and delivered inputs. Removing the
operator field recovers the ordinary input; restoring only the two advice
fields recovers the entire retained input. Exact count and dispatch verify
these identities and the current workspace diff. Each dispatch binds the
request, packet, candidate, segment, observation placement and advice stage.

The complete diagnostic remains current only on its exact observed seed.
After edits it becomes historical together with the full observed seed patch;
ordinary `current_diff` stays current. Exact return restores the current form.
There is no new truncation, summary, handoff rule or operator-to-check promotion.

## Pre-assessment review and outcome boundaries

The public review includes A/D delivery evidence and the first public decision's
executed batch, then applies the unchanged semantic U and C/R definitions.
Actual unchanged submission is distinct from continued inspection/edit/check,
stop without submission and unobservable or censored action. A changed first
action alone never earns repair success. A/D are supported by matching counts,
provider dispatch records and exact input parity, not a prepared preview alone.

The callback/file exchange seals A/D/first-response, U, and C/R before the
terminal public oracle and isolated evaluation. Invalid semantic citations or
probe classifications block all seals and both assessments. U PASS requires
public explanation linked to an accepted new non-noop source edit; conditional
qualification and a plan-update explanation can satisfy the frozen semantic
rubric. A correct patch alone remains insufficient evidence of uptake.

No qualifying later handoff gives C NOT_EXERCISED. Zero same-case probes without
an edit gives R NOT_OBSERVABLE. Configuration changes remain counted under the
same-case rule; strict identical replay is separate. C/R remain secondary for
I4's new primary A/D/U/P/I/safety target, while the old I3 conjunction stays
separate. The old I3 grades and I2 uncertainty-censored grade are not changed.

Unknown transport/billing or input integrity closes without retrospective
grading, retries or replacement samples. Review and assessments share the
720-second deadline. Only actual submission permits one public oracle and one
isolated evaluation; normal public behavior failure may still be evaluated,
while infrastructure uncertainty stops it. No verdict returns to the solver.

## Free validation

The focused suite passed **113 tests in 84.83 seconds** with four workers. It
uses finite SDK doubles and local fixtures; network connections are forbidden
in the execution fixtures and funded-entry tests use inert key/metadata doubles.
Coverage includes:

- Both exact advice forms, suffix preservation, non-ready identity, historical
  inputs and tools; rejection of unknown advice, double application and changes
  outside the treatment before count/dispatch.
- Whole first-input parity; complete diagnostic after a real segment boundary
  and within a segment; historical observation after edits; exact-seed return.
- A local fixture completing two edits, checks and submission, with all public
  seals before both assessments; repair after a failed check and its automatic
  recheck; conditional U linkage, invalid U/R citations and no-handoff/no-edit
  outcomes.
- An immediate unchanged finish remains permitted and is classified correctly:
  scripted U FAIL, public repair FAIL, C NOT_EXERCISED, R NOT_OBSERVABLE. This
  fixture also verifies that the same row cannot be retried or resumed.
- USD 3.50 and full-output reservation; exact single-use count/dispatch binding;
  six generation/count ceilings including the sixth matching dispatch; two-edit
  ceiling that still allows check/finish; individual parallel-tool counting and
  the existing completion reserve.
- Solver, preparation, review, phase and whole-invocation time; late usage
  settlement without late actions; first/later input overflow without pruning;
  count/transport/usage/cleanup/setup uncertainty and no correction call.
- Manifest/hash/scope/price/treatment/readiness rejection before credentials,
  one metadata attempt under inert doubles, and exclusion of private verdicts
  from the automatic collection summary.

The real-checkpoint free rehearsal is `C:/pt/isortfinishbridge01/result.json`.
It restores the original prefix through event 338 and supplies scripted read
and stop responses: two simulated generations/counts, two actions, no edit.
The new collection journal is `runs/run_dev_isortfinishbridge.jsonl`; its I4 row
uses the inherited `run_dev_49397fa9568d4b80` identifier inside a fresh directory.

The first displayed remaining time was 278 s versus the preview's 270 s. Its
normalized request hash is
`sha256:bb0fe4cf4f149f7919622766512d2e27d9fe90facf9ff36769c838b1c7aff19a`.
Undoing the advice treatment also recovers the full I3 first input after that
same clock normalization. The second input retains the complete packet after
the normal handoff. Synthetic A/C are PASS; U/R are NOT_OBSERVABLE. D, model
uptake, advice/retention effects and actual isort acceptance remain NOT_RUN.
Provisional mock accounting of USD 0.001100 is not a provider charge; billed
cost and actual provider calls are zero.

The saved-input audit is `C:/pt/isortfinishchecks01/rehearsal-audit.json`, hash
`sha256:6ca6bc4302081220158934656296b6b77267989c3de87a54267748c4c47ea7b9`.
It verifies both dispatched inputs and the handoff, with A/D, U and C/R seals
at row events 380/381/382. No target check, submission or evaluator occurs in
that read/stop rehearsal. The separate fixture tests exercise the repair path.

The ordinary CSV mock smoke at `C:/pt/isortfinishsmoke01`, run
`run_dev_6d713e5f33f54703`, reached local isolated `EVALUATOR_PASS`: four mock
turns, five actions, one edit, zero cost. Its safety state is NOT_RUN. This is
not an isort repair result. Ruff passed across runtime, diagnostics and tests.
The complete suite passed **5,028 tests, 19 skipped in 1,600.40 seconds**;
the focused suite remains under two minutes. Five documentation layout/link
tests passed in 0.16 s. Reports and the rehearsal are bound in
`C:/pt/isortfinishchecks01/validation.json`, hash
`sha256:8e9baf6d5a1e3935eea421b84ff6831f82a7184e0863d4c3c472ddeb0049afdc`,
and its append-only validation journal. No source changed during validation.

## Frozen execution preparation

Design hash remains
`sha256:9bab428334bcbec950e1013f754950f5ea1b01f92c3aa174d1660e42175f8250`.
Runtime hash remains
`sha256:b3c8e80c0656fb4954eebcb5d30de411d4b0fa687a150ef3308883487bb08208`.
Diagnostic implementation hash:
`sha256:4fd1a84bbf0a3e60f98eca3958192036d82a3ed506f422f536b237d2b8fc0704`.
The user's existing AGENTS.md change is preserved separately.

Preparation creates `C:/pt/isortfinishready01/manifest.json` after committing
the connector and binding free validation. It fixes I4 once, the exact
`original-isort-2491` dev-train checkpoint, `gpt-5.4-2026-03-05`/xhigh/default,
the existing repository `.env` path, USD 3.50, six generations/counts,
18 tools, two edits, 60,000 input/25,000 output tokens, 281 s solver/720 s total,
one 30 s public oracle and one 330 s isolated evaluation. All other caps remain
unchanged. It binds the committed implementation, source, fixed design,
treatment, retention, grading, cap application, first-input parity and rehearsal.

The future live output is `C:/pt/isortfinishlive01` and must remain absent until
separately approved execution. The collection CLI only prepares a manifest.
The funded entry point requires the exact approved manifest hash and positive
USD 3.50 cap, fresh official price review, read-only environment readiness and
at most one exact-model metadata read. Preparation performs none of these live
calls. No automatic Docker startup, image pull/build, retry, resume, wording
change or follow-up is permitted. The manifest keeps paid_authorized=false;
implementation approval is not paid-execution approval.

This establishes connector behavior with controlled fixtures, not model uptake,
an accepted isort repair, causal effect or performance gain. Keep the baseline.
