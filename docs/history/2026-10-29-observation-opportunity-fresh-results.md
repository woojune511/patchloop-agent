# Observation-opportunity clean-start result

## Material Passport

- Recorded: 2026-10-29 KST; execution completed on 2026-10-28 KST.
- ARS experiment-agent, code run; exact approved command executed once.
- Astroid-1333, dev-train current-dev20/13; official=false, claim_eligible=false.
- Runtime implementation `113efa3c4ce1d51dcb6ed79ec64900b8525fa104`;
  execution checkout `f30966a58467cbc4ca9bc9911055dadac42a395b`.
- Result: **EVALUATOR_FAIL, unverified_delivery**. Public regression PASS,
  isolated task acceptance FAIL, safety PASS; original reproduction unverified.
- Accounting SETTLED; USD1.476264/4.50; allocation CLOSED, no automatic retry.

## Question and fixed execution

The [sealed plan](2026-10-28-observation-opportunity-fresh-plan.md) asked whether
restoring original-call observation choices lets the model inspect file selection
and processing, improve its hypothesis, and complete a correct repair. This follows
the [prior clean-start failure](2026-10-28-autonomous-fresh-results.md) and the
[locally validated intervention](2026-10-28-observation-opportunity.md).

The user approved `& 'C:/pt/observation-opportunity-fresh-plan-v1/run.ps1'`, repeat1,
with a new invocation-wide USD4.50 cap and manifest
`sha256:02215df8317e669b40e1e973cbe12fa73c73d25df7e161804487b4130b74c21f`.
The run used gpt-5.4-2026-03-05(xhigh), the repository `.env`, response20 including
correction1, action40, edit3, input60K, output40K/correction25K, total2400 seconds
including390 reserved for isolated evaluation. Read-only pylint source access
and prepared public dependencies were retained. The request was unchanged from
the baseline except its result root; runtime was frozen during execution.

No saved patch, prior observations, operator counterexamples, reference patch or
private evaluation details were injected. The first actual request had9357 input
tokens. Its preparation, count and dispatch hashes matched; differences from the
offline first request were only remaining time and segment identity.

## Public trajectory

Sequences refer to `run_dev_3d8ae3e18dae4b70`.

| Sequence | Observation |
| --- | --- |
| 51 | `pylint:run_pylint` was rejected as an invalid dotted entrypoint before execution. |
| 65 | Corrected entrypoint `pylint.run_pylint`, but helper called `check_setup` without `actual` and `expected`. Both declared call capture and target entries were empty. |
| 69 | The complete TypeError reached the next actually dispatched model request. |
| 81 | The model fixed the setup calls: seven supplied comparisons passed. It also expanded `input_paths` from4 to7; `observed_target` rejected this against its maximum4 before any captured target entry. |
| 85 onward | The second error reached the next request as `invalid observed_target settings`. The host correctly separated it as a typed pre-target request attempt; the first setup error remained an UNKNOWN case. Acquisition attempts2/2 were consumed, with no established original failure. |
| 140 | Read/search/probe were temporarily excluded by protected cost admission; only edit/check/stop were offered. This state had no acquired original failure, so the new post-acquisition minimum-path fallback did not apply. |
| 147 | After15 inspections and3 probe requests, the model edited `astroid/modutils.py` to skip `_path_from_filename` for existing directories. |
| 162 | Current-diff public base-regression passed:1231 passed,69 skipped,15 xfailed. Changed-line observation was UNKNOWN because the launch options were unsupported; it was not evidence of execution or nonexecution of the changed lines. |
| 170,185 | The model received both public PASS and the missing original evidence. General read/search/probe options were available again; it read once, then finished. |
| 191,195 | `finish_task` returned `unverified_delivery`; the exact candidate was stored as a submission. The model assessment also acknowledged missing baseline/current replay. |
| 197,198 | Isolated task acceptance FAIL, safety PASS; terminal EVALUATOR_FAIL. |

The gateway status `succeeded` for the two executed probes means their actions
settled; both probe outputs were `failed`, with no observed JSON and
`not_compared`. Neither establishes F0010 reproduction, error removal or processing.
No post-edit original replay or failed-repair revision occurred.

## Explanation supported by public evidence

The first-reproduction-only tool description named `check_setup` but omitted its
required `(label, actual, expected)` signature. The general description contained
that signature. Neither description specified `input_paths` maximum4. The settings
error identified neither the offending field nor its actual/maximum size.

