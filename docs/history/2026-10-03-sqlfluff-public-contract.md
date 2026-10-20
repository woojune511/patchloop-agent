# SQLFluff 1625: public requirements and old test expectations

## Question and decision

The [public setup calibration](2026-10-03-sqlfluff-public-setup.md) corrected missing
test prerequisites but rejected mandatory full-suite expansion. This review asks
which existing expectations actually constrain the requested repair, using only
the public issue and source at `14e1a23a3166b9a645a16de96f694c77a5d4abb7`.
Neither reference implementation nor its raw failure output was read. No private
test or new reference control was used.

Separate default behavior, explicitly invoked rule behavior and inferred extensions.
Keep the existing required scope. No runtime prompt, tool, test expectation or
submission gate changes follow from this review. The operator guide now states
this interpretation boundary. The earlier failure to select a CLI test does not
by itself establish failure to verify a valid requirement.

## Requirement and expectation map

| Evidence | What it establishes | Disposition |
| --- | --- | --- |
| Public issue, Expected Behaviour, Dialect=TSQL, Configuration=N/A | Both supplied queries must lint cleanly under ordinary configuration; adding the shown alias must not produce the reported L031 error. | Confirmed requirement for those two examples. |
| L031 rule documentation and explicit-rule fail/fix fixtures | The explicitly invoked rule avoids aliases, with documented exceptions such as self-joins. | Preserve these current explicit-rule checks unless a public requirement changes them; they do not establish default activation policy. |
| CLI snapshot, default ANSI configuration | Historically the fixture emits L003, L010 and L031 in a particular text prefix. | Separate unaffected formatting/other-rule behavior from disputed default L031 behavior. The entire old prefix is not automatically a repair acceptance condition. |
| Consistent alias rename of issue example | A simple transformation preserves the same reference binding. | Derived consistency diagnostic, not another supplied requirement example. |
| No-join issue example plus a WHERE reference | Tests whether the repair depends on the clause containing the alias reference. | Derived boundary diagnostic; the issue's no-join wording motivates it, but the exact case is not supplied. |
| JOIN-containing TSQL or default behavior in other dialects | Not specified by the issue's two examples. | Unresolved policy scope; do not silently require either suppression or continued default L031 output. |

Public source establishes why these distinctions matter:

- `src/sqlfluff/core/default_config.cfg:4` selects ANSI, and line 6 has no explicit
  rule selection. The issue instead names TSQL.
- `src/sqlfluff/testing/rules.py:59` constructs fail/fix checks with
  `overrides={"rules": code}`. Its pass helper at line 96 obtains the named rule
  and crawls it directly. `test/rules/std_test.py:97` also passes an explicit rule.
- `test/cli/commands_test.py:49` includes L031 in `expected_output`; the assertion
  at line 70 compares the whole default CLI prefix. It does not explicitly select L031.
- `test/fixtures/rules/std_rule_cases/L031.yml:3`, line 12 and line 81 supply the
  self-join, ordinary join and unused-alias cases. A rule-local pass fixture can
  still trigger unrelated rules in a default lint invocation.

The public issue does not determine whether a solution should alter default rule
activation, rule semantics, or a narrower dialect condition. None of those designs
can be inferred from the known fact that a reference failed the old full suite.

## Frozen public-only diagnostic

Nine cases were selected before execution: two exact issue code blocks, consistent
alias rename, a WHERE extension, the CLI fixture, unused alias, self-join, ordinary
join, and the same join SQL under TSQL. The last two dialect/settings choices and
their public provenance are recorded in `plan.json`; no cases were added after
observing results. Each was linted in default mode and with `rules=L031`, for base,
saved A1 and saved B1: 54 observations in three sandbox executions.

The driver reuses the registered temporary public checkout and offline example
plugin setup, replacing only pytest dispatch with a public Linter observation.
Each check has a 120-second cap and stops on setup/parser/internal errors, execution
uncertainty or workspace changes. Outputs are observations, not 54 passing tests.

