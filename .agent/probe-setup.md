# Setup comparisons in public probes

The optional `check_setup(label, actual, expected)` global in `run_probe` compares
values from the program's constructed input before the program exercises behavior.
Use it on the actual object/settings, not a restatement of the intended input.
This addresses a failure where a merge changed a setting, but the model treated an
assertion against its intended setting as a candidate defect despite printed evidence.

## Contract

- It records type-strict equality of plain `None`, bool, int, finite float and str
  values. For example, `True` differs from `1`; `1` differs from `1.0`.
- At most 16 comparisons, labels of 1–120 characters, string values up to 256
  characters, integer magnitude up to 256 bits, and an 8,000-byte JSON report.
  Project objects and subclasses are not compared or stringified. For complex
  inputs, select concrete scalar attributes or a boolean property explicitly.
- A mismatch records both values then raises `SetupMismatchError`, a subclass of
  `AssertionError`. Normally this stops subsequent statements. A program can catch
  it and continue; a receipt must not claim that candidate code was never executed.
- Invalid labels/values or exceeded limits raise `ValueError` and leave the report `unknown`, even
  if caught or followed by a passing comparison. Threaded calls serialize the
  bounded record; this does not add worker-thread line coverage.
- `setup_checks.status` is `failed` for a recorded mismatch, `passed` when all
  recorded comparisons match, or `not_checked` for a complete empty report.
  Missing, malformed, duplicate, oversized or identity-mismatched reports, timeout,
  output-limit and uncertain-cleanup results are `unknown`.
- A normal process exit with a caught mismatch still has `setup_checks=failed`.
  A later ordinary assertion can fail with `setup_checks=passed`. The existing
  process status and exit code stay independent of setup observations.

The helper compares model-selected values and expectations. It cannot establish
that the selection covers the setup, matches the public requirement, or represents
the object actually passed to candidate code. Code can change state after a check,
run behavior beforehand, or interfere with the helper/frame. Like line observations,
this in-process report is advisory, not an attestation or a behavior verdict. No
check/report/submission gate or task-specific expected answer is added.

## Delivery, identity and isolation

The host copies the stdlib-only helper beside the read-only trusted runner and
binds its bytes and report cap in `probe_profile()`. It changes the runtime/profile
hash, without changing the container's network, filesystem, process/thread or time
limits. The installed base image needs no build. New preparations bind the new
runtime; consumed packets remain closed and cannot be resumed across this change.

The Python source executes unchanged. Its hash and raw `action_id + input_hash`
remain the existing recovery identity. A separate bounded stderr frame binds the
source and execution identity; the host validates shape/bounds and derives equality.
The existing line frame and public stdout/stderr remain separate. The host records
the public receipt in the same hash-chained journal; completed replay returns it
without another execution. Receipts predating this helper remain readable.

Both dev context policies and the fixed-candidate discovery runner deliver the
receipt in the next native function result. A compact observation distinguishes
setup comparisons from execution status and leaves `behavior_verdict=not_assessed`.
All discovery guidance modes share the helper; no new prompt-policy variant exists.
Reports remain model claims requiring public review even after a setup check.

## Validation evidence

`C:\pt\analyses\probe-setup-checks-20260919-v1` records focused/regression checks,
Ruff, both context policies' mock mutation/check/submission/isolated evaluation,
and synthetic probes on the existing pinned Docker image. No provider/count call,
old candidate execution, hidden-evaluator inspection or new paid packet is part of
this implementation. Live discovery benefit and task acceptance are unassessed.

Focused: 146 PASS/23.75s. Docker: 11 PASS/181.30s. Full regression: 2,878 PASS,
16 SKIP and six existing description-snapshot failures/2,383.77s. The new helper
paragraph explains all six; the older memory boundary and current full-schema
snapshots are updated and 11 targeted checks pass. Production code remains identical
through that resolution. Both initial and targeted receipts remain available; this
is not a claim of a second clean full run. Ruff and documentation checks pass.

## Separate live observation, 2026-09-19 KST

`C:\pt\analyses\counterexample-discovery-setup-20260919-v1` closes one new $1.20
sample at runtime `b3ea4b8b`, with the original dev-train task, fixed P10, GPT-5.4
medium and applicability-contrast-v1. Only the generic helper description changes
the initial request relative to the preceding observation; no old cases/history enter.

The model constructs a copied profile with dataclasses.replace, then compares four
properties obtained from the actual changed/plain model profiles before mapping messages.
All four comparisons and both complete serializer expectations match. Full setup rows,
compact observation, stdout and applicability feedback reach the next actual input.
The model reports no counterexample. Public review is NO_REPRODUCTION, discoveries0/1;
this narrow no-mismatch statement is supported, with task acceptance NOT_ASSESSED.

There is no mismatch opportunity, so repair-after-mismatch is NOT_OBSERVED. The
preservation input switches off field mode; behavior under the same candidate condition
but different public applicability is still untested. The report's rationale treating
field mode as the complete applicability boundary is unsupported by that pair: the
task separately qualifies the provider-supplied profile. Its joined/abridged excerpt
does not pass literal binding. Helper uptake is observed, not a causal improvement.

Six model/count calls, five searches, four reads, one probe and one report. Recorded
cost $0.1750365, cache-neutral $0.3268125, max input26,370, active153.755s/wall281.547s.
No infrastructure/resource stop; output and cleanup complete. Unused $1.0249635 is
closed. No additional candidate execution, retry/resume/replacement or private review.
The unchanged runtime reuses the implementation validation above; new documentation
checks and preservation verification accompany the observation. All 1,407 prior evidence
entries are preserved. Keep discovery guidance opt-in; the remaining selection gap
does not automatically authorize another prompt variant or paid sample.
