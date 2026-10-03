# SQLFluff 1625: public decision trace review

## Scope and decision

After the [public contract review](2026-10-03-sqlfluff-public-contract.md), inspect
where the saved agent trajectories first depart from supported evidence. The scope
is four existing fresh 1625 solves (A1/B1/A2/B2) and two subsequent seeded runs.
These are bounded public trace observations on one development-exposed task, not
a new model comparison or a cross-task failure-rate estimate.

The strongest observed mechanism is an unsupported explanation of regression
feedback followed by a repair condition chosen to reconcile examples. A1 also
declares a false last-call constraint despite ample delivered resources. The tools
and source access needed to investigate were available. Preserve the baseline:
no runtime arithmetic/admission defect or effective replacement intervention has
been demonstrated. This closes the trace audit without another prompt variant,
compulsory probe, state field or paid allocation.

## A1: earliest unsupported explanation and decisive narrowing

Source run: `run_dev_31b82ad97f904d2f` under `C:/pt/pv1live01/1625A1`.
Sequences below refer to its original hash-chained journal.

| Turn / event | Observation or declared decision | Interpretation |
| --- | --- | --- |
| T1-2, seq 13/32 | Reads L031 and searches for tests; describes a missing no-join guard. | The requested issue and owning source were available. |
| T3, seq 48 | Adds a broad `len(from_expression_elements) <= 1` early return. | A testable first candidate; no dialect restriction. |
| T4, seq 66 | Regression fails only `alias_single_char_identifiers` and `alias_with_wildcard_identifier`. | Output establishes missing L031 in those cases, not a parser-count defect. |
| T5, seq 77 | Says failing cases evidently have a JOIN shape collected as one FROM element, then reads the fixture. | Earliest unsupported causal explanation: the inputs are actually no-join SQL. This is declared before reading them. |
| T6, seq 92 | Acknowledges existing no-join alias failures; searches for issue text and dialect patterns. | The initial JOIN explanation is corrected. It should not be described as permanently retained. |
| T7, seq 112 | Exempts one-table aliases used in SELECT but not after FROM, calling that the supported repair. | Decisive unsupported narrowing: neither the issue nor executed behavior supplied the SELECT-only boundary. |
| T7, seq 122 | Automatic required recheck passes. | Establishes compatibility with the selected public suite, not coverage of the new condition. |
| T8, seq 130 | Submits, acknowledging the issue example remains unprobed and mentioning the final completion call. | No probe was attempted. The supplied budget contradicts a last-call restriction. |

The exact failing fixture strings were delivered in public source messages at
T6, T7 and T8. Thus missing access to those inputs does not explain the final
SELECT-only condition. The two fixtures require warnings for unused/wildcard
aliases; preserving them does not establish a general exemption based on reference
location. The earlier public WHERE diagnostic independently demonstrated the
consequence of A1's chosen condition: adding a WHERE reference reintroduces L031
while the original issue examples remain clean. That case is still labeled derived,
not a supplied issue assertion or a complete correctness oracle.

At T8, actual delivered state had 33 model calls, 86 tool actions, two accepted edits,
1,280 seconds and USD 2.4033735 remaining. `run_probe` was offered, exploration was
open and `model_turns_available_for_exploration` was 32. In contrast,
`completion_budget_calls=1` and `minimum_completion_calls=1` describe the remaining
completion path, not the number of calls available. Current runner source assigns
the former from `budget.protected` (`patchloop/dev/runner.py:885`). Arithmetic and
admission agree with the delivered state.

The public rationale is consistent with confusing these concepts. It does not
prove which input caused the choice, that a renamed field would change it, or that
an extra probe would produce a correct repair. This is an observed explanation/state
mismatch, not a demonstrated scheduler restriction.

## A2: recurrence and a useful falsifying observation

Source run: `run_dev_f3ec232880584e90`, `C:/pt/pv1live01/1625A2`.
The first regression at seq 93 names the same two single-table fixtures. T7/seq 104
nevertheless describes joined tables missed by a narrower crawl and edits traversal.
After another failure, T10/seq 154 switches to top-level enumeration. The actual
failing fixture is read at T13/seq 209, after three accepted edits in total.