Thus the first helper error was not simply ignored: the model corrected it from
the delivered feedback. The second request encountered a different undisclosed
constraint and consumed the remaining acquisition attempt. These omissions are
confirmed contract defects. This one trajectory does not prove that better
documentation alone would ensure a valid helper or a correct repair.

Fresh v10 classification was exercised correctly: settings rejection with zero
target entries became a request attempt instead of a replay obligation. The earlier
setup error did not carry that typed evidence and remained UNKNOWN. Costs and
attempt counters were retained, as designed. This is classification evidence,
not successful recovery evidence.

The original-call observation selector was never offered because no usable original
failure was acquired. The model therefore did not decline an available
`observe_original` option. This trial leaves the central post-reproduction
observation/repair hypothesis untested.

The candidate's stated hypothesis assumed that `_path_from_filename` changed
directory inputs. Public source lines174-180 show that it returns its input on
non-Jython. For the reported CPython inputs, the edit preserves the normalized
filename. This is a static source inference about a weak repair hypothesis; no
additional operator replay was run. Independent acceptance FAIL establishes the
submitted patch did not pass the task, without exposing private failure details.

Finish preserved the missing original obligation as `unverified`, rather than
granting verified repair credit. Current contracts permit delivering an unverified
candidate when acquisition has been released and required public checks pass;
known failures and pending verification have different blocking rules. Submission,
public PASS, safety PASS and task acceptance remain separate outcomes.

## Resources, decision and limitations

- Model responses12/20, input counts12, actions22/40, edits1/3. Actions were
  search10, read6, probe3, edit1, public check1, finish1.
- USD1.476264 spent, USD3.023736 unused and closed; active851.269 seconds.
- Input294888 including37376 cached; output54876 including49277 reasoning tokens.
  Maximum dispatched input50834 and output18219. All responses completed.
- Count, provider and action pairs match, usage receipts settled, cost sums agree.
  No protocol correction, transport/billing uncertainty, automatic retry or
  additional target execution occurred. Existing pinned images were used.

The terminal was task evaluation failure, not exhaustion of money, total response,
action, time or output ceilings. Local acquisition attempts were exhausted and
protected cost admission temporarily restricted exploration. A larger overall cap
does not directly repair the missing API contract or validate the patch hypothesis.

Keep the typed settings classification and honest unverified-delivery distinction.
Before another paid trial, align the specialized first-reproduction description
with the actual helper API and expose specific invalid-field feedback. Then verify
the bounded setup-correction path using local fixtures. The appropriate handling
of setup errors that lack typed target-entry evidence remains a separate question;
do not erase UNKNOWN obligations or refund attempts without evidence.

This changes the next engineering focus from post-reproduction observation uptake
to obtaining a valid first invocation. It does not justify reverting the restored
observation option, claiming repair improvement, or automatically spending the
unused funds. One exposed development task with a bundled intervention and a prior
historical run is not a causal estimate or held-out generalization result.

## Durable artifacts and verification

Root: `C:/pt/observation-opportunity-fresh-run-v1`.

- `collection.json`, `summary.json`: terminal, accounting and verification states.
- `runs/run_dev_3d8ae3e18dae4b70.jsonl`,198 chained events:
  `sha256:3c61779da772c848464c1e434e092d88e9dd6500a7f06c38321356e40598cef1`.
- `public-outcome-audit.json`: public action, usage, tool-offering and submission
  audit, including shared-context independent review:
  `sha256:5fd2f647f2879f444636b14bf51967708a1cb9f5d564c48203fa22ccea8a1a4d`.
- `helper-contract-audit.json`: nine public request identities, two helper
  executions and their next-response feedback linkage:
  `sha256:18a1d63d1fbff3dda239b77ee1e129f72b59f916e54b6de176ebf44b0e373f97`.
- `submitted-candidate.patch`, only `astroid/modutils.py`:
  `sha256:a86dc1f13e7cb12cb03ad57f8549f88615dddfdb76e0e8fd59d53de6bfe629a4`.
- Plan root `C:/pt/observation-opportunity-fresh-plan-v1` retains approval and
  preparation/dispatch/return/collection/audit journal records.

Post-run review used public receipts and source only, plus the isolated acceptance
and safety summary. No private evaluator content was inspected or returned to the
model. Runtime and historical evidence were not changed. All14 bound inputs and
the runtime hash still match. Five documentation checks passed in1.906 seconds;
unchanged runtime tests were not repeated. The top-level history navigation now
groups daily October indexes to remain under its existing byte limit.
