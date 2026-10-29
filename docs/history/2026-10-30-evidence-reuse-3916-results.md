# Evidence reuse: integrated tasks 3, 9 and 16

Date: 2026-10-30 KST. CLOSED. Three fresh development runs, one per task;
`official=false`, `claim_eligible=false`. No unused allocation remains active.

## Question and conditions

The previous [same-roster run](2026-10-30-contract-guidance-3916-results.md)
returned PASS/PASS/FAIL with repeated narrow probes. A subsequent
[public delivery audit](2026-10-30-verification-evidence-reuse.md) reproduced
loss of concrete probe output at a completion handoff, despite delivery of the
relevant source. This affected verification reliability and justified preserving
existing bounded observations rather than adding tools or finish gates.

This run exercises that fix together with the revised shared contract/case-selection
guidance. The question is whether useful observations survive, relevant public
verification broadens, and repairs complete correctly at acceptable cost/time.
Retention without broader cases or acceptance would weaken the explanation that
lost observations were the primary remaining repair bottleneck. More probes or
successful submission alone are not adoption evidence.

- Execution commit: `45ff269c65d296aa7a60635f5decbece8ed6f6b5`.
- Runtime: `sha256:e8098f8b558a6bd8a5310e0cb07f70deacc3fe86c41fe3a7dab6bd00368d05d9`.
- Baseline commit: `05b1bd7be6340038b5cfca52a1221edd0277c158`.
- Tasks: exact checked-in dev-train 3/pvlib1154, 9/pydicom1694, 16/SQLFluff1517.
- Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 maximum output tokens.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`; contents were not logged.
- Fresh once each, maximum two workers, USD4 per task and USD12 invocation cap.
  Limits per task: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds
  including a 330-second evaluation reserve.
- Policies/source/dependency identities match the baseline: current/brief-v1,
  segmented-v1/result-or-size-v1, ordinary probes, repair-recheck, protected-v1,
  public-checks-v1 and per-call cost admission. Pristine prepared sources were used;
  no prior patch, notes, diagnosis or mini-SWE output entered solver context.
- Mini-SWE had finished before dispatch; host load was not experimentally controlled.
  The worktree remained separate from the primary checkout.
- Count immediately before dispatch, zero SDK retries, shared stop on count,
  transport, billing, continuation or cleanup uncertainty. No resume, replacement,
  image pull/build or extra isolated evaluation.

The question, baseline, selection, intervention, criteria and stop conditions were
frozen in the external manifest before approval. The user explicitly approved this
new USD12 scope. The approval receipt was saved at 21:39:13.395551 UTC, verified at
21:39:26.658027, before batch start at 21:39:26.746876. Previous allocations stayed closed.
Official [model](https://developers.openai.com/api/docs/models/gpt-5.4) and
[pricing](https://developers.openai.com/api/docs/pricing) documentation was rechecked:
USD2.50 input, USD0.25 cached
input and USD15 output per million at the bounded short-context setting.

## Results

| Task | Independent acceptance | Safety | Edits | Calls | Task seconds | API cost USD |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 3 pvlib1154 | PASS | PASS | 1 | 9 | 521.422 | 0.6269575 |
| 9 pydicom1694 | PASS | PASS | 2 | 14 | 468.094 | 0.8680935 |
| 16 SQLFluff1517 | FAIL | PASS | 1 | 10 | 439.083 | 0.72645 |

Total: **USD2.221501**, **33 calls**, two-worker elapsed **909.436 seconds
(15 min 9 s)**. All three submitted with `unverified_delivery`: none supplied a
comparable unchanged-base reproduction. This delivery label is separate from
independent acceptance and safety.

Generation 33/33, input counts 33/33 and actions 53/53 have matched starts/finishes,
input hashes and ordering. Token-based costs reconcile with the ledger and each
reservation; journals and bound inputs validate. No pending action/call/count,
retry, cleanup failure or accounting uncertainty remains. Allocation is CLOSED.

The baseline was the same verdicts, USD2.66038, 40 calls and 882.901 seconds.
This attempt used 16.5% less cost and seven fewer calls, but took 3.0% longer.
Task3 increased from 345.332 to 521.422 seconds; task9 increased from 410.307 to
468.094; task16 decreased from 535.207 to 439.083. Provider dispatch occupied
78.7%, 77.8% and 79.5% of the respective task times. Fewer calls did not imply
lower total latency. One exposed attempt per condition does not establish a
causal improvement, stable efficiency or general repair accuracy.

## Public verification and actual observation reuse

Only public task/source, tool actions/results, public handoff state and submitted
diffs were reviewed, plus independent verdict summaries. No private evaluation
artifact, reference patch, provider payload or reasoning transcript was opened.
Sequence numbers below refer to the corresponding task journal.

### pvlib: retained observations used, duplicate test execution remains

Run `run_dev_c8d128f1b6e44767`. One edit changed the calculation and added
`test_reindl_ghi_zero` in the existing test file. Sequence77 required check and
sequence94 selected test both ran that whole file on the same diff: **99 PASS**
each. This is duplicate execution. Changed-line tracking was unknown, so these
receipts must not be presented as instrumentation proving each new assertion ran.

Sequence111 probed NumPy arrays with zero/normal GHI plus a normal control.
Sequence128 checked scalar zero/normal values and scalar return type. These are
different conditions, not repetitions of the same case. The fresh completion
handoff at turn136 retained sequence111's concrete array/control output under
`recent_probes`, while sequence128 arrived as the latest result. Finish sequence144
cited the observed results. Output retention and subsequent use were observed live;
their causal contribution to acceptance was not measured.

### pydicom: stronger regression test, repeated configuration mistake

Run `run_dev_651a04b8c2b047d3`. Sequence58 moved element access inside the exception
handler and added a mock regression; sequence73 ran **27 PASS**. Probe sequence127
used a malformed raw IS value with default WARN validation and failed because the
expected exception was absent. That condition-selection mistake also occurred in
the preceding run. Sequence160 used RAISE validation and a valid PN control,
observing ValueError and preservation of the valid element. Its question named
TypeError, whereas the actual observation and final regression used ValueError;
question metadata is not itself behavioral proof.

Sequence173 replaced the mock with an actual RawDataElement regression, strict
validation and whole-JSON equality. Sequence189 ran **27 PASS** on the final diff.
Sequence207 replayed the successful probe program after that test-only mutation;
this was reuse bound to a changed full diff, not an identical same-diff observation.
It also exposes the cost of full-diff evidence freshness when only tests change.

The new completion handoff at turn150 retained sequence127's failed output.
After mutation, the earlier probe became historical and was correctly excluded
from current-diff evidence. No unchanged-base comparison was performed.

### SQLFluff: retained output, still narrow cases and incomplete static guards

Run `run_dev_52faf580f57d463b`. Final diff:
`sha256:458da631dfd3cabebea613abe66c3edaaa21026a50523119a2d6c36e8b1994e3`.
The patch still changes the empty-section return in `Delimited.match`. Unlike
the previous unconditional partial success, it returns the accumulated prefix and
remainder only when `allow_trailing=True`; otherwise it fails with original segments.
That addresses one success condition. The new success return still lacks a
`min_delimiters` guard, and the sibling failed-match return still uses
`from_unmatched(mutated_segments)`.

Sequence125 public check ran **167 PASS**. The only probe, sequence144, used normal
`;` and adjacent `;;`, checked a tree existed and observed parse violations. It did
not assert raw preservation/statement counts or test whitespace, newline/comment
gaps, `allow_trailing=False`, or minimum delimiters. A parse violation itself is
allowed by the public issue and is not the established defect.

Full implementation was delivered at sequence60, option tests at sequence97 and
surrounding implementation again at sequence159. After that read, the fresh
completion handoff at turn167 retained sequence144's question and actual output.
Finish sequence175 used it. Neither missing source nor this previously fixed
output-loss path explains the narrow checks observed in this attempt.

The revised patch's gap/minimum cases were **not dynamically rerun**. These are
static residual concerns and absent verification, not reproduced counterexamples
on this exact patch. The exact independent failure remains unknown.

## Decision and next question

Keep bounded observation retention: it repairs a reproduced delivery defect and
now works in live handoffs. Do not claim that it solves verification selection or
improves task correctness; acceptance stayed PASS/PASS/FAIL. There is no speed
improvement in this run. No automatic paid repeat is pending.

The leading remaining question is how the agent turns already-read failure paths
and success guards into discriminating checks before accepting a narrow patch.
First distinguish what was represented in its public plan/check question from
what its test/probe actually exercised. Dynamic public-only replay of this exact
SQLFluff patch would be needed before asserting its residual behavior. Adding
more prompt text, tools or hard gates is not justified by retention success alone.
Duplicate same-diff test-file execution in pvlib is a separate concrete latency
opportunity; it does not explain most elapsed time or SQLFluff acceptance failure.

## Evidence bindings

Preparation: `C:/pt/reuse3916-20261030-v1`.
Results: `C:/pt/reuse3916-run-20261030-v1`.

- Manifest: `sha256:d5f4f3f2d3877f7c7a1c4e5f38330b5f87554ffa53ee59bbf5c39aa522fe9ef7`.
- Approval: `sha256:a97e417aa44d6e612a0caa56f258b1bb444d96545a4fc7be2cbfb9440e306482`.
- Result: `sha256:b06772ede840d0fdfaa2b0b722d44a8226957ce1a9052c154a6699fd14dc85aa`.
- Summary: `sha256:f06e6ffdb8901d258c8a630738275f77ada752b4b8b20cf1e673de4e9e22c081`.
- Operator public review: `sha256:323afeb5cfad4f0464fc8da7a5610aae688fe3f125c5d8c1bab03114b16a88da`.
- Final batch event: `sha256:b60664ac60492e6835625f5cb00c3ab081f7ad38b761e70929537dc7bee1fd50`.

Summary and public review were appended to the external analysis journal. The
implementation's earlier focused/quick/mock validation remains in the linked
implementation record; this follow-up changes documentation only. Post-run
documentation tests: 6 PASS. HTML has 51 unique IDs, 68 valid links and unchanged
scripts; visual rendering was not rerun for this text/table-only update. Runtime
hash remains the execution hash above. Prior reports
and closed historical record bytes are unchanged.
