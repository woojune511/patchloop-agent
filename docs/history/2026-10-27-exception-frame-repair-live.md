# Seeded exception-information comparison

Date: 2026-10-27. Status: CLOSED. official=false; no repair or quality claim.
Implementation commit: `afe9d98a`. Runtime:
`sha256:5753dbef010721c721db788aa01525fc269ad12093b46e45ffc2ffd158c929f3`.

## Material Passport and question

ARS experiment run and interpretation, public development evidence only.
Does providing exception frames/chain, in addition to type/message, change the next
repair of the same saved failed candidate? This is an operator seeded diagnostic,
not the production runner's fresh-solve or continuation outcome. See the
[local mechanism and preparation](2026-10-27-exception-frames.md).

The user explicitly approved the exact prepared manifest hash
`sha256:73367ba93e99a6aa09b1312f53bc8ef00cfe857011ae8d2fa3063bdf7d6395a5`:
dev-train current-dev20/13, gpt-5.4-mini-2026-03-17/xhigh, repository `.env`, A/B once,
USD 0.60 each and USD 1.20 invocation-wide. Ordinary/correction ceilings were
40,000/25,000, input ceiling 60,000, four ordinary model responses plus at most one
protocol correction, twelve tools, one diagnostic probe and one accepted edit per arm.
Initial requests differed only by the exception-details field; subsequent tools
were identical. A was permitted to acquire frames itself. No private data was supplied.

## Execution and results

Root: `C:/pt/exception-frame-repair-live-v1`. Result hash:
`sha256:2e638c896b39a28ba66032de88b1cefba0af13b89271fb90723ed6419d8aece0`.
Both conditions restored the identical first failed candidate `9914a973...`.
Local images/profile and public regression image were checked before credentials.
Provider counting, dispatch and settled billing completed without retries or uncertainty.

| Measure | A: initial type/message | B: initial frames/chain |
| --- | --- | --- |
| Terminal | MODEL_LIMIT | MODEL_LIMIT |
| Model responses | 4 | 4 |
| Read/search actions | 4 | 6 |
| New edits / diagnostic probes | 0 / 0 | 0 / 0 |
| Maximum input tokens | 14,943 | 18,585 |
| Total output tokens | 1,752 | 2,052 |
| Largest response output | 608 | 858 |
| Actual output ceiling on every call | 40,000 | 40,000 |
| Settled USD | 0.023769150 | 0.023945700 |

Total settled cost: USD 0.047714850. Both arms stopped at the predetermined four
ordinary responses. They did not hit cost, input or output ceilings. No correction
was needed. Every requested read/search succeeded. No model-produced candidate
existed, so original/control replay, public regression, submission and independent
acceptance were NOT_RUN. Existing calibration replays are not new model verification.
The allocation is closed; unused funds do not authorize another run or continuation.

## Action evidence and limits

A searched `file_build`, read builder.py, searched `_build_namespace_module`, then
read manager.py. B also searched/read those locations, additionally found
`build_namespace_package_module`, and used its fourth response to search
`ast_from_file`. Neither used a diagnostic probe, investigated the captured
`tokenize_module` context exception, or read the Module stream implementation.
B's declared questions still focused on namespace names/search locations and the
pre-open builder route. This is observable action evidence, not access to reasoning.

The complete chain and nine public frames were present in B's actual first request.
They were therefore delivered, but a frame-guided diagnostic action was not observed
within four responses. More source coverage in B is not repair improvement evidence.
All searches yielded new source; these actions cannot simply be labeled duplicates.

The audit at `C:/pt/exception-frame-repair-analysis-v1/analysis.json`, hash
`sha256:081b6b4d40e481ca66cf7fe91df00489aab22032eb85dafe82cd37cad2dc6de7`,
verifies journal/CAS identities, all eight settled calls, actual first-request field
equality and B's complete frame count. It records the action sequence and token bounds.

## Interpretation and decision

The experiment did not reach the repair outcome it intended to measure. The four-call
horizon cut off both branches during inspection; it provides no estimate of whether
frames would improve a later edit. Its design was too short for these observed
trajectories. This is a limitation of the operator diagnostic, not evidence that the
ordinary runner has a four-call limit or that the model cannot repair this task.

The missing-frame defect is locally fixed. That information alone did not immediately
redirect these four B responses. Information salience, accessibility of dependency
source, task-versus-current-failure framing, model action selection and sufficient
inspection opportunity remain separate hypotheses. Request schema complexity is not
shown to cause these terminations: requests were valid and small. Raising the 60K
context or 40K output ceiling would not address the observed stop condition.

The next design decision is to make the current failed execution the clear starting
point of a stable debugging loop, with its public code reachable through the same
small inspection/edit/check surface. Completion certainty must not determine whether
a known exception can be diagnosed. Avoid adding another failure-specific mandatory
stage. Before another funded comparison, make the repair opportunity measurable:
either provide identical, already-observed relevant source to both conditions or
justify enough inspection responses from this trace, then retain a bounded edit and
host original/control/regression checks. Those designs answer different conditional
questions and require a recorded choice; no further experiment is approved here.

Only after usable evidence and a feasible action horizon are established should a
separate controlled model/reasoning comparison attribute stalled repair to capability.
There is no basis here for a broad context increase, a larger total budget, another
fresh solve, or a success claim. The existing finish blocker remains necessary.

ARS methodological scan: 11/11 checked. One adaptively selected candidate and one
pair, with no candidate produced, cannot support causal repair-rate or generalization
claims. No significance test is appropriate. Both failures and the restrictive
response horizon are retained; no successful subset was selected.
