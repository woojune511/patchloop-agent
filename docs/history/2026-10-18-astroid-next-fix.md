# Astroid: acquire the original caller evidence before another policy change

## Decision and scope

Prioritize evidence acquisition for the original failing call path. The four
Astroid trajectories never established how `pylint src/project`, from `root_dir`,
reaches the chosen repair branch. Correctly exercising a related helper did not
close that gap. Next investigate the public reproduction/caller environment, with
no provider call, before changing source retention or adding general judgment
instructions. This is a proposed diagnostic, not an adopted runtime intervention.

Selected because Astroid was the only task without an accepted repair in any arm
of the [closed E/J comparison](2026-10-18-repair-mechanism-results.md). These are
four trajectories of one development-exposed task, one model, one repetition per
arm; recurrence here is not an estimate of prevalence across tasks. E selects
question-focused evidence; J changes interpretation/purpose presentation.
Earlier evidence remains in the [plan-closure record](2026-10-16-astroid-plan-closure.md).

This follow-up is post-unblinding. It does not replace the original sealed review
or grades. Only public requests, actions, source excerpts, dependency metadata,
saved replay comparisons and already-published outcome labels were read. No
private evaluator bodies, reference patch or encrypted reasoning were inspected.

## What the existing logs distinguish

| Row | Evidence missing | Error despite delivered evidence | Recorded outcome |
| --- | --- | --- | --- |
| E0J0 | Original caller; first probe fails while importing `MANAGER`, second uses module-name resolution with a context file | Turn 34 favors an init-dependent discovery explanation although `list_all=True` explicitly bypasses that condition and an existing test targets it | Test addition only; unsubmitted, `INCOMPLETE_RESPONSE`; acceptance `NOT_RUN` |
| E1J0 | Whether the original caller produces `PKG_DIRECTORY` with no initializer; no targeted execution or finder-body evidence establishing that premise | Conditional conversion to `PY_NAMESPACE` follows the delivered branch, but task-level adequacy cannot be judged as evidence-complete | Submitted; public suite PASS, registered/native FAIL |
| E0J1 | Original caller; the probe compares module-file lookup and import helpers | Turn 34 passes a full module prefix with an already-advanced parent directory despite delivered finder code showing how the prefix is consumed | Later added regression FAIL; no subsequent model request; unsubmitted, `LIMIT_REACHED`, acceptance `NOT_RUN` |
| E1J1 | Original caller and directory/AST/F0010 route | A successful file-to-module helper test becomes an unsupported claim of end-to-end verification; task and exact probe scope were delivered | Submitted; public suite and helper probe PASS, registered/native FAIL |

Acquisition and judgment labels overlap. Absence of the caller link does not mean
every local judgment lacked evidence; conversely, a bad coverage claim does not
prove the hidden reason for rejection. Two submitted failures and two unsubmitted
outcomes must not be reported as four evaluator failures.

### Evidence-present errors are concrete, but differ in scope

- **E0J0 turn 34, request sequence 487:** actual delivered
  `astroid/modutils.py:474-491` includes the documentation for non-package discovery
  and `if not list_all and "__init__.py" not in filenames`. Delivered
  `tests/unittest_modutils.py:345-349` already tests a non-package with `list_all=True`.
  Neither supports claiming that this mode requires an initializer. Adding another
  discovery test does not establish the missing caller connection.
- **E0J1 turn 34, sequence 476:** delivered `modutils.py:261-271,308-323` and
  `interpreter/_import/spec.py:130-148,331-369` expose the argument relationship.
  On the reported nested layout, the proposed call has prefix `['src', 'project']`
  and parent `root/src`; the finder starts again with `src`. This is a concrete
  source-level mismatch. The subsequent helper regression fails with ImportError,
  consistent with the diagnosis; it does not uniquely identify every cause of
  failure or establish the original CLI behavior. The final failed check occurs
  after the last dispatched request, so the model did not ignore a delivered FAIL.
- **E1J1 turns 26,28,30,32,33:** the problem begins before the final assessment.
  Turn 26 observes ImportError from `modpath_from_file` on a temporary tree with
  its root inserted into `sys.path`. At turn 28/sequence 380 the plan says this
  confirms the failure is in file-to-module resolution rather than AST building.
  Turn 30 records that exclusion as a note. The observation establishes a helper
  failure; it does not exclude another route from the original directory caller.
  Turn 32's plan then treats two helper assertions as the completion criterion.
  Their success is real; turn 33/sequence 451 expands it into "end-to-end" repair
  of the original failure. The source, original issue and exact probe scope were
  available for detecting that overstatement.

E1J1 had 13 remaining model calls, 68 actions and USD 0.4782601 before the turn-28
request, with read/search/probe tools offered; at turn 33 it still had eight calls
and USD 0.2700778. Thus hard resource exhaustion does not explain its early scope
substitution. In contrast, both E0 rows had only replace/stop offered at turn 34
despite seven nominal calls remaining. Remaining calls alone are not evidence
that another probe was available. The original caller's executability also remains
unverified, even when a generic probe tool was offered.

