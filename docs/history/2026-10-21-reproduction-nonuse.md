# Why the six verification-state runs declared no reproduction

The declaration feature was disclosed, but no model request selected it.
There is no rejected declaration or failed declaration execution to explain its
nonuse. This does **not** prove that the model understood the feature: delivery,
recognition, selecting a verification action, and binding that action are different
steps. The strongest observed mechanisms are substitution of helper/suite coverage
for the original requirement, late verification selection, and running a genuinely
needed reproduction without binding it.

This follow-up preserves the [closed six-run results](2026-10-20-verification-state-reduced-results.md).
It does not change their judgments, outcomes or frozen allocation. The question
matters because the proposed code-derived case state was never exercised, even
though the models sometimes investigated the original failure.

## Scope and method

- Frozen manifest: `68932078768e3297094f912a5561d6bd5d7d54c19cd5c9c39bc5f003e4f36300`.
- Execution commit: `8e308ab7920a9d78139e3eb07f8696afbacaded9`.
  Read-only diagnosis started at documentation commit `e5dbbfa9`.
- Six saved runs, 132 dispatched inputs/decisions, 134 requested tool calls and
  135 action receipts, including one automatic required-check recheck.
- Read exact public schemas, reconstructed current state, bounded public decisions,
  plans and receipts. Raw solver journals were inspected for event-type counts,
  not provider-response bodies or private evaluation payloads. Encrypted reasoning
  was not decoded or analyzed.
- New provider calls, input counts, probes and evaluator executions: **zero**.
  Runtime, transition rules, two references and resource limits: unchanged.

Evidence is in `C:/pt/verification-state44-declaration-diagnosis-20261021`:
`audit.py`, six row files, `summary.json`, `findings.json`, and the append-only,
hash-chained `run_dev_declarationdiagnosis44` journal. The inventory verifies
original public-artifact hashes and binds decisions to request/action identities.
Ten quoted passages were checked against their original event hashes. All 132
public decisions were reviewed; no new model judge was used.

## Exposure, selection and rejection

| Row | Inputs | Probe/declaration schema offered | Probe calls | Non-null declarations | Observed verification route |
| --- | ---: | ---: | ---: | ---: | --- |
| A1/OFF | 20 | 20 | 0 | 0 | Added helper regression; promoted its suite PASS to F0010-path coverage. |
| A2/OFF | 12 | 12 | 0 | 0 | Added namespace-type helper test; treated the required suite as the remaining verification. |
| A3/OFF | 37 | 37 | 3 | 0 | Two Pylint experiments and one helper experiment; all unbound. |
| B1/ON | 11 | 11 | 0 | 0 | Test-import edit rejected; then substituted suite PASS for the planned targeted test. |
| B2/ON | 40 | 37 | 0 | 0 | Deferred behavior verification while investigating source; late tool horizon constrained choices. |
| B3/ON | 12 | 12 | 2 | 0 | Two pre-edit helpers; explicitly considered a post-edit reproduction unnecessary. |

Declaration guidance remained in **132/132** system prompts, including every first
request and handoff. The same `run_probe` schema appeared in **129/132** requests.
It included the required nullable `reproduction` key, its five required object
fields, and the instruction to set it before an original-task reproduction.
All five probe calls explicitly generated `reproduction=null` and
`replay_action_id=null`. All 132 state views reported `no_bound_reproduction`
with an empty case list. No declared case was created and later lost.

OFF means the new **verification-state separation** was disabled. Both arms
retained declaration and action replay. `probe_policy=none` disables the older
saved-case fields, not `run_probe.reproduction`; none of these schemas required
`save_program` or a separate registration action.

All 132 generations settled and produced recorded decisions, with zero protocol
corrections. All five probes reached execution and returned successful tool
receipts. A3's last probe had process exit 1 because its behavior assertion
failed; that is a diagnostic observation, not a declaration-admission failure.
The three tool-contract rejections were B1's test import edit and B2/B3's reads
exceeding the 400-line limit. None concerned reproduction metadata.

The structured public narratives contain no explicit discussion of declaring or
replaying a bound case, `expected_json`, or `reproduction_review`. This absence
and null arguments cannot establish whether the model overlooked, misunderstood,
or deliberately bypassed the formal binding. They do establish nonselection.

## What the trajectories distinguish

**A3 disproves the broad claim that no model felt a need for original verification.**
At decision 356/input 354 it requested Pylint execution to identify the actual
failure before editing. At 461/input 459 it explicitly said the registered suite
passed but the exact public reproduction remained a material gap. It executed
Pylint on the current candidate, observed F0010 at receipt 465, and continued
investigating at 476 rather than declaring completion. Both original-task
experiments still used null declaration metadata.

