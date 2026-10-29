# Latest SQLFluff1517 patch: public counterexamples

Date: 2026-10-30 KST. Completed public-only paired diagnosis. Provider calls/cost:
**0 / USD0**. Independent evaluation: **NOT_RUN** in this follow-up. The prior
acceptance FAIL remains unchanged; no private test, evaluator artifact or reference
patch was read. No repair was applied to the saved submission or PatchLoop runtime.

## Question and comparison

The [latest evidence-reuse run](2026-10-30-evidence-reuse-3916-results.md) retained
concrete probe output but still submitted after checking only adjacent semicolons.
Static review identified unhandled failure returns and a missing minimum guard.
The user requested public counterexamples on this exact new patch. Reproducing
the earlier patch's failures was insufficient evidence about this submission.

Leading explanation: the empty-section branch repair leaves sibling input-loss
paths and turns one failure into partial success without all grammar conditions.
Stale imports or differing test/fixture bytes were alternatives; source provenance
and a complete paired file inventory distinguish them. An all-pass public replay
would leave the static concerns unresolved rather than establish a hidden failure.

- Operator HEAD: `98dc1535d472f61c488a4c665492ae47102c15e9`.
- Runtime: `sha256:e8098f8b558a6bd8a5310e0cb07f70deacc3fe86c41fe3a7dab6bd00368d05d9`.
- Source run: `run_dev_52faf580f57d463b`, dev-train task16.
- Base revision: `304a197829f98e7425a46d872ada73176137e5ae`.
- Exact submitted patch:
  `sha256:458da631dfd3cabebea613abe66c3edaaa21026a50523119a2d6c36e8b1994e3`.
- Both fresh workspaces receive that full patch; baseline alone restores
  `src/sqlfluff/core/parser/grammar/delimited.py` to original bytes. The latest
  added linter test and operator diagnostic are identical in both conditions.
- Existing local digest-pinned task image, Python 3.9.20, public copy runner;
  no image acquisition, network, credentials, model or private evaluation.
- Frozen before execution: question, alternatives, cases, source/patch/program/
  driver bindings, expected matching behavior and stop conditions. Limits were
  120 seconds overall, 70 per condition; stop on setup/source drift, program failure,
  timeout, output truncation or cleanup uncertainty, without retry.

Preparation/execution took **48.496 seconds**, with sandbox execution 15.861 and
15.469 seconds. Both completed and cleaned up normally. Each emitted 27 records:
one provenance, 14 API observations, eight grammar cases, two CLI cases, collection
and required pytest. Diagnostic exit zero means observations were collected, not
that their behavior passed.

## Reproduced failures and improvements

Both `parse_string` and `lint_string` showed the same crash distinction:

| Public SQL input | Original implementation | Latest patch |
| --- | --- | --- |
| Normal `select id from tbl;` | No RuntimeError; raw preserved | Same |
| Adjacent `select id from tbl;;` | Token-loss RuntimeError | Parse violation; no crash; raw preserved |
| Adjacent `;;` with final newline | Token-loss RuntimeError | Parse violation; no crash; raw preserved |
| Space: `select id from tbl; ;` | Token-loss RuntimeError | Same failure |
| Newline between semicolons | Token-loss RuntimeError | Same failure |
| Comment: `select id from tbl; /* gap */ ;` | Token-loss RuntimeError | Same failure |
| Two valid statements | No RuntimeError; raw preserved | Same |

Smallest remaining example:

```text
RuntimeError: Dropped elements in sequence matching! 'select id from tbl; ;' != ' ;'
```

Exact stdin CLI replay confirmed the distinction too: `select id from tbl;;\n`
changed from exit1/RuntimeError to exit65/normal PRS diagnostic. The space variant
`select id from tbl; ;\n` still exited1 with RuntimeError in both conditions.
The public issue permits a parse violation for repeated delimiters; PRS/exit65 is
not itself the established defect. API choice or final-newline omission does not
explain the gap.

Generic `Delimited` cases separate input preservation from matching correctness:

| Input/options | Original | Latest patch |
| --- | --- | --- |
| `bar..`, trailing=False | No match; prefix lost | No match; whole input preserved: improved |
| `bar..`, minimum=3, trailing=True | No match; prefix lost | **Incorrect match `bar.`**, remainder `.`, whole input preserved |
| `bar. .`, trailing=False | No match; prefix lost | Same loss |
| `bar.foo.`, trailing=False | No match; prefix lost | Same loss |
| `bar.bar`, minimum=2 | No match; prefix lost | Same loss |
| Valid `bar.bar`; allowed trailing `bar.` | Correct match and preservation | Same |
| `bar.bar.bar`, minimum=2 | Correct match and preservation | Same |

