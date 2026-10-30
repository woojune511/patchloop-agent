# SQLFluff fresh run with applied-change review

Date: 2026-10-30 KST. Allocation CLOSED. One exposed development attempt;
official=false and claim-ineligible. No retry or extra evaluation is pending.

## Question, scope and comparison

The user requested one fresh SQLFluff task 16 run on the latest code to see whether
the agent connects changed success conditions to a refuting case, executes it,
finds a violation and repairs it. This follows the
[applied-change review implementation](2026-10-30-post-mutation-review.md).
The question matters because earlier public checks passed while operator public
cases found rejection-to-success regressions. This is a normal integrated
development run, not a forced reproduction of that earlier repair.

Execution HEAD `fbfdd213ca28fdfb0eb27e65c533a22c0d72188d`; runtime
`sha256:47057ca997eaa2ba5c3c566aa76df16ae9c4e2bdb41b47f08d68da05b0ff2fd9`.
The direct request continues the previously specified single-task conditions:
dev-train 16 / SQLFluff1517, gpt-5.4-2026-03-05 / xhigh, credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, one fresh repeat and worker, new USD4
total cap, 40 model calls, 100 actions, 12 edits and 1,800 seconds including a
330-second evaluation reserve. Output target 25,000; current/brief-v1,
segmented-v1/result-or-size-v1, probes enabled/policy none, repair-recheck,
protected-v1, per-call-v1 and public-checks-v1.

