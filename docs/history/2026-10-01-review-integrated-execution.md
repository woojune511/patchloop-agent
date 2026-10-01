# Reviewer response and sandbox integration

## Defects found and change

The scripted reviewer passed the entire generation request to token counting and
discarded reasoning continuation between calls. The finite fake SDK tolerated both;
that did not establish real SDK compatibility. Reused OpenAIResponsesAdapter for the
count payload and response/usage validation, instead of building another parser.

The reviewer retains encrypted reasoning items, then all function calls in returned
order, followed by their tool outputs. Plaintext reasoning/summary is not persisted.
Usage uncertainty, incomplete output, missing continuation, duplicate call IDs and
model mismatch stop before tool execution. Known usage is settled even when the
response's continuation or protocol is invalid; uncertain usage stays unresolved.
Reviewer count/create calls receive the remaining deadline.

This follows the stateless function-calling guidance in the
[official Responses documentation](https://developers.openai.com/api/docs/guides/reasoning).
The intended model remains gpt-5.4-2026-03-05; no provider availability claim is made.

## Integrated execution boundary

diagnostics/review_integrated_execution.py uses finite ScriptedClient responses but
the actual source/image/dependency admission, registered Docker probe executor and
isolated evaluator. It blocks provider socket connections and replaces credential
loading with a dummy; it does not patch the real Docker preflight or evaluator.
It requires an explicit current-runtime fork and cannot retry an existing branch.

Inherited probe receipts remain auditable but are excluded from current submission
probe evidence. A checked lineage event records historical/current receipt sets.
Submission uses the current executing Git identity instead of inheriting the parent's
Git identity. Existing local-only rehearsal behavior and ordinary runtime code are
unchanged. The manifest builder now also binds this new adapter's source hash.

## Evidence scope

Provider-free driver: C:/pt/review_integrated_rehearsal_20261001.py.
Root: C:/pt/analyses/review-integrated-rehearsal-20261001-v1.
The fixed sequence is reviewer probe, report, repair probe, finish, once for each
saved candidate in arm B. Probe source only prints a wiring marker. No patch is
changed, and no model judgment or new solve is being measured. Source packages,
including original pyinfra v1, are used; the planned separate v2 score is not replaced.

All four sequences completed with first-state restoration verified and one new
repair probe receipt packaged per submission. Acceptance was FAIL for OpenSandbox,
isort and original pyinfra v1, and PASS for Conan. Docker safety was PASS for all
four. These reproduce the original saved-patch verdicts; they are not four fresh
agent solves. The driver verified original source-journal hashes unchanged and
recorded integration_finished. No provider calls or image acquisition occurred.

Forty-four focused tests passed: 28 review integration tests and 16 offline/scoring/
lineage tests. Five documentation tests also passed. Tests include encrypted
parallel-call ordering, count payload filtering,
malformed response failures before tool execution, and exclusion of historical
receipts. Ruff and whitespace checks passed. Mock smoke run_dev_f914d3c15fab42d3
reached EVALUATOR_PASS with safety_state=NOT_RUN at
C:/pt/analyses/review-integrated-mock-20261001-v1. Full repository CI was not run.

## Remaining admission

This is a provider-free integrated execution path, not a paid collector. A
manifest-bound authorized entry point and post-submission scoring integration,
including pyinfra v2's separate result, remain before requesting paid execution.
The preceding preparation manifest remains immutable but its implementation hashes
are superseded by this change; it cannot authorize the new code. No paid allocation
has been opened, and no quality-improvement conclusion follows from these rehearsals.
