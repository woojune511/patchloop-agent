# Separate public conditions from the reviewed case

Date: 2026-11-01. Baseline: `3f102bf9483429f05dd6a0c89d34b838c34ff0ab`.
Status: implementation and local validation; new live work NOT_RUN.
Observed failure: [capability-aligned diagnostic](2026-11-01-capability-aligned-verification-results.md).

## Selected problem and alternatives

The latest task8 diagnostic correctly reused saved execution evidence, disclosed
unexecuted caller paths and received the corrected capability/terminal contract.
It still ended without a new observation or a sufficient original-input mapping.
Its original H-array-to-bytes conditions and helper I-array/direct-array conditions
were not explicitly compared. A direct-array helper failure was used to explain
the public report even though the earlier bytes control passed on the base.

This matters because a real helper PASS and valid receipt can support the wrong
input scope. The existing case.input string can describe either the required
conditions or the tested conditions, or mix them without naming the difference.
Execution binding checks identity/diff/return status, intentionally not semantics.
Stronger prose had already reached the model without demonstrating better judgment.

The saved plan also ended with one helper then reporting limitations. Its influence
is plausible, not established: source-supported local writer reasoning and sampling
variability are alternatives. Planning null preservation and review-trigger
consumption are working as specified; there is no evidence of a lost plan or a
host completion gate incorrectly marking the original requirement verified.

The selected change separates the two input roles inside the existing review. A
fresh review that still misstates public conditions or omits material differences
would weaken the usefulness of this representation. If delivered source genuinely
establishes that a difference cannot affect the requirement, another probe can be
unnecessary. These possibilities must remain distinguishable in a future live run.

## Minimal implementation

Fresh scope_review.cases[].input is an object:

```json
{
  "public_conditions": "Public caller receives serialized bytes using its default mode.",
  "case_conditions": "Helper calls the internal converter with a list and explicit mode."
}
```

Both strings are bounded at 500 characters. public_conditions can be null for
unknown original conditions or a separate control, with its reason
in the existing interpretation field. Never manufacture the original setup from
the helper. case_conditions names what was actually executed or is planned.
The existing interpretation compares substitutions, missing assumptions and evidence
that makes them material or irrelevant, then identifies a useful feasible observation
or a concrete stopping/blocker rationale. Existing expected_observation, disposition,
source IDs and execution IDs retain their roles and bounds.

The existing brief-plan scope paragraph is replaced to use this comparison and
assess the plan's own finish condition against the public task. No extra warning
paragraph, plan reset, review call, tool, mandatory probe or semantic finish gate
is added. A valid report can still stop immediately or disclose a concrete blocker.

Legacy input strings remain accepted by the parser and retain their exact form in
stored/projected reviews, null updates, diff transitions and replay. Fresh schemas
request only the object. Invalid annotations retain the prior review and do not
block the real tool action. No migration silently asserts that an old helper's
conditions were the original requirement. Runtime/contract identities change;
old frozen approvals are not upgraded or resumed.

The extra distinction adds at most 500 text characters per case, 2,000 across four
cases, plus JSON keys. Other row/plan/reason limits are unchanged. Both condition
statements and equivalence reasoning remain model-authored and unverified. Receipt
binding is not semantic coverage; no new input quote/source authority is claimed.

## Validation and evidence limits

Local tests cover equal and substituted conditions, unknown original setup and a
separate control, invalid bounded shapes without erasing the previous review,
legacy/new forms through null/rewrite/restart/replay, and a scripted selected probe
whose exact program and source/input/action identities reach the next request and
report. These are host transport/compatibility tests, not autonomous judgment tests.

Contract comparison uses independent baseline/current schema generation. The
intended wire-shape change is limited to the nested case input; other parameters,
ordering, limits and old frozen arms must remain intact. Historical bytes and
closed paid results are immutable. No task-specific counterexample or private
evaluator information is added to prompts or host tests.

The saved real public request was also reconstructed locally: all public task,
source, execution history, budget and saved plan messages remained unchanged.
Only the relevant system paragraph and scope-review tool schemas changed. This is
an offline delivery audit, not a newly approved diagnostic or provider invocation.

Runtime: `sha256:763e4efd4f14a7939d9ca1e01db91d770be3445da6b3642404da3ddb12e96298`.
External evidence: `C:/pt/input-comparison-local-20261101-v1/`.
The independent schema proof is `schema-proof/comparison-proof.json`
(`sha256:b2a2245163fbef341e49b32b31a6388a573cc0a21c28de7b5e5f0ca93a2a4b1d`).
The saved-request audit is `saved-public-request-audit.json`; reconstructed request
hash: `sha256:42b2b773a533ebe467dace95125b5a783a41859284daf3f9521068b51ad19640`.
Final local checks and source bindings are in `local-validation.json`, external
content-addressed artifacts and the append-only `run_dev_inputcomparisonlocal`
dev-run-v1 journal. No historical run artifact is modified.

Focused validation: 62 scope/delivery/replay tests passed in 10.219 seconds;
13 contract/planning compatibility tests passed. Ruff passed for patchloop,
tests and the relevant diagnostic modules. The full quick suite passed 1,453 tests
with one platform-dependent symlink skip in 410.343 seconds. Both submission-to-
isolated-mock-evaluation paths passed in that suite; no extra smoke run was needed.
Final document-layout checks and diff whitespace validation are recorded alongside
these results in `docs.xml` and `final-checks.txt`.
There is no new paid allocation. The next live question is whether the model fills
both sides accurately, uses their differences to choose an observation or justified
stop, and revises an inadequate plan finish condition when needed. The format alone
does not demonstrate that effect or isolate the inherited-plan hypothesis.
