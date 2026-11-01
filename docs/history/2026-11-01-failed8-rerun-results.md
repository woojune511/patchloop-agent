# Failed-eight rerun: one new independent PASS

Date: 2026-11-01. Lane: dev-head, official=false, claim-ineligible. CLOSED.

## Question and selection

The [public audit and filename correction](2026-11-01-failed8-and-test-discovery.md)
addressed a concrete missed-discovery defect and recurring input/expectation gaps.
This run asks whether the integrated agent now repairs the eight failures from the
[latest full20](2026-11-01-pre-edit-dev20-results.md), and what failures remain.
The user accepted the proposed fresh eight-row invocation. Selection was explicitly
outcome-based: tasks **7, 8, 10, 12, 13, 16, 17, 19**, one attempt each. The twelve
previously passing tasks were not included, so this is not a full20 regression run.

The question, baseline, intervention, selection, criteria and stop conditions were
bound in the manifest before dispatch. Independent acceptance and safety, actual
public assertions, input fidelity, cost and time matter; fewer actions alone do not.

## Frozen execution

- Execution commit: `062dde2e4be641cfb1b8ffc7d9a7fef7b3e12e88`.
- Runtime: `sha256:268b9abb488f62a08bb7c6c7c754080c8893831fe68327caa467cf33085c4792`.
- Model: `gpt-5.4-2026-03-05`, xhigh, output ceiling 25,000; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env` (contents never recorded).
- New allocation: USD4 per task, USD32 invocation-wide, at most two workers.
- Per row: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds including
  a 330-second independent-evaluation reserve. Existing selected policies retained.
- Requests differ from the prior full20 rows only in fresh `state_root`. Pristine
  prepared sources and the existing corrected task13 dependency descriptor were
  reused after public import/operation/test canaries. No prior patch, helper, answer,
  checkpoint, diagnostic hint, cross-run note or private expectation entered a solve.
- All count/transport/billing/continuation/cleanup uncertainty stops new admissions.
  SDK retries are zero. No retry, resume, extra evaluation, budget transfer or
  mid-batch runtime edit occurred. Docker was not started, built or pulled.

The official [standard pricing table](https://developers.openai.com/api/docs/pricing)
was checked during preparation: USD2.50 input, USD0.25 cached input and USD15 output
per million tokens, below 272K context. The runtime input limit is 60K.
Exact source and local validation remained bound: 88 focused PASS in 20.65s;
1,494 quick PASS/one host skip across the documented corrected runs; Ruff, docs and
isolated mock PASS. Those are prior local validation, not new live success evidence.

## Results

All eight submitted once and received independent evaluation. **1 PASS, 7 FAIL;
8 safety PASS.** Only task13 changed from FAIL to PASS. Every final required public
check passed; tasks13 and17 first exposed and repaired public regression failures.

| Task | Instance | Independent | Calls | Accepted edits | Generation USD | Row seconds |
|---|---|---|---:|---:|---:|---:|
| 7 | pydicom1139 | FAIL | 9 | 1 | 0.6356825 | 287.613 |
| 8 | pydicom1413 | FAIL | 9 | 1 | 0.5569460 | 288.593 |
| 10 | pydicom901 | FAIL | 9 | 1 | 0.8260260 | 396.979 |
| 12 | astroid1268 | FAIL | 7 | 1 | 0.4978040 | 208.425 |
| 13 | astroid1333 | **PASS** | 30 | 2 | 3.4596270 | 1,083.726 |
| 16 | sqlfluff1517 | FAIL | 14 | 1 | 0.9985425 | 425.708 |
| 17 | sqlfluff1625 | FAIL | 20 | 2 | 2.0241060 | 893.146 |
| 19 | sqlfluff1763 | FAIL | 23 | 2 | 1.8266195 | 694.159 |

Generation usage totals **USD10.8253535**, **121 calls**, **124 input counts** and
201 completed actions. Batch wall is **2,277.183 seconds (37m57s)** excluding
preparation; row times overlap. All usage settled, every actual request matched its
count and projected public input, and all submitted artifact/journal hashes checked.
USD21.1746465 is closed, not available for another run. Invoice and count-endpoint
billing were not independently reconciled.

The same eight baseline rows cost USD10.2215815 with 122 calls and eight FAILs.
Cost rose USD0.603772 while one task became PASS. Multiple changes, selected prior
failures and one attempt per task prevent feature-level causal or held-out claims.
The latest eight cannot be combined with twelve older verdicts into a new-code
full20 score. All submissions retain the separate `unverified_delivery` label
because no registered original-obligation replay was acquired; task13 nonetheless
passed independent evaluation.

## Public mechanisms observed

**Task13: the diagnosis reached the faulty path operation.** The new regression
preserves `src/__init__.py`, the child directory without `__init__.py`, and relative
search roots such as `path=[".", str(project)]`. The earlier failed run omitted the
parent initializer in its caller probe. This run reproduced F0010 through
`pylint.lint.Run`, distinguished module-path derivation from namespace classification,
and repaired `_get_relative_base_path`. The first edit broke an existing symlink
test (1 FAIL/1,231 PASS); the second changed only production code and kept the new
test unchanged. Automatic public recheck then reached **1,232 PASS**, and the
retained caller probe no longer emitted F0010. The normal package control also
worked. This sequence and independent PASS support this repair within the observed
conditions; they do not isolate the contribution of the new review format.

**Task8: a stated stopping constraint contradicted the delivered resources.** At
call9 the model said the exact original reproduction could not fit a “one-call
completion stage.” Its actual input showed 32 model calls, 31 exploration calls,
87 actions, 1,209 solver seconds and USD3.504356 remaining; edits and probes were
offered and exploration was open. `completion_budget_calls=1` was the protected
completion requirement, not a hard remaining-call cap. The scope review had already
identified substituted input/setup, but the patch and probe stayed on OL plus a
text-VR control. The contradictory explanation is observed. Misreading reservation
terminology is a hypothesis; a low-value judgment or post-hoc justification could
also explain the choice. Neither field causality nor the private FAIL cause is proved.

**Other tasks did not share one established failure cause.** Task7 directly checked
the reported PatientName containment/iteration example. Task10 added the previously
missing explicit `debug(True/False)` control. Task12 still chose the exact result
`'Unknown'` from the node's name although the public issue does not settle that
string oracle. Task16 observed non-crashing `;;` and a single-semicolon control but
left broader grammar behavior to the passing subset. Task17 repaired two existing
alias-test regressions and executed the exact TSQL assertion and nearby controls;
independent FAIL remained. Task19's encoding-failure preservation and UTF-8 control
passed, while the full dbt/postgres and `--noqa` report remained unverified. Private
assertion bodies were not read, so these public gaps are not exact grading attribution.

**New-test behavior and review uptake.** Both new modules,
`pydicom/tests/test_config.py` (10) and `test/core/linted_file_test.py` (19), match
their public filename rules and were explicitly executed successfully. No filename
mismatch was proposed, so rejection/recovery effectiveness was not exercised live.
Matching names and explicit execution do not independently prove ordinary directory
collection. All 37 emitted scope-case occurrences used structured `outcome` and
`public_basis`; that is uptake, not proof that each basis is a valid oracle.

Task17 recovered from unsupported YAML test editing and duplicate paths in an atomic
edit. Task19's first test failed in NamedTuple setup; an attempted repair changing
shared imports was rejected, then a local dummy setup preserved the arrow/cp1252,
original-file and temporary-file assertions and passed. These three rejected
mutations rolled back. None was a filename-discovery rejection. The public audit
found no identical same-diff probe AST or identical selected-check repetition;
overlapping or semantically repeated tests remain possible.

## Decision and next question

Keep the concrete filename defect correction and the source-supported review
format. Task13 supplies a successful repair trajectory to preserve, while the
seven remaining FAILs rule out treating this panel as a general solution.

The next bounded design question is how to make the actual remaining resource and
offered-action state unambiguous. Remove or clarify redundant completion-reservation
terminology before adding another review gate or increasing limits. A diagnostic
at task8's saved public decision could distinguish an interface-reading error from
a persistent judgment that additional verification is unnecessary. That diagnostic
and any new paid execution are **not performed or authorized by the closed balance**.
Do not require a registered original replay solely because the bookkeeping label
is unverified; task13 shows why that label and independent correctness stay separate.

## Evidence and validation

Preparation/operator records: `C:/pt/failed8-rerun-20261101-v1/`.
Run records: `C:/pt/failed8-rerun-run-20261101-v1/`.

- `manifest.json`: `sha256:b384d08e92c425fd3aac204d80faa37011e59d5c1b92efa2bf626af6b54f7689`.
- `closure.json`: `sha256:7dd9a8e63509113486fb9c203b7362ab63e88efc75ec19dbf8d02fe0635f7b73`.
- `findings.json`: `sha256:73c27e68c8b656323f463d4e66ad9b22a3103b5a78f7aef9a579d1b1092ceccf`.
- `audit.json`: `sha256:a2d3c1e775988d42e6c4574746d0cebb77ffc24f5b0f2c3941c95c64226edd19`;
  individual `taskN.json` files retain public input/action/check and patch references.
- Live `analysis/public-flow.json`:
  `sha256:0177bc2381bf56be4171c816657558c06d8cee2cfd83971b859298f25a22bc34`.

Post-run collection/closure/public analysis executed no model, target or evaluator.
The common input verifier's derived `current_diff.test_execution_review` authority
exception was handled only after full projected-state equality, then the canonical
diff and public authority fields were compared separately. It was not an ignored
input discrepancy. Result-document checks and the commit binding are in
`result-validation.json` and `result-commit.json` in the preparation directory.
