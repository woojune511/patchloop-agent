# SQLFluff prepared-probe follow-up results

Date: 2026-10-02. Execution head `2650d04302742d8e2a83a514f21c9666da9e9adc`.
Ubuntu and Windows fast-dev-head CI both passed before dispatch. This allocation
is closed; every run is official=false and claim-ineligible.

## Question and decision

The closed dev20 baseline contained three SQLFluff failures whose requested public
probes never reached behavior execution. The selected question was whether prepared
public dependencies and plugin metadata would enable useful reproduction evidence
and better repairs. Selection, alternatives, scope and stop rules were frozen in
the [plan](../../.agent/lite-sql3-probe-followup.md). The baseline's original hidden
resolution for these same three tasks was 0/3.

The user approved the new USD 3.60 scope after exact-head CI passed. Each task ran
once in a fresh workspace with the same public task/source bytes, model, prompt
policies and resource limits. The request differences were prepared probe
dependencies and new state roots. The merged preparation-helper change and generic
probe environment/profile description are disclosed differences. The model was
`gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens, with USD 1.20 per
task, 40 calls, 100 actions, four edits and 1,800 seconds. No prior patches,
trajectories, operator programs or private evaluation results entered solver context.

Prepared dependencies enabled real task diagnostics in two tasks, but original
hidden resolution stayed 0/3. Keep the dependency support as an available capability;
this experiment does not establish a repair-quality improvement. Do not expand the
budget, add compulsory probes or launch another adjacent paid comparison from this
result alone. The next useful question is provider-free: why does final submission
proceed without checking the reported behavior on the final patch, even after useful
earlier probes? Inspect the current completion/verification evidence and public
traces before deciding whether this is a runtime contract defect, a policy choice,
or a model reasoning failure. Absence of a final probe alone does not prove that
requiring one would make the repair correct.

## Results

All three tasks completed and submitted. Final public regression and safety were
PASS for all three. Original-native evaluation agreed with registered evaluation
in all three cases; required test-result coverage was 43/43, 65/65 and 4/4. No
counting, transport, billing, evaluation infrastructure or cleanup uncertainty was
observed. NOT_RUN is zero.

| Instance suffix | Original hidden | Model calls | USD | Solve seconds | Public probes |
| --- | --- | ---: | ---: | ---: | ---: |
| 1517 | FAIL | 15 | 0.34373205 | 384.549 | 0 |
| 1625 | FAIL | 30 | 0.81667485 | 1368.558 | 7 |
| 1733 | FAIL | 24 | 0.51130575 | 619.442 | 3 |
| Total | 0/3 resolved | 69 | 1.67171265 | 2372.549 | 10 |

There were 70 input-count calls. Solve time includes registered evaluation but
excludes CI waiting, preparation and the subsequent original-native evaluation.
The same three historical baseline rows used 81 model calls, USD 2.26119915 and
2233.904 seconds. This run was cheaper but slower in aggregate, with no increase
in correctness. These are descriptive observations, not causal cost/latency gains.

## Public trace observations

- **1517:** No custom probe was requested. The agent changed one unmatched-segment
  return in `Delimited.match`, passed public regressions and submitted. Making
  dependencies available did not cause probe use in this sample.
- **1625:** The first probe failed with a model-authored `NoneType.get_child` error.
  A subsequent probe corrected traversal and produced real parse/lint observations.
  Seven probes ran: five exited zero and two raised API errors. Several zero-exit
  diagnostics still returned missing nodes or empty observations, so exit status
  is not a measure of diagnostic usefulness. The first patch failed two public
  L031 fixtures; a second patch restored public PASS. Every custom probe preceded
  that final edit. The agent did not rerun the issue example on the submitted patch.
- **1733:** Three probes executed the issue behavior successfully before editing.
  The agent compared full versus CTE-only SQL, isolated L003/L036 combinations and
  instrumented indentation coercion, observing an intended width of eight with an
  extra whitespace segment remaining. It then made one edit, passed 506 public
  tests and submitted without rerunning the reproduction on the changed source.

Across ten probes there were no missing-dependency, snapshot rejection, timeout or
cleanup errors. Eight zero exits therefore support operational availability, while
the traces qualify how much useful evidence was obtained. No task performed a
custom reproduction after its final edit (0/3). Public regression success remained
insufficient for original task acceptance (0/3). These findings support further
inspection of evidence interpretation and final-patch verification; they do not
isolate the cause of each incorrect repair or prove a particular intervention.

## Evidence and validation

External root: `C:/pt/analyses/lite-sql3-registration-20261002-v1`.

- `manifest.json`, `preflight.json`, `authorization.json`: frozen input/runtime/
  driver/harness identities and exact human-approved scope.
- `canaries.json`, `controls-pass.xml`: three provider-free import/plugin/parse
  checks and fourteen driver plus five documentation checks before approval.
- `launch.json`, `live.stdout.log`, `live.stderr.log`,
  `runs/run_dev_litesql3live.jsonl`: one durable invocation and three allocations.
  Child hash-chained journals are under `C:/pt/lp3live01/1` through `/3`.
- `predictions.jsonl`: exact submitted diffs. `native-launch.json`, `native.log`,
  `native-summary.json` and `C:/pt/lp3native01`: one original-harness evaluation,
  complete required-case coverage and confirmed removal of all three owned containers.
- `audit.py`, `summary.json`, `runs/run_dev_litesql3audit.jsonl`: reconciled
  journal chains, task/runtime hashes, provider-settled costs, model calls, final
  artifact hashes, patch/prediction identity and final public-check diff identity.
  Neither provider calls nor input counts remain unresolved.

Summary file SHA-256: `7cee971eb59c529d732a2651b90e07c96af00d71640d86eaca4bf89f401921ed`.

This was a historical before/after development diagnostic with one stochastic
sample per task, not a randomized comparison or held-out accuracy estimate.
The prepared public Python 3.12 environment includes operator-pinned setuptools
support and differs from the Python 3.9 evaluator environment. Hidden tests,
reference patches and grading were unchanged and never given to the solver.
No retry, resume, task replacement, source/image/dependency acquisition or extra
paid run occurred. The old dev20 10/20 result stays unchanged; these three repeat
samples must not be appended to its denominator. Original evidence is preserved.
