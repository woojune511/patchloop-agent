# Completion advice comparison

## Problem and hypothesis

The [scope audit](2026-09-26-verification-scope-audit.md) found narrowing in initial
verification plans, before a final submission recommendation could explain it.
The [diagnostic](2026-09-26-completion-status-diagnostic.md) therefore removes the
check/submit recommendation and its imperative message from the first input while
keeping status facts, ordinary prompts, tools and admission rules fixed.

## Execution

The newly authorized group ran HA, HB, PB, PA once each, using
`gpt-5.4-2026-03-05`, xhigh, common runtime `4d2fc8ba` / surface v45 and diagnostic
implementation `0d35e21`. A kept ordinary advice; B used `status-only-v1`.
H was `hf-hub-xet-endpoint-propagation-v5` with its saved R1 port-only candidate;
P was `pydantic-ai-synthetic-tool-reasoning` with its saved P1 candidate.
Prepared sources, exact-base excerpts and seeds matched within each pair.
There were no inherited plans, notes, check results or operator/private feedback.

Each run had a $1.20 cap, repeat=1; the group cap was $4.80 with no transfers.
The chosen baseline settings and limits stayed fixed. The group used existing
Docker/images and fresh workspaces; every result is `official=false`.

## Results

| Arm | Acceptance PASS / planned | Started / submitted | NOT_RUN | New reads / edits | Recorded USD |
| --- | --- | --- | ---: | --- | ---: |
| A | 0/2 | 2/2 | 0 | 0/0 | 0.235153 |
| B | 0/2 | 2/2 | 0 | 2/0 | 0.364497 |

All four terminal results were `EVALUATOR_FAIL` with safety PASS. Each run passed
both public checks and submitted its seed unchanged. No cost/input/output/segment
limit or infrastructure uncertainty ended a run. Total recorded cost was $0.599650;
cache-neutral equivalent was $0.881890. The remaining $4.200350 is closed. No retry,
resume, extra sample or post-submission candidate execution occurred.

H-A, H-B and P-A selected check, check, then finish. P-B first read the edited
serializer and DeepSeek profile in one model response. It correctly described the
candidate's field-mode/nonempty-field guard and the provider's settings, recorded
a source-linked note, and selected the same two checks. That note remained in
actual inputs through submission. No alternative-profile observation or repair
followed. The public requirement's provider applicability was still not separated
from the candidate's broader field-mode predicate.

This is a different investigation sequence in one sample, with no acceptance gain.
The public decisions show confirmation of existing candidate logic rather than
loss of the obtained source fact. Public source/check evidence supports that
description; hidden evaluator details were not read to explain failure.

## Validation and limits

All 13 actual model inputs passed public delivery, count/dispatch, usage and
continuation audits. B's projection appeared on all seven B inputs, and A retained
ordinary advice on all six. Normalized initial inputs matched within task; prompts
and generated schemas remained ordinary. Read/search/probe tools were offered in
all inputs. Every output ceiling stayed 25,000; maximum actual output was 937 and
maximum counted input was 29,135. Each run used two segments with the ordinary
`initial` / `major_result_reviewed` reasons.

The new collector's network-prohibited tests passed 24 cases in 1.15 seconds;
Ruff passed. The previous implementation mock/regression validation was reused.
The packet retains the initial fixture-only test failure and corrected final XML.
The closure verifies protected previous bytes and all five execution locks, and
seals public records without including evaluator directories.

Detailed protocol, prices, per-run traces, metrics, documentation validation and
closure: `C:\pt\analyses\completion-status-compare-20260926-v1\result.md`.
Raw run root: `C:\pt\cmpstatus0926a`.

## Decision and unresolved question

The two advice fields alone were insufficient to improve these saved candidates.
One sample per task/arm cannot establish a general effect or reliably attribute
P-B's extra reading. Other completion cues, seeded framing and sampling variation
remain possible influences; this result does not establish a model ability ceiling.
Keep the baseline unchanged and leave the option diagnostic-only.

The remaining improvement target is choosing evidence that distinguishes the
requirement's applicability from the current candidate predicate, then using that
evidence to change a repair. Reading more code and retaining an accurate note did
not accomplish that in P-B. This result adds no new prompt, tool, gate or paid group.
