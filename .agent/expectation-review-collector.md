# Matched expectation review collector

`diagnostics.expectation_review_collector` prepares and collects a single A1/B1
pair from an immutable expectation-review checkpoint. Both arms retain completion
advice removal. B alone receives the generic review field on its first dispatch;
subsequent current states do not reinject it. No task-specific answers are added.

Preparation binds exact dev-train task, model, effort, output ceiling, credential
path (not contents), runtime, implementation, funded request hashes, and result root.
A positive invocation-wide fresh cap is divided equally, with no transfer. Historical
spend remains provenance; closed historical allocations are never reopened.
Restoration changes only current cost allowance, identically in both arms.

Collection requires explicit manifest hash and approved cap. The result root is
single-use, including preflight failure. Count immediately before dispatch, zero
SDK retries, ordinary registered tools and isolated evaluation remain in force.
Count/transport/billing uncertainty stops remaining arms. No automatic resume,
Docker startup, image pull, or build. Store journals/artifacts outside the repository.

Use `prepare --packet ... --packet-hash ... --env-file ... --result-root ...
--output ... --new-cap-usd ...`, then `collect --manifest ...
--approved-manifest-hash ... --approved-new-cap-usd ...` after authorization.
Both require `python -m diagnostics.expectation_review_collector`.

All results are official=false. One matched pair is development evidence, not a
fresh solve, efficacy estimate, or default adoption. Inspect delivered information,
next actions, candidate changes and public checks separately from benchmark results.
