# Current status

`dev-head` is the only active coding-agent runtime. It is mutable, development-only,
and always records `official=false`. The available commands are `patchloop dev`,
`patchloop doctor`, and `patchloop task validate`; legacy Rapid and provider-backed
claim commands are absent.

## Targets and limits

- focused local validation: under 2 minutes
- default one-row live limit: 1,800 seconds
- 40 model calls, 100 tool actions, and 4 accepted mutations
- one protocol/incomplete correction and at most 4 parallel reads
- `repeat=1` by default, 6 maximum, under one invocation-wide cost cap

## Authority

Mock execution carries no provider authority. One exact live `patchloop dev`
invocation authorizes only its declared `dev-train` task, model, credential file,
repeat count, and positive total cap. It never authorizes an image pull/build,
another task, an automatic retry after uncertainty, or a confirmatory claim run.

Repository policy alone never initiates paid work. No live provider or Docker
execution occurred during the reset or this documentation consolidation.

## Evidence state

Ruff, the fast suite, and mock smoke pass. The first live row has not been run, so
the 30-minute operational target remains unverified. See
[Evidence and limitations](evidence.md) for exact local observations and non-results.

Historical executables are recoverable at checkpoint `b71ddeee`; immutable
historical artifacts and `docs/archive/` remain preserved. Current checkout
compatibility with those runners is intentionally unsupported.

## Next decision

The next operational step is a separately approved one-row `dev-train` invocation.
A confirmatory lane is not considered until three distinct tasks submit without a
harness/contract terminal and at least two privately pass. That threshold opens a
design review only; it does not support a quality or generalization claim.
