# Clean-original failure analysis: source uptake and observation admission

## Material Passport

- Date: 2026-10-28. Status: ANALYZED from settled public records and source.
- Subject: Astroid-1333, dev-train current-dev20/13, official=false,
  claim_eligible=false; run `run_dev_8fadb1628e0d4415`.
- Analysis checkout: `3b743b31`; runtime and candidate unchanged.
- No new provider, target, public-test or evaluator execution. No private tests,
  reference patch or prior successful repair was used as an answer source.
- The [closed live result](2026-10-28-autonomous-fresh-results.md) remains unchanged.
  This is a separate interpretation, not an extra trial or a revised outcome.

## Question and importance

The clean-start run reproduced F0010, inspected source 31 times, made two edits,
and exhausted its tool horizon without establishing that its selected failing
fixture was processed.
The important distinction is whether the model lacked caller evidence, ignored
repair feedback, chose unnecessary exploration, or faced a restricted action set.
These explanations imply different interventions; more context or another rule
is not automatically the appropriate response.

The audit used journal action results, the public portions of actually dispatched
inputs, current candidate/source and pure completion-policy calculations. Raw model
reasoning and private evaluation material were not inspected. Independent read-only
reviews covered source delivery, candidate semantics and resource admission.

## Caller evidence reached the model

| Evidence | Actual exposure and limit |
| --- | --- |
| `pylint/lint/expand_modules.py` | Request180, result183: all lines1-139, 5328 characters, `truncated=false`. Both actual inputs238 and261 retain the whole caller file. |
| File-selection connection | Caller lines91-100 classify namespace/directory;101-110 add the candidate init path;115-118 call `get_module_files(..., list_all=is_namespace)`. These branches were delivered. |
| `get_module_files` implementation | No dedicated read of the function. Search44 delivered `modutils.py:487-491`, including the skip when `list_all` is false and init is absent. This fragment was present in input238 but absent after context reconstruction in input261. |
| Broad public test read | Request141, result142: `tests/unittest_modutils.py:1-260`, 10140 characters, `truncated=false`; full native result in inputs154/238 and inline range1-260 in261. A shorter source-index coverage label was not a truncated tool response. |
| Inspection totals | 21 searches and10 reads; no exact repeated request. Two searches returned no matches (`Unable to load file`, `namespace=True`). One test search hit its20-span limit; no direct read was truncated. |

The strong missing-caller-source explanation is contradicted for the first edit.
The entire relevant caller branch and a discriminating callee fragment were in its
input. The second input lost that callee fragment, so perfect source preservation
is also not supported. More source access or a larger context window alone would
not resolve the demonstrated gap between received evidence and the repair hypothesis.
The31 actions delivered1186 distinct source lines; repeated identical requests do
not explain their cost. Conversely, `file_info_from_modpath` was searched only to
its definition/docstring, and the implementation was not read. Broad coverage did
not establish the specific classification/enumeration chain.

## Feedback changed the patch locally, not the file-selection hypothesis

The public task's fixture contains `src/project/file.py`, optionally with `import os`,
and no project init. The model selected that nonempty file plus a regular-package
control. The baseline106 reproduced F0010 on the first call and normal lint messages
on the control.

The first edit243-244 changed `astroid/manager.py` to return a namespace module when
asked to load a nonexistent init file. Replay251 removed F0010 but raised
`FileNotFoundError: src/project/__init__.py`. Both target calls had complete captures;
the unexpected exception made the whole comparison incomplete. This was not output
truncation or missing target entry.

The actually dispatched input261 retained that candidate's exception, call captures,
observed values and failed processing witness. The second public repair hypothesis
explicitly acknowledged the exception and replaced the branch with
`string_build("", modname, filepath)`, setting package/path fields. Thus failure
feedback was delivered and used; it was not simply ignored.

The unsupported step was the prediction that the empty module would still let the
caller discover and lint submodules. Pylint builds its file list earlier in
`expand_modules.py:91-118`. In the unchanged Astroid `modutils.py:489-491`, a directory
without init is skipped if `list_all=False`. The final manager edit changes how an
already selected item becomes an AST; it does not rerun that earlier enumeration.