This is a separation between **recognizing the need for a reproduction** and
**selecting the binding protocol**. The public record gives no reason for that
second omission. The early Pylint program also inserted the temporary root into
`sys.path`; the later program did not. They are not a fixed before/after comparison.
Its eventual cost stop explains curtailed follow-up, not the earlier null fields:
the three probe inputs still showed 16, 12 and 9 model calls remaining.

**B3 provides the clearest explicit sufficiency judgment.** At 85 and 99 it ran
helpers to choose a repair, with null declarations appropriate to their exploratory
scope. At 145 it still planned a post-edit missing-init check. After only the
registered suite, decision 176 said:

> I did not add a second targeted reproduction after the fix because the current-diff regression result and the narrowly scoped source change already cover the public failure branch

The finish input still offered `run_probe`, showed 29 model calls remaining and
about USD 0.626 remaining before that request. Its old probes were marked
historical and original coverage unassessed. This was an observable choice to
treat the available evidence as sufficient, not a probe admission failure.
Its mistaken directory-input interpretation already appeared before source loss.

**A1/A2 took the ordinary test route.** Their initial plans included a focused
regression; both added helper tests and ran them through the suite. At A1 decision
299 the agent promoted the namespace/location result to executed F0010 coverage.
At A2 decision 156 it reduced the remaining plan to suite PASS followed by finish.
These were attempts to verify behavior, but they did not establish the original
Pylint-to-helper connection. Declaration count alone would miss their test work;
the current declaration surface attaches only to `run_probe`.

**B1 encountered a real, different obstacle.** Its import modification in the test
file was rejected at receipt 132 by the additive-test contract. At decision 143 it
revised the plan to revisit the test only if the mandatory suite exposed a gap,
then claimed completion at 160. This obstruction explains a branch in its
verification plan, but declaration was never attempted. The final input still
offered probes and showed 30 model calls remaining.

**B2 encountered late resource gating after repeated deferral.** Its first 33
decisions were reads/searches. At inputs 453 and 467, the protected completion
horizon removed optional probes while reserving edit/check/finish resources.
After suite PASS, probes reopened at 483, 498, 512 and 527, with 5, 4, 3 and 2
model calls respectively. The model spent these on more reads/searches; at
decision 529 it was still deciding whether a focused probe was worth running.
The last input 542 had one model call left and offered only finish/stop.

Thus its final lack of a probe option was real. It cannot explain all nonuse:
37 earlier inputs offered it, including four after PASS. No declaration was sent
and rejected. Late selection plus the fixed horizon constrained this row; removing
all limits is not warranted by this diagnosis.

## Design friction and limits of the causal explanation

The implementation creates a binding only for non-null metadata in
[`reproduction.bind`](../../patchloop/dev/reproduction.py). Plans, concerns,
questions and assertions do not create one. The new state logic can preserve and
compare a declared experiment, but it depends on the model independently choosing
that five-field mode. General reminders and a permanently UNKNOWN requirement do
not themselves connect a planned check to an executable case. This is an observed
activation dependency, not proof that an extra reminder would fix it.

There is also a concrete output-contract mismatch between the two uses of the
same tool. The delivered [`run_probe` description](../../patchloop/dev/tools.py)
encourages intermediate progress prints and printing **or asserting** observations.
Its declaration suffix requires exactly one JSON value. Existing
[`observation_json`](../../patchloop/dev/probe_cases.py) also requires exit zero.
Applying that pure parser to saved outputs, without executing anything, finds:

| Existing observations | Parser result |
| --- | --- |
| A3 decisions 356/414 and B3 85/99 | `stdout_not_json`: progress/Python-dict output, Pylint text, or multiple records. |
| A3 decision 461 | `execution_not_healthy`: assertion fails before its JSON print, leaving stdout empty. |

These are **not recorded declaration failures**: every program was unbound.
They show why simply adding declaration metadata to the same program would not
satisfy the structured-observation prerequisite, even if the named call were
observed. Assertions that detect the expected bug remain useful public evidence;
the comparator's eligibility label must not be read as an infrastructure failure.
The competing instructions and extra authoring requirements are plausible friction,
but there is no observable statement attributing nonuse to them.

The result changes the next design question from "was the feature absent?" to:
how should selecting an original-requirement check connect its caller/setup,
expected observation and program identity in the ordinary verification flow?
A small candidate change would bind that explicit choice within the existing probe,
separate progress output from the comparison value, and preserve failed behavior
observations without inventing issue coverage. Helper probes remain useful and
should not be automatically promoted to original-task evidence.

That candidate is **not implemented or live tested** here. A3 also demonstrates
that an agent can use a refutation without a bound case. Declaration usage alone
would not establish better judgment or repairs; these remain separate outcomes.
No new completion gate, budget increase, transition change or paid follow-up follows
from this audit. Runtime behavior is unchanged.
