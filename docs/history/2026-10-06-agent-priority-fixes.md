# Agent priority fixes after the current dev20 audit

Date: 2026-10-06. Every run is official=false and claim-ineligible.
This follow-up records implementation and provider-free validation. It does not
change the closed [audit](2026-10-06-current-agent-audit.md) or
[panel results](2026-10-06-current-dev20-results.md).

## Problem and decision

The audit found four concrete execution defects and a separate agent-judgment
problem. SQLFluff-1625 weakened source-located verification helpers. A confirmed
evaluation deadline stopped independent tasks. Solver work could consume the full
task deadline before evaluation. Marshmallow imported successfully but its ordinary
Schema.validate operation failed on collections.Mapping in the Python 3.10 probe.
These mechanisms threaten result integrity, completion, and usable verification,
so correcting them precedes another performance comparison.

All eight agreeing failed repairs also submitted while tools and edit budget were
available. More availability or a generic mandatory probe rule does not establish
better verification judgment. The smallest next diagnostic therefore distinguishes
correct verification from self-confirming expectations, a wrong entry point, and a
caught setup error without making another paid model call.

## Changes

1. The five current SQLFluff packages forbid edits to src/sqlfluff/testing/** using
   the existing scope contract. Reading remains possible. Gateway and isolated
   evaluation already enforce scope; native assessment now checks it before test
   projection. This is explicit package protection, not a new test-path heuristic.
2. The parallel coordinator continues independent rows after a confirmed task-local
   evaluation deadline. Classification requires a validated completion receipt,
   matching artifact hashes, settled accounting, completed native assessment and
   confirmed cleanup. The row retains its ERROR/native verdict and unsuccessful
   status. Real verdict disagreements and uncertainty still stop new admissions.
   Runtime stop_remaining=true now survives invocation-result serialization and
   evaluator uncertainty reaches the shared stop flag.
3. Development requests optionally reserve evaluation time inside the original total.
   The panel derives 330 seconds from public check timeouts plus a 30-second checkout
   allowance, leaving 1,470 seconds for the solver within the same 1,800 seconds.
   General default zero preserves old serialization. A bound, timely solver_finished
   receipt supports evaluation recovery without another model call or solver action.
   Late/mismatched receipts are rejected. No auto-submit or deadline extension exists.
4. Probe capabilities now exercise six ordinary project APIs in addition to imports
   and selected tests. Preflight checks the operation receipts, program hashes and
   current driver. Marshmallow uses a clean, digest-pinned Python 3.9 profile; Astroid
   keeps Python 3.10 and PyVista keeps its prepared graphics profile. Interpreter
   markers and dependency identities support Python 3.9. Runtime never pulls images.
5. An operator-only synthetic diagnostic freezes a public specification, literal
   expectations and the same test source across base/candidate phases. It records
   execution, readiness and behavior separately. It adds no solver tool, prompt,
   default gate, automatic replay, or claim of semantic attestation for arbitrary code.

Relevant contracts: [current panel](../../.agent/current-dev20.md) and
[runtime guide](../../.agent/guide.md).

## Evidence and validation

Evidence root: C:/pt/analyses/agent-priority-fixes-20261006-v1. New journals use
append-only, hash-chained dev-run-v1 records. Original panels and saved patches are
read-only inputs. Base implementation commit: 3a15acbda8698ecc784b552bba6145e2af29ac1b.
Final implementation identity and validation hashes are recorded in closeout.json.

- The original SQLFluff-1625 saved patch now fails explicit scope validation.
  Protection tests cover readable helpers, rejected mutation, isolated rejection
  despite passing fake checks, and native rejection before projection.
- The actual saved SQLFluff-1625 completion receipt also passes the new deadline
  classifier, preserving registered ERROR and native FAIL with no re-execution or
  journal change. This is a classifier-only check: full assessment under the new
  constraints first rejects that patch's forbidden helper edit.
- All 20 real public-operation canaries passed. The same Marshmallow operation fails
  in the old Python 3.10 environment and passes in Python 3.9. The clean official
  Linux image was explicitly acquired by digest; no evaluator image was pulled/built,
  no compatibility shim or task-source patch was introduced, and cleanup was confirmed.
- Reserve, durable evaluation recovery and Git deadline regressions: 57 passed;
  the 12 new focused tests passed in 55.122 seconds. Tests exercise real mock runner
  sequencing, late finishes, receipt mismatch, resume without new solver actions,
  total deadline enforcement and uncertain batch-stop propagation.
- The synthetic diagnostic executed 12 base/candidate phases. Correct repair gives
  FAIL-to-PASS; raw-value and constant repairs give FAIL-to-FAIL. Self-confirming
  expectations and the wrong entry point produce pytest PASS but are unfit to assess
  the contract. The caught setup-error control exits normally and passes pytest but
  remains SETUP_ERROR/NOT_ASSESSED. The fixture is trusted, locally authored code.
- Early test-fixture/temp-directory errors and their later successful runs remain
  separately preserved; an initial failed run was not overwritten as a pass.

The final integration group ran 66 tests in 130.003 seconds: 65 passed and one
documentation-size check failed. After condensing current guidance, all five
documentation checks passed. The 12 reserve tests took 99.762 seconds in this
concurrent run; other owning focused groups also remained below two minutes.
Ruff and diff checks passed. Both default and 330-second-reserve mock smokes reached
isolated EVALUATOR_PASS with zero cost; safety is NOT_RUN for the local mock sandbox.
Two operator result-export mistakes were preserved in the integration journal;
the successful default mock completion was recovered from verified durable evidence
without re-executing its solver or evaluator.

The complete suite passed: 4,264 passed, 18 skipped, zero failures/errors in
2,839.37 seconds with four workers. Raw JUnit/logs and final implementation hashes
are bound in closeout.json. Runtime source remained unchanged during that run.

## Result and unresolved question

The concrete defects are corrected and environment capability is demonstrated on
the 20 current snapshots. Reserving time does not guarantee evaluator completion.
The diagnostic shows why a successful test process is insufficient evidence of a
correct repair; it does not show the model choosing better expectations or tests.

Model behavior improvement: NOT_RUN. New repair acceptance: NOT_RUN. Paid model
calls: zero. No complete dev20 success-rate, speedup or generalization claim follows.
The full capability freeze/preflight was not rerun; this follow-up executed all
20 operation canaries and tested their admission integration locally.
No previous allocation was resumed, retried or expanded. A future comparison must
freeze new identities and explicitly authorize its task/model/cost scope. Its useful
question is whether the agent chooses requirement-grounded expectations and exercises
the relevant entry point before submission, while actual patch correctness, regressions,
cost and time remain the outcome measures.
