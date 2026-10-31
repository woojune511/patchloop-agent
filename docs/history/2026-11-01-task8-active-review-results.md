# Task 8: active post-mutation diagnostic result

Status: CLOSED, 2026-11-01. One explicitly approved attempt, no retry, resume or
extra sample. `official=false`, claim-ineligible. The [preparation record](2026-11-01-task8-active-review-preparation.md)
and previous [input171 result](2026-10-31-execution-linked-task8-diagnostic-results.md)
remain unchanged.

## Question and fixed conditions

The earlier diagnostic used a finish-point review without active `behavior_change`.
The user requested a
small follow-up at the actual post-mutation `behavior_change` trigger to observe
whether the model constructs and executes a new unverified public case. This is a
correction to the diagnostic's state, not a new production prompt intervention.

Use task `dev-train/current-dev20/8` (pydicom1413), saved public input **138** from
`run_dev_3be40073fc4640bd`, with candidate
`sha256:be082f2721c12b34c2e8032d185297fb2e09379e45a46f5ce7fff1bd642862b9` fixed.
Code **f3d2f8d79c4e7762f63fa97df258376f92f45267**, runtime
`sha256:0963cb074795d1809310160f02dd3c2bc42efe892af302846c3a6454bf598e75`.
Model `gpt-5.4-2026-03-05`, xhigh; credential file
`C:/Users/geonj/Documents/PatchLoop/.env`, with no secret recorded.

The user approved **one new USD2 invocation-wide allocation**, four model calls,
12 actions including report, two probes and 600 seconds total; 40,000 input-token
admission ceiling per call and 25,000 maximum output tokens. Allowed tools were
registered reads/searches, public inline probes and a diagnostic report. No patch
mutation, normal finish or independent evaluation was allowed. Exact predispatch
counting, zero SDK retries and stop on uncertainty remained in effect.

The actual saved gate is `needs_visible_checks`; the current review has
`context_handoff`, `mutation_result` and the admitted mutation identity. The first
actual request delivered that trigger with current guidance in both current-plan
representations. From the second request onward, both correctly showed it consumed.
The packet imported 38 allowlisted public records, ending 134 before boundary 138.
Later check/probe results, the input171 diagnostic and private outcomes were excluded.
Historical actions were not counted as new executions or rebilled.

The diagnostic also used neutral reporting text, current scope-reference guidance
and restricted tools/budgets. Checkpoint and framing changed together, so a different
action is not a causal estimate of either intervention. This was not an exact normal
resume, fresh solve or repair trial. A new case had to be materially different from
the already supplied helper and actually run; a plan or needed post-edit replay
alone was insufficient.

## Outcome and public trajectory

Run `run_dev_20a92fefac33413d` ended with **`INPUT_LIMIT_EXCEEDED`** after
**250.368 seconds**. It made **three model calls**, **two `read_file` actions and
one `search_files` action**. There was no probe, report, mutation or evaluation.
Task acceptance is `NOT_ASSESSED`; independent evaluation is `NOT_RUN`.

The first response replaced the old edit-oriented plan with a plan to inspect the
affected family and run a grouped probe. Its accepted scope review has one
`source_inferred` row and **two `untested` rows**: an OL array helper, and sibling
VR members with a bytes control. It remains `coverage_status=not_certified`.
This shows active-review uptake and planned verification, not executable case
construction. No concrete new values/type/tag/setup or assertion program was emitted.

The plan calls raw `array` -> `Dataset.add_new` -> `write_dataset` the reported OL
path. The actual public issue uses `array('H').tostring()` -> bytes ->
`lineSeq.add_new` -> `ds.save_as`. The plan still substitutes the earlier helper's
construction; no execution establishes equivalence to the original caller or input.

| Action | Public result | Overlap with initially retained inline source |
| --- | --- | --- |
| Read `pydicom/filewriter.py:1148–1165` | 18 lines including OB dispatch | 5 lines already inline; 13 outside that selection |
| Read `pydicom/filewriter.py:248–290` | 43 lines including `write_OBvalue` | 15 already inline; 28 outside that selection |
| Search `OW'` in `pydicom/**/*.py` | 20 dictionary windows, truncated; composite VR entries appear | 0 lines overlap with the initial dictionary selection; 45 unique lines |

Neither read is entirely redundant. Fresh diagnostic gateway coverage starts empty,
so its `new_covered_line_count=18/43` also counts the imported inline 5/15 lines. Those
counters cannot measure novelty relative to the saved model packet. The public audit
compares scope, path, file hash and line ranges directly.

