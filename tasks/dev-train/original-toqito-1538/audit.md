# Original-input pilot: toqito-1538

Source: SWE-rebench-leaderboard `vprusso__toqito-1538`, revision
`ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`, split `2026_03`.
The original problem_statement is preserved verbatim as issue.description.

Public feedback runs the existing base module in a disposable copy. It excludes
only `test_sandwiched_renyi_conditional_entropy_unsupported_uparrow`: its public
docstring explicitly requires the feature to remain unimplemented, contradicting
the original issue. No reference-added assertions are public.

Private evaluation applies the original test patch to a separate submitted-source
copy and executes the original command and pinned parser/grading functions.
Reference material contains production changes only. API changes are allowed
because the issue explicitly asks for a public variant/API extension. Four source
files/1,000 lines are pilot restrictions, not original benchmark restrictions.

BASE public PASS/private FAIL; production reference public/private/scope/safety
PASS through the actual evaluator. See
[package integration](../../../docs/history/2026-09-27-original-pilot-packages.md).
All results are `official=false`, development calibration, not agent performance.
