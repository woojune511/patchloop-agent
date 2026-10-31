# Task 8 active review with expanded diagnostic budget

Date: 2026-11-01. Status: CLOSED, one authorized attempt, official=false,
claim_eligible=false. No retry, mutation, submission or independent evaluation.

## Question and decision

The [prior active input138 diagnostic](2026-11-01-task8-active-review-results.md)
stopped before its fourth generation at 43,789 > 40,000 input tokens, after
inspection without an executable probe. The selected question was whether the
active post-mutation review could construct and execute a material untested public
case when that diagnostic admission constraint was relaxed. The
[preparation](2026-11-01-search-span-coalescing-and-diagnostic-budget.md) combined
60k input/six-call caps, search-window coalescing and consistent remaining-budget
delivery. Other principal diagnostic limits and the saved public checkpoint stayed
fixed. This was one bounded integrated attempt, not a causal comparison.

Result: **new test construction, execution, interpretation and current-diff evidence
binding were observed**. The model executed nine helper cases with exact byte
assertions, then reported `no_counterexample_found`. None of those assertions failed.
This supports the ability to extend and execute a concrete check in this setting;
it does not establish discovery of a remaining defect, original-case reproduction,
repair, independent acceptance or general improvement.

No further cap increase is supported by this run. It used three calls, a maximum
39,650 input tokens, one probe and no search. Therefore neither the newly available
fourth-through-sixth calls, the input range above 40k, nor search coalescing was
exercised. The changed budget text, ordinary sampling/decision variation and the
combined configuration remain plausible contributors to the different behavior.
Do not attribute the progression specifically to increased caps or deduplication.

The remaining question is verification selection and stopping: the model explicitly
kept the original caller and additional writer path untested, then reported with
resources remaining. A terminal report was allowed and did not require exhaustive
verification. This is not itself a demonstrated host defect or a reason to add a
mandatory probe or coverage gate.

## Frozen scope and authorization

- Executed commit: `f06e50dc3ff990079b62488fdfd3b359e4e901e3`.
- Runtime: `sha256:4fdcc4fb9eb3d71ad81a5d929a0af689cecd876fbd39c212204d0c6343b608c7`.
- Task: checked-in dev-train8, pydicom1413; saved public input138, before a
  current-candidate check/probe. Active `behavior_change` bound to the admitted edit.
- Candidate: `sha256:be082f2721c12b34c2e8032d185297fb2e09379e45a46f5ce7fff1bd642862b9`.
- Model: `gpt-5.4-2026-03-05`, xhigh, one attempt; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Limits: USD2 invocation-wide, six model calls, 60,000 input tokens, full 25,000
  output reservation or stop, 12 actions including report, two probes, 600 seconds.
- Tools: registered read/search/public probe/report only. No edits or evaluator.
- User instruction: “그럼 실험해보자”, directly following the specified changed
  diagnostic scope. A new bound authorization receipt records this instruction;
  no prior allocation or unused balance was reused.
- Stop rules: count/transport/billing/recovery uncertainty stops new calls; SDK
  retries zero. No Docker startup or image pull/build.

Independent read-only preflight confirmed the clean commit, task/checkpoint/
candidate, 14 file and 11 implementation bindings, current pricing receipt, credential
presence, 28 mocked validation cases and the previously absent result root. Execution
also inspected and matched the already installed probe image/profile before dispatch.

## Actual behavior

| Decision | Public action | Observed result |
| --- | --- | --- |
| 1 | Read `pydicom/dataelem.py:494-523` | Current buffer guard and conversion branches delivered |
| 2 | Execute grouped helper | Seven array-input VR cases and two controls; all assertions passed |
| 3 | Bind execution and report | Three executed case groups, one untested group; no counterexample found |

First actual request carried active mutation review; subsequent requests consumed
that trigger and carried the new observations. Current state and appended budget
messages agreed. An intermediate `scope_review` was rejected because it labeled a
historical baseline execution as current. The tool action still ran. The final
review corrected the reference to the newly executed current-diff probe and was
accepted. Reference acceptance certifies identity/currency, not semantic coverage.

The new helper used `Dataset.add_new` and implicit little-endian `write_dataset`:

