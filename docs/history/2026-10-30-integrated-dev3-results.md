# Integrated development run: three submitted repairs accepted

Date: 2026-10-30 KST. Paid allocation: **CLOSED**, all usage settled.

## Purpose and conditions

The user prioritized a fast integrated development loop over separate feature
comparisons. Run the current agent from scratch on three development-exposed
tasks, inspect correctness, cost and time, and use concrete failures to choose
the next fix. This run does not isolate individual feature effects.

Tasks 3 (pvlib1154), 13 (Astroid1333) and 18 (SQLFluff1733) cover numeric boundary
handling, import-path resolution and formatter-rule interaction in three repositories.
Each ran once with GPT-5.4-2026-03-05/xhigh, 25,000 desired output tokens,
current/brief-v1, segmented-v1, public-checks-v1, ordinary probes, repair recheck,
protected inspection and per-call cost admission. Limits were 40 model calls,
100 actions, 12 accepted edits and 1,800 seconds per task, including a 330-second
evaluation reserve. No prior patch, operator repair or saved model state was seeded.

The user approved repository `.env`, two workers, fixed USD4 per task and USD12
total, with no transfers/retries and stop-all on accounting or operational uncertainty.
The existing batch scheduler and isolated evaluator were reused; no second native
evaluation or new experiment framework was added. All required images were local.
The pricing check used the [official standard rate](https://developers.openai.com/api/docs/pricing):
USD2.50 input, USD0.25 cached input and USD15 output per million tokens, within
the runtime's 60K input bound. Counting remained immediately before dispatch.

Execution HEAD: `467d08c545aba96b41543fa24842dcdb20176435`.
Runtime hash: `sha256:45e1bfe96a20897102c6903cc14a19e261f82bb5d4a0887a8f63e579707acb7c`.
The preparation HEAD was earlier by one documentation-only commit; runtime bytes
and all task/request bindings stayed fixed throughout execution.

## Results

| Task | Independent acceptance / safety | Accepted edits | Model calls | API cost | Task elapsed | Model dispatch-to-return |
|---|---|---:|---:|---:|---:|---:|
| 3: pvlib1154 | PASS / PASS | 1 | 9 | USD0.491115 | 278.272 s | 190.816 s |
| 13: Astroid1333 | PASS / PASS | 2 | 26 | USD1.9359835 | 808.135 s | 611.188 s |
| 18: SQLFluff1733 | PASS / PASS | 1 | 18 | USD1.3781115 | 724.194 s | 451.518 s |

All three submitted. Total cost **USD3.80521**; two-worker batch wall time
**1,005.053 seconds (16 min 45 s)**, excluding operator preparation and follow-up.
All 53 model calls settled, with no batch stop, retry or undispatched row.
Provider dispatch-to-return occupies approximately 69%, 76% and 62% of each row's
elapsed time. These overlapping per-task timings are not additive batch wall time.
They identify substantial model latency in this run, not a tested speed intervention.

### Public repair evidence

- **pvlib:** One `edit_files` action changed `reindl()` and created a test file.
  It handles GHI=0 without division warnings and returns zero for scalar, ndarray
  and Series inputs. The registered check passed 98 tests; a helper probe confirmed
  zero inputs and a positive-input control. The new test file was outside that
  check's fixed file selection and the agent did not execute it with `run_tests`.
- **Astroid:** The first change normalized relative paths too broadly using
  `realpath()`. Public regression reported one symlink test failure with 1,231
  passing tests. The agent then restricted `abspath(expanduser(...))` normalization
  to explicit relative search paths and preserved existing symlink-sensitive
  fallbacks. The second check passed 1,232 tests, including the added regression.
  Replaying the same helper program without adding cwd to `sys.path` changed the
  prior missing-initializer failure into the expected module and actual file path.
  Full `pylint src/project` CLI behavior was not directly replayed.
- **SQLFluff:** One `edit_files` action changed L036 to carry the following item's
  indentation when moving the first SELECT item onto a new line. The public check
  passed 506 tests. A final `sqlfluff.fix()` probe produced the expected WITH-query
  indentation and preserved the standalone SELECT control. The new test filename
  ends in `_combo.py`, outside `tox.ini`'s `*_test.py` automatic collection pattern;
  the agent did not run that file explicitly.

All public delivery states remain `unverified_delivery`; independent acceptance
PASS is a separate result. Private evaluator details were not inspected or fed
back to any model. No hidden/reference material informed the public diagnosis.

## Decision and follow-up

Keep the integrated configuration. All three used multi-file transactions; two
created new test files. This establishes live use and accepted repairs under these
conditions, not causal gain from the file tools or the 12-edit limit. Actual edits
were 1/2/1, so the higher mutation ceiling was not exercised beyond the old limit.
No rollback was needed. Do not schedule a separate quota/forecast ablation first.

The repeated actionable gap is **new tests being written but omitted from execution**.
The existing `run_tests` supports these newly tracked files; this is not missing
execution capability. `check_review` reports the registered `python -B -c` wrapper
as an unresolved selection, so concise check feedback does not reveal the omitted
new files. The next small improvement should make actual test selection visible,
without adding a new submission gate or a new tool. Shortening unnecessary model
turns is a latency candidate; no speed gain has been measured yet.

Operator-only execution of the two omitted test files is recorded separately below;
it cannot retroactively become an agent-selected check or part of the live solve.

### Operator-selected new tests

After all three model runs terminated, the existing registered `selected_check`
and Docker sandbox executed each omitted file explicitly on its unchanged submitted
candidate. pvlib's new file passed its one test (6.229 s sandbox duration); SQLFluff's
new file passed its one test (17.836 s). Both candidate/test bytes and original solver
journals remained unchanged. This added two public-check dispatches and zero model
calls. It confirms that the files can run and pass, while preserving the observed
agent-side execution omission.

Follow-up root: `C:/pt/integrated3-new-tests-20261030-v1`.
Result artifact: `sha256:0d5659959c57263344c201d848fe4ca3ceec7356f06b707c8ca7659e58c37d31`.
Journal final hash: `sha256:9dc0e0a55b53df8742fef18254a2ead95059f718b226690636f9596f113fe546`.

## Evidence and validation

- Approved manifest: `C:/pt/integrated3-20261030-v1/manifest.final.json`,
  `sha256:6bd2a4f05f1222904374f9f76525b997be430bfbad7b57c90ec4a10d3d213214`.
- Run root: `C:/pt/integrated3-run-20261030-v1`.
- Result: `result.json`, `sha256:d2dc09b5a48aca9eb434c86162a31267f2d8d7fb7669821c7377b30aab2e753a`.
- Derived accounting/timing: `summary.json`; preparation and all run journals are
  hash-chained `dev-run-v1`. No additional model call was made by analysis.
  Summary artifact: `sha256:449073ac48c8d937f80029c6e788ef391db640f2959d22c7990b267abb684847`.
  Final batch journal: `sha256:ca8665f7947c222099520cd48f962d4f479b008475fbcd9535177f95e47fd30c`.
  All 53 actual dispatched requests match their preceding token-count identities.
- Existing batch tests: 25 PASS / 19.50 s. Launcher assessment controls: 7 PASS.
  Prepared source/dependency bytes and probe/evaluator image identities validated.
- Agent runtime was unchanged; its existing 1,101-test quick/Ruff validation remains
  the implementation baseline. No full-suite rerun or held-out measurement occurred.
- Final documentation tests: 6 PASS / 0.21 s. HTML static validation: 51 unique IDs,
  59 valid links, unchanged JavaScript. Browser visual QA was not run. No Docker
  container remained running after the model runs and operator checks completed.

Three exposed tasks with one sample each are a development result, not a general
success rate, a feature attribution or a comparison against historical dev20.
