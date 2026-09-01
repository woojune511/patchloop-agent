# Current status

## Active runtime

`dev-head` is the sole mutable coding-agent runtime. Its state machine is
`WORK -> VERIFY -> REVIEW -> SUBMITTED`; there is no `PLAN` phase, work-plan tool,
candidate switch, qualification gate, activation gate, or memory retrieval path.

The only coding command is `patchloop dev`. `patchloop doctor` and
`patchloop task validate` are read-only support commands. Legacy `run`, `resume`,
`evaluate`, `rapid`, and provider-backed claim commands are absent.

## Development target

- focused validation: less than two minutes
- default live cycle: one row within 1,800 seconds
- default limits: 40 model calls, 100 tool actions, 4 accepted mutations,
  1 protocol/incomplete recovery, and at most 4 parallel read/search calls
- repeat: 1 by default, 6 maximum, with one invocation-wide cost cap

## Authority

Mock execution has no provider authority and forbids credentials and cost options.
For OpenAI, one fully specified `patchloop dev` invocation is explicit development
authority for exactly its `dev-train` task, model, credential file, repeat count,
and positive total cap. It does not authorize image pull/build, a different task,
a retry after uncertainty, or any confirmatory/claim run.

Repository policy alone never initiates a paid call. The reset implementation was
performed without live provider or Docker execution.

## Evidence status

The local fast suite and mock smoke pass; see `docs/09-evidence.md`. No first-row
live acceptance has been run, so the 30-minute operational target is unverified.
Every current result is `official=false`, and no quality, generalization, causal,
or memory-benefit claim follows.

Historical Rapid and claim code remains recoverable at checkpoint commit
`b71ddeee`; immutable historical results and archive documents remain in their
existing directories. Current checkout compatibility with old runners is not a
goal.
