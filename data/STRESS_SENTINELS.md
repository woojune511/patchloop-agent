# PatchLoop stress sentinel freeze

Status: **selection and schedule frozen; stress execution pending**

This document records the preregistered three-task reliability panel and fault matrix. It is selection
evidence, not a stress-result report.

## Freeze identities

- Dataset: `patchloop-benchmark-v1`
- Dataset manifest:
  `sha256:cf608ca1a35cb270f2e4cadcf0b34912256ef1c9cd3c0757a89692f8a5fdf786`
- Stress schedule:
  `sha256:d5a3d90f8429f24b6940d4a5cb1b78a35fa34d3fe3df9937ad6c57daba23f468`
- Selection policy: `public-contract-structure-v1`
- Schedule ID: `terminal-recovery-v1`
- Seed: `20260723`
- Memory condition: `no_memory`
- Baseline source: matching `core-no-memory` runs
- Core inclusion: `false`

## Candidate boundary

Only the twelve admitted tasks in `core-same-repo` and `core-cross-repo` were eligible. Selection read
only agent-visible public contracts: task IDs, registered visible-check timeouts and mutation constraints.
It did not read private specifications, hidden tests, hidden assertions, reference patches, known-bad
patch contents, agent traces or model outcomes.

The selector applies the following rules in order and removes each selected task before the next rule.

1. Wide change surface: highest `max_changed_files`, then task ID ascending.
2. Narrow mutation surface: lowest `max_changed_files`, then lowest `max_diff_lines`, then task ID
   ascending.
3. Long visible check: highest maximum registered visible-check timeout, then task ID ascending.

## Selected panel

| Archetype | Task | Public evidence |
| --- | --- | --- |
| Wide change surface | `fusesoc-retained-parse-error-diagnostics` | `max_changed_files=3`; task ID wins the deterministic tie |
| Narrow mutation surface | `anyio-extensionless-entrypoint-worker-main` | `max_changed_files=1`, `max_diff_lines=40` |
| Long visible check | `pyfakefs-file-wrapper-io-capabilities` | Maximum registered visible-check timeout is 240 seconds |

These archetypes diversify the panel; they do not assign one fault to one task. Every selected task
receives every frozen fault.

## Fault schedule

| Fault | Trigger | Persistent state | Repetitions per task | Derived runs |
| --- | --- | --- | ---: | ---: |
| `context-reset` | Immediately after model call 10, once | `on`, `off` | 2 per mode | 12 |
| `worker-kill-after-patch` | Immediately after the first durable patch checkpoint, once | `on`, `off` | 2 per mode | 12 |
| `test-timeout` | First registered visible check, once | `on` | 2 | 6 |
| **Total** |  |  |  | **30** |

The expansion is:

```text
3 sentinels × (
    context reset: 2 state modes × 2 repetitions
  + worker restart: 2 state modes × 2 repetitions
  + test timeout: 1 state mode × 2 repetitions
) = 30 derived stress runs
```

The 30 stress runs are separate from the four memory conditions × twelve held-out tasks × two
repetitions = 96 core runs. Fault-free comparisons reuse the matching no-memory core runs rather than
creating another unregistered stress baseline.

## Freeze gate

Run:

```powershell
uv run patchloop dataset audit
```

The gate must report all of the following:

```text
complete = true
dataset_status = frozen
task_count = 25
research_task_count = 20
stress_ready = true
stress_plan_ready = true
freeze_eligible = true
freeze_blockers = []
expected_stress_runs = 30
core_expected_runs = 96
```

It also recomputes the public-contract selection and both hashes. A frozen manifest is rejected if it
has a different sentinel set or order, an incomplete rationale, a non-held-out task, a missing/extra
fault, a changed trigger/state arm, or a schedule count other than 30.

## What this freeze does not prove

The current evidence freezes dataset membership, sentinel selection and schedule configuration. It does
not prove that:

- the schedule is consumed end to end by the fault runtime;
- full context-reset semantics or the persistent-state-off arms are implemented;
- any of the 30 stress runs succeeded;
- the 96 core runs or live OpenAI campaign ran;
- persistent state improves recovery.

Those claims require separate executable runtime tests and immutable run artifacts. Until then, stress
and recovery numbers remain unreported and the outstanding runtime/campaign work is tracked in
[`docs/08-limitations.md`](../docs/08-limitations.md).
