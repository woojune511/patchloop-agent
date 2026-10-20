# Counterevidence displaced by focused handoffs

Date: 2026-10-17. Runtime: `fa2dbddbe740a06147f4b6831ad321bac66835bf`.
User requested analysis of the 68 displaced versus 61 newly retained source-line
occurrences, with unchanged budgets and no paid execution. This is a separate
follow-up to the [implementation](2026-10-17-evidence-handoff-implementation.md).
No runtime, selection rule, timing, limit, historical record or original run changed.

## Decision and limits

The trade at boundary 303 is useful: error provenance replaces copyright comments.
At boundary 476, giving the entire old builder citation priority is a poor match
for the unresolved routing question. It removes a distinct namespace route and
missing-location guard while retaining unrelated neighboring builder code.
Preserving a declared citation does not establish that it is the best evidence.

The strongest displaced material is eight lines useful for distinguishing routes,
not an observed execution that falsifies the patch. The namespace branch can support
the proposed fallback mechanism as well as challenge an unconditional file-loading
explanation. No saved target reproduction or branch trace identifies the actual
route taken in the reported failure. These logs do not establish repair causality.

Retain the 24k budget, timing and mutation-anchor precedence. The next design issue
is the scope and continued relevance of declared references, including a competing
route or precondition, rather than globally favoring old source or adding budget.
No replacement selector is adopted here. One case-specific capacity comparison
below is post-hoc analysis, not a model-selected reference or a quality experiment.

## Method and source identities

Evidence root: `C:/pt/analyses/handoff-counterevidence-20261017-v1`.
It contains `audit.py`, `cases.json`, `classification.json`, `linebook.md`,
`paired-evidence-input.json`, `read-manifest.json` and the hash-chained
`runs/run_dev_counterevidence.jsonl`.

1. Recheck the prior replay: only row 13, astroid-1333, boundaries 303 and 476 change.
2. Verify the original journal chain and artifact hashes. Resolve source through
   the actual original post-handoff inputs and the implementation replay inputs.
3. Confirm all 68 losses and 61 gains are actual delivered line-version differences,
   not merely differences in a retained-source list with duplicates elsewhere.
4. Bind every compared line to public observations before its boundary. Compare
   its function with the public issue, note, plan, mutation and registered check.
   Classification is an analyst judgment, not a runtime relevance score.
5. At 476 only, run one fixed two-reference alternative through the unchanged
   selector and input composer. Assert source identity, 24k retention, complete
   focus delivery and preservation of all 14 mutation-protected lines.

The 61 gains are occurrences across two inputs: they represent 58 distinct
line-versions because builder lines 124–126 occur in both. No later decision,
private test, reference patch or evaluator result selects an alternative reference.
No provider/count call, Docker, task-source execution or new check/probe ran.
Exact token counts and full request admission remain `NOT_RUN`.

## What the lost lines could establish

At 303, the three lost lines are `builder.py:9-11`, copyright comments. The five
gains, `builder.py:122-126`, connect an `OSError` to `AstroidBuildingError` and the
reported `Unable to load file` message. This is a good exchange for error ownership,
but the fragment does not show who selected the path or prove a guard is needed.

At 476, 62 of the 65 losses are in `manager.py`. The following eight are the
highest-priority discriminating subset for the saved routing question:

| Displaced source | Observed code role | What it can challenge or qualify |
| --- | --- | --- |
| `manager.py:167` | `found_spec = self.file_from_module_name(modname, context_file)` | The path and module kind have an upstream origin; the builder's error does not identify the chooser. |
| `manager.py:199-202` | `PY_NAMESPACE` returns `_build_namespace_module(modname, submodule_search_locations)` | A namespace route already bypasses ordinary file loading. “Missing init always reaches file_build” is too broad. This also supports the proposed fallback if the correct spec is reached. |
| `manager.py:206-208` | Reject a spec whose location is `None` | Raising `NoSourceFile` is not alone proof of a successful fallback. The eventual spec/type/location and caller controls still matter. |

Line 209, closing that error, and line 211, dispatching to
`ast_from_file(..., fallback=False)`, remain delivered in the current selection.
Removing their preceding branch conditions leaves an incomplete control-flow view.
The namespace helper at 142–146 also remains, but a helper definition does not
replace the missing condition that invokes it.

The other losses are not all useless. `manager.py:163-166,215-221` (11 lines) carry
working-directory and failed-import-hook/exception context. They are secondary
to the main route comparison but could matter for a context-dependent failure.
The remaining 49 of the total 68 losses are lower direct priority for this question:
other import kinds, the start of a zip helper, an isolated `type=module_type` field,
blank/docstring delimiters and copyright comments. Other import paths can still
matter to the original concern about preserving normal imports; this is not a
general instruction to delete them.

The absence of a target execution is decisive for claim scope. Before 476 there
were no `run_probe` results. The only post-edit registered check reported PASS
(1,231 passed, 69 skipped, 15 xfailed), while changed-line execution feedback was
`unknown` due to `unsupported_python_options`. Unknown is not unexecuted. There
is no observed failing target result among the newly displaced material.

## What the gained lines add

At 476 the old selector already delivered `builder.py:119-123`. The 56 additional
lines complete the declared 110–170 range, but they have different roles:

