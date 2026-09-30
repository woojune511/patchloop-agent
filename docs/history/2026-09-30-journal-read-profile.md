# Journal read cost: bounded mock profile

## Problem and frozen decision

`DevJournal.events()` reads, parses and validates the full hash chain. Append and
several current-state helpers call it repeatedly. Repeated reads are observable in
source; their contribution to execution time was unmeasured. Possible causes of
slow execution include journal validation, Git/subprocess work and other runtime I/O.

The provider-free protocol used one csv-quoted-newline smoke task: three normal
runs, one interruption before the mutation result receipt followed by resume, and
one terminal resume. Settings were mock-dev, segmented-v1, brief-v1 and
repair-recheck, with probes disabled. No live provider or Docker work was requested.
The decision rule was frozen in the evidence journal before execution: consider
reuse only if the normal-run median repeated non-append read time reaches both
1 second and 10% of invocation wall time.

## Measurement

[The diagnostic](../../diagnostics/journal_read_profile.py) wraps `events()` without
changing its validation or return value. Its timer surrounds the original call;
file-size sampling, caller attribution and counters are outside that timer. Raw
rows retain the last verified event hash, latest recorded turn, three caller frames,
logical file bytes and elapsed time. They are stored after each invocation, outside
the measured interval, as hashed artifacts referenced by a dev-run-v1 journal.

Logical bytes mean the journal size at each read, not physical disk traffic.
Repeated-prefix time includes only non-append calls whose verified tail hash has
already been seen in that invocation. Removing all such calls is an optimistic
upper bound for this particular reuse opportunity, not an implemented optimization
or an upper bound on every possible incremental-state design. Append validation
remains separate. Turn attribution uses the latest *recorded* turn, so a read before
a new turn event is appended belongs to the preceding recorded boundary.

Base: `9880633a63993f12ba02a4edb4ef2a2bde0e5c6e`, Windows, local Python 3.14.
Observer bookkeeping took about 10 ms per normal invocation, in addition to the
reported read/validation time. Wall times are instrumented and environment-specific.

| Invocation | Reads | Logical MB | Wall seconds | Read/validate seconds | Repeated non-append seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Normal 1 | 168 | 6.386 | 7.135 | 0.374 | 0.0758 |
| Normal 2 | 168 | 6.386 | 7.613 | 0.375 | 0.0770 |
| Normal 3 | 168 | 6.386 | 7.998 | 0.365 | 0.0737 |
| Terminal resume | 1 | 0.086 | 0.039 | 0.00135 | 0 |
| Interrupted before mutation receipt | 82 | 1.186 | 3.406 | 0.145 | 0.0249 |
| Mutation receipt resume | 115 | 6.463 | 4.721 | 0.263 | 0.0728 |

For normal run 1, the 168 reads partition by latest recorded turn as follows:

| Recorded boundary | Reads | Logical bytes | Read/validate ms |
| --- | ---: | ---: | ---: |
| Before first turn | 35 | 54,924 | 21.603 |
| Turn 1 | 37 | 779,314 | 80.229 |
| Turn 2 | 35 | 1,493,345 | 77.298 |
| Turn 3 | 38 | 2,287,656 | 99.946 |
| Turn 4, including finalization | 23 | 1,770,798 | 94.613 |

Across normal runs, append made 49 reads and consumed 189-196 ms. Other visible
callers included `action_result` (five reads, 30-32 ms), `_record_planning_decision`
(four reads, 20-21 ms), `segments.is_fresh` (ten reads, 16 ms), and
`_tool_policy_transition` (four reads, 14-15 ms). Raw artifacts include all callers
and turn buckets for the interruption and resume invocations as well.

## Result and decision

Normal median repeated-prefix non-append cost was **0.0758197 seconds, 1.0113%** of
wall time. The frozen threshold was not met. Keep runtime journal validation and
state construction unchanged; add no cache or RunState in this change.

All three normal runs and the interrupted/resumed run reached isolated acceptance
PASS with the same submitted patch, one accepted mutation, four mock model calls
and five tool actions. Resume retained the original journal prefix and one mutation
result; terminal resume returned the same result without changing journal bytes.
Every final chain was revalidated outside instrumentation. Safety was NOT_RUN,
cost was zero, and all runs were official=false. These are mock consistency results,
not live repair-quality evidence.

This closes the short-smoke measurement only. Long journals, large tool payloads,
Linux timing and live model latency were not measured. A future optimization needs
evidence from an actually slow execution with its journal size and safe reuse scope;
the present result neither establishes nor rules out that bottleneck.

## Evidence and reproduction

Local evidence: `C:/pt/analyses/journal-read-profile-20260930-v1/summary.json` and
`runs/run_dev_journalprofile.jsonl`, with six hashed raw measurement artifacts.
Summary SHA-256: `e4581516a4f24f1ac534fc6e82b67e639497ea9ea5720f734cfcd2cd96af39c3`.
Diagnostic source SHA-256: `32584416b638f46b1ad2e9c017f040603fc34e12ae5287db711dec235b12a7d4`.
Caller and turn aggregates were independently reconciled to every raw row.

Reproduce with a **new external output directory**; the command refuses to overwrite
an existing directory and has no live-provider option:

```powershell
uv run --locked python -m diagnostics.journal_read_profile --output C:\pt\analyses\journal-read-profile-new
```
