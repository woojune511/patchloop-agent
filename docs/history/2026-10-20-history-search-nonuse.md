# Why the ON runs did not use history search

The six ON trajectories do not support the explanation that history search was
unnecessary throughout. B5 contains a concrete missed recovery opportunity for
its own stated source question. Conversely, B6's final decision had the complete
latest probe program and result; recovering that evidence again would not close
its caller-coverage gap. The common unresolved problem was failure to observe the
original Pylint route and distinguish it from a substitute helper test.

This is a follow-up to the closed [OFF/ON results](2026-10-20-history-search-results.md),
not a relabeling of their sealed annotations or another performance experiment.
The previous label "opportunity" included lost probe programs in B2/B5/B6. That
label means recoverable material existed; it does not establish that every missing
program was necessary for the next decision or that search would improve repair.

## Question and evidence boundary

The question matters because zero usage leaves retrieval quality and repair benefit
unmeasured. Before changing ranking, context limits or prompts, distinguish:

1. Information already sufficient for the immediate decision: retrieval adds no
   identified missing fact.
2. Previously acquired information missing from the current input and relevant to
   the model's declared next question: recovery could help. A current source read
   can be an equally valid alternative to history search.
3. A missing observation never acquired in this run: history search cannot create it.
4. Evidence present but interpreted beyond its observed caller/input/outcome:
   retrieval alone does not correct the inference.

These categories apply to individual decisions, not exclusively to whole runs.
No case proves that `search_history` was the only possible useful action.

Read-only reconstruction covered all **159 actually dispatched ON requests** and
their public decisions/results. It reused the saved public exports, reconstructed
the current state, checked exact source line identities and separately checked
complete probe program/stdout/stderr presence. Every reconstructed probe-presence
record matched the prior audit. Missing complete text does not imply that every
fact in it was absent elsewhere. No encrypted reasoning was interpreted.

The analysis also replayed two existing source-search query strings against the
history prefix using the runtime `EvidenceHistory` class. These were operator
diagnostics, not model-selected history searches or simulated repairs. No new
provider count, request admission, model response, probe or evaluation was run.
Network connection entry points were blocked in the diagnostic scripts.

## Availability was not the general blocker

| ON row | Model requests | Search offered | History searches |
| --- | ---: | ---: | ---: |
| B1 | 20 | 20 | 0 |
| B2 | 24 | 24 | 0 |
| B3 | 22 | 22 | 0 |
| B4 | 36 | 36 | 0 |
| B5 | 35 | 33 | 0 |
| B6 | 22 | 22 | 0 |
| Total | 159 | 157 | 0 |

The search instructions appeared in the system message in **159/159** requests
and in the tool description on **157/157 offered** requests. Thus the feature was
not merely enabled in configuration while omitted from the actual prompt. No
public decision named `search_history`; this does not reveal private consideration
or establish that the model failed to notice the tool.

Only B5 requests **482/492** lacked the tool: the completion horizon had closed
inspection. The earlier post-probe requests **441/455/468** still offered search,
with **3/2/1** exploration turns, **10/9/8** total model calls and approximately
**USD 0.328/0.308/0.288** remaining. Final closure cannot explain earlier non-use.
B2 request 257 and B6 request 333 still reported 24 and 18 exploration turns.
These are observed availability/budget facts, not a guarantee that any hypothetical
larger search response would pass the next request's size and cost admission.

## The strongest missed recovery: B5's builder question

1. Decision **318** read `astroid/builder.py:115-160`; the complete original was
   delivered at request **329**. Its `file_build` body opens the supplied path at
   line 121, handles the open error, and only later derives a module name. This is
   directly relevant to whether the builder synthesizes `__init__.py` before opening.
2. By request **468**, **none of the function's lines 115-151** remained in the
   delivered source. The unchanged-file identity matches the earlier read. Only
   preceding lines 113-114 remained nearby.
3. Decision **470** explicitly sought to determine whether the builder treats a
   directory as a package file and where `__init__.py` is synthesized. It chose
   `search_files("def file_build", "astroid/builder.py")`, repeating decision 305's
   query, rather than retrieving the earlier body or reading that known range.
