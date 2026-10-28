# Caller contracts and exploration reservation after the repair follow-up

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-28, Asia/Seoul
- Verification Status: ANALYZED; pinned public source, saved execution and offline arithmetic.
- Version Label: caller_budget_analysis_v1
- Scope: explanation and proposed improvements; no runtime edits or new model/target execution.

## Problem and evidence boundary

The [latest continuation](2026-10-28-diagnosis-exploration-results.md) used
diagnosis and revisions but exhausted three edits without processing file.py.
This matters because repeated callee changes consumed scarce repair attempts
while the original caller's file selection and consumption remained unverified.
The question is what that caller actually requires and whether reservations
prevented the model from obtaining the missing evidence.

Use the same installed pylint2.12.2 bytes as that run, not current upstream code:
`C:/pt/calleruptake18/preparation-v2/B/site-packages/pylint`.
Manifest `685f01a9d10d047d798a164480ab4a16482b13299debd6ef2377b88a43077450`
and content `7f8484e0a2e66aae35864de791ce886d6ff2a2932895f1bfe3c07c4b01e74b9d`
match the saved execution. All inspected caller file hashes match the inventory.
Final candidate/source and exception frames are public. No hidden evaluator,
reference patch, new provider call or target replay was used.

## Caller selection and consumption

1. `pylint/lint/expand_modules.py:62-73`: an existing directory goes through
   modpath_from_file and is assigned directory/__init__.py. file_from_modpath
   is used only in the other module-name/non-existing-path branch74-87.
   Thus edit1 changed the wrong branch; complete trace185 recorded zero entries.
2. ImportError from modpath_from_file changes only modname to the basename.
   It does not request a different traversal and does not remove the synthetic
   init filepath. Edit2's claimed exception-to-traversal effect is contradicted
   by the catch block and trace250's subsequent ast_from_file(init) call.
3. Namespace classification and enumeration happen separately at expand_modules
   90-118. file_info_from_modpath failure sets is_namespace=false; get_module_files
   receives list_all=is_namespace. An init-less directory is skipped when false.
   The latest run observed the missing-init AST input, not the full returned
   descriptor list. The latter remains a source-based explanation supported by
   the separately labelled earlier operator trace, not a new trace in this run.
4. `pylinter.py:1057-1069,1175-1194` sends each selected descriptor to
   MANAGER.ast_from_file(..., source=True), then consumes that AST. Returning
   a namespace object cannot retroactively add file.py to the selection list.
5. Edit3 returns a namespace Module without file or file_bytes. Its stream()
   returns None (`astroid/nodes/scoped_nodes/scoped_nodes.py:541-555`).
   `pylint/utils/utils.py:163-166` unconditionally uses `with node.stream()`.
   This explains the recorded AttributeError('__enter__'). The crash-report
   handler then opens the original missing init path and raises FileNotFoundError
   (`pylinter.py:1032-1045`, `lint/utils.py:18-23`). That escaped error is secondary.

The repair hypotheses changed local return/exception behavior while assuming
the caller would then discover the real file. Neither local exception suppression
nor a successful AST return establishes that contract. The meaningful public
chain is selected real filepath -> usable source AST/stream -> checker processing
-> the same original call's expected diagnostics and normal control.

## Access gap in PatchLoop

The existing DependencySources registry validates exact caller pins, indexed
public Python paths and descriptor hashes. Existing read_file/search_files already
support its catalog; diagnosis and repair contexts retain dependency source bodies.
The diagnostic feedback_source collector constructs this registry, but ordinary
runner.py:5291-5344 loads dependencies only into the probe sandbox and never passes
dependency_sources to DevToolGateway. The normal tools therefore omit source_scope.

This is an integration gap, not a need for a new shell/search tool or all-source
dump. Bounded helper-based inspection was available in early general turns; the
model did not use it. Do not claim that every form of caller access was impossible,
or that adding direct reads alone guarantees repair. In the compact pending
diagnosis stage, run_probe selects a function/call rather than arbitrary helper
source, so ordinary registered reads are particularly relevant.

## Reservation reconstruction and corrected timing interpretation

| Decision | Actual available tools | Binding restriction |
| --- | --- | --- |
|155, before edit1 | replace_text/stop_task | Effective responses10 equal protected horizon10 |
|176, first diagnosis | run_probe/stop_task | Explicit read/search cost rejection |
|214 then229 | read/search/probe/stop | Effective responses7 then6, required read successor reserve5 |
|241, second diagnosis | run_probe/stop_task | Effective responses5 equal successor reserve5 |
|193/258, after diagnosis | edit/test/stop | Reads absent; do not assume arbitrary further investigation remained offered |

Effective response counts exclude the still-unused run-wide protocol correction.
The second diagnosis reserve5 consists of current completion minimum4 plus one
diagnostic-request correction. Money remained at241, but another read would consume
this protected route. The first mutation restriction155 is also a response-count
restriction, not the cost rejection seen at176.

