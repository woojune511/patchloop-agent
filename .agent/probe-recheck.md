# Saved-program recheck

`--probe-recheck saved-program-v1` requires `--enable-probes --probe-policy cases-v1`.
The default is `none`; selected repair defaults remain unchanged. This is a feedback
policy, not a new test authority or submission gate.

## Runtime contract

The active program is the last completed reference-free `save_program=true` action
still retained in the three-case catalog. Failed assertions/imports can be saved.
Manual replay does not select a different program. A new save replaces selection;
eviction clears it without resurrecting an older program. Source edits and changed
expectations use a new save; existing sources/results are immutable.

After a successful changed mutation, select from its durable pre-admission prefix.
Drain existing required repair-recheck first, then execute the selected program once
on the candidate diff before inference. One gateway action consumes action/time
budget and no model call. Existing probe admission protects completion reserves;
if unavailable, record NOT_RUN with the reason and never retry that skipped action.
No registered check credit or extra edit capacity is granted.

The child identity binds run, parent mutation, case definition and both diff hashes.
Started/finished/skipped receipts are append-only. Completed actions replay receipts;
interrupted execution uses the existing sandbox cleanup/recovery contract. Uncertain
cleanup or identity is a stop, not an assertion failure. The optional contract is
bound in model hash, manifest and exact resume envelope. OFF context/schema bytes
are preserved. Native model calls/outputs are never fabricated for harness actions.

Public context exposes active ID, latest child observation, bounded output and current
versus historical diff. Expectations remain model_authored_unverified and behavior
remains not_assessed. Process success, assertion failure and import failure are not
host-certified patch verdicts. A failed program never changes finish eligibility.

## Fixed development comparison

Driver: `diagnostics/probe_recheck_panel.py`; operator-only public programs:
`diagnostics/probe_recheck_public.py`. Commands are prepare, controls, freeze, preflight, run,
and assess, with an external --root and, after freeze, the exact --packet-hash.
Preparation does not call a provider or read credential contents. Only run reads
credentials through the ordinary runner after exact packet-bound human approval.

A uses current brief-v1 and probe-policy none. B adds common public expectation,
entrypoint and preservation guidance with cases-v1. C uses identical B guidance
and enables saved-program-v1. No operator program, historical diagnosis, candidate,
reference patch or hidden result is supplied to any fresh solver.

Tasks in order: dev-train SQLFluff-1733, pydicom-1413, pydicom-1694. Repetition one
orders ABC/BCA/CAB; repetition two CBA/ACB/BAC. Each starts at its public base.
Model gpt-5.4-2026-03-05, xhigh, desired output 25,000; 40 calls, 100 actions,
four edits, 1,800 seconds per row. USD 3 per row and USD 54 invocation maximum;
18 rows. Credential: repository .env. No retry, replacement, resume, transfer or
automatic follow-up. Any count/transport/billing/cleanup uncertainty stops the panel.
Existing source/environment descriptors are frozen. Missing images stop preparation;
no automatic pull/build is permitted. Every run is official=false, claim-ineligible.

Only dispatch after focused tests, Ruff, fast suite, isolated mock smoke, public base
reproductions, exact clean implementation freeze and environment preflight pass,
and the user approves that frozen scope. Old allocations cannot authorize this run.

## Assessment and decision

Assess hash-verified submitted workspaces only after the paid panel closes. Keep
original acceptance, independent public behavior, safety, cost and elapsed time
separate. In public trace review classify missing/invalid expectations, construction
or entrypoint errors, ignored observed failures, unsuccessful repairs, and unexplained
acceptance gaps. No successful probe count is a repair-success metric.

`decide` requires the complete exact 18-row roster. Selection requires C>A and C>=B
in both repetitions, total C>B, no paired A/B success lost by C, and total C cost and
time each <=125% of A. Require verified contract/safety accounting and at least one
public trace showing a valid automatic failure delivered before another edit, then
the same program passing and original acceptance passing. Record that operator
review separately with its run/action/diff evidence; exit codes alone cannot supply
the mechanism flag. No valid use means insufficiently exercised, not disproven.
Failure of any criterion preserves baseline and closes the allocation. Even selection
is limited to this exposed development group; CLI defaults and general claims stay
unchanged. Complete findings belong in one new history record, not appended here.