4. The real lookup returned only **lines 113-117**: the definition and start of its
   docstring, without the opening/exception/module-name branches. Request 482 still
   lacked those branches and no longer offered inspection. The last two responses
   were incomplete; B5 never edited or submitted.
5. Using exactly the selected string `def file_build` in offline history search at
   prefix 468 ranked the earlier **115-160 read second**. Its original body was
   complete both in the normal full-first response and the 48,000-character overflow
   rendering. The normal eight-record response was 69,787 canonical JSON characters.

This establishes an avoidable failure to recover the information requested by the
next action. The model selected a location lookup whose result could not answer
its stated behavior question, despite having a known source range and a searchable
original. It does **not** establish that history search was uniquely necessary,
that the next complete model request would fit, or that reading the body would
repair the task. A direct current `read_file` was also a sensible action.

Recovery is query-dependent. At prefix 441, replaying the then-selected
`def file_info_from_modpath` put that same builder read eighth: complete in the
normal 51,466-character response, but metadata-only in the overflow rendering.
The success of the later specific query is not a general guarantee about ranking
or preservation. No live retrieval/displacement measurement is claimed here.

## Lost probe code versus already visible counterevidence

| Row / decision | What was missing or still present | Diagnosis |
| --- | --- | --- |
| B1 / 242 | Builder lines 115-151 were still delivered before the directory-normalization edit. No original caller trace had been acquired. | A necessary missing historical fact was not established. The directory-input explanation remained source inference. |
| B2 / 242, 259, 382 | Request 240 contained the full direct-directory probe. Decision 242 explicitly acknowledged its no-init success and initializer-present directory error. From 257 the program disappeared, but both output/error texts remained through final request 380. | Recovering setup could help assess applicability, but the switch to suite/test sufficiency began while the complete probe was visible. Loss alone does not explain it. |
| B3 / 268, 298 | The model added a namespace-directory fixture test, then treated its suite pass as covering the original failure. It never observed the Pylint route. | Missing caller acquisition and overstatement of helper coverage; no indispensable lost original identified. |
| B4 / 434-465, 518 | It used the failed check's `KeyError`, source searches and fresh reads to revise the PathFinder edit. Later it claimed a direct module-path test covered the original case. | Ordinary inspection successfully supplied evidence for the intermediate repair. History-only necessity is unproved; final caller coverage remained unsupported. |
| B5 / 428-470 | Probe program vanished after request 426; stdout/stderr persisted. Separately, the builder body needed by decision 470 was absent and recoverable. | A concrete missed source-recovery opportunity, plus optional setup recovery. The whole run was not free of useful retrieval opportunities. |
| B6 / 246, 275, 335 | At request 244, the complete post-edit probe showed `AstroidImportError`. Decision 246 recognized it and said the full user-facing behavior was not yet verified. The model then added a test expecting that error. At final request 333 the newest program, stdout and stderr were all complete. | The final gap was accepting a changed helper exception as evidence for the original task. Re-fetching the current probe would add no missing program/result. |

B5's missing probe setup is a useful caution against counting every lost program
as a necessary loss. Its saved program never changed cwd or added the temporary
root/src to `sys.path`. Yet the retained output itself still listed the failed
module lookup's search path, with the temporary roots absent, and distinguished
directory and child-file outcomes. Recovering the program would make the setup
easier to audit; its absence did not erase every clue about why the probe differed.

B2's initializer-present *directory helper* error is counterevidence to that helper
comparison, not proof of a real caller regression. The already completed local
original-caller control passed. B6's extensionless-file control also established a
useful narrow fact; the problem was extending that fact to the unobserved caller.

## Why the model did not recognize a need to retrieve

The public record supports three mechanisms, with different confidence levels.

**Observed: many decisions framed the gap as new source inspection or test work,
not reconstruction of old evidence.** B5 repeatedly requested source locations;
B2 shifted to a fixture and then a cache assertion; B6 shifted from the original
purpose to directory rejection plus an extensionless-file control. The next actions
followed those declared goals. This is stronger evidence than guessing the model
avoided search because of its cost.

