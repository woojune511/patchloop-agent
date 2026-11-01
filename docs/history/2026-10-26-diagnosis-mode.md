# Diagnosis mode schema and actionable field correction

Date: 2026-10-26. Follow-up to the [closed pilot](2026-10-26-diagnosis-request-live.md).

## Material Passport and problem

- Origin: academic-research-suite / experiment-agent, authorized implementation and
  bounded local validation; version `diagnosis-mode-local-v1`.
- Evidence: implemented and locally tested; `official=false`, `claim_eligible=false`.
- Baseline commit: `171feeb772b0d9ee0c7f541e90be16136c586d4c`.
- No provider call, Docker launch, Astroid execution or independent target acceptance.

The last live model selected symbolic focus/watches but populated question and
purpose. The delivered description required null, while the common schema still
allowed incompatible values. Admission rejected before source construction and
reported only a root-level replay/source error, naming fields already null. No
diagnosis executed; the original F0010 remained after one repair. This repeated
pre-dispatch bottleneck prevented measurement of useful diagnosis and repair.

The host already knew the pending workflow stage. The selected intervention exposes
that stage in the existing tool contract and makes rejected fields actionable.
It is a contract correction, not evidence that description length caused output
exhaustion. Wrong focus, uninformative observations, ineffective repair and funding
limits remain plausible later failures.

## Implementation and preserved boundaries

- `runner.py` selects the pending mode from `needs_path_diagnosis` before model
  request preparation/counting. `dev_tool_schemas` defaults to the old generic path.
- In that mode, run_probe requires symbolic call_path and fixes question,
  python_source, replay_action_id and purpose to null. The model selects focus and
  watched public functions/fields. Saved-case creation fields are absent. Current
  turn-decision or thin-policy memory metadata is attached after this projection.
- A short mode-specific description replaces helper/new-original instructions.
  The recorded live description had 10,588 characters; the new one has 805. This is
  a character measurement, not observed token, latency or cost savings.
- Admission lists exact incompatible paths with required null/false values.
  Existing correction receipts compare these fields. It never silently changes
  the submitted original program, inputs or oracle to accept a request.
- Review found secondary replay/case preparation could overwrite the first
  diagnosis error. It now runs only without an existing preflight error. Returned
  gateway feedback, durable rejection and result replay cover all three probe policies.

The tool name, frozen original binding, source/watch construction, raw action/input
hash, canonical admission/recovery and legacy recovery remain unchanged. The
one-request-correction/one-actual-diagnosis limits and all cost, output, action and
time settings remain unchanged. No new retry policy or persistent state is added.
See the [current contract](../../.agent/repair-path.md).

## Local evidence

The saved public request `call_Fl8sjLNnHp386RruaHYlLI5C` was inspected against its
unchanged saved candidate. No task source was imported or executed.

| Control | Result |
| --- | --- |
| Unchanged saved mixed request | Rejected at `/question` and `/purpose`, before construction |
| Clear only those two fields | Static host construction PASS; same function/field choices and original root/call |
| Ordinary schema comparison | 9/9 byte-identical to baseline across three probe policies and current/brief/thin configurations |
| Current/thin pending schemas | Null-only fixed fields, required symbolic call_path, correct metadata |
| Error feedback at gateway | Primary invalid-field paths survive replay/case preparation; rejection consumes no execution |
| Scripted tiny integration | Rejection, same-case correction, one diagnostic, linked repair, original mismatch-to-match, checks, finish, isolated mock evaluation |

The integration deliberately returns one schema-incompatible fake-model action to
exercise host validation, then corrects only question/purpose. It verifies the
same case/candidate link, unchanged raw inputs, exact corrected-field receipt and
one diagnostic dispatch. The complete sequence uses four probe executions across
baseline, wrong-repair replay, diagnosis and repaired replay; finish reuses the
last success. Mock safety is NOT_RUN.

- Focused: 96 PASS in 43.91 seconds pytest / 45.373 seconds command wall time.
- Ruff: PASS.
- Quick integration: 366 PASS in 72.17 seconds pytest / 73.608 seconds command wall
  time, including isolated mock evaluation.
- Full regression, Linux CI, provider schema acceptance, model uptake, actual-target
  tracing and F0010 repair: NOT_RUN.

Initial focused validation passed 93 tests. Source review then identified the
secondary-error overwrite and added three gateway cases; the focused suite was
rerun for that change. The static audit's first adapter incorrectly forwarded an
unsupported deadline argument to the compile-only binder; the adapter was corrected
and the saved-request control passed. A Ruff line-length issue was also corrected.
Failed and successful receipts remain separate in the external journal.

One native reviewer shared task context and inspected source only. Its error-ordering
finding was fixed and rechecked; it did not rerun tests or provide blinded/model
effectiveness evidence.

## Decision and evidence scope

The local results support agreement between the delivered pending-mode contract
and runtime admission, actionable correction, and preserved ordinary contracts.
They do not show that a live model selects useful functions, interprets the trace
correctly or repairs F0010. A future live test should keep the previous budget
conditions and measure admission, dispatch, trace return, hypothesis revision and
original-call repair separately. This record authorizes no paid continuation.

Artifacts are under `C:/pt/diagnosis-mode-local-v1` in hash-chained dev-run-v1 state.
`saved-request-control.json` hash:
`sha256:64a88ab7dab65eb3f0b4aa4b9b6e8eeb3d8180b8c072ada6a7ff2909190ae89a`.
The final closeout binds source, tests, documentation, validation and commit hashes.
Closed historical evidence and unrelated working-tree changes remain preserved.
