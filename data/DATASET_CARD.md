# PatchLoop dataset card

## Purpose

The dataset evaluates whether failure-memory representations change coding-agent reliability under fixed
model, prompt, tools and budgets. The evaluator outcome is deterministic; `bad_patch` is never a model
prediction.

## Current contents

Four independently content-addressed `mini-data-utils` tasks are audited and executable.

Smoke:

- `csv-quoted-newline`: parser state across quoted LF/CRLF fields
- `config-falsy-override`: explicit falsey values in merge semantics
- `path-prefix-boundary`: segment boundaries and parent-segment normalization

Dev-train:

- `duration-minute-boundary`: completed-unit semantics around elapsed-minute boundaries

Each package contains public issue/check metadata, evaluator-only hidden acceptance, a reviewed reference
patch and known-bad patches. The smoke packages are pipeline fixtures. The dev-train package is eligible
for development failure collection only; its reference and private assets remain excluded from agent
context and memory source text.

## Planned splits

| Split | Planned | Memory source | Current |
| --- | ---: | --- | ---: |
| Smoke | 3 | no | 3 |
| Dev-train | 6 | reviewed failures only | 1 |
| Dev-validation | 2 | no | 0 |
| Same-repo held-out | 6 | prohibited | 0 |
| Cross-repo held-out | 6 | prohibited | 0 |

Repeated runs of one task must stay in the same split. Dev and held-out tasks may share a failure pattern,
but not a solution. Private checks and reference patches are excluded from context, traces visible to the
agent and memory source text.

## OSS audit

`astanin/python-tabulate` candidates must be merged bug-fix PRs before 2026-01-01, pass the size,
dependency, base-test and hidden-acceptance criteria, and be selected deterministically within the three
predeclared categories. Every exclusion and fallback is recorded in `oss-candidate-ledger.csv`. No OSS
task is currently represented as audited.

## Intended metrics

SCRR, hidden pass, regression-free, scope violations, recovery, cost per success, token overhead and
success/failure flips are reported. Two repetitions are first averaged per task; paired task bootstrap uses
10,000 samples, seed 20260723 and a 95% percentile interval.
