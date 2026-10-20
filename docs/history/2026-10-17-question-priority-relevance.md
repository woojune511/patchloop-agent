# Relevance of restored routes and omitted causal-order evidence

Date: 2026-10-17. Baseline: `27f2e568c96b8bea9ef0df677d4f7eaf0b08f229`.
Runtime content: `sha256:eac04bee22dc7bc571a925364a0f851c5c9101f721243478690bfd322ecdde76`.

## Decision

Prioritizing the namespace/location branches remains appropriate for the current
question. The [preceding implementation](2026-10-17-question-evidence-priority.md)
does not, however, establish that all 53 restored lines deserve priority over the
seven omitted builder lines. Only eight directly distinguish the relevant routes;
other import paths account for 31. The seven provide a useful, narrower exclusion
of a possible explanation and generally outrank those other paths for this question.

The larger unresolved omission is the caller bridge at `manager.py:106-116`.
It connects the edited `get_source_file` behavior to source loading, name derivation
and fallback. These lines were already missing before either focus implementation;
they are not a new regression caused by the latest seven-line loss.

Keep mutation protection, current-question scope, the existing two-reference
contract, transition rules and all budgets. This audit supports the direction of
the explicit priority, but not adequacy or optimality of the remaining selection.
It does not justify increasing the budget or adding a task-specific selector.
No runtime, prompt or historical evidence is changed by this analysis.

## Question and available evidence

The historical question was whether `ast_from_file` sends a directory without
`__init__.py` into a file-backed load and which condition should prevent it.
The fixed, operator-authored replay question is: "Does the directory guard reach
the namespace route, and which branch raises the observed file error?"
The two declared references are builder 115-128 and manager 199-211. The historical
model never selected these references or saw their new role contract.

The public issue reports a missing `src/project/__init__.py`; the saved patch adds
a directory guard under `include_no_ext and not orig_ext and exists(base)` in
`get_source_file`. Whether the failing caller supplies the bare directory, and
whether fallback obtains the right module spec, remain material open premises.
There is one saved registered-check PASS before boundary 476 and no `run_probe`
or `run_tests` action. Changed-line feedback is `unknown`, not proof of non-execution
or coverage.

This analysis uses only public source/actions/state preceding boundary 476.
Original journals and artifact hashes are verified, and the current paired input
is reproduced byte for byte. Later actions and evaluator outcomes do not choose
the classifications or the capacity witness.

## Necessity of the 53 restored lines

These are analyst classifications for the current question, not measured utility
scores. They partition all 53 restored line-versions without overlap.

| Group | Lines | Source | Need for the current question |
| --- | ---: | --- | --- |
| Direct routing evidence | 8 | manager 167, 199-202, 206-208 | Highest of this set: spec origin, namespace bypass and missing-location rejection distinguish the proposed fallback from ordinary file loading. They outrank the seven local ordering lines. |
| Conditional execution context | 8 | manager 163-166, 215-218 | Working-directory setup and failed-import hooks qualify context-dependent paths. Secondary without evidence that the relevant context/hook is active; still potentially important. |
| Other import paths | 31 | manager 162, 168-171, 173-190, 192-197, 203-204 | Main-module stub, ZIP, C built-in/extension, compiled and frozen branches. Useful to the broader unresolved normal-import preservation concern, but lower direct relevance to the reported directory/namespace question. |
| Structural fragments | 6 | manager 172, 191, 198, 205; astroid_manager 1; spec 35 | Blank lines or a docstring delimiter. Low independent reasoning value; very little character budget is recovered by removing them. |

The direct eight are route-discriminating source, not an executed counterexample.
The namespace branch can also support the patch's intended mechanism if its
preconditions hold. It does not demonstrate that the reported input reaches it.

Only **10 of the 53** restored lines fall within the explicit countercheck range
(manager 199-208); the other **43** return through ordinary source selection.
There is no policy that semantically ranks all 53 above the seven. After protected
mutation evidence and declared ranges, the selector orders ordinary groups by
existing priority and observation recency, then consumes their consecutive lines.
The editable manager and builder code have the same ordinary priority here.
Manager 167 is still retained through that ordinary path, not explicitly pinned.

