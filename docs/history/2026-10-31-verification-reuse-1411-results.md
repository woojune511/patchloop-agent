# Verification reuse: fresh integrated runs on tasks 1, 4 and 11

Date: 2026-10-31. Status: CLOSED. All runs official=false, claim_eligible=false.

## Question, intervention and fixed conditions

After the [reuse correction](2026-10-31-verification-reuse-decision.md), the user
authorized the proposed fresh 1/4/11 batch with "진행해줘". The question was whether
the agent would reduce repeated same-diff checks/probes while preserving useful
verification and independent acceptance. This matters because repeated decisions
consume model latency and cost even when the test process itself is fast.

Code: `1569ec49e75e09dbe8f5e3024fa8cccc73b5a2c7`.
Runtime: `sha256:06b0bbc8bd933616c7e40495a87bdaf76207db10f477263d98bbb6ab0cb8e866`.
The intervention distinguishes declared selection from unreported collection,
makes file selectors optional, removes repeated suggestions after passing explicit
file selections, and compares intended input/setup/assertions with existing evidence.
No new execution cache, semantic gate or cross-run memory was introduced.

The reference is the closed [previous 1/4/11 batch](2026-10-31-integrated-1411-results.md)
at `90adcb15`. This is a historical single-attempt reference, not a randomized or
seed-matched control. The new serialized requests differ only in state_root:

- dev-train 1 marshmallow1343, 4 pvlib1606, 11 Astroid1196; one fresh attempt each.
- `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`, without key content in artifacts.
- Two workers; USD4 per row, USD12 invocation cap, no allocation transfers.
- Per row: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds;
  the same 330-second evaluation reserve inside that limit.
- segmented-v1, result-or-size-v1, brief-v1, current agent, probes enabled/none,
  probe-recheck none, repair-recheck, protected-v1, per-call-v1, public-checks-v1.
- Same pristine prepared source and public dependencies, unchanged task hashes.
  No earlier patch, counterexample hint, private expectation or reasoning was supplied.
- Exact input counting before dispatch, default service tier, zero SDK retries.
  Count/transport/billing/continuation/cleanup uncertainty stops new admissions;
  already admitted calls settle. No extra independent evaluation or automatic retry.