The search returned 20 five-line windows: **100 displayed line occurrences, 45 unique
lines, 55 internal duplicates**. The delivered native search-output string was 17,190
characters. This is a concrete source-payload duplication finding, separate from
whether the search question was useful. It produced new public dictionary evidence
but the next generation was never dispatched, so its later use is unobserved.

| Counted request | Input tokens | Action after admission |
| --- | ---: | --- |
|1 |34,320 |First read |
|2 |36,861 |Second read |
|3 |37,880 |Search |
|4 |43,789 |Rejected before model dispatch: above 40,000 |

The final 5,909-token increase contains accumulated tool calls/results and current
state as well as search output; it is not attributed entirely to search. The
diagnostic appends source observations and conversation to an already large saved
packet. It does not exercise normal segmented-runtime context management.

At interruption the allocation still had **USD1.5740385, one model call, nine
actions, two probes and about 349.632 seconds** available. This was an input-admission
stop, not time/cost exhaustion or an observed model decision to abandon the probe.

## Decision and evidence limits

The corrected setup demonstrated active-review use, explicit untested case groups
and continued source inspection. **The declared new-case execution criterion was
not met.** Executable construction, original-input fidelity, probe execution and
contradiction discovery remain unverified. No defect was newly reproduced or repaired.

The observed limiting mechanism is diagnostic context growth. Before another paid
attempt, the relevant local engineering question is how to preserve exact task,
mutation, prior program/result and source facts while avoiding repeated overlapping
source payloads. Coalescing source ranges with the same scope/path/file hash is a
candidate correction to test; reduction sufficient to admit the next request has
not yet been demonstrated. No such runtime/driver change was implemented after this
run, and the consumed diagnostic is not resumed.

Do not infer that the model could not construct a counterexample, would never have
probed next, or needs another generic reasoning reminder. The planned original-case
substitution and ordering of inspections remain separate questions. This single
development-exposed, fixed-state sample cannot establish production repair gains,
held-out generalization or a causal effect of review wording.

## Accounting and integrity

Recorded generation usage:

| Call | Input | Cached input | Output | Recorded USD |
| --- | ---: | ---: | ---: | ---: |
|1 |34,320 |0 |6,195 |0.178725 |
|2 |36,861 |27,008 |9,913 |0.1800795 |
|3 |37,880 |27,008 |2,215 |0.067157 |

Total **USD0.4259615**; cache-neutral generation amount **USD0.5474975**. All three
generation usages and four input counts were recorded; the fourth generation did
not start. Count-endpoint billing and provider invoice reconciliation remain
**UNVERIFIED**. Unused allocation is closed, not additional execution authority.

The 55-event chain ends in the recorded terminal. Exact approval, 14 plan bindings,
11 implementation hashes and runtime identity were verified. The actual retained
candidate diff independently remained be082f27, 1,587 bytes, with no untracked files.
No retry, source mutation, private body/reference-patch inspection or raw provider
reasoning inspection was performed during the operator audit.

Evidence:

- [Sealed plan](C:/pt/active8-review-20261101-v1/plan.json):
  `sha256:56d36ba7f9fa356bc847ee57947c19d1fb5429f44575661d56a15d6fcdc33987`.
- [Approval](C:/pt/active8-review-20261101-v1/approval.json), same exact task/model/
  credential/repeat/cap, fixed input 138 and patch.
- [Result](C:/pt/active8-review-run-20261101-v1/result.json):
  `sha256:d07bf3c5b64dfc679ead7d0f3560e6ce787e56a7653303f10d27d5a1ba37cad0`.
- [Journal](C:/pt/active8-review-run-20261101-v1/runs/run_dev_20a92fefac33413d.jsonl):
  `sha256:0b80901520f3199e9c7e60e1b8dfa83f4e21ba17eb417201983e5a2860efaf9b`;
  terminal event `sha256:02982cf4ea645e7eb6da30a4f714800c5a0092d76d64f0ee1950cf48f57ab489`.
- [Closure audit](C:/pt/active8-review-closure-20261101-v1/audit.json):
  `sha256:476e7af9942ac371e799fec0bf201ecde2b22ea8e9698b7487f02c5e5017492b`.
- [Public behavior/lifecycle/overlap audit](C:/pt/active8-review-closure-20261101-v1/public-audit.json):
  `sha256:ce96d6937fe56413636daf5ca043e35cb70d0bc0289983eb3b1bcd4ffb3db329`.

Preparation's 24 mocked tests, Ruff and offline real-packet audit remain local
mechanism evidence. This follow-up changes documentation only; its documentation
checks and integrity receipt are under the closure directory. Runtime, tasks,
grading, prior closed records and existing submitted patches remain unchanged.