**Observed: retained summaries often preserved the outcome but not the full setup.**
B2/B5/B6 could continue with stdout, current diff, authored plans and concerns. A
summary that supports a chosen helper hypothesis can appear sufficient without
establishing applicability to the original caller. At B5 requests 441/455/468,
`open_question.evidence_delivery=complete` referred to the two selected ranges in
manager.py and modutils.py; it did not certify that the missing builder body or
probe setup was present. B2 and B6 also received explicit incomplete-evidence flags
on some notes. Therefore this was neither a universal absence of loss indicators
nor a reliable semantic trigger to search. We cannot infer that a particular flag
caused a decision.

**Plausible but untested: the tool integration makes selection depend on noticing
that summaries are insufficient.** The instruction is conditional on that judgment;
it neither retrieves automatically nor ties the next question to a specific missing
record. The system's opening response-shape list omits `search_history`; a later
system paragraph and the tool schema explicitly permit it. This split enumeration
could be confusing, but the later paragraph explicitly extends the permitted actions;
it is not evidence that search was forbidden or that the model treated it that way.
The runtime accepts singleton inspect searches. Any effect of this wording on
selection is unmeasured in these zero-use logs.

The original task itself was retained unchanged in **159/159** requests, including
`cd root_dir` and `pylint src/project`. Prepared Pylint availability and the warning
that a reduced helper covers only its own entry/setup were in all **157** offered
probe descriptions. Nevertheless, all **seven B probe programs** called helpers
or failed during helper setup; none acquired the original Pylint invocation/trace.
The later saved-patch caller trace was observed only after these runs. Run-local
history search cannot recover evidence never delivered to the solver.

## Decision and limits

Reject both blanket explanations: "there was nothing useful to search" and
"searching the missing logs would have solved the failures." B5 supports a local
information-selection problem. B6, and the earlier fully visible mixed probe in
B2, show that sufficient delivery for recognizing a scope gap can coexist with an
unsupported completion judgment. All six lack direct acquisition of the original
caller route. These mechanisms can coexist within the same trajectory.

Keep the default OFF and the prior result unchanged: retrieval's effect on repair
was not tested by this zero-use panel. The next targeted change, if requested,
should first make the permitted action list consistent and distinguish recovering
an already observed body from locating fresh source. B5 prefix 468 is a concrete
local fixture for that requirement. It should not force search when the body is
already present, as in B6's final probe, or pretend to replace acquisition of the
original caller. Changing top-k, segment rules or the context ceiling is not
supported by this diagnosis. No implementation or new paid panel is authorized by
this report; its results would require a separate comparison to establish benefit.

## Reproduction and validation

- Execution commit: `11cf4553b8ba6b54e9fb8dbb2428d37b1443cfb0`.
  Analysis base: `7b683ed90831faf2ebcff330ed97c99ec0c83ae2`.
- Runtime content hash, unchanged:
  `sha256:6d36884fc7f07f8ecb232e4b85189eca3db8fe8112cb4f72c1ce1daf0b790175`.
- External follow-up: `C:/pt/historysearch-nonuse26/`. `audit.py` and
  `verify-cases.py` produce append-only outputs and the hash-chained
  `runs/run_dev_historysearchnonuse.jsonl`. `request-audit.json` covers every ON
  request; `case-context.json`/`case-sources.json` retain inspected public detail.
- `verified-cases.json` binds the exact runtime-class recovery and real subsequent
  five-line lookup. It supersedes only the preliminary base-class queries in
  `offline-recoveries.json`; the preliminary bytes remain preserved. Use the
  verified file for runtime ranking/rendering claims.
- `audit-receipt.json` binds original export hashes to the frozen public index and
  records unchanged old outputs, annotations, closed report and user `AGENTS.md`.
  Final validation is recorded separately in `final-validation.json`.
- Implemented: diagnostic/report only, no runtime changes. Locally executed:
  saved-log reconstruction and exact candidate checks; documentation tests.
  Additional provider calls, solves, probes and evaluations: **0**. New model uptake,
  counterfactual request admission and repair success: **NOT_RUN**.
- Transition rules, two references, 24k source/60k input and execution/cost budgets
  are unchanged. The prior full-suite four failures remain unresolved; a docs-only
  check does not establish a new full-suite pass.
