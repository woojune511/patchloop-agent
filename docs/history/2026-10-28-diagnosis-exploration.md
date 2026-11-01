# Let the model explore before observing the original call

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: authorized implementation and local validation
- Origin Date: 2026-10-28, Asia/Seoul
- Verification Status: local mechanism validation; live repair gain unmeasured
- Version Label: diagnosis_exploration_local_v1
- Scope: dev-head, official=false, claim-ineligible

## Problem, evidence and decision

The user requested caller/test exploration and model-selected observation timing
within the existing total budget and original-failure verification obligations.
The [ruleless diagnosis fix](2026-10-28-ruleless-path-diagnosis.md) made the existing
structured diagnosis reachable, but its one-read quota and focus-selection-only
guidance still constrained multi-file investigation. Its context projection also
discarded retained source bodies outside the changed file, even when they had
already passed public-source and retention checks.

The [saved repair trial](2026-10-28-post-reproduction-repair-results.md) had seven
searches and three reads, so lack of all exploration is not the diagnosis. It failed
to establish the caller's fallback/traversal behavior before editing. The later
[processing comparison](2026-10-28-file-processing-results.md) showed file omission
upstream of the edited builder. This motivates removing an arbitrary exploration
restriction; it does not prove that more reads would have corrected that run.

The known requirement is choice inside a bounded workflow, not more global
resources or a prescribed list of files. Model misunderstanding, unhelpful searches
and the later edit cap remain plausible independent limits. No causal model
comparison or improvement claim is made in this implementation.

## Change

Pending call-path diagnosis now permits another registered public read/search
while its next action fits the shared budget. Reads remain one action per response;
there is no separate per-diagnosis read quota. Durable read action IDs and normal
run counters remain, including through recovery. The model may inspect callers,
callees and related tests, or choose the original-call trace immediately.

Every optional read preserves the current minimum route: diagnosis, a still-missing
repair anchor, mutation, original replay, required checks and finish. It also keeps
an unused diagnostic request correction. Reading arbitrary caller/test source is
not assumed to provide an editable anchor. Cost admission uses this successor
count; role-aware reservation also keeps the anchor response and pending diagnostic
execution time. A rejected request has no target-execution time. The model receives
the current reserved counts and available exploration estimate, qualified again
against money and time at every action.

Only this exploration quota changes. One actual diagnostic execution and at most
two rejected diagnostic requests remain. Unknown execution cannot be retried;
changing call IDs cannot refill it. The original program, failure declaration,
identity and comparison remain fixed. A complete diagnosis is still needed before
another mutation, and original replay and required checks still govern completion.
Reading a test does not run it. No shell, new source scope or benchmark-specific
repair hint is introduced. Global response/action/edit/context/output/cost/time
limits are unchanged.

Diagnosis retains all already bounded public repository source bodies, including
observed callers and tests, rather than filtering them to the changed file.
Already registered dependency callers retain a separate read-only source/provenance
field through normal context construction and diagnosis/repair projection. This
reuses their existing bounded pool and keeps them outside edit evidence, including
when repository and dependency paths collide. Global counted-input limits remain
authoritative; the repository and dependency retention pools are not claimed to
share one combined character cap.

Automatic dependency registration is outside this change: ordinary run_dev does
not yet derive a source catalog from its prepared caller dependencies. Existing
diagnostic gateways with registered scopes keep that access; an unregistered
gateway gains none. That source-access gap is distinct from exploration timing.

## Local validation and limits

The focused selection is `tests/diagnosis-exploration.txt`. It covers sequential
caller/test reads, recovery of the same read action, preserved refutation and one
linked diagnosis under canonical and null-rule observations. A scripted runner
checks actual provider input, including compact inline and native source delivery,
and confirms that reads consume model turns. Resource controls check repeated
affordable reads, closure at count/cost/time boundaries, missing-anchor retention,
request correction, original replay and unchanged completion restrictions.

Evidence is stored in `C:/pt/diagnosis-exploration-local-v1/` as a hash-chained
dev-run-v1 journal and separate validation report/receipts, with baseline
`6f709ef33d86d5807b4298a37cc67e393c93c66e`. Exact commands, source and JUnit hashes,
test results and any failed attempts are recorded there.

The final focused selection passed 68 tests in 23.85 seconds. Quick passed 663 and
failed seven in 85.50 seconds: five prompt-length assertions, the changed current
prompt identity, and a diagnostic-context equality assertion that did not allow
the newly displayed exploration capacity to decrease after a correction. The
prompt was shortened to 7,936 characters, its current identity updated without
changing historical arms, and the context control now separates stable failure
evidence from resource counters. All seven failing targets are covered by the
14-test recheck, which passed in 13.84 seconds. Final docs passed five tests; Ruff
and diff checks pass. This is split validation, not a zero-failure quick invocation.
Both existing isolated mock-evaluation smoke cases passed in quick. The full quick
selection was not repeated after these focused corrections.

No paid provider, benchmark target or evaluator image was invoked. Local fixtures
and isolated mock evaluation test mechanisms, not Astroid repair or hidden-test
acceptance. The remaining question is whether a model uses the additional
exploration to form and test a better repair hypothesis within the same caps.
