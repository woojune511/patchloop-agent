# Observation A/B follow-up: source premises and a one-edit horizon

Date: 2026-10-27. ARS experiment-agent, public-evidence analysis.
Status: ANALYZED; no additional model, target or evaluator execution.
official=false, claim-ineligible. This supplements the closed
[results](2026-10-27-selection-observation-results.md); their bytes are unchanged.

## Question and evidence

Both models received their assigned observation packet and made an incorrect first
edit. The important question is whether this demonstrates failed reasoning despite
sufficient information, or also reflects gaps in source acquisition and the repair
opportunity. This matters because increasing context or adding another observation
rule would address different mechanisms.

Read-only review used the public action journals under
`C:/pt/selection-observation-live-v2/{A,B}/runs/run_dev_selectionmodel.jsonl`,
the audited public receipts, and the diagnostic operator source. No private
evaluation artifacts, raw provider reasoning, credentials or new executions were
used. The [existing audit](2026-10-27-selection-observation-results.md) establishes
packet delivery, same original caller, settled costs and the candidate outcomes.

## A: an unsupported source premise survived an unsuccessful probe

A's sixth response searched `namespace` in `astroid/modutils.py`. Journal sequence
44 returned overlapping spans 266-270 and 267-271 around `join(modpath)`.
The actual function's initialization at line 263 and incremental append at line
265 were absent. Its earlier full read of this file covered lines 349-520.
The edit's old text matches the five-line search excerpt. Thus A did not inspect
the enclosing function before claiming it tested the full path rather than the
current prefix; saying it saw the full evidence and ignored it would be wrong.

The actual code already builds `modpath` incrementally. A's prefix slice therefore
does not change the relevant nonrepeated path components. The host's bounded
launch-thread traces also did not observe the changed executable lines. These are
separate reasons the patch did not repair the measured caller, not universal
claims about every input or all execution threads.

After six responses and ten inspection actions, two response/action slots remained.
`repair_opportunity` then offered probe, edit and stop, but no further reads. A used
the seventh response for a helper. Its first `modpath_from_file` call omitted the
temporary root from the search path and raised ImportError before the intended
comparison loop. It did not invoke the original Pylint caller. The eighth response
offered only edit/stop: the failed helper consumed the sole probe allowance, and
the protocol-correction allowance did not cover this settled tool execution.

This supports a combined failure: a source hypothesis drawn from an insufficient
excerpt, a probe that did not test that hypothesis successfully, and no remaining
inspection or diagnostic opportunity. The model could stop; it was not forced to
edit. Extra actions might help, but this run does not establish that they would.

## B: relevant source was available, but code contradicted the prediction

B read `astroid/modutils.py` lines 250-430 in response two, including the relevant
path conversion, and received all supplementary observations on every request.
It later requested test lines 1-500, received the explicit 400-line range error,
and successfully read 1-250 on its next response. This was a recovered request
mistake, not missing dependency-source access or an unresolved infrastructure error.

In response seven B chose an edit while a probe and successor edit were still
available. Its prediction was to avoid fabricating an initializer; its code instead
appended `__init__` to directories. Host observations show both the surviving F0010
and the new ordinary-package child omission. Unlike A, changed lines were observed.
The issue here is the untested transformation and its caller consequences, not a
demonstrated lack of context capacity. Delivered observations alone do not prove
that every needed fact was acquired or correctly understood.

## Scope of the experimental structure

`diagnostics/selection_observation.py` explicitly ends the model phase at the first
successful `replace_text`. `diagnostics/exception_frame_repair.py` implements that
stop before any host checks. The host subsequently runs original/public controls,
regression and separate acceptance, but none of these results return to the model.

This was a prespecified first-edit comparison, not an implementation bug. It can
measure first-candidate quality under the two packets. It cannot answer whether
the model would recover after seeing its patch's public failure, or characterize
the full production repair loop. Acceptance details must remain isolated in any
future continuation; only public failure evidence can feed back.

Both candidates reached an edit without input/output/money/time cutoff. Maximum
counted input was 30,354/22,771 against 60K; maximum output per response was
26,138/1,716 against 40K; total cost was $0.3003564 of $2.40. Those facts do not
erase A's response/action shortage. B used only seven responses and nine actions,
so a single common budget-exhaustion explanation is contradicted by B.

## Decision and next unresolved question

The known [operator repair](2026-10-27-relative-root-repair.md) normalizes the
relative search root before comparing it with absolute filenames. Its controlled
results establish a repairable upstream cause. That answer and its counterfactual
were deliberately excluded from the model packet; neither model rediscovered it.

Do not increase context/output as the first response to this pair, or claim mini
cannot solve the task from one sample per arm. Preserve production defaults. The
next focused question is whether a bounded continuation can revise a demonstrably
wrong repair premise using its own public post-edit observations. Such a diagnostic
should preserve access to the enclosing source and a usable diagnostic opportunity,
then permit one further edit followed by the same public controls and separate
acceptance. A continuation would test feedback uptake; it would not be a fresh
solve or isolate the effect of every opportunity change. It is proposed, not run.

The original preflight metadata KeyError occurred before all provider calls and
was already corrected. It is an operator defect separate from these repair failures.
No new paid allocation or production behavior change follows from this analysis.
