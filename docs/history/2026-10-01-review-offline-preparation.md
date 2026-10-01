# Review pilot offline preparation

## Implemented and observed

Added an operator-only module, diagnostics/review_context_offline.py. It has no
provider client, credential loading, Docker startup or live collector. It checks
source journal/envelope/public identities, selects the pre-finish prepared input,
rejects uncertain or post-submission prefixes, verifies the candidate-bound public
PASS, and recursively copies hash-verified referenced artifacts into fresh stores.
Accepted mutations are applied in sequence with preimage/postimage/diff checks;
rejected mutations are not replayed. The ordinary workspace recovery validator
checks the materialized candidate. No historical action/check was re-executed.

| Case | Accepted historical edits restored | Verified referenced artifacts |
| --- | ---: | ---: |
| OpenSandbox | 1 | 41 |
| Isort | 2 | 99 |
| Pyinfra | 2 | 42 |
| Conan | 2 | 43 |

All final diff hashes equal the inspected saved candidates. Original journals,
artifacts and task packages remain unchanged. Each restored store records a fork
and preparation event; it does not record a new solve or evaluation.

The first Conan attempt stopped before output creation because the source runtime
hash differs. Inspection of source commit 24f6562 through main fcd89cc1 found only
repository allow-list additions and prepared-probe dependency metadata changes
within patchloop. Added an explicit offline-only materialization mapping for the
exact old/new runtime hashes and Conan task identity. The original envelope remains
unchanged. This does not bypass the ordinary runner's resume guard, prove native
continuation equivalence or authorize a live migration. The initial blocked result
and subsequent successful materialization are separate evidence.

## Projection, advice and resources

A/B draft requests use the same review instruction, public task, candidate diff,
current-candidate public receipt fields and registered read/search/probe schemas.
A retains trajectory input; B omits prior rationale, plans and encrypted reasoning.
Neither receives private results, role/outcome labels or later operator diagnostics.
These are draft provider requests, not evidence of provider acceptance. Registered
tool dispatch and a structured report response still need integration.

The report validator accepts five bounded text fields, binds the candidate hash,
rejects fabricated result fields and marks the report untrusted/non-executable.
It never creates a successful check receipt from model prose.

SharedBudget tests one sequential ledger across review and repair: four reviewer
calls within sixteen total, twelve reviewer actions within forty-eight total,
180 reviewer seconds within 900 total, and one positive monetary cap. Unsettled
dispatch blocks another dispatch/handoff; invalid or over-admission usage stops
the episode. Uncertainty can stop both phases. The clock and simulated usage are
injected for tests. No real token count or bill was generated.

This contract is not connected to the live runner, not a durable panel-wide stop
mechanism, and does not yet replenish inherited model/tool/time counters. Its
conservative two-edit-attempt limit is not equivalent to two accepted edits.
Do not use it as a live admission authority or claim that scripted unit tests
validate complete three-arm execution.

## Validation and remaining work

Twelve new focused tests and six existing checkpoint-continuation tests passed.
They cover history separation, matching A/B facts/tools, report provenance,
shared cost/call/action/time limits, uncertain usage and phase handoff. Ruff and
whitespace checks passed. Documentation checks passed. No production runtime code
changed; full suite/mock smoke were not repeated for this isolated diagnostic module.
Existing continuation tests exercise their own scripted fixture, not this new
module's end-to-end review-to-repair integration.

Next necessary work is that integration: live-shaped report/tool schema, native
continuation with equal fresh allowances, accepted-edit accounting, durable shared
panel stop/ledger, exact evaluator/scoring manifest, and scripted end-to-end runs.
Dependency/image admission and all private evaluations remain NOT_RUN here. The
pilot remains NOT EXECUTABLE and no paid approval is requested.

Evidence root: C:/pt/analyses/review-offline-restoration-20261001-v1.
Each case retains its materialized workspace, prefix journal and copied CAS;
run_dev_reviewofflinevalidation records the initial three successes/Conan rejection
and a separate final follow-up. Generated state is external to the repository.
