# Original-input pilot image acquisition and calibration

## Scope and method

User explicitly authorized the three image downloads and base/reference validation
following [pilot selection](2026-09-27-original-input-pilot-selection.md). No paid
model call was authorized or performed. Added the operator-only
`diagnostics/original_pilot_calibrate.py` driver.

Downloaded the three selected image tags and bound repository digests in the
[pilot protocol](../../.agent/original-input-pilot.md). The saved selection journal
and original problem hashes were checked against the frozen dataset. Original
reference/test patches and grading identities remain evaluator-only artifacts.
The unchanged pinned parser/grading source from the AnyIO calibration was reused;
this remains selected-function execution, not the full upstream CLI.

Each environment check and each BASE/REFERENCE control used a separate disposable
container, no host mounts, no network, dropped capabilities, 2 CPUs, 4 GiB RAM,
256 PIDs, 90-second test and 115-second container-command timeouts. No dependencies
were installed and no tests deselected. The original command ran after applying
original test material; reference controls applied the original reference patch.

## Observed results

| Instance | BASE F2P | BASE P2P | REFERENCE F2P | REFERENCE P2P | Reference command exit |
| --- | --- | --- | --- | --- | --- |
| toqito-1538 | 0/15 | 16/16 | 15/15 | 16/16 | 0 |
| MontePy-933_interface | 0/6 | 40/40 | 6/6 | 40/40 | 0 |
| darts-3065 | 0/4 | 8/8 | 4/4 | 8/8 | 0 |

All BASE commands exited 1 and scored RESOLVED_NO; all REFERENCE commands scored
RESOLVED_FULL. Every required case was present, with no timeouts. All images report
Python 3.13.13 and the selected clean base commit. These are known control patches,
not agent solutions, so this establishes local evaluator readiness only.

## Evidence and checks

Raw root: `C:/pt/analyses/original-pilot-calibration-20260927-v1`.
Journal: `runs/run_dev_originalpilotcalibration.jsonl`, SHA-256
`ddeb82f0220827ddb787034f4209377cb9cc460dba7897a19c1043402e69bb98`.
The executed driver source is retained as an artifact. A subsequent lint-only edit
binds synchronous loop closure defaults explicitly; the executed bytes remain saved.

Audit root: `C:/pt/analyses/original-pilot-calibration-audit-20260927-v1`.
All 48 journal events and 38 referenced artifacts verified; all six controls match
their expected outcomes. The original selection journal is unchanged. Nine owned
containers were removed and the follow-up matching container listing was empty.

Focused reused calibration/selection/state/documentation suite: 19 passed. Ruff
passed. Mock smoke `run_dev_f09006f12ba44316` reached EVALUATOR_PASS with safety
NOT_RUN at `C:/pt/original-pilot-calibration-smoke-0927a`. Full repository suite
NOT_RUN. No runtime/task package changes, paid calls or general performance claims.

## Next step

Prepare the three original-input task packages: verbatim issue text, registered
base-only public commands, production allowlists and isolated original scoring.
Bind package/runtime identities before requesting any paid allocation. Do not reuse
the adapted AnyIO task or treat this calibration as a completed agent baseline.