Replay275 is consistent with this upstream omission: the failing call exited0 with
empty stdout, while the same control still produced C0114/W0611 for `file.py` and
exited20. Both captures were complete. The leading explanation is that the patches
handled the synthetic init without restoring selection of the real file. It is not
a proven runtime branch diagnosis: the run did not record selected files or the
actual `is_namespace`/`list_all` values. A trace showing `file.py` selected and
processed would weaken this explanation and redirect diagnosis to later reporting.

The model's processing witness was also weak: `'project' in stdout + stderr` already
became true on the baseline error path. It does not establish that `file.py` was
processed. This run still failed that predicate after the second edit, so its
weakness did not produce a false PASS here. A same-call diagnostic or processing
event tied to the actual nonempty fixture file would be more discriminating.

## Observation was unavailable after reproduction

After baseline106, actual input114 and later exploratory inputs did not offer
`run_probe`; cost admission rejected it. `observe_original` was not offered either.
Consequently, the later source-only exploration cannot be described as repeatedly
choosing reads over an available execution observation.

At114, the conservative cost estimate for the general probe plus protected future
failure recovery was USD3.866520 against USD3.861695 remaining: a USD0.004825
shortfall. This is a reservation estimate, not an actual provider charge. The
success-minimum route in the same state needed USD2.570760; both time forecasts
fit (895/465 seconds versus about1666 available). Read/search admission can fall
back to that minimum guarantee, while the general probe cannot unless it belongs
to the narrower path-diagnosis state (`runner.py:1495-1503`). Thus the host allowed
exploration to spend future recovery but denied observation under a stronger
guarantee. This asymmetry is more specific than a general lack of money.

The first-observation selector in `patchloop/dev/first_observation.py:129-167`
requires usable diagnostic rules to identify the failing call and confirm unchanged
failure. This case had `diagnostic_rules=null`; the state remained
`status=not_needed, available=false` despite an acquired original failure. The
existing ruleless post-edit diagnosis support did not supply this pre-edit choice.

A separate helper construction failure at71 left no valid call rows. Although it
occurred before target execution, `completion_reproduction._pre_target_attempts`
requires at least one validated pre-target row. It therefore remained an
unestablished case after the corrected baseline106. The projection reported
`early_replay_reusable=false`, and ordinary resources used the legacy forecast.
The corrected request had changed input/environment conditions and no typed
correction link, so the old case cannot simply be treated as the same binding.

Pure reconstruction of policy at114/222/238/261 reproduced their actual offered
tools. Changing only `early_replay_reusable` to true moved ordinary reads/edits to
shared routes but did not reopen the probe or change offered tools/read parallelism
at any of those points. The stale helper case is a real state-model inconsistency,
but blaming it alone for the blocked probe is contradicted by this counterfactual.
Even if the acquired case later passed, the old UNKNOWN would keep overall
verification unverified. Current finish code can return `unverified_delivery` for
this state; it does not necessarily block delivery (`tools.py:4627-4639`). This is
a separate latent verification issue, not the action-limit cause of this stop.

## Tool exhaustion preserved a minimum path, not another failed-repair cycle

| Decision | Remaining capacity and result |
| --- | --- |
| Input222, before last search batch | Seven model slots and nine actions. Three searches were allowed while keeping the minimum completion path. |
| Input238, first edit | Six model slots and six actions. First edit plus original replay consumed two actions. |
| Input261, second edit | Five model slots and four actions. Another edit, replay, required check and finish could fit only if this repair succeeded. |
| Terminal277 | Four model slots and two actions remained, but minimum completion required three model slots and four actions. Only tool actions blocked continuation. |

The three-search batch did not violate the successful minimum path. The problem
was that optional exploration could consume speculative future failure recovery;
the remaining four-action route did not cover a second unsuccessful edit. The
second failure was recorded but never reached another model dispatch. This is
different from first-failure feedback loss.

USD1.549624 of USD4.50 and656.865 active seconds were used. Individual outputs stayed
below40K; maximum dispatched input was59149. One oversized count was reconstructed
before dispatch. Increasing money, time or output ceilings would not remove the
observed action-limit stop by itself. A larger action limit might enable more work,
but this record does not establish that the same local repair direction would
become correct with another attempt.

