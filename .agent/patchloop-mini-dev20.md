# Current PatchLoop versus the mini-SWE dev20 baseline

Date: 2026-10-16. The user requested a fresh measurement of PatchLoop on the same
problems and selected all twenty development-exposed tasks. This continues that
request within the conversation's cumulative USD 24 ceiling; no extra allowance
or unrestricted shell is granted to PatchLoop.

## Fixed question and scope

Measure the current agent's submissions, independent task success, cost and elapsed
time on the original dev20 roster. Use runtime source at
`fcfa496dfb57f7e0d79616e5389fac034cfbc6b2`; any subsequent operator-only commit must
preserve its runtime bytes. This is a descriptive whole-agent comparison, not an
estimate of one planning feature's effect or a held-out accuracy claim.

Inputs are `tasks/dev-train/current-dev20/{1..20}/public.yaml`, in their existing
order, one fresh run each. Use `gpt-5.4-mini-2026-03-17`, xhigh, desired output
25,000, standard/global, and the credential file
`C:/Users/geonj/Documents/PatchLoop/.env`. Keep selected policies: segmented-v1,
result-or-size-v1, brief-v1, 24,000 retained source characters, ordinary probes,
probe-policy/recheck none, repair-recheck, protected-v1, per-call-v1.

Each row keeps 40 model calls, 100 actions, four accepted edits and 1,800 seconds,
including a 330-second registered-evaluation reserve. Two independent workers use
registered PatchLoop tools only. Native grading uses the existing pinned harness
and local images. Public task/base-commit and opaque evaluation identities must
match the mini baseline; no hidden material or old solution enters solver context.

## Budget and stop rules

The closed mini experiment cost USD 6.2666922, verified against
`C:/pt/mini5metadataaudit01/closeout.json` and its raw usage evidence. Reserve
USD 0.88 per row / USD 17.60 for this fresh panel. The worst-case conversation
total is USD 23.8666922, below USD 24. Unused row allocations are not transferred.
The lower per-row ceiling differs from mini's original approximately USD 1.20;
report whether it actually constrained any row. Do not treat the larger-budget
five-task completion as part of a uniform mini score.

Freeze manifest, resolved requests, operator/runtime hashes, public dependency
identities, existing images, native harness and validation before dispatch. Preserve
the exact user messages selecting this work and its previous cumulative ceiling in
the fresh authorization record. Prior closed runs remain immutable and are never
resumed. Count immediately before dispatch, use zero SDK retries and stop pending
work on count, transport, billing, cleanup or identity uncertainty. Known row limits
close only that row. No image pull/build, replacement solve, tuning, automatic
follow-up or held-out run is included.

## Validation and reporting

Run focused allocation/accounting tests, Ruff, the fast suite and mock smoke.
Recheck all twenty public import, ordinary-operation and selected-test environments
without provider calls. For SQLFluff, also check default configuration, one core
plugin registration and ordinary parsing/linting through the real public probe and
registered check environments. The mini adapter's metadata defect is not assumed
to apply to PatchLoop's separately prepared public metadata.

Keep the original mini 20-row result (10 PASS, 5 FAIL, 5 NOT_RUN), its five-task
completion and the new PatchLoop result in separate columns. Report each task's
submission, registered/native grade, agreement, safety, billing and cleanup. Missing
grades remain NOT_RUN/ERROR. Preserve the mini environment limitation and differences
in shell/tool interface, verification, concurrency and cost ceilings. Any quality
signal concerns this exposed roster and these complete agent configurations only.
