# Helper preflight and original argument correction

The [failed-helper audit](../docs/history/2026-10-25-helper-stop-analysis.md)
found a helper using `reproduction_workspace`, which is injected only for original
reproduction. The error was delivered, but ordinary reads consumed the remaining
diagnostic opportunities. This contract addresses that first-repair bottleneck.

## Available APIs and scope

Fresh `purpose={kind: helper}` programs have normal Python builtins and the shared
`check_setup(label, actual, expected)` function. They import public project code
and Python libraries normally. Use `tempfile.TemporaryDirectory` and `pathlib.Path`
for helper fixtures. `reproduction_workspace`, `reproduction_outputs`, `observed_target`, and
`record_observation` belong to `original_requirement`; its frozen fixture and
observation identity contract stays unchanged.

`patchloop/sandbox/probe_api.py` owns the injected API signatures, mode availability and
settings limits. Both ordinary and first-reproduction descriptions include its
setup and observer contracts. The first description remains under the existing
4K control with the default environment description; parameter schemas are unchanged.
The live failure motivating this change is recorded in
[the observation-opportunity result](../docs/history/2026-10-29-observation-opportunity-fresh-results.md).

`helper_program.validate` compiles without execution and checks lexical bindings
for those four original-only names in helper mode. It rejects syntax errors and unbound uses
before dispatch, naming `/python_source`, the source hash and available APIs.
Fresh helper and original programs also check definite direct API calls: missing
setup arguments, invalid observed-target keywords and literal count overflow.
Errors retain the authored line and structured `helper_program_error.api_error`
(API, parameter, error code, missing parameters or actual/maximum counts).
Imports, local definitions and closure bindings are allowed. Dynamic namespace
operations and wildcard imports make the name check inconclusive; syntax checking
still applies. Aliases, argument expansion and shadowed names are not resolved by
the call check. A valid source is not guaranteed to execute successfully.

The trusted runner's setup wrapper binds the same signature before comparison;
`inspect.signature(check_setup)` retains the real label/actual/expected parameters.
Runtime binding errors return bounded `setup_checks.api_error`. They do not establish
target nonexecution: arbitrary target code may have run before a setup call.
Fresh v11 observed-target settings use the same validator and report the precise
field, actual count and limit in stderr. The existing typed request phase remains
the settings-rejection classification evidence. Stored v1-v10 programs retain
their exact bytes and completed receipts remain idempotent.

`input_paths` accepts at most 4 fixture roots and recursively snapshots directories.
Related inputs may share one root; required files must not be omitted, generated
outputs/ancestors remain excluded, and existing snapshot bounds remain enforced.
The API module is copied beside the trusted setup helper and bound by
`helper_api_hash` in the sandbox profile. No observer/source/resource limit increases.

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

Run `uv run --locked --offline pytest @tests/helper-api.txt --basetemp C:/pt/<unique>`
for short API-contract, dynamic-error, next-request delivery and recovery checks.
Use `@tests/argument-correction.txt`
for focused helper/original correction controls and isolated mock evaluation.
The broader quick suite remains available for cross-feature integration. These
checks establish mechanics, not real-model uptake or F0010 repair gain.

## Original-call argument binding

V9-v11 `observed_target(...)` wrappers expose `target.signature()`: a bounded
actual callable signature string, or None if unavailable/oversized. Inspect it
before choosing Python arguments. A zero-parameter CLI reads its own sys.argv;
setting argv does not add a Python list parameter. No argument coercion occurs.
Each call records its actual signature again at binding time. `binding_error`
marks only TypeError from Signature.bind with an available signature; target
TypeError, import/snapshot errors and missing signatures are not this evidence.

Before the first mutation, a settled original v9-v11 invocation whose valid call rows
all prove target_started=false and include an explicit binding error may create
`original-argument-correction-v1`. Its action, input, program, diff and execution
receipts must agree, with confirmed cleanup and no timeout/truncation/uncertainty.
This shares the existing one-per-run helper correction allowance; it adds no
separate retry counter. Legacy v1-v8 records do not create the new ticket.

The next response receives the failed source, signature, supplied arguments and
argv. Only a changed program with the exact question, original purpose and
call-path request, using a new action ID, or stop is offered. The small original
schema remains active. Every attempted correction consumes the ticket, including
rejection. A repeated pre-target failure stays verification incomplete. A healthy
returned invocation with all recorded calls entered and complete captures settles
only argument correction; original behavior still needs observations and replay.

Acquisition attempt/rejection quotas remain enforced by scheduler and gateway,
including after recovery. The completion forecast reserves one correction plus
one prospective original replay, without counting acquisition twice. Existing
model/tool/output/cost/time caps and uncertain-execution recovery remain unchanged.
No error is automatically retried, and a completed action is recovered idempotently.
The closed first-probe diagnostic still stops at its first result; it is not the
runtime feedback loop and needs separate authorization to test a continuation.