## What the omitted seven establish, and what they do not

`builder.py:142-148` occupies 299 standalone source characters. The body derives a
module name only after `open_source_file(path)` at line 121 has returned, and only
when `modname is None`. With the retained open/error lines, it excludes the local
builder name-derivation block as the cause of that earlier open failure.

This is useful exclusion evidence, but it is narrower than "name derivation cannot
be responsible." The already-observed caller at `manager.py:110-114` derives a name
before calling the builder at 124; that call passes its name explicitly. Under
this observed string-path flow, the builder's own `modname is None` fallback is
not the primary name-resolution step. Losing the seven does not erase the whole
causal explanation, and retaining them would not settle the upstream path choice.
The saved note asks about the chooser; it does not explicitly assert that this
post-open builder block caused the failure. Do not label a hypothetical mistake
as an observed wrong hypothesis that the model persisted with.

The missing caller lines 106-116 are more directly needed to connect this patch
to the current question: call `get_source_file`, set `source=True` on success,
catch `NoSourceFile`, derive `modname`, and enter the cache condition. Lines 117-127
are already delivered and show the rest of the cache/source/fallback branches.
Combining them exposes that raising `NoSourceFile` is not a standalone guarantee
of namespace fallback: the incoming `source`, cache, `fallback`, `modname` and
eventual spec still matter. The unchanged source budget does not certify these
preconditions or the actual public issue's call path.

For this question, the defensible ordering is protected mutation evidence, then
the direct route and caller-connection conditions, then the seven local exclusion
lines, followed by conditionally relevant execution context and other import paths.
The latter groups must rise again if their context or preservation subquestion
becomes active. This is a question-specific judgment, not a new universal ranking.

## One frozen capacity witness within 24k

Before measuring, freeze one manual retained-line exchange:

- Remove manager 173-190: 18 C built-in/extension lines, 783 standalone characters.
- Add builder 142-148: the seven exclusion lines, 299 characters.
- Add manager 106-116: the 11 missing caller lines, 372 characters.

| Property | Current paired selection | Manual capacity witness |
| --- | ---: | ---: |
| Retained source characters, including contiguous-line separators | 23,990 | 23,878 |
| Protected mutation lines | 14/14 | 14/14 |
| Direct routing lines | 8/8 | 8/8 |
| Builder exclusion lines | 0/7 | 7/7 |
| Missing caller bridge | 0/11 | 11/11 |
| Existing question references | 2, both complete | Same 2, both complete |

All added line-versions were observed before the boundary. There is no unseen
source, extra reference, new execution or enlarged budget. The result leaves 122
source characters free and demonstrates that character capacity alone does not
force the present omissions.

This witness is a manually edited line inventory, **not** a supported model
declaration, an automatic-selector result or a newly composed model request. It
does not solve how the current two contiguous references and ordinary selection
would choose that evidence. Full request/token admission is `NOT_RUN`.
The newly removed C branch is real context for the original normal-import concern;
its removal is not universally harmless or proof of a better repair trajectory.
No alternative ranges were searched after measuring this one exchange.

## Evidence and validation

Evidence root: `C:/pt/analyses/question-priority-relevance-20261017-v1`.
It contains `audit.py`, `results.json`, classified `linebook.md`, `read-manifest.json`
and append-only `runs/run_dev_relevanceaudit.jsonl`. The journal records the question,
baseline, fixed exchange, unchanged limits, alternatives, stop conditions and hashes.

The audit reproduced the baseline input byte for byte, verified the exact 53 gains
and 48 losses, checked all line classifications, current pre-boundary observations,
the 24k character calculation, both declared ranges and all 14 mutation anchors.
Original files and the runtime content hash remain unchanged. Documentation
layout/link checks passed. Only this follow-up and current-status pointers changed;
runtime tests and mock smoke were not repeated for this documentation-only analysis.
Provider calls, remote token counts and task executions: **zero**.

The decision is to keep the explicit focus principle and record a remaining
question about causal coverage and ordinary selection. The evidence supports a
same-budget capacity gap, not an empirically validated semantic selector, model
uptake, reread reduction, repair improvement or a paid follow-up.
