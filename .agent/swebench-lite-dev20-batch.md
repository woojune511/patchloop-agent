# SWE-bench Lite dev20 baseline batch

Prepared 2026-10-02. Status: **completed; allocation closed**. This is a closed
operator execution plan, never solver context or permission for another run.
The approved batch at `3077f81a` submitted 20/20 and resolved 10/20 under the original
hidden evaluator; registered/native verdicts agree. Cost: USD 5.01124395. See the
[outcome record](../docs/history/2026-10-02-lite-dev20-results.md). Unused budget
does not authorize any further calls. The previous three-task pilot remains separate.

## Question and fixed design

Can the unchanged agent baseline solve the remaining twenty Lite development tasks
once public checks and original evaluation have been calibrated? The pilot resolved
one of three tasks. The larger, fixed remainder can reveal recurrent failure classes
without selecting only promising tasks. This is a baseline measurement, not an A/B
comparison, adoption test, held-out estimate, or official benchmark submission.

All twenty calibrated packages are registered byte-for-byte under
`tasks/dev-train/swebench-lite-dev-<instance_id with __ replaced by ->`.
The original Lite dev split contains 23 tasks; the three completed pilot tasks are
excluded. No task from the 300-task test split is included. No replacement or tuning
after observing live results is permitted within this allocation.

Fixed execution order:

1. marshmallow-code__marshmallow-1343
2. pvlib__pvlib-python-1072
3. pvlib__pvlib-python-1154
4. pvlib__pvlib-python-1606
5. pvlib__pvlib-python-1707
6. pvlib__pvlib-python-1854
7. pydicom__pydicom-1139
8. pydicom__pydicom-1413
9. pydicom__pydicom-1694
10. pydicom__pydicom-901
11. pylint-dev__astroid-1196
12. pylint-dev__astroid-1268
13. pylint-dev__astroid-1333
14. pylint-dev__astroid-1866
15. pyvista__pyvista-4315
16. sqlfluff__sqlfluff-1517
17. sqlfluff__sqlfluff-1625
18. sqlfluff__sqlfluff-1733
19. sqlfluff__sqlfluff-1763
20. sqlfluff__sqlfluff-2419

## Executed paid scope

- Model: `gpt-5.4-mini-2026-03-17`; reasoning `xhigh`; output limit 25,000 tokens.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; exact
  `OPENAI_API_KEY` entry, read only by the provider adapter and never logged.
- One fresh solve per task, sequentially, no retry/resume/replacement.
- USD 1.20 per task and USD 24.00 invocation-wide maximum. Unused task budget is
  not transferred; remaining budget never authorizes additional calls or runs.
- Each task: 40 model calls, 100 actions, four accepted mutations, 1,800 seconds.
- Baseline policies: `segmented-v1`, `result-or-size-v1`, `brief-v1`, probes enabled
  with policy `none`, repair recheck, `protected-v1`, `per-call-v1` cost admission.
- Exact input counting immediately before dispatch, zero SDK retries, and the
  existing worst-case output admission remain mandatory.
- A settled agent failure or resource cap is a result, not a reason to retry.
  Stop the whole batch on count/transport/billing uncertainty, source/image drift,
  evaluator infrastructure errors, or unconfirmed cleanup. Preserve unstarted rows
  as NOT_RUN; do not silently drop failures from the denominator.

The official model page lists USD 0.75 input, USD 0.075 cached input, and USD 4.50
output per million tokens: <https://developers.openai.com/api/docs/models/gpt-5.4-mini>.
These match the existing cost table. USD 24 is a ceiling, not a forecast.

## Frozen inputs and execution

External evidence root:
`C:/pt/analyses/lite-dev20-registration-20261002-v1`.

- `manifest.json`: all twenty task/source/native-row hashes, image identities and
  resource scope. Private evaluator inputs stay operator-only.
- `batch.py`: the approved one-shot invocation is complete and must not be restarted.
  The preflight receipt binds exact HEAD, runtime, manifest,
  driver, clean tracked task bytes, prepared source trees and existing Docker images.
- `preflight.json`: written only after all twenty checks pass at the committed head;
  rechecked immediately before execution. A changed head requires a new review.
- Completed child state roots: `C:/pt/ld20live01/1` through `/20`; durable run journals
  and artifacts remain outside the repository. No existing live state may be reused.

Reuse calibrated prepared sources, eight already-built derivative images and the
other twelve original images. No image pull/build, source download, extra dependency
installation, or package regeneration is included. Solver workspaces contain public
source only; neither reference patches nor private tests/results are supplied.

## Evaluation and decision

Keep exact submitted diffs and official-format predictions. Evaluate submitted
patches with the original native harness and pinned per-row images, in addition to
the registered isolated evaluator. No model calls are needed for this evaluation.
Missing submissions, infrastructure failures and safety outcomes remain separate.
Any disagreement between original and registered verdicts blocks aggregate claims
until diagnosed; never rerun the solver to improve a result.

Report attempted/completed/submitted/original-resolved counts, public regressions,
safety, NOT_RUN, cost, calls and elapsed time, with task-level evidence. Calibration
PASS is not agent success. The eight environment corrections and two public-check
projections must accompany the results. Preserve the original three-task pilot
separately even if presenting a descriptive total over the dev split.

The result chooses the next important recurring failure to investigate. It does
not itself authorize a new prompt/tool change, more paid runs, or a 300-task run.
