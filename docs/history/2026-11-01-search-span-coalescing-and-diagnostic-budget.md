# Search overlap removal and bounded diagnostic budget

Date: 2026-11-01. Status: local implementation and preparation; paid execution NOT_RUN.
Baseline commit: `79592cab8df3984d7ed91a6ada7f0c37e3ba4b3a`.
Runtime: `sha256:4fdcc4fb9eb3d71ad81a5d929a0af689cecd876fbd39c212204d0c6343b608c7`.

## Problem and decision

The [closed active-review diagnostic](2026-11-01-task8-active-review-results.md)
reached 43,789 input tokens after three calls, exceeding its 40,000-token limit.
It had USD1.5740385, approximately 350 seconds and both probes left. The model had
named untested case groups but had not emitted or executed a probe program. This
stop confounds any conclusion about whether it could continue to a discriminating
case. Its last search repeated 55 of 100 displayed line occurrences. The first
two reads also acquired new lines, so removing all additional inspection would
discard evidence rather than merely eliminate duplication.

Choose two bounded interventions together: remove overlap in newly produced
search results, and give the saved-state diagnostic 60,000 input tokens and six
model calls. This is an engineering preparation, not a one-factor causal study.
No new reasoning reminder, mandatory probe, semantic coverage gate or model is
introduced. Normal solve limits remain unchanged.

An alternative explanation remains that inspection or report selection will
continue without an executable probe even with room to proceed. If that happens
while budget remains, the admission limit no longer explains that decision.
Repeated calls, misleading input/caller substitutions, or a fresh input/cost/time
stop would require their own evidence; none establishes a general capability limit.

## Implemented change

`DevToolGateway` coalesces overlapping search spans after the existing selection
of at most 20 match windows and 24,000 source characters. Selection, match order,
searched-file counts and truncation keep their original meaning. Freed space
does not cause additional matches to be selected. Contiguous same-source groups
are sorted by start line because a clipped window can start after a later full
window. Only overlapping ranges merge; adjacency and unobserved gaps stay separate.

The union of exact source lines is preserved, including empty lines. Identity
includes scope, path, file hash, dependency provenance and read-only authority.
Merged spans receive the existing canonical span identity before normal evidence
decoration, caching and journaling. Both repository and registered dependency
searches use the same implementation. Existing journal/replay output is not
rewritten. No alternative diagnostic-only source format or new tool is added.

The tool semantic contract adds `same-source-overlap-after-bounded-selection-v1`.
The general tool-surface hashes change intentionally for planning OFF and ON;
the planning contract and prompt instructions are unchanged. Updated hash
expectations record that source-output change, not a new reasoning policy.

The new external driver is `C:/pt/active8-review-20261101-v2/`; the consumed v1
driver, checkpoint, approval and result remain unchanged. Its single live
remaining-budget snapshot now feeds both developer state and the appended budget
message, avoiding stale initial allocations beside current balances. Immutable
saved public archives and the source checkpoint are retained separately.

## Prepared scope and admission semantics

| Setting | Prior diagnostic | New diagnostic preparation |
| --- | --- | --- |
| Saved public state | Task 8 input138, active behavior_change | Same |
| Fixed candidate | be082f27 | Same |
| Model / reasoning | gpt-5.4-2026-03-05 / xhigh | Same |
| Input ceiling | 40,000 | 60,000 |
| Model calls | 4 | 6 |
| Invocation cost | USD2 | USD2 |
| Wall time / actions / probes | 600 seconds / 12 / 2 | Same |
| Output reservation | 25,000, full reservation or stop | Same |
| Mutation / independent evaluation | Disabled | Disabled |

The credential file is `C:/Users/geonj/Documents/PatchLoop/.env`; its contents
were not read for this preparation. One fresh attempt would use the absent root
`C:/pt/active8-review-run-20261101-v2/`. No new approval, dispatch or result exists.
Count, transport, billing or recovery uncertainty still stops new calls without
retry. Prior approvals and leftover balances do not authorize a new attempt.

