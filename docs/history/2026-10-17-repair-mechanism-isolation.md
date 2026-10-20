# Retention and judgment: isolated experimental arms

Started: 2026-10-17. Completed: 2026-10-18. Provider-free implementation and validation. Paid execution is
**NOT_AUTHORIZED**; repair-quality outcomes remain **NOT_RUN**.

## Problem and decision

The [comparison specification](../../.agent/plans/question-support-comparison.md)
asks whether losing relevant evidence and making an unsupported judgment despite
available evidence require different interventions. Earlier delivery audits and
unsuccessful plan comparisons justify distinguishing these mechanisms; neither
establishes a repair benefit. Implement three removals from one common runtime,
without changing the default agent, transition rule, two-reference interface or
resource limits. Do not roll back unrelated reliability fixes.

The default combined implementation remains byte-identical. The experiment can
separate body selection from judgment presentation on identical public states.
Whether either improves autonomous repairs remains unanswered. Metadata size can
couple J to delivery at admission, so the mechanism audit must retain that
interaction rather than classify every J contrast as judgment-only.

## Implemented conditions and identities

Common runtime base: `168765b55b7d5c26cdfc7ce50c0d70cf729e39b8`.
Common diagnostic/test commit: `116e970b6a51a7c921b278f60ccd39b5854b3037`.
The three experimental commits are separate attached worktrees/branches; no runtime
switch was added to product defaults. `PATCHLOOP_TEST_REPAIR_ARM` selects expected
test assertions only. A test checks the actual five source files against the arm,
so changing the variable cannot disguise a different runtime.

| Arm | Exact commit | Removal | Base / brief prompt characters |
| --- | --- | --- | --- |
| E0J0 | `33e95588a9fb204fd7a7635393004a38c026e3a8` | Both packages | 7,889 / 10,184 |
| E1J0 | `6c8e929a40f6de9d422ce87559ad968c83c91a24` | Judgment presentation and added purpose guidance | 7,893 / 10,188 |
| E0J1 | `bd2125757b711ad7bfe3de1adf5779173de35a0d` | Focused evidence selection and optional cited-result replay | 7,996 / 10,805 |
| E1J1 | `116e970b6a51a7c921b278f60ccd39b5854b3037` | None; current behavior | 8,000 / 10,809 |

E0 passes no priority references to source projection and adds no optional old
question-cited exchanges. Binding, ordinary recency, anchors, native latest results,
staleness and the original candidate pool remain. The corresponding help sentence
states that references receive no priority. There are no task/path exceptions.

J0 removes only the final interpretation projection and restores the specified
earlier plan/completion wording, with honest baseline field names. It retains
model-authored/unverified warnings, original note text and check verdicts, concern
persistence, plan predecessor/reason validation, diff-bound finish review, and all
mechanical completion requirements. It does not roll back the earlier plan-history
or concern-persistence changes. E and J source transforms commute exactly.

The [builder](../../diagnostics/repair_mechanisms.py) checks the fixed base and
canonical Git bytes, refuses a dirty or calling/product checkout, and saves the
patch and source hashes externally. On Windows, create/canonicalize only a clean
separate checkout without line-ending conversion before preparation. Each frozen
arm was committed clean before the full suite. Runtime/lock identities, prompts,
schemas, import roots and common control hashes are in each `finalized-arm-v3.json`
and `validation-final/inspection.json` in the evidence root below. The final
inspection matches `validation-v2` in every field except the test-only commit.
The arms share the pinned Python dependency environment, with separate processes,
checkout working directories and `PYTHONPATH`; each imported package root was verified.

Unchanged: result-or-size transition algorithm; 2 references; 24,000 source
characters; 60,000 counted input tokens; 1,048,576 request bytes; 262,144 encrypted
item bytes; 40 model calls, 100 actions, 4 edits, 1,800 seconds and 330-second
evaluation reserve. Shared validators, cost/count admission and recovery code retain
identical bytes. The earlier spec called 8,000 the whole system prompt limit, but
the existing brief prompt was already 8,000 + 2 + 2,807 = 10,809. Correcting that
description increased no runtime limit; all arms stay within both existing sizes.

## Validation

