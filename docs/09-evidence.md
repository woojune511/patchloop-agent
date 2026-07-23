# Implementation evidence — 2026-07-23

This is a local implementation checkpoint, not the planned core experiment result.

## Executed gates

| Gate | Command | Outcome |
| --- | --- | --- |
| Lock consistency | `uv lock --check` | pass, 78 packages resolved |
| Static analysis | `uv run ruff check .` | pass |
| Tests | `uv run pytest -q` | 37 pass, including Docker isolation tests |
| Package build | `uv build` | sdist and wheel built |
| Task contract | `patchloop task validate tasks/smoke/csv-quoted-newline` | pass |
| Docker build | pinned base, `--network=none --provenance=false`, repeated twice | stable image ID in 2/2 builds |
| Docker isolation | network, UID, read-only workspace, host secret | all pass |
| Evaluator | reference plus six bad patches on Docker | reference pass; every bad patch rejected; all `official=true` |
| Offline campaign | `patchloop evaluate --suite experiments/smoke.yaml` | 1/1 completed, 0 infra errors |
| Report regeneration | `patchloop report --experiment offline-smoke ...` | JSON/CSV/HTML and portable evidence bundle |
| Viewer routes | six ASGI route requests | all HTTP 200 |
| Portable bundle scan | username, absolute workspace, private/reference path scan | pass |

Latest bundled offline run: `run_671aa408ac4241ca`.

- SCRR: pass
- hidden: pass
- regression: pass
- scope: pass
- official: false
- model calls: 5 mock calls
- tool calls: 4
- measured active wall time: 1,144 ms

The one-task bootstrap interval `[1.0, 1.0]` is mechanically correct but not inferentially useful. It must
not be presented as benchmark evidence.

## Official Docker evaluator evidence

The pinned base image is
`python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de`.
Two network-disabled builds with BuildKit provenance disabled produced the same evaluator image ID:
`sha256:5d430c8dbf2e1222148909ed4c79c3cbf212aa25a94c8c2d0cbd0a97adfccf1f`.

| Fixture | Final run | Expected boundary | Observed |
| --- | --- | --- | --- |
| reference | `run_251d172b049e49c3` | full success | success |
| no-op | `run_8da6d410add948e4` | hidden fail | rejected |
| regression | `run_9b86d529fd57493b` | regression fail | rejected |
| forbidden path | `run_9328887b3bfc4d12` | scope fail | rejected |
| dependency | `run_e68390d517824e4b` | dependency/scope fail | rejected |
| test tampering | `run_2f57822c729348c1` | tampering/scope fail | rejected |
| public API | `run_a7771fc59af24470` | public-API/scope fail | rejected |

The machine-readable [Docker gate summary](../reports/docker-gate/summary.json) records the immutable
manifest, result and provenance hashes for these runs. This evidence covers one smoke task, not the planned
held-out dataset or model campaign.

Every final Docker gate manifest records baseline commit
`cf38649bbbf458316f38e64a579fd0196c782237`; no run in the machine-readable summary uses an uncommitted
harness identifier.

## Recovery evidence

Both automated E2E and a CLI-derived run were exercised. The run was suspended immediately after the
durable patch checkpoint, resumed, reached the hidden evaluator and retained exactly one `PatchApplied`
event. Checkpoint/worktree hash corruption is separately rejected by test.

## Open gates

`patchloop doctor` now passes with authenticated `gh`, WSL2, Docker Desktop and the pinned evaluator image;
`official_evaluation_ready=true`. `patchloop dataset audit` still intentionally exits non-zero: 1 of 23
packages exists and 0 of 6 OSS tasks is selected. No live OpenAI request or paid campaign was made.
