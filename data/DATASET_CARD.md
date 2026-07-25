# PatchLoop dataset card

## Purpose

The dataset evaluates whether failure-memory representations change coding-agent reliability under fixed
model, prompt, tools and budgets. The evaluator outcome is deterministic; `bad_patch` is never a model
prediction.

## Current contents

Five independently content-addressed `mini-data-utils` tasks are audited and executable as calibration
fixtures. They validate task authoring, sandboxing and deterministic evaluation; they are not members of
the research dataset.

Original smoke fixtures:

- `csv-quoted-newline`: parser state across quoted LF/CRLF fields
- `config-falsy-override`: explicit falsey values in merge semantics
- `path-prefix-boundary`: segment boundaries and parent-segment normalization

Additional calibration fixtures stored under the historical `dev-train` path:

- `duration-minute-boundary`: completed-unit semantics around elapsed-minute boundaries
- `csv-final-record-flush`: parser-state finalization when chunked input reaches EOF

Each package contains public issue/check metadata, evaluator-only hidden acceptance, a reviewed reference
patch and known-bad patches. All five are excluded from failure-memory generation, the core SCRR
denominator and performance headlines. A physical directory such as `dev-train` does not override the
dataset-manifest role.

The first two admitted research tasks are:

- `loguru-invalid-format-feedback`, derived from SWE-rebench `delgan__loguru-1451` and upstream
  Loguru issue #1450 / PR #1451. Its admission evidence contains three reference passes, one base hidden
  failure, 20 upstream regression tests and five independently authored known-bad patch rejections.
- `anyio-interrupt-runner-cleanup`, derived from `agronholm__anyio-1121` and upstream AnyIO issue
  #1060 / PR #1121. A later upstream incident showed that the original fix regressed normal pytest
  outcome handling, so PatchLoop uses a hardened reference and rejects a source-equivalent normalization
  of the original fix. It records three official passes, 20/20 hidden-oracle stability runs, 32 P2P
  regressions, one base hidden failure and five known-bad rejections.

Both tasks pin an exact upstream base commit, MIT license evidence and a digest-addressed SWE-rebench
evaluator image.

## Research dataset target

The research target is 20 newly admitted tasks, separate from the five calibration fixtures.

| Manifest role | Target | Memory source | Currently admitted |
| --- | ---: | --- | ---: |
| Memory development | 6 | reviewed failures only | 2 |
| Development validation | 2 | no | 0 |
| Core same-repo | 6 | prohibited | 0 |
| Core cross-repo | 6 | prohibited | 0 |
| **Research total** | **20** |  | **2** |

Repeated runs of one task must stay in the same role. Development and held-out tasks may share a failure
pattern, but not a solution lineage. Private checks and reference patches are excluded from context,
agent-visible traces and memory source text.

Research admission requires immutable benchmark/upstream provenance, an independently reviewed
medium-or-harder difficulty audit, a base visible-pass/private hidden-fail result, three official Docker
reference passes and at least three representative bad-patch rejections. An executable calibration
fixture or a row in a candidate ledger is not an admitted research task.

## OSS audit

`astanin/python-tabulate` rows in `oss-candidate-ledger.csv` are candidate inventory only. They must pass
source, license, environment, issue/test alignment, dependency, base-test, hidden-acceptance, difficulty
and solution-lineage audits before registration. No `python-tabulate` task is currently admitted.

`benchmark-candidate-ledger.csv` records the pinned SWE-style shortlist and
`terminal-bench-pattern-ledger.csv` records direct-import/adaptation decisions. Candidate rows are not
admissions.

SWE-style benchmark instances and upstream issue/PRs are the primary research candidate sources.
Terminal-Bench 2.1 is used to shape a three-sentinel reliability overlay and external acceptance lane.
Terminal tasks that depend on unrestricted shell, runtime network, binary forensics or background service
administration are not imported into the core suite. Code-writing candidates must first be adapted to the
PatchLoop constrained tool, registered check, submitted patch and separate hidden evaluator contract.

The three stress sentinels are selected from admitted research tasks and receive deterministic
`context-reset`, `worker-kill-after-patch` and `test-timeout` overlays. They do not add to the 20-task
research target and their results are not aggregated into the 96-run core campaign.

## Intended metrics

SCRR, hidden pass, regression-free, scope violations, recovery, cost per success, token overhead and
success/failure flips are reported. Two repetitions are first averaged per task; paired task bootstrap uses
10,000 samples, seed 20260723 and a 95% percentile interval.

Calibration, stress and external acceptance results are always shown separately from research/core
headlines.
