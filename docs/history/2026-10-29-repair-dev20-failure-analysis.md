# Dev20 failure classification: repair evidence, evaluation contracts and preparation

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-29
- Verification Status: ANALYZED (retained traces and static source; no rerun)
- Version Label: dev20_failure_analysis_v1

## Question and scope

The user requested classification and analysis of the nine acceptance failures
and one unsubmitted attempt in the [closed dev20 measurement](2026-10-29-repair-dev20-results.md).
The important question is which failures demonstrate incorrect repairs, which
reflect a gap between the public report and evaluation contract, and which arise
from preparation, test construction or incomplete diagnostic retention.

Three delegated operator analysts inspected disjoint groups and the parent
inspected the unsubmitted case and integrated the records. Context was shared;
this was not blinded or cross-family verification. Evidence consists of the
public issues, submitted diffs, candidate public source, actual requests/actions,
public observations/checks and retained evaluator receipts. No target execution,
new repair-model/provider call, reference-patch lookup or repair was performed.
Private assertion details remain in external operator reports, outside solver
requests. Original benchmark grades remain 10 PASS / 9 FAIL / 1 NOT_RUN.

## Classification

These are primary descriptive groups, not mutually independent causal effects.
Several rows also have a public verification or compatibility gap.

| Primary group | Count | Tasks | Supported interpretation |
|---|---:|---|---|
| Input/caller hypothesis not established | 2 | pydicom-1413, astroid-1333 | The chosen diagnostic or intermediate behavior does not establish the original failing caller/input path. |
| Numerical boundary/dataflow gap | 1 | pvlib-1707 | An early numerical guard does not protect the later calculation across a broader parameter combination. |
| Output/API/implementation contract mismatch | 4 | pydicom-1139, pydicom-901, astroid-1268, SQLFluff-1763 | Evaluation asks for details not fully specified by the public issue; public compatibility concerns differ by row. |
| Public symptom improved, exact remaining assertion unavailable | 2 | SQLFluff-1517, SQLFluff-1625 | Useful public execution evidence exists, but truncated evaluation output prevents exact failure diagnosis. |
| Added-test error and exhausted mutation allowance | 1 | pydicom-1694 | One source edit followed by two test edits; the new test fails on its exception expectation, then no repair slot remains. |

### Input/caller hypotheses

**Pydicom-1413:** the public report concerns bytes. Two pre-edit probes used
bytes that succeeded, then numeric lists/arrays that produced a similar error.
The model treated the latter as its reproduction and changed the writer. The
public `DataElement.value` setter can split some bytes before serialization;
the model read the lower conversion functions but missed this preceding setter.
No post-edit probe ran. The private grade confirms failures in byte-assignment
cases, although its detailed traceback was cropped. Public-source reasoning
strongly supports an input-representation/wrong-layer explanation; exact new
before/after behavior has not been rerun. More probes of the numeric surrogate
alone would not validate bytes preservation.

**Astroid-1333:** the only helper, before editing, observed normal namespace
resolution. The model hypothesized that rejecting the directory would avoid
the downstream pylint error and changed Astroid accordingly. It never ran pylint
or replayed the candidate. Evaluation executes the changed function and observes
an inappropriate rejection. Thus an unexecuted edit is not the explanation;
whether the original F0010 persisted or changed remains unobserved.

There is also a concrete preparation gap. The current row-13 request omits
`caller_source_roots`, its dependency descriptor has zero pylint Python files,
and actual first/last read/search schemas offer no dependency source scope.
The earlier successful helper-contract fresh run registered
`{'pylint': 'pylint'}` and included 125 pylint Python files. Current
`C:/pt/repair-dev20-plan-v2/prepare.py:32` copies the five-task index-1 request,
then replaces task/state/source/dependency paths at lines 65-68 without adding
task-specific caller roots. It reuses the older row-13 dependency bundle.
`patchloop/dev/dependency_sources.py:53-62` correctly returns no catalog for empty
roots; the runtime feature exists but the run did not enable/provision it.
Execution dependencies and readable source scopes are separate readiness checks.
Do not describe this as the model ignoring offered pylint source access. This
condition difference also limits comparison with the earlier Astroid success.
Restoring access is not by itself evidence that a new attempt would succeed.