| Arm | Full suite | Elapsed | Frozen runtime hash prefix |
| --- | --- | --- | --- |
| E0J0 | 5,225 passed / 19 skipped | 81.18 min | `537090417919` |
| E1J0 | 5,225 passed / 19 skipped | 84.19 min | `c615fe30cc1a` |
| E0J1 | 5,225 passed / 19 skipped | 86.69 min | `dc18b3779d8f` |
| E1J1 | 5,225 passed / 19 skipped | 88.19 min | `2f0d160691da` |

The common focused product checks passed, and all arms passed Ruff, 74 focused
tests, 22 additional expectation checks, 24 handoff/plan tests and mock isolated
evaluation. Final test commits additionally passed Ruff and 31 focused tests per
arm (about seven seconds each). All four mock runs reached EVALUATOR_PASS at zero cost; Docker safety is NOT_RUN. The focused runs remained below two minutes;
parallel handoff/integration checks took longer and are reported separately.
Completed full-suite runs used four pytest workers in one arm at a time, distinct
external state roots, no automatic test retries or worker restarts, and verified
tracked bytes/HEAD/runtime before and after. The same 19 existing opt-in/platform skips remain; no ablation-only skips
or relaxed timeout/size assertions were added. All 5,234 baseline test outcomes are preserved, with 10 added isolation tests per arm.

The first J0 preflight failed an exact prompt-hash assertion that still expected
J1. Related legacy presentation assertions were audited and now check explicit
J0 fields/hashes while preserving E1J1 assertions and the factual/recovery checks.
The first mock invocation incorrectly supplied a paid-only cost field; request
validation rejected it before execution. The corrected mock omits that forbidden
field, still costs zero, and leaves the later paid allocation unchanged. Original
failed receipts remain beside `validation-v2`; they are not overwritten.

The first full-suite attempt ran all four arms concurrently with two workers each
(eight in total). It was interrupted after about 145 minutes and partial failure
marks of E0J0 2, E1J0 3, E0J1 1 and E1J1 1. Its console logs, process identities,
partial progress and unchanged-source receipts are preserved. Termination prevented
final JUnit output: zero reported cases in those receipts means no final XML, not
zero failures. Only the identified E0J0 `after_write` recovery case has a captured
run-level diagnosis: Git reconciliation exhausted its existing five-second recovery
bound and stopped with LIMIT_REACHED. Other failure tracebacks were not captured
before interruption, so they are not individually attributed to resource contention.

That case and four adjacent recovery cases passed unchanged in an isolated run
(5 passed, 41.13 seconds). This is consistent with shared execution load contributing
to the known failure; it is not proof of the cause of every initial failure.

The next complete E0J0 run, with four workers and no other arm running, returned
5,220 passed / 5 failed / 19 skipped in 81.49 minutes. All three mutation-recovery
crash cases passed. The five failures were missing explicit J0 expectations: three
legacy tool-surface hashes (including plan instructions) and two ordered public-view
hashes; the actual tool schemas remain identical. The remaining arm
queue was deliberately held before E1J0 started; its `QUEUE_HELD.json` is an operator
stop, not a test outcome. The complete failed run stays under `E0J0/full-suite-v2/`.

The five expectations now assert exact J0 alternatives and retain the exact J1
literals. An independent public-view comparison proves that the only wire change
is J1's `working_plan.role` label in both key orders; state independence, field
order, schema, recovery and original factual assertions remain enforced. No product
source, recovery bound, timeout/size assertion or skip condition changed. Final
full suites then ran sequentially on the frozen commits above. Their receipts are
under each arm's `full-suite-v3/`; neither the initial partial attempt nor the
completed failing E0J0 run is presented as a pass.

## Saved-log factor isolation

[Replay](../../diagnostics/repair_mechanisms_replay.py) uses 75 historical public
handoff states: 75 original legacy questions, 75 unscoped reference surrogates,
2 active source-reference cases, 1 stale question and 43 tool-reference surrogates
with normal/omit variants. This produces **239 inputs per arm / 956 total**.
The references in the surrogate/active cases are operator-authored, not evidence
of autonomous uptake. These are state projections at historical sample points,
not new solves or counterfactual continuations of the old trajectories.

- J0/J1 preserve identical source line versions and original tool call/result
  bodies in all **478 paired comparisons** (239 for each E value). Other factual
  state is identical; every view change matches the intended interpretation
  projection. The corpus contains 26 distinct model-note versions and 20 distinct
  verification observations, all preserved as data.
