# Seeded public-test selection diagnostic

Question: with `run_tests` available, does the agent independently select public
checks that expose the saved A1 CLI regression, repair it, and preserve both public
TSQL examples? B1 is a preservation control for these three checks. It is not a
fully correct reference solution. Prior public replay established the missing
verification distinction; autonomous selection remains untested.

## Frozen design

- Task: `dev-train/swebench-lite-dev-sqlfluff-sqlfluff-1625` only.
- Order: A1, then B1, once each, fresh current-runtime runs seeded with their exact
  submitted patches. Same ordinary baseline instructions, tools and resources.
- Model: `gpt-5.4-2026-03-05`, xhigh, desired output ceiling 25,000 tokens;
  per-call admission may reduce that ceiling. Credential: repository `.env` at
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Per run: USD 3, 40 model calls, 100 actions, 1,800 seconds, four mutation slots.
  The existing seeded-run seam consumes one slot; three new edits remain.
- Invocation total: two solver runs, USD 6. Zero SDK retries; no replacement,
  resume, extra repetition or budget expansion. Stop all remaining runs on count,
  transport, billing, execution cleanup or public-assessment uncertainty.
- No prompt variant, old conversation, plan, result, reviewer advice, extra
  source snapshot or public counterexample is supplied. The shared existing
  `candidate_reconsideration` notice only identifies a previously authored patch.
  Seed labels/source-run IDs are journal provenance, not model input.
- Operator criteria, test node and calibration artifacts stay outside the solver
  context. Public issue/source/diff and the generic registered suite remain visible.

Existing `candidate_review_repair.run_seeded` runs the normal runner and isolated
evaluator in a dedicated sequential process. There is no runtime/default change.
The driver is `diagnostics/selected_tests_diagnostic.py`; generated evidence lives
at `C:/pt/analyses/selected-tests-diagnostic-20261003-v2`. Fresh calibration checkouts
use `C:/pt/stcal02`; paid runs, if separately authorized, use `C:/pt/stlive01`.

## Measurement and decision

Calibrate exact public-base/seed checkouts before freezing: base has CLI PASS and
example FAIL; A1 has CLI FAIL and example PASS; B1 passes both. The CLI selector is
`test/cli/commands_test.py::test__cli__command_directed`. The example program checks
the public issue's two TSQL inputs for exact empty violation lists. No extra output
normalization is allowed. Setup errors/truncation are uncertainty, not task failure.

After each solver stops, assess its exact submitted diff with both public checks
in a separate operator journal; never feed those results back. A missing submission
is recorded separately with final assessment NOT_RUN. Keep original isolated
acceptance and safety verdicts separate, even if public criteria pass. Record model
calls, actions, new mutations, cost and solver time; operator check time is separate.

Review public action/result evidence for selection, interpretation, repair and
recheck. A1 success requires final public CLI/example PASS plus an independently
chosen agent check that exposed the CLI mismatch and a current-diff recheck. Choosing
a containing test file also counts if its actual output covers that case. Equivalent
public probes may establish behavior but do not establish selected-test-tool use.
B1 preservation requires a submitted diff that still passes all three checked cases.
Tool invocation counts, a model's explanation or submission alone are not success.

If A1 is never checked, the selection problem remains; if a failure is delivered
but mishandled, interpretation/repair is the next question. If repaired but not
rechecked, final operator PASS alone does not prove the full verification routine.
B1 damage weakens the safety of this approach. Two seeded runs establish neither a
fresh-solve rate nor a causal quality gain from adding `run_tests`; no automatic
adoption or further comparison follows. Any later experiment needs new evidence.

## Execution

Run `python -m diagnostics.selected_tests_diagnostic prepare --root <external-root>`
without provider calls. Commit the driver/contract, then run `freeze` at that root.
The packet binds commit, runtime/task/model identities, source/dependency descriptors,
seed bytes, calibration, driver and this contract. `run --packet-hash <hash>` rejects
changed conditions and requires an external `authorization.json` recording a new
human approval bound to that packet. The earlier eight-run allocation is closed.

Official [GPT-5.4 pricing](https://developers.openai.com/api/docs/models/gpt-5.4)
was checked on 2026-10-03: USD 2.50 / 0.25 cached / 15 output per million tokens;
the current runtime prices match. Provider counting and dispatch use the existing
bounded cost controller. Calibration never calls a provider or private evaluator,
and uses already installed images/dependencies without acquisition.