The normalized request matches the preceding normal run except for the fresh
state root. Runtime is the intended intervention; source, dependencies and local
image identities were revalidated without starting Docker or pulling/building
images. The [official pricing table](https://developers.openai.com/api/docs/pricing)
confirmed USD2.50 input / USD0.25 cached input / USD15 output per million at this
context tier. Exact counting, zero SDK retries and uncertainty stopping remain.
The new direct-request authorization is recorded separately; old allocations and
approval receipts were not reused. A local timestamp-serialization error was
corrected before dispatch, with zero provider calls at that point.

No prior patch, operator counterexample, audit rubric or other-agent output entered
solver context. The observer criteria were frozen before execution: actual review
delivery, independently authored contract/input/assertion, execution on current
diff, and evidence-driven repair or narrowing. A different correct first repair
need not exhibit the previous defect or manufacture a violation.

Preparation: `C:/pt/postedit16-20261030-v1`.
Result: `C:/pt/postedit16-run-20261030-v1`.
Run: `run_dev_1249575172444847`.

## Result

| Measure | Previous normal run | Applied-change review run |
| --- | --- | --- |
| Independent acceptance / safety | FAIL / PASS | FAIL / PASS |
| Required public check | 167 PASS / 1 deselected | 167 PASS / 1 deselected, twice |
| Delivery | unverified_delivery | unverified_delivery |
| Accepted edits / calls / actions | 1 / 12 / 24 | 2 / 30 / 51 |
| Probe executions | 1 | 5 |
| Cost | USD0.7579325 | USD2.1578225 |
| Task wall time | 457.526 seconds | 1,046.929 seconds |

All 30 calls and input counts settled. No transport, cleanup or action error was
reported. Batch wall time was 1,049.710 seconds. Generation dispatch occupied
785.199 seconds, approximately 75% of task wall time. The submitted diff is
`sha256:ab25026869f0d02dec7a32bb34c06140b7fdec55cb0ce337f6c6565b4e46c82b`.
Independent evaluation ran once. Its private failing assertion was not inspected.

This attempt used more calls, money and time without independent acceptance gain.
These are descriptive results, not a causal estimate of the new review instruction.
Both runs are exposed development attempts; host load and model sampling differ.

## What the agent actually did

| Public sequence | Observation and implication |
| --- | --- |
| 164/165 | First mutation changes five single-line `from_unmatched(mutated_segments)` returns to `from_unmatched(segments)`. It explicitly aims to preserve failure semantics and full input, rather than return a matched prefix. It also adds a parse-only regression. |
| 173, 178, 180 | New review is delivered; the plan selects the required regression. 167 tests pass. This review happens after the initial implementation, so it cannot be credited with causing that first repair. |
| 198, 215, 260 | Two probes wrap lint calls and `check_tuples()` in the same try block. A SQLParseError from result inspection is labelled `lint_exception` or `wrapped_exception`; the plan incorrectly treats it as a remaining stdin caller defect. |
| 294, 330, 347, 359 | On the same implementation diff, probes without that accessor return normal lint results. Public `linted_file.py` lines50-64 explain the accessor's default exception behavior. The plan retracts the caller-defect interpretation. |
| 407/408, 416, 423, 425 | Only the added regression changes: it now calls `lint_string_wrapped(..., fname="stdin")`, checks one path/file, a tree, exact raw input and a returned SQLParseError. The second review is delivered and the current-diff suite again passes167 tests. |
| 443, 459/460, 474/475 | The correct wrapped-lint probe is replayed after the test-only change. Source searches reconfirm the accessor and CLI caller. Finish cites the observed result and explicitly says exact original CLI replay remains unverified. |

All five probes use adjacent doubled semicolons and a normal single-semicolon
control. No new grammar-option counterexample is executed. However, this first
repair preserves failure returns; assuming it still has the earlier partial-success
regression would be incorrect. Its remaining behavioral defect has not been
established by this audit.

The observed loop is diagnostic misinterpretation -> discriminating observation
and source -> corrected interpretation -> caller regression strengthening. It is
not an observed semantic violation -> implementation repair loop. The second
mutation changes tests only; implementation remains the first candidate's code.
Tool exit0 or `probe_status=passed` alone does not make the probe's interpretation
correct: both misleading exception-labelled probes also returned exit0.

## Delivery and stopping evidence

Actual active review requests appear only at 173 and 416, with the correct admitted
action/input identity, before/current diff and exact attached guidance. Historical
receipt copies do not create another active review. First review173 also supplies
the before/after hunks and the full current Delimited file through the public
mutation archive: mutation evidence 141-251 plus revalidated source 1-143, file hash
`sha256:5ef33ea1a5130777251e0becd7aaafd050d090faaf839dd1903a8195e3aeb4b4`.
An inline character count of zero at that turn does not mean missing source.

At 416 and final 468, the full Delimited body is absent from current sources and
native/public source archives; the complete submitted patch's hunks remain.
This bounded-context observation is distinct from the verified first-review delivery.
Neither establishes a cause of the independent failure.

At final request 468, before its dispatch, 11 model calls, 50 actions, 10 edits,
520 solver seconds and USD1.9469635 remain. Read, search, edit, probe and test tools
are offered. A hard resource gate did not force finish. The final assessment
correctly separates the wrapped-lint helper evidence from unexecuted exact CLI
replay; public-checks-v1 leaves that missing original-case evidence advisory.

## Decision and limits

The review-delivery mechanism worked in this live run. Autonomous discovery and
repair of a changed success-condition violation remain unverified, and acceptance
did not improve. The first repair takes a different approach and was authored
before the first review, so neither its difference nor the test strengthening
establishes a causal gain from the intervention.

Do not add another general warning or mandatory probe merely because this run
failed. The concrete diagnostic weakness observed here is conflating an operation
with later result inspection under one exception label, which led to extra
investigation. Any follow-up should distinguish remaining public candidate defects
from probe-program mistakes before selecting a runtime change. This record does
not authorize another run, saved-patch execution or evaluator replay.

## Evidence identities

- Manifest: `sha256:86b26c3babfb195eccfc518da443f391f484be2b5ebbbd32a813321c9f8609cc`.
- Settled summary: `sha256:b3c112c677ef3b11961f15d0d1b4d6b218b49d217dd8e32ff163aee70347be8f`.
- Batch completion: `sha256:2c16a0da02f6e14b8a4ca1d42561cd7d65f82e345cd2c4dbd126961001a02c9d`.
- Public-flow report: `sha256:d1f311992696fbf9bf70cc7a27b7703b8bf1f6d6bf83d3be06087749da6dc331`.
- Request-delivery report: `sha256:522d9b49d1ce85b1c83a440280a68f2b9dc3f7d84229c6f74b6202301137cc58`.
- Final run event: `sha256:21b0dec735fa2da21e445b50b2c58513b8132c69ed7ad90cfd059054d1653238`.

All generated evidence is external in append-only dev-run-v1 journals and
content-addressed artifacts. Operator audits added zero provider calls or target
executions and read no private evaluator body, hidden test, reference patch or
provider reasoning.

Documentation validation: 6 tests pass; 81 HTML links and 51 unique IDs resolve;
scripts, historical record bytes and runtime remain unchanged. Current status is
11,633 bytes. Result artifact:
`sha256:05866f1c598a7c1f9f761ccaf066739de2ce33e83e9995b171e1847622d2db13`.
No runtime source changed in this experiment/reporting turn.