### Numerical boundary

**Pvlib-1707:** the patch zeroes an intermediate transmittance but a subsequent
absorption/normalization calculation can still introduce NaN. The observed
failure concerns a broader parameter boundary, not a demonstrated failure of
the exact default-parameter public example. The full function was accessible;
no helper or new test was used, and the old public suite passed. The reusable
question is how modified intermediate values reach the final output, including
source-justified parameter interactions. Do not inject an operator-discovered
private case as though it had appeared in the issue.

### Contract mismatches

**Pydicom-1139:** the requested membership and normal iteration behaviors pass
the retained evaluation cases. The remaining failure concerns an exception
class for a different protocol usage which the public issue does not specify.
It remains benchmark FAIL, but not evidence that membership itself is broken.

**Pydicom-901:** import-time logging configuration was removed. Nearby documented
opt-in debug output was not executed, so compatibility is not established merely
because the function remains present. Evaluation also asks for handler/API
details absent from the short issue. Separate the publicly grounded compatibility
question from those private expectations. Two searches used `OR` even though
`search_files` matches literal text; they returned no spans. This is observed
tool-usage friction, not established cause of the final failure. The literal
matching instruction is buried in the path-glob description (`tools.py:310`).

**Astroid-1268:** adding the missing visitor removes the reported missing-method
exception. The model selects a string representation, then adds a test that
expects that same selection. Evaluation expects another representation. The
issue did not state an exact string; related public visitor and node-rendering
conventions were available. A test derived only from the patch's own assumption
establishes consistency, not correctness of that assumption. Original-call replay
alone cannot choose between two non-throwing outputs without grounded expectations.

**SQLFluff-1763:** the candidate implements temporary-file write followed by
replacement inline in the existing persistence method. The private evaluation
directly calls a particular newly expected internal helper, which the candidate
does not define. Its recorded failures therefore do not exercise the new inline
branch. That is concrete implementation coupling in the evaluation, not proof
that the candidate still truncates files. The candidate's file preservation is
also not proven: its only helper ran before editing and did not trigger encoding
failure or call the modified persistence method. Benchmark FAIL and unverified
public behavior must both remain visible. Do not add the private helper name to
a repair prompt.

### Exact causes limited by capture

**SQLFluff-1517:** a candidate helper processes the reported SQL without the
internal RuntimeError, preserves its text and reports a parse error. A new
public regression test plus existing checks pass. The issue allows a normal
error instead of a crash. Evaluation fails related semicolon cases, but exact
assertion operands are missing. It is unsupported to conclude either that only
wording differs or that the original crash persists.

**SQLFluff-1625:** the same helper before and after editing observes the reported
TSQL alias violation disappear. The public rule suite passes. The remaining
evaluation failure is in a CLI test, with its exact assertion missing. This row
is counterevidence to a blanket explanation of missing observation/replay.

The evaluator retains only the last 24,000 stdout bytes: row 16 omitted
1,402,003 bytes and row 17 omitted 1,965,770 bytes. Final grading reports are
complete, but the assertion blocks are gone. Row 8 also lost 11,419 bytes of
detailed output. Tail-only capture is therefore a demonstrated diagnostic
limitation. Prioritize failure sections or a bounded structured failure record
in operator evidence, while keeping evaluator output outside solver feedback.
No new evaluation was run to recover these lost details.

### Unsubmitted pydicom-1694

The first accepted edit moves deferred value conversion inside the existing
exception guard, as suggested in the public issue. The second adds a regression
test; the third fixes an accidental call of a globals dictionary in that test.
These were not three distinct failed production repairs.

