# Observation-to-repair comparison

Opt-in diagnostic only. Reuse candidate_review_repair.run_seeded and ordinary
dev-head tools, checks, submission and isolated evaluation. No default change.

Task: hf-hub-xet-endpoint-propagation v5, dev-train. Seed the exact H A1 candidate
at the selection checkpoint. Each episode starts with fresh context; it does not
resume the original native conversation or claim fresh task solving. Same public
task, seed, tool settings, program, model and budgets in both arms. No inherited
plans, reasoning, source views, tool results or check credit. Seed consumes one
mutation slot; current-source reads are still required for edits.

Both arms receive the unchanged H B2 model-authored probe program, public issue
text, receipt identity and limitation text. Only the stdout feedback field differs:
A explicitly withholds execution observations; B supplies the actual stdout,
stderr, exit code and setup comparisons from the registered-path replay. No added
operator diagnosis, suggested edit or evaluator detail. The program already
contains expected values and a concrete hypothesis; this isolates observations
beyond that shared hypothesis, not all information versus none. A may run the
program itself through existing tools; report such crossover rather than forbidding
normal agent behavior. Feedback is bound to the initial diff and becomes historical
after edits. Neither arm receives post-run audits or private outcomes as model input.

Order A1/B1/B2/A2, four episodes. Exact model gpt-5.4-2026-03-05, xhigh, 25K output,
credential C:/Users/geonj/Documents/PatchLoop/.env. Proposed NEW total USD 8 cap,
USD 2 per episode, 900 seconds each, 4200 seconds overall. Normal 40-call/100-action
limits, four mutation slots including the seed; protocol recovery disabled in both
arms. Count immediately before dispatch, zero SDK retries. Stop all on runtime
stop_remaining, count/transport/billing uncertainty or uncertain cleanup. No resume,
replacement, extension or reuse of earlier unused funds. Prices must be freshly
reviewed on the execution UTC date; changing the date requires a new frozen packet.

After each settled episode, run the identical frozen public program once on its
final candidate, outside the agent, through the registered probe sandbox. No code
correction or alternate evaluator environment. Audit maximum 90 seconds including
preflight/cleanup, normal probe maximum 30 seconds. Skip audit and later episodes
on runtime uncertainty. Preserve resource-limited, rejected and unsubmitted outcomes.

Primary: independent repair of the explicit/ambient distinction, with frozen probe
control outputs and registered public checks on the same final diff. Report isolated
benchmark acceptance and safety separately, not as prompts for another attempt.
Secondary: source/condition explanation, new edits, public checks, submission, cost,
time, and A self-acquisition of observations. Audit PASS alone is not full correctness;
same evaluator failure after a probe fix remains unexplained. No blind selection
claim, no held-out/generalization claim, and no adoption from four seeded episodes.

Entry points: freeze(root), preflight(root, packet_hash), then only after exact paid
approval run(root, packet_hash, approved_cap=Decimal('8')). Freeze/preflight must not
load credentials or dispatch a provider. External dev-run-v1 journals and immutable
artifacts hold all generated state. Preparation and mock validation are not approval.