T15/seq 240 finally runs a public probe. Its output shows top-level and recursive
counts both equal one for the single-table cases and both equal two for the JOIN
case. The probe directly weakens the traversal explanation. T16/seq 253 explicitly
acknowledges this and replaces the broad bailout with a TSQL/select-alias exception.
The final required recheck passes; no final-diff probe follows.

This supplies a second occurrence of explaining a failing test as a parser/traversal
problem before inspecting its actual input. It also shows that executable evidence
can change a decision. At submission A2 still had 24 calls and 862 seconds, but all
four accepted edits had been consumed. Unlike A1, further repair really was blocked
by the edit cap; do not describe all rows as unconstrained. The record does not prove
that earlier probing would have led to an accepted patch.

## Contrasts that limit a general diagnosis

| Row | Relevant behavior | Limit on inference |
| --- | --- | --- |
| B1, `run_dev_ae26a17d5f29413c` | After the same broad-guard failure, narrows by TSQL and executes a final probe of the issue query plus an ANSI contrast. | Available tools can be used successfully. Its T11 probe is selected with `completion_budget_calls=1`. |
| B2, `run_dev_1638101e30964195` | Applies a TSQL guard initially; final probe tests standalone and joined TSQL examples. | T9 also chooses a probe with completion budget 1. The field is not a universal stopping cause. |
| Seeded A1/B1 | Each performs required check then finish; no inspection, probe, selected test or edit. | Tool availability alone does not produce verification selection. The seeds' creation paths cannot be inferred from these two-turn runs. |

B1/B2 probe results passed their chosen assertions, but all four fresh 1625 runs
failed original acceptance in the [closed comparison](2026-10-03-positive-verification-results.md).
The contrast therefore does not justify compulsory probing or prove repair success
from these examples. Both seeded final turns offered `run_tests` with 39 calls and
three edits remaining, confirming that their optional selection was not barred by
those resources. The old CLI discrepancy remains a compatibility question, not a
validated must-repair criterion for the seeded agent.

Removing completion advice is also not an untested generic remedy: the earlier
[completion advice comparison](2026-09-26-completion-status-comparison.md) retained
zero accepted repairs in both arms on different tasks. That does not rule out a
specific budget-label effect here, but prevents treating advice removal as an
evidence-backed default improvement.

## Evidence and confidence

- **Directly observed:** specific public claims, edits and check/probe outputs;
  the untested SELECT-only boundary; input/state budget mismatch; B's contrasting
  choices; A2's consumed edit budget.
- **Supported local explanation:** regression feedback was overinterpreted as a
  particular structural cause before the failing inputs were established, followed
  by narrowing to satisfy known cases. This recurs in A1/A2 on this task.
- **Unresolved:** why the model made those inferences internally, how much completion
  wording contributed, recurrence across tasks, and which intervention improves
  accepted repairs without regressions. A recorded rationale is observable output,
  not access to an internal causal mechanism.

No reference implementation, hidden test program or private evaluator failure
artifact was examined. Projection selects public tool requests, results, input
state and budgets; it excludes provider reasoning/continuations and private
evaluation events. Some solver-authored explanations call the supplied issue query
"hidden"; that wording is not evidence that hidden material was supplied.

External evidence: `C:/pt/analyses/sqlfluff-trajectory-review-20261003-v1`.
`review.py` validates six original journal chains, verifies context/input artifact
hashes and matches delivered budget state on all 51 turns. Public projections retain
event sequences and source journal hashes; original bytes are unchanged. The new
`run_dev_sqlflufftrajectoryreview` journal binds the review scope and artifacts.
Result hash:
`sha256:c1cf2359ba5e5acddb0560b5e2e33231bd821ef252292733c1c36b59e6a5bb93`.
No new model, Docker, repair, reference or evaluation execution occurred; provider
cost is zero. Every result remains official=false and claim-ineligible.

Documentation layout/link tests: five passed in 0.14 seconds (`docs.xml`); Ruff and
diff whitespace checks passed. Runtime and task registration are unchanged. Full
tests and mock smoke were not repeated for this documentation-only trace audit.
