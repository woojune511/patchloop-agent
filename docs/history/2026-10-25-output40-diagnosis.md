# Output-40K diagnosis: ineffective edits and competing recovery reserves

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-10-25
- Verification Status: ANALYZED; public records and source projections, no full rerun
- Version Label: output40-diagnosis-v1
- official=false; claim_eligible=false

## Question and evidence boundary

The [closed 40K pilot](2026-10-25-output40-live.md) delivered comparable original
failure feedback before two subsequent edits, but all three edits retained F0010.
It then stopped with unused money because the correction reserve left fewer than
three fundable minimum calls. The user asked why feedback did not yield a repair
and whether the reservation was too conservative.

This investigation reads the existing public task, recorded tool requests/results,
actual dispatched model inputs and matching source/dependency files. It runs pure
arithmetic and source functions over a virtual POSIX fixture tree. It does not
rerun Pylint, launch containers, call a provider, change runtime behavior, resume
the allocation or inspect private reasoning/evaluator material. The virtual
projection is conditional source evidence, not a newly observed execution trace.
Budget reasoning also received a separate native, shared-context review; that is
not a blinded independent experiment or acceptance evaluation.

## Findings that change the diagnosis

1. Feedback was delivered and explicitly acknowledged, but no additional authored
   diagnostic probe distinguished the repair hypotheses. The model inspected
   source 27 times between the initial reproduction and its first edit.
2. The edited helpers do not establish the caller's crucial intermediate values:
   module name, module specification, or the file path selected for parsing.
   Recorded stdout/stderr, outcomes and exits are identical across the baseline
   and all three candidate replays for both failing and control calls.
3. Under the recorded paths and public fixture setup, the failing directory's
   module-name lookup falls back before the edited package callback can help.
   This explains why changing namespace recognition and callback components did
   not change the final F0010. The exact internal lookup trace was not recorded.
4. On every edit-generating model call, the only offered tools were `replace_text`
   and `stop_task`. Feedback arrived while fresh diagnosis was unavailable. This
   closure preceded the final monetary stop and was caused by the protected
   physical-call horizon, not by the dollar reservation alone.
5. The 40K correction reservation follows the current contract, but at the frozen
   final state it excludes a minimum path that a 25K correction reserve would
   admit. Neither calculation establishes useful future output or repair success.
6. Model-call forecasting does not distinguish healthy early replay from final
   replay even though finish reuses the early receipt. This is a separate,
   state-specific source of conservative forecasting.

## Why these edits did not change the observed failure

Frozen Pylint 2.12.2 source supplies the missing caller context. In
`pylint/lint/expand_modules.py:62`, a directory input is converted to a module
name; an `ImportError` falls back to the basename. Line 71 constructs a provisional
`src/project/__init__.py` path. Lines 91-101 separately obtain a module specification
and decide whether the directory is a namespace package. An `ImportError` here
sets `is_namespace=False`; the provisional initializer is then added to the work
list. `pylint/lint/pylinter.py:1177` passes that path to
`AstroidManager.ast_from_file(..., source=True)`. The file-open failure in
`astroid/builder.py:121` becomes the observed F0010.

Two similarly named functions have different contracts. The edited
`astroid/interpreter/_import/util.py:is_namespace(name)` returns a boolean from a
module name. Pylint's branch consumes `astroid/modutils.py:is_namespace(spec)`,
which tests `spec.type == PY_NAMESPACE`. The former can influence some upstream
paths; changing it does not directly supply the latter with a successful spec.

| Edit | Proposed mechanism | Evidence against its sufficiency |
| --- | --- | --- |
| 1, `util.py` | Recognize implicit namespaces using `importlib.util.find_spec(name)` | It does not repair a wrong module name/search root or change the caller's missing-spec fallback. The same F0010 and control output remain. |
| 2, `util.py` | Separate the import and guard `ModuleNotFoundError` / `ValueError` | The observed failure remained a file-open error. The new exception-handler lines were not observed by the launch-thread line feedback. No discriminating observation established this guard as the missing mechanism. |
| 3, `modutils.py` | Pass all directory name components to the package callback | The changed callback is reached only after a nonempty relative module path is found. The virtual projection reaches no such callback for the failing directory, before or after this edit. |

The virtual projection extracts the actual `get_python_path`,
`_get_relative_base_path` and `modpath_from_file_with_callback` functions. It uses
recorded cwd/sys.path, the authored failure/control files and POSIX path rules,
including Pylint's `fix_import_path` addition. It reconstructs the three versions
from public replacement requests without modifying the saved workspace.