At the pinned pricing, a 60,000-input/25,000-output reservation is USD0.525.
Six such maximal calls would cost USD3.15, so USD2 does **not** promise six full
calls. The diagnostic reserves the complete 25,000-output ceiling or stops;
it does not shrink the output cap to spend the remaining balance. Actual usage
can be lower than the reservation, but neither six calls nor a completed report
is guaranteed. No price refresh or provider count call was made in this change.

## Local evidence

Offline audit of closed run `run_dev_20a92fefac33413d`, public action sequence46:

| Measure | Original selected spans | Coalesced spans |
| --- | ---: | ---: |
| Spans | 20 | 5 |
| Displayed line occurrences | 100 | 45 |
| Unique lines | 45 | 45 |
| Source body characters | 11,209 | 4,694 |
| Canonical pre-decoration span-list JSON characters | 15,506 | 5,828 |
| Query-matching lines | 20 | 20 |

Exact line identity/content equality and the unchanged closed journal were
asserted. These are selected-span measurements, not a reconstructed full request,
a new token count, or a live behavioral result. Character reduction cannot be
converted directly into token savings or an assurance that later requests fit.
Receipt: `C:/pt/context-budget-local-20261101-v1/search-audit.json`.

Focused source/contract tests: **22 PASS in 9.244 seconds**. External v2 driver:
**28 mocked tests PASS in 109.12 seconds**, including a six-call inspection ->
probe -> result interpretation -> report path, 60k admission, cost exhaustion and
no seventh call. Ruff passed for repository and external driver sources.
The frozen request hash is
`sha256:a1dea8fac1c90dd7631c8473feef27572a41d72bd1a0a87f390acc41c667ade6`;
checkpoint hash `sha256:91672c7d253a0d8281af8a976321e97d1a1b52bed00e5320c014624711ff3bd8`
is unchanged. Driver receipt: `C:/pt/active8-review-20261101-v2/local-validation.json`
(`sha256:17ca6eb9035f4774e5420793b54fe011f694fcb32e952d7f2092dd8f1c564539`).

An initial owner sweep selected 158 cases and found 12 failures: seven new test
assertions incorrectly compared observation-recency metadata with canonical source
payloads; five existing planning cases assumed the full planning prompt at every
stage or assigned annotations to a mutation whose optional decision is now absent.
A follow-up also corrected the new test's mistaken assumption that dependency
reads use the repository's same-diff cache. Same-action replay remains exact for
both; a new dependency action still revalidates its pinned source.

Disabling the coalescer reproduced both representative old-test failures, with
only one input span, establishing that overlap removal did not cause them. The
planning tests now check actual repair/completion stages and annotate only actions
that carry a decision. They still require isolated `EVALUATOR_PASS`, exact dispatch
counts, one mutation, no protocol correction and unchanged resumed journals.
All **five corrected cases PASS in 86.155 seconds**. Baseline failures and the
successful rerun are retained in `C:/pt/context-budget-local-20261101-v1/`.
These are test-fixture/expectation fixes; no additional runtime rule was introduced.

Final quick: **1,435 PASS / one host-symlink SKIP in 445.102 seconds**, four workers,
no worker restart. The suite includes two isolated mock evaluation paths; no
separate smoke rerun was needed. Documentation checks also passed. Final source,
receipt bindings, XML, failure/fix evidence and Ruff are retained in immutable
artifacts and a `dev-run-v1` journal under
`C:/pt/context-budget-local-20261101-v1/validation-final.json`.

## Remaining question and boundaries

No additional production mechanism is justified before observing this bounded
configuration. The next diagnostic question is whether the active review proceeds
from public untested cases to an executable discriminating probe and its result.
That diagnostic cannot establish repair because it cannot edit the fixed patch.
The original bytes/caller construction must still be distinguished from the
model's raw-array helper; no task-specific answer or private criterion was added.

Overlap between separate reads and earlier inline context remains. Fresh-session
source-gain counters do not subtract the saved packet's imported inline spans,
so they must not be read as novelty relative to the checkpoint. Importing old
gateway authority/state or replacing earlier source with references would be a
larger change; the present fix leaves those semantics alone.

No provider count/model request, live target execution or private evaluation was
added. No Docker startup, image pull/build, hidden/reference material or historical
artifact mutation occurred. Local mocks show delivery and bounds, not autonomous
counterexample construction, correctness improvement or generalization.
