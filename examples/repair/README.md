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
