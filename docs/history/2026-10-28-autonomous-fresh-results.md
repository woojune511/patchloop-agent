# Clean-original autonomous repair result

## Material Passport

- Date: 2026-10-28. Executed once under the user's exact command/cap approval.
- Astroid-1333, dev-train current-dev20/13; official=false, claim_eligible=false.
- Execution checkout `2e2711a6079bec13319fad9d5b59f4eb49bf6f0c`.
- Result: **LIMIT_REACHED; repair incomplete; no submission or isolated evaluation**.
- Accounting settled; USD1.549624 spent from USD4.50. Allocation CLOSED.

## Question and fixed scope

The [assisted continuation](2026-10-28-required-public-check-repair-results.md)
successfully revised a saved candidate using operator-selected public failures.
The next question was whether the current normal runner could reproduce, repair
and verify the same task from its original source without that trajectory or packet.
This matters because an assisted final repair does not establish autonomous end-to-end
completion. The [sealed plan](2026-10-28-autonomous-fresh-plan.md) fixes the setup.

The approved command was `& 'C:/pt/autonomous-fresh-plan-v1/run.ps1'`, manifest
`sha256:db006cc81bda32aa3574e5d4d1d1c9fbbbe43fb9f9df5c380469cbc221303479`.
One run used `gpt-5.4-2026-03-05` (xhigh), repository `.env`, USD4.50, response20
including correction1, action40, edit3, input60K, output40K/correction25K, and
2400 seconds including390 reserved for isolated evaluation. Explicit read-only
pylint source access and prepared public dependencies remained available.

No saved patch, checkpoint, prior observation, operator counterexample or private
evaluation material was injected. The first actual request had an empty original
diff, no prior source/results/notes, an unfulfilled original-call obligation, and
only base-regression as a required visible check. Its actual input was9363 tokens;
prepared, counted and dispatched request identities matched. The supplemental
counterexample feature was not registered and is NOT_EXERCISED, not a failed
test of that mechanism.

## Public trajectory

Sequences refer to `run_dev_8fadb1628e0d4415` in the result root.

| Stage | Observed result |
| --- | --- |
| Initial exploration | The model searched and read `pylint.run_pylint` through the registered caller scope, then searched Astroid source. |
| Request rejected, 57 | `pylint:run_pylint` did not satisfy the dotted-entrypoint format. |
| Corrected request, 71 | The entrypoint was corrected to `pylint.run_pylint`; a separate helper error occurred because `input_paths` contained7 entries against the maximum4. No declared target call was reached. |
| Original reproduction, 106 | The model corrected the helper and executed the selected call on unchanged source. The failure fixture produced F0010; the regular control did not. Declared failure matched. |
| Exploration before edit | The model read/searched caller file expansion, modutils, manager, builder, scoped nodes and related tests. Before the first edit it had spent31 inspection actions and3 probe requests:34/40 actions. |
| First edit, 244 | Added a missing-`__init__.py` special case in `astroid/manager.py` returning `_build_namespace_module`. |
| First replay, 251 | F0010 disappeared, but the target raised `FileNotFoundError: src/project/__init__.py`. Captures were complete; the unexpected exception made the case incomplete and `not_compared`. |
| Failure delivery, 257-263 | The same candidate's observed values, failed target exception, call captures and exception frames reached the next actually dispatched request. Finish remained unavailable. |
| Second edit, 268 | Replaced the special-case return with `string_build("", modname, filepath)`, setting package/path fields. The stated hypothesis addressed the first patch's missing readable source buffer. |
| Second replay, 275 | Complete comparable execution, but expected behavior mismatched. The target exited0 with empty stdout; F0010 was absent but the project-processing witness was false. The regular control still emitted C0114/W0611 for its file. |
| Terminal, 277 | Tool actions remaining2 versus minimum completion4; the host stopped before another provider dispatch. No further model response received the second failure. |

The first replay's issue was not a capture limit, timeout or missing target entry:
both calls entered and capture status was complete. The unexpected exception with
an empty declared exception policy set whole-case `incomplete=true`. A read-only
review verified this distinction and the actual follow-up request linkage.