An earlier helper under default validation did not reproduce the old exception.
The test then enables strict validation but still expects the old report's
TypeError. The public run actually raises ValueError before reaching the test's
suppressed-call assertion: 26 tests pass, only the added test fails. This does
not establish that the candidate's suppression fix is wrong. It also does not
establish acceptance PASS without evaluation.

The host had rejected adding a name to an existing module-level import under
the additive-test rule, which created friction before the model chose the
indirect globals access. A function-local import was an available alternative;
the rule did not require the mistaken workaround. After the failed check, the
completion planner stops before another response because all three accepted
mutation slots are used. Seven responses, nineteen tools, USD3.77435 and about
1,769.64 solver seconds remain. The immediate blocker is mutation accounting,
not money or response length. Do not bypass the required failing test to finish.

## Cross-cutting conclusion and priorities

The ten rows contain 125 provider responses, all completed with no incomplete
reason or provider error. Maximum request/response sizes among them were
50,628/10,516 tokens, below 60K/40K. All nine graded failures reached
normal submission with unused monetary and mutation allowance. Several explicit
last-request audits show diagnostic/edit tools still available. These observations
do not support a blanket context/output/cost increase or reopening a mandatory
original-reproduction gate. They do not prove that every admission choice or
context selection was optimal either.

The highest-confidence engineering defects are **missing task-specific caller
capabilities in preparation** and **loss of evaluation failure details**. Both
can be corrected and checked locally without a new repair run. Neither correction
is yet implemented by this analysis. Preparation should derive declared callers
and source scopes from public task requirements and verify both actual dependency
bytes and the rendered request, not merely verify the hashes of an incomplete
bundle. Operator logging should preserve the failure block as well as summary.

For model behavior, the strongest public-evidence target is **hypothesis-
discriminating verification**: preserve input representation; trace producer and
consumer; distinguish issue-stated expectations, existing API conventions and
new assumptions; test the changed candidate's observable behavior. Prefer an
optional concise evidence record in the existing workflow over another blanket
gate. This is a proposed intervention, not a measured gain. Rows 7/12/17 show why
simple exception absence, more replay, or more tests alone cannot settle every
contract. Row 9 separately motivates validating test construction before spending
the last mutation and examining the granularity of mutation accounting within
fixed overall bounds. No new policy or budget is adopted here.

## Interpretation limits and validation

Fallacy scan: 11/11 considered. No inferential test or population effect estimate
is made. Simpson, base-rate neglect and reverse-causality claims are not applicable
to these trace-level descriptions. Ecological/selection/collider risks are bounded
by retaining per-task evidence and not comparing probe counts only among failures.
Regression-to-mean, look-elsewhere and forking-path risks remain for any later
rerun/retuned design: categories are explicitly post hoc. Survivorship is avoided
by retaining the unsubmitted row and the original denominator of 20. Correlation
is not promoted to causal improvement: proposed changes have not been tested.
No held-out or repeated-run reliability inference is supported.

This is a read-only analysis plus documentation change. No runtime behavior,
historical outcome or candidate was modified. Documentation checks, row coverage,
evidence identity and diff checks are recorded separately in the analysis closeout;
no target/benchmark rerun was needed or claimed.

Detailed operator-only evidence, including exact event sequences and private
receipt identities, is retained under `C:/pt/repair-dev20-failure-analysis-v1/`:

- `library-findings.md`: indices 5/7/8/10.
- `astroid-findings.md`: indices 12/13 and caller-capability comparison.
- `sql-findings.md`: indices 16/17/19 and capture limitations.
- `pydicom1694-findings.md`: public-only index 9 diagnosis.
- `operational-profiles.json`: all 20 rows, avoiding a failures-only operational view.
- `classification.json` and `runs/run_dev_failureanalysis.jsonl`: classifications,
  input hashes and append-only analysis receipts.

The prior paid allocation remains CLOSED; this analysis creates no new one.
