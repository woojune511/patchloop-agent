# Five public-selected tasks: frozen-agent evaluation prepared

## Material Passport

- Workflow: academic-research-suite experiment-agent, plan/preparation.
- Status: PREPARED_NOT_EXECUTED; real provider/count calls and credential reads zero.
- Scope: five existing dev-train issues, one fresh solve each, official=false.
- Operator plan: `C:/pt/repair-five-plan-v1/plan.md` and `manifest.json`.
- Future results: `C:/pt/repair-five-run-v1/`; this directory does not yet exist.
- Live scope is pending exact approval; no prior paid allocation is reopened.

## Question and why now

The [pvlib follow-up](2026-10-29-private-evaluation-logs-pvlib-native.md) resolved
the saved candidate's acceptance-failure question. It did not show a transport
failure or establish that a new submission gate or budget increase would help.
The user accepted preparing a small fixed panel to identify remaining repair and
reliability failures before selecting another intervention.

Question: what fails on other public issues with the current agent and unchanged
resource settings? This is descriptive, without a concurrent baseline, causal gain
estimate or general-success-rate claim. A known bad patch, unavailable execution
and incomplete verification remain distinguishable outcomes.

## Public-only selection

| Order/index | Exact task suffix | Public problem type |
|---|---|---|
| 1 | marshmallow-code-marshmallow-1343 | Nested validation and invalid-input errors |
| 3 | pvlib-pvlib-python-1154 | Numerical zero-input boundary |
| 10 | pydicom-pydicom-901 | Import-time logging side effects |
| 11 | pylint-dev-astroid-1196 | Reference inference and exception contracts |
| 15 | pyvista-pyvista-4315 | Sequence input support in a constructor |

Each full task id has the prefix `swebench-lite-dev-` and lives at
`tasks/dev-train/current-dev20/<index>/public.yaml`. A fresh scoped reviewer read
only those public task files, not earlier outcomes, private tests or reference
repairs. Recent exact issues 5, 9, 13 and 18 are excluded. An initial repository-wide
exclusion would leave only two candidates; it was narrowed to exact issues before
final selection, yielding five repositories. That stricter exclusion was not a
user requirement. `selection.json` records reasons and alternatives.

The tasks are existing development material, not newly held-out problems. Public
author hints are preserved unchanged. Task 3's declared public regression projection
does not establish the requested behavior by itself. No operator diagnosis from
another task is added to any request.

## Frozen configuration

Use the same request settings as the latest fresh SQLFluff follow-up, changing
only task, prepared source/dependencies and new output directory:

- gpt-5.4-2026-03-05, xhigh; credentials at
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Five sequential fresh run_dev executions, one each; USD4.50 per task,
  USD22.50 total, no transfers, retries or resume.
- 20 total responses including at most one protocol correction; 40 tools;
  at most three accepted mutations; input 60K; normal/correction output 40K/25K.
- 2,400 seconds per task including 390 reserved for isolated evaluation.
- public-checks-v1, thin, segmented-v1, completion-recovery-v1; repair-recheck and
  protected-v1 inspection; optional probes, no automatic replay.

Implementation baseline is `98a0f5b6`. Agent runtime hash remains
`sha256:08b32133d33201efb3b55cd44db917ff76ffc8752676e00f5cdc366280b16b1e`.
The final manifest binds current task hashes, source/dependency descriptors,
existing images, execution helpers, validation receipts and planning commit.
It contains no live approval; a matching approval receipt is required separately.

Existing public wheel snapshots were copied unchanged into the new plan directory.
Python 3.12/graphics descriptors were rebound to the currently selected clean
images at the same ABI; Python 3.9 remains the existing offline compatibility
profile. Original snapshots were not modified. No downloads, image pulls/builds,
private evaluator runs or issue-specific reproduction occurred during preparation.

## Local evidence

- Five ordinary public API checks and five selected public tests PASS, 85.112 s.
  These establish selected environment capabilities, not repair correctness.
- Five initial requests constructed through the real runner with synthetic count/
  stop responses: empty diff, no prior results/source spans, matching counted and
  dispatched input/tools. Network, target execution and credential reads were
  blocked in these audits. Actual live token-fit remains NOT_MEASURED.
- Nineteen budget/stop checks and four synthetic summary checks PASS. Acceptance,
  public checks, original-call evidence and submission stay separate.
- Scoped source review found no blocking defect in actual generated execution
  files. Seal checks compare all request fields to the prior request, allowing
  only the four intended identity/path changes.
- Top-level external scripts pass Ruff with line-length E501 excluded. An initial
  overly broad lint also scanned third-party snapshots; that output is not project
  validation. No third-party or target source was changed by lint.
- Reuse the previous 33 focused and 923 quick PASS results because runtime code
  is unchanged; quick includes isolated mock evaluation. Docs are checked separately.

## Outcomes, stops and next decision

Primary outcome: registered isolated original SWE-bench acceptance, reported as
PASS/FAIL/ERROR/NOT_RUN across all five planned tasks. The registered oracle uses
the original test patch and upstream grading, so a duplicate native run is not
part of this panel. Submission, current-diff public checks, original observations,
safety, edits, calls, settled cost and active time are secondary measurements.

Detailed private logs are retained for operators after evaluation and never fed
back into solver requests. Classify concrete failures from evidence after the
panel; no prompt/runtime/budget adjustment is allowed between tasks. A repeated
mechanism may justify a later controlled change. One run per task cannot establish
repeatability, causal policy benefit or held-out generalization.

Count, transport, billing, execution or cleanup uncertainty, identity drift and
unknown/unreconciled outcomes stop remaining tasks without retry. Settled row
failures and settled cost exhaustion may proceed to the next fixed allocation.
Unused money authorizes no extra task. The executable command is
`& 'C:/pt/repair-five-plan-v1/run.ps1'`; its exact manifest and new USD22.50 cap
must be approved under AGENTS.md Hard gate 5 before dispatch.
