# Public repair

`patchloop repair --request request.json` runs the existing solver in a separate
checkout. It returns a content-addressed patch and public check receipts. It does
not apply the patch to the source or run independent acceptance (`NOT_RUN`).

For a provider-free executable example, using only the public CSV fixture:

```powershell
.venv/Scripts/python.exe examples/repair/make_mock_request.py C:/pt/repair-example
.venv/Scripts/patchloop.exe repair --request C:/pt/repair-example/request.json
```

This uses the scripted smoke model and trusted local checks; it tests plumbing,
not autonomous repair quality. Choose a new directory for each example.

For a real public task, write `public.yaml` with the issue, exact commit and checks:

```yaml
schema_version: repair-task-v1
task_id: my-public-fix
repository:
  url: https://github.com/owner/project.git
  base_commit: REPLACE_WITH_FULL_40_CHARACTER_COMMIT
  language: python
issue:
  title: Describe the reported public failure
  description: Describe expected and observed behavior, using public information only.
constraints:
  allowed_paths: [src/**]
  forbidden_paths: [tests/**]
  max_changed_files: 4
  max_diff_lines: 120
visible_checks:
  - id: public-regressions
    command: [python, -m, pytest, tests]
    timeout_seconds: 120
```

Use an existing local Git source containing that commit and an already prepared
image containing the project's dependencies. Replace the placeholders in this
`request.json`; paths are relative to the request file (absolute paths also work):

```json
{
  "task": "public.yaml",
  "source": "C:/work/public-project",
  "state_root": "C:/patchloop-state",
  "sandbox": {
    "backend": "docker",
    "image": "your-prepared-image@sha256:REPLACE_WITH_64_HEX_DIGEST",
    "image_digest": "sha256:REPLACE_WITH_64_HEX_DIGEST"
  },
  "provider": "openai",
  "model": "gpt-5.4-mini-2026-03-17",
  "reasoning_effort": "xhigh",
  "context_policy": "segmented-v1",
  "env_file": "C:/private/approved.env",
  "max_cost_usd": "3.00",
  "repeat": 1,
  "limits": {
    "max_model_calls": 40,
    "max_tool_actions": 100,
    "max_accepted_mutations": 4,
    "wall_time_seconds": 1800
  }
}
```

The example is not paid execution authorization. Obtain approval for the exact
public task/source, model, credential, repetitions and invocation-wide cap first.
No remote source fetch, dependency installation, image pull/build or PR creation
occurs. Source working-tree edits and untracked files are not copied. Submodules
are unsupported. Keep generated state outside both PatchLoop and the source tree.

Read `runs[0].delivery.patch.path` for the patch and
`runs[0].delivery.public_verification.path` for the receipt (bounded check outputs,
action identities, checked diff hashes and finish evidence). `PATCH_READY` means
the existing finish conditions passed, not independently established correctness.
Failures retain their normal terminal reason and journal without a delivery.
No hidden tests, reference patch or evaluator environment belong in this request.

To explicitly resume, add `resume_run_id` from the result, keep `repeat: 1`, and
retain the identical request, public task, runtime, source path and sandbox
identity. Completed delivery recovery verifies its artifacts without re-running
the solver or checks. Live resume needs its own authorization. The initial path
does not enable probes or prepared-source descriptors; it uses the local source.

## Verify a returned regression test

When the task requires a regression test, allow the relevant existing test files
in `allowed_paths` and remove them from `forbidden_paths` before running repair.
After delivery, use the original request and the unmodified returned patch:

```powershell
patchloop repair-verify --request C:/work/request.json --patch C:/work/returned.patch --state-root C:/pt/verification
```

This command makes no model calls and does not read credentials. It creates three
separate checkouts at the request's exact base: unchanged base, base with the
submitted test files, and the complete submitted patch. Identical test bytes are
used in the latter two. It executes every original registered public check on
each checkout with the original environment, timeout and output bound. The whole
comparison uses the request's wall-time limit. Source working-tree changes are
not copied or modified. Images and dependencies must already exist.

The first version supports Python edits and additions in existing pytest files:
new top-level `test_*` functions, or literal cases added to one existing
`pytest.mark.parametrize` list without changing the function or its other
decorators. Existing cases must remain unchanged and in order. New test decorators
may be `parametrize`, `skip`, `skipif` or `xfail`. Changed imports, existing test
bodies, fixtures, helpers, classes, configuration, new files, file modes and
renames are `UNSUPPORTED`; the command never rewrites them to make them separable.
Parametrization keywords, computed added cases and class methods are unsupported.
This is structural separation, not proof that arbitrary test code has no side effects.

At least one check must directly invoke `python -m pytest` (versioned Python
executables also work). Its arguments are preserved and a sandbox-side pytest
reporter records collection and setup/call/teardown outcomes. Other registered
commands run unchanged and retain exit codes and bounded output. No extra test
targets are silently added: unselected additions are reported as missing.

Stdout is `repair-verification-v1` JSON, also stored in a content-addressed
`result_artifact`. `checks` contains all three phases, original-check summaries,
added-test outcomes, diff hashes and raw output receipts. Test file hashes,
request/patch/public-task artifacts and an append-only `dev-run-v1` journal
identify the inputs. The original patch, parsed changed paths and unsupported
reasons remain available, including when patch parsing itself is unsupported.

- `status`: `COMPLETE` means execution/recording finished, not that tests passed;
  `UNSUPPORTED` means safe separation is unavailable; `ERROR` means execution failed.
- `comparison.status`: `OBSERVED_FAIL_THEN_PASS`, `PASSED_BOTH`, `NOT_COLLECTED`,
  `INCONCLUSIVE`, or `NOT_RUN`. A positive observation requires all selected added
  tests to pass afterward and at least one to have a call-phase failure before.
- `observation` distinguishes collection errors/skips, zero collection, setup or
  teardown errors, timeout, incomplete output and invalid reports. Individual
  tests distinguish failure, pass, skip, xfail/xpass and non-execution; exception
  types and bounded failure details remain available for human review.

Even fail-before/pass-after does not establish the cause of failure, issue
coverage or correctness: `requirement_fit=NOT_ASSESSED`, `acceptance=NOT_RUN`.
Existing public failures remain in the result independently of the added-test
comparison. Repository pytest hooks and tests are untrusted observations, not an
independent evaluator. Humans should review the original diff and failure details.

The CLI's exit status indicates whether it returned a report; inspect the JSON
statuses for the outcome. Each invocation starts a new verification; there is no
automatic retry, repair, resume, submission or publication. Interrupted runs keep
their started/finished check events and artifacts without a fabricated final result.
