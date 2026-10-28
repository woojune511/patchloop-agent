# Saved SQLFluff candidate: public indentation failure is unchanged

Status: LOCAL_TARGET_EXECUTED, AUDITED. Two target executions, zero model calls.
All evidence is official=false and claim-ineligible. This is a separate follow-up
to the closed [live result](2026-10-29-edit-prerequisite-single-results.md).

## Question and controlled replay

The user requested the same public SQL on the saved candidate and original to
check whether the indentation was actually repaired. The preceding run passed
506 public regression tests and submitted but failed independent acceptance. Its
only public-example helper ran before the edit. Checking the saved candidate is
the smallest diagnostic that distinguishes a remaining reported failure from a
candidate that fixes that example but fails elsewhere.

Replay used dev-train current-dev20/18, task
`swebench-lite-dev-sqlfluff-sqlfluff-1733`, on original commit
`a1579a16b1d8913d9d7c7d12add374a290bcc78c`. Two fresh local workspaces used the
same source, prepared dependencies, pinned probe image and original helper.
Only the saved submitted patch was applied to the candidate. The helper invokes
`sqlfluff.fix(sql)` with defaults on the public WITH example; its source and input
were extracted from the saved action and checked against the public task. Expected
SQL came from the public issue's Expected Behaviour, with line endings normalized.
There was one execution per condition, no retry, a 30-second per-target ceiling,
and a 240-second whole-script ceiling. No new instrumentation or repair was added.

Host checkout was `57ee4ff5`; runtime hash was unchanged at
`sha256:8eb3e389ce20f0b9143c330a3dae3dbd9fcca65f8f0b1ad5d1f5c6dc6a621cfb`.
Original source-run manifest and all 29 sealed bindings were verified. The new
replay used explicit user authorization; it did not reopen the paid allocation.

## Observed result

| Measure | Original | Saved candidate | Public expected |
| --- | --- | --- | --- |
| Spaces before `my_id` | 9 | 9 | 8 |
| Spaces before `other_thing` | 8 | 8 | 8 |
| Spaces before `one_more` | 8 | 8 | 8 |
| Whole SQL matches expected | No | No | Yes |
| L003 repeated-fix warning | Present | Present | Not an acceptance criterion |
| Helper exit code | 0 | 0 | Execution health only |
| Timeout / truncation / cleanup failure | None | None | None |

Both full stdout and stderr exactly matched the saved pre-edit observation as
well as each other. The SQL output files are byte-identical, with hash
`sha256:51ef111354495993b42ba4c3913703be9d717e79d01536201fa1dd377078cfc8`.
Both retained `One fix for L003 not applied, it would re-cause the same error.`
The original snapshot matched the saved helper snapshot; the candidate snapshot
was different. The candidate diff before and after execution matched the submitted
patch hash, confirming that the comparison actually included the intended edit.

Verdict: **PUBLIC_EXAMPLE_NOT_FIXED**. The saved patch does not fix the reported
extra space in this same API/helper environment. Successful helper execution is
not behavioral success. The previous 506-test PASS was insufficient for this
concrete public example; that suite was not repeated during this replay.

## Decision and limits

The immediate uncertainty about candidate behavior is resolved. The model's edit
was insufficient even for its own observed public input. This supports examining
candidate verification coverage and the interaction producing the extra space;
it does not justify increasing resources or exposing more tools on its own.
Keep the existing runtime, submission-policy default and budgets unchanged here.

The next unresolved code-level question is whether the edited L036 branch ran and
why its whitespace change did not change the final output. Identical output does
not establish branch nonexecution. The helper's later segment walk parsed the
original SQL, not the transformed output, so it cannot answer that question.
No new trace or repair was attempted. This API replay does not establish full CLI
equivalence, the exact hidden-test failure cause, or general repair quality.

This was a post-submission operator replay. Its results were not given to the
model and cannot be retroactively counted as model verification. Independent
acceptance remains the prior FAIL; no private evaluation was rerun or inspected.

## Evidence and boundaries

External evidence: `C:/pt/sqlfluff-public-replay-v1/` contains `replay.py`,
`setup.json`, `helper.py`, `input.sql`, `expected.sql`, `submitted.patch`,
`summary.json`, and the empty `output.diff`. Each of `baseline/` and `candidate/`
contains the request, receipt, raw stdout/stderr and extracted `fixed.sql`.
Execution state is the append-only, hash-chained
`runs/run_dev_sqlfluffpublicreplayv1.jsonl`, with action/input identities.

- Original run: `run_dev_d5806f63861b47e6` under
  `C:/pt/edit-prerequisite-single-run-v1/18-B`.
- Original helper action: `call_5oLtz1MjhQUvp7K37V2SO48p`.
- Helper source: `sha256:42cd2a2949a936da828a20895b1321427b9ef1e6e785645b837d33d489f7ae4d`.
- Submitted patch: `sha256:d3022a59756dfb1c7ad44b9b2c063306a384e147f78c9f0a0194d3fc560bfe62`.
- Probe profile: `sha256:b429a023997ea2f86d42bcd1389ed8bbb866d1d5cc6280c4b714214a2bb0417e`.
- Probe image: `sha256:3b37b00de42a063f990e9b55d3918bb0a64cf5ec533a79e9650ca3ce9ccbe3b1`.

The already-running Docker server and existing image were reused without pull or
build. No credentials, paid API calls, private test contents or reference patches
were used; API cost was USD0. Historical artifacts were not changed. No runtime
code was modified. Documentation validation: `tests/test_documentation_layout.py`
passed 5 tests in 0.17 seconds; `git diff --check` passed. Its XML receipt is
`documentation-tests.xml` in the replay evidence root. Target health and behavior
are recorded above; no broader regression or mock suite was needed for docs only.
