# Task8 unchanged public regression: base assertion failure, candidate pass

Date: 2026-11-01. CLOSED, operator-selected and provider-free; official=false,
claim-ineligible. No new solve, private evaluation or target retry.

## Question and decision

The [latest task8 attempt](2026-11-01-completion-reserve-task8-results.md) submitted
a buffer conversion patch after its base OL-bytes approximation already passed.
Its new regression had candidate-only evidence and truncated public stdout.
This matters because successful checks on a different input can leave the reported
failure unexplained, even when the patch has an observable effect.

The user authorized the smallest follow-up: execute the submitted regression
unchanged on original production code and the submitted production patch. An
assertion failure followed by PASS supports the patch's effect on that case;
PASS/PASS would make the test nondiscriminating, while collection/setup errors
would make the comparison inconclusive. Neither transition proves that the new
case corresponds to the original issue or that its expected behavior is required.

**Observed: one collected test, assertion FAIL on base, PASS on the candidate.**
The existing comparison facility works for this question. Keep it and the advisory
requirement boundary. The next question is why repair selection shifts to a
different input representation after a passing approximation, without a public
source or comparable-execution bridge. This result does not justify another
finish gate, more calls, or mandatory paired tests for every edit.

## Frozen scope

- Execution HEAD: `2517ce8427bf4411f2900bed7b31906b70d0fe43`.
- Runtime unchanged from `a1833855`:
  `sha256:c455b38f9be2d1845b7cae4609536190a665b4ab5c8d0e0f6156b9b72b52773c`.
- Public task: `tasks/dev-train/current-dev20/8/public.yaml`, pydicom1413.
- Saved run: `run_dev_abbcd884047f44be`; submitted patch:
  `sha256:52f7cc595dc7547f70b4d81a736812243cdb3fb329fc71afc25943c5101294da`.
- Original base: `f909c76e31f759246cec3708dadd173c5d6e84b1`.
- Exact target:
  `pydicom/tests/test_filewriter.py::TestWriteDataElement::test_write_OL_buffer_values_match_bytes`.
- Existing `run_tests`, suite `public-pytest`, comparison `original_base`.
  Two isolated clones receive identical submitted test-file bytes. Only production
  code differs. No test input, expectation, ordering or assertion was changed.
- Selected test-file hash:
  `sha256:c162b3ad32d8a2e0fc4573f967c64b912dfa4f98d5ed9a88f75418693d62d15e`.
- One comparison / two sandbox executions, 600-second total bound, registered
  300-second per-check timeout. Same existing pinned task image on both sides:
  `sha256:ce1687a82b9b9eaa4d93763ac8405105c1eb8c5123f295f0aa15d3252c10e39d`.
- Zero provider calls, zero new API cost, zero independent evaluations. No credentials
  loaded, Docker startup, image pull/build, or modification of the saved workspace.

The question, source identities, alternative outcomes and limits were saved before
target dispatch. The first external recorder rejected its manifest destination
because it was outside that recorder's ArtifactStore root. This happened before
any journal or target execution. `compare.py` is retained; `compare_v2.py` corrects
only the recorder root, and its manifest binds that preparation failure. There was
one executed comparison, not a retried test.

## Exact observation

| Phase | Collection | Setup / teardown | Test body | Exit |
| --- | --- | --- | --- | --- |
| Original base with submitted tests | 1 | PASS / PASS | Assertion FAIL | 1 |
| Submitted patch with identical tests | 1 | PASS / PASS | PASS | 0 |

Base fails at `test_filewriter.py:583`:

```python
assert isinstance(elem.value, bytes)
```

Expected predicate: `True`. Actual: `False`; pytest reports the stored value as
`[1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7, 0, 8, 0, 9, 0]`.
The exception is `builtins.AssertionError`, not an import, collection, setup or
teardown failure. The retained output establishes that it is not bytes; it does
not independently print the object's exact Python class.

This is the first loop iteration, `bytearray(bytestring)`. Base stops at that type
assertion, before this input's value and writer comparisons or the second
`array.array('H', range(1, 10))` iteration. Do not claim those later base assertions
or writer failures were observed. Candidate completes both inputs, checking byte
equality and equality to the bytes reference under implicit and explicit
little-endian element encoding.

Both structured reports are complete and untruncated, without collection errors,
skips, timeout or cleanup uncertainty. Sandbox durations were 10.232s and 4.994s;
the whole comparison took 20.171s. These are execution timings, not speedup evidence.
Exact node collection is established for this follow-up; it does not retroactively
restore the missing node telemetry from the original broad public check.

## Original-task connection remains unverified

The public issue passes the bytes result of `array(...).tostring()` into `add_new`
and describes a later `save_as` error. The submitted regression instead passes
bytearray/array objects into `DataElement` and uses the element writer helper.
The earlier base bytes probe at sequence54 already reported OL and OB writes as
successful. Its saved receipt was reused without replaying that probe.

The unchanged regression necessarily builds and encodes bytes reference elements
inside each phase. This is not a new exact-original-input reproduction. The
manifest's reuse count of zero refers to additional original-bytes probe runs,
not to the reference encodes that are part of this test.

The observed FAIL-to-PASS rules out a no-effect patch or PASS/PASS for this selected
test. It leaves original-input correspondence and the public basis for the new
test's expectations unresolved. A plausible ancillary buffer behavior is not, by
itself, the reported defect. The original issue's incomplete `indexData`, dataset
and sequence setup also prevents treating the earlier approximation as exact.

The next diagnostic should preserve the reported bytes representation and public
caller while locating the condition that distinguishes the failure, or establish
that link through public source. Repeating buffer successes would not answer that
question. No new paid diagnostic or source change was performed here.

The tool reports `requirement_fit=UNVERIFIED`, `original_requirement_credit=false`
and `counts_toward_completion=false`. Operator selection does not demonstrate that
the agent would choose this comparison or revise its hypothesis autonomously.
No private assertion was inspected; the exact independent FAIL cause is not
attributed by this result.

## Evidence and validation

External append-only journal and artifacts: `C:/pt/task8-test-pair-20261101-v1/`.
Audit verifies identical test-file bytes, original/candidate identities, exact
node phases, complete output, and unchanged saved source, prior journal and
closed operator records. No runtime implementation was changed.

- `manifest.json`: `sha256:525f50df09ce1247a39896c24760f2a88727b1d90034537b75a1694787f44e47`.
- `result.json`: `sha256:8be3ea4935938ffbff3d6c2a68c7ee5660f18eae06d2fe46517e084ac8316c83`.
- `audit.json`: `sha256:f97a70e51541169d60bbc6ef5dad52a6a889197c744f5b274eb8a1fd6c707d05`.
- Baseline raw/report receipt: `sha256:7e2b96988dcd7445e3e273ed2ba07a137c2867d0a5d44378fb66a0f17e9536d4`.
- Candidate raw/report receipt: `sha256:303214afc337eac2aeb829aad55f0d3dde915ce3c78bfcef76b8164d24e1648c`.
- Audited execution journal head:
  `sha256:c1f2f75662d2eabc024abde3c5e3237f01d7c8081d819713014ead8fc35415f9`.

Documentation validation and the final commit are recorded separately in
`result-validation.json` and `result-commit.json`. The runtime's previously passing
focused/fast suites and isolated mock evaluation were not rerun for this
documentation-only change; no new repair-quality claim follows.
