# External mini-SWE-agent baseline preparation

Date: 2026-10-16. Provider-free preparation; live execution NOT_RUN.
Every proposed run remains official=false and claim-ineligible.

## Problem and decision

The user requested an external agent baseline and selected all 20 existing
SWE-bench Lite dev-train instances. Recent PatchLoop comparisons had not established
a quality gain. An independently designed harness on the same public tasks can
locate differences in repair outcomes before proposing more PatchLoop mechanisms.
This is a descriptive agent comparison, not a test of one isolated feature.

Use upstream mini-SWE-agent v2.4.6 at
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`. Preserve its DefaultAgent, SWE-bench
prompts, Responses action parser, observation/error templates and linear history.
An operator adapter adds exact pre-dispatch input counting, cost reservations,
durable usage settlement and zero retries. Its environment restricts native bash
to an offline container; it does not replace mini's tools with PatchLoop tools.
PatchLoop solver policy and runtime are unchanged by this work.

The [execution contract](../../.agent/mini-swe-baseline.md) records the question,
conditions, known differences, interpretation and stop rules. A better mini result
would motivate inspection of public traces, not establish a causal mechanism.
Failure by both agents would not by itself establish a model ceiling. No outcome
automatically adopts a runtime change or authorizes another experiment.

## Frozen proposed run

- Same 20-instance roster and base commits; current public dev-train packages.
- `gpt-5.4-mini-2026-03-17`, xhigh, desired output ceiling 25,000, default tier.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; never copied into a
  container, task prompt, subprocess environment or artifact.
- One attempt per task, one worker; USD 1.20 per task and USD 24 total, no transfer.
- At most 40 model generations and 100 bash actions per task. No retry or resume.
- Solver allowance 1,470 seconds; independent native evaluation allowance 330
  seconds, including its 300-second test timeout. Cleanup/host overhead is separate.
- Mini retains unlimited edit count and source-only submission. Historical
  PatchLoop has registered tools, four accepted edits, segmented context and
  automatic rechecks; some panels also allow additive tests and use two workers.
  The staged timeout is not identical to an invocation-wide deadline.
- Unchanged native grader revision `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` and
  exact locally available instance images. No image pull/build or dependency install
  occurs inside a solver container.

Prepared manifest: `C:/pt/mini20prep04/manifest.json`.
Canonical packet: `sha256:3e17672013e891246a91dd160650dbde81a758f7c5d53e3ab19986833b721132`.
Solver/adapter commit: `a6987993513a9f5bf38cc6b555db42bd37097b1b` in the attached
`C:/Users/geonj/.codex/worktrees/mini-swe-dev20/PatchLoop` checkout.
The isolated checkout keeps concurrent dev-head changes out of this packet.
Proposed fresh live state: `C:/pt/mini20live01`; no authorization file is present.

## Preparation findings and evidence

Only a verified public base-commit archive and public issue/constraints/check
descriptions enter the solver environment. A fresh tmpfs masks the image's original
checkout, with one synthetic Git commit, no remotes, no host mounts, no network and
a read-only root filesystem. The solver container is destroyed before private
grading. External hash-chained journals and content-addressed artifacts retain
operator actions, model input/output, accounting and cleanup.

Environment checks found preparation defects before any provider call:
copying into a read-only image required streaming the source archive into tmpfs;
masking SQLFluff's editable checkout removed its package metadata. The latter is
recreated using public `setup.py egg_info`, without installing dependencies or
changing tracked source. An initial unconditional metadata query also broke older
pydicom Python and an Astroid checkout without `setup.py`, although their public
imports already worked. The final implementation removes that unnecessary query:
only an observed metadata-related import failure triggers regeneration. Regression
tests cover successful imports, missing metadata and unrelated import failures;
pydicom, Astroid and SQLFluff controls then imported with clean tracked source.

Earlier failed preparation evidence stays under `C:/pt/mini20prep01`,
`C:/pt/mini20prep02` and `C:/pt/mini20prep03`. Their manifests are not the proposed execution packet.
No live task was attempted, replaced or rerun during these operator-only checks.

Validation:

- Frozen preflight: all 20 public environments PASS, with confirmed cleanup, zero
  provider calls and USD 0. Receipt: `C:/pt/mini20prep04/preflight.json`.
- Focused adapter and documentation checks: 23 passed in 1.63 seconds; Ruff passed.
  Cases cover pre-dispatch admission, billing uncertainty, replay, public-only input,
  environment isolation, import compatibility, command timeout and cleanup failure.
- Actual upstream DefaultAgent and Responses parser/observation transport ran with
  two fake responses. Its submitted comment-only patch reached the unchanged native
  grader and failed as expected, with scope PASS and cleanup confirmed. Receipt:
  `C:/pt/mini20prep01/mock-native-control/smoke.json`. Actual provider calls/cost: 0;
  simulated usage in the mock ledger is not incurred cost.
- Positive seam control: the unchanged historical accepted Marshmallow patch
  (`sha256:bb0747c46d17c412b8ef13e069c124d6b4cce0c221b0507680af85d48c71294b`)
  passed scope and native grading with confirmed cleanup. Receipt:
  `C:/pt/mini20prep04/operator-positive-control/control.json`. It stayed outside
  solver inputs. This is a saved-patch control, not a fresh agent solve or mini score.
- Frozen PatchLoop runtime mock smoke reached isolated EVALUATOR_PASS with zero
  cost, run `run_dev_aceff2969d69411e` under `C:/pt/mini20prep02/mock-patchloop`.
  Mock safety remains NOT_RUN.
- Full fast suite: 5,116 passed, 19 skipped in 3,414.83 seconds (56m54s), using
  `tests -n 4 --dist loadfile --max-worker-restart 0 --durations=20` and external
  basetemp `C:/pt/tmp/mifull01`. The suite began at `234b25b7`; core runtime bytes
  stayed frozen. Later adapter metadata corrections are covered by the 23 focused
  checks and the final 20-image preflight above. Final documentation checks also
  passed (5 tests in 0.11 seconds). Tail: `C:/pt/mini20prep04/full-suite-tail.txt`.
- An earlier shared-checkout suite was interrupted because concurrent changes
  prevented a stable validation target; it is not a passing test result. The attached
  frozen checkout supplies the completed core-suite evidence.

Live performance, registered PatchLoop runtime/safety evaluation for mini and any
improvement claim remain NOT_RUN.

## Approval and later reporting

The existing AGENTS.md hard gate 2 prohibits unrestricted shell for the coding
agent. Native mini needs an explicitly authorized exception for bash only inside
this isolated benchmark container. Hard gate 5 also requires exact task/model/
credential/repeat/cost scope for live OpenAI work. Neither the task-selection answer
nor a provider-free preflight supplies those approvals. An authorization JSON may
record a human decision but cannot replace it.

After an approved run, report all 20 planned tasks: native PASS/FAIL, scope failures,
unsubmitted/NOT_RUN rows, infrastructure, cleanup, known costs and uncertain billing.
Compare each historical PatchLoop panel separately. Preserve the corrected panel's
11 PASS / 7 FAIL / 2 NOT_RUN and its separate two-task supplement; do not pool them
into a newly measured full-panel success rate. A public-check PASS is not task
acceptance, and mini container isolation is not PatchLoop registered-tool safety.
