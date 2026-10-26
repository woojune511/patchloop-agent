# Separate call coverage from bounded detail

Status: implemented and locally validated. official=false,
claim-ineligible. Parent commit: `3098ae7635c481d56d22473349380c279c3ebd1c`.

## Problem and decision

The [closed analysis](2026-10-26-trace-limit-analysis.md) found two different
collector bottlenecks in the same failed repair. The pre-edit observation spent
200,000 events on unrelated initialization before reaching the selected functions.
The post-edit observation filled 48 detail records with repeated checker loading,
including duplicated focus/watch events. Both became unknown and deprived the
repair loop of useful original-call evidence. Raising either cap alone would
preserve the other bottleneck and the focus-only blind spot.

The intervention separates discovery, coverage and representation. This changes
how bounded evidence is collected and interpreted; it does not repair the saved
Astroid candidate or establish a live-model gain.

## Implemented change

- Global discovery counts calls only. Local tracing runs only for selected frames
  or the trusted changed-line delegate. Call discovery and selected-frame events
  each have a 200,000-event limit; an exhausted coverage counter remains unknown.
- Complete entry, selected-line, return and exception counts are independent of
  detailed values. The 48-record/8,000-byte sample budgets are shared across
  duplicate physical function selections and divided among distinct functions.
  Equivalent bounded projections coalesce; the first and recent distinct samples
  survive. The 24,000-byte report cap can remove details without erasing counters.
- Versioned collection metadata names exhausted counters and the first selected
  target/event/line where available. Host validation checks bounds, alias and
  counter consistency. Missing samples never establish missing events. The next
  premise/repair summary retains sampling and count metadata.
- Fresh focus-only diagnosis covers the entire selected call, so the focus need
  not enclose the modified function. Saved legacy requests retain absent scope and
  input identity. Receipt scope mismatch cannot complete diagnosis. Refuted
  original calls, finite correction/execution allowances and completion reserves
  retain their previous rules. Tool-surface identity advances to v58.

## Local checks

Runtime: `sha256:207d9b9e81ec10b3e013e7028520366d3103c2dea59a289307fba700b5125dda`.
Evidence root: `C:/pt/trace-budget-local-v1`, with append-only hash-chained
`runs/run_dev_tracebudgetlocalv1.jsonl` and CAS receipts. No provider calls or paid
allocation. The frozen-call replays ran no model, repair or evaluator; mock
integration checks remain separate.

- Short repeatable owner selection: `uv run --locked --offline python -u -m pytest
  @tests/trace-budget.txt -o addopts= -q -p no:cacheprovider --basetemp C:/pt/tbl-short`:
  **111 PASS, 8.39 s**. It covers late calls after over 200,000 unselected line
  events, repeated/aliased selections, partial values, genuine coverage gaps,
  malformed reports, source/trace drift, prediction use and scope identity.
- Quick, with four workers/loadfile and no worker restart: **374 PASS, 34.58 s**,
  including the existing isolated mock evaluation path (mock safety NOT_RUN).
  The first quick run had 372 PASS/two stale v57 hash expectations; only the
  current dev-head expectations were updated, leaving frozen-arm values intact.
  The entire quick selection then passed on the unchanged runtime.
- Ruff across `patchloop tests`: PASS. Broader exploratory integration: 194 PASS
  in 172.63 s; this exceeded the two-minute owner target, so it is not the new
  routine selector. An earlier redirected attempt was interrupted without a
  completed result and receives no PASS credit. The short selector replaces it.
- Independent bounded source/report review found and resolved two defects:
  qualified versus bare names for one physical function had to share coverage,
  and inconsistent counter/line/sample reports had to fail host validation. The
  review is code/mechanism evidence, not independent task acceptance.

### Frozen-call operator replays

Before dispatch, `replay.py` declared two executions, no retries, 30 seconds per
probe and a 180-second overall deadline. Both used the same original program,
selected targets, source snapshots and per-condition scope as the saved live
receipts. In particular, the post-edit legacy focus scope stayed unchanged. The
existing prepared dependency/image identity was checked; no image was pulled or
built. Only the collector implementation changed. The run completed both probes
with confirmed cleanup and no output truncation.

| Condition | Previous limit | New complete coverage | Retained detail | Target time |
| --- | --- | --- | --- | --- |
| Pre-edit, selected call | 200,000 mixed trace events | 31,323 call events; 15 selected-frame events | 13 unique records, 2,091 bytes; two repeats coalesced | 14.084 s |
| Post-edit, legacy focus | 48 retained records | 403 call events; 403 selected-frame events | 26 unique records, 3,559 bytes; 377 repeats coalesced | 9.688 s |

Neither new report exhausted a cap or omitted detail. Full captured call records
(arguments, cwd/environment, fixtures, output and exit) matched the original
records exactly. F0010 remained present and absent from the control respectively;
host judgment stayed consistent. The pre-edit observation now shows zero
`AstroidManager.ast_from_module_name` entries and one `AstroidBuilder.file_build`
entry with `/tmp/patchloop-case/src/project/__init__.py`, including FileNotFoundError
and AstroidBuildingError trace events. The saved first premise is therefore
testable instead of being lost to initialization.

Post-edit `check_modpath_has_init` entered and returned 31 times, with 341 watched
line events. Changed lines 270-275 remained unobserved in both the path collector
and the separate changed-line collector. The candidate was preserved, not repaired.
Fresh post-edit whole-call scope is covered by synthetic gateway/recovery controls;
the saved post-edit replay does not claim to exercise that scope change.

Results: `sha256:9bc62f6e9163464e73b656d770eb6733b3333f00211c8ed19686085d735a84b3`.
Closeout: `sha256:f65502f6055b9d96819c1e82408e910043c12a2d12abe2ead13a2e2a78e79557`.
The local scripts and exact requests/results are linked in the external journal.

## Interpretation and remaining question

The local evidence supports replacing mixed-event truncation with separate
coverage and coalesced detail. It restores useful original-call observations in
these saved cases without changing their result. It does not show that the model
will interpret them correctly, choose a different repair, resolve F0010 or pass
independent task evaluation. The next live question is whether this evidence
changes the repair hypothesis before another mutation; it needs a separately
authorized model run. Full regression and Linux CI were NOT_RUN.

The previous frozen invocation differs from the public issue's cwd/relative CLI
steps. The collector preserves saved calls rather than changing that identity;
broader reproduction equivalence is still untested. Returned/raised remain trace
events, not proof of normal return or an escaped exception. Other threads and
processes are unmeasured. No historical artifact is rewritten.
