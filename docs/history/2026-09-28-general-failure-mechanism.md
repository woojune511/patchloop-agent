# General failure mechanism: self-authored expectation becomes authority

2026-09-28, provider-free, `official=false`. This extends the
[public toqito diagnosis](2026-09-28-toqito-public-validation.md) by auditing the
harness/agent boundary. No task-specific rule, prompt, test gate or runtime change.

## Causal question

Was the wrong repair caused by missing observations, a misleading harness verdict,
a forced action, or an unsupported interpretation of delivered evidence? A single
case can establish a mechanism and eliminate local explanations. It cannot establish
how often other tasks exhibit the same problem or whether an intervention improves them.

## Saved delivery evidence

The exact prepared requests at journal sequences 88, 103 and 122 were read through
hash-verified artifacts. These are the requests after probe 1, after probe 2, and
before the edit-producing call. They expose only public tools/data.

- Full recorded stdout from probe 1 is present at 88; both complete probe stdout
  strings are present at 103 and 122. The important numeric discrepancy was not
  truncated or replaced by a summary.
- At 103, the second probe's actual expectation expression and state-construction
  code remain in the request. The model could examine what its expected value meant.
- At 122, that full expectation source expression is absent, although both outputs
  remain. Retention loss is real at this later boundary. It cannot explain the
  initial unsupported attribution already stated in the response to request 103;
  its contribution to later persistence has not been isolated.
- All observed probe projections say behavior_verdict=not_assessed. The model view
  separates execution completion from semantic correctness; setup checks only cover
  selected supplied values. The wrong expectation formula was not validated by them.
- The saved system prompt already says that failure may be in the experiment itself,
  limits conclusions to actual inputs/observations, and asks the next action's basis
  to connect the observation to the action. These generic instructions are delivered,
  not merely present in current source.
- At these three decision points, read_file, search_files, run_probe, run_check and
  replace_text remain available. The model was not forced into the exact branch
  by a tool mask. Financial pressure may affect decisions, but that causal effect
  has not been measured; more budget might permit later correction.

## Observed mechanism and competing explanations

| Layer | Evidence | Interpretation |
| --- | --- | --- |
| Experimental expectation | Self-authored comparator represents the reversed conditional quantity | The claimed reference value is an unverified hypothesis, not an independent oracle |
| Attribution | Public action rationale calls the discrepancy optimizer failure | One explanation was selected without distinguishing program, setup and expected-value errors |
| Repair choice | Subsequent plan prefers exact branches; CQ branch uses an inapplicable formula | The initial attribution directed repair toward an unjustified shortcut |
| State retention | Outputs persist; complete probe source drops before the edit request | Potential reinforcement/repair obstacle, not established origin of the error |
| Completion | No candidate validation before the original cost stop | Non-submission remains NOT_RUN; absence of later correction is not proof it could never correct |
| Check scope | Separate operator replay passes 14 old public tests but finds a new counterexample | Existing regression checks cover preserved behavior, not the entire requested extension |

The last row is a verification coverage limitation, not the cause of the original
belief: the original agent never ran those checks. Do not describe this as an agent
being misled by green tests. Likewise it noticed the numerical discrepancy; this is
not an inability to read numeric output. The mistake is assigning cause to a mismatch
and extending a formula's scope without sufficient support.

The task-independent failure pattern is: **a self-generated expected value is treated
as ground truth; disagreement is attributed to the implementation; the resulting
interpretation is used to justify a new implementation without an independent check**.
Similar logical risks exist for units, coordinate frames, argument order, normalization,
sign conventions and API semantics. These examples explain transferability of the
mechanism, not evidence that PatchLoop has failed on those tasks.

## Harness implication

There is no evidence here for fixing transport, changing PASS labels, enforcing more
probes, or copying the mathematical counterexample into the default harness. Existing
generic warnings did not prevent the failure, so merely adding another warning is not
a justified fix. More model budget addresses truncation/completion, but its effect on
this reasoning error remains unmeasured. Keep the two questions separate.

Before changing defaults, use this as a diagnostic category: at an observed mismatch,
record where the expected value came from, which assumptions make it applicable,
which alternative explanations remain, and whether a discriminating check precedes
the consequential edit. These are developer audit questions, not mandatory fields or
a new agent workflow. Inspect actual action evidence rather than requiring longer prose.

The next useful experiment can test whether the agent revisits its comparator with
adequate resources and no task-specific correction. If a generic self-check cue is
compared later, keep the saved state, model, tool surface and allowance equal and label
it a development intervention. Do not equate a supplied exact counterexample repair
with autonomous discovery. No new paid execution is authorized here.

## Evidence and validation

Root: `C:/pt/analyses/general-failure-mechanism-20260928-v1`.
Journal: `runs/run_dev_generalmechanism.jsonl`; report: `delivery-audit.json`.
Scripts: `C:/pt/general_failure_delivery_audit_0928.py` and
`C:/pt/general_failure_verify_delivery_0928.py`.
The report stores selected public observations and input identities, not private
reasoning or private evaluation. Three request-artifact checks plus full stdout
comparison and initial prompt verification passed. The original source journal and
all historical records remain unchanged. Additional provider cost: $0.

Focused validation: probe-observation module 17 passed; documentation layout 5 passed
after shortening current status. Runtime/defaults unchanged; no new full-suite run.
