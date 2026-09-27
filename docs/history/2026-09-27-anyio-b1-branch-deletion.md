# AnyIO B1: removal of the extra cancellation branch

Date: 2026-09-27. Follow-up to the
[evidence/action audit](2026-09-27-anyio-evidence-action-link.md).
Operator-selected patch-component experiment, `official=false`,
`claim_eligible=false`. No model calls or private evaluation.

## Question and intervention

B1 both repaired the shared runner loop and added `except CancelledError: raise`
in `run_test`. Its original explanation partly attributed ordinary cancellation
failure to the helper called by the broader `BaseException` handler. The earlier
seed trace instead showed that helper returning before issuing another cancel.
Successful combined repairs did not establish that the extra branch was needed.

Two fresh local clones used the same prepared base commit. Both received B1's
hash-verified submitted patch. Only the second then deleted these two lines:

```diff
-        except CancelledError:
-            raise
         except Exception as exc:
             self._exceptions.append(exc)
         except BaseException:
             self._cancel_current_call()
             raise
```

The runner-loop repair and all other source remained fixed. Both resulting full
patches and their two-line intervention diff are stored in the new packet. Existing
candidate workspaces, submissions and historical records were not changed.

## Execution and results

Order: B1 control, then B1 without the branch. Each ran the exact existing public
probe once and both registered public checks once. Control failure or any timeout,
truncation, identity or cleanup uncertainty would stop the experiment without retry.

| Observation/check | B1 control | B1 without branch |
| --- | --- | --- |
| Runner survives ordinary cancellation | Yes | Yes |
| Cleanup starts/completes once in original task | Yes | Yes |
| Cancel handler/finally once; no post-cancel continuation | Yes | Yes |
| `interrupt-lifecycle-contract` | 7 passed, 0 failed | 7 passed, 0 failed |
| `upstream-pytest-plugin-regression` | 32 passed, 3 deselected | 32 passed, 3 deselected |

The control's probe snapshot matched its previous replay. All six owned containers
were confirmed absent. No execution timed out or truncated; full declared timeouts
remained available. The probe catches exceptions, so its exit zero means diagnostic
completion; the behavior assessment above comes from emitted state and task IDs.

The collector also discriminated the changed path. Control entered its explicit
`CancelledError` branch (2355-2356). Without it, the broader exception handler
(2357-2359) called the helper; lines 2298/2300 read and test `_call_future`, and
2305 returns. Its pending-count increment and runner cancellation (2307-2308) were
within the measured changed-line scope but not observed. Thus the branch removal
changed exception routing while leaving the observed behavior intact. This is
launch-thread Python line-entry evidence, not complete branch coverage.

## Interpretation and limits

The additional branch is unnecessary for these measured behaviors with B1's
runner-loop repair present. This is stronger than comparing independently generated
patches: the new pair differs only by the two-line removal. It supports the prior
helper-path correction and narrows the original repair explanation.

It does not establish all-state equivalence, necessity of each remaining runner-loop
line, repeated/concurrent cancellation behavior, post-context-exit behavior, or
private task acceptance. The operator selected this deletion and the verification
cases; no autonomous diagnosis, patch-minimization skill or general harness quality
improvement was measured. Historical B1 remains the originally submitted candidate.

This closes the specific extra-branch question at the public-check/probe scope.
No prompt, memory, runtime or default change follows. A future harness comparison
must choose a separate causal question and matched inputs; removing a patch branch
is not an ablation of completion guidance. The existing status-only diagnostic's
feedback restriction still prevents an unmatched reuse of the prior A/B as controls.

## Environment and evidence

Both arms used existing images, without daemon startup, pull/build or network fetch:

- Base commit: `cb245dba9883516f2ed4c23899de157183a1cb50`.
- Probe image: `sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
- Probe dependency manifest: `sha256:ae8d0a01dd8c67305ea620a885a75c73344979104f6d067e83dc3aebc79f143e`.
- Probe profile: `sha256:df3a7c7097f2c964d74f53c7d0b2c2c2b1a6d5c6e0d40f77c3d1ed678e650e01`.
- Registered-check image: `sha256:063bb968109c70a3fe617d9d30287a3a43d549eb1091b27a030a9af2a74c2320`.
- Original B1 patch: `sha256:82222e9665213b89293a6a728fc7a6301128e7cb6b53d0d2111c077da73b3844`.
- Branch-removed patch: `sha256:6255554a6453492e1a85325e1fee5e9b6ef12e0e6894019d8961bcd830c43f8e`.

Packet: `C:\pt\analyses\anyio-b1-branch-deletion-20260927-v1`. It contains the
script, fixed plan and inputs, environment admission, both patches, intervention,
six execution receipts, results and closure. The 17-event `dev-run-v1` journal
verified, 39 protected input/history files were unchanged, and the runtime hash
remained unchanged before the documentation follow-up.

Probe execution limits were 30 seconds, with 120 seconds per operator probe row.
Registered checks retained their 120/90-second limits, each with 30 seconds extra
operator allowance; the group cap was 900 seconds. There was no retry or partial arm.

Operator-script Ruff, five documentation layout/link tests and Git whitespace
validation passed. No PatchLoop runtime code changed; its full regression suite
and mock smoke were not rerun. Private acceptance remains `NOT_RUN` for this pair.
