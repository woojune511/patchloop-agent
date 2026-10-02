# SWE-bench Lite mini pilot: one of three original tasks resolved

## Question and decision

The user requested a cheap original-benchmark measurement with GPT-5.4 mini after
repeated development-task diagnosis. This fixed three-task development pilot asks
whether the current agent can submit repairs through the original evaluation and
what a fresh solve costs. It is not an agent intervention or model comparison.

All three fresh solves submitted once. Original native SWE-bench evaluation
resolved pydicom and rejected astroid and marshmallow, agreeing with the registered
private adapter. All required tests were present; these are completed wrong-patch
outcomes, not public-check infrastructure failures. The allocation is closed.

The integration and low-cost execution worked for these three tasks. The failures
retain a correctness question: patches can pass existing public regressions while
covering only the immediate symptom. This does not justify a new prompt, mandatory
probe rule or another attempt on these exposed cases without a distinct question.
The next scale decision needs a frozen broader task/environment plan and separate
budget; 300-task execution remains unapproved.

## Frozen execution

The [pilot protocol](../../.agent/swebench-lite-pilot.md) binds dataset revision,
selection seed, three dev instances, original harness revision, repository commits,
image digests, public/private separation and stop rules. No test-split task ran.
Execution HEAD was 898509b46b52d5e6e5fe160236a2c93b626ff6c7. Task package bytes match
the calibrated v4 drafts. Raw-byte Git attributes retain original evaluator hashes.

- Model: gpt-5.4-mini-2026-03-17, xhigh, desired output ceiling 25,000.
- One fresh solve per task, ordered astroid, pydicom, marshmallow; no retries.
- Nontransferable caps: USD 1.20 each, USD 3.60 combined. Limits: 40 model calls,
  100 actions, four accepted edits and 1,800 seconds per task.
- Existing segmented-v1/result-or-size-v1/brief-v1 policies, optional probes enabled
  with policy none, repair-recheck and protected-v1 inspection; per-call-v1 cost.
- The API key was read only by the existing credential-file path. No credential
  content entered source, task inputs, evaluator environments or records.
- No runtime/prompt intervention, hidden feedback to a solver, oracle edits,
  reference-patch seeding, correction attempt or funded continuation occurred.

Pricing was checked using OpenAI Docs and the
[official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini):
USD 0.75/M input, 0.075/M cached input, 4.50/M output. The existing adapter pins
standard service and the global API endpoint, counts immediately before dispatch
and uses zero SDK retries. Costs below are computed from returned token usage,
not an invoice or a measurement of local compute/storage costs.

## Results

| Instance | Submitted | Public checks | Native original result | Calls | Solve seconds | USD |
| --- | --- | --- | --- | ---: | ---: | ---: |
| pylint-dev__astroid-1978 | yes | pass | unresolved, 12/13 cases passed | 6 | 132.410 | 0.12645810 |
| pydicom__pydicom-1256 | yes | pass | resolved, 23/23 cases passed | 6 | 69.438 | 0.08333595 |
| marshmallow-code__marshmallow-1359 | yes | pass | unresolved, 76/77 cases passed | 7 | 65.117 | 0.08118915 |

Completed 3/3; submitted 3/3; resolved 1/3. There were no resource-limit,
transport/count/billing-unknown or evaluation-infrastructure outcomes. PatchLoop
scope/safety verdicts passed for all three. All three used one accepted edit and
no optional probes. These observations do not isolate a probe benefit or model effect.

Total: 19 model calls, 19 input-count calls, USD 0.29098320 and 266.965 seconds of
solve invocations, including their registered evaluation but excluding preparation
and final native re-evaluation. Mean cost: USD 0.09699440/task. Total cost divided
by the one resolved task is USD 0.29098320. Unused cap: USD 3.30901680, not authority
for more runs. No provider dispatch or input count remains unresolved.

Applying only the observed minimum/mean/maximum task costs arithmetically to 300
tasks gives USD 24.36 / 29.10 / 37.94. This is not a forecast or a suitable hard cap:
three selected dev tasks do not characterize larger tasks, setup failures or longer
trajectories. Reusing a USD 1.20/task ceiling would instead imply a USD 360 ceiling,
which is not approved. No general benchmark success rate is inferred from 1/3.

## Failure observations, without retuning

- **Astroid:** the submitted patch special-cased missing NumPy attributes and
  replaced sys.modules indexing with get(). Original evaluation rejected the
  module-getattr output-capture behavior: expected captured output was absent from
  the log. This demonstrates noncompliance with the original test; the patch is a
  narrow workaround, not evidence of general output-capture correctness.
- **Marshmallow:** the patch avoided AttributeError when the parent field has no
  opts by falling back to the default format. The original nested-DateTime test
  expected the root schema's iso8601 setting and observed iso instead. The crash
  guard omitted inherited configuration semantics.
- **Pydicom:** the patch propagated bulk_data_element_handler into nested JSON
  DataElement conversion and passed the unchanged original evaluator.

These are post-run operator observations. No failed test details were returned to
the agent, and neither failed task was repaired or rerun with the model.

## Evidence and validation

Main root: C:/pt/analyses/swebench-lite-live-20261002-v1. Its hash-chained
runs/run_dev_litepilot.jsonl binds admission, preflight, the one-shot driver,
requests, per-task results, exported predictions, native files and allocation close.
summary.json is a derived readable projection. predictions.jsonl contains only the
three final submitted patches in official prediction format.

| Task | Run ID | External state root |
| --- | --- | --- |
| astroid | run_dev_a6957c1d86404f40 | C:/pt/lm1002v1/1 |
| pydicom | run_dev_1d98c72e8b8348de | C:/pt/lm1002v1/2 |
| marshmallow | run_dev_db7e873506c14bc9 | C:/pt/lm1002v1/3 |

Before paid execution, all three known references passed the actual isolated
EvaluationEngine, including scope/safety, under
C:/pt/analyses/swebench-lite-engine-controls-20261002-v1. The native prediction route
was also calibrated with two reference patches and one deliberately irrelevant
public patch: expected resolved/unresolved/resolved, complete test accounting.
Native agent evaluation agrees with all three registered outcomes and all owned
evaluation containers were removed.

Focused selection, transport, prediction binding, private error classification and
public launcher tests: 19 passed. Ruff and documentation checks passed. Runtime
source did not change; the preceding full-suite/short-path rerun evidence is recorded
in the [public-check follow-up](2026-10-02-swebench-lite-public-checks.md). The full
suite was not repeated for operator-only prediction routing and package admission.
Remote CI has not run. Every result remains official=false and claim-ineligible.