- Raw array inputs: OB(`B`), OD(`d`), OF(`f`), OL(`I`), OW(`H`), OV(`Q`), UN(`B`).
  Each asserted that the stored value was not `MultiValue` and that encoded bytes
  equaled the expected element header plus `array.tobytes()` payload.
- OL bytes control: exact encoded output equals the OL raw-array output.
- UL list boundary control: remains `MultiValue` and encodes the expected numeric
  bytes, checking that the new buffer guard does not absorb this list case.

The prior helper covered bytes OB/OF/OL and raw OL. This helper added six sibling
raw-array cases, a non-byte list control and exact output assertions. Its stdout
reached `all_assertions_passed` after all nine cases. Exit0, no timeout/truncation,
cleanup confirmed; probe execution took 24.011 seconds. Thus this was substantive
new executed verification, not merely a plan, state-preservation check or exact
replay. The operator audit did not execute the program again.

The original report's `array('H') -> bytes -> lineSeq.add_new -> ds.save_as`
construction was still not replayed. The helper's raw OL array uses `I`; its bytes
control also derives from that `I` array. Explicit-VR/save_as behavior, the added
pytest function and visible regression checks remained unexecuted. The model
reported those limits rather than asserting task correctness. Checks were not
offered by this diagnostic, although one public probe remained available.

## Resources and accounting

| Measure | Result |
| --- | --- |
| Terminal | `REPORT_RECORDED` |
| Model calls / input counts | 3 / 3 |
| Actions | One read, one probe, one report |
| Counted input tokens | 34,319 -> 34,812 -> 39,650 |
| Output tokens, including billed reasoning | 10,962 / 11,407 / 7,511 |
| Recorded generation cost | USD0.6170485 of USD2 |
| Cache-neutral generation cost | USD0.7201525 |
| Elapsed | 432.903 seconds, approximately 7m13s |
| Candidate | Unchanged, no untracked files |
| Acceptance / private evaluation | NOT_ASSESSED / NOT_RUN |

All three dispatched generation usages are known and reconcile with the ledger;
reservations fit the USD2 limit immediately before dispatch. Input counting was
performed on each exact request. Count-endpoint billing and invoice reconciliation
remain **UNVERIFIED**; recorded generation usage is not a reconciled invoice total.
At completion, three model-call slots, nine action slots, one probe,
approximately 167 seconds and USD1.3829515 remained. No budget renewed or next
attempt followed.

## Durable evidence and closure

- Preparation/plan/approval: `C:/pt/active8-review-20261101-v2/`.
- Plan hash: `sha256:3f39da35aaa2652b808ac5118686960a4113dc015c2a4ceb6087574e41a00d85`.
- Approval hash: `sha256:7cf7551aa87ddb5ea664146bab747b622a814bb8666a85bcaff6b2a1b7e5fe84`.
- Request hash: `sha256:a1dea8fac1c90dd7631c8473feef27572a41d72bd1a0a87f390acc41c667ade6`.
- Live root: `C:/pt/active8-review-run-20261101-v2/`;
  run `run_dev_62da82f8f7e34345`, 49 hash-chained events, permanently consumed.
- Result hash: `sha256:e92840f86bc61935e0a64ae9c9827101ddea6082cfa8fe17ed3feb13f4406296`.
- Journal hash: `sha256:0007d67dd77075af1478904a22ff932f7dc29619bea9781736c3cf2b311bba47`.
- Probe action: `call_P83JeQxKd1Qnq3qwbB74sSC5`, action sequences 30/33.
- Probe source hash: `sha256:9a10024996e43bb2a1f42d658bd42b36b428469d4ecd1268d7096a63adcd1fa4`.
- Closure accounting and separate public-behavior audits:
  `C:/pt/active8-review-closure-20261101-v2/`.
- Public audit hash: `sha256:977114d061d35bd0b88431892f7b383fb76e36c456bde1dd769d7423a47ef26c`.

Accounting/integrity audit passed without new provider, count, target or evaluator
calls. Public interpretation uses only the delivered public request, selected
source, tool arguments, execution results and plan/report fields. No raw/encrypted
provider reasoning, hidden tests, private evaluator bodies or reference patches
were inspected. Historical preparation/results remain unchanged. Source runtime
and task packages are unchanged after the run; documentation records this result.
