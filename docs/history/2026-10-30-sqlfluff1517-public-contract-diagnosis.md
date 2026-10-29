# SQLFluff1517: public PASS with an incomplete delimiter repair

Date: 2026-10-30 KST. Completed public-only operator diagnosis, official=false.
Provider calls/cost: **0 / USD0**. Independent evaluation: **NOT_RUN** in this
follow-up. The prior acceptance FAIL remains unchanged; no private test, reference
patch or evaluator implementation was read.

## Problem and decision

Task 16 in the [integrated run](2026-10-30-integrated-3916-results.md) submitted after
167 public tests passed and a candidate probe avoided the reported crash, yet failed
independent acceptance. This was selected because the same task had already shown
public-PASS/acceptance-FAIL in the earlier dev20 run. The important question was
whether the saved repair had a public correctness gap, not whether another paid
attempt could finish.

**The saved patch is incomplete:** it fixes adjacent `;;`, but whitespace, a newline
or a comment between semicolons still causes the same token-loss RuntimeError.
Its new partial-success return also bypasses delimiter options. The new test was
collected and passed in replay, so missing execution is not the explanation supported by
this replay. These findings establish public defects in the candidate; they do
not identify the exact case used by independent evaluation.

## Question and controls recorded before execution

The leading explanation was a narrow branch repair combined with narrow tests.
Alternatives were omitted test discovery, importing an unchanged installation, or
the public CLI's trailing newline exposing a different path from the API probe.
Correct collection, candidate source provenance and exact CLI reproduction would
weaken those alternatives. If all public contract cases passed, the diagnosis
would remain unresolved rather than be inferred from the private verdict.

- Original implementation versus the exact submitted implementation. Both fresh
  workspaces contain the identical agent-authored test and operator diagnostic.
- Public base revision: `304a197829f98e7425a46d872ada73176137e5ae`.
- Submitted patch: `sha256:4cf0b28830384ded6e92cd514edf69d60e19faa52a9300bfa2fac7e48173b66e`.
- Same installed digest-pinned task image, Python 3.9.20 and standard public copy
  runner. No image acquisition, model, credential, network or private evaluation.
- API parse/lint examples, exact stdin CLI replay, generic `Delimited` contract
  cases using the existing public fixture, pytest collection and required suite.
- Same diagnostic bytes, inputs, test bytes and environment in both conditions.
  Baseline includes the new test so only implementation differs.
- Limit: 120 seconds overall, 70 seconds per condition; stop on setup failure,
  timeout, source drift, truncated output or cleanup uncertainty. No semantic
  success is inferred from the diagnostic process exiting zero: case outcomes
  and captured exceptions are assessed separately.

Implementation HEAD was `1a86755a7c7585893b82bb1c0a7a0e8a0d5f9245`; PatchLoop
runtime remained unchanged from the integrated run. Both sandbox checks completed
and cleaned up normally. Preparation plus execution took **50.098 seconds**;
individual sandbox executions took 16.025 and 15.998 seconds.

## Reproduced behavior

Both `Linter.parse_string()` and `lint_string()` produced the following results:

| Public input | Original implementation | Submitted patch |
| --- | --- | --- |
| `select id from tbl;` | No parse error; raw preserved | Same |
| `select id from tbl;;` | Token-loss RuntimeError | Parse violation; no crash; raw preserved |
| Same `;;` with final newline | Token-loss RuntimeError | Parse violation; no crash; raw preserved |
| `select id from tbl; ;` | Token-loss RuntimeError | Same failure |
| Newline between the two semicolons | Token-loss RuntimeError | Same failure |
| `select id from tbl; /* gap */ ;` | Token-loss RuntimeError | Same failure |
| Two valid semicolon-separated statements | No parse error; raw preserved | Same |

For the smallest failing variant, the candidate reports:

```text
RuntimeError: Dropped elements in sequence matching! 'select id from tbl; ;' != ' ;'
```

The original public `echo` reproduction was also replayed through
`python -m sqlfluff lint -`, passing `select id from tbl;;\n` directly to stdin.
Original: exit 1 with RuntimeError traceback. Candidate: exit 65 with a normal PRS
diagnostic and no traceback. With `; ;\n`, both still exit 1 with the token-loss
traceback. The public issue explicitly leaves ignoring duplicates versus reporting
a violation open; candidate exit 65/SQLParseError is not itself a proven defect.
Final-newline omission and using the API instead of CLI do not explain this gap.

## Mechanism: input preservation is separate from matching success

The original `Delimited.match()` retains the original `segments`, accumulated
`matched_segments`, and a remaining `mutated_segments` buffer. Its empty-section
failure at `delimited.py:185-189` returned only the remaining buffer. For `;;`,
this dropped the already consumed statement. The patch returns accumulated matched
segments plus the remainder, preserving raw text for this one branch.

For `; ;`, `pre_content` initially contains whitespace and enters the other branch.
After non-code trimming it contains no SQL expression. The failed match returns
`MatchResult.from_unmatched(mutated_segments)` at line 147, still omitting the
previous statement. `BaseSegment.parse()` at line 821 calls `check_still_complete()`;
the helper at `helpers.py:21-34` compares input raw against matched plus unmatched
raw and raises. Comments/newlines follow the same unmodified failure path.

