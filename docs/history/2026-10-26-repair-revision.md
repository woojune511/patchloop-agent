# Refutation-linked repair revisions and additive-test diagnosis reuse

## Problem and decision

The [closed trace-budget pilot](2026-10-26-trace-budget-live.md) delivered complete
pre/post-edit traces. The source edit still ran after the observed exception, and
the next edit added an unexecuted test with different lookup conditions. F0010
remained. A test-only full-diff change required another diagnosis, while the budget
forecast treated any accepted edit as progress toward source repair. This matters
because collection and submission progress must not obscure unchanged task failure.

The authorized change is local implementation and validation. It does not reopen
the paid allocation. Baseline HEAD: `a6ee1a4ca492641abe0b22b802b55ede72e2c5e5`.
External append-only evidence: `C:/pt/repair-revision-local-v1`, journal
`run_dev_repair_revision_local_v1`; all generated logs and receipts remain there
or in uniquely named `C:/pt/tmp/repair-revision-*` test workspaces.

## Requirement and alternatives

Keep the measured refutation visible when collection finishes; link the next
repair to an observable change; distinguish source repair from a test addition;
reuse a complete diagnosis only when runtime source and original failure are
unchanged; reserve actual remaining work. These are known contract defects and
local mechanism requirements, not a claim of model repair improvement.

The observations could still be insufficient for a useful repair, or the model
could retain a wrong causal explanation despite explicit counterevidence. Typed
fields cannot decide which explanation is correct. A valid prediction with the
same original failure would weaken any claim that the new structure improves
repair quality. Source/environment/captured-output drift must defeat historical
reuse. No need for an increased trace/output/cost limit is established here.

## Change

- Separate diagnosis collection completion from original-effect refutation.
  Preserve bounded exception sites, unobserved changes and exact evidence refs.
- Add a small source/test prediction to an edit after diagnosis. Source predictions
  select a host-bound observable on the original call; an event already true in
  the failed observation is rejected. Target -1/original_failure_absent permits
  value repairs without requiring different call counts.
- Observe source predictions during the existing automatic original replay.
  Keep its raw action/input identity. Check complete scope, current file/request/
  snapshot/execution identity and unchanged invocation/environment. Prediction
  support, original-case support and semantic correctness remain separate.
- Bind test additions to an actually added/extended function or method in a
  registered suite. The next action compares identical test bytes before/after
  the named source edit. PASS/PASS is non-discriminating; request/execution errors
  stay unverified. Neither consumes or supplies original verification credit.
- Reuse diagnosis through a fully validated additive-test mutation chain only.
  Require the same current captured failure and environment; preserve historical
  diff/snapshot provenance and previously consumed finite allowances.
- Reserve test edit, automatic replay/recheck, paired comparison and remaining
  source repair/check/finish costs. Keep two source/test edit slots available for
  the test-addition option. Normal limits and the unused correction reserve stay
  unchanged. Tool surface v59 binds the new optional-field contract on resume.

No reference patch, hidden test, evaluator internals or provider reasoning entered
the model context or this investigation. Existing historical experiment bytes and
the unrelated user AGENTS.md edit were preserved.

## Local validation

The short owner selection is `tests/repair-revision.txt`. It covers observed versus
refuted predictions, missing/invalid predictions, call/environment drift, partial
trace rejection, exact automatic replay, source/test mismatch, actual added-test
selection, historical diagnosis reuse and invalidation, budget boundaries, frozen
comparison, and uncertain child/parent recovery without duplicate execution.

Core: **68 PASS in 37.93 seconds** (39.42 seconds including process startup).
Quick: **377 PASS in 36.34 seconds**, four workers with worker restart disabled
(37.78 seconds including startup); includes isolated mock evaluation. Ruff: PASS.
An initial quick check reported 374 PASS/3 FAIL: two deliberately changed v59
surface pins and the current-guide byte bound. The pins were updated and detail
kept in the dedicated guide; no bound was enlarged. Final parallel quick passed.
Raw earlier failures remain in the append-only validation record.

Final runtime content hash:
`sha256:26ae466981d6d553a521e1fa57d86ddf074e21d7b7308c405154e6cdd45a9453`.
Core ran on the preceding runtime hash recorded in the journal; only compact
prompt wording changed afterward, and the final quick rechecked that path.

The tiny local integration demonstrates a contradicted path prediction alongside
a supported original repair without letting the prediction overwrite that result.
A separate test-only integration returns PASSED_BOTH, retains original refutation,
reuses historical diagnosis and does not renew its comparison allowance. During
integration, the prediction assessor's execution-identity projection was corrected
to the existing two-field runtime identity; the recovery control then passed.

## Evidence boundary and next question

Implemented and locally exercised; actual-model uptake, real astroid/pylint F0010
repair, Linux CI and general repair gains remain unverified. There was no provider
generation, target Docker run, image pull/build or cap increase in this work.
The next live question is whether the model changes its repair mechanism after
the factual refutation and reaches a discriminating source/test observation within
the unchanged limits. It requires a separately authorized exact run scope.