This limits the earlier description of model-selected observation timing:
the model did choose two preparation actions, but at the actual observations176
and241 no further read was offered. The previous closed record remains unchanged;
this follow-up supplies the more precise interpretation.

At176, remaining money was USD3.74106870. At the registered uncached prices,
a future60K-input/8192-output response reserves USD0.27288; a40K-output repair
reserves USD0.75; the25K protocol correction reserves USD0.525.

- Probe's future reserve: two40K repairs + four8192 roles + correction = USD3.11652.
- Read preserves pending diagnosis and its request correction: two more8192 slots,
  making future reserve USD3.66228. Current read USD0.27288 makes USD3.93516,
  exceeding remaining money by USD0.19409130.
- Actual probe input15695 and that future reserve leave a39020 output ceiling.
  It is normal exact-count admission, not lost tokens or transport failure.
- Counterfactual read without speculative *next* failure recovery: one40K repair
  + four8192 roles + protocol correction = USD2.36652 future; plus current read
  gives USD2.63940. It fits with USD1.10166870 headroom. Physical read floor at176
  already fits; no response-floor change is needed for this particular decision.

If both that read and the unchanged probe remain offered, dispatch still reserves
the largest offered successor, USD3.11652. This counterfactual opens a read choice;
it does not make every provider request use the smaller reserve or establish a
successful repair. At155 a monetary-only fallback would not fix the earlier
physical restriction. At241 speculative recovery was already absent, so the
same fallback cannot safely create another read.

No simple duplicate debit was established. Physical completion_budget and monetary
recovery_resources describe future failures differently: physical forecasts can
protect sequential check/original failures plus mutation retry, while monetary
routes use one protect_failure flag. Conversely, a future mandatory path diagnosis
is not an explicit monetary successor. This is a consistency/design problem to
test by named paths, not justification to delete an arbitrary reservation.

## Recommended changes and short local validation

1. Connect the existing registered caller-source reader to ordinary runs. Bind
   approved package-to-source roots to the prepared identity and resume envelope;
   do not infer import roots merely from distribution names. Expose the catalog
   and traceback/function source locators through existing reads/searches. Keep
   dependency source read-only and separate from repository mutation anchors.
2. Model completion as explicit feasible paths, with roles/actions for current
   diagnosis, repair, original replay, checks, finish and each kind of correction.
   Derive response/tool/money/time forecasts from the same paths. Distinguish
   required current completion from a speculative later failure/revision instead
   of adding unrelated worst cases or silently treating them as interchangeable.
3. For an already observed original failure, allow a bounded read to exchange
   speculative later-revision protection for understanding the current failure,
   as required repair/check actions already can. Preserve current completion and
   original verification. Expose exactly which recovery guarantee was released.
   Keep the invocation cap and actual pre-dispatch count/settlement unchanged.
4. Give the model usable source and optional observations of caller selection
   and consumption, rather than adding another mandatory task-specific diagnosis
   prompt. Test whether real file.py selection/consumption changes before claiming
   success; keep same-call absence of fatal/unexpected error plus processing witness.

Small local controls should cover: ordinary-run catalog/read/recovery identity;
dependency read cannot authorize a mutation; actual model input retains caller
body; saved176 read offered only under the explicit protection tradeoff; saved155
physical and monetary paths agree; saved241 still closes when the preserved path
cannot fit; changed original failure cannot become PASS from an empty capture.
Use synthetic caller fixtures or saved public receipts, no hidden expected patch.
Then a new authorized live comparison can test uptake/repair; none is started here.

The leading explanation would weaken if ordinary inputs already contained the
caller catch/consumption bodies, or the exact protected path proved unavoidable
for all permitted choices. Current source and receipts contradict the first;
offline176 arithmetic supplies a feasible weaker-guarantee alternative for the
second. Neither establishes that the model would choose or use the new read well.

## Validation scope and evidence

ARS fallacy coverage11/11 reviewed: Simpson/ecological/Berkson/collider/base-rate/
regression-to-mean/survivorship/reverse-causality are not estimable from this single
mechanistic case; preserve failed attempts for look-elsewhere and forking-path
risks; do not infer a causal solve-rate gain from cumulative changes. No p-values,
effect sizes or statistical performance claims are made. Full model outcome
reproducibility was not rerun; source and pure reservation arithmetic were checked.

Evidence root: `C:/pt/caller-budget-analysis-v1`, with caller-analysis.json,
access-analysis.json and budget-analysis.json plus the offline calculation script.
Public raw journal remains `sha256:6212f3ae0faeb60b97c103dd737bcdf8d5b4205ee31165a21b1cb9a10071f9d8`.
All generated analysis is outside the repository with append-only dev-run-v1 receipts.
The proposed runtime changes and live benefit remain UNIMPLEMENTED/UNTESTED.
