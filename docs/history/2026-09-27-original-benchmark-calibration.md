# Original AnyIO oracle calibration

## Question and implementation

Can the pinned original test material and parser distinguish the unmodified base
from the original reference patch in the local evaluator image?
Added `diagnostics/anyio_benchmark_calibrate.py`, an operator-only successor to
[preparation](2026-09-27-original-benchmark-preparation.md).

Two fresh network-disabled containers used the existing image digest and Python
3.13.13. No host folders were mounted, no packages installed and no images pulled
or built. Each started at the verified clean base. The reference arm applied the
original patch; test-patch paths were reset to base before applying original tests.
Both ran the original full pytest command, without deselections. Containers had
bounded CPU/memory/PIDs, a 90-second test timeout and 115-second outer timeout.

Parser and grading functions were extracted unchanged from the pinned upstream
sources, with enums from the same revision. Extraction and constants are saved.
This executes the upstream per-test parsing and resolution functions, not the full
upstream CLI or its log-wrapper implementation. No historical scoring-version
equivalence is claimed. Reference/test bodies and logs remain evaluator-only.

## Observed result

| Control | F2P success | P2P success | Missing required | Upstream resolution | pytest exit |
| --- | --- | --- | --- | --- | --- |
| BASE | 0/1 | 32/32 | 0 | RESOLVED_NO | 1 |
| REFERENCE | 1/1 | 32/32 | 0 | RESOLVED_FULL | 1 |

Neither control timed out. The declared 33-case oracle distinguishes the controls.
The full command is not green: the three top-level Hypothesis-dependent tests fail
outside the declared set, with three missing-Hypothesis messages in each log. Raw
parser output also contains nested pytest output and expected child failures; those
extra entries must not all be counted as top-level product regressions.

The stored `infrastructure_complete=true` is narrowly defined as required-case
presence, no timeout and exit 0/1. It does not certify all dependencies or all tests.
Both the original resolution and the nonzero full-command exit remain visible;
neither is silently substituted for the other. No tests were removed to obtain this
result. No PatchLoop candidate or model was evaluated.

## Evidence and verification

- Raw root: `C:/pt/analyses/anyio-original-benchmark-calibration-20260927-v1`.
- Journal: `runs/run_dev_originalbenchmarkcalibration.jsonl`, SHA-256
  `2391ed741988794f1a996eb2e0aa99e5455f6103bb0f39acd2a1e43812e9d83e`.
- Independent receipt audit:
  `C:/pt/analyses/anyio-original-benchmark-calibration-audit-20260927-v1`.
  Journal chain and 11 referenced artifacts verified. Four synthetic cases through
  the saved upstream functions verified all-pass, F2P failure, missing F2P and P2P
  regression handling. Synthetic cases are parser checks, not additional task runs.
- Focused suite: 17 tests passed; Ruff passed. Complete repository suite NOT_RUN.
- Mock smoke `run_dev_726d1420fc8d4157` reached EVALUATOR_PASS, safety NOT_RUN,
  at `C:/pt/original-benchmark-calibration-smoke-0927a`; not benchmark evidence.
- Both owned containers removed; subsequent matching container listing empty.
  Preparation journal hash unchanged. No paid calls or changes to historical tasks.

## Next decision

The declared original oracle is usable for controlled local calibration with the
documented full-suite dependency limitation. Existing guided candidates could be
rescored for compatibility, but that would not measure fresh problem solving.
Before a fresh baseline, freeze original issue inputs, agent restrictions, budgets,
sample selection and reporting of environment failures. Keep AnyIO as development
calibration data and choose separate evaluation tasks. All evidence is `official=false`;
there is no active paid allocation or general performance claim.
