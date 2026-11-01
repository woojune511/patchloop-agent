# Selected-file pages and a saved-candidate feedback comparison

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation and local validation, followed by authorized run
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY TESTED; live result recorded separately
- Version Label: feedback-source-implementation-v1

The user requested implementation and execution of the
[follow-up design](2026-10-27-feedback-source-plan.md). This accepts that exact
Astroid-1333 dev-train task, mini snapshot/xhigh, repository `.env`, one R0/R1 pair
and $2.40 invocation cap. The executable is sealed after local validation. All
previous paid allocations remain closed; this is the new pair's scope only.

## Problem and implementation

A five-line search excerpt omitted the prefix construction immediately before A's
edit, and the diagnostic's remaining-action policy removed further reads. The whole
saved file fits 24,000 characters but exceeds 400 lines. This justified simplifying
selected-file acquisition while measuring source delivery separately from the tool
interface and action horizon.

`read_file` now accepts absent/null bounds for a whole-file or first-page read.
An integer start and null end continues at a returned `next_start_line`. It returns
complete consecutive lines up to the existing 24,000-character bound. Explicit
integer ranges retain the old 400-line behavior and result format. Empty files,
oversized single lines, source hashes, tracked-public-path restrictions and only
delivered-line edit anchors remain explicit. Completed action_id/input_hash replay
does not dispatch a new read. The tool-surface fingerprint identifies the changed
contract; current schema pins changed while frozen historical-arm pins did not.

No search expansion, forced whole-file gate, extra hypothesis declaration, context
increase or production action-budget change was added. Reading a file once still
does not guarantee its retention across a production context handoff.

`diagnostics/feedback_source_packet.py` reads the frozen A model/public journals,
13 public receipts and bound source. It projects the original issue/caller,
full saved diff, authored-unverified previous hypothesis, public before/after
observations, scoped changed-line facts and regression output. Operator solutions,
old B, acceptance data and cached causal judgments are excluded. R0 gets current
lines 265-273, R1 lines 1-400 and 401-676. The common diff preserves its existing
`modpath.append(part)` line. Model inputs are identical outside current source.

`diagnostics/feedback_source.py` adds offline prepare/validate and single-use
collection. Both rows reconstruct the same saved A on the immutable task base.
Imported source is not a model mutation; only actually delivered ranges register
as anchors. One/two host preload reads are accounted separately from 12 model
actions. Both model schemas and backend validation use `read_range_only=True`,
preserving the old explicit-range interface for this comparison. Thus this live
pair measures complete-source preloading, not model uptake of the new read API.

The first additional accepted edit closes each model row. Reused public checks
compare against a fresh clean base, not the failed seed. Public semantic failures
remain reportable even when regression passes; isolated acceptance runs at most
once under the existing regression eligibility rule. Private outcomes never return
to the model. Count/transport/billing/cleanup/identity uncertainty stops the pair.

## Local verification and corrected preparation defect

- Whole/page reading and related existing checks: 45 PASS in 4.99 seconds.
- New continuation operator: 15 PASS in 6.215 seconds, including partial-anchor
  refusal, complete-anchor admission, seed mutation count zero, one new edit,
  pair equality, persistent source and stop/verification boundaries.
- Public packet projection: 4 PASS; deliberate operator/private sentinel fields
  are not projected, public receipt store/hash/size and source coverage are checked.
- Ruff passed for the implementation and focused tests.
- The fast suite initially exposed intentional current schema/fingerprint pin
  changes and the guide byte budget; these were corrected before final validation.
  Final fast suite: 472 PASS in 104.09 seconds, including isolated mock evaluation.
  Pytest emitted one cache-write permission warning; tests completed successfully.
  Exact current snapshot/whole-read/docs selection: 40 PASS in 3.40 seconds.
- A broader file-level selection also encountered 21 failures in older fixture
  and annotation paths outside the prescribed quick selection. Those paths were
  not repaired or established as passing; no full-suite PASS is claimed.

The first real restoration preflight found a Windows Git boundary: global autocrlf
changed the saved LF postimage to CRLF while leaving its canonical diff identical.
The raw source hash correctly rejected that state. Set `core.autocrlf=false` only
inside each newly owned restoration workspace before applying the saved patch,
then verify exact file and diff hashes again. No source artifact was rewritten.
`C:/pt/feedback-source-preflight-v1` preserves the failed zero-provider attempt;
v2 passed both actual workspace restorations, exact R0/R1 span registration and
zero model-mutation counts. Neither preflight read credentials or executed targets.

## Execution boundary

Fixed proposal: gpt-5.4-mini-2026-03-17, xhigh; R0 then R1 once each; $1.20 per row,
$2.40 total; eight normal and one protocol correction, 12 model actions, one probe,
one additional edit; 40K/25K output, 60K counted input; 600 seconds of model work
after source registration, 390 public-check seconds and 390 isolated-evaluation
seconds. Workspace/image/source registration has a separately bounded setup deadline.
These maxima are not a guarantee that every maximum-output response is affordable.

The full source packet is initially supplied by the host and kept in each request.
This is an assisted saved-candidate comparison of source content, acquisition cost
and observed anchor availability. It is not a fresh solve, general success-rate
estimate, isolated feedback effect, or unrestricted-shell comparison. Acceptance,
public mechanism checks, regression, scope and safety remain separate outcomes.
