# Reviewer probe admission

## Question and change

The proposed mechanism requires reviewers to execute public counterexamples, but
the scripted integration previously rejected every probe. Read/report-only wiring
could not test that mechanism. Connected the existing registered gateway to the
existing Docker probe backend, explicitly opt-in within the scripted diagnostic.
This changes no default agent behavior and adds no provider collector.

Admission loads the source-bound prepared dependencies and compares the image and
profile identities with the saved envelope. It uses existing images only. A single
180-second reviewer deadline covers preflight and tools; consumed time/actions/cost
still reduce the episode allowance. Reviewer journal identities now vary by output
root, avoiding shared container identities across separate rehearsals.

Actual probe receipts enter the review conversation and remain in its own journal.
The report is still untrusted advice without required-check credit. Failed behavioral
assertions may inform review; cleanup uncertainty, recovery errors and exhausted
deadlines stop the panel before repair. A late report also cannot escape the reviewer
time limit. Repair-stage probes in the older local adapter remain unsupported.

## Conan compatibility boundary

Compared Conan source commit 24f6562f6071b039032fc717193a6ade35f59f84 with the
current checkout. Only two runtime files differ: repository.py adds three allowed
repositories, and prepared_probe_dependencies.py handles nested lock directories
during dependency preparation. Runner, prompt, gateway and probe execution are
unchanged. This narrows the migration question; it does not authorize ordinary resume.

Conan's existing exact-hash materialization opt-in remains limited to offline
candidate/context work. Public probe compatibility can be checked on that restored
candidate without resuming its native agent. Native load still rejects the old
runtime identity. A future live fork must explicitly bind source and target runtime
provenance; do not silently rewrite the original envelope or weaken resume checks.

## Evidence and next decision

Provider-free driver: C:/pt/review_probe_rehearsal_20261001.py.
Evidence root: C:/pt/analyses/review-probe-rehearsal-20261001-v1.
The fixed driver uses a harmless print probe, not task-specific counterexamples.
It tests admission, execution, candidate-bound receipts and report plumbing only.
Original source records and earlier integration evidence remain unchanged.

All eight reviewer executions (A/B on OpenSandbox, isort, pyinfra and Conan)
returned exit 0 and the expected marker, with receipts bound to each original
candidate hash. This confirms public probe admission/execution, not task correctness
or the reviewers' ability to design tests. Conan did not enter native continuation.
The panel journal records all eight receipts; review journals retain tool actions.
The audit driver C:/pt/review_probe_audit_20261001.py rechecked all four original
journal hashes/chains and confirmed default Conan load still rejects runtime drift.

Thirty-one focused tests passed (29 combined plus two added identity tests), including
behavioral failure delivery, cleanup/recovery/deadline stops, admission before dispatch
and source-profile mismatch. Five documentation tests, Ruff and whitespace checks
passed. Mock CLI smoke run_dev_b9a848810224417b reached EVALUATOR_PASS with
safety_state=NOT_RUN, at C:/pt/analyses/review-probe-mock-20261001-v1. Two initial
CLI invocation mistakes stopped before execution; the supported CLI with external
PATCHLOOP_STATE_ROOT completed. Full repository CI was not run for this diagnostic
change. No provider calls, image acquisition or Docker startup occurred.

This completes the reviewer execution seam, not the experiment. Remaining work is
full repair/evaluator environment admission, the explicit Conan fork, a live collector
with rehearsed durable accounting, and frozen scoring/row identities. No paid call
or quality comparison is authorized; no improvement conclusion follows from wiring.