The gap/invalid/minimum-failure input loss is a pre-existing defect left unrepaired.
By contrast, matching `bar..` when minimum=3 is a **new success-condition regression**
relative to the original: only two delimiter tokens exist, yet the patched branch
returns a truthy partial match. Preserving all raw text does not satisfy that guard.
The false-trailing case genuinely improved and must not be described as still broken.

## Source mechanism and test coverage

In the candidate `delimited.py:143-144`, a failed/incomplete match still returns
only `mutated_segments`. Whitespace/comment content takes this sibling branch
after trimming, omitting the already consumed statement. The caller's
`check_still_complete` at `helpers.py:21-34` detects input versus matched+unmatched
raw mismatch and raises. The latest empty-section branch at `delimited.py:191-195`
guards `allow_trailing`, but its early partial-success return bypasses the minimum
condition. Other minimum-failure returns also retain only the remaining buffer.

The new node was explicitly collected in both conditions:
`test/core/linter_test.py::test__linter__double_semicolon_does_not_crash_parse`.
The unchanged public parser/linter selection returned:

- Original implementation plus the identical added test: **1 FAIL / 166 PASS**,
  one deselected. The sole failure was that added node's adjacent-semicolon crash.
- Latest submitted implementation: **167 PASS**, one deselected.

Quiet pytest output omits passing node names, so the candidate's execution-output
`authored_node_present=False` field is not missing-collection evidence. The separate
collection receipt includes the node. The added test checks normal input and a
parse violation for adjacent `;;`; it contains no separated-delimiter or generic
minimum/trailing cases. This confirms insufficient coverage rather than test omission.

## Decision and boundaries

The exact patch's residual behavior is now dynamically established. Preserve two
separate obligations in a repair: failure must retain the full input, and success
must satisfy all applicable grammar options. Merely converting a failure into a
prefix match can preserve bytes while introducing false success.

For PatchLoop, output retention worked in the preceding live run, yet the solver
did not test the relevant sibling paths/options. The next agent-level investigation
should compare public plans/check questions with actual cases and their observed
outcomes. This diagnosis does not determine the model's internal reasoning, justify
a new blanket finish gate or establish a general prompting solution. Operator cases
and repair details are not injected into a fresh benchmark solver as hidden hints.

No independent re-evaluation or code repair was performed. These public failures
establish incompleteness and a regression, but the exact private failing assertion
remains unknown. Normal controls are not proof of complete SQL grammar correctness.

## Evidence and integrity

External root: `C:/pt/sqlfluff1517-latest-public-20261030-v1`.
Journal: `runs/run_dev_latestsqlfluff1517diagnosis.jsonl` (`dev-run-v1`).
Driver/program: `reproduce.py`, `diagnostic_program.py`. Pointers:
`comparison-results.json`, `public-audit.json`.

- Public packet: `sha256:669f1a8b7c42f6469276ef5b0a64fe165a935eb1effa8eb1a6c35defcd4289af`.
- Baseline receipt: `sha256:85c268387a79e3fc7659a9816dd9ceba42ed806adf90049e05ae65383b75b788`.
- Candidate receipt: `sha256:2dfd13abe3414a60d2e0f298e5d85c0e5d6e4c3ba365ea384e5c675c7afa5a69`.
- Comparison: `sha256:f600d457be16b5dce49a984f6581dfb93a1383321d42f819fa67a1cf0badb480`.
- Paired audit: `sha256:ae4ae51f8aa8a44616a8a30141a7c71c4d2379d71947fba63cda062185e9f149`.
- Original grammar: `sha256:027a5eb2b20d20511fc13298594516b1c76159af25d902aea7e317a5fd222173`.
- Candidate grammar: `sha256:898306258ba5747065780d130f5d3a98d01c8698c1c6d65b10f8a0b9c3735f2e`.
- Identical test: `sha256:02812026377143c4bc9b96e58decebc0c4abef91189cf4c701a51fdf779d4c72`.

All 1,699 public files in each workspace were hashed: only `delimited.py` differs.
Imported package/source paths and hashes match the copied candidates. Receipts,
journal chain, source live journal and runtime identity were checked. Closed prior
reports remain byte-preserved; this separate record supersedes their then-unrun
counterexample status in current guidance.

Documentation checks: 6 PASS; HTML has 51 unique IDs, 69 valid links and unchanged
JavaScript. Visual rendering was not rerun for this content-only update. Runtime
source is unchanged; these documentation checks add no agent-quality claim.
