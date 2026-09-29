# Observations to repair: prepared comparison

The [frozen-program replay](2026-09-29-selected-probe-execution-results.md) produced
two valid HF endpoint counterexamples, two environment failures, and a Pydantic
program that passes its unsupported expectation. Do not collapse these into one
generic prompting failure. This experiment tests only whether actual HF observation
adds repair value beyond the same program and expected values.

## Fixed causal question

Use hf-hub-xet-endpoint-propagation v5 (dev-train), the H A1 candidate at the
pre-first-check seam, and the unchanged H B2 probe from the selection experiment.
The B2 program has explicit/direct/ambient controls; it was selected by this
preparation rule, not by the successor model's outcome. Candidate and receipt
hashes were verified against saved public inputs and content-addressed artifacts.

Both arms receive the same public issue, candidate patch, model-authored program,
expected values, receipt identity and limitations. A explicitly withholds execution
observations. B receives actual stdout/stderr/exit code/setup comparisons. Only
that feedback field differs. No operator diagnosis, patch hint or private evaluation
detail is supplied. The shared program already conveys a specific hypothesis:
this is observed evidence versus an unverified hypothesis, not information versus none.

Reuse the existing seeded-candidate run engine with fresh context in both arms.
This is deliberately not native continuation of the prior sampled response: no
old plan, reasoning, source views or check credits are inherited. The agent must
read current code for edits. One seed consumes one of four mutation slots. The
fresh-context choice is common to both arms, but limits conclusions about the
original agent's ability to recover within its own trajectory.

A may independently execute the supplied program. Preserve normal tool access
and report this crossover; the intervention changes initially supplied evidence,
not eventual evidence availability. Feedback becomes historical after a mutation.

## Executable scope and limits

Order A1/B1/B2/A2. Model gpt-5.4-2026-03-05, xhigh, 25K response ceiling,
credential C:/Users/geonj/Documents/PatchLoop/.env. Proposed new cap USD 8 total,
USD 2 per episode, 900 seconds per episode, 4200 seconds overall. Normal 40 calls,
100 actions and four mutation slots (including seed). No protocol recovery, SDK
retry, resume, replacement or extension. Existing pre-dispatch accounting stops
on count, transport or billing uncertainty; runtime stop_remaining halts the panel.

The actual repair loop includes registered reads, edits, public checks, optional
probes, submission and isolated benchmark/safety evaluation. After each settled
episode, execute the frozen program once against its final candidate through the
probe sandbox, without feeding the audit back. No program correction or evaluator
image substitution. A resource-limited or unsubmitted candidate remains labeled as
such even if the external audit passes. Unknown cleanup stops all remaining work.

Primary evidence: repair of the explicit/ambient distinction, control outputs,
and public checks on the final diff. Report benchmark acceptance, safety, cost,
time and submission separately. Inspect the requirement-to-condition explanation;
passing only the supplied assertion does not establish a complete repair. Four
seeded episodes on one already-used task cannot establish generalization or justify
adoption. P's expectation validity and G's environment limitations are not tested.

The [contract](../../.agent/observation-repair-panel.md) and
[driver](../../diagnostics/observation_repair_panel.py) define freeze/preflight/run.
Packet: C:/pt/analyses/observation-repair-panel-20260929-v1/packet.json,
sha256:d3fa07e2afc24240dd84bdf2a49e8f8c254cc316d1cb4fb6f37a603035d8cd33.
All state is external, immutable and recorded in dev-run-v1 hash chains.

## Preparation evidence

Read-only preflight confirmed the existing Linux evaluator image, pinned Python
probe image and prepared HF dependencies. It made zero provider calls and read no
credentials. Official [GPT-5.4 pricing](https://developers.openai.com/api/docs/models/gpt-5.4)
was reviewed on the packet's UTC date: USD 2.50 input, 0.25 cached input and 15 output
per million tokens under the long-context threshold. A later UTC execution date
requires fresh pricing review and a new frozen packet.

Four new tests cover the single-field intervention, diff-bound observation currency,
exact scope/caps, stopping all work after runtime uncertainty, and refusal to restart.
The existing seeded-run tests cover repair/check/submit/isolated evaluation and
invalid seed/feedback rejection (19 tests); all passed with provider-free mocks.
The first test attempt hit a Windows temporary-directory permission error; rerunning
under a new external test directory succeeded. A preparation-only UTC date formatting
error was fixed before any packet or model dispatch. Ruff and documentation checks
passed. Full runtime testing was not rerun: production behavior is unchanged.

Live repair runs, post-repair probes and new benchmark evaluations are NOT_RUN.
The earlier USD 13 allocation is closed. This prepared USD 8 proposal is not paid
approval; approval must identify this exact task/model/credential/repetitions/cap.
