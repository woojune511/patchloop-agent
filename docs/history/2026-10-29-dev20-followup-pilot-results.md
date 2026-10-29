# Dev20 caller and test-guidance pilot results

Date: 2026-10-29. CLOSED, official=false, claim-ineligible. Two fresh solves completed;
no retry, continuation, candidate replay or further model call is authorized by the
unused allocation. Original SWE-bench acceptance is the primary repair outcome.

## Question, intervention and conditions

The [dev20 failure analysis](2026-10-29-repair-dev20-failure-analysis.md) identified
missing caller preparation in Astroid and a bad test exhausting pydicom's mutation
slots. These matter because public regression PASS did not ensure task correctness,
and a plausible source repair could fail to submit through test-construction errors.
The [implementation](2026-10-29-dev20-followup-implementation.md) adds inherited
caller declarations, bounded private failure capture, and guidance on comparable
inputs, grounded expectations, literal searches and function-local imports.

The [sealed plan](2026-10-29-dev20-followup-pilot-plan.md) ran current-dev20/13
Astroid-1333 then /9 pydicom-1694 once each from original source. The user approved
`C:/pt/dev20-followup-pilot-plan-v1/run.ps1` and manifest
`sha256:5881ba165c4e12ddd60443ef22ed4d44ca5ab1d4ee2aab6a9ec9f9e2f648e466`.
Model: gpt-5.4-2026-03-05/xhigh; credentials: repository `.env`; USD4.50/task,
USD9 total without transfers. Keep public-checks-v1, thin, segmented-v1,
completion-recovery-v1, 20 responses including at most one protocol correction,
40 actions, three accepted edits, context60K/output40K/correction25K, and 2,400s
including 390s for evaluation. No prior patch, observation, operator diagnosis or
private evaluation feedback entered either solver's context.

Runtime implementation commit `5d27037e`, package declaration correction `5e3a5c57`,
and preparation commit `0479c748` precede execution. Runtime hash stayed
`sha256:c9fd20d950163c453aea27e0d050fcc19f40b92a76c4338ffffd900ffd8c4169`.
The package correction changed stale adapter hash declarations, not grading or
hidden-test bytes. Fresh Astroid preparation retained Python3.10 and previous wheel
hashes, adding pylint2.12.2 and its caller dependencies. pydicom retained its
Python3.12 snapshot. No evaluator image was pulled or built. The runtime and each
task's prepared configuration remained unchanged during execution.

## Observed outcomes

| Task | Final public checks | Submitted | Original SWE-bench acceptance | Edits | Model calls / actions | USD | Active seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 13 Astroid-1333 | 1231 passed, 69 skipped, 15 xfailed | Yes | FAIL | 1 | 15 / 26 | 1.1497085 | 389.129 |
| 9 pydicom-1694 | 27 passed, after 1 failed / 26 passed | Yes | PASS | 3 | 14 / 17 | 0.6830285 | 266.682 |

Total USD1.832737; wall time 662.791s. All 29 provider calls, 30 count requests and
43 actions reconcile, with no accounting, execution or cleanup uncertainty. Cost
is recorded provider usage, not invoice reconciliation. Maximum counted input was
57,398 tokens and maximum observed output 9,541; no output exhaustion occurred.
Both evaluations completed their expected case sets, with zero missing cases, and
both safety verdicts were PASS. Both deliveries remain `unverified_delivery` with
zero formal original-call attempts. That diagnostic label does not reverse the
pydicom benchmark PASS. The earlier full-panel result remains 10/20; this selected
two-task repeat is not substituted into that score.

## Astroid: caller availability worked, repair confirmation did not

The model made four `dependency:pylint` searches and read all 139 lines of
`pylint/lint/expand_modules.py`. Before editing, its helper called
`expand_modules(['src/project'], [], [], [])` on a public issue-like fixture with
`src/__init__.py` and `src/project/file.py`. It observed an entry for the nonexistent
`src/project/__init__.py`, with `errors=[]`. This was a caller path-selection
observation, not an actual pylint CLI/F0010 reproduction.

The model changed `_spec_from_modpath` in `astroid/modutils.py`: a `PKG_DIRECTORY`
without an initializer would become `PY_NAMESPACE`, instead of `PY_SOURCE`.
The helper's final output did not show whether that branch was reached. Public
caller code also constructs the initializer path before spec lookup and has an
ImportError fallback; the observed path alone cannot distinguish those routes.
The public suite passed, but changed-line observation was unavailable and no
post-edit helper or original-call replay was performed.

