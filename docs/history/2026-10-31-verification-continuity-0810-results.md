# Verification continuity: fresh tasks 8 and 10

Status: CLOSED. Executed 2026-10-31; official=false, claim-eligible=false.

## Question and frozen scope

Can the agent retain the original input/caller/assertion while finding and repairing
remaining defects? Tasks 8 (pydicom1413) and 10 (pydicom901) were selected by the user
because the [previous full20 run](2026-10-31-verification-reuse-dev20-results.md)
failed both and exposed gaps in delivered probe programs and rejected test proposals.
The [continuity change](2026-10-31-verification-continuity.md) supplies those existing
public facts without another prompt rule, tool or completion gate.

The current explicit instruction authorized each task once. The established session
baseline supplied the same model, credential file and USD4 per-task limit; the new
two-row allocation was USD8, stated before dispatch. The authorization receipt
records that contextual derivation, not a new numeric quotation or reuse of the
closed USD80 allocation. No previous patch, known operator counterexample, private
expectation or cross-run notes entered either solver's context.

- Code: `4559062da796b6145ad1f7e2e84689fe084f9759`.
- Runtime: `sha256:832d5d3f6c58da7a64af4743794f1557fa1b307245110c7e86ce98b89f453ab3`.
- Checked-in `dev-train/current-dev20/8` and `/10`, pristine prepared sources.
- `gpt-5.4-2026-03-05`, xhigh, 25,000 output-token ceiling; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- One fresh attempt each, two workers; USD4 per row / USD8 invocation cap, no transfer.
- Per task: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds including
  the 330-second evaluation reserve. Existing selected policies remained unchanged.
- Zero SDK retries; count, transport, billing, continuation or cleanup uncertainty
  stops new admissions. No retry, extra evaluation or runtime edit during execution.

