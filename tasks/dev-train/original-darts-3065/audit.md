# Original-input pilot: darts-3065

Source: SWE-rebench-leaderboard `unit8co__darts-3065`, revision
`ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`, split `2026_03`.
The original problem_statement is preserved verbatim as issue.description.

Public feedback runs the existing base static-covariates-transformer test module
in a disposable copy. No tests are deselected and no reference-added assertions
are public. Private evaluation applies the original test patch to a separate
submitted-source copy and executes the original command and pinned parser/grading
functions. Reference material contains production changes only.

Four source files/1,000 lines and the dependency/test-edit restrictions are pilot
constraints, not original benchmark restrictions. BASE public PASS/private FAIL;
production reference public/private/scope/safety PASS through the actual evaluator.
See [package integration](../../../docs/history/2026-09-27-original-pilot-packages.md).
All results are `official=false`, development calibration, not agent performance.
