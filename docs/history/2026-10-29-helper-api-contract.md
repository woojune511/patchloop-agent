# Shared helper API contract and precise correction feedback

## Material Passport

- Date: 2026-10-29. ARS experiment-agent, implementation and local verification.
- Starting checkout: `72c46372`; mutable dev-head, official=false.
- Scope: shared helper API descriptions, bounded validation, concrete error
  feedback and preservation through the next model request and recovery.
- No paid provider, real token-count endpoint, benchmark or Docker run.
- Status: implemented; local validation only. Live repair improvement is untested.

## Observed defect and reason for selection

The [clean-start follow-up](2026-10-29-observation-opportunity-fresh-results.md)
failed before a valid original invocation: the first helper omitted two arguments
to check_setup; after correcting them it supplied seven input roots against a
maximum of four. Both actual acquisition attempts were consumed. The first-only
description had replaced the ordinary text and dropped the setup signature. Neither
description explained the path-count limit. The runtime returned a generic settings
error, hiding the offending field and its actual/allowed count.

This prevented the experiment from testing its intended post-reproduction
observation policy. The model did fix the first error when it received the traceback;
it is not evidence of ignoring all feedback. The selected intervention repairs a
specific host/API inconsistency, rather than increasing budgets or adding a
task-specific repair hint. Complete API guidance may still be insufficient for a
model to construct a valid reproduction or choose a correct repair.

## Implementation

`patchloop/sandbox/probe_api.py` is a small stdlib-only source for API parameters,
availability, limits, setup binding, observed-target settings validation and bounded
error records. The ordinary and first-reproduction descriptions use the same setup
and observer paragraphs. Actual setup scalar/count limits refer to the same values.
The first description is 3954 characters with the default environment paragraph,
below its existing 4000-character control. Ordered tool parameter schemas remain
unchanged; description snapshots were updated only for the intended text.

Fresh helper and original programs run the existing compile/lexical preflight plus
checks on definite direct host API calls. Missing setup arguments, extra/unknown
keywords and literal count overflow produce `/python_source` errors carrying source
hash, authored line, API, parameter and missing-argument/count details. Alias calls,
argument expansion, shadowed names and dynamic namespaces are not resolved by this
check. It never executes submitted code and does not prove target nonexecution.

The injected setup wrapper uses the same binding rules, retains the actual
`inspect.signature(check_setup)` signature and leaves comparison behavior unchanged.
Dynamic binding errors are returned as bounded `setup_checks.api_error` diagnostics.
Malformed report types, wrong request identity and invalid comparison rows remain
UNKNOWN without exposing an unbound API error or raising a host parsing exception.

Fresh observer channel v11 invokes the same trusted settings validator. An oversized
dynamic path list now reports `observed_target.input_paths: received 7 items; maximum 4`
through the existing stderr result. It retains v10's exact typed request-phase fields.
The new message is not used as classification evidence. A target's own TypeError or
a setup error after a recorded target call cannot erase target entry or certify repair.

The shared source is copied into the existing trusted read-only mount and bound by
`helper_api_hash` in the probe profile. Fresh observer code is 7292 characters; the
longest entrypoint plus optional call-path hooks is 7746, below the unchanged 8K limit.
Old v1-v10 generated programs retain their byte identities. No runtime fallback
silently substitutes a missing validator; local test launchers inject the same API.

## Feedback, budget and recovery

The local scripted adapter exercises both a statically rejected setup call and a
dynamic path-limit failure. Each concrete error appears in the next counted and
dispatched model input, followed by a corrected original call and explicit stop.
The static error uses `helper_program_error.api_error`; the dynamic settings error
uses precise stderr plus existing typed phase evidence. Neither is only buried in
an operator log.

The tests crash after a settled action and resume. Counts remain three responses,
three counts and three tool actions, with exact counted/sent inputs and summed
synthetic costs inside the cap. Static rejection consumes a request-error slot and
no actual original dispatch; a dynamic failure consumes its actual dispatch.
Completed action recovery does not refund counts/cost or run the target again.
Changing arguments under the same action ID remains a conflict.

Correction success establishes request validity and, in the controlled fixture,
baseline reproduction. It does not discharge current-candidate repair verification.
No acquisition, helper/protocol-correction, output, dollar or time allowance increased.
Stored UNKNOWN evidence is not retroactively reclassified by the new description.

## Local evidence and limits

- Final focused API selection: 161 PASS in 42.162 seconds, including next-request delivery,
  frozen-program identity, trusted source binding and original-obligation controls.
- A shared-context review found an error-frame type-check ordering defect; it was
  fixed before handoff. Additional runtime/setup/contract checks: 65 PASS, including
  list/dict error values, mismatched request identity and malformed comparison rows.
- Owner integration: 73 PASS and one opt-in Docker test skipped in 69.436 seconds.
  These use controlled local fixture programs and mocked container launch/isolation,
  not a real Docker sandbox or a benchmark repair.
- Final quick selection: 855 PASS in 115.437 seconds, including the five documentation
  checks and isolated mock evaluation. Ruff passes for `patchloop`, `tests` and the
  changed Docker launcher. A later equivalent conditional flattening for Ruff was
  covered by the final focused selection; no behavioral change followed quick.

Commands (all local and offline):

```powershell
uv run --locked --offline pytest @tests/helper-api.txt -q --basetemp C:/pt/tmp/api29focusfinal --junitxml=C:/pt/tmp/helper-api-focus29-final.xml
uv run --locked --offline pytest @tests/quick.txt -q -n 4 --dist loadfile --max-worker-restart 0 --basetemp C:/pt/tmp/api29quickfinal --junitxml=C:/pt/tmp/helper-api-quick29-final.xml
uv run --locked --offline ruff check patchloop tests docker/probe_runner.py
```

The initial quick run found seven stale description snapshots/normalizers. Updating
the intended current text preserved ordered parameter schemas and frozen-arm hashes.
Running three complete touched test files also exposed eleven old fixture assertions:
their corresponding production functions were unchanged from HEAD. The fixtures now
provide the current completion interface and verify current annotation rejection,
while retaining frozen-arm checks; all eleven cases passed in 1.91 seconds.
A whole-directory Ruff sweep additionally included six existing generated fixture
files under the untracked `.pytest_tmp_finish_reproduction/`; those files were left
untouched. Validation uses the guide's source/test scope plus the changed launcher.

The earlier helper description and complete-input error fixtures are positive controls;
dynamic or shadowed calls, actual target exceptions, post-target setup errors,
malformed receipts and recovery conflicts are negative controls. Two shared-context
workers implemented bounded runtime/preflight pieces and a third checked real request
delivery/recovery. Parent review corrected the parsing boundary and inspected the
combined source; this is not blinded model or repair-effect evaluation.

Evidence files remain outside the repository under `C:/pt/tmp/`:
`helper-api-focus29-final.xml`, `helper-api-quick29-final.xml`,
`helper-api-edge29.xml`, `helper-api-runtime29-v1.xml`,
`helper-api-integration29-v1.xml`, and `helper-api-feedback29-v3.xml`.
Historical run records and prepared trial manifests were not modified.

## Decision and next question

Keep the common contract and concrete error feedback. Local evidence supports
consistent API guidance, bounded rejection, actual feedback delivery and preserved
recovery semantics. It does not show that a live model repairs F0010 or that the
post-reproduction observation policy is useful.

The next live question is whether the model can acquire the original failure with
these corrections, then choose useful observation and repair under the same limits.
That would be a new bound invocation; prior allocations remain closed. Do not add
automatic retries, erase unknown obligations or raise limits to turn these local
controls into an apparent successful repair.
