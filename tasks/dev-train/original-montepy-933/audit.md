# Original-input pilot: MontePy-933_interface

Source: SWE-rebench-leaderboard `idaholab__montepy-933_interface`, revision
`ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`, split `2026_03`.
The original problem_statement is preserved verbatim as issue.description.

Public feedback executes the existing base universe test modules in a disposable
copy, allowing Hypothesis scratch writes without changing the read-only source
mount. No tests are deselected and no reference-added assertions are public.

Private evaluation applies the original test patch to a separate submitted-source
copy and executes the original command and pinned parser/grading functions.
Reference material contains production changes only. API changes are allowed
because the original issue requests a property deleter. Four source files/1,000
lines are pilot restrictions, not original benchmark restrictions.

BASE public PASS/private FAIL; production reference public/private/scope/safety
PASS through the actual evaluator. See
[package integration](../../../docs/history/2026-09-27-original-pilot-packages.md).
All results are `official=false`, development calibration, not agent performance.
