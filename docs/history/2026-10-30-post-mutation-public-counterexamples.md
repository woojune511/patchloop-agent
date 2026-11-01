# Latest SQLFluff failure-preserving patch: public counterexample comparison

Date: 2026-10-30. Completed operator diagnosis, official=false, claim-ineligible.
No provider call, private evaluator read/replay, solver continuation or patch edit.

## Question and decision

The user requested public counterexamples against the exact latest SQLFluff16
submission, to identify remaining defects before another runtime intervention.
The [latest live run](2026-10-30-post-mutation-review-results.md) had acceptance
FAIL despite public checks. That status alone does not locate a defect or establish
why the agent did not find one. Its failure-preserving patch differs from the
[previous partial-success patch](2026-10-30-retained-source-public-counterexamples.md).

**No remaining violation was reproduced in this public comparison.** All 20 grammar
cases preserve input, and all 19 specified matching/count expectations hold.
Seven wrapped-lint inputs return results with exact raw input. The original CLI
now reports a parse violation without the internal crash. This weakens the
explanation that the latest patch still has the previously demonstrated defects.
It does not overturn acceptance FAIL or establish complete correctness.

Keep the runtime and submitted patch unchanged. Do not add another generic warning,
mandatory probe or model run based only on the old defect narrative. The next
unresolved question is which intended behavior accounts for independent rejection;
this public diagnostic does not answer it. The observed whole-input parse violation
needs an explicit public behavioral requirement before treating it as a new defect.

## Fixed comparison

- Operator HEAD: `b53840d5`; original live execution code: `fbfdd213`.
- Task: `dev-train/current-dev20/16`, SQLFluff1517.
- Base commit: `304a197829f98e7425a46d872ada73176137e5ae`.
- Exact submitted patch: `sha256:ab25026869f0d02dec7a32bb34c06140b7fdec55cb0ce337f6c6565b4e46c82b`.
- Original Delimited: `sha256:027a5eb2b20d20511fc13298594516b1c76159af25d902aea7e317a5fd222173`.
- Candidate Delimited: `sha256:5ef33ea1a5130777251e0becd7aaafd050d090faaf839dd1903a8195e3aeb4b4`.
- Unchanged runtime: `sha256:47057ca997eaa2ba5c3c566aa76df16ae9c4e2bdb41b47f08d68da05b0ff2fd9`.
- External root: `C:/pt/postedit16-public-comparison-20261030-v1`.
- Journal: `runs/run_dev_postedit16publiccomparison.jsonl` in that root.

Two fresh public source copies, one execution per condition. Both contain the
identical agent-authored linter test addition; only Delimited is restored in the
baseline. The candidate contains the exact submitted patch. The program and
criteria were recorded before execution. The first eight grammar cases repeat
the previous public comparison; new cases cover gaps, comments and termination.

Use the existing task image, digest
`sha256:6e93dc479c481210c7a9b8ee6662288bd6b8220203a43074e46b0764729a653b`,
with the registered public-copy runner pointed at the fixed diagnostic program.
Both report Python3.9.20 and the expected source hash. Network disabled, read-only
workspace/root, no Docker start, image pull or build. Limits: 180 seconds total,
80 seconds and 80,000 output bytes per condition. No retry on setup drift, timeout,
truncation, program failure or cleanup uncertainty.

Elapsed comparison: **56.776 seconds**; sandbox durations 17.490/16.681 seconds.
Both sandbox programs exited0 with no timeout, truncation or cleanup failure.
Exit0 here means observations collected, not that all original cases passed.
Model calls 0, API spend USD0, new independent evaluation NOT_RUN.

## Results and public oracles

| Public comparison | Original | Latest candidate |
| --- | --- | --- |
| All 20 grammar cases: exact raw preservation | 11 lose input, 9 preserve it | 20 preserve it |
| Specified matching bool and matched-segment count | 19/19 hold | 19/19 hold |
| Remaining adjacent/trailing-allowed case | Input lost; bool not prescribed | Input preserved; bool not prescribed |
| Seven wrapped-lint inputs | Normal succeeds; six abnormal inputs raise RuntimeError | All return one file/result with exact raw input |
| Original CLI with echo newline | Exit1, dropped-elements traceback | Exit65, PRS violation, no traceback |

The original eight include normal/minimum controls, insufficient minimum,
trailing allowed/denied, adjacent delimiters with trailing denied or minimum3,
and an invalid middle element. All eight now satisfy their explicit expectations.
In particular, the previous patch's two rejection-to-success regressions do not
occur: `bar..` remains a failure with `allow_trailing=False` and with minimum3.
The other old losses, `bar.bar` with minimum2 and `bar.foo.`, are also repaired.