The [official Standard pricing](https://developers.openai.com/api/docs/pricing) was
rechecked: USD2.50 input, USD0.25 cached input, USD15 output per million tokens for
the selected short-context tier. The runtime's 60K input bound stays below 272K.
All existing images and three public import/operation/selected-test canaries passed.
No Docker startup or image pull/build was performed. Canaries were operator
preflight executions, not model calls or solver verification evidence.

Predeclared criteria included acceptance, safety, public regressions, repeated
selections, new cases, post-edit rechecks, calls, settled cost and wall time.
Fewer checks alone was not an improvement criterion. Runtime stayed fixed during
execution; all three rows and billing settled, with no uncertainty stop or retry.

## Results

| Task | Independent acceptance / safety | Calls / actions | Edits / probes | Row seconds | USD |
| --- | --- | --- | --- | --- | --- |
| 1 marshmallow1343 | PASS / PASS | 9 / 12 | 1 / 2 | 319.598 | 0.6293905 |
| 4 pvlib1606 | PASS / PASS | 14 / 18 | 2 / 1 | 529.036 | 0.9396450 |
| 11 Astroid1196 | PASS / PASS | 15 / 23 | 2 / 2 | 583.923 | 1.0270865 |
| Total | 3 PASS / 3 PASS | 38 / 53 | 5 / 5 | 905.879 batch wall | 2.5961220 |

| Observation | Previous | Current |
| --- | --- | --- |
| Independent acceptance | 3/3 PASS | 3/3 PASS |
| Model calls | 49 | 38 |
| Actions | 66 | 53 |
| Batch wall time, two workers | 1,387.099 s | 905.879 s |
| Settled model cost | USD3.607668 | USD2.596122 |
| Selected tests overlapping passing declared scope | 3 | 2 |
| Strict same-diff semantically equivalent successful probe repeat, manual audit | 1 | 0 |

Observed cost decreased 28.04%, batch wall time 34.69%, and calls 22.45%.
These are batch observations, not causal savings attributable to the guidance.
Row4 calls/cost increased (11 to14, USD0.806706 to0.939645); different patch and
verification paths contribute. Provider dispatch occupied 81.9–87.5% of row time.
All three deliveries are still `unverified_delivery`: independent acceptance,
public observations and the registered original baseline/replay requirement differ.

## Public behavior and remaining repetition

### Task1: success observations reused; logging correction was necessary

One source/test edit (seq59–60) skips None data/items in field validation and adds
one regression for the public report. Required check seq74–75 passes 780 tests.
No later run_check or run_tests occurs on that patch.

The first helper seq109–112 executes cases but fails JSON sorting on mixed integer/
string keys; only before-call markers survive. Seq124–127 corrects output handling
and prints six outcomes: invalid single/many inputs and normal/validator-rejection
controls. The helper has no automatic assertions, so exit zero alone is not semantic
verification; the concrete outputs support the limited conclusions. The next action
is finish seq141–142, which uses those outcomes. No candidate defect was found by the
failed helper, and no second source repair occurred.

Compared with the earlier run, subset tests fall 2 to0 and helpers 6 to2. The new run
has no unchanged-base reproduction, mixed valid/invalid list helper, or invalid-whole-
many helper. This is a difference in explicit diagnostic scope, not proof those
behaviors were absent from the suite or incorrect in the patch.

### Task4: real regression repaired, collection reassurance still repeats

The first edit seq48–49 indexes a scalar convergence result as an array. Public
check seq63–64 finds 7 FAIL / 251 PASS. The second source edit seq94–95 fixes scalar
handling with np.all; the harness recheck seq99–100 passes 258 tests. This is a
necessary repair and recheck, not redundant success verification.

Helper seq129–132 checks equal/ordinary scalar bounds and also asserts the normal
objective value, beyond the existing scalar test's optimum-position assertion.
Then seq144–145 selects four nodes in the already passing `test_tools.py`: 6 PASS.
Its public basis explicitly cites unreported collection. Input seq135 already
contains full-file PASS, exact registered targets without filters, selected test
definitions, new reuse guidance, and no optional selector. No new input/assertion
or concrete discovery/filter suspicion is named. This is residual scope overlap;
the narrower receipt adds explicit node confirmation, not a new behavior case.

Later searches/reads prepare a CEC caller diagnostic but it is not executed.
Finish seq215–216 cites current PASS, source support and no current failure; it
honestly discloses that full ModelChain/bound original replay remains unverified.
run_probe and substantial resources were still available. There is no explicit
reason why the newly prepared caller case stopped adding value, but this does not
establish a defect, resource exhaustion or a mandatory caller-probe requirement.
The new guard also covers initially small nonzero intervals, unlike the old
equality-only guard; no separate near-equal boundary observation was recorded.

### Task11: same-diff repeat removed; test-only replay and subset selection remain

Source edit seq108–109 iterates inferred unpack values, skips Uninferable and catches
getitem errors; it differs from the old unique-Dict restriction. Helper seq123–126
prints named-dict success and unresolved-name AstroidIndexError. Seq155–156 adds two
asserting tests without changing implementation. Required check seq168–169 passes
1,293 tests with 76 SKIP /14 XFAIL.

Seq184–187 replays the same helper after that test-only edit changed the full diff.
It adds no case, but is a different-diff replay under the existing currency rule,
not a new delivery defect or strict same-diff repeat. The old observations were not
presented as current evidence after the mutation.

Seq220–221 then selects the two new nodes on the same diff after full-suite PASS:
2 PASS. The earlier plan reason said targeted execution was unnecessary, then the
new basis cites unreported collected nodes without a new edit or failure. Input
seq214 retains the suite PASS, tests-directory scope, directory_selected/not_reported,
optional selector, reuse guidance and helper stdout. PASS delivery loss is contradicted.

The earlier non-Dict helper boundary is absent; multiple-inference behavior and the
wider AttributeError catch have no separate diagnostic here. These are unobserved
boundaries, not demonstrated failures. There is no second implementation repair.

## Scope overlap costs and interpretation

| Current selection | Tool seconds | Associated model seconds | Associated USD |
| --- | --- | --- | --- |
| Task4, four nodes after explicit-file PASS | 5.516726 | 12.126291 | 0.049421 |
| Task11, two nodes after directory PASS | 3.241333 | 61.409270 | 0.111070 |
| Total | 8.758059 | 73.535561 | 0.160491 |

Prior corresponding totals were 11.805931 tool seconds, 125.496561 model seconds
and USD0.237240. Declared scope overlap is not per-assertion execution proof or a
guaranteed avoidable cost. Both batches have zero exact same-check-ID/same-diff
rechecks after PASS. The helper's exact-program detector does not identify renamed
semantic equivalents; that distinction was manually audited from public evidence.

Keep the correction: its scope display is more accurate, and no local-contract or
independent acceptance regression was observed on this panel. It only partially
addresses repeated verification. The remaining selections happened with the new
guidance and PASS evidence visible, so another generic reuse sentence is not supported
as the next intervention. Concrete collection/execution receipts are a possible way
to resolve the remaining uncertainty, but their benefit and complexity are untested.
No new gate, mandatory probe, implementation change or paid allocation follows here.
This batch cannot establish that all prior verification coverage was preserved,
general repair improvement, or a causal latency/cost gain.

## Reproducibility and evidence boundaries

Preparation: `C:/pt/reuse1411-20261031-v1/`.
Execution: `C:/pt/reuse1411-run-20261031-v1/`.
The manifest records the question and criteria before execution. Approval and
readiness records bind this fresh authorization; older allocations stayed closed.

- Manifest: `sha256:f7162c731b999cbb759a5c8605723ac34f0c4829cd5f329bef5cf7f5e79d511d`.
- Result: `sha256:c77fc278d85f6a6f2d26684e185ae34f64288f611fb27c9c09ab37bb6fbd82a9`.
- Batch completion: `sha256:6829a2de1874f473d5d65fc70647cfc6d66f068fd34c3372623076b44d678df5`.
- Public flow CAS: `sha256:c0aefb1d811d7d6e4d928f40a72de9c400e51360f33d69a83b8f36fdebb476fc`.
- `summary.json`: settled calls/cost/time, patches and final journal hashes.
- `analysis/verification-comparison.json`: declared overlaps and origins; classification
  helper has seven synthetic local tests. This is an operator audit, not solver state.

Exact public prepared inputs used in the audit (artifact hashes):

- Task1 after suite, seq83: `sha256:7a721d7992ee7a3ee7144472609e9a61c91b057c3c98983d1ac73d3b0a09a8ef`.
- Task1 before finish, seq135: `sha256:4aad304f7a825c646a9306f067f1cac972b19ba836824ee5f0681af5050cfbfe`.
- Task4 before subset, seq135: `sha256:0b0482ead7d7ff25ce72b85c68a36080b8d1f693a3112151898001387621363d`.
- Task4 before finish, seq209: `sha256:9f844d8ab9120008efdb337caefcc3f44b16c59229b22b4b9b0ddd5175fe1ffc`.
- Task11 before replay, seq177: `sha256:52cac469054b22bcec31c72f991a82fe6bffc1b9cef51b30aa02bfcabd693810`.
- Task11 before subset, seq214: `sha256:f00d83e9b9ce5adce22cb8b6ec42c7bdef8998d7347b43ce3b032f0feedd7d55`.

Audit reads public actions, source and delivered inputs, plus evaluator verdict
summaries only. Private evaluator bodies and provider reasoning were not read or
fed back. No target test or evaluator was rerun for the post-run audit. Generated
state stays outside the repository in hash-chained dev-run-v1 journals and CAS.