- E0/E1 source deltas and optional result selections are identical under J0/J1
  in all 239 states. E1J1 matches all **153 prior canonical input objects byte for
  byte**; all 251 original read artifacts/journals remain unchanged.
- Source selection differs in only the 2 active source-reference states. The
  75 original legacy and 75 unscoped states, stale case and tool surrogates show
  no source-selection difference. No-reference replay is not evidence against E.
- Optional older result bodies appear in **41 of 43** normal tool-surrogate
  states under E1, versus none under E0. The other 2 cite automatic rechecks with
  no matching original model call, so no call/result pair is fabricated. All
  43 explicit omit variants omit them. Source bodies stay unchanged.

Maximum input-only bytes: E0J0 142,610; E1J0 146,467; E0J1 143,808; E1J1 147,894.
J adds 666–1,635 bytes with E0 and 666–2,399 with E1. These figures exclude the
full provider request and are not token-count/admission results. In a synthetic
byte-only stress check, identical padding places E1J0 at the unchanged request
limit in 41 states; J1 then exceeds it, and each already-replayed omission candidate
fits again after removing optional results. This demonstrates a possible
delivery-mediated interaction, not an observed historical fallback or a guarantee
that the synthetic request passes the token bound. The actual automatic fallback,
unknown-count stop and crash recovery paths are separately covered by the
fake-provider handoff tests. No count API or generation API was called.

## What the evidence selector trades away

This contrast removes the entire E package, so its counts differ from the earlier
incremental selector audit. It introduces **no new loss in the product's E1J1
behavior**, whose old inputs remain identical. Relative to E0's ordinary recency:

| Public question / boundary | Added line occurrences | Displaced line versions | Observed delivery difference |
| --- | ---: | ---: | --- |
| Astroid row 13 / 303: which open raises the file error? | 47 | 42 | Missing primary lines 122–126 become present, with the file-open call/error handling and immediate caller conditions. |
| Astroid row 13 / 476: directory guard, namespace route and file error | 63 | 67 | Missing primary lines 115–118 and 124–128 become present; the cited namespace countercheck was already present in both arms. Caller/source-opening support also returns. |

Total: **110 added line occurrences (67 unique versions), 109 displaced versions**.
All 109 displaced lines were reviewed in 18 public source units, with complete
text/version inventories retained. Citation completeness is not a sufficiency grade.

Some lost material is copyright, whitespace, documentation or another operation.
Useful competing evidence also disappears: `spec.py:246–250` contains another
`__init__.py` open/OSError path; `objectmodel.py:147–150` has a file/directory path
condition; `manager.py:148–155`, 183 and 223–229 describe extension/zip alternatives;
261–269 carries lookup error caching/rethrow; 271–287 contains outer caller gates
and the `ast_from_file`/`module_build` split. Several are incomplete fragments or
indirect to the frozen question, but they cannot all be dismissed as irrelevant.
The selected immediate support bundle does not guarantee every outer caller gate.

Preserve the frozen selection for the planned comparison. This audit supports
mechanism separation and documents the tradeoff; it neither establishes minimum
semantic sufficiency for every hypothesis nor justifies tuning these exposed cases.
Actual subsequent claims, actions and accepted repairs must decide the quality
question under the prespecified audit, including unfavorable displacement.

## Evidence and remaining boundary

Evidence root: `C:/pt/analyses/repair-mechanisms-20261017-v1`.
Key receipts: `factor-audit/{summary,source-deltas,optional-deltas,displacement-review}.json`,
`size-interaction-audit/`, each arm's `full-suite-v3/full-suite-result.json`,
`final-preflight-result.json`, `interrupted-attempt-result.json`,
`recovery-diagnostic-result.json`, `wire-view-diagnostic/result.json`,
`E0J0/full-suite-v2/full-suite-result.json`, and `validation-result.json`. New journals use
append-only hash-chained `dev-run-v1`; previous experiment packets and historical
records were not edited. The user's independent `AGENTS.md` edit remains unstaged.

The 3-task × 4-arm × 1-repeat, USD 0.88/row and USD 10.56 total proposal is unchanged.
Both live roots remain uncreated. Real provider/count calls and paid cost are zero.
Fresh task canaries, current image/rate checks and a fully resolved dispatch manifest
are still NOT_RUN/NOT_READY; no paid execution is authorized. No repair, autonomous
uptake, statistical reliability or generalization claim follows from this local work.
