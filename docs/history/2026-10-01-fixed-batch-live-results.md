# Fixed three-task live batch: no accepted repairs

## Question and frozen scope

Where does the unchanged baseline fail across three tasks selected before outcomes
or environment inspection? The purpose was to obtain comparable failure evidence
before choosing an intervention. Selection, preparation and controls are recorded
in the [protocol](../../.agent/fixed-batch-proposal.md) and
[package admission](2026-10-01-fixed-batch-package-admission.md).

The user approved one fresh run per task, gpt-5.4-2026-03-05 xhigh, the repository
.env credential file, USD 3 per invocation and USD 9 aggregate. Execution used clean
main commit `6a815f606d6f1df2cf9226e1ee393c0ddc9151bc`, after PR 17 passed Linux
and Windows CI. Runtime hash:
`sha256:dfd10fb7c338ce8a3548eacf5210bf3241254e3aaae9efc13aef23b2cf0a44c5`.
Task hashes, source/dependency descriptors and baseline policies stayed fixed.
No agent feedback from private evaluation, retries, replacement tasks, tuning or
extra budget was used. Every run is official=false and claim-ineligible.

## Results

| Task | Bug cases passing (F2P) | Regressions passing (P2P) | Model calls / edits | Active seconds | USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenSandbox 816 | 0/1 | 108/108 | 10 / 1 | 429.520 | 0.595407 |
| pyinfra 1679 | 1/3 | 10/10 | 10 / 2 | 510.560 | 0.905987 |
| isort 2491 | 0/1 | 73/73 | 21 / 2 | 1545.187 | 2.5637795 |

All three selected tasks were executed, submitted and evaluated. Acceptance was
0/3. Each terminal was EVALUATOR_FAIL / PRIVATE_EVALUATION_FAILED. Each submitted
patch passed registered public regression checks, scope and real sandbox safety.
Original hidden test accounting was complete with zero missing cases. These are
completed repair failures, not preparation, infrastructure or timeout outcomes.

Recorded spend totals **USD 4.0651735**; all provider dispatch/completion and input
count start/completion events are paired. Counts are 41 model calls and 44 input
counts across the batch. Isort's long response eventually completed and usage
settled; no uncertain call was retried. All individual caps were respected.
The allocation is CLOSED; unused USD 4.9348265 is not further authorization.

## Evidence and preservation

External root: `C:\pt\runs\fixed-batch-20261001-v1`.
Top-level `summary.json` binds compact outcomes;
`runs/run_dev_fixedbatchlive.jsonl` records approval, invocation receipts, accounting
reviews and closure. Each task subdirectory retains append-only hash-chained run
events, immutable envelope, submitted manifest/patch, public tool/probe receipts,
private evaluator results and terminal provenance.

| Task | Run ID | Submitted patch SHA256 |
| --- | --- | --- |
| OpenSandbox | run_dev_75ec90f0be654c84 | 5295695164a555a65c6373515dfdf9ecf3c1deadafebc617044fe9ba00896493 |
| pyinfra | run_dev_710588e1c1a94d4f | b34362d8686ee9a0798e40e55eed651ce8fdc60080f9bece13dd6f8fa129c3ed |
| isort | run_dev_49397fa9568d4b80 | 6edb32a68f8fea1002de9fa6836b1e583de021a53c176b94653dc894567e2940 |

An operator launcher logging error occurred before any CLI subprocess or model
dispatch: a dependency identity object was not JSON serializable. The original
driver remains `C:\pt\fixed_batch_live_20261001.py`; corrected driver is
`C:\pt\fixed_batch_live_20261001_v2.py`. The correction and both hashes are journaled.
This was not a paid retry or change to agent runtime. Existing preparation,
calibration and earlier failed public-check evidence remain unchanged.

## Decision and next question

Preserve the baseline. Public regression success did not establish target bug
correctness in any of these three runs. This recurrence makes repair/verification
coverage worth diagnosing, but does not identify a shared causal mechanism or
justify another prompt/memory experiment. The sample is development-exposed and
too small to support general accuracy claims.

Start the next provider-free diagnosis with OpenSandbox: one edit, a narrow path
validation requirement and a security-relevant public issue make the submitted
patch comparatively easy to inspect. Compare the public requirement, inspected
source, submitted patch and public probe/check evidence; construct the smallest
public-input reproduction that distinguishes an incomplete repair from a test or
environment assumption. A public reproduction that passes would weaken the
incomplete-repair explanation and require checking the evaluator contract. Do not
feed private failing cases back into a solving agent. No further run or diagnosis
was executed as part of this closeout.
