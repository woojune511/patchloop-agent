# Search overhead fix and two-task supplement

Date: 2026-10-06. Allocation CLOSED; official=false and claim-ineligible.
This fresh supplement preserves the original panel and its two NOT_RUN outcomes.

## Problem and decision

The [corrected dev20 run](2026-10-06-corrected-dev20-results.md) stopped when
SQLFluff-1733 reached its solver deadline during search with unconfirmed Git
descendant cleanup. SQLFluff-2419 was interrupted by the shared stop. Neither had
an edit or submission to grade. The user authorized fixing search overhead and
freshly solving and grading only these two tasks, not repeating the whole panel.

Search launched a Git tracked-file check for every matching file. Prior SQLFluff
search intervals consumed hundreds of seconds; row 18's completed and unfinished
intervals occupied about 47.3% of its solver budget. This was a concrete execution
bottleneck, separate from repair correctness. Small files and fast enumeration
weakened a large-file explanation. A same-output, provider-free comparison tested
whether one enumeration removed the overhead without changing public behavior.

`patchloop/dev/tools.py` now obtains a fresh NUL-delimited tracked-path set once per
uncached search. It keeps the ordered workspace walk, current file reads, public
path and symlink exclusions, UTF-8 handling, size/span limits and deadline checks.
There is no persistent index cache. Git uncertainty still propagates and stops the
batch; this change does not weaken cleanup or cancellation requirements.

## Local evidence and validation

A 128-file synthetic repository used the same absent and late-match queries with
the old method extracted from 2f419d5ee6ec38a02d767448ec71a472ae6eec96. Both complete
outputs and hashes matched exactly:

| Query | Old Git calls | New Git calls | Old seconds | New seconds |
| --- | ---: | ---: | ---: | ---: |
| Absent marker | 128 | 1 | 10.047109 | 0.067195 |
| Late match | 128 | 1 | 9.499338 | 0.067295 |

These are two fixed-order queries on one synthetic workspace, measured while
focused tests ran. The timings describe this host; they are not a whole-agent
speedup or repair-quality estimate. Source and subprocess counts establish the
mechanism. Regressions cover enumeration count, index/content freshness, unusual
filenames, size/symlink boundaries, expired/mid-scan deadlines and uncertain Git.

- Focused validation: 78 passed, one skipped in 34.04 seconds. Windows prevented
  the symlink case from running. Ruff passed. A fresh isolated mock reached
  EVALUATOR_PASS with no provider cost; mock safety remains NOT_RUN.
- Full collected coverage: 4,277 passed and 19 skipped across 4,296 exact nodes.
  This combines the main run and its failed/unexecuted remainder, not one
  uninterrupted passing invocation. The main C-drive run had 4,151 passes,
  17 skips and one documentation-size failure in 45m38s. After a documentation-only
  correction, the remaining 128 nodes produced 126 passes and two skips in 105s.
- Earlier nonpassing artifacts remain: a corrected test-fixture Git removal guard,
  a missing D-drive temp parent, and D-drive Git ownership errors. No global Git
  trust setting was relaxed; validation moved to fresh C-drive temporary paths.
  Documentation checks then passed after current guidance was condensed.

## Frozen live conditions

- Implementation: a28aa364f44901bc06162281ed7e773d26c92667.
- Runtime: sha256:040699254997d7461ec16fc09f6d79e369249b510c34ba6de70ad438fb3f937c.
- Canonical packet: sha256:5f984bcd9e568440de9638b060520fde39f0cceb329032317c280654a87beac8.
- Exact dev-train tasks sqlfluff__sqlfluff-1733 and sqlfluff__sqlfluff-2419,
  original rows 18 and 20; one fresh attempt each, two parallel workers.
- gpt-5.4-mini-2026-03-17, xhigh, 25,000 desired output tokens, repository .env.
- New USD 1.20 per row and USD 2.40 total; no transfer. Each task retained
  40 model calls, 100 actions, four accepted edits and 1,800 total seconds,
  including a 330-second evaluation reserve (1,470 solver seconds).
- Probes, selected tests, additive tests and repair recheck enabled; automatic
  probe replay none. No cross-run memory, held-out tuning, retry or resume.
