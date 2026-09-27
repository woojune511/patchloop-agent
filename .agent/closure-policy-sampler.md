# Closure-policy response sampler

`diagnostics/closure_policy_sampler.py` validates the frozen closure-policy pair
and reuses `decision_sampler` for four independent responses in A1/B1/B2/A2 order.
It never executes returned actions, restores a workspace, runs Docker or evaluates
a candidate. Acceptance and safety remain NOT_RUN even if an action is well formed.

Preparation binds the original dev-train public task, source journals and actual
dispatch, native delivery, and exact two-sentence system-message deletion. Every
other request field remains equal. The live plan binds runtime, implementation,
price table, credential path and request pair. Collection revalidates disk inputs
before claiming a fresh output root or reading credentials. No retry or resume.

The fixed model is gpt-5.4-2026-03-05, xhigh, 25,000 output tokens. The proposed
invocation cap is $4 with $1 per response; preparation is not paid authorization.
The inherited 60,000 counted-input limit and full output reservation must jointly
fit $1 at the bound prices. Reject a changed price table that violates that bound.
Unused allowance does not increase another response's limit. Count immediately
before dispatch; use zero SDK retries. Count/transport/billing uncertainty stops
the group. The shared collector's active deadline is 1,800 seconds for the whole
invocation; frozen agent-displayed historical time is unchanged.

Commands (paths and hashes must refer to the reviewed external packet):

```text
python -m diagnostics.closure_policy_sampler prepare --pair PATH --pair-hash SHA --output FRESH_DIR
python -m diagnostics.closure_policy_sampler validate --packet PATH --packet-hash SHA
python -m diagnostics.closure_policy_sampler collect --packet PATH --packet-hash SHA --grant JSON
```

The grant uses `decision_sampler.Approval`: packet_hash, sampler_hash, result_root,
credential_file, max_cost_usd, pricing_hash, pricing_verified_on. Prices require
review on the execution UTC date. Source/plan ancestors and descendants cannot be
result roots. Tracked runtime, collector and public task must be clean for live use.

Review shuffled public response artifacts before arm/cost metadata. A chosen probe
is only a plan, not an executed check or improvement. Private evaluator material,
operator-discovered cases, review rubric and prior returned finish decision never
enter these requests. Prior policy exposure is shared; this is a local current-input
ablation, not a fresh-solve or general quality comparison.