| Newly retained at 476 | Lines | Role for the current question |
| --- | ---: | --- |
| 115–118, 124–128 | 9 | `file_build` expects a source file; the visible failure wraps the failed open. Useful scope and error provenance. |
| 142–148 | 7 | Module-name derivation happens after opening the file. This is useful causal counterevidence to attributing the earlier open failure to this later name derivation. |
| 149–151 | 3 | Successful post-open AST construction; adjacent context. |
| 110–114, 129–141, 152–170 | 37 | Prior method tail, encoding failures, string building and post-build metadata; lower direct relevance to the missing-file route. |

Across both boundaries, the analyst classification is 21 gains for error scope or
causal ordering, three for successful-parse context and 37 of lower direct relevance.
These counts describe the classification, not measured utility. The gain is not
simply “more confirming evidence”: the newly retained ordering at 142–148 is itself
useful for challenging the saved explanation.

## Why the current priority produces this trade

The old note was last updated at event 312 to cite builder 110–170. The agent then
read manager source at 328/341 and made a five-line `modutils.get_source_file`
change at 455/459, followed by the registered PASS at 473. At 476 the note still
asks which branch should be guarded; concern `v1` remains unresolved and the plan
is labelled historical relative to the diff. The builder bytes did not change,
so the source citation remains current despite its old investigative focus.

The implemented order is mutation anchors, explicit focus references, then ordinary
selection. The replay's surrogate promoted this entire 61-line old citation; it
did not choose a fresh question about the new patch. Manager lines 162–208 mostly
come from read 328, while newer fragmented observations keep 209–213 separately.
Recency and atomic focus admission therefore preserve neither a complete competing
route nor a semantic evidence ranking.

This is not a broken source identity check. It is a relevance limitation:
current file bytes do not imply a current question, and complete delivery of one
broad citation does not imply sufficient competing evidence. Historical models
were never exposed to the new reference field, so their behavior with it is unknown.

The public issue names a missing `src/project/__init__.py`, whereas the patch acts
under `include_no_ext and not orig_ext and exists(base)`, adding a directory guard.
Whether the actual caller supplies a bare directory and then reaches namespace
fallback is a material unverified premise. The relevant caller around manager
103–127, including 106–116 already absent in the old post-handoff selection, helps
evaluate it. Those 11 pre-existing omissions are not part of the new 68-line loss
and must not be attributed to this implementation.

## One comparison at the same budget

The alternative declares `builder.py:115-128` and `manager.py:199-211`: the failing
open/error boundary plus the namespace/location dispatch. It uses two existing
reference slots, only already-observed source and the unchanged 24k selector.

| Boundary 476 | Old selector | Current broad focus | Paired diagnostic |
| --- | ---: | ---: | ---: |
| Retained source characters | 23,997 | 24,000 | 23,990 |
| Eight route-discriminating lines delivered | 8/8 | 0/8 | 8/8 |
| Added lines versus old selector | — | 56 | 9 |
| Lost lines versus old selector | — | 65 | 13 |
| Protected mutation lines delivered | 14/14 | 14/14 | 14/14 |

Manager 167 survives ordinary selection in this example; it is not explicitly
pinned by the second reference. The result proves feasibility in this snapshot,
not a general guarantee of eight-line preservation or an optimal reference pair.

The remaining costs are explicit:

- The paired version removes builder 110–114 and 129–170 from the current focus,
  including the useful seven-line post-open name-derivation ordering at 142–148.
- Against the old selector it loses manager 219–229 and spec 60/111. CWD restoration
  at 219–221 is still absent; spec 111 is a newly removed `try:` line. Narrowing one
  reference does not create a universally harmless displacement.
- The old note's 110–170 citation becomes `incomplete`; the two new focus references
  are complete. It would be wrong to keep labelling that old citation fully delivered.
- The composed input grows from 79,015 to 79,530 bytes despite fewer retained source
  characters: the second reference and changed projection metadata also cost space.
  Existing final request/token caps still apply; no remote count was performed.

## Consequence for the next design decision

The 303 exchange supports declared-evidence priority over low-value historical
text. The 476 exchange rejects using complete retention of a broad stale citation
as the adequacy criterion. The budget is sufficient for at least one more balanced
local choice; increasing it or changing transition timing is not justified here.

Keep mutation protection first. Within the existing two focus references, prefer
the smallest observed unit that answers the current question and, when relevant,
a competing route or a condition on the proposed causal explanation. Assess those
declarations against the current mutation and unresolved concern, not just file-hash
currency. Do not promote every namespace branch, assign “counterevidence” from a
keyword, mandate a new review call, or automatically clear all pre-edit evidence.

Mechanical priority still cannot decide these semantics. This audit identifies the
failure mode and a capacity-feasible alternative, but does not implement a semantic
ranker or establish that a prompt/rule change would improve model choices. A further
intervention requires a separate specific design; no paid comparison is scheduled.

Validation: exact whole-input loss/gain sets, original selector reproduction,
two-reference admission, unchanged mutation anchors, current-only source identity,
zero cross-segment reasoning and original-file hashes were checked locally. Only
documentation changed in the repository; documentation layout/link checks passed.
