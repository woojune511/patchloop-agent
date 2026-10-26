# Request validity and correction continuity

Status: implemented and locally validated. No paid continuation.
All runs are official=false, claim-ineligible. Baseline: commit
`2068edee4d0845c05b450e24a724df203f9539af`, tool surface v61. Current tool surface
v62 binds the changed contracts. Runtime identity is captured with validation.

- Runtime: `sha256:9632249097a22a6e8d8e63adf5df3d5000510f9e7da778360341afc9353799bd`.
- Default surface: `sha256:f3c479d9325d34be7679d66f95f909977f657721bb2188abb507b4d2e2cc0e0b`.

## Problem and decision

The closed [completion-feedback pilot](2026-10-26-completion-feedback-live.md)
spent USD 0.843607950 with 33 reads/searches, one preflight-rejected probe and no
applied edit or target execution. The [follow-up analysis](2026-10-26-completion-feedback-analysis.md)
identified three request defects: symbolic diagnosis offered without pending
diagnosis, parallel generation at a single-edit gate, and two rejected new-text
bodies missing after the correction input crossed an encrypted-size boundary.
Old anchors were present. Six initial inspection actions had also released the
original-acquisition stage without an execution.

These defects block the first meaningful behavior/repair experiment and recur
through multiple stages, so fix their contracts before increasing output or the
total cap. Missing drafts plausibly increase reconstruction burden; this change
does not establish that they caused all 25K correction output to be spent without
a tool. Model reasoning efficiency and a wrong repair hypothesis remain possible
separate obstacles. A live continuation that still exhausts output with the drafts
present would weaken the sufficiency of this intervention.

## Changes

- General fresh probes accept null call_path; a pending diagnosis has its own
  small focus schema. Original acquisition permits a new original program only,
  with no replay, symbolic path, judgment correction or helper-case selection.
- Provider parallel generation requires room for a read batch at the actual gate.
  Count and dispatch share the same flag. Other actions retain the single-call
  validator; the compact repair prompt states that rule explicitly.
- A rejected edit batch keeps up to two complete argument objects within 32,000
  canonical UTF-8 bytes, bound to origin turn/action, input hash and current diff.
  Explicit omission reasons replace truncation. The same packet survives journal
  recovery, gate-guidance refresh and compact segment replacement. Stale-diff
  bodies are withheld. The model must emit a new single action; normal anchor,
  scope and execution checks still apply, with no draft-derived source or PASS.
- Fresh bounded acquisition uses six preparation actions, then request-or-stop,
  retaining two actual dispatches and two rejected-request bounds. Preparatory
  reads reserve one original dispatch and its new-case completion route. Legacy
  registration shapes preserve their shared-six limit. Stored response validation
  uses the recorded fresh-mode flag, not a newly inferred rule. Budget release and
  uncertain execution never become verification credit.

No output ceiling, overall cap, model, task data, retry count or evaluator changed.
Runtime contracts: [request continuity](../../.agent/request-continuity.md).

## Local evidence

Evidence root: `C:/pt/request-continuity-v1`; append-only hash-chained journal
`runs/run_dev_request_continuity_local.jsonl`. `validate.py` records commands,
runtime/surface identities, output CAS hashes and durations; JUnit files retain
case outcomes. `validation-summary.json` is a convenience copy of its CAS record.

| Executed local check | Result | Output CAS hash |
| --- | --- | --- |
| `pytest @tests/request-continuity.txt -n 4 --dist loadfile --max-worker-restart 0` | 70 PASS, 28.95 s (30.361 s command wall time) | `sha256:9a970dc4be1cbebd056b74c19f7e7448e2e60a1cb979d62030ab768ab1febad5` |
| `pytest @tests/quick.txt -n 4 --dist loadfile --max-worker-restart 0` | 450 PASS, 37.81 s (39.248 s command wall time) | `sha256:16dc16416af8748148f1c01bba6261e5079505e7ce2f679f60ee56a85452327c` |
| `ruff check --extend-exclude .pytest_tmp_finish_reproduction .` | PASS, 0.448 s | `sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |

All commands use `uv run --locked --offline` and unique external basetemp paths.
The core/quick counts overlap and are not independent samples. The core includes
real local mock submission and isolated evaluator PASS (safety NOT_RUN); the
deterministic provider fixtures separately test rollover and both recovery points.
No paid provider call, Docker launch, image pull/build or Astroid target execution
occurred. Existing user AGENTS bytes and temporary files were preserved. Ruff
excludes that pre-existing generated checkout tree, not project source.

`reproject_pilot.py` reads only the original public rejected calls and checks their
exact retention and compact projection. Both drafts fit: 6,605 argument UTF-8
bytes, no omission and no execution. Projection summary CAS:
`sha256:7af58132d9e8622d6f8c47b5fe52d5833777baf04a7c9cfa8f9e835f204a1785`.
The original source journal hash remains
`sha256:bf24219f42ed3a851e2da397c06c10b3bb3286d98070ba52f0edcfcd3d0961eb`.

The initial integration regression exposed a second drop point: refreshing a
pending protocol correction rebuilt only its guidance. The correction now carries
the original packet through that refresh. The rollover/restart fixture verifies
that no rejected edit starts and exactly the corrected single edit executes.
Schema inspection additionally found inherited helper-case fields in the narrowed
original schema; those now expose only null/false, matching gateway admission.
Earlier failed local iterations remain in the evidence journal. Two stale test
fixtures were updated to the current host-bound issue/call adapter and existing
repair/finalization segment transitions. Current schema pins and the diagnostic
control's removed-field description follow the v62 shape; frozen arm pins and
historical reports were not changed.

## Interpretation and remaining question

This is a known-contract repair with deterministic local mechanism tests, not an
agent-quality comparison. Local fixtures can verify exact draft delivery, correct
stage admission and resource/recovery behavior. They do not show that a real model
will reuse the draft, produce a correct original call, or resolve F0010. Prior paid
allocations remain closed. A separately scoped live solve can test original-call
execution, first applied edit, current original behavior, public regression and
independent acceptance separately under the same selected caps.