Source/dependency identities, existing pinned images, public capability canaries and
11 frozen bindings passed before launch. Docker was already running; preparation
did not start Docker Desktop or pull/build images. Available host disk was about 1.1 GiB,
above the prior two task directories' approximately 80 MiB footprint. Official
[Standard pricing](https://developers.openai.com/api/docs/pricing) was checked:
USD2.50 input / USD0.25 cached input / USD15 output per million tokens within the
short-context tier. No model or service tier was changed.

Success criteria were original observable fidelity, executed counterexamples,
production repair and post-edit verification, with independent acceptance/safety
reported separately. Exact delivery versus subsequent use and conditional rejected
proposal recovery were audited. Two development-exposed single attempts cannot
estimate a causal effect or held-out repair gain; a trajectory without rejection
cannot test rejected-proposal retention.

## Results

| Task | Public check | Probes | Edits | Calls / actions | Independent / safety | Cost | Row wall |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| 8 pydicom1413 | 213 PASS | 1 PASS | 1 | 9 / 10 | FAIL / PASS | USD0.6141665 | 275.674 s |
| 10 pydicom901 | 96 PASS, 1 SKIP | 0 | 1 | 10 / 22 | FAIL / PASS | USD0.579916 | 211.573 s |

Total **USD1.1940825**, 19 model calls, 19 input counts, 32 actions, two accepted
edits and one probe. Batch wall **278.086 seconds (4m38s)**. All counts, actions and
billing settled; both patches were submitted and evaluated exactly once. Neither
row exhausted a cost, model, action, edit or total-time limit. There was no retry,
uncertainty stop or extra evaluator execution. The allocation is closed.

Both registered original-case delivery states remain `unverified_delivery`:
zero original executions, no baseline failure and no replay. Their diagnostic
acquisition states ended with `preparation_action_limit` (6 investigation actions
for task 8, 10 for task 10). This is an internal acquisition limit, not exhaustion
of the whole run budget, nor proof it caused the failed repair. Ordinary public
probes and checks were still available.

## Task 8: useful source repair and controls, incomplete caller evidence

The agent read the setter and conversion code, then independently identified the
missing binary VR exclusions before running any probe. Mutation 82→83 added OL/OD
to the no-backslash-split path and added an OL bytes-with-0x5c writer regression.
The test asserts that the stored value equals the input bytes and that serialized
element bytes match the expected bytes. The public check at 97→98 passed 213 tests.

Probe 113→116 exercised the changed setter: OL and OD byte payloads containing a
backslash must remain equal bytes, while text VR LO must still split `A\\B` into a
MultiValue. All assertions passed. OD and LO provide a sibling case and a negative
control; this is meaningful expansion, not a repeated identical successful check.

The public report instead constructs bytes from `array('H', ...)`, inserts the
reported OL tag through `Dataset.add_new`, then calls `Dataset.save_as`. Undefined
fixture details in the report require explicit assumptions. The added test uses
`DataElement` plus the element encoder at another tag; the probe uses direct
`DataElement` construction and does not write a file. Neither executes the full
reported caller on the unchanged base or submitted candidate. Finish 130→131
explicitly discloses that omission.

Completion input 124 retained the exact program inline under
`recent_probes[0].program`; its hash is
`sha256:5e4a313f9cd65ad5fac1196bc4fbe6f3a13eb4282f2f38fe36f55d4934f6182d`.
The input artifact is
`sha256:6c3e24e429a27a41b96b73f95d1a5a6f4935af706857cf3af6b03a529382be6b`.
No native or archived probe call supplied an alternative copy there. The final
assessment uses the OL/OD/LO observations, so program delivery and result use were
observed. No subsequent counterexample construction or repair occurred after that
delivery. The initial discovery preceded the only probe; retention therefore cannot
be credited for discovering it. Independent acceptance was FAIL. The inspected
public executions contain no residual failure, and they do not identify the private
failed assertion or prove the omitted caller is its cause.

## Task 10: state assertions did not observe duplicate output

Mutation 82→83 removed import-time handler/formatter setup and `debug(False)`, set
the initial debugging flag to false, and added a reload test. The test installs a
NullHandler as caller configuration; production code does not add it. Assertions inspect the logger's handler
list, ERROR level and debugging flag. It does not emit, capture or count a record.
Public check 97→98 passed 96 tests with one skip. Nine subsequent source searches
and finish 166→167 added no behavioral execution; there was no probe.

The original user-visible concern is duplicate emitted log records under caller
configuration. Logger state is relevant but cannot substitute for observing that
output. The final assessment admits no end-to-end replay. Thus the original
observable remained untested even though the implementation addresses the reported
import-time setup. This public audit establishes a verification gap, not a remaining
source defect or the private FAIL's exact cause.

There was no rejected mutation. All ten prepared public states had no rejected
proposal or prior probe program to retain. Both retention mechanisms were therefore
unexercised for task 10: there was no stronger earlier assertion lost during this
run, and no basis for saying the new mechanism failed to preserve it.

## Decision and limits

Keep the locally verified delivery correction, but **do not claim repair gain**.
The latest attempt shows actual probe-program delivery, not the intended sequence
of retained evidence → new counterexample → additional repair. Task 8 found a useful
source defect before that mechanism could act; task 10 never triggered either path.
Both independent outcomes remain FAIL, as in the historical reference attempts.
Lower observed cost/time accompanies different and narrower execution trajectories;
it is not an efficiency improvement with correctness preserved.

Do not add another general reminder or increase the whole-run budgets from these
results. The next unresolved question is the exact submitted-patch failure versus
the missing original-caller/output observations. An operator-only inspection of the
saved failed assertions, followed by a separately scoped public reproduction where
possible, would distinguish source defects from test-oracle differences before
another agent intervention. Private details must never enter solver context. No
such inspection, extra target execution or further paid run was performed here.

## Durable evidence and validation

- [Frozen manifest](C:/pt/continuity810-20261031-v1/manifest.json):
  `sha256:2d5e519818eeb7ebdc9f55a7f053256c5ea2825105170dea22a2ce1768abcb98`.
- [Batch result](C:/pt/continuity810-run-20261031-v1/result.json):
  `sha256:2d2b437896b4f925994e0e6bd8dba0ecc0c8975432f5bdeca60ec9ad155fee40`.
- [Summary](C:/pt/continuity810-run-20261031-v1/summary.json):
  `sha256:ff7dd1fafc898437ecd4f558652e627f094197ffbe56b70a7098bc55970cb27a`.
- [Public flow](C:/pt/continuity810-run-20261031-v1/analysis/public-flow.json):
  file `sha256:d7c6758fde3be74e5ceea2465b9be2e0f86bc5fa2b3f401d468b5029bdd26773`;
  CAS `sha256:ef1a92b2df8375cc5f49d2cad35e670b18679d69d5b3046805c84c44feae5a56`.
- [Task 8 audit](C:/pt/continuity810-20261031-v1/audits/task08.json) and
  [task 10 audit](C:/pt/continuity810-20261031-v1/audits/task10.json) bind public
  action, model-input and submitted-patch identities. No private evaluator bodies
  or raw provider reasoning were read.
- [Independent metadata validation](C:/pt/continuity810-20261031-v1/audits/batch-independent-validation-v2.json):
  128/128 checks; 11 bindings, three journal chains, count/call/action settlement,
  exact token pricing and both submitted patch CAS identities. File hash
  `sha256:1675e9365fe58ce214b93cde81c2b51f349681c1a16c6968a3465729eec60233`.

The first local metadata report write failed to serialize a datetime; its empty
output and original script were preserved. The successor reports that failure and
uses an ISO timestamp. No solver/provider/target execution was repeated. Runtime
source is unchanged from the prior 1,362-PASS quick suite with isolated mock.
This reporting follow-up passed all six documentation-layout tests; link, script
and runtime/hash validation receipts are stored with the preparation artifacts. Historical
experiments, prior submitted patches and prior reports remain unchanged.
