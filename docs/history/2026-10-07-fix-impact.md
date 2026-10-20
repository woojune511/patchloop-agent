# Recent bug fixes and agent-performance relevance

Date: 2026-10-07. Read-only implementation/trace audit at
`71015696a720523dfc05937197ebb9cf9b68b5eb`, followed by documentation only.
No provider, new task solve, probe or evaluator execution. Existing paid allocations
remain closed. Source changes are not themselves task-success measurements.

## Question and scope

The user asked whether recent bug-fix commits could materially affect agent
performance. The important distinction is a fix's consequence when its trigger
occurs versus evidence that the trigger occurred in the measured failures.
The review covers the latest two runtime fix commits, the checkout/diagnostic fixes,
and two earlier fixes with particularly direct execution-budget evidence.

Checked source and regressions, then audited 24 retained public run journals:
20 corrected dev20 rows, two search-supplement rows and the two latest SQLFluff
counterexample episodes. This is not 24 completed solves: the first group retains
its original interrupted/NOT_RUN rows. All 20 current public task registrations
were checked separately. Private evaluator semantics and raw model reasoning were
not inspected.

## Mechanisms and observed relevance

| Commit and change | Consequence when triggered | Evidence in the reviewed runs |
| --- | --- | --- |
| `345d24b3`: journal LF framing | Unicode line separators inside valid JSON no longer break event replay; incomplete final records are rejected before another append | No raw U+0085/U+2028/U+2029 or missing final LF in the 24 journals. Important recovery integrity, not an observed explanation for these failures |
| `345d24b3`: unique check IDs | Prevents different registered commands sharing one check identity and corrupting completion accounting | All 20 current task registrations already have unique IDs |
| `345d24b3`, `71015696`: Git path decoding and literal lookup | Non-ASCII/quoted filenames can be edited and submitted correctly; bracket filenames are not interpreted as patterns; an untracked lookalike cannot satisfy a tracked lookup | No matching unusual read/mutation paths or changed-file paths in these journals |
| `71015696`: changed-line feedback paths and relative script identity | Correctly attributes execution to changed paths, including scripts that change working directory | Current dev20 checks all use unsupported Python options, so the relative-script fix does not enable their registered-check tracing |
| `71015696`: shared panel ledger restoration | Adds native-compaction usage to the invocation total exactly once; preserves row accounting on invalid restoration | Zero compaction events in the 24 journals. This repairs budget/report correctness, not a demonstrated repair-quality gain |
| `71015696`: durable safety evidence validation | Missing or corrupted leaf safety evidence cannot be accepted when finalizing a saved evaluator result | No resume events in these runs. Changes recovery validation after solving, not the model's repair decision |
| `27d10acc`: preserve current-dev20 bytes in Git | Clean checkouts retain the bytes required by the existing package inventory hashes | Directly unblocked the isolated preparation; existing primary task bytes and semantic content were unchanged |
| `d8fb98fd`: separate fresh entry from repeated admission | A collector can revalidate its environment after creating its own output folder | Directly unblocked the latest diagnostic before its first model call; does not modify the ordinary solver |

Implementation references: [journal](../../patchloop/dev/state.py),
[task admission](../../patchloop/contracts.py), [Git paths](../../patchloop/repository.py),
[tool lookup](../../patchloop/dev/tools.py),
[line feedback](../../patchloop/sandbox/execution_feedback.py),
[script tracing](../../patchloop/sandbox/line_trace.py),
[panel accounting](../../patchloop/dev/panel.py),
[evaluation recovery](../../patchloop/dev/evaluation_completion.py).

The [latest A/B](2026-10-07-counterexample-results.md) already included `345d24b3`,
`27d10acc` and `d8fb98fd`. It predates `71015696`, so that newest commit has not had
a fresh quality measurement. Its fixed trigger paths were absent from the A/B:
both used ordinary ASCII paths, no compaction or recovery, and unsupported-option
check launches. The observed current-counterexample delivery and voluntary early
submission therefore remain relevant; no reviewed fix supplies a mechanism that
would directly reverse those decisions.

## Execution feedback limitation

Every current-dev20 visible check starts Python with `-B -c ...`. The trace wrapper
accepts `-c`, `-m`, or a script as the first Python argument; `-B` produces
`unsupported_python_options` under the explicit current contract. In the recorded
public tool results there were 37 such file observations and one collected file
observation across the 24 runs. These are file-level diagnostic entries, not 38
tests or task outcomes. All 20 current registrations were independently confirmed
to select the unsupported-options branch.

The public check launcher also copies the source into a temporary tree and runs
pytest in a child process. Merely admitting `-B` would not establish target-source
coverage: the current tracer observes the launch thread, not arbitrary children or
copied paths. Thus the latest filename fix is valuable but does not remove this
benchmark's instrumentation limitation. This is declared unknown coverage, not a
false execution PASS or a newly proven cause of incorrect patches. In the latest
B episode the actual behavioral failure was already delivered independently.

## Earlier fixes with stronger performance connections

`a28aa364` removes one Git process per searched file. The
[search investigation](2026-10-06-search-once-supplement.md) compared identical
outputs on a 128-file workspace: an absent query used 128 versus one Git call and
10.047109 versus 0.067195 seconds. Earlier real SQLFluff searches consumed hundreds
of seconds; all 36 search intervals in the later two-task supplement were below
0.74 seconds. Query sequences differ, so those live runs are not a controlled
latency A/B, but the mechanism and large avoidable overhead are established.
Both supplemented tasks completed evaluation and failed acceptance. Keep the
performance fix without attributing a correctness improvement to it.

`e55393ed` corrects [completion reservations](2026-10-06-resource-budget-context-review.md):
an automatic recheck consumes a tool action without consuming a model call. The
same protected path changed from eight to seven model calls while still reserving
eight tool actions. A saved public state with eight calls remaining consequently
gained one optional model turn. This can affect boundary decisions; it does not
prove that the newly available turn will be useful. The latest A/B already had
39 calls and three edits available when it chose to finish, so this correction
does not explain its early submission either.

## Decision, validation and evidence

Keep the fixes. They address reproducible execution, portability, budget and evidence
integrity defects. Do not infer an agent-success gain from their count, their test
results, or their size. The strongest observed speed/admission benefits are search
enumeration, resource reservation and preparation correctness. The latest two
runtime commits principally protect conditions absent from the examined failures.
They do not alone justify another paid twenty-task rerun or a new default policy.

The next quality intervention still needs a mechanism connecting observed failed
verification to actual patch revision. If changed-line feedback is considered,
first validate the real `-B -c`/copied-source/subprocess boundary provider-free;
path-only regression tests do not establish that capability. This is an unexecuted
conditional investigation, not a new queued experiment or permission to change it.

External evidence: `C:/pt/analyses/recent-fix-impact-20261007-v1/trigger-audit.json`
binds all 24 source journals and 20 public task files by hash. The append-only
`runs/run_dev_recentfiximpact.jsonl` records the audit. The source journals were
loaded through their hash-chain verifier without alteration. Existing outcome
records remain unchanged. The six relevant regression files passed 109 tests in
232.00 seconds (`C:/pt/recentbugaudit01.xml`); this broader contract audit exceeds
the two-minute target for a small focused check. Documentation tests passed 5/5
in 0.14 seconds (`C:/pt/bugimpactdocs02.xml`). Receipts are bound at closeout;
full-suite, new live quality evaluation and publication remain NOT_RUN.
