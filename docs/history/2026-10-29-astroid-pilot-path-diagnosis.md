# Astroid saved candidate: lookup failed before the edited branch

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run; public saved-candidate replay and branch diagnosis
- Origin Date: 2026-10-29
- Verification Status: VERIFIED for the recorded public calls and selected traces
- Version Label: astroid_pilot_path_diagnosis_v2
- Evidence class: operator diagnostic; official=false, claim-ineligible

## Problem and method

The [two-task pilot](2026-10-29-dev20-followup-pilot-results.md) restored caller
access, but Astroid still failed acceptance after 1,231 public tests passed. The
model had observed a nonexistent initializer selected by pylint, edited a spec
classification branch, and submitted without replaying that observation. The user
authorized comparing the saved candidate with the original and checking the actual
path. The question matters because changing a branch outside the failing route
cannot repair that call, even when the test suite passes.

Alternatives were lookup failure before the edit, an already-namespace spec that
bypasses the edit, an executed but ineffective branch, or a repaired public example
with a different acceptance failure. Only the saved public helper, issue, caller
source and submitted patch selected the inputs; no private assertions were used.

The original and candidate used the same prepared Python3.10/pylint2.12.2 environment
as the pilot. Each logical cell ran in a fresh sandbox process, with read-only
source, no network and the existing 30s/12,000-byte limits. The fixture was
`src/__init__.py` plus `src/project/file.py` containing `import os`, with no
`src/project/__init__.py`, and cwd at the fixture root. No search root was added
by the operator.

The first call was the exact saved helper, including
`expand_modules(['src/project'], [], [], [])`. The second was the public command's
Python entry point, `Run(['src/project'], reporter=TextReporter(...), exit=False)`.
The reporter captures messages and `exit=False` returns status instead of ending
the helper; no checker or target argument was changed. This is an in-process CLI
entry point, not a new operating-system shell invocation.

Both calls were compared plain and with a read-only `sys.settrace` observer.
It recorded selected caller decisions, lookup calls/returns/exceptions and branch
line entries without replacing functions or editing target source. Loaded source
hashes matched the workspace/dependency bytes. Complete traced/plain stdout matched
after replacing only temporary fixture-root names; stderr also matched per pair.
This bounds observer validation to output, not timing or every internal state.

## Results

| Measurement | Original | Saved candidate |
| --- | --- | --- |
| Helper-selected file | nonexistent `src/project/__init__.py` | same |
| Helper errors list | `[]` | `[]` |
| Public pylint entry-point status | 1; F0010 | 1; same F0010 |
| Selected `['project']` lookup in `_spec_from_modpath`, per trace | 1 | 1 |
| Lookup at modutils.py:617 | `ImportError: No module named project` | same |
| PKG_DIRECTORY body at line 630 | 0 entries | 0 entries |
| Added no-initializer body at lines 632–634 | not present | 0 entries |

The **function ran, but the edited branch did not**. This is supported by the
explicit exception at line 617 and its propagation, not merely missing coverage.
The exception precedes successful-lookup line 618, the type test at line 629,
and the candidate's new condition/body at lines 631–634. Both helper and public
pylint traces show this route with no capture overflow.

Pylint produced the same public error before and after:

```text
src/project/__init__.py:1:0: F0010: error while code parsing:
Unable to load file src/project/__init__.py:
[Errno 2] No such file or directory: 'src/project/__init__.py'
```

The probe processes exited zero because they completed collection. Pylint's own
status was 1. Probe execution success and `errors=[]` from path expansion do not
mean this public behavior was repaired.

## Observed route and source explanation

1. `modpath_from_file_with_callback('src/project', ...)` raises ImportError at
   modutils.py:321. Pylint catches it at expand_modules.py:68–69 and selects basename
   `project` as the module name.
2. The caller constructs `src/project/__init__.py` for that directory, then asks
   `file_info_from_modpath(['project'], path=additional_search_path)` for its spec.
3. The path begins with `'.'` and the fixture's **project directory itself**. The
   CLI additionally has that same project directory in sys.path; the saved helper
   does not. Neither observed path supplies the missing parent as an explicit
   search root for the name `project`. All four spec finders return None.