| Projected value | Missing-initializer tree | Control tree |
| --- | --- | --- |
| Pylint's added search root | `/tmp/patchloop-case/fail/src/project` | `/tmp/patchloop-case/control` |
| Relative name discovery | No usable candidate; `ImportError` | `['src', 'project']` |
| Caller name after fallback | `project` | `src.project` |
| Package callback for the directory | Never reached | Parent parts before edit 3; full parts after edit 3 |
| Effect of edits 1-3 on the computed name | None | None |

For the failing tree, the explicit `.` search entry is not normalized by this
relative-path function before comparison with an absolute filename. The added
absolute directory is the input directory itself, yielding an empty relative
path; it is skipped. The remaining recorded roots do not provide the fixture
parent. The callback change is downstream of that failure. The helper's separate
`find_spec(name)` also uses the process import path rather than the caller's
explicit search-path argument.

This source-derived explanation is consistent with the actual diagnostic heading
`Module project` on every failing call and `src.project.file` on every control.
It identifies the path-to-module-name/spec boundary as the next diagnostic target.
It does not validate a proposed fix or prove the full standalone CLI environment
is identical. Original report-to-caller mapping remains model-authored/unverified.

Changed-line feedback confirms entries into parts of the changed files somewhere
in the probe's launch thread. It aggregates setup and both calls, so it cannot
establish that a changed branch handled the failing case or produced a particular
return value. It weakens a blanket "the patch never ran" explanation; it does not
establish causal coverage. No transport, truncated diagnostic or condition drift
explains the repeated result: captures are complete and replays comparable.

## Why feedback acknowledgement was not enough

The final public `causal_revision` acknowledges that namespace hardening did not
change F0010, then chooses the directory callback as a new hypothesis. That is
explicit feedback use. It is not evidence that the new branch lies on the failing
path. The second edit similarly adds safety around a suspected importlib problem
without an observation showing that exception to be the blocker.

The initial probe retained a boolean failure marker plus raw diagnostic output.
Automatic replay answers whether the selected failure remains; it does not locate
the cause. No authored follow-up measured `modname`, `file_info_from_modpath`'s
result/exception or the caller's selected file list. Twenty-seven source reads and
searches cost USD 0.500723250, and the first edit began after USD 0.596339250 had
been spent. Source inspection was available and sometimes useful, but its volume
did not substitute for a hypothesis-discriminating observation.

By calls 29-31, the policy offered only mutation or stop. The last generation used
34,882 output tokens and USD 0.173954700 with no opportunity to gather a new
observation inside that turn. More generation capacity did not provide the missing
runtime distinction.

## Two separate reservation effects

Physical admission closes diagnostics using a protected completion path. At call
29 there were 12 model slots left, of which one was reserved for a protocol
correction. The protected path required 11, leaving no optional diagnostic slot.
That path includes the three-call minimum plus mutation-rejection recovery,
check-failure recovery and failed-replay recovery. The correction slot is separate;
the whole protected path must not be attributed to it.

| Model call | Physical slots | Correction slot | Protected path | Offered diagnosis |
| --- | ---: | ---: | ---: | --- |
| 28 | 13 | 1 | 11 | One last opportunity; closure warning delivered |
| 29 | 12 | 1 | 11 | Closed |
| 30 | 11 | 1 | 11 | Closed |
| 31 | 10 | 1 | 9 | Closed |

At call 29, monetary admission still funded eight minimum calls, enough for a
diagnostic plus the three-call minimum. Lowering only the dollar reserve would
not reopen the physically closed tools at that point. The selected policy was
`protected-v1`. The separate `current-failure-v1` relaxation currently keys on a
failed registered check, not an original case marked `refuted`; it was not selected.

There is also a concrete execution/forecast mismatch. `runner.py:3785` shares the
same case/diff replay between early feedback and finish, and reuses its durable
result. A comparable early failure sets `needs_mutation` and blocks finish. For
a healthy acquired case already evaluated on that diff, finish cannot consume a
new call and then discover a newly executed failure of the same case. Nevertheless,
`completion_budget.py:89` protects a failed final replay that consumes finish,
using `recovery = check_count + 3`. `early_reproduction_count` changes tool-action
reserves only. A pure same-state calculation gives protected model calls 11 with
early replay disabled or enabled; protected tool actions change from 14 to 15.

This supports state-specific over-conservatism after the replay timing changed.
It is not a safe general rule to subtract one: early replay may be deferred when
admission closes, and unacquired/pending cases can still need final fallback.
The exact tightened bound needs path enumeration across edits, rejected mutations,
checks and early/deferred replays. The existing early-feedback tests cover receipt
reuse and deferred fallback, but do not establish an optimized model-call bound.

The final stop is monetary. With USD 0.330274650 remaining, the current reservation
keeps 60K uncached input and 40K output for one correction: USD 0.225000000. It is
18.75% of the total cap and about 68.13% of the money remaining at termination.
It is not billed spend. Each ordinary minimum is 60K input plus only 128 output,
USD 0.045576000. The still-failing state requires three such calls.

