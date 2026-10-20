# Failure-to-source navigation across five saved tasks

Date: 2026-10-08. Provider-free public trace audit; official=false.

## Question and selection

The preceding [ownership diagnosis](2026-10-08-rule-ownership.md) found two
unsuccessful literal searches for a generated pytest ID in SQLFluff-1733. Before
adding navigation guidance or an ID resolver, determine whether this friction
recurs across tasks and whether the current tool contract is defective.

The leading hypothesis was that generated failure labels hide the actual fixture
source. Alternatives were that relevant source was already available, direct
locations were sufficient, or the repair inference remained wrong despite useful
evidence. Successful navigation after a public failure weakens a general interface
explanation; it does not establish original-task correctness.

Five tasks were selected deliberately, using the existing
[trace inventory](2026-10-06-agent-trace-comparison.md): the SQLFluff-1733 anchor;
SQLFluff-1625 with the same generated YAML-ID family; and Pvlib-1707,
Astroid-1196 and Pydicom-901 with public failures in three other projects.
These are mixed historical runtimes and a purposive sample, not a prevalence
estimate or controlled agent-performance comparison. Preliminary reads informed
selection; the five journals were bound before the saved extraction.

## Observations

Sequence numbers below belong to each original journal, not to a new execution.

| Task and saved run | Failure to next action | Public outcome |
| --- | --- | --- |
| SQLFluff-1733, thin row 8 | Check 294 names `L036_test_multiple_select_targets_some_newlines_missing_2`. Searches 307→308 and 320→321 repeat that literal string: zero spans from 1,541 files. Second result is cached and marks stagnation. | Later edits recover the 506-test regression suite; original CTE correctness is separate. |
| SQLFluff-1625, corrected row 17 | Check 133 exposes six failures, including generated L031 IDs. Fixture had already been read at 50 and 79. Search 148→149 finds `join_clause` in the modified rule; repair follows. | 6 FAIL/494 PASS becomes 500 PASS, one deselected. |
| Pvlib-1707, corrected row 5 | Check 91 names `pvlib/tests/test_iam.py:81`, with float64 actual versus int64 expected. Added test was returned at 76. Next action 106→107 changes expected values to floats. No searches in the run. | 1 FAIL/30 PASS becomes 31 PASS. |
| Astroid-1196, corrected row 11 | Check 181 names test line 284 and implementation line 2376. Test and owning method had been read. Next action 195→196 adds `continue`; no postfailure read/search. | 1 FAIL/1,290 PASS becomes 1,291 PASS; 76 skipped, 14 xfailed. |
| Pydicom-901, prior row 10 | Check 59 reports missing `config.debugging` at `filereader.py:828`. Search 74→77 returns three relevant spans; parallel reread 75→76 opens config. Edit 91→92 restores the sentinel. | 9 FAIL/86 PASS becomes 95 PASS; one skipped. |

These are saved public regression outcomes, not five new evaluations or five
successful task repairs. In particular, correcting an introduced regression or a
test's dtype expectation does not establish complete issue coverage.

### The concrete SQLFluff mismatch

The actual key is `test_multiple_select_targets_some_newlines_missing_2` at
`test/fixtures/rules/std_rule_cases/L036.yml:80`. Lines 86–88 explain why existing
indentation is preserved. `src/sqlfluff/testing/rules.py:45` constructs IDs by
joining the rule, underscore and YAML key; the pytest wrapper consumes those IDs.
The searched full ID is therefore not the fixture key.

Both failed searches share input hash
`sha256:441c485dc4f3ad466fd0d2bda44ef2c84b6e3bb95b6fa0cba4f2f5b0bf80ba01`.
Their action IDs are `call_Y0MAUSLQ8PXluR0cjcK9goFf` and
`call_UB1h9FhvQe66K9Vbzo1LjVAJ`. No fallback fixture read follows; the agent instead
reads L003. This is an observed navigation miss, not a failed literal-search
implementation. Current `search_files` documents literal matching and performs
that matching directly; no automatic prefix interpretation is promised.

The failed check also supplied the complete `RuleTestCase` input/expected strings
and the `a,` versus `  a,` mismatch in the next request, sequence 298. Capture was
not truncated, although pytest itself elided part of its pretty comparison.
The missed fixture comment may have helped interpretation, but an absent public
counterexample is not the finding. No experiment measured whether avoiding these
two searches would change the final patch.

### Delivery and mapping boundaries

- SQLFluff-1625 request 137 retains L031.yml lines 1–170 and the failed check.
  The same generated-ID format did not prevent this trace from finding its fixture.
- Astroid request 184 retains the failed check, test lines 260–300 and candidate
  implementation lines 2345–2394. Source delivery is established, understanding is not.
- Pydicom requests 63 and 81 retain the failure and subsequent source results.
  Failure capture was truncated, but the relevant exception, locations and summary
  survived; no navigation impairment was observed.
- Pvlib evidence establishes journal-returned mutation source and failure output.
  Its next request was not inspected; do not claim request-level retention from it.

The checks can report `mapping_status=unmapped` while stdout names useful files
and lines. This field concerns the narrower inline-source mapper. It is not a
general statement that the agent lacks the failure location.

## Decision

Only the SQLFluff-1733 anchor exhibits this repeated generated-ID search miss among
the five selected traces. No current search/delivery contract violation was
reproduced. Lower the priority of a general navigation intervention and preserve
the baseline. Do not add a SQLFluff-specific normalizer, another generic prompt,
or an automatic-test policy on this evidence. Their benefits are unmeasured,
not disproved.

The previous ownership diagnosis remains the stronger explanation for SQL1733:
the agent assumed a helper change covered the full behavior and did not establish
that the original reproduction survived the later regression repair. The operator
L039 patch is a public repair control, not an autonomous agent improvement. This
audit changes the navigation priority; it does not justify another adjacent A/B.

A future navigation change needs a concrete failing tool/delivery contract or
additional evidence connecting the missed location to repair decisions. Any later
agent intervention must be judged on preserving the original reproduction and
existing regressions together, not on fewer searches or merely reaching a fixture.
No further investigation or paid run is queued by this report.

## Evidence and validation

External root: `C:/pt/nav01`.

- `plan.json`: five journal bindings, question, alternatives, selection and limits.
- `<task>-actions.json`: public action requests/results only; action/input identity
  retained. All five original journal chains and start/result identity pairs verified.
- `findings-final.json`: source spans, exact action identities, request-delivery
  bindings, 26 unchanged input-file bindings and the decision. Hash:
  `sha256:4bad5ef59b8b440e151d6f9e11b0affaebc105bfb824e0a8db4415be399f9329`.
  The earlier `findings.json` is preserved; its loader line 44 was corrected to 45
  in the final artifact without changing observations or conclusions.
- `runs/run_dev_navigation.jsonl`: append-only hash-chained investigation and
  closeout receipts. No raw reasoning, hidden tests or reference patches inspected.

Runtime source unchanged. Documentation checks and boundary/commit receipts are in
`closeout.json`. No provider calls, Docker launches, task tests, solver replay or
private evaluations; full runtime suite and mock smoke are not relevant to this
documentation-only change and were not rerun. User-owned AGENTS.md is preserved.
