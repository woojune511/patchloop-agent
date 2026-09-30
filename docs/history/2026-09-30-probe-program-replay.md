# Reference-free probe program reuse and tracking explanations

## Problem and evidence

The existing cases-v1 interface retains candidate programs only after selecting a
healthy JSON reference. A first assertion/exception failure cannot itself register
a reference-free reproduction. This is an interface limitation, not evidence that
it caused the observed agent failures: the fresh Darts run did not invoke a probe.

The command tracker also intentionally leaves Python launches with options such as
`-B` uninstrumented, but its feedback used the same missing-report reason as a
supported launch whose report was lost. MontePy additionally runs copied source in
a child process; recognizing the option alone would not observe that execution.

## Change and boundary

Keep the existing run_probe action, three-case retention, journal events and
idempotency. Explicit `save_program=true` in cases-v1 registers source/question
without a reference. A completed failed or non-JSON execution can retain that
program. Later case-ID calls execute exactly the saved source on the current diff;
changing source creates a new content-derived identity. Reference comparison remains
available, with unchanged healthy-JSON eligibility. Ordinary probes remain unsaved.

Reference-free results expose exit/status and timeout/cleanup/output flags alongside
source, environment, snapshot and policy hashes. The durable action binds the diff.
They report not_compared/no_reference, never an inferred patch verdict. Existing
cleanup/deadline stops, budgets, mutation admission and submission gates are unchanged.
No new tool, automatic rerun, cross-run catalog or mutable program registry is added.

Tracking admission and explanations share one command classifier. Feedback separates
unsupported executable/options, incomplete launch, timeout and missing report. Launch
semantics are unchanged; subprocesses, other threads and copied paths remain outside
the stated observation scope. Unknown does not mean the source was not executed.

## Validation and decision

Fifteen focused tests passed in 17.59 seconds. They cover failing assertion -> edit
-> identical-program success, changed-source identity, current/historical diff binding,
invalid mixed modes, recorded execution failures without automatic retry, and mock
recovery after a durable failed probe without duplicate execution. The mock resumes
through isolated acceptance PASS with safety NOT_RUN. Tracking regression tests passed
75 cases in 19.95 seconds; the full reusable-probe module passed 38 cases in 110.06
seconds. Documentation checks and Ruff also passed.

The default-policy mock smoke `run_dev_dff2732be5c346d2` reached EVALUATOR_PASS with
safety NOT_RUN and zero provider cost. Its external root is
`C:\pt\smoke\probe-program-20260930`. These are controlled functional tests, not
evidence of autonomous test selection, patch-quality improvement or real sandbox safety.

Keep the selected baseline at probe-policy none. No paid comparison, new task solve,
default adoption or historical run migration was performed. A later quality comparison
must assess actual repairs, regressions and total cost, distinguishing operator-supplied
tests from tests the agent independently creates. Utility remains an untested hypothesis.
