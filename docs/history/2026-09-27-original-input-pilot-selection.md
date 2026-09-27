# Original-input pilot selection

Following original AnyIO calibration, froze the three-task protocol in
[original-input pilot](../../.agent/original-input-pilot.md).
Selected previously unlisted repositories through deterministic hash ordering,
excluding all repositories in the candidate ledger and public task inventory.
The frozen 2026_03 split contains 110 rows; 87 met the metadata/exclusion rules.

The fixed order is toqito-1538, MontePy-933_interface, darts-3065. Selection uses
public metadata only, with one task per repository. Original issue text is saved
verbatim and hashed. No solution/test patch, hint or result was inspected to choose
the sample. This is a development pilot, not verified historical non-exposure or
held-out evaluation. No task replacement based on readiness or outcomes is allowed.

Evidence: `C:/pt/analyses/original-input-pilot-selection-20260927-v1`, append-only
`runs/run_dev_originalbaselineselection.jsonl` and content-addressed operator artifacts.
The driver captures source hashes for exclusion inputs and dataset bytes. All three
Docker inspections explicitly returned `No such image`; no pull/build was attempted.

Implemented selection driver and deterministic selection/exclusion tests.
Focused selection/documentation tests: 7 passed; Ruff passed. Mock smoke
`run_dev_a420218faf234ff2` reached EVALUATOR_PASS with safety NOT_RUN at
`C:/pt/original-input-pilot-smoke-0927a`. Full repository suite NOT_RUN.
Runtime, task packages and existing historical results remain unchanged. Live runs and
environment calibration are NOT_RUN. The protocol proposes repeat 1 and $1.20 per
task ($3.60 total), but no budget or model invocation is authorized. Exact execution
bindings remain pending environment and public-package preparation.

Next required external action is authorization to acquire the three named evaluator
images, then digest binding and isolated base/reference calibration. Do not confuse
a frozen sample/protocol with execution readiness or benchmark performance.
