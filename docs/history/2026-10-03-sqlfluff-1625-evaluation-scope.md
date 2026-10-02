# SQLFluff 1625: public behavior and evaluation scope

Date: 2026-10-03. Operator-only follow-up to the
[positive-verification comparison](2026-10-03-positive-verification-results.md).
Starting commit: 9d98c0d653a400f7057a8313dd60c9fa097e8fdb.
Original task grades, historical records, task packages and submitted patches remain
unchanged. This record is evidence, not solver guidance.

## Question and decision

Why did all four 1625 patches pass the two explicit public examples and registered
regression, yet fail original acceptance? This repeated gap matters because an
unexplained FAIL could incorrectly be attributed to ineffective positive-result
verification and motivate another prompt experiment.

The gap is now explained within the evaluated conditions. All four original reports
completed 65 items with no missing results or infrastructure failure: the same CLI
output test failed, and the other 64 passed. Static operator comparison establishes
that the original evaluation test patch changes one test file; its parsed Python
structure is identical except for the expected-output constant. That constant differs
only in the L031 diagnostic description. The existing test assertion is unchanged.

Three submitted patches preserve the original public CLI output and fail the evaluated
expectation solely on that description. A1 also suppresses the existing ANSI warning,
which is an independently reproduced public regression. Thus the four failures are not
four demonstrations that the reported TSQL behavior remains broken.

Preserve the baseline and original A/B scores, A 1/4 versus B 2/4. The experiment's
adoption criterion remains unmet. This diagnosis narrows what the 1625 failures mean;
it does not convert them into benchmark passes or establish complete patch correctness.
No additional prompt variant, runtime gate, task patch or paid comparison is selected.

## Public contract and source

The public issue explicitly expects no L031 violation for both the unaliased TSQL
query and its aliased counterpart. It does not specify a replacement warning string.
All four submitted patches meet those two expectations, as both the frozen post-batch
assessment and this follow-up replay demonstrate.

The base source also supplies preservation evidence:

- `src/sqlfluff/rules/L031.py` documents avoiding aliases in FROM clauses as well as
  JOIN conditions. Its emitted description mentions only a join condition.
- `test/fixtures/rules/std_rule_cases/L031.yml` contains single-table alias failures.
- `test/cli/commands_test.py::test__cli__command_directed` checks the full output for
  an existing ANSI fixture, including the original L031 warning and description.
- The task's registered public command runs `test/rules -m "not dbt"`; it does not
  include this CLI test. Passing that command therefore misses A1's public CLI regression.

There are two distinct contracts to assess: the ticket's requested TSQL behavior and
the diagnostic wording required by original acceptance. Checking the ticket examples
more often would not distinguish the three wording-only failures. Conversely, expanding
public preservation coverage to the existing CLI test would expose A1, but still would
not establish the new private wording expectation for the other three patches.

## Executed public replay

The same public program ran on the unchanged base and four hash-verified submitted
workspaces, using the existing pinned evaluation image. It invoked the public CLI
through Click and the public Linter API. Public source was copied without Git metadata,
private files or symlinks, then mounted read-only with network disabled. No hidden test
or private expected string was passed to these programs.

| Workspace | Both issue examples | Original public CLI output | L031 warning in CLI | Evaluated CLI prefix after ignoring only description text |
| --- | --- | --- | --- | --- |
| Base | FAIL | PASS | Present | MATCH |
| B1 | PASS | PASS | Present | MATCH |
| A1 | PASS | FAIL | Missing | MISMATCH |
| A2 | PASS | PASS | Present | MATCH |
| B2 | PASS | PASS | Present | MATCH |

The last column is an operator text comparison of captured public output, not a new
acceptance grade. Removing description text is a diagnostic operation only. Original
acceptance was not rerun or modified. The three MATCH rows preserve the full checked
prefix outside that one description; A1 remains different even with it ignored.

Public variants also demonstrate why passing the two examples is not exhaustive:
A1 still reports L031 when the TSQL alias is referenced in WHERE, and A1/A2 report it
when the single-table alias is unused. B1/B2 suppress those warnings. The variants
were derived from the public query and patch conditions; their observations are not
new authoritative acceptance requirements or proof of an overall preferred patch.

## Implication for harness development

This case supports requirement-to-check mapping before using task grades to diagnose
agent weaknesses. Record separately whether a check covers the requested behavior,
preserves existing behavior, or demands an additional exact interface expectation.
Senior engineering practice also calls for checking public callers and observable
output when changing a shared rule; A1 shows a concrete omission there.

These are analysis conclusions, not evidence that adding another instruction helps.
The runtime already distinguishes public checks from isolated acceptance. Repeating
the same positive examples or forcing a probe would not reveal the wording difference.
Future verification research needs tasks whose measured failure exercises the target
behavior, with private audit conclusions kept out of solver context. No replacement
task, grading policy or live experiment is chosen here.

The remaining uncertainty is the desired behavior outside the two explicit TSQL
examples, given the broader public rule documentation and differing patch conditions.
This investigation neither resolves that product-policy question nor validates every
regression surface. It does resolve the observed four-run acceptance discrepancy.

## Evidence and validation

External root: `C:/pt/analyses/sqlfluff-1625-scope-20261003-v1`.

- `audit.json` binds four original child journals/reports and five public replay
  receipts. SHA-256: `8e5623d654e056a959b50bf8f9ef9973b678eb626264b942caf436ac4e08b316`.
- `run_dev_sqlfluff1625scope2` is an append-only dev-run-v1 journal; final head:
  `sha256:f83037a9caf0167da2c9789937106523ae9cc429d2cb9898bd88775b669b3744`.
- Original report artifacts and submitted patch identities were hash-checked; the
  four journal chains were validated. Workspace diffs were unchanged after replay.
- All five replay programs completed with exit zero, no truncation, timeout or
  cleanup uncertainty. Their internal CLI exit was the expected lint-failure code.
- The first operator driver referenced a nonexistent preflight method and stopped
  before any replay. Its corrected successor executed all five replays, then used
  the wrong artifact-store root for its summary. `finalize.py` verified those saved
  receipts and wrote the summary without repeating execution. Both errors are retained.
- No reference repair was read. Private literals remain outside solver prompts and
  public replay programs. Provider calls, new hidden evaluations and image acquisitions
  were all zero. Runtime/default changes and claim-producing work were not executed.

Documentation validation: five layout/link/history-preservation tests passed;
`git diff --check` passed. No runtime test or mock rerun was needed for this documentation
change; executable production code and task packages are unchanged.
Final report: `C:/pt/validation/sqlfluff-1625-scope-docs-20261003-b.xml`.
