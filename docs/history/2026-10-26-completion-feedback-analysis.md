# Completion-feedback analysis: request modes and lost correction drafts

Date: 2026-10-26. Follow-up to the immutable
[pilot result](2026-10-26-completion-feedback-live.md).

## Material Passport

- Origin: academic-research-suite / experiment-agent / validate.
- Verification: ANALYZED from sealed public requests, receipts and matching source.
- Scope: one exposed Astroid-1333 run; no provider or target rerun, no runtime edit.
- Runtime: `sha256:3a7fd37953ffeee6074c53f93ebc315ebe4a77673c9dc40b1645480c9082a1f0`.
- Evidence: `C:/pt/completion-feedback-analysis-v1/analysis.json`.
- Analysis hash: `sha256:aff79b3479cb162a21ad13dd40645c87eaf00c2838ec8d1c48427530e3c32853`.

## Why inspect these transitions

The pilot never applied its first edit despite unused total funds. Its terminal
alone could suggest that correction output was too small. The more discriminating
question is whether the host exposed executable request modes and preserved what
the model was supposed to correct. This matters before funding another solve or
attributing failure to the new downstream completion features.

The earlier record remains correct about the event sequence. This analysis adds
the actual provider request settings and the public contents of the correction
handoff. Model reasoning text, private tests and reference patches were not read.

## Findings

**Initial reproduction was recommended, but its bounded stage could end entirely
through inspection.** Calls 1-6 received needs_original_reproduction and an explicit
run_probe recommendation. Six reads/searches consumed the investigation-action
allowance with no target dispatch. Call 7 changed to needs_mutation. The original
obligation correctly remained unverified, but this was release of the acquisition
stage, not acquisition of a reproducible failing call. The run accumulated
33 inspections without an executable edit. This does not make every read wasteful;
six had zero new line coverage, a separate and incomplete information-value metric.

**The general probe schema offered a diagnosis option that this state could not
execute.** Call 23's actual schema allowed a non-null symbolic call_path and an
original_requirement purpose in one object. Its description said diagnosis was
conditional, but the schema did not exclude that combination. The host rejected
the emitted combination because no original-call diagnosis was pending. There
was no Python helper source and no target execution. The model then resumed
searching. In this configuration a pending diagnosis would instead replace the
general tool with the small focus-only schema; the legacy symbolic option remains
in the general fresh schema. This is a request-surface mismatch, not a target bug.

**The provider and host used different action-cardinality rules.** Calls 33 and
34 offered only replace_text and stop_task, while their exact prepared provider
requests retained parallel_tool_calls=true. The active small repair system prompt
did not explicitly state the host's reads-only batching/single-other-action rule.
Call 33 returned a source edit and a test edit together. The host rejected both
with INVALID_TOOL_BATCH before mutation. The explicit batch rule appeared in
call 34's correction. Enabling parallel calls does not prove why the model chose
two, but it left an avoidable mismatch with the host's admission rule.

**The correction lost the unexecuted drafts it asked the model to preserve.**
After call 33, an encrypted_item_bytes boundary created a new context segment.
Call 34 contained one system, two developer and one user item: no native function
call, function output or reasoning item. Its correction said to preserve valid
content and change only the invalid fields, with tool_contract_failure=null and
last_failed_mutation=null.

| Rejected draft | Old anchor in call 34 | Proposed new text in call 34 |
|---|---|---|
| astroid/builder.py: 1,516 old / 2,080 new characters | Present | Absent |
| tests/unittest_builder.py: 602 old / 1,043 new characters | Present | Absent |

These checks decode public message JSON recursively; they do not confuse escaped
JSON with missing text. Original source remained available. The missing material
was the newly authored replacement text and the rejected function calls. Only
replace_text/stop_task were offered, so the model had no history-read action to
retrieve those drafts. The journal retained them for audit but the next model
input did not.

The source matches the observed gap: batch rejection creates a correction from
the exception message without attaching the rejected calls. Fresh compact repair
segments project current state/evidence, while last_failed_mutation represents
an attempted action and is empty for a rejected batch. The handoff therefore lacks
an explicit carrier for an unexecuted proposal that still needs correction.

## Budget and causal limits

Call 33 used 30,833 of 40,000 output tokens and returned tools; it was not
truncated. Call 34 received the full 25,000 protected correction allowance, used
all of it as reasoning output, and returned no tool. The run stopped at 34 calls
and USD 0.843607950, leaving six model slots and USD 0.356392050 below the maxima.
The time limit was also not reached. Global budget exhaustion is contradicted by
the receipts; correction-output exhaustion is observed.

Loss of the drafts makes this a reconstruction task instead of a bounded
one-request resubmission. Its marginal contribution to the reasoning-only response
is not identified. The model may still need more output, or may still fail with
preserved drafts. Neither increasing the ceiling nor preserving the drafts has
been tested as a controlled intervention here. No proposed edit was applied or
verified, so their semantic correctness is also unknown.

Exception feedback, the post-observation reuse advisory and compact finalization
were never triggered. This run cannot establish their behavioral effectiveness.
The 8,192 finalization reserve was calculated, but no ready stage used it.

## Decision and next question

Prioritize the actual request/correction boundary: expose modes valid in the
current state; give an executable original request a bounded opportunity distinct
from ordinary source exploration; align mutation-only generation with single-action
admission; and carry rejected drafts through a segment boundary so correction can
select one proposal without regenerating its replacement body. Draft preservation
must not confer execution, verification or automatic mutation authority.

The smallest next local check should exercise this exact two-edit rejection and
segment rollover, verifying that one pending draft is reviewable and resubmittable
with the same current-source constraints. The open behavioral question is whether
that produces a useful model action; it still requires a separately scoped live
measurement. No runtime implementation or additional paid run was performed here.

Relevant source: original_obligation.py acquisition accounting; tools.py general
probe schema and batch validation; diagnosis_request.py state gate; runner.py
protocol correction, request preparation and segment construction; repair_context.py
public projection. Their hashes and sealed wire references are in analysis.json.

All 11 ARS fallacy types were screened for applicability in that evidence file.
There are no significance tests or population estimates. The relevant limitations
are exposed-task selection, post-hoc inspection and lack of a causal counterfactual;
the failure and unexecuted stages remain visible. Script assertions passed, the
original journal stayed byte-identical, and no generated state entered the repository.
