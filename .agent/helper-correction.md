# Helper program preflight and one correction

The [failed-helper audit](../docs/history/2026-10-25-helper-stop-analysis.md)
found a helper using `reproduction_workspace`, which is injected only for original
reproduction. The error was delivered, but ordinary reads consumed the remaining
diagnostic opportunities. This contract addresses that first-repair bottleneck.

## Available APIs and scope

Fresh `purpose={kind: helper}` programs have normal Python builtins and the shared
`check_setup(label, actual, expected)` function. They import public project code
and Python libraries normally. Use `tempfile.TemporaryDirectory` and `pathlib.Path`
for helper fixtures. `reproduction_workspace`, `observed_target`, and
`record_observation` belong to `original_requirement`; its frozen fixture and
observation identity contract stays unchanged.

`helper_program.validate` compiles without execution and checks lexical bindings
for those three original-only names. It rejects syntax errors and unbound uses
before dispatch, naming `/python_source`, the source hash and available APIs.
Imports, local definitions and closure bindings are allowed. Dynamic namespace
operations and wildcard imports make the name check inconclusive; syntax checking
still applies. A valid source is not guaranteed to execute successfully.

This is preflight correction, not a general runtime setup-error classifier.
Traceback location, `check_setup` failure and absent changed-line hits cannot prove
that no target ran. Arbitrary NameError, import failures, assertion failures,
timeouts and uncertain execution do not create a correction ticket.

## Same-question bounded correction

Before the first accepted mutation, the first confirmed helper program preflight
failure creates one run-wide `helper-program-correction-v1` ticket. It binds the
original action/input/source hashes, exact question and workspace diff. The public
state retains the source and error until the correction is attempted.

While pending, offer only a fresh helper `run_probe` with the exact same question
and changed source, or `stop_task`. Original replay, another question, project
mutation and unrelated inspection cannot consume the reserved diagnostic as useful
work. Host validation also enforces the restriction for direct gateway requests.
The single correction request is recorded even if rejected; a new action ID,
restart, later malformed helper or comment-only change cannot replenish the ticket.
Changing source alone is insufficient: complete preflight must pass.

A settled execution ends the program correction. A returned target exception or
assertion can be diagnostic evidence, so exit 1 is not automatically classified
as another setup failure. Execution status remains visible and behavior is
`not_assessed`; original-call verification and registered checks remain separate.
Another preflight rejection, missing/uncertain return, timeout or unavailable
completion capacity leaves verification incomplete. Explicit stop abandons the
run without submission. No failed program is automatically executed again.

## Resources and recovery

The pending correction adds one model call and one tool action to minimum and
protected completion forecasts. Admission can spend speculative recovery capacity
while preserving minimum repair, acquired-original replay, fresh checks and finish.
Actual cost admission and the separate protocol-response correction reservation
still apply. No count, time, output or dollar limit is increased.

`action_started.helper_recovery_link` binds the attempted correction. Existing
`action_id + input_hash` recovery returns completed receipts; a durable probe return
can finish a lost action receipt without re-execution. A started execution with no
durable return retains `RECOVERY_ERROR`, never an automatic retry. Pure forecasts
do not write state. Unresolved correction at an output/resource stop preserves the
underlying stop cause and returns `VERIFICATION_INCOMPLETE`.

Run `uv run --locked pytest @tests/helper-correction.txt --basetemp C:/pt/<unique>`
for short local controls, then quick for integration and isolated mock evaluation.
These checks establish mechanics, not real-model uptake or F0010 repair gain.
