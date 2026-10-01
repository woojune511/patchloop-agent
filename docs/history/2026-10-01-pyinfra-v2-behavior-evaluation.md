# Pyinfra v2 behavioral evaluation

## Problem and revision

The [operator audit](2026-10-01-pyinfra-evaluator-audit.md) reproduced two original
failures caused by internal call spelling and a mock that bypassed timeout
resolution. Those assertions could reject equivalent implementations. Added the
separate original-pyinfra-1679-v2 development package to test the effective values
at the Paramiko connection and channel boundary instead.

V1 package bytes and original FAIL remain unchanged. V2 preserves all public
fields except task_version=2, including the issue, source/base, constraints and
visible regression command. The evaluator image is unchanged. A task-private-v2
inventory binds the new hidden program. Hidden material is never projected into
agent context. No acceptance gate is bypassed.

Seven test methods cover target SSH configuration, independent hop configuration,
explicit paramiko overrides over ordinary defaults and SSH configuration, direct
timeout kwargs, absent timeouts, direct-host configuration, and gateway effective
arguments/return value. The gateway method includes omitted, explicit None, zero
and positive timeout subcases. Real SSHConfig parsing and SSHClient connection,
configuration and gateway code run; Paramiko network calls and host-key loading
are replaced with local fixtures. Equivalent keyword omission is accepted.

The reference artifact is the saved submitted patch, not an independent reference
implementation. Checks were authored after inspecting that patch and the original
failures. This is exposed, post-run development calibration, not an original
benchmark result or held-out measurement.

## Frozen calibration

The external protocol fixed seven controls, one execution each, before dispatch.
Unexpected verdicts, timeouts or cleanup failures stop before full evaluation.
Controls ran in fresh prepared-source checkouts with the same existing pinned
image, network disabled, read-only source/root and 60-second hidden-check limits.
The imported candidate module is checked against /workspace/src.

| Control | Expected and observed | Failed assertions / subcases |
| --- | --- | --- |
| Unmodified base | FAIL | 5 assertions, 3 unsupported-interface errors |
| Saved submitted patch | PASS | 0 |
| Saved patch with explicit None forwarding | PASS | 0 |
| Channel timeout discarded | FAIL | 6 |
| SSH ConnectTimeout ignored | FAIL | 4 |
| Target timeout incorrectly forwarded to hop | FAIL | 2 |
| Explicit paramiko override omitted before configuration resolution | FAIL | 1 |

Wrong-behavior mutations all failed assertions, with no setup errors. The base
also lacks the newly required gateway timeout parameter, producing TypeErrors in
three interface subcases; those are contract failures, not infrastructure failures.
No completed control was retuned or rerun. All container cleanups succeeded.

Full isolated EvaluationEngine replay of the saved patch on v2 then returned
hidden PASS, regression PASS, scope PASS, safety PASS and
scope_compliant_success=true. Manifest model identity is
operator-saved-patch-no-model; no provider or count call occurred.
This is a separate saved-patch evaluation, not a new autonomous solve.

## Decision and limits

V2 distinguishes the selected working/equivalent implementations from the tested
incorrect implementations. Keep the agent baseline unchanged. Preserve the fixed
batch's original 0/3 accepted result and the pyinfra v1 FAIL; the new PASS belongs
only to this separately identified v2 operator replay. No paid run is queued.

These tests establish argument flow and selected precedence semantics. They do not
measure real network waits, banner exchange, multi-hop configurations or general
repair quality. The fixtures still depend on implementation entry points, although
they avoid the two overly specific internal-call assertions identified in the audit.

## Evidence and validation

Task content hash:
`sha256:68d8c7269e4a47561e462e157e9d2a9189dd2662fe172f85aa6d9a9dee23eaa1`.
Saved patch hash:
`sha256:b34362d8686ee9a0798e40e55eed651ce8fdc60080f9bece13dd6f8fa129c3ed`.
External root: `C:\pt\analyses\pyinfra-v2-calibration-20261001-v1`.
Journal: `runs/run_dev_pyinfrav2calibration.jsonl`; all eleven events validated.
Receipts bind each control's exact diff and full output. `evaluation/` retains the
persisted manifest and isolated result for `run_dev_pyinfrav2savedpatch`.
Driver: `C:\pt\pyinfra_v2_calibrate_20261001.py`.

Five package-integrity/public-preservation/projection tests, five documentation
checks, package CLI validation, Ruff and whitespace checks passed. Mock smoke
reached EVALUATOR_PASS with safety NOT_RUN, separate from the real Docker saved-patch
safety PASS. An optional four-worker full suite was interrupted after several
minutes at roughly 8% with no failures reported; it is incomplete, not a full-suite
PASS. Focused checks and isolated evaluation cover this package-only change.
No runtime, prompt, original package or earlier historical record changed.
