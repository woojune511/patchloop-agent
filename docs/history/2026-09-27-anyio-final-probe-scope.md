# AnyIO final candidates: environment and verification scope

Date: 2026-09-27. Follow-up to the
[process audit](2026-09-27-anyio-observation-process-audit.md).
All observations are `official=false`, `claim_eligible=false`. No model calls,
candidate generation, registered task checks or private evaluation were executed.
The closed A/B acceptance and safety results are unchanged.

## Question and method

The public `explicit_cancel` case selects a plain fixture, and its
`same_fixture_task` assertion short-circuits for plain fixtures. Its PASS did not
directly establish same-task cleanup after ordinary cancellation. The original
model-authored state-observing probe had not been rerun on the final candidates.

We replayed that exact public program once on the previous failed seed and once
on each of the four submitted candidates. Each candidate was reconstructed from
its hash-verified submitted patch on a fresh local prepared-source clone. Stored
workspaces, patches and closed journals were not modified. No remote source fetch
or dependency resolution was needed.

The probe observes setup, cancellation and fixture advancement before leaving the
runner context. It catches and prints exceptions, so process exit zero establishes
diagnostic completion, not task correctness. The operator separately assessed
runner survival, cleanup event counts and task identity from its emitted states.

## Environment evidence

Docker Desktop's existing Linux daemon responded; it was not started. The ordinary
DockerProbeSandbox admitted the existing pinned Python 3.12 image and verified the
selected pytest dependency inventory. Runtime, public task, prepared source,
dependency descriptor and probe identities matched the earlier reproduction.
No image pull/build, network access inside probes or private task material was used.

- Runtime: `sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.
- Probe: `sha256:ac9690149fcc5a3c8694a3db21859479a19ba610434f67551b80502c653d5cc8`.
- Dependency descriptor: `sha256:ae8d0a01dd8c67305ea620a885a75c73344979104f6d067e83dc3aebc79f143e`.
- Image: `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
- Profile: `sha256:df3a7c7097f2c964d74f53c7d0b2c2c2b1a6d5c6e0d40f77c3d1ed678e650e01`.

Each row retained the full 30-second execution timeout within a 120-second operator
deadline. Network-none, read-only source/root/dependencies, one CPU, 512 MB memory
and the existing PID/thread limits remained in force. Five processes exited zero
without timeout or output truncation; five owned containers were confirmed absent.
The exact lifecycle entry point completed, beyond merely importing TestRunner.

## Observations

| Candidate | Runner survives cancellation | Cleanup completes once | Cleanup in original task |
| --- | --- | --- | --- |
| Previous failed seed | No | No | No cleanup observed before final print |
| A1 / NA1 | Yes | Yes | Yes |
| B1 / NB1 | Yes | Yes | Yes |
| B2 / NB2 | Yes | Yes | Yes |
| A2 / NA2 | Yes | Yes | Yes |

The seed reproduced the prior done/cancelled runner and `ClosedResourceError`
during fixture advancement, with the same public source snapshot hash. All four
final candidates propagated CancelledError to the caller while keeping the shared
runner alive. Cleanup started and completed once on the setup task. Each test's
cancel handler and finally block ran once; no post-cancellation continuation ran.

These observations close the specific unverified same-task teardown question for
these saved candidates and this single-cancellation plain-fixture program. They do
not prove equivalence across all cancellation states, necessity of extra branches,
post-context-exit shutdown behavior, spontaneous model verification, or fresh
end-to-end solving within the original budget. No runtime/prompt/default change is
supported by this replay. The separate full-solve budget question remains open.

## Evidence and validation

Packet: `C:\pt\analyses\anyio-final-probe-scope-20260927-v2` contains the bounded
operator script, plan, environment admission, five raw receipts, five assessments,
results and closure. Generated state is a 13-event hash-chained `dev-run-v1` journal.
Closure verified 44 input/history files unchanged and an unchanged runtime before
this follow-up and the mutable current/index documentation were written.

The first operator preparation (`v1`) stopped on Windows cp949 decoding while
reading a UTF-8 journal, before any probe dispatch. Its script is preserved. The
successor specifies UTF-8 and is a separate packet; no task failure is attributed
to that preparation error. Initial sandbox Docker/Python access restrictions were
resolved through approved host execution, not daemon startup or environment edits.

Operator-script Ruff and the five documentation layout/link tests passed. Product
regression and mock smoke were not rerun because no runtime code changed. No paid
run, private acceptance evaluation or general capability claim was produced.