J1 already says to limit experiments to actual inputs/results, retain original
purpose and distinguish execution from source inference. Its warnings and
unverified-note labels did not prevent the E1J1 scope substitution. Another generic
warning is therefore not the next supported intervention. A bounded, nonexclusive
judgment target remains: do not replace an unresolved original cause with a helper
failure, and do not describe helper coverage as original-path execution.

### Missing evidence is not established to be a retention failure

The four runs contain 128 dispatched requests, five probe programs and 16 later
handoffs. The saved same-state comparisons have **zero E-induced changes to source
or tool-exchange bodies** across these Astroid handoffs. Thirteen have no focus
declaration; the other three already retain their cited bodies. E-on rows have no valid
focus declarations. The four-byte priority disclosure still differs; this is not
a claim that full E0/E1 prompts or independent trajectories are identical.

There are 3,339 current-version source-line loss occurrences, including repeated
lines at different boundaries. They are not 3,339 necessary facts. Builder/callback
bodies are sometimes lost and reread. E0J1's finder body is lost at sequence 511,
after the wrong edit at 476; that later loss cannot explain the earlier error.
E1J1 rereads the callback after the loss at 379. The missing original Pylint caller
was never acquired, so retaining more of the observed Astroid body would not itself
supply that link. Loss may still add work; its causal contribution to failure or
output exhaustion is not identified by these logs.

### The acquisition environment is an unresolved prerequisite

The public issue names Python 3.9.1/Pylint 2.12.2 and a directory invocation from
`root_dir`. The five saved probes use the prepared Python 3.10 Astroid environment.
Its bound dependency descriptor lists lazy-object-proxy, setuptools and wrapt;
its file inventory contains no Pylint distribution or package. None of the four
trajectories requests a Pylint-named read/search or executes the original command.

This establishes absence from the prepared probe bundle, not a fresh importability
test of every tool environment. Do not infer what the registered-check image
contains or claim the task is impossible. Nor assume that instructing the solver
to run the exact CLI would be actionable under the existing probe contract. A
different Python/environment and different entry point make the observed helper
failure insufficient to establish reproduction of the reported F0010.

## Next bounded question

First establish, from public material, the original caller's entry, working
directory, import-path setup, arguments and observed failure. Determine whether
the existing bounded execution surface can supply that evidence. If the caller
dependency is unavailable, report that capability gap; any prepared-environment
change is a separate intervention, not a silent modification of the closed panel.
No package acquisition, image launch or target execution was done in this audit.

The smallest useful subsequent diagnostic compares the unchanged public base and
the saved candidate on the same original caller/setup, or on a smaller boundary
whose equivalence is established by public caller source. Observe whether the
reported failure occurs and whether the candidate branch is actually reached.
Do not substitute a synthetic helper failure for F0010 merely because the file
tree matches. Stop without a repair claim if the original failure is not reproduced
or caller equivalence cannot be established.

That result separates the next engineering choices:

1. If the public caller cannot be observed with the supplied environment, address
   evidence access/reproduction capability first.
2. If it can be observed but the solver selects an unrelated probe or discards the
   original purpose, target probe selection and scope judgment. Reuse the existing
   bounded plan/assessment fields; do not impose a blanket probe quota or finish
   gate. Properly qualified source inference remains allowed.
3. If a delivered, complete caller counterexample is ignored, prioritize judgment
   with evidence fixed. Only evidence acquired and subsequently unavailable at a
   consequential decision justifies reopening the retention mechanism.

These are discriminating conditions, not a queued paid experiment or proof that
additional evidence improves repair success. The existing mini-model capability,
local code-reading mistakes and resource endings remain plausible contributors.
No selector, prompt, transition timing, two-reference limit or budget changed.

## Evidence and validation

External follow-up: `C:/pt/analyses/astroid-next-fix-20261018-v1/`:

- `audit.py`, `audit.json`: source excerpts, decisions, offered tools, remaining
  budgets, five probe programs/results and four row classifications' raw basis.
- `input-manifest.json`: 420 hashed inputs, including the four validated journal
  chains, original request/context artifacts and sealed public projections.
- `before.json`: repository byte baseline and frozen arm heads.
- `validation.json` and `runs/run_dev_astroidnext18.jsonl`: local checks and
  preservation receipts. The journal is append-only `dev-run-v1`.

Reconstructed delivery inventories for all 128 saved public requests; checked
32 existing normal/optional-omitted replay records covering 16 handoffs, including
actual-arm calibrations. This is local artifact validation, not a new model or
target execution, and not a fresh full counterfactual admission/count exercise.
Documentation layout/link tests: five passed; Ruff and whitespace checks passed.
Runtime source and the user's pre-existing `AGENTS.md` edit remain unchanged.
Full runtime suite and mock smoke were not rerun for this documentation-only
follow-up. New provider/count calls, target runs and spending: zero.