After the public check, the actual next context offered `run_probe` and linked the
previous helper with `probe_followup.replay.available=true`. The model chose
`finish_task` while acknowledging incomplete reproduction. Immediately after the
edit, the tool had been unavailable, but it was not blocked through submission.
Thus neither missing caller access nor persistent tool hiding sufficiently
explains this failure. Repair-path diagnosis and verification of the selected
change remain unresolved. Benchmark FAIL alone does not establish that the exact
original F0010 persisted or identify the failing branch.

Public journal `run_dev_aecd56b8decc47ff`: caller read seq88/89; helper seq153/156;
edit seq194/195; public check seq209/210; offered replay seq218; finish seq224/225.
Patch: `sha256:1ac127d0b6c304ac53f23ba4724953b59e25e665926f2b00bae9253af9d6ad57`.

## pydicom: a mutation slot remained for the actual public failure

The production change moved `data_element = self[key]` inside the existing `try`
in `Dataset.to_json_dict`. This is the same changed hunk as the prior failed run;
the edit anchors differ only in an unchanged prefix. The subsequent helper used
raw IS `b'2.0'` without strict validation settings. It produced no default exception
and retained value `[2]` with suppression. Exit zero established execution, not
the helper's hypothesized raise/drop behavior.

The added regression test used `enforce_valid_values` and imported `RawDataElement`
inside the test function. Unlike the prior run, it avoided a rejected global-import
attempt and the faulty `__globals__` workaround. Its initial `TypeError` expectation
was still wrong: the public check raised `ValueError: Invalid value for VR IS: '2.0'`.
The next counted and dispatched request contained the failed action ID, exception
and message; matching request hashes verify actual feedback delivery. The third
edit changed that expectation to ValueError. Harness recheck then passed all 27
tests, submission succeeded, and original benchmark acceptance was PASS.

Previously, the third edit fixed the workaround error, leaving no accepted edit
for this same exception mismatch. This time, local import preserved that opportunity.
This observed sequence explains the difference in mutation use; it does not isolate
the causal effect of the guidance from model variation. Initial expectations and
helper/test configuration comparability were not fully corrected by the intervention.

Public journal `run_dev_6f688ccc090f41f0`: source edit seq94/95; helper seq122/125;
test addition seq150/151; failed check seq162/163; feedback request/dispatch seq171/173;
test correction seq177/178; recheck seq182/183; solver finish seq201.
Patch: `sha256:ed4f07b4f7ac183924567475fb9253aa91afea2fb3a2282a97c6b2c050e956c2`.

## Failure capture, decision and limits

Astroid's operator-only evaluation capture retained one complete failure block:
2,832 original/retained bytes, no omitted, truncated or unclosed block. Its entire
7,880-byte stdout also fit the old tail, so this run exercises extraction but does
not demonstrate recovery of previously cropped large output. That case remains
supported by local synthetic tests only. pydicom had no failure block. Private
receipts/logs were not reinjected into solver context; the result audit started no
new provider call or target execution.

Preserve the caller capability, local-import guidance, public failure feedback and
unchanged total budgets. Actual caller use weakens availability as a sufficient
Astroid diagnosis. Successful pydicom submission and acceptance support investigating
avoidable test-construction edits; they do not establish general solve-rate gain.
A blanket budget or context increase is unsupported by these completed responses.

The smallest next diagnostic would compare the saved Astroid candidate and original
source using the same public caller/input, then observe which lookup/fallback and
edited branch execute. This is a proposed operator diagnostic, not a new solver
attempt or an executed result. Keep any private evaluation details out of it.
The two exposed tasks, one attempt each and bundled interventions do not establish
repeatability, causal feature effects or held-out improvement.

## Evidence and validation

- External plan/audits: `C:/pt/dev20-followup-pilot-plan-v1/` with `approval.json`,
  `results-summary.json`, `postrun-audit.json`, `public-mechanism-audit.json`, and
  `operator-evaluation-audit.json`; the master preparation journal is under `runs/`.
- Live journals and immutable artifacts: `C:/pt/dev20-followup-pilot-run-v1/13/` and
  `/9/`; `batch-collection.json` closes both rows without an unrun remainder.
- Preparation: all twenty package identities load; 2 package tests, 19 stop/accounting
  tests, 4 summary tests, two offline first-request audits and two public environment
  checks passed. Runtime validation from the implementation was reused unchanged.
- Post-run: both oracle summaries complete; 12 collected artifact hashes verified;
  all usage/action pairs settled. Public mechanism audits read saved evidence only.
  The closeout receipt records result-document validation and the final docs commit.
