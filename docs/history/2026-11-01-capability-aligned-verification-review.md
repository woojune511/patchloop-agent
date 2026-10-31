# Capability-aligned verification decisions

Date: 2026-11-01. Status: implementation and local validation; new live work NOT_RUN.
Baseline: `0ff6402aee11d8e32ab17366b9224e6e0b8cde42`.
Evidence: [two-probe diagnostic](2026-11-01-two-probe-recovery-results.md).

## Problem and why it matters

The last task8 diagnostic successfully expanded from write_dataset to six save_as
helper cases, then reported no counterexample. It named regression coverage as the
largest remaining uncertainty, but justified stopping by saying another check was
unnecessary to state that no counterexample was found. A truthful limited outcome
does not itself decide whether another observation is useful. There were still
three model calls, one probe and474 seconds at the reporting request.

That is not evidence that all skipped work was executable or mandatory:

- The public example omits indexData, construction of lineSeq, its link to ds and
  serialization settings. Exact reproduction of that unknown setup is impossible.
- Known H-array -> bytes construction could be preserved in an assumption-labeled
  helper; the actual I-array/flat Dataset helper changed those conditions.
- Unchanged-base reproduction was outside this fixed-candidate diagnostic's scope.
- The registered base-regression check was public, but run_check was not offered.
  Its separate testbed interpreter/subprocess wrapper is not a Python probe. The
  prepared probe includes the public test files but no pytest distribution, and
  blocks fork/exec/subprocess. Direct Python assertions can provide narrower
  observations; they do not establish that the registered suite ran or passed.

The investigation found concrete request mismatches in addition to the model's
weak stopping rationale. Current diagnostic state retained needs_visible_checks,
remaining_visible_check_ids and the repair_recheck instruction that other checks
require run_check. An original user continuation still requested edits/checks/
submission. Reproduction state also retained historical replay/acquisition controls.
Actual tools were only read/search/probe/report. Finally, the saved-state report
annotation was copied from read_file, forcing inspect mode and an inspection goal
for a terminal report. The recorded report used exactly that shape.

These mismatches plausibly contribute to choosing an unavailable check and treating
termination as evidence narration, but causality is not established. The normal
dev runner already has its own visible-check admission and submission contract;
the diagnostic failure cannot be generalized to a broken normal check gate.

## Minimal change

Use one diagnostic request projector at initial preparation and subsequent request
construction. Align current workflow and continuation with the actual fixed-review
tools; remove inherited execution directions and historical capability/budget
claims from the current control view. Keep the public task, NOT_RUN check facts,
source/program/result bodies, relevant original-verification facts and saved
checkpoint immutable. Historical evidence remains evidence, not current permission.

When report_discovery already has an optional turn_decision annotation, align it
with finish mode and null evidence_goal. Keep null/immediate reporting available;
do not add an annotation to the fresh seven-field report contract. Freeze the
projected request before execution and reject an unprojected seed before dispatch
instead of silently sending different input from the prepared identity.

For general verification choices, clarify the existing basis and scope-review
input/interpretation descriptions: retain known original conditions, label missing
or substituted setup, name the observation that could change the decision, and
connect it to a currently offered action/environment. A terminal choice explains
why no useful feasible observation remains; narrowing the reported claim alone
does not justify ending. This reuses existing fields and limits rather than adding
a new review step or prompt paragraph.

No new check backend, dependency installation, mandatory probe, semantic acceptance
gate, unrestricted command or budget increase. Do not fabricate missing original
setup, require every untested case, or treat unused resources as a reason to test.
The host still cannot certify the model's relevance judgment. Genuine evidence
sufficiency, irrelevant alternatives and concrete execution blockers permit stop.

## Validation and limits

Local checks must cover immutable/idempotent projection, initial frozen request
matching dispatch, refreshed state not reviving old capabilities, and report
annotation alignment. Preserve raw public observations while removing conflicting
workflow directions. Exercise selected additional probe -> actual gateway dispatch
-> result delivered to the next request -> report, plus immediate/blocked reporting
and unavailable-tool rejection. Setup failure is not candidate failure evidence.

Scripted model turns test host delivery and execution paths, not autonomous model
selection. A read-only projection audit of the saved public request checks that
the observed mismatch is actually removed. No provider call, new task execution,
private evaluation or claim-producing comparison is part of this change.
The unchanged production implementation passed the normal focused batch (57 tests,
16.478s). The diagnostic batch initially had 15 passes and one bad test assertion:
it looked for raw output.status in the model-facing view. That view deliberately
uses observation.execution_status=failed and behavior_verdict=not_assessed, while
the raw evidence retains output.status=failed. Correcting that assertion passed
in 7.457s; no production fix was needed for it.

The quick suite, including isolated mock evaluation, initially recorded 1,432
passes, 13 failures and one Windows symlink skip in 325.284s. Twelve failures were
current schema/contract fingerprints affected by the intended descriptions; the
thirteenth was the assertion above. Initial failure XML files are retained.
Separate HEAD/current schema generation verifies that only basis.description and
scope-review input/interpretation descriptions changed. Ordered argument shapes,
types, limits and unrelated policy surfaces are preserved. Current fingerprints
are refreshed, with historical thin/path-diagnosis fingerprints left intact.
The affected schema tests and added ordered-shape regression then passed: 20
tests in 1.094s. Together with the corrected diagnostic assertion, this resolves
all 13 initial quick failures. Production code stayed unchanged; the entire quick
suite was not rerun after these test-only corrections. The extra shape regression
is included through its existing quick-suite file selection.
Documentation checks: 6 PASS. Ruff and git diff whitespace checks: PASS. Each
focused batch stayed below two minutes. No worker crash or unresolved local
failure remains; the Windows symlink capability skip remains explicit.

Read-only audit PASS on three actual saved public requests: prepared request,
first dispatch and pre-report request. Projection is idempotent; original bytes,
public task/source/program/result bodies, NOT_RUN facts and current resources are
unchanged. Only recognized current control fields and the existing report
annotation are transformed. This audit uses saved descriptions and does not test
the effect of newly written guidance.

Evidence root: `C:/pt/capability-review-local-20261101-v1/`. Initial and corrective
XML, schema-comparison proof, audit and final source bindings are retained there
and bound by the append-only `run_dev_capabilityreviewlocal` journal.
Runtime content: `sha256:876d3b26215e17c1bb4123c2adfb499bd6290fefaf47fe25bf8465a9abc4771e`.
Audit: `audit/public-projection-audit.json`,
`sha256:d0072f34135fd3dc3fd898bcb3b87c31d5ceaf58bb14529b3f1f022fe90ed2b6`.
Schema proof: `schema-proof/proof.json`,
`sha256:cdc3ade935799f60149ebd314e4d2bc24f330a6d838305d9994cf293bc97148d`.

This selects a capability-delivery correction and clearer existing decision
fields, not more mandatory checks or larger budgets. No claim is made that the
model will now choose a useful observation autonomously. That remains a live
question: does it retain known original conditions, select and execute a feasible
discriminating observation, or give a concrete sufficiency/blocker rationale?
The prior paid allocation remains closed; no new provider or benchmark execution
was performed.
