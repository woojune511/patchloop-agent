# A1 caller-path inference and B1 usage uncertainty

Date: 2026-10-20. Operator diagnosis, official=false, claim-ineligible. The
[closed comparison](2026-10-20-evidence-recovery-results.md) and its grades remain
unchanged. No solver, caller assessment, native evaluation or paid request ran.

## Question and decision

A1 submitted an incorrect repair; B1 stopped before its first tool action. These
are different problems. Investigating them separately matters because another
memory change cannot explain a provider response, and a provider fix cannot
establish repair quality.

The public evidence supports an A1 caller-path and verification-scope failure.
Critical source conditions were present when it selected the wrong edit. Missing
source alone is therefore insufficient to explain that decision. B1's historical
record establishes inconsistent SDK-visible usage, but cannot locate the cause
between HTTP reporting and SDK decoding. Keep the existing runtime; do not add a
fourth intervention or reopen the paid allocation from these observations.

## A1: acquired source did not establish the actual caller

The saved public caller receipt, on the submitted source-only projection, records:

`pylint src/project` -> `get_ast("src/project/__init__.py", "project")` ->
`ast_from_file(..., modname="project", source=True, fallback=True)` -> `file_build`.

The file does not exist. The caller exits 1 with F0010; this is the existing
assessment, not a new execution. In `astroid/manager.py:120-126`, `source=True`
returns through `file_build` before the module-name fallback. The submitted patch
instead changes `_spec_from_modpath`'s `PKG_DIRECTORY` conversion. This does not
repair the observed failing file-load branch. The saved profiler did not trace
every modutils call, so this finding does not claim that no resolver ran anywhere
upstream.

A1 never acquired the Pylint implementation/setup or executed that original caller.
Its added test builds `src/__init__.py` and an empty `src/project` directory, calls
`file_info_from_modpath(["src", "project"], [tmpdir])`, and asserts a namespace
specification. It has no `project/file.py`, Pylint invocation, original working
directory or observed caller arguments. It verifies a different route.

The original test was added only after the source edit. No execution established
that it failed before that edit. Static inspection predicts that the existing
namespace finder already handles this test: `ImportlibFinder` returns
`PKG_DIRECTORY` only after finding an initializer, while `PathSpecFinder` already
returns `PY_NAMESPACE` for a namespace directory. A baseline PASS remains a
prediction, not a measured result of this diagnosis.

## A1: branch counterevidence was delivered at the edit decision

The archived actual input at sequence **401**, immediately before edit decision
**403**, includes all these source ranges:

| Source condition | Lines | Implication |
| --- | --- | --- |
| `astroid/interpreter/_import/spec.py` | 130-140 | `PKG_DIRECTORY` requires an existing initializer in this finder. |
| `astroid/manager.py` | 120-126 | The direct source-file route returns before module-name fallback. |
| `astroid/builder.py` | 115-128 | It opens the given path and raises on its loading failure. |

The finder guard is also verified in a `function_call_output` inside that actual
input, not merely in a model-authored note. Nevertheless, decision 403 treats the
missing-initializer `PKG_DIRECTORY` hypothesis as the repair location, clears its
open question, and says broader discovery no longer changes the choice.
Decision 507 requests a test that would fail before the fix without measuring
that property. Decision 537 extrapolates the passing suite and helper test to
avoidance of the reported F0010.

Later transitions do remove relevant source. At input 436 the builder body and
manager's direct-return lines are absent; at final input 535 only manager line
145 remains, and the finder guard is incomplete. This could weaken later review,
but those losses occur after the initial wrong edit. The trace supports both
missing caller-condition acquisition and unsupported use of delivered source;
it does not isolate a causal effect of retention on final completion.

## B1: response-accounting failure before treatment behavior

Input count and generation use the same request hash. The count is **13,885** and
the output ceiling **25,000**. After **1,710 ms** the SDK-visible response reports
`incomplete/max_output_tokens`, zero output items, and integer zero for input,
output, cached, reasoning and total tokens. The diagnostic observes these values
before compatibility defaults. This establishes the count inconsistency, not
that 25,000 tokens were consumed or that the configured context was exhausted.

No tool action ran. B1 cannot measure retrieval use, caller reasoning or the
three interventions' effect. Billing remains UNKNOWN. Neither a returned zero
nor the reserved USD 0.12291375 is a settled charge. The old HTTP usage fields and
request ID were not captured, so existing records cannot decide server versus
SDK attribution. Commit `d89874d0` adds bounded
[HTTP/SDK diagnostics](../../.agent/provider-usage-diagnostics.md) for future
parsed failures; it neither recovers the old response nor fixes the remote cause.

## Local verification and next question

Two frozen helper programs were prepared: the exact submitted test AST against
the baseline resolver and against the submitted resolver, with branch tracing.
The existing public Python sandbox failed preflight because Docker's Linux
engine pipe was unavailable. **Both helper executions are NOT_RUN.** No Docker
startup, image pull/build, substitute host execution or evaluator retry occurred.
Image presence itself was not established. This observation is separate from
the original experiment's settled local evaluation.

The evidence packet is `C:/pt/a1b1-diagnosis30/`. `diagnosis.json` binds actual
input coverage, public decisions, the saved caller trace and B1 counters; its
SHA-256 is `31777a30e8264cc30f1764f67bd319d5ebbcd9645705a5ec606d7326a3e67052`.
The hash-chained `run_dev_a1b1diagnosis30` journal preserves the attempted local
preflight and its cause. Sixteen frozen comparison files, including nine verified
journals, retain their recorded hashes.

The next useful check is the two local helper variants when Docker is available:
does the proposed regression distinguish the edit and enter its changed branch?
Then assess the existing B mechanism, not a new prompt: can a declared, fixed
original-caller before/after comparison correct A1's unsupported conclusion?
`reproduction_review` separates declared probe evidence and helper probes; it does
not independently infer test coverage from a general suite PASS or force the model
to choose the original caller. A1 is the pre-change control, so its failure does
not establish that B fails. Existing mocked contract tests can check that
separation, but cannot establish model uptake or repair success.

Documentation and existing evidence-recovery contracts: **17 passed in 12.22s**,
including submission through isolated mock evaluation. Ruff and `git diff --check`
passed. These mocked checks do not substitute for the two unexecuted Astroid helper
programs. No new tests or full-suite run were needed for this documentation-only
diagnosis; the four previously recorded timing failures remain unresolved.

No runtime policy, transition, two-reference limit or budget changed. No paid
follow-up is queued; the closed allocation cannot be resumed or retried.
