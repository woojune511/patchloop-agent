# Frozen pre-edit instruction: next-action A/B results

Date: 2026-10-15 KST. Execution HEAD: `d9fb242a392b59f4bccb64bab5dc7bb5745f255e`.
`official=false`, claim-ineligible. Four fresh model responses; no returned tool
execution, task repair, regression run, private evaluation or paid judge.

## Question and frozen execution

The [design](2026-10-15-pre-edit-diagnostic-design.md) asks whether one instruction
changes the next action at SQLFluff-1733 input 367 from an unsupported last edit
to a diagnostic of its preservation premise. The separate [public probe](2026-10-15-pre-edit-probe.md)
had established that an operator-written program could distinguish current CTE
behavior from a temporary L036 reversion. Its program and output were not added
to either model request.

The user authorized the prepared comparison within its fixed limits and explicitly
forbade wording changes or additional runs even if results were negative. A used
the exact historical request; B appended only the previously frozen paragraph.
Both arms preserved all original public inputs, tools and opaque encrypted
continuation. No previous sampled response was reused or chained into another cell.

| Setting | Executed scope |
| --- | --- |
| Task/checkpoint | `swebench-lite-dev-sqlfluff-sqlfluff-1733`, dev-train, input 367 |
| Model | `gpt-5.4-2026-03-05`, xhigh, default tier |
| Order | A1, B1, B2, A2; two fresh responses per arm |
| Limits | 60,000 input / 25,000 output tokens; USD 3; 1,200 seconds |
| Actual calls | Four counts immediately before four generations; one model metadata lookup |
| Actual inputs | A: 50,083 tokens each; B: 50,176 tokens each |
| Duration | 64.742 seconds collection; 66.506 seconds including model lookup |
| Usage settlement | USD **0.250177**; all four usage records reconciled |
| Excluded | SDK retries, corrections, replacement samples, resume, tool execution, evaluation |

The exact repository `.env` supplied the credential directly to the SDK, never
through subprocess environment variables. The existing response-only collector
was reused by an external wrapper; its process-local deadline was reduced to the
remaining authorized 1,200 seconds and restored on return. Production bytes stayed
unchanged. Runtime/task inputs were HEAD-clean; the user's unrelated AGENTS.md edit
was preserved.