The table reports whether **L031** occurs; absence does not imply an otherwise
clean query. In this panel its presence agrees across the two invocation modes.

| Public case | Base | A1 | B1 |
| --- | --- | --- | --- |
| Exact TSQL example without alias | absent | absent | absent |
| Exact TSQL example with alias | present | absent | absent |
| Consistently renamed alias | present | absent | absent |
| TSQL alias plus WHERE, still no JOIN | present | present | absent |
| Existing ANSI CLI fixture | present | absent | present |
| Existing ANSI unused-alias fixture | present | present | present |
| Existing ANSI self-join | absent | absent | absent |
| Existing ANSI ordinary join | present | present | present |
| Same join under TSQL | present | present | present |

Both saved patches lint the exact issue examples and renamed-alias example cleanly
in default mode. A1 emits L031 again for this extension; B1 remains clean:

```sql
SELECT a.[hello]
FROM
    mytable AS a
WHERE a.[hello] IS NOT NULL
```

A1's public patch counts alias references in SELECT separately from later clauses
and skips L031 only when no later-clause reference exists (`L031.py:184-207` in the
saved A1 workspace). The WHERE observation matches that mechanism. B1's public
condition uses the TSQL dialect and FROM-element count instead (`L031.py:94` in B1).
This explains the observed difference without using a stale ANSI CLI expectation
as an oracle. It supports a clause-sensitive limitation in A1 under the derived
no-join interpretation, not a new accepted-task verdict or proof that B1 is correct.

L003/L010 remain in the default CLI fixture on all three controls. The default
self-join fixture emits L003 while explicit L031 selection emits no violation.
These observations show why rule-local PASS and full default-lint PASS must not be
conflated. No fix-output or complete CLI-format comparison was added in this run.

## Evidence and limits

Execution head: `330d936299dff7464372e06e3d53cc42695e7c26`.
Runtime content remained
`sha256:c5db9ef2e78b2f56944bbc8910d57c978346111fbba6cf03c409c61177917792`.
Existing image digest:
`sha256:b61e33ddbf217f64b2ce29abc39aa9e577e0eacdbcd1b885d78e4ecdfaff9069`.
Base/A1/B1 heads and exact patch hashes were checked before each execution.
Elapsed Docker times: 14.750, 14.125 and 14.074 seconds, respectively. All completed
without setup/parser/internal errors, truncation, timeout, cleanup uncertainty or
workspace changes. Source imports were verified to come from the temporary current
checkout, and configured rule selection is recorded with every observation.

Evidence root: `C:/pt/analyses/sqlfluff-public-contract-20261003-v1`.
`run.py`, `plan.json`, `result.json`, content-addressed receipts and the hash-chained
`run_dev_sqlfluffpubliccontract` journal preserve the driver, case provenance,
source hashes, exact commands and observations. Result artifact hash:
`sha256:2a956c711d8c902a184b134523db74c89006e1ab030bc8b4f27ce35f5b9cf6bc`.

Provider calls/cost and new private evaluations were zero. No solver was run,
reference bytes projected, fresh solve measured, or historical artifact rewritten.
Every result is official=false and claim-ineligible. Original acceptance failures
remain separate historical results; this diagnostic does not explain all of them.

Documentation layout/link tests: five passed in 0.18 seconds (`docs.xml`). Ruff
and diff whitespace checks passed. Full repository tests and mock smoke were not
repeated for this documentation-only change; the three real public Docker checks
above are the new execution evidence. Task registration and runtime bytes are unchanged.

## Resulting decision

The existing default CLI snapshot is a behavior observation, not the authority for
the issue's scope. Explicit rule semantics, default activation and the requested
TSQL behavior need separate evidence. The public WHERE case provides a more direct
future diagnostic of A1's clause-sensitive behavior, but remains labeled as derived.
No adjacent paid A/B, test exclusion or new mandatory gate is justified merely by
having found this difference. The current task registration remains unchanged.
