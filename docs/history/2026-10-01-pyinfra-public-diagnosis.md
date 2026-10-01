# Pyinfra public timeout diagnosis

## Question and evidence boundary

Does pyinfra's submitted failure repeat OpenSandbox's incomplete caller/helper
coverage, or does it need a different explanation? The fixed batch reported 1/3
target bug cases passing and 10/10 regressions passing. That aggregate result does
not establish which public behavior is wrong. This diagnostic used the original
public issue, base source, submitted patch and public action trace only. Hidden
test contents and reference patches were not inspected or executed.

Base: `185f7dbec96f8e1d5f7cfefe0f325f99ab73927a`.
Run: `run_dev_710588e1c1a94d4f`; submitted patch SHA256:
`b34362d8686ee9a0798e40e55eed651ce8fdc60080f9bece13dd6f8fa129c3ed`.

The patch extends gateway(timeout=None), forwards supplied timeout to
transport.open_channel, reads SSH ConnectTimeout when no explicit timeout exists,
and merges paramiko overrides before configuration parsing. The jump-host connect
call still receives its own derived settings rather than the target's timeout.
This suggested a possible propagation gap, with alternatives that the target
channel fix is sufficient or that import/environment behavior explains the result.

## Public trace

The agent read client.py across its connection, parsing and gateway code and read
the upstream public tests. Two edits were accepted; another edit failed because
its exact anchor was stale/absent. No run_probe action occurred. The registered
public checks passed, including the previously documented exclusion of the old
gateway call-shape assertion. That exclusion and the original hidden tests were
not changed here. Lack of a probe is an observation, not proof that mandatory
probes would have improved the result.

## Frozen controlled diagnostic

Before execution, recorded the question, alternatives and program in an external
hash-chained journal. Ran six observations on each of three fresh source snapshots:
base, submitted patch, and a local control that forwards cfg.timeout into the jump
connection. Used the same already-installed pinned benchmark image, explicit
PYTHONPATH=/workspace/src and asserted the imported module's /workspace/src origin.

Parsed real SSHConfig text and executed SSHClient.connect/parse_config/gateway.
Mocked Paramiko's network connection, host-key loading and transport/channel calls
to record actual arguments. DockerSandbox used network none, read-only source/root,
existing resource bounds and 60-second check timeout. All three executions exited
0 and cleanup was confirmed. These are argument-flow observations, not measured
SSH handshake timeouts or network integration tests.

| Submitted-patch input | Jump connection timeout | Target connection timeout | Channel-open timeout |
| --- | --- | --- | --- |
| Target SSH ConnectTimeout 5 | omitted | 5 | 5 |
| Explicit paramiko timeout 2 over ordinary timeout 10 | omitted | 2 | 2 |
| Direct timeout kwarg 2 | omitted | 2 | 2 |
| No timeout configured | omitted | omitted | omitted |
| Jump ConnectTimeout 3, target ConnectTimeout 5 | 3 | 5 | 5 |

The explicit paramiko case also preserves auth_timeout, banner_timeout and
channel_timeout=2 on the target connection. Direct gateway(timeout=2) forwards 2
to open_channel. Base omitted the channel timeout in all five composed cases and
did not support the direct gateway timeout argument.

The local forwarding control changes an omitted jump timeout to the target value,
but also changes the jump-specific 3 to target-specific 5. It therefore demonstrates
a precedence regression for that control, not a solution to adopt. The public issue
does not clearly require target-specific settings to override a distinct jump host's
settings. We cannot label absence of that propagation a proven defect on these data.

## Decision

The narrow missing-boundary explanation is not established for pyinfra. Unlike
OpenSandbox, the submitted code carries the issue's explicit values through the
target connection/channel boundary in this diagnostic. Preserve that positive
evidence alongside the historical hidden FAIL; neither erases the other.

Do not add a shared prompt, mandatory probe rule or timeout propagation change.
Next audit the evaluator's two failing expectations against the public contract
as an operator-only investigation before deciding whether this is an uncovered
behavioral defect or an overly specific test expectation. That audit was NOT_RUN
here, and the exact hidden failure cause remains unresolved. Multiple hops,
actual waiting/exception behavior and a full SSH environment are also untested.
The six selected observations are not a general correctness claim.

## Evidence

Root: `C:\pt\analyses\pyinfra-public-diagnosis-20261001-v1`.
`runs/run_dev_pyinfrapublicdiagnosis.jsonl` is the append-only hash-chained journal.
`summary.json` retains all 18 observations and each artifact receipt includes the
program result and execution policy. Driver: `C:\pt\pyinfra_public_diagnosis_20261001.py`.
Only documentation changed in the repository. No paid call, new image, private
oracle modification or historical rewrite occurred. Documentation checks passed.