The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4)
confirmed the snapshot and xhigh support. [Official Standard pricing](https://developers.openai.com/api/docs/pricing)
matched the frozen rates: USD 2.50/M input, 0.25/M cached input, 15/M output.
The API model lookup then confirmed this account could retrieve the exact snapshot.
The original [stateless encrypted continuation](https://developers.openai.com/api/docs/guides/migrate-to-responses#4-decide-when-to-store-state)
was preserved without interpretation. No model substitution or prompt adjustment occurred.

## Actual requested actions and grading

Public proposals were extracted without plaintext private reasoning. Grades were
saved before opening the explicit arm mapping. This was informed, **partially
masked** review: the initial artifact references exposed timestamps, permitting
schedule inference. It was not independent or fully blinded review.

The primary retains the design's setup/scope requirement for the submitted
diagnostic, including its assertions. Merely choosing `run_probe`, mentioning a
counterfactual, or writing a plausible causal explanation does not qualify.

| Cell | Requested next action | Primary qualification | Reason |
| --- | --- | --- | --- |
| A1 | Revert the L036 copied-indentation addition | No | Repeats the preservation premise without testing it |
| A2 | Same reversion, with a causal-revision explanation | No | Explanation changes, but no distinguishing observation is requested |
| B1 | Temporarily revert L036; fix CTE and flat SQL; assert both outputs | No, borderline | CTE diagnostic is useful; additional YAML assertion uses an incompatible rule scope |
| B2 | Temporarily revert L036; print flat output and CTE indentation; restore in `finally` | Yes, proposal only | Explicit CTE observation distinguishes preservation from dependence on L036 |

Both A replacement anchors were unique in the visible current source. Applying
either replacement to bytes in memory produces exactly the recorded final L036
file, without writing a file. A1 again says the separate L003 change should address
the reported bug; A2 predicts that the CTE will still have eight-space indentation.
Neither obtains evidence for that premise before requesting the last edit.

Both B programs use the actual public CTE input and default `sqlfluff.fix` entry
point. Their hypothetical methods match the recorded L036 reversion's AST, ignoring
only the function name and docstring. Required symbols are imported, SQL literals
contain actual newlines, and source/question lengths fit the offered limits.
They perform no repository writes. Syntax and source equivalence were checked
statically; **neither sampled program was executed**.

Neither B program reruns an unchanged-candidate control: each labels its change as
hypothetical and tests the contemplated behavior against the earlier success and
public expectation. A paired control would strengthen attribution, but the frozen
rubric did not require duplicating the operator reference program. Both proposals
reach the previously untested preservation premise.

## B1 scope mismatch and the grading boundary

B1 calls:

```python
cte_result = sqlfluff.fix(cte_sql)
yaml_result = sqlfluff.fix(yaml_sql)
print({'cte_line': cte_result.splitlines()[2],
       'yaml_lines': yaml_result.splitlines()[:5]}, flush=True)
assert cte_result == cte_expected, cte_result
assert yaml_result == yaml_expected, yaml_result
```

Its `cte_expected` is correct for the public task. Its additional `yaml_expected`
comes from `test_multiple_select_targets_some_newlines_missing_2` in
`test/fixtures/rules/std_rule_cases/L036.yml`. The fixture deliberately retains odd
indentation left untouched by L036. The original test helper
`src/sqlfluff/testing/rules.py:62` restricts execution with `overrides={"rules": code}`.
B1 instead uses the default all-rule API, including indentation rules, but still
asserts exact equality with that single-rule output. No source evidence justifies
transferring this expectation to the larger rule set.

Under the frozen exclusion of mismatched setups, the full submitted B1 proposal
is not credited. This is a **static expectation/scope defect**, not an observed
assertion failure: the program was not run. Its cleanup also restores the method
only after both assertions; a failed assertion skips restoration before the isolated
process exits. That does not mutate the repository and is not the primary exclusion.

B2's question also mentions the unindented flat expectation, so its flat output
would not establish that the registered L036 regression passes. However, B2 does
not assert that expectation or make it a pass condition. It unconditionally prints
the CTE target line and its leading-space count, then restores in `finally`.
That independent eight-versus-five-space observation qualifies for the CTE question.

B1 is a real scoring boundary: its printed CTE observation is independently useful
before the questionable extra assertion. **If only that sub-observation were
credited, A would be 0/2 and B 2/2.** The primary applies the prepared setup/scope
requirement to the entire submitted diagnostic and is **A 0/2, B 1/2**. This
interpretive distinction is reported explicitly; the narrower score is not used
to pass the progression gate. Do not describe the result as a robust superiority
finding or B1 as wholly irrelevant.

## Decision

The added instruction changed both sampled B actions toward the relevant
counterfactual test, while both sampled A actions retained the unsupported edit.
This supports a narrow action-selection effect at this historical thin-policy
checkpoint. It does not show reliable test construction, observation uptake,
an improved final patch, hidden acceptance or a general policy benefit.

The predeclared gate required B 2/2 qualifying proposals and strictly more than A.
The primary did not meet it. **Keep the runtime baseline and close this formulation.**
No wording change, extra sample, repaired version of either sampled probe, model
continuation or automatic next stage was executed. USD 2.749823 of unused cap is
closed; remaining authorized generation/count calls are zero.

The remaining uncertainty is whether an agent can consistently choose a relevant
counterfactual while also matching each asserted expectation to the exact check
scope, and then use the observation to make a feasible repair. This result does
not authorize another comparison. The separately prepared revision comparison is
unaffected. Even the narrower 2/2 reading would only support discussing a separate
experiment, not runtime adoption.

Cost differences are not efficiency evidence: A1 had no cached input while the
other three calls each reported 49,536 cached tokens. No performance claim is made
from output length, probe count, successful collection or elapsed time.

## Evidence and validation

Preparation/review root: `C:/pt/hypab01`. Live root: `C:/pt/hypablive01`.

- `packet.json`: user-authorized frozen execution binding, hash
  `sha256:0d2ec81de0d7c0d21d3415552e9faaf0aec3bc323bbf50be4f43f7407e64f9fa`.
- `collect_frozen.py`, `test_frozen.py`, `official-verification.json`,
  `offline-validation.json`: external wrapper and provider-free boundary checks.
- `model-availability.json`, `collection-result.json`: snapshot lookup and invocation closeout.
- `masked-public.json`, `masked-content.json`, `static_review.py`, `static-findings.json`:
  public proposals and non-executing syntax/source review, including masking limits.
- `masked-grades.json`: grades frozen before explicit labels, hash
  `sha256:9b76edd77130b4eb4edcc199e78c63b2a2ce1ba3e9d354a29c546fead043628e`.
- `reveal_and_audit.py`, `summary.json`: exact labels, usage reconciliation, conservative
  primary and narrower-reading sensitivity. All four request hashes match the
  prepared A/B inputs; all eight public/opaque sample artifacts verify.
- Plan/review journal: `runs/run_dev_frozenpreeditab.jsonl`; live journal:
  `C:/pt/hypablive01/runs/run_dev_sample_f87767e6bf544a18.jsonl`.
- `validation.json`, `closeout.json`: documentation checks and commit/integrity binding.

The external wrapper passed nine focused offline tests; the reused collector suite
also passed. Tests covered exact request preservation, caps, input/deadline limits,
stop-all on count/transport/billing/model/continuation uncertainty, invalid-proposal
retention, and no resume. Credential/provider/tool/container paths were forbidden
in the focused mocks. Final documentation/link, Ruff and whitespace checks passed.
All 36 input bindings stayed unchanged. No runtime source changed; broad runtime
tests and mock smoke were not repeated. Closed historical records remain immutable.