Additional grammar cases are `bar. .`, `bar.\n.`, line-comment gaps; no-gap
first/later termination with satisfied/unsatisfied minimum; explicit STOP
termination with minimum1/2; trailing whitespace allowed/denied; and adjacent
delimiters with trailing allowed and no minimum. That last case asserts only raw
preservation, because the inspected public contract does not settle its precise
partial-match strategy. It must not be counted as a specified success/failure oracle.

Expected matching/count behavior follows public `grammar_test.py:565-613` and
Delimited's option/termination rules. Exact raw preservation follows public
`helpers.py:23-35`, independently of match truthiness. The fixture constructs
actual comment/newline segments for comment cases; block comments use real SQL
lexing instead of the fixture's generic CodeSegment fallback.

The SQL inputs are normal single semicolon, adjacent doubled semicolon, a space,
a newline, an inline comment, a block comment, and two statements followed by
the doubled delimiter. All include the echo newline. The six abnormal candidates
report SQLParseError as a returned violation; none raises the internal RuntimeError.
The diagnostic deliberately does not call `check_tuples()`, which can raise a
returned parse violation and must not be mislabeled as a lint-call failure.

CLI uses the package's `python -B -m sqlfluff lint -` entrypoint with exact original
stdin. Exit65 is the ordinary violation result (`linting_result.py:132`, returned
by `commands.py:410`), not a clean lint PASS and not an internal exception.

## Cause, remaining uncertainty and agent interpretation

The original loss occurs after an earlier prefix has been consumed: returning
only `mutated_segments` omits that prefix. The latest patch changes five such
failure returns to the original `segments` while retaining failure truthiness.
Per-case source tracing actually reaches **all five changed return lines:
144, 173, 189, 199, 251**. Each previously losing path now preserves input.

The remaining multiline returns at 130-132 and 213-215 are unchanged but not reached
by these cases. Trace records are nonempty and include known return lines, so this
is an observed coverage boundary rather than absent instrumentation. NonCodeMatcher
terminates the tested no-gap inputs earlier. Neither universal unreachability nor
correctness of those unexecuted paths has been established.

On abnormal SQL the candidate marks the whole code input unparsable, including a
valid prefix. This is observed, but **not a confirmed violation of the inspected
public requirement**. The issue explicitly leaves ignoring the extra delimiter
versus reporting a violation open. Public `BaseSegment.parse:845-857` wraps the full
input when grammar matching fails; partial matching follows a different branch.
Requiring recovery of earlier parsed statements would be an additional expectation
that needs evidence. It must not be invented to explain independent FAIL.

Thus this comparison cannot support “the agent again failed to find the same
remaining counterexample” or diagnose inadequate reasoning. The latest agent's
earlier accessor/caller confusion is a separate, observed diagnostic mistake.
Its first repair predates the applied-change review, and these cases were executed
by the operator after submission. No autonomous counterexample discovery, causal
review benefit, held-out improvement or task acceptance claim follows.

## Evidence and reporting integrity

- Raw original result: `sha256:f1532c5d3cd2f6723e3d12dca543aa6112a69ec07c125668cbd1360cb954a48f`.
- Raw candidate result: `sha256:db2f369fcceec2a9d37f99e99d284b21174f8ff32c5c6e033ccd75300222239e`.
- Summary: `sha256:eb57941f2298608bc452f427db571902dc1af0da3c135a0a67900b05720a1038`.
- Saved-result integrity audit: `sha256:8251ea227d5dd82787a5a353e609fcc8fd04d864947082a30b81cd77e0e17b63`.
- Program/driver/patch/public source identities are in the journal's first event.
  Additional public parse/exit-code source evidence is in its interpretation event.

Each raw result has 29 JSON records: provenance 1, grammar 20, wrapped 7, CLI 1.
After both executions and summary persistence, host console output failed because
cp949 could not print a CLI emoji. The original completion and subsequent reporting
error remain in the append-only journal. A no-execution audit verified every saved
result hash, source provenance, same-test isolation, trace and cleanup receipt.
Its convenience-pointer export initially hit ArtifactStore's root boundary after
the audit was persisted; the existing reference was then exported with exclusive
file creation. Neither host reporting issue repeated target execution or changed
evidence. The plan's old label “unchanged-failure comparison” refers to preserved
rejection semantics; candidate line144 itself was changed.

Historical records, solver inputs and runtime remain unchanged. This follow-up
does not authorize another paid run, private replay or patch repair.

Documentation validation: all 6 layout tests pass. No runtime source or test
contract changed, so the fast runtime suite, Ruff and mock evaluation were not
repeated. Link/ID/script and evidence-integrity checks are recorded separately
under the external root's `docs-validation/`; no additional target execution.
