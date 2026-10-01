# Reviewer tool contract audit

## Problem and evidence

The second [pilot](2026-10-02-review-pilot-batch-stop.md) stopped on its first
reviewer response: read_file and run_probe appeared together. Neither executed.
After two contract-related paid stops, auditing the whole reviewer interface was
more useful than another adjacent paid attempt. This audit starts from 48b24321.
The closed allocation and its USD 0.1639325 settled total remain unchanged.

The reviewer replaces the ordinary agent's system instruction but inherits tool
schemas. Its instruction omitted the batch restriction that its executor enforced.
Other mismatches were visible without provider calls: it bypassed native batch
validation, advertised note/plan updates that it did not apply, and offered probes
even in the scripted mode where probe execution was disabled.

Missing guidance plausibly contributed to the observed mixed response; stochastic
noncompliance remains possible. This audit establishes interface mismatches, not
that guidance caused the model response or that the repair-quality hypothesis is
correct. A future valid review with no useful repair would weaken the intervention's
practical value even if the tool contract were followed perfectly.

## Contract and change

| Boundary | Current contract and implementation |
| --- | --- |
| Response grouping | Explicit instruction: 1-4 reads/searches, one probe, or one report |
| Pre-execution admission | Parse every decision and reuse native validate_tool_batch before any gateway call |
| Decision metadata | Read/search inspect plus evidence goal; probe verify; unsupported note/plan updates restricted to null |
| Available tools | Registered read/search and enabled probe only; no edits, checks, shell or task finish |
| Report | Standalone finish_review, no turn_decision, exact current candidate hash; existing bounded fields retained |
| Horizon | Existing four-call/report-reservation rule retained; no corrective replacement call |
| Usage | Existing pre-dispatch count, zero retry, settled partial usage and panel stop retained |
| Continuation | Native call IDs/results and encrypted continuation preserved; no private evaluator input |

The shared validator removes the separate reviewer batch grammar rather than
adding another enforcement layer. The gateway still owns per-tool argument/path
semantics; this is not an atomic transaction over all tool arguments. No automatic
batch splitting, new notes subsystem or extra review call was introduced. The
ordinary coding-agent runtime and original paid manifests were not changed.
The changed diagnostic/protocol hashes require a new manifest for any future run.

## Provider-free validation

- Focused review/collector/integration/manifest suite: 109 passed in 87.78 seconds.
- New 47-case contract coverage includes both review arms, accepted shapes,
  mixed batches in both orders, invalid second decisions, unknown/unavailable
  tools, annotations, duplicate IDs, candidate mismatch and separate
  read/probe/report turns. Rejected batches execute zero gateway calls and retain
  settled usage without a replacement generation. Gateway execution is stubbed
  in this matrix; existing integration tests exercise actual tool routing.
- Ruff passed for patchloop, tests and both changed diagnostic modules.
- The exact saved mixed response was replayed through native batch admission and
  rejected with zero gateway/probe/provider calls. The original manifest, result
  and reviewer journal hashes still match the prior audit. Replay evidence:
  C:/pt/analyses/review-contract-replay-20261002-v1/summary.json.
- Mock smoke run_dev_37e52387ea99485e reached isolated EVALUATOR_PASS; safety
  NOT_RUN, official=false, zero provider cost. State:
  C:/pt/runs/review-contract-mock-20261002-v1.
- Full regression suite: 3,951 passed, 16 skipped in 3,258.17 seconds (54:18).
  JUnit evidence: C:/pt/tmp/reviewcontractfull01-results.xml. The full suite is
  distinct from the focused 88-second contract validation above.
- Documentation layout: 5 passed; smoke task validation and git diff --check passed.

## Decision and remaining question

The reviewer contract is now explicit and shares native admission. Preserve the
baseline and both stopped allocations. No paid call, retry, new manifest or paid
run is queued by this change. Local routing tests do not establish live model
compliance, reviewer usefulness, patch correctness or a fresh-context advantage.
If another bounded comparison is considered, its unresolved question remains
whether a valid review changes actual repair correctness under the frozen caps;
it requires a fresh manifest and explicit approval before dispatch.
