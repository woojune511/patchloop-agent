# Why completed B review did not produce a repair

## Question and evidence boundary

The [completed B run](2026-10-02-review-time-extension-result.md) returned a report
in about 117 seconds but submitted the original patch. Distinguish missing input,
investigation selection and interpretation failures before adding another feature
or paying for another run. This audit uses only the saved public issue/request,
public tool calls/results, candidate source and public finish decision at e9cfe2e9.
No private spec, hidden test or reference patch was read, and no model or probe
was executed. Encrypted reasoning was not examined. The earlier
[public diagnosis](2026-10-01-opensandbox-public-diagnosis.md) supplies the bounded
caller/helper distinction; it is operator evidence, never a new agent hint.

## Requirement-to-observation map

| Public requirement or clue | Delivered evidence | B's follow-up |
| --- | --- | --- |
| Reject symlink components in ensure_valid_host_path | Full original issue and 27-line helper patch | Read validators.py 389-520; probed helper symlink rejection |
| Issue names _validate_host_volume as the vulnerable backend | Full original issue; later docker.py 1486-1490 search span | Initial definition search was restricted to validators.py and missed; no backend body read followed |
| Backend helper call is conditional on allowlist and changed resolved path | Exact if-condition appeared in the first span of the broad search result | Report mentioned the conditional call, but no backend or full-sequence probe |
| Align host validation with _validate_pvc_volume / strict realpath | Full original issue explicitly named the comparison | No PVC body read or comparison |
| Preserve cross-platform path behavior | Candidate comment and public test snippets | Probed a Windows-style allowlisted path on Unix |

The initial factual packet contains public_task, current_diff and receipts. The
saved public issue exactly matches the task public file. No requirement was lost
when removing the prior trajectory. Full backend/PVC implementations were not
preloaded, but registered source inspection could retrieve them.

The broad search was truncated and included many public test snippets. However,
the conditional docker.py call was actually returned first and cited in the final
report. Truncation therefore does not explain the absence of that clue. Search
noise and the initial wrong-file search may have consumed attention or calls, but
their causal effect cannot be established from one trace.

## Actual inspection and conclusion

B performed search/search, read/search, one probe, then the forced final report.
Its first attempt to find _validate_host_volume looked only in validators.py.
It subsequently broadened the helper-call search, saw the docker.py condition,
but spent its third call probing the edited helper and cross-platform behavior.
It never read _validate_host_volume or _validate_pvc_volume in full. The final
report accurately described the probe observations and explicitly declined to
claim a concrete defect. It was not a fabricated success or a proof of correctness.

The public backend source shows conditional helper revalidation and lexical
subpath normalization, whereas the PVC branch includes strict realpath calls.
The ordinary volume-validation sequence also runs the shared validator first.
Thus the conditional snippet alone is not proof that a static symlink bypasses
the ordinary full path. The missing work was to investigate those boundaries,
not to infer an exploit from a five-line search result. The earlier public
diagnosis scoped the uncovered backend/subpath/interstage behaviors and did not
claim atomic mount safety or identify the exact hidden assertion.

After receiving the review, the repair agent made only finish_task. Its public
decision cited inherited helper-probe action call_BjoEiL8ngId3HVoyCH10do95, with no
new repair actions. The final candidate hash is unchanged. This shows continuation
of the previous narrow verification basis, not that B's report alone caused the
submission or that the repair agent ignored the report internally.

## Diagnosis and alternatives

1. Missing requirement in the review packet: contradicted by exact issue delivery.
   Missing full source in the packet is normal on-demand inspection, not an access
   failure; no tool denial prevented a backend/PVC read.
2. Investigation stopped at the edited helper: directly observed and the strongest
   supported diagnosis. The task explicitly covered a second validation layer;
   the review did not turn that requirement or returned clue into a targeted check.
3. Misreading a completed backend test: unsupported, because no such test or full
   backend inspection happened. The final report's stated probe results are correct.

The instruction to investigate one possible defect, the prominent helper diff,
limited calls and existing passing regressions plausibly favor a narrow local
question. That is a mechanism hypothesis, not a demonstrated psychological cause.
Different context did not expand requirement coverage in this particular run.
Four-call reservation also forced a report after the chosen probe; more wall time
alone did not provide more investigation calls. No evidence here establishes that
extra calls or a different prompt would yield a correct patch.

## Decision and evidence

Keep the baseline and close the review/context/time lane for this allocation.
Do not automatically add another reviewer, increase time, or require a positive
defect claim. The concrete unresolved engineering question is whether selecting
investigations from named task requirements rather than only changed code improves
repair completeness. This trace supports that question, not an implemented rule
or a paid comparison. Any future intervention must have independent scope and
correctness criteria and must not inject operator-known cases or hidden outcomes.

Audit: C:/pt/analyses/review-scope-audit-20261002-v1/summary.json and its append-only
dev-run-v1 journal. Driver: C:/pt/review_scope_audit_20261002.py. Assertions verified
exact issue delivery, returned conditional span, actual read/probe scope, inherited
finish evidence, unchanged candidate and original journal/result bytes. Provider
calls, probes and private-spec reads: zero. Documentation checks and diff hygiene
passed; runtime behavior was not changed, so runtime tests were not repeated.
