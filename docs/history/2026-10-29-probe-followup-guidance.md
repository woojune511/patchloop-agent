# Pre-edit helper observation and candidate replay guidance

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: local implementation and validation
- Origin Date: 2026-10-29
- Verification Status: locally tested; live model uptake NOT_RUN
- Version Label: probe_followup_guidance_v1

## Problem and decision

The [SQLFluff follow-up](2026-10-29-edit-prerequisite-single-results.md) executed
one helper before an edit, passed 506 registered tests and submitted. The
[operator replay](2026-10-29-sqlfluff-public-candidate-replay.md) subsequently found
the public example unchanged, and the [branch diagnosis](2026-10-29-sqlfluff-branch-diagnosis.md)
showed an accepted edit that produced the same intermediate result. The specific
verification gap was an observed public question left unchecked on the candidate.

Existing action-ID replay, unresolved notes and current-probe retention already
exist. Adding another tool, mandatory note or general warning would duplicate
them. Compact completion retains current probe details but omits historical bulk,
so a prior helper alone did not provide a persistent, actionable comparison with
the current candidate's check status. This is a transport/usability opportunity,
not proof that missing context caused the model's decision. An alternative is that
the model sees the gap and still prioritizes submission; only a live comparison
can distinguish that outcome.

The user authorized observation linkage and replay guidance. The change reuses
existing mechanisms and keeps the selected submission policy, tool admission,
resource forecasts and budget limits unchanged. No SQLFluff repair or answer hint
is added to the product.

## Implementation

`probe_followup.review()` derives a bounded card from durable public actions:

- Select the latest completed unbound helper preceding the latest accepted edit
  that produced the current diff. No helper or matching edit means no card.
- Preserve its question, action/input/program/diff identities and bounded raw
  observations. Each stdout/stderr preview keeps 1,000 characters and an omitted
  count; execution status, exit code, timeout/truncation/cleanup and environment
  identities remain distinct from behavioral correctness.
- A current result with the same question and program is recorded as observed or
  partial. Rejected requests and other questions/programs do not count as a new
  observation. A matching unfinished action is unresolved and receives no replay
  suggestion. An edit refreshes the candidate currency without resolving the task.
- Use the existing replay resolver to validate the selected reference and a
  matching current result's durable identity. Invalid current receipts remain
  unresolved; reference ineligibility does not erase the old observation. No output-preview equality,
  relevance, expected value or semantic pass/fail is inferred by the host.

`DevToolGateway.reproduction_review()` includes the card. Runner guidance qualifies
the replay route against offered tools and stage restrictions, retaining case-policy
differences in required arguments. The arguments are tool fields, not a substitute
for the existing turn/memory metadata required by the offered schema.
Small repair and diagnosis contexts retain only this additional review card;
ordinary, thin and completion contexts preserve it through their existing paths.

The probe description now distinguishes repeating a relevant example after an edit
from exploring a new input for a new question. This replaces the unqualified
instruction favoring input variations, which could be read as discouraging useful
repetition. It does not force either choice. The card suggests reconsidering branch
execution, intermediate changes and later transformations if unchanged behavior
refutes a repair hypothesis; it names no task-specific rule or solution.

No journal schema, automatic target execution, check registration, mutation limit,
cost/time reserve or finish rule changes. The card is a derived public view, rebuilt
on recovery. Registered public checks and independent acceptance retain their
previous meanings.

## Local evidence and remaining question

Focused controls cover helper-to-edit linkage, current/partial/unresolved outcomes,
rejected/different requests, clipped output, invalid references, stage restrictions,
and all three probe policies under ordinary/thin schemas. The gateway test executes
a local fixture helper, edits, manually replays it and restores the gateway; repeated
action recovery performs no duplicate execution. Public-check and saved-case credit
remain absent. Model-wire controls preserve the card through ordinary, thin, repair,
diagnosis and completion projections and JSON assembly.

The saved SQLFluff journal was also projected without rerunning its target or model.
Its actual helper action was retained with nine-space output, current-candidate
`not_run`, and a valid replay reference. This checks compatibility with real public
receipts, not model behavior or a new benchmark result. The prior journal was
unchanged. The supplied stage for this projection was the prior general completion
stage; it did not claim to rerun provider admission.

Evidence root: `C:/pt/probe-followup-local-v1/`. The saved-receipt projection is
recorded in hash-chained `runs/run_dev_probefollowuplocalv1.jsonl`; its script is
`audit_saved_observation.py`. Validation receipts are separate XML files there.
Focused suite: 51 passed in 27.26 seconds (`focused.xml`), including existing manual
replay recovery controls. Review added current-receipt identity checks, and the
focused projection/description rerun passed 40 tests in 4.80 seconds (`review.xml`).
Final fast suite: 923 passed in 124.22 seconds (`quick-final.xml`, four workers),
including isolated mock evaluation. Ruff and `git diff --check` passed. The first
fast run found eight stale description-hash expectations; these were updated,
with additional tests verifying that restoring only the old description restores
the old complete schema hashes. Argument schemas and other tool descriptions
remain unchanged. The full suite and Linux CI were not run.

No paid invocation, Docker target execution, hidden evaluator or reference patch
was used. Historical evidence remains unchanged. The next question is whether
retaining this link changes the model's replay/diagnosis/repair choices under the
same budget. Local tests do not establish a repair-rate gain or justify a default
submission-policy change.
