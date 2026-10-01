# Review pilot v2 environment readmission

After the user started Docker, the frozen proposal from the
[blocked preparation](2026-10-02-review-pilot-v2-preparation.md) was revalidated
without a model call or credential read. No implementation, task selection,
scoring, budget or manifest bytes changed. Source HEAD was 6a0ab81.

## Verified evidence

- Manifest: C:/pt/analyses/review-pilot-ready-20261002-v2/manifest.json
- SHA-256: 2b10fc24828b4c8c2d3d7873728172faea53e298a74e68654a744acd96742707
- Readmission driver: C:/pt/review_pilot_v2_readmit_20261002.py
- Evidence: C:/pt/analyses/review-pilot-v2-readmission-20261002-v1/summary.json
  and its append-only dev-run-v1 journal.
- Docker server reported 29.8.0. Existing source, evaluator and probe admission
  passed for original-opensandbox-816, original-isort-2491,
  original-pyinfra-1679 and original-conan-19735.
- Full manifest rebuild/validation passed both before and after admission.
- Credential loader was blocked by a test guard; credential contents read: zero.
  Provider calls: zero. No images were acquired. The result root remains absent.

The user's local AGENTS.md change removing the Docker-start prohibition was
observed and preserved, not staged with this follow-up. It is outside the frozen
runtime/diagnostic implementation set. No required implementation-clean check was
bypassed.

## Exact proposed paid scope

Same four dev-train checkpoints, CAB / ABC / BCA / CBA order, one repetition per
arm (12 rows). C is ordinary continuation; A reviews with the trajectory; B reviews
without prior rationale. Model gpt-5.4-2026-03-05, xhigh, maximum output 25,000;
credential file C:/Users/geonj/Documents/PatchLoop/.env.

USD 24 invocation cap; USD 2 per row shared by review and repair. Per row:
900 seconds, 16 calls, 48 actions, two new accepted edits. Reviewer subset:
180 seconds, four calls, twelve actions. Operator-only scoring has 300 seconds
and no model calls. Result root: C:/pt/runs/review-context-pilot-20261002-v2.
Existing public matrices and isolated hidden evaluation remain frozen; pyinfra
v1 evidence is preserved separately from calibrated v2.

No retries, resume, replacements or budget extensions. Invalid reviewer output,
count/transport/billing/cleanup uncertainty or scoring failure stops the remaining
panel. Results distinguish correctness, regressions, completion, cost and time.
The exposed, outcome-selected panel cannot establish generalization or justify
automatic adoption. The earlier two paid allocations remain closed.

## Decision

Preparation is complete. Explicit approval of this exact manifest and USD 24 cap
is still pending. Revalidate the manifest and environments again before paid
dispatch, as the collector already requires. This record is readiness evidence,
not live execution or repair-quality evidence.