- Shared stop on count, transport, billing or cleanup uncertainty, unexplained
  grading disagreement or identity drift. No images pulled or built.

Both import, ordinary-operation and selected-test capability canaries passed.
Previous task packages and dependencies were reused read-only with hash checks;
live state was fresh. Source stayed frozen through closure and the read-only
audit. The user's unrelated AGENTS.md edit was preserved.

## Outcomes and observed behavior

Both tasks submitted and completed agreeing registered/native evaluations.
Both failed acceptance and passed safety. There was no new uncertainty stop,
unassessed row or grading disagreement. Total cost was **USD 1.07327790** across
49 settled model calls; parallel wall time was **940.258 seconds (15m40s)**.

| Task | Registered / native | Calls | Accepted edits | USD | Solver seconds | Search count / union seconds |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| SQLFluff-1733 | FAIL / FAIL | 36 | 2 | 0.91865010 | 869.706 | 19 / 3.911713 |
| SQLFluff-2419 | FAIL / FAIL | 13 | 1 | 0.15462780 | 171.180 | 17 / 3.645160 |

All 36 completed search action intervals, including one cached result, were below
0.74 seconds (maxima 0.736422 and 0.638089). Union durations avoid adding overlapping intervals. Query sequences
differed from the original run, so this is observed task latency, not a matched
whole-run causal speedup. The synthetic comparison separately isolates overhead.

SQLFluff-1733 used four probes before editing. Public output reproduced the CTE's
nine-space indentation versus the intended eight spaces. Its first L003 change
introduced a KeyError in existing regressions (3 failed, 503 passed); repair recheck
led to a second edit guarding missing memory. The next check passed all 506 tests.
It then submitted without a post-edit probe, selected test or added regression for
the reproduced task behavior. Thus the repair loop corrected a regression, but
did not directly recheck the original requirement. This observed verification gap
does not establish the exact cause of the acceptance failure.

SQLFluff-2419 added a dynamic L060 diagnostic description and submitted after one
public check passed. It used no probe, selected test or test addition. Both private
evaluations failed. Its prior full-panel result was PASS; this fresh attempt did
not reproduce that success. One attempt does not establish a search-induced quality
regression or the exact semantic cause. No hidden tests or reference patches were
provided to either solver or used to author another candidate.

## Interpretation and closure

Keep the search fix: it preserves tested search semantics and removes measured
per-file Git overhead. The two tasks can now reach submission within the existing
limits under these observed conditions. This supplement provides **no repair
success gain** and no feature-level or general accuracy claim.

The original panel remains 11 PASS / 7 FAIL / 2 NOT_RUN. This separate, later
two-task supplement is 0 PASS / 2 FAIL. Do not rewrite the old NOT_RUN rows or pool
the runs as a uniform 20-task measurement. Verification selection remains the
unresolved agent issue: available tools and passing existing tests did not ensure
the changed task behavior was checked. No mandatory-probe policy or automatic
replay is adopted from these observations. No further paid run, retry, full panel,
held-out/test300 execution or publication is queued.

## Evidence

- Preparation and native grading: C:/pt/s2p06; fresh live state: C:/pt/s2live06.
- Analysis: C:/pt/analyses/search-once-20261006-v1. plan.json, benchmark.json,
  validation.json and retained JUnit/log files bind local evidence.
- supplement.py is the frozen operator recipe. Preparation manifest.json,
  authorization.json, capabilities.json and result.json bind dispatch and closure.
- supplement-audit.json checks frozen source/task/model identity, journal chains,
  single dispatch, fresh runs, exact token-cost arithmetic, settled counts/billing,
  caps, solver admission cutoff, helper protection, bound evaluation completion,
  native artifact hashes, complete controls, verdict agreement and cleanup.
  Its issues list is empty. The auditor made no provider or evaluator calls.
- public-closeout.json retains public search intervals, probes, edits and checks;
  its recipe also makes no provider or evaluator calls. Generated records use
  immutable files and append-only hash-chained dev-run-v1 journals outside Git.
- closeout.json separately binds final documentation validation, file hashes and
  the documentation commit. Final documentation edits do not change the runtime.