The submitted return has a second consequence: `MatchResult.__bool__()` means
any matched segments, so preserving the prefix as *matched* turns failure into
partial success before option checks. Public grammar reproductions show:

| Grammar condition | Original | Candidate |
| --- | --- | --- |
| `bar..`, `allow_trailing=False` | No match, but loses prefix | Matches `bar.` and leaves `.` |
| `bar..`, `min_delimiters=3`, trailing allowed | No match, but loses prefix | Matches `bar.` despite insufficient delimiters |
| `bar. .` or `bar.foo.` | No match, loses prefix | Same loss |
| `bar.bar`, minimum 2 | No match, loses prefix | Same loss |
| Valid `bar.bar`; allowed trailing `bar.` | Match and preserve input | Same |

The first candidate result accepts a trailing delimiter despite the option; the
second violates the source comment that a match must contain at least the minimum
number of delimiters. The unchanged failures are pre-existing defects the repair
left behind, not new regressions introduced by it. Token preservation and grammar
success must be handled independently; retaining text by declaring a partial match
is not a general solution.

## Why the public check and probe passed

Explicit collection found the added node in **both** conditions:
`test/core/parser/delimited_test.py::test__parser__double_semicolon_does_not_crash`.
The unchanged required command selected 167 tests and deselected one:

- Original implementation plus the same added test: **1 FAIL / 166 PASS**. Only
  the added double-semicolon test failed with the original RuntimeError.
- Submitted patch: **167 PASS**, one deselected, matching the live receipt.

The existing 14 `Delimited` parameter cases at public `grammar_test.py:566-613`
cover ordinary lists, gaps, trailing-delimiter options and minimum counts, but not
consecutive delimiters. They assert match length, not complete input preservation.
The new test asserts only that `parse_string("select id from tbl;;")` produces some
`SQLParseError`. It neither varies the empty section nor exercises generic options.

The live probe repeats the same adjacent-semicolon example and a valid control.
It catches exceptions and prints outcomes; exit zero is not an assertion of task
correctness. Its captured output does support crash avoidance for `;;`, and this
paired replay confirms that improvement. It adds no coverage of the surviving
branches or option semantics. This is a coverage gap, not evidence that probes
are useless, required checks are broken, or the candidate imported stale code.
Both executions recorded the copied checkout's package path and source SHA-256.

## What this changes and what remains open

Prioritize public-contract coverage around the changed failure return: preserve
the whole input on failure while retaining failure semantics, and check adjacent,
whitespace/comment-separated and minimum/trailing cases together. An operator
repair is not implemented or validated here. Do not transfer the resulting solution
as a hidden hint to a fresh benchmark solver.

For PatchLoop, the evidence supports a task-specific failure diagnosis: the visible
edit, new test and probe all centered on one example, leaving sibling branches and
caller invariants unchecked. It does not establish the model's internal reasoning,
prove a general prompt intervention, or justify another blanket completion gate.
First consider an existing lightweight verification prompt's coverage of changed
failure returns and affected caller contracts; any agent-level benefit remains to
be measured. No paid repeat is necessary to establish the defect reported here.

Independent evaluation's exact failing assertion remains unknown. No private detail
was inspected, and no independent re-evaluation was run. Successful public controls
do not establish overall grammar correctness, tree semantics or generalization.

## Evidence

External root: `C:/pt/sqlfluff1517-diagnosis-20261030-v1`.
Append-only journal: `runs/run_dev_sqlfluff1517diagnosis.jsonl` (`dev-run-v1`).
Reusable public diagnostic: `diagnostic_program.py`; driver: `reproduce.py`.
`comparison-results.json` points to the content-addressed result summary.

- Public evidence packet: `sha256:a15a8adda79f74f849bda2dec261fc32600b01924b8df9cab7ad54bb3047a78e`.
- Baseline receipt: `sha256:0a6c1e1b9513375ad4001c0cc3fde1bf1230b43657153df8e11326b953ceb774`.
- Candidate receipt: `sha256:e6866cbc085a9d56b4957a7840271b81381ee42012be115d4e009ff1e0e93518`.
- Summary: `sha256:549a46156140bab7a22fd6aa976282f115666f0336241a30bac5c6ca29da94cc`.
- Original grammar: `sha256:027a5eb2b20d20511fc13298594516b1c76159af25d902aea7e317a5fd222173`.
- Candidate grammar: `sha256:72a1c6d38b369f70e2265351dd017bae908185b07b215cb1838da6239063e633`.

The source live journal and historical reports were preserved. This follow-up
replaces uncertainty about collection in current guidance without rewriting the
closed run's original evidence assessment.

Post-execution audit compared all 1,700 files in the two fresh checkouts (excluding
Git metadata): only `src/sqlfluff/core/parser/grammar/delimited.py` differed.
Receipt hashes and the eight-event journal chain verified. Documentation checks:
6 PASS in 0.13 seconds; HTML has 51 unique IDs and 64 checked links, with JavaScript
unchanged. No PatchLoop runtime source changed, so no runtime quality or speed claim
is added by these documentation checks.