The second replay observed:

```json
{"call1_has_f0010":false,"call1_mentions_project":false,"call2_has_f0010":false,"call2_mentions_controlpkg":true}
```

The model-selected processing predicate was a name occurrence, not a comprehensive
analysis coverage test. Even that selected witness failed. Error absence or exit0
therefore does not establish successful repair. There was no later operator replay
or patch cleanup to change this result.

## Resources and evidence boundaries

- Responses16, all completed; input counts17; actions38; accepted edits2.
  Actions: search21, read10, probe5, edit2. Check/finish actions0.
- Probe actions comprise one request rejection, one helper failure, one baseline
  reproduction and two post-edit replays. Execution success is separate from
  behavioral agreement.
- At termination: model slots4 versus required3; tool slots2 versus required4;
  one edit allowance left; solver time about1353.225 seconds left. The single
  blocking resource was `tool_actions`.
- Cost **USD1.549624**, unused **USD2.950376** closed; active elapsed **656.865s**.
  No automatic retry/resume, protocol correction, response output exhaustion or
  accounting uncertainty occurred.
- Total input473794 including153856 cached; output47421 including41901 reasoning.
  Maximum dispatched input59149 and output15784. One count at68205 input tokens
  was not dispatched; context reconstruction produced a new count within60K.
  Context management acted, but context/output exhaustion was not the terminal cause.
- Public regression, normal submission, isolated acceptance and safety are all
  **NOT_RUN**. Do not treat the wrapper's process exit0 or settled accounting as
  successful repair. The candidate is preserved explicitly as unsubmitted.

## Decision and remaining question

The agent autonomously corrected request/helper errors and established the original
failure. It also received the first patch's negative result and revised. Those are
positive mechanism observations, but the second patch still failed the selected
processing expectation and the entire solve did not complete.

The evidence does not support raising the money, time or output ceilings as the
immediate fix. The observed bottleneck is the use of31 source-inspection actions
before the first edit, followed by two unsuccessful repairs of the downstream
missing-file path. Broad source access was used; useful causal diagnosis did not
follow merely from more exploration.

Before another paid run, the next bounded question is why the explored caller/test
evidence did not change the repair hypothesis toward actual file selection and
processing, and how exploration consumed the opportunity for another verified
revision. The current evidence does not by itself prove those31 actions were all
wasteful, that a larger tool cap would solve the task, or that an extra diagnostic
gate is necessary. Inspect the public read/search results, hypothesis transitions
and reservation decisions before choosing the smallest intervention.

Keep the required-check completion rule. It neither admitted this unresolved case
as success nor received operator-selected counterexamples in this run. No new
runtime change, trial, generalization claim or extra allocation follows automatically.

## Artifacts and audit

Root: `C:/pt/autonomous-fresh-run-v1`.

- `collection.json` and `summary.json`: normal-run public terminal/accounting receipts.
- `runs/run_dev_8fadb1628e0d4415.jsonl`, 277 hash-chained events:
  `sha256:d92e6c835ea5bb2f4ea54506562786055279e6745d2daa3fb816004e8b6db3b6`.
- `public-outcome-audit.json`: accounting, feedback, call observations and terminal
  resource audit, including shared-context independent review:
  `sha256:b180669d53e801ce052f4f9e5c4c908f69cf4ae5fd26758fca641f30f07c800d`.
- `unsubmitted-candidate.patch`, only `astroid/manager.py`:
  `sha256:d52aba72a851f72745986f7f018b5e900b141e390a46be3efdf8a67b0dac2f62`.
- Plan journal `C:/pt/autonomous-fresh-plan-v1/runs/run_dev_normalfreshpreparation.jsonl`
  records exact approval, the single dispatch, returned collection, closed allocation
  and public audit. Historical plans/results remain unchanged.

All outcome review was read-only with respect to the target and solver. No extra
provider, target or evaluator execution was used to audit the result. All five
focused documentation checks passed; runtime behavior was unchanged in this turn.