4. `_spec_from_modpath` consequently raises at its `spec.find_spec` call. Its new
   PKG_DIRECTORY-to-PY_NAMESPACE conversion is never considered.
5. Pylint catches that error at line 94, sets `is_namespace=False` and
   `is_directory=True` at lines 96–97, then includes the nonexistent initializer.
   The helper result contains no `file.py`; the complete entry point emits F0010.

Source reading explains why the initial mapping is fragile: `_get_relative_base_path`
normalizes case but compares an absolute filename against a possibly relative
`path_to_check`. `'.'` does not match that absolute prefix. A search path equal to
the target directory instead yields an empty relative module path, which its caller
skips. These facts are consistent with the traced mapping failure; this diagnostic
did not test a counterfactual repair to path normalization or directory handling.

The original edit also assumed that a no-initializer directory arrived as
PKG_DIRECTORY. In this source, ImportlibFinder produces that type only after an
initializer existence check, while PathSpecFinder can represent namespaces directly.
The actual traces resolve the local ambiguity: this call did not return either
kind of spec at all. They do not establish that the added branch is globally dead.

## Decision and limits

For this candidate, the repair targeted a later classification step while the
failure occurred during earlier module-name/search-root lookup. Broad public-suite
PASS did not contradict that failure because the exact public caller still failed.
The model's missing post-edit replay left its hypothesis unchallenged. This result
weakens budget shortage and caller availability as sufficient explanations here.

Investigate module-name/search-root agreement and directory input handling before
another classification-only edit. Any candidate repair should make the same public
caller include the real `file.py`, remove F0010, and preserve normal package/file
behavior. No such repair was implemented or validated in this investigation.

For the agent, the next bounded design question is whether reusing its saved public
observation after edits and delivering the result before finish changes its next
decision. The existing replay opportunity was offered but unused in the pilot.
This case motivates testing that feedback path; it does not prove that a new hard
submission gate or always-on tracing improves performance. Source repair, automatic
feedback and model uptake remain separate questions.

This is an operator diagnosis of one exposed saved candidate. It is not a fresh
model solve, acceptance reevaluation, causal architecture gain or generalization
result. The earlier acceptance FAIL and original 10/20 score remain unchanged.
Historical Python3.9 equivalence is unverified; the comparison preserves the pilot's
Python3.10 environment. No model API call, credential read, private evaluator,
network access or image pull/build occurred. Model API cost: USD0.

## Diagnostic failure, correction and provenance

The first observer exceeded the existing output cap: 12,307 observed bytes versus
12,000 allowed. That comparison stopped after original helper success and the
failed trace; candidate/CLI cells had not run. The incomplete trace is excluded
from branch conclusions. A review also identified unstable filtering of a callback
whose local modpath changes, and unnecessary target preimports.

A separately recorded observer revision removed duplicate paths/unneeded line
details, retained selection for each matched frame and removed target preimports.
A synthetic local check verified exception capture after modpath becomes None;
Ruff passed. The completed original helper receipt was reused with exact program,
profile, request diff and snapshot checks. Seven remaining cells ran once under a
new 240s local diagnostic deadline, taking 68.951s. All four final traces had zero
overflow, at most 5,279 total output bytes and confirmed cleanup. All eight complete
logical cells had no timeout/output failure. There were **nine physical executions**
including the first failed observer, not eight. No unchanged crash retry occurred.

Host commit at execution: `0f5a5cd1`; unchanged runtime hash
`sha256:c9fd20d950163c453aea27e0d050fcc19f40b92a76c4338ffffd900ffd8c4169`.
Candidate patch:
`sha256:1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57`.
Public source commit: `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.

Evidence roots: `C:/pt/astroid-pilot-path-diagnosis-v1/` retains the failed observer;
`C:/pt/astroid-pilot-path-diagnosis-v2/` contains the corrected plan, programs,
hash-chained run journal, source workspaces, plain/trace receipts, `summary.json`
and `analysis.json`. The analysis script's zero-execution field describes only
reading those receipts; the summary records seven new/nine combined executions.
The final closeout records document validation and evidence hashes. A native
shared-context reviewer checked public source and traces; this is not cross-model
or blinded evaluation. Existing closed artifacts were not rewritten, and no result
was injected into the previous repair model.