## Decision and smallest follow-up

Keep original-call and current-diff completion requirements. They correctly kept
this incomplete repair from successful finish. Do not add an unconditional
diagnostic gate or inject the known answer into the solver.

1. Repair the observation opportunity first: allow a bounded selection of an
   already acquired call when diagnostic rules are absent, with explicit call
   identity and unchanged binding. Account for it as observation of an existing
   case rather than conservatively assuming every helper adds a new obligation.
   Preserve model choice between related-source exploration and observation.
   General probes should also be evaluated against an explicitly labeled minimum
   successful path when speculative failure recovery does not fit, as reads are;
   still count any extra case/replay they can actually introduce.
2. Distinguish a host-confirmed construction failure before any target entry from
   an unresolved executed case. Record the attempt and correction link without
   making it a permanent replay obligation. An empty/missing record alone must
   never erase uncertain execution or supply verification credit.
3. Reserve the same bounded observation, edit, original replay, required check and
   finish path across response/action/cost/time admission. Make loss of a later
   revision opportunity explicit before optional inspections spend it. Do not
   reserve every hypothetical future failure or increase all ceilings.
4. Judge the next repair by actual fixture processing as well as error absence.
   For this public case, the discriminating observation is file selection and
   processing of `file.py`, not just successful construction of an empty package.

Before another paid run, use the saved public state for short local controls:
ruleless call selection is available without granting PASS; a proved pre-target
failure remains an attempt; unknown/entered calls remain obligations; each admitted
observation leaves its real completion path. Then a single bounded same-budget
trial could test whether the model uses the option and changes its hypothesis.
No such implementation or trial was performed or authorized by this analysis.

## Scope, interpretation and provenance

There are no p-values, effect estimates or population claims. Statistical fallacy
coverage: **11/11 checked**. Simpson, ecological, Berkson, collider and base-rate
analyses are not applicable to this deterministic one-run audit. Regression to the
mean, survivorship and selective reporting are avoided by retaining both failures,
unexecuted checks and the closed result. Forking-path and causal risks remain:
this is post hoc mechanism diagnosis, not a controlled repair-gain estimate.
Chronology establishes feedback-before-edit and admission-before-stop, but not that
offering a trace would make this model solve the task. Assisted success and this
fresh run have different starting information and cannot be pooled as an A/B.

Primary artifacts under `C:/pt/autonomous-fresh-run-v1` were rechecked unchanged:

- Journal `runs/run_dev_8fadb1628e0d4415.jsonl`,277 events:
  `sha256:d92e6c835ea5bb2f4ea54506562786055279e6745d2daa3fb816004e8b6db3b6`.
- `public-outcome-audit.json`:
  `sha256:b180669d53e801ce052f4f9e5c4c908f69cf4ae5fd26758fca641f30f07c800d`.
- `unsubmitted-candidate.patch`:
  `sha256:d52aba72a851f72745986f7f018b5e900b141e390a46be3efdf8a67b0dac2f62`.

Public caller: `C:/pt/calleruptake18/preparation-v2/B/site-packages/pylint/`.
Candidate: `C:/pt/autonomous-fresh-run-v1/workspaces/run_dev_8fadb1628e0d4415/repo/`.
Public regression, submission, isolated acceptance and safety remain NOT_RUN.
The prior allocation remains CLOSED; no runtime or candidate edits were made.

The pure resource audit was saved separately under
`C:/pt/autonomous-fresh-analysis-v1`:

- `budget_audit.py`:
  `sha256:1443c9f9aa939a90fcf7c25f70ee21a4dfe448c0399b3d3620a195cd19564205`.
- `budget-audit.json`:
  `sha256:0e011d133b7a854e4bfbaa020f24e3848507c766178663215f8e9e645be2146e`.
- One2.20-second pure replay passed assertions for actual admission at four turns
  and unchanged offered actions under the early-replay-only counterfactual. It
  records source/journal/envelope hashes and verifies those bytes unchanged.
  It does not run a model, target, container or evaluator.

All five focused documentation checks passed. Runtime tests and mock smoke were
not repeated for this documentation-only analysis; no new repair-success claim
follows from those documentation checks or the pure policy audit.
