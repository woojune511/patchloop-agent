# Current dev20 interruption and additive test correction

## Question and frozen scope

The user accepted a fresh run of the same twenty development tasks with useful
verification capabilities available and the existing model/resource limits, then
requested independent task concurrency and ordinary probe support for all three
initially incompatible Astroid/PyVista environments. The
[preparation](2026-10-06-current-dev20-preparation.md) passed all twenty public
import canaries and all twenty selected-test canaries.

Execution used commit `2a8bf737`, gpt-5.4-mini-2026-03-17, xhigh, `.env`, one fresh
attempt per task, two workers, USD 1.20 per task and USD 24 in total. Limits were
40 model calls, 100 actions, four accepted edits and 1,800 active seconds per task.
Automatic probe replay remained off. Original issues, base commits and private
oracles were preserved. SQLFluff-1625 used the corrected current public launcher;
this differs from the preceding portfolio panel's frozen launcher.

The exact manifest and existing-user-request authorization are recorded under
`C:/pt/cd20p06b`. Manifest identity:
`sha256:b3a60df791fdcccc3c7a6f9af91538d0d4dd97c5ea4fb4b540017d97434f4f94`.
Live state is under `C:/pt/cd20live06`. Both remain immutable evidence; no task was
retried or resumed, no budget was transferred, and no follow-up panel was launched.

## Observed result

| Outcome | Tasks |
| --- | ---: |
| Registered/native agreement: PASS | 8 |
| Registered/native agreement: FAIL | 8 |
| Registered evaluation deadline, native FAIL | 1 |
| Interrupted by batch stop | 1 |
| Not started | 2 |

SQLFluff-1625 submitted a patch but exhausted its active deadline during registered
evaluation: terminal `LIMIT_REACHED`, acceptance `ERROR`, safety `ERROR`, failure
class `ACTIVE_DEADLINE_EXHAUSTED`. Native evaluation completed as FAIL with cleanup
confirmed. ERROR versus FAIL did not satisfy the frozen agreement gate, so the
coordinator stopped further admissions. SQLFluff-1733 then stopped before another
call (`BatchStopped`); SQLFluff-1763 and SQLFluff-2419 never started.

All 263 generation calls and their input counts were reconciled, including the
interrupted row. Recorded cost was **USD 5.39413050**, with no unknown billing.
Elapsed batch time was **4,068.996 seconds (67m49s)**. Two overlapping provider
calls were observed. This proves concurrent execution, not a speedup estimate:
the panel was incomplete, workload differed, and local validation also ran on the
host during part of execution. There were no remaining Docker containers at the
post-run observation; this does not replace the ERROR/NOT_RUN safety axes.

The sixteen agreeing task outcomes exactly match the preceding 9/20 panel's
outcomes on those same tasks. **This is not an 8/20 success-rate result and cannot
establish improvement or deterioration of the complete current agent.** Native
FAIL for the deadline row is retained separately, without inventing a registered
FAIL verdict. No new quality/adoption or held-out claim follows.

## Capability use and remaining test restriction

Every started task's actual first model request exposed `run_probe` and `run_tests`.
The agent called ordinary probes **9 times** and made **2 accepted test additions**
(pvlib-1707 and pydicom-1694). It never called `run_tests`. Tool availability and
usage are distinct from repair correctness; pvlib-1707 still failed despite its
accepted test addition.

There were eleven rejected test-edit attempts. Inspection found a defect in the
new connection: its reused structural checker only supported module-level test
functions. It also rejected ordinary new methods inside existing pytest/unittest
classes, a new test class, and a new function decorated with `mock.patch` even
when original definitions were preserved. These restrictions caused repeated
rejections in four tasks. They matter as a demonstrated authoring bottleneck,
without proving that accepting these tests would solve the tasks.

The executing code was left unchanged. A separate worktree corrected admission
after the observed failures: dev-head's opt-in test-edit path now permits new test
methods, `Test*` classes containing tests, new decorated test functions, and literal
parameter cases inside existing methods. Original test bodies, class headers,
imports, fixtures and helpers remain structurally unchanged. Isolated private
grading still restores original tests. The separate `repair-verify` tool retains
its existing module-level selector contract.

Provider-free structural replay accepted eight previously rejected additions.
The two other edits in that replay changed existing test bodies and remained
unsupported. The eleventh edit, in SQLFluff-1625's YAML fixture, rewrote existing
failure expectations and remained outside the additive Python-test contract.
These are admission results, not executed regression tests or repair successes.

## Validation and evidence boundaries

- The measured commit's full-run and focused-rerun validation is recorded in the
  preparation record. Its failed first report was preserved, not rewritten.
- The test-definition correction passed 60 related regression tests, including
  the unchanged repair-verification path. Focused admission/evaluation tests
  passed 28 cases in 20.161 seconds. Normalized-source validation repeated those
  28 cases successfully; the accompanying documentation-size failure was fixed
  and the five documentation checks were rerun separately. Original reports are
  preserved below the same external preparation root. A real pytest subprocess
  collected and passed the five
  representative added cases. Rewritten original assertions, changed class
  headers, changed helpers, removed cases and fixture additions were rejected.
- Ruff passed, and mock smoke reached `EVALUATOR_PASS`; mock Docker safety remains
  `NOT_RUN`. The correction did not receive a new paid run or a new full-suite run;
  validation covers the changed admission/evaluation path and its legacy caller.
- `result.json`, `postrun-audit.json`, their hash-chained journals, and the frozen
  manifest preserve run/accounting/assessment evidence. `class-method-replay*.json`
  and `method-*.json`/`method-*.xml` preserve the separate correction checks.

The correction is implemented and locally tested, but its effect on task success
is **NOT_RUN**. The interrupted panel is not evidence for the post-correction
runtime. Before another measurement, resolve how ordinary per-task time exhaustion
should interact with the batch's evaluator-agreement stop condition. Do not silently
extend the task limit, weaken the recorded verdicts, resume this allocation, or
launch another paid comparison from leftover budget.
