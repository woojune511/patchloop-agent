# C2 fourth-edit choice: two live continuations

Date: 2026-10-04. Both approved continuations completed; allocation closed.
Public paired success: 0/2. Keep the baseline. No further run is authorized.

## Question and fixed scope

The [operator investigation](2026-10-04-sqlfluff-c2-regression.md) established that
C2 recognized the output mismatch and that a within-four-edit public repair path
exists. The remaining question was whether the unchanged historical C configuration
would autonomously choose a fourth edit satisfying both the issue and public
regression. This evaluation tested that choice, not recognition or a new policy.

The user approved the [prepared scope](2026-10-04-c2-choice-preparation.md): two
independent continuations of registered dev-train SQLFluff-1733 from the identical
edit-3 prefix, before the next input count. Model gpt-5.4-2026-03-05, xhigh, desired
output ceiling 25,000; each allowed 26 additional calls, 73 actions, one accepted
edit, 970.510 active seconds and USD 1.4345025 newly funded usage. Total cap was
USD 2.869005. Historical spend remained bookkeeping, not a new charge.

Execution commit: 93ab47d6e14f22bbb93eb00ea029cfc4e146fab2.
Manifest hash:
sha256:b92ff3300b3cb6cb623036ffe5de7c90d3f2ed690d1b34214cd6fdf8f97f54f6.
Both first wire requests exactly matched the frozen original request; all 238
source-prefix events were retained verbatim. The original C guidance, native
segment state, saved program and automatic recheck policy remained unchanged.
No operator correction, later regression result or retrospective edit-3 PASS
was supplied. Repetition 1's result was not passed to repetition 2.

## Results

| Continuation | Issue full output | Public regression | Original acceptance / safety | New calls / actions / edits | New USD | Solver active seconds | Post-run public seconds |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| live1 | PASS | 504 PASS, 2 FAIL | NOT_RUN / NOT_RUN | 5 / 8 / 1 | 0.8495815 | 427.984 | 39.409 |
| live2 | PASS | 504 PASS, 2 FAIL | NOT_RUN / NOT_RUN | 4 / 9 / 1 | 0.6267640 | 359.925 | 44.345 |

Both ended LIMIT_REACHED after the registered regression failed with no accepted
edits remaining. Neither submitted. Their hidden acceptance is unexecuted, not
FAIL. The stopping resource was the edit completion horizon, not exhausted model
calls, money or wall time. New billed usage totaled USD 1.4763455 across nine calls;
solver active time totaled 787.909 seconds. Post-run operator checks used a separate
83.754 seconds, within each frozen 120-second allowance. Solver process wall times,
including final bookkeeping, were 428.119 and 360.072 seconds respectively.

Each final candidate was unchanged across the independent issue-output program
and registered base-regression execution. Both produced the issue's eight-space
output and failed these existing public cases:

- L036_test_multiple_select_targets_some_newlines_missing_1
- L036_test_multiple_select_targets_some_newlines_missing_2

Final diffs:

- live1: sha256:fcd8ecd44c3ee2e15d75390350b276cc15730498630faf3c8db5e20d2901982c
- live2: sha256:5ead512bfdc00b9ac0d3e80036a352677e42a31ba1ba2a83cefb1fec55c7c9fa

## Observed choices and bounded conclusion

live1 first ran an additional public probe, then inspected source. Its fourth edit
copied existing post-newline whitespace in L036 whenever such whitespace existed.
live2 inspected source without a new manual probe; its edit also required the
whitespace to precede the final select target. Both retained the earlier L003 edits.
Both auto probes produced the desired issue output before registered regression.

These conditions still applied the indentation copy too broadly in mixed-line
select lists. The added position condition in live2 did not separate the public
cases requiring preservation. The agent selected a relevant location and corrected
the target output, but neither tested choice supplied an adequate scope condition.
This is new autonomous-choice evidence on the exposed checkpoint; operator repair
success remains a separate result.

The failed registered regression was followed by a completion-horizon stop, with
no further model dispatch. Do not characterize these traces as the model ignoring
the failed regression or failing to repair it after receiving another opportunity.
The effect of a fifth edit, and autonomous narrowing after regression feedback,
remain NOT_ASSESSED. No recognition diagnostic, stronger gate, prompt intervention
or general performance claim follows from this two-choice result. The allocation
is closed without retries, replacement runs, resume or transferred budget.

## Evidence and verification

Preparation, manifest and human authorization:
C:/pt/analyses/c2-choice-prep-20261004-v1.
Live workspaces/journals: C:/pt/c2cp01/live1 and live2.
Allocation evidence: C:/pt/c2cp01/allocation.

result.json retains both outcomes, same-candidate public receipts and separate
timings. live1.diff/live2.diff preserve the final patches. audit.json binds the
result and allocation journal hashes. audit-live.py verifies exact inherited
prefixes and first inputs, matching counts/dispatches/settlements, unique completed
actions, unchanged final candidates, complete public outputs and resource limits.
All nine new calls settled; historical spend was not charged again. No count,
transport, billing, cleanup or identity uncertainty occurred. Source records and
user AGENTS.md bytes were verified unchanged. Existing images only were used.

Closeout changes documentation only. Documentation layout/link tests, Ruff and
diff checks are appropriate; the full fast suite and separate mock smoke are not
repeated. Live public executions establish the table above, not hidden acceptance.
