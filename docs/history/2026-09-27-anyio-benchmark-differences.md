# AnyIO original benchmark versus PatchLoop development task

## Scope and sources

Read-only comparison completed on 2026-09-27. No task/runtime changes, Docker
operations, provider calls or benchmark evaluation were performed. This record
compares inputs and declared contracts, not newly executed behavior.

The original row is `agronholm__anyio-1121` in `nebius/SWE-rebench-leaderboard`,
split `2026_03`, revision `ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`.
The [pinned parquet](https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard/resolve/ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b/data/2026_03-00000-of-00001.parquet)
was downloaded into memory and its SHA-256 matched the pinned Hub LFS metadata:
`18e198ac18b3c25b307c0aa5d9b6e20d338886e186bf7c12addb759ad4165a61`.
Only public issue and metadata columns were decoded; patch, test_patch and hints_text
were excluded. No reference patch or private assertion body was inspected.
PyArrow was used through an isolated `uv run --with pyarrow` dependency; repository
dependency declarations and lockfile were not changed.

Local authority: `tasks/dev-train/anyio-interrupt-runner-cleanup{,-v2,-v3}`
public YAML and audit documents, and `data/benchmark-candidate-ledger.csv`.
Structured YAML comparison confirmed repository, issue and constraints equal
across all three versions, and the upstream visible check unchanged.

## Comparison

| Dimension | Original pinned benchmark | Current PatchLoop v3 | Consequence |
| --- | --- | --- | --- |
| Source | AnyIO base and environment setup commit `cb245dba9883516f2ed4c23899de157183a1cb50` | Same repository/base | Source identity is reusable. |
| Problem input | Original issue report, environment information, reproduction code and observed output | Rewritten short description; explicitly requires once-only cleanup and preservation of pass/fail/skip/xfail across shared fixtures | Not identical model input; issue identity alone does not establish input fidelity. |
| Edit constraints | Inspected row does not declare PatchLoop's edit limits | Only `src/anyio/**`, one changed file, 50 diff lines; tests/dependency files forbidden; no dependency/API changes | These are harness restrictions; their effect must be reported separately. |
| Existing tests | 32 declared P2P cases in pytest-plugin tests | Same upstream test file, with three optional Hypothesis cases deselected, unchanged since v1 | Existing regression coverage is useful, but is only part of final benchmark scoring. |
| Added visible feedback | Original row provides final F2P/P2P metadata; does not prescribe PatchLoop's public lifecycle command | v2 adds operator-authored lifecycle feedback; v3 strengthens context/task/teardown checks with seven cases | Additional information reaches the agent and gates submission. These checks were developed by us, not autonomously by the evaluated agent. |
| Final correctness oracle | One F2P plus 32 P2P declarations, original test patch and pytest result parser | Hardened private acceptance plus registered regressions and PatchLoop scope checks | Current acceptance is not original benchmark acceptance; a stricter intent does not prove equivalence or logical inclusion for every patch. |
| Oracle history | Original issue/resolution | v1 audit explicitly adds follow-up outcome-regression hardening; v2/v3 audits retain private contents unchanged | The divergence predates v2's added public checks. |
| Environment declaration | Python `3.13`; prescribed installs including Trio, pytest and uvloop; image named with mutable `:latest` | Task audit pins evaluator image digest `063bb968...c2320`; recent operator probes use a separate prepared Python 3.12 bundle | Original configuration, actual evaluator runtime and probe runtime are distinct. Their equality has not been demonstrated here. |
| Test command | Entire pytest-plugin file with `-rA --tb=line --color=no` and the declared parser | Public regression uses `-q`, explicit deselections, timeout and `PYTHONPATH`; lifecycle has its own subprocess assessment | Passing the public command is not proof the original scoring procedure ran. |
| Run protocol | Row alone does not specify agent sampling or context protocol | Recent four runs continue a selected failed checkpoint, with prior information and arm-specific intervention | These are continuation experiments, not independent fresh benchmark solves. |

The source issue is [AnyIO #1060](https://github.com/agronholm/anyio/issues/1060).
Its reported Python version is 3.12.3; that is distinct from the dataset's Python
3.13 installation configuration. The recent probe's 3.12 environment must not be
mistaken for the original benchmark environment simply because it is closer to
the issue reporter's version. The pinned row's mutable image tag also cannot prove
which image digest was used historically.

## What existing evidence can support

- Reuse source identities, exact saved patches, run traces, delivery/billing
  receipts and environment diagnostics as development evidence.
- Retain existing acceptance verdicts under their original task version. Do not
  pool v1/v2/v3 as unchanged inputs or relabel results as original benchmark scores.
- Saved patches could later be rescored with the original oracle. That would
  answer patch compatibility, not fresh agent success without added guidance.
- Earlier fresh runs are fresh starts on adapted tasks, not automatically original
  benchmark runs. Resource-limited/non-submitted outcomes remain separately reported.
- AnyIO has already informed harness development. Use it for adapter calibration;
  it cannot serve as an untouched held-out example for this development process.

## Next bounded step

Prepare the original-oracle adapter and environment verification specification,
without launching a model: pin the original test artifact and scoring implementation
on the evaluator side, verify exact case membership and parsing, resolve an image
digest and actual interpreter/dependency versions, and distinguish infrastructure
failure from task failure. Keep original issue input separate from added developer
checks. Base/reference calibration belongs only in isolated evaluation, never agent
context. No such calibration or original-oracle score was executed in this review.

Then choose a separately declared development/evaluation sample and run protocol.
A new paid run still requires its own exact allocation. All current evidence remains
`official=false`; this document makes no general performance claim.
