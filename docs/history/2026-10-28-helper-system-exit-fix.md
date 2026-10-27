# Helper SystemExit configuration compatibility

Status: implemented and locally validated; no paid collection.
Official=false. No new paid model or benchmark probe is authorized or executed.

The [model comparison](2026-10-28-first-reproduction-model-results.md) exposed a
specific helper defect: full constructed a valid original request but supplied
`expected_exceptions=(SystemExit,)`. The wrapper rejected that setting before both
target calls, although it already captures SystemExit automatically. Its description
did not disclose the Exception-subclass restriction. This avoidable API mismatch
blocked all reproduction evidence and is the reason for the change.

## Change and boundaries

Fresh invocation v8 accepts Exception or SystemExit subclasses in the existing
four-item tuple. Only the configuration predicate changes; SystemExit capture,
actual exit code, per-call streams and target-entry recording are unchanged.
Ordinary Exception observations still match exact listed types. BaseException,
KeyboardInterrupt, GeneratorExit, instances, strings and malformed/oversized tuples
remain invalid. No unexpected exception becomes a successful observation.

The first-original and general descriptions share an explicit contract stating
allowed classes, exact matching, automatic SystemExit capture and the distinction
between an observed result and task success. No extra tool, retry, state or budget
is introduced. Parameter schemas and diagnostic-processing requirements stay fixed.

V1-v7 observers remain byte-exact. V8 is a fresh observer transformation rather
than an edit to the common legacy source. V7 and v8 share the target-phase and
canonical comparison readers, retaining exact binding/trace channel equality.
Surface v67 records the API change; this is a serialization/replay boundary, not
a new runtime activation process. The largest entrypoint plus optional call-path
hooks produces a 7,998-character observer, within the existing 8K allowance.

The separate positive-processing gap is unchanged: a control call's output does
not prove that the original directory processed its file. This fix is not evidence
of F0010 reproduction, live-model correction, repair gain or isolated acceptance.
The preceding comparison remains closed and its saved v7 failure is not rewritten.

## Local validation

The focused owner selection passed **89 tests in 28.176 seconds**. The owner tests
execute trusted local fixture targets with network/model/Docker absent; they cover
automatic/explicit SystemExit equivalence, subclasses, strict ordinary exceptions,
invalid settings before target entry, frozen legacy fingerprints and size bounds.
They also retain fixture/output isolation, pre-target obligation accounting and
same-call diagnostic behavior. Current description goldens change only where the
shared helper contract is intentionally updated; diagnosis-stage descriptions and
parameter schemas remain fixed.

Quick covered **594 cases in 190.914 seconds**: 587 PASS, including isolated mock
evaluation, and seven stale current contract/description hashes. After independently
confirming that API schemas differ only in the intended helper description and that
reverting the v67 contract fields recovers the old surface hashes, those current
pins were refreshed. Their seven focused reruns plus five documentation checks
passed (12 total). Four additional surface-identity owner cases passed in 0.98s.
Historical FROZEN_ARM hashes remain unchanged. Ruff and diff checks PASS. The only
subsequent runtime edit was a lint-only line wrap; no extra full suite was needed.
This is split validation, not a claim that the original quick invocation was green.

Local receipts and JUnit hashes are recorded outside the repository in
`C:/pt/helper-system-exit-local-v1/runs/run_dev_helpersystemexit.jsonl`.
No model credentials, provider dispatch, Docker benchmark run or new paid comparison
was used. Positive target-processing design and real-model recovery remain unverified.

Implementation baseline: `84db3452b2f4198ebcf16bfc1d5d19315fec6f95`.
Initial local test runs exposed test-fixture path/import mistakes and two expected
current-description golden changes; these were corrected before final validation.
No provider or target benchmark execution occurred in those failed local checks.
