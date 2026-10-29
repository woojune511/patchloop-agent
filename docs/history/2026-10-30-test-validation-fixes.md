# Allowed test edits and exact restoration

Date: 2026-10-30 KST. Implementation and local validation only; no new paid allocation.

## Problem and decision

The [integrated selection run](2026-10-30-integrated-selection-results.md) exposed
two conflicting validation paths on pvlib1154. Its first patch added a test that
the mutation policy accepted, but the public wrapper rejected the changed file's
whole-file hash before pytest. Moving that addition into another file then hit
an earlier additive-only validator before the exact-original-restoration exception.
Seven rejected requests preceded a full undo and rebuilt patch. This matters for
reliable repair and unnecessary model calls; the run took longer, but it does not
quantify how much time either defect caused.

Public receipt reconstruction had already established exact original bytes after
removing the addition. Whitespace drift was ruled out. These are known contract
defects, so the user requested fixing both together without another paid ablation.
Keep original-test preservation, observed-source admission and transactional recovery;
remove conflicting checks rather than adding a prompt, tool, gate or policy setting.

## Change

- `validate_test_addition` permits an existing file restored to its exact HEAD bytes
  before applying additive-case rules. Replacement admission, file batches and final
  validation share that rule. `file_edits` no longer carries a separate restoration
  exception; it retains the original-file deletion prohibition. New empty files and
  AST-equivalent but byte-different replacements are not exact restoration.
- pvlib's required and selected public wrappers retain the GHI-zero expectation
  projection, but pin the original target function's body/signature AST and its exact
  local assertion anchor instead of the entire module hash. A unique top-level target
  is required, and replacement occurs only within that function's source span.
  Added tests stay in the temporary checkout and execute, even if they contain a copy
  of the same anchor. Changing that target anchor's whitespace still fails explicitly.
- The shared admission/final-diff policy continues to protect the whole module's
  original tests, imports, fixtures and decorators. The adapter is not a substitute
  for that policy. Its target digest excludes decorators so permitted literal case
  additions remain possible, and normalizes empty AST fields for host/image Python
  compatibility. The ordinary `PUBLIC_RUNNER` and other task registrations are unchanged.
- Current task 3 and the canonical pvlib public package use the same generated wrapper.
  Both new regression modules join the existing quick manifest. No wire schema,
  prompt, edit cap or new runtime version is introduced.

Execution base HEAD: `06d1d980`. Changed runtime identity:
`sha256:d3c4d806ddc25b6cbd06a2b9d44cc844e1d675df29309d5e120d1e7ecf0e2132`.
Current task 3 public YAML byte hash:
`sha256:cb463988735dfb0bad633ae10dc2b85ccc6c9aade34cfd1f482bc7095151e62b`.
Old prepared runtime/task identities must not be reused for a future solve.

## Local checks

Restoration selection: **25 PASS in 93.04 seconds**, including 15 new cases and
10 existing additive-policy/file-edit checks. Coverage includes both mutation tools,
moving a test while preserving source repair, rollback after a partial write,
crash recovery, completed-action replay without double charging, conflicting action
identity, source/scope admission, original deletion/tampering, empty new files and
deadline enforcement. Receipt: `C:/pt/validation/restoration1030.xml`.

Adapter selection: **19 PASS** across the initial 17 and two added checks. The
registered wrapper runs real local pytest with the public target function and small
scientific-library doubles. Allowed functions, classes, methods and literal cases
execute; an added failing test and nonzero-GHI regression still fail. Duplicate or
altered targets, missing exact anchors, and forbidden original setup/assertion
changes are rejected. Caller workspace bytes remain unchanged. Ruff passed.

Quick regression: **1,208 PASS, 1 unavailable symlink check skipped, 332.31 seconds**.
The selection includes both new modules and isolated mock submission/evaluation;
four file-grouped workers completed without restart or failure. Command:

```powershell
uv run --locked pytest '@tests/quick.txt' -n 4 --dist loadfile --max-worker-restart 0 --basetemp C:/pt/tmp/tvf1030q --junitxml C:/pt/validation/test-validation-fix1030-quick.xml --durations=10
```

`uv run --locked ruff check patchloop tests` and `git diff --check` passed.
Final documentation validation: **6 PASS in 0.27 seconds**, retained in
`C:/pt/validation/test-validation-fix1030-docs.xml`. All three JUnit reports are
also CAS-bound by the external validation journal; summary:
`sha256:b876f0d67f5b5271ade70a6123e33b0a89f6862401e0668eaaa803b7853e1327`.
HTML static checks found 51 unique IDs and resolved all 62 links; inline JavaScript
is unchanged. Public YAML semantic comparison confirms only the registered runner
strings changed. Static-check CAS:
`sha256:ba00e779e36e66be258a0eb6845a226ff5c4daaebe74b31f15c6c4dfebe34a2c`.
Full-suite, Linux and browser visual validation were not run.

## Actual public replay

Two provider-free registered Docker checks used the already installed task image
`sha256:e9c63e07cdef7fee63af473e6556dff00ed3b951a5e75b72fded8667baf615e5`.
No daemon startup, image acquisition, model call or private evaluation was performed.

Fresh workspaces were prepared from the existing public source snapshot. The first
reused the public mutation bytes from action `call_jsbDG3P9r6nkNo10QmbRuL0Q` in
`run_dev_c32896c165e14053`, exactly the candidate the old wrapper rejected. The control
kept the original implementation and the identical added test. Other registered
check settings and the new wrapper were identical; runtime stayed frozen.

| Public candidate | Result | Sandbox elapsed | Pytest elapsed |
| --- | --- | ---: | ---: |
| Recorded first repair + added test | 99 PASS | 17.902 s | 3.85 s |
| Original source + same added test | 1 FAIL / 98 PASS | 9.186 s | 3.65 s |

The control fails specifically at `test_reindl_zero_ghi`. This confirms the wrapper
now reaches pytest, preserves execution of the added regression and distinguishes
this repair from the original behavior. It does not establish independent acceptance
or the model's future choices. The original run journal and both caller workspaces
were unchanged by checks. The old run and its closed report remain immutable.

Evidence root: `C:/pt/test-validation-fix-20261030-v1`.
`result.json` binds the replay script and full public receipts through CAS. The
external `dev-run-v1` journal is append-only and hash-chained. Report:
`sha256:2feacdce9bb532129dd5dbbf8ea231aaffc7bf4606625aa3617306ee774345d7`.
Script: `sha256:63cc1ad29fd1fc87ad2102f5519b8f723eae8552663ea9a3c37882b833190a73`.
Saved repair diff:
`sha256:95770a5fdb685fb52d3e7c0a7c7ea3232a8ebf0af837574e7f76c15aed9492b6`.

## Scope and next question

Both known validation conflicts are corrected. Local tests support restoration,
preservation and recovery, and the public replay supports this saved candidate's
test behavior. Whether the current model avoids the earlier detour, spends fewer
calls or finishes faster remains unmeasured. The next integrated development run
can answer that without making a separate ablation a prerequisite. All previous
paid allocations remain closed; this change authorizes no new paid execution.
