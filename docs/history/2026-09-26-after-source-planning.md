# First plan after source

Date: 2026-09-26. Implementation and provider-free verification record;
not a paid experiment, default adoption or performance claim.

## Problem, evidence and hypothesis

The closed [planning ON/OFF comparison](2026-09-26-planning-off-comparison.md)
found acceptance 0/4 with brief-v1 and 2/4 with planning OFF, confined to Pydantic.
Both ON runs narrowed the applicability of the repair in their initial public plan,
before observing source. The experiment toggled the entire explicit-planning feature;
it did not prove that the first plan caused the later scope error. HF Hub failures
and verification selection did not improve with planning OFF.

Hypothesis: requesting the first plan only after a source observation may avoid an
early commitment while retaining later coordination. This needs a fresh comparison
with brief-v1 at the same runtime; it is not a diagnosed cause or guaranteed repair.

## Change and boundaries

Opt-in `brief-after-source-v1` replaces only brief-v1's initial timing instruction
and defers review requests until a successful read/search returns nonempty source
text. The initial segment does not bypass the deferral. Empty searches, failed reads,
EOF or output truncation without a source body do not activate planning. Returned
search snippets count without claiming semantic sufficiency.

The next model response receives the initial request; a null annotation leaves it
pending. Voluntary early plans remain accepted. Subsequent whole-text replacement,
mutation/check/probe/ready/handoff review, invalid annotations and exact replay use
the existing mechanism. Durable public tool results supply the timing condition
through resume and segment transitions; no extra state or source read is introduced.

CLI, request, envelope and evaluator manifest accept the new policy. Its review and
instruction identity differ; old policy contracts and ordered tool schemas stay exact.
No task-specific hints, new templates, mandatory review/probe, tool mask change,
completion gate, segment transition change or automatic live execution is included.
CLI defaults and the selected brief-v1 working baseline remain unchanged.

## Validation and result

Runtime content identity: `9320c697313e8340762a3fe48eb8717ef547e95a3696354d7fdad9d90d9935c6`.
Receipts: `C:\pt\validation\after-source-planning-20260926-v1`.

- Quick contract checks: 15 PASS / 4.52s wall time. They cover initial deferral,
  empty/failed observations, read/search activation, persistent requests, voluntary
  early plans, later review behavior, identities, schemas and CLI/context options.
- Expanded group: 20 PASS / 164.85s wall time, including actual input comparisons
  in append and segmented modes plus three crash/recovery boundaries. This combined
  group exceeded the two-minute focused target; the quick selection is documented
  separately, without reducing integration coverage.
- Ruff over runtime/tests/diagnostics and `git diff --check`: PASS.
- CLI mock smoke: acceptance PASS, safety NOT_RUN; 4 model decisions, 5 tools,
  1 accepted mutation, 2 segments, zero recorded cost. All four saved actual inputs
  passed the existing public-state audit. Before source, review is not requested;
  after source it is requested, with plan revisions `null, null, 1, 2` across inputs.
  Public task/diff/check delivery, submission and isolated smoke evaluation remain intact.
- All four existing planning/tool identities and 848 protected historical file hashes
  match the pre-change snapshot. No historical artifact or old envelope was rewritten.
- Full regression: 158 files / 3,435 cases, with `--durations=20`, split across four
  pytest processes with separate external state roots. Result: 3,412 PASS, 7 FAIL,
  16 SKIP in 7,642.49s wall time (127.37 minutes). Runtime/test/diagnostic source
  hashes stayed fixed throughout. The original broad run remains recorded as failed.
- All seven failed cases passed unchanged-code rechecks: four individual runs during
  the sweep, then the remaining three in one sequential pytest process after every
  sweep worker exited. No assertion, deadline, cleanup guard or runtime code was
  relaxed. Final documentation checks passed as recorded in `docs-final.json`.

The first CLI verification command mistakenly targeted `python -m patchloop`, which
has no package entry point. It stopped before a run began; the corrected
`python -m patchloop.cli` command produced the successful smoke receipt. Both command
receipts are retained. This is separate from the regression failures below.

### Whole-regression failures and rechecks

None of these existing tests enables `brief-after-source-v1`. Exact node IDs,
tracebacks and timings remain in `full-*.xml` / `full-*.log`; `verification.json`
summarizes the original sweep and the isolated rechecks separately.

| Existing test | Observed original failure | Passing recheck receipt |
|---|---|---|
| Counterexample discovery, original guidance | TOOL_EXECUTION_UNCERTAIN after an admitted probe, without a finished action | `diagnose-1.json` |
| Public check feedback privacy | ExecutionDeadlineExceeded during post-check Git diff inspection, before the context assertions | `diagnose-2.json` |
| Repair/recheck recovery, child admitted | LIMIT_REACHED on the resumed run | `diagnose-3.json` |
| Mutation recovery, before admission | LIMIT_REACHED with active execution deadline exhausted | `diagnose-4.json` |
| Pending scope rollback, baseline hash | ExecutionDeadlineExceeded while inspecting the restored Git diff | `diagnose-5.json` |
| Pending scope rollback, CRLF source | GitExecutionUncertain during the recovery diff lookup | `diagnose-5.json` |
| Local subprocess partial-output capture | No first output within the test's 0.3-second timeout | `diagnose-5.json` |

The discovery journal stops about 5.77 seconds after probe admission; the existing
post-probe recovery read has a five-second limit. Its missing exception detail means
that deadline explanation remains an inference. The other original exceptions above
are recorded directly. Parallel load is consistent with the timing symptoms and
passing rechecks, but its causal role was not isolated. These results verify the new
option's local contracts while leaving the broad sweep's execution-stability caveat
visible; they do not establish a clean first-pass regression run or an efficacy gain.

## Remaining question

Does delayed planning change repair scope, verification choice and acceptance on
fresh solves? A successful authored mock plan proves delivery, not useful reasoning
or better task solving. No provider/count request, Docker startup/pull/build, hidden
evaluator inspection or new paid allocation belongs to this implementation. The
prior $9.60 group's unused funds stay closed; no retry, extension or automatic resume.