| Frozen terminal-state calculation | Correction reserve, USD | Ordinary money, USD | Fundable minimum calls |
| --- | ---: | ---: | ---: |
| Actual 40K correction | 0.225000000 | 0.105274650 | 2 |
| Correction reduced to 25K | 0.157500000 | 0.172774650 | 3 |
| Monetary correction reserve released | 0 | 0.330274650 | 7 |

The three-call minimum costs USD 0.136728000; the actual state is short by
USD 0.031453350. A diagnostic plus that minimum costs USD 0.182304000, so even
the 25K-reserve counterfactual is short by USD 0.009529350 for diagnosis first.
These calculations fix the entire prior history. They do not simulate a rerun,
predict the next response, or show that a fourth edit would succeed. Minimum
128-token admission is not a guarantee of useful reasoning/tool output.

The reserve is conservative in opportunity cost, but not a counting bug. The
contract ties correction output to invocation output and releases it only on the
first correction or termination. Thirty-one valid responses do not prove the
next would be valid: the previous run exhausted both its initial and correction
responses. Nonetheless, prioritizing a full speculative correction over an
already observed unresolved failure is a design choice worth revisiting.

## Decision and smallest next investigation

Do not equate feedback delivery with a validated repair mechanism, or unused
reserved money with a promise of repair. Keep the original failure criterion,
current-diff required checks and independent evaluation boundaries intact.

The next bounded diagnosis should observe the caller boundary: which module name
was produced, whether spec lookup succeeds and returns `PY_NAMESPACE`, and why a
missing initializer enters the work list. Preserve the original case unchanged;
any added helper observation supplies diagnosis rather than acceptance credit.

Two policy directions warrant separate local checks before any live comparison:

- Decouple normal output capacity from the correction-specific allowance. Making
  a late correction smaller or releasing its reservation sacrifices that recovery
  guarantee, while the actual pre-dispatch count/cap check can still prevent
  exceeding USD 1.20. Do not claim the old full-correction guarantee after release.
- Let a comparable original failure use one bounded diagnostic opportunity while
  preserving a minimum completion path, rather than requiring all speculative
  recovery paths before every read/probe. This trades protection against possible
  later failures for information about the current known failure. It does not
  create extra budget or guarantee success.

Before broadening policy, align the forecast with observed early-replay eligibility
and same-diff reuse. Remove unreachable recovery work only for states where the
execution contract proves it unreachable; retain deferred and unacquired fallback.

These are proposals, not implemented or measured improvements. There is no new
paid allocation or target-execution authorization in this analysis.

## Validation, provenance and limits

Source run: `run_dev_fd87d80110a643b5`, runtime hash
`sha256:2d1a7111c4fb45675cbb415df884c96460fbc138eca2bec06c6a06f747fa5dce`.
Analysis entry commit: `e420d172b6079c3de715431c864064c16c4e6f29`.
Read-only calculator and source bindings: `C:/pt/output40-diagnosis-v1/analyze.py`.
Analysis: `C:/pt/output40-diagnosis-v1/analysis.json`, hash
`sha256:670ebf2aac1c18c2f34a4ad7cc6439aca0f7ea7e6fc934717947bec11ee48085`.
Early-replay forecast: `C:/pt/output40-diagnosis-v1/early-replay-forecast.json`, hash
`sha256:83327e3d056f29b07d7c8b886593fcf7f8c4d53f291d2a2ee0ba54414e30254a`.
The result and script are content-addressed and recorded in a separate append-only
`dev-run-v1` analysis journal. Source execution journals are unchanged.

ARS fallacy coverage: 11/11 reviewed. Simpson, ecological inference, collider,
base-rate inference and reverse causality are not applicable to these descriptive
records. Selection of an exposed failed task limits generalization; the preceding
extreme output failure makes regression-to-mean a live-comparison alternative.
Unfinished runs and all three negative edits are retained (survivorship and
look-elsewhere checks). The source projection is explicitly post hoc (forking
paths). Feedback use and arithmetic admission are not repair-effect estimates
(causation). No p-values, effect sizes or independent-trial interpretation of the
three dependent edits are warranted.

Runtime/model behavior is unchanged. Two focused mock checks passed for early
receipt reuse and deferred replay, together with five documentation checks
(seven checks, about eight seconds total command time). The receipt is
`C:/pt/output40-diagnosis-v1/local-checks.xml`; the final commit receipt is recorded
under the same analysis root. These checks do not validate a tightened forecast.
Public regression, independent acceptance and a full target diagnostic rerun
remain NOT_RUN.
