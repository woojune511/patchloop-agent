# Eight-worker dev20: fourteen evaluations, then a deadline-related shared stop

Date: 2026-11-01. Lane: dev-head, official=false, claim-ineligible. CLOSED.

## Question and execution

The user requested twenty fresh tasks with greater parallelism and handling for
temporary HTTP 429. The [preparation record](2026-11-01-parallel429-preparation.md)
motivates eight workers from the prior panel's large provider-wait share and records
the bounded retry implementation. This run exercises the integrated agent after the
[review lifecycle and delivery fixes](2026-11-01-review-lifecycle-and-delivery-fixes.md).
It is not a one-feature causal comparison.

- Approved execution commit: `c95fdda4cbc1b4935a8f2a14f7603021d1b6d85c`.
- Runtime: `sha256:28154e0bc3c6da43fde86c414a7446864e16818717a14f407cdb462f8c29d211`.
- All dev-train current-dev20 tasks 1-20, one fresh attempt each, eight workers.
- gpt-5.4-2026-03-05/xhigh, 25,000 output tokens; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`, never recorded in solver artifacts.
- New allocation: USD4 per task and USD80 overall, without transfers.
- Per task: 40 logical model calls, 100 actions, 12 accepted edits and 1,800 seconds,
  including the 330-second independent-evaluation reserve.
- Existing segmented-v1, result-or-size-v1, brief-v1, public-checks-v1 and repair
  recheck settings. Fresh pristine source and state; no old patch, helper, response,
  checkpoint, cross-run note, private expectation or operator diagnosis supplied.
- Dispatch order, using only historical elapsed times in operator metadata:
  18, 16, 8, 13, 17, 4, 19, 1, 5, 20, 15, 3, 11, 2, 9, 10, 12, 7, 14, 6.
- `bounded-429-v1`: only confirmed temporary 429 codes may retry, at most two retries
  per logical request and at most 120 seconds of scheduled backoff inside the
  existing deadline. SDK retries remain zero. Other transport, usage, continuation
  or cleanup uncertainty stops new admissions; already admitted requests may settle.

All twenty source/dependency/image identities and public import, operation and
selected-test canaries were checked before dispatch. No Docker startup, image build
or pull occurred. Preparation validation includes 1,573 quick PASS/one host skip,
eight-process rendezvous, retry/peer-stop/recovery controls and isolated mock
evaluation; see the linked preparation record for intermediate test corrections.
Those local controls remain separate from live correctness and recovery evidence.

## Results and accounting

The batch closed after **1,583.372 seconds (26m23s)**, with **19 tasks started and
one not started**. Fourteen submitted candidates received independent evaluation:
**9 PASS, 5 FAIL; 14 safety PASS**. Six tasks have acceptance and safety NOT_RUN.
This duration is an interrupted batch time, not a completed full20 throughput result.

Generation cost has a **known settled lower bound of USD22.435737**. Task18's final
generation has no response/usage receipt, so the actual total and unused allocation
are unknown. Its last conservative reservation was USD0.524015; that reservation is
not billed usage. The allocation and all task allocations are closed. No unused
amount authorizes further calls, and earlier unresolved billing remains unresolved.
Invoice and input-count endpoint billing were not independently reconciled.

| Task | Instance | Prior full20 | Current acceptance | Logical calls / settled | Row seconds | Settled generation USD |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | marshmallow1343 | PASS | PASS | 9 / 9 | 617.898 | 1.0165800 |
| 2 | pvlib1072 | PASS | PASS | 7 / 7 | 452.005 | 0.5866495 |
| 3 | pvlib1154 | PASS | PASS | 8 / 8 | 445.356 | 0.5908915 |
| 4 | pvlib1606 | PASS | PASS | 15 / 15 | 1,106.456 | 1.6683075 |
| 5 | pvlib1707 | PASS | PASS | 6 / 6 | 433.692 | 0.5740140 |
| 6 | pvlib1854 | PASS | NOT_RUN: not started | 0 / 0 | — | 0 |
| 7 | pydicom1139 | FAIL | NOT_RUN: peer stop | 5 / 5 | 125.154 | 0.2365465 |
| 8 | pydicom1413 | FAIL | FAIL | 12 / 12 | 533.459 | 1.0962565 |
| 9 | pydicom1694 | PASS | NOT_RUN: peer stop | 11 / 11 | 384.625 | 0.9088715 |
| 10 | pydicom901 | FAIL | NOT_RUN: peer stop | 5 / 5 | 283.276 | 0.4543120 |
| 11 | astroid1196 | PASS | PASS | 14 / 14 | 562.877 | 1.0764410 |
| 12 | astroid1268 | FAIL | FAIL | 9 / 9 | 326.967 | 0.6864225 |
| 13 | astroid1333 | FAIL | PASS | 25 / 25 | 1,148.051 | 2.9281880 |
| 14 | astroid1866 | PASS | NOT_RUN: peer stop | 4 / 4 | 112.699 | 0.1773190 |
| 15 | pyvista4315 | PASS | PASS | 10 / 10 | 606.096 | 0.9553750 |
| 16 | SQLFluff1517 | FAIL | FAIL | 15 / 15 | 938.270 | 1.6398055 |
| 17 | SQLFluff1625 | FAIL | FAIL | 12 / 12 | 518.930 | 0.9482695 |
| 18 | SQLFluff1733 | PASS | NOT_RUN: response unknown | 27 / 26 | 1,470.289 | 2.9902020 + UNKNOWN |
| 19 | SQLFluff1763 | FAIL | FAIL | 24 / 24 | 1,253.152 | 2.4575635 |
| 20 | SQLFluff2419 | PASS | PASS | 21 / 21 | 820.907 | 1.4437220 |

Row durations overlap and include worker overhead. They are not the same as the
terminal's active elapsed time. Peer-stopped tasks 7/9/10/14 have settled usage but
no terminal candidate verdict; they are not evaluated failures.

The [prior full20](2026-11-01-pre-edit-dev20-results.md) had 12 PASS/8 FAIL in
4,916.317 seconds at two workers. Among the fourteen tasks evaluated in both runs,
the prior result was 8 PASS/6 FAIL and the current result is 9 PASS/5 FAIL: task13
changed to PASS, and no other completed verdict changed. The six missing current
verdicts were four prior PASS and two prior FAIL. They cannot be treated as retained
passes, new failures, or combined with older results into a current full20 score.
Task13 had also passed in the separate [failed-eight rerun](2026-11-01-failed8-rerun-results.md);
this is not its first observed independent success.

## Transport and stop evidence

There were **239 logical generation starts, 238 settled generations, 245 input
counts and 245 completed counts**. Physical transport receipts record **484 attempt
admissions and 483 received responses**. There were **zero observed temporary 429
rejections, zero scheduled retries and zero scheduled retry delay**. The new retry
path therefore has local test coverage but no live recovery demonstration here.
An attempt admission alone is not proof of remote execution.

Task18's last generation was admitted with 55.494 seconds of solver time remaining,
59,606 counted input tokens and a 25,000-output ceiling. It ended with
`RequestWaitExpired` at about 1,470.036 active task seconds, leaving its response and
usage unknown. This is observed local deadline expiry, not an observed 429/500/503
response. The final call is `call_ffc1012bff364a95ad5ed78c0a5da6ff` in
`run_dev_8cae50257e0546bd`. No unreceived repair is credited as produced or applied.

The earliest durable stop-confirmed witness is batch `row_finished`, sequence 44,
at **2026-11-01 14:41:04.490064 UTC**. Across 968 count/generation/physical-attempt
admission records, none occur after that witness and none have an ambiguous equal
timestamp. Fourteen response or settlement records occur later, which is permitted
for requests admitted before the stop. The actual shared-latch set instant was not
journaled: the earlier set-to-witness interval is unverified, and same-host wall
timestamps are not a cross-process total-order receipt.

Closure verified frozen bindings, all recorded row journal chains, prepared public
input/count/dispatch hashes, physical request identities, usage arithmetic and
submitted patch hashes. Missing usage remains unknown; it was not replaced with
zero. No new provider, probe, task or evaluation call was made by these audits.

## Public repair observations

**Task8 retained the original/helper discrepancy but did not pursue it.** The first
serialized-bytes helper used a different tag and `write_dataset` rather than the
reported `save_as`; OL and OB both succeeded. The next helper removed conversion
to bytes, making direct array inputs fail for both OL and OB. The accepted repair
normalizes buffer-protocol values to bytes; its replay and the 213-test public
check pass, but this does not explain the reported OL-only contrast with OB/OF.
Chosen literal quotes omitted that contrast. The final plan and finish assessment
retain the original-path gap and still submit with 29 model calls, 81 actions,
11 edits and about 982 solver seconds displayed as remaining before the decision.
Independent acceptance is FAIL; the private failing assertion was not inspected.

The post-edit review successfully cites the historical base helper and preserves
its interpretation and actual historical diff in later public context. That is
observed uptake of historical comparison. However, no inspected snapshot reaches
`review_recorded` or uses the `recorded_review` fallback because helper identity or
replay advanced. The previously fixed later-unrelated-review reopening scenario
was not exercised. Retained discrepancy is not proof that the model interprets it
correctly or chooses the next discriminating experiment.

**Task13 preserved a distinguishing public setup and repaired a different cause.**
The prior full20 helpers omitted `src/__init__.py`; this run includes it while
keeping `src/project/__init__.py` absent. Stage-by-stage observations connect
relative explicit search paths to `modpath_from_file` failure and the later
nonexistent initializer fallback. The repair normalizes explicit path entries in
`astroid/modutils.py`, rather than changing namespace classification as the old
patch did. The replay and a later actual `pylint.lint.Run` helper preserve this
setup, observe positive module processing without F0010, and retain a regular
package control. Required public checks report 1,232 PASS/69 skip/15 xfail;
independent acceptance is PASS. This supplies a useful repair trajectory, not
feature-level causality, formal original-obligation certification or a speed gain.

**Task18 exposed an unresolved public regression before running out of solver time.**
Five distinct helper programs progressively separate rule behavior and a possible
second-pass/convergence effect; exact-AST screening found no identical program.
There is one `run_check` and no `run_tests` action, so this is not an observed loop
of identical successful checks. An initial test filename was rejected without
mutation; the corrected first edit was accepted at about 1,005.7 seconds. Its public
regression then reports **1 FAIL/507 PASS**, with **9 actual leading spaces versus
8 expected** before `my_id`. Later evidence shifts the plan from the L039 change to
convergence/deduplication and `LintFix` equality. Eleven further reads/searches
occur after the final probe, but no second accepted edit or submission follows.
About 87.7% of active time is generation dispatch-to-result/timeout intervals;
these are wrapper intervals, not isolated model-compute measurements. Large inputs
are observed, but their separate causal contribution to latency is not established.

These focused audits inspect public context artifacts and action/check receipts.
They do not certify every hydrated provider-wire projection or read private failing
assertions, reference patches, provider-response artifacts or continuation artifacts.
The closure audit hashes encrypted request material opaquely for identity and does
not inspect reasoning semantics. Public findings are not private grading attribution.

## Decision and outstanding request

The batch confirms that eight-worker admission and the shared uncertainty stop were
used; it does not establish a completed full20 speedup or live 429 recovery. The
completed subset contains a task13 success and the persistent task8 diagnosis gap.
Task18 demonstrates progress and an unresolved public failure followed by local
deadline expiry, without an evaluated submission. Those findings leave correctness,
time allocation and safe continuation as separate questions.

The user's subsequent request to consider larger time/cost limits and continuing
interrupted work is **under feasibility review, not yet authorized or executed**.
This record prescribes no continuation design and grants no new allocation. The
closed invocation is not resumed, retried or supplemented; existing unknown billing
and every previous closed allocation remain intact.

## Evidence

- Preparation and exact approval: `C:/pt/parallel429-dev20-20261101-v1/`, including
  manifest, preflight, approval, scheduling, requests and public canary receipts.
- Execution: `C:/pt/parallel429-dev20-run-20261101-v1/result.json`, row journals and
  the final operator summary.
- Closure: `C:/pt/parallel429-closure-20261101-v1/audit.json`, hash
  `sha256:609bf900e4ea1de42509118015d6857261d5ac729e1b258385789d6b16df2c6e`,
  bound in the external CAS and append-only closure journal.
- Focused public evidence: `task8-public-audit.json`, `task13-public-audit.json`,
  `task18-public-audit.json` and their referenced public extracts in the closure root.
- The closure helper's seven transport fixtures plus five stop-witness fixtures
  passed; existing prepared-public-input identities were also checked offline.
  Audit execution added no provider or target calls.
