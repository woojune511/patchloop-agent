# Original-input task package integration

## Problem and changes

Three image-level calibrations were not yet executable PatchLoop task packages.
Added original-toqito-1538, original-montepy-933 and original-darts-3065 under
`tasks/dev-train/`. Original issue descriptions are preserved verbatim. Registered
public commands execute only existing base tests in a temporary checkout; hidden
assets contain the original test patch, original grading lists and pinned scoring
functions. Reference patches retain only production changes, excluding test edits.

The actual sandbox mounts source read-only. Public/private temporary copies preserve
that boundary while allowing pytest/Hypothesis to write local scratch. PYTHONPATH
explicitly selects the copied submitted source, not installed image source. Hidden
test application and logs remain evaluator-only; no agent context receives reference
patches, hidden assertions or grading lists.

The three exact GitHub URLs were added to the existing repository allowlist. Fresh
remote checkouts now set core.autocrlf=false before checkout: Windows CRLF conversion
had prevented the original test patch from applying inside the Linux sandbox.
Existing historical/prepared workspaces are unchanged.

RegisteredCheck gains optional infrastructure_exit_codes; empty defaults are omitted
from serialization, preserving old task identities. The isolated evaluator maps
declared infrastructure exits (and timeouts for opted-in checks) to ERROR and aborts
evaluation so the agent loop reports EVALUATOR_ERROR, not EVALUATOR_FAIL. Original
oracle exit 2 means incomplete/setup execution, distinct from completed failure 1.

## Failed draft and pre-execution corrections

The initial draft is retained through receipts at
`C:/pt/analyses/original-pilot-packages-20260927-v1` and archived draft files in v2.
It exposed three independent issues:

- CRLF conversion broke private test-patch application for all three tasks.
- MontePy's public Hypothesis test could not write its database on read-only source.
- Toqito's base test explicitly required uparrow to remain unimplemented, contradicting
  the original public issue; the old 120-line/no-public-API restriction also conflicted
  with requested feature/API changes (the reference production diff has 141 lines).

Fixed checkouts and scratch placement. Excluded only the contradictory public toqito
test, based on its public body and original issue. No new semantic public tests were
authored. Amended the pilot before any model run to four production files/1,000 diff
lines and allowed public API changes; dependency/test/evaluator edits remain forbidden.
This amendment is explicit, not an unchanged baseline or post-result model tuning.

## Executed validation

Package sandbox receipts: `C:/pt/analyses/original-pilot-packages-20260927-v2`.
For all three tasks, BASE public checks passed and original private checks failed;
REFERENCE public/private checks and scope/API policy checks passed. Hidden originals
still use the complete original test command and original F2P/P2P sets.

Final evaluator receipts: `C:/pt/analyses/original-pilot-package-endtoend-20260927-v2`.
The earlier v1 receipts remain unchanged; v2 verifies the final infrastructure-error
propagation change. Final audit: `C:/pt/analyses/original-pilot-package-audit-20260927-v2`.
All three production-reference submissions completed with task acceptance true and
hidden/regression/scope/safety PASS through EvaluationEngine. This exercised fresh
source preparation, manifest and submitted diff identity, private asset injection,
DockerSandbox registered checks, policy evaluation and isolated result storage.
No model generated these patches and no performance rate is claimed.

Package identities:

| Task | SHA-256 task content |
| --- | --- |
| original-toqito-1538 | cf5cb8a9fbe896ed5b16f41fa034c003b18881e825cf33aee11030df354b3a08 |
| original-montepy-933 | d3142728487f6b08e75c60f542b037c0866e68c54a96d94d1a9d4ae505a6d62d |
| original-darts-3065 | 7375e3b698cf9cf5d5558e56c13c36094f577221025aca8b0b86be3046333b17 |

Runtime SHA-256: `b6181cde07a5f8df9fac0c81eb55c25015baf4adf520d6cccec1c697b72a4faf`.
Tool surface: `25f1db63f18b3f138ee8bdc8686ad320d7c9a3965d4e10acd1055fdd590555b7`.
Focused contracts/evaluator/source/package suite: 65 passed; final error-boundary,
evaluator and evaluation-resume suite: 40 passed. Runtime source was
frozen during end-to-end verification. General probe dependency readiness and paid
model runs remain NOT_RUN. A live invocation still requires exact credential/cap
authorization and a final manifest; image approval is not model approval.

## Final regression checks and limits

The broad parallel suite recorded 3,468 passed, 23 failed, seven errors and 16
skipped in 843.288 seconds. Its first portion overlapped the infrastructure-error
runtime edit: provenance checks explicitly reported changed runtime identities.
One CAS write also reported FileNotFoundError on an overlong Windows scratch path.
This execution is not a clean final-source full-suite result.
All 30 failed/error cases were rerun with frozen source and short scratch root
`C:/pt/ppr1`: 30 passed in 75.127 seconds. No further runtime changes were needed.
Changing both conditions resolves the failures but does not establish the individual
cause of every collector assertion. XML receipts are
`C:/pt/validation/original-pilot-packages-parallel-0927a.xml` and
`C:/pt/validation/original-pilot-packages-retry-0927a.xml`.

Ruff passed across patchloop, tests and diagnostics. Documentation checks: five passed.
Final mock smoke `run_dev_fffd858543f64465`, rooted at
`C:/pt/original-pilot-packages-smoke-0927b`, reached isolated EVALUATOR_PASS;
Docker safety remains NOT_RUN for this mock, and paid cost is zero.
The final owned-container listing was empty. No live model/count request ran.

Final index-byte validation found Git newline normalization would alter the three
oracle JSON assets and raw package identities. Package-scoped -text attributes preserve
all calibrated bytes, including YAML. Loading staged package bytes verifies the same task identities;
runtime and evaluator inputs remain unchanged.
