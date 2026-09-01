# Implementation plan

The reset is the active seam; there is no Work Item 87 candidate.

## Completed reset surface

- one mutable `dev-head` runtime and one `patchloop dev` command
- four-state loop without a plan phase or plan tools
- constrained turn batching and embedded mutation intent
- automatic full-diff projection and gated finish
- bounded public context with memory disabled
- invocation-wide cost admission and zero transport retries
- external append-only state and idempotent action recovery
- separate private evaluator and public-safe summary
- focused fast suite plus one mock end-to-end path
- removal of historical runner modules, scripts, tests, and claim CLI

## Next small seams

1. Keep focused validation below two minutes while fixing defects found in
   `dev-head`; do not version the runtime for each fix.
2. With a separate exact user invocation, run one `dev-train` row and verify a
   durable terminal plus evaluator summary within 30 minutes.
3. Repeat only on distinct development tasks under their own explicit caps.

Do not consider a confirmatory claim lane until at least three distinct
`dev-train` tasks reach submission without harness/contract terminal and at least
two privately pass. That threshold only opens design review; it does not itself
support a quality or generalization claim.
