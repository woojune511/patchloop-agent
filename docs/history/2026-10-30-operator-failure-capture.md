# Preserve operator assertion evidence behind long pytest headings

Started 2026-10-30, completed 2026-10-31 (KST). Local diagnostic implementation;
no live model or task rerun.

## Problem, evidence and decision

The [operator evaluation audit](2026-10-30-sqlfluff-operator-evaluation-audit.md)
found that a bounded output tail retained failure statuses but not their assertion
tracebacks. Its section extractor recognized no blocks. The user requested better
retention of failed assertions and actual/expected values while leaving evaluation
criteria unchanged. This affects diagnosis: a FAIL without its assertion encourages
speculation about the agent or patch instead of evidence-based intervention.

The old header parser required at least three separator characters on both sides.
Pytest emits only one underscore on each side when a parameterized test name is
wider than the terminal. A fresh synthetic pytest failure reproduced that output;
all six new synthetic regression cases failed before the change because their
failure blocks were not retained. This establishes a generic recognition defect.
The original omitted private traceback remains unavailable, so the historical
failure's exact lost header is not retrospectively established.

Use a small recognition correction within the existing operator capture mechanism.
Do not change tests, assertions, test commands, grading, output budgets or solver
feedback. A new reporter/plugin, larger log store or semantic value parser is not
needed for the demonstrated defect.

## Change and boundaries

`diagnostics/swebench_lite_oracle.py` now recognizes one/two-character pytest case
headings, short captured-output boundaries and section headings. ANSI SGR color is
removed only for recognition. Byte offsets and stored slices still refer to the
original output. An explicit normalized section-end marker prevents a colored
summary from leaving the failure section open and capturing later ordinary text.

The retained section includes the runner's assertion source, error explanation and
actual/expected diff. These are original diagnostic bytes, not inferred or rewritten
values. The existing 24,000-byte stream tail, eight failure-block limit and 12,000
failure bytes per stream remain. Huge blocks retain head/tail with explicit omitted
bytes; unrecognized and partial output remain explicitly labelled. Values that the
test runner did not print, or that exceed retention bounds, are not promised.

The recognition label is `pytest-sections-unittest-sgr-text-v2`; the outer
`private-evaluation-log-v1` envelope remains compatible. Original stdout/stderr are
still supplied unchanged to the benchmark grader. The grading `main()` AST is
identical, including test patch/command execution, completeness checks and exit0/1/2.
No private input, test body, expected value or reference patch was copied into the
new tests or solver context. Old receipts and historical records are immutable.

Refresh exactly the twenty mutable current-dev20 adapter copies and their declared
adapter hashes. Byte-check 1,181 protected files and all private-manifest changes:
original tests, reference artifacts, grading/parser files, commands and historical
packages remain unchanged; each private manifest changes only one adapter hash.
The package builder already copies/hashes the canonical adapter, so it needs no edit.

The runtime hash remains
`sha256:47057ca997eaa2ba5c3c566aa76df16ae9c4e2bdb41b47f08d68da05b0ff2fd9`:
diagnostics/task files have separate task identities. Updated task packages require
new preparation identities; old prepared manifests must not silently be reused.

## Local evidence

- Six new synthetic cases: short headings/boundaries and adjacent failures;
  ANSI/UTF-8 original offsets and summary closure; actual/expected diffs between
  megabytes of output; real pytest with color enabled and disabled.
- Real pytest children still exit1 and report their intended synthetic failure.
  Assertion source and expanded value differences are retained outside the stream
  tail; bulk captured output is excluded from the failure block.
- Focused owner/package suite: **24 PASS in 14.82 seconds**. Existing tests cover
  bounded output, timeout/collection/setup/unittest failures, unchanged grading
  exits and private evidence not being reinserted into solver requests.
- Ruff passed for `patchloop`, `tests` and the canonical adapter.
- Quick suite: **1,291 PASS / 1 host-symlink SKIP in 849.14 seconds**; includes
  isolated mock evaluation, which was not run again separately. This is validation
  duration, not a runtime speed improvement claim.
- Final document checks and artifact identities are recorded in the external
  validation journal. HTML behavior scripts remain unchanged.

This demonstrates diagnostic retention for the tested formats. It does not recover
old missing bytes, validate an actual task repair, establish complete recognition
of arbitrary output or improve model acceptance. Text inside captured logs can
imitate framework headings; `recognized-blocks-only` remains the coverage claim.

## Evidence identities

- Starting HEAD: `ef7a1173`.
- External root: `C:/pt/oracle-failure-log-20261030-v1`.
- Append-only journal: `runs/run_dev_oraclefailurelog.jsonl`.
- Original adapter: `sha256:2f2f1e5d74554fcdc1797fc0be63534273d753cda38fb2665853868d3385e554`.
- Updated adapter: `sha256:94949d0098e5482be501868e5cd105176e49f672bcb4ea05211727a0b92103fe`.
- Scope/grading integrity: `sha256:f4c9d1812117986986b0de286e66d513c6ae1ca2e0adf8163a62eec75802066f`.
- Focused result: `sha256:cb9b23cdba8e6c976700d2a2534755ab3476e97d1deaa3e0cc9384bbeae51f79`.
- Ruff result: `sha256:e2b94e15477fe0541dca95032bcab931c49d7f2ebfe051a856d24a8c9c1577fd`.
- Quick result: `sha256:eba5131000735c94de1a33afddb36c13cf9dbda994ce9c81dd70682f68c7bd90`.

No paid allocation, target task execution or evaluator replay was started. Further
changes should follow a concrete unsupported output format, not speculative growth
of diagnostic machinery or transfer of private evaluation criteria to the solver.
