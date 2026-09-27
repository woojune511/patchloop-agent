# AnyIO: two fresh solves with the corrected probe environment

Date: 2026-09-27. User-authorized steps 1 and 2: fresh full solves and a public
information/action/result audit. `official=false`, `claim_eligible=false`.
No harness ablation, prompt change or automatic baseline adoption.

## Question and fixed execution

The earlier supplied-candidate repairs and operator replays did not establish
whether the agent could investigate, repair, verify and submit from the public
issue within its original budget. This packet tests that full path with the
corrected pytest probe dependencies. It is not an old/new environment A/B.

N1 then N2 each started from the prepared base, with no prior candidate, probe
program/question, operator observation, notes or earlier model context. Both used
AnyIO dev-train v3, `gpt-5.4-2026-03-05`, xhigh, desired output 25,000, brief-v1,
segmented-v1/result-or-size-v1, probes enabled/probe-policy none, repair-recheck,
protected-v1 and per-call-v1 completion-cost admission. Limits remained 40 calls,
100 actions, four mutations and 1,800 seconds per run, with 60K maximum counted input.

Credentials came from the existing repository `.env`; no value was recorded.
Budget was $1.20 per run and $2.40 for the invocation, with no transfer, retry,
replacement or resume. Actual input counting preceded dispatch; SDK retries were
zero. Uncertain transport/count/billing/continuation/cleanup would stop both slots.
Settled ordinary task/resource failures could proceed to the next planned slot.

The source, dependency inventory and existing digest-pinned images passed preflight.
No Docker startup, image pull/build, source fetch or dependency resolution occurred.
Runtime hash remained `sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.
The selected-pytest manifest was
`sha256:ae8d0a01dd8c67305ea620a885a75c73344979104f6d067e83dc3aebc79f143e`.

## Results

| Run | Submission / acceptance / safety | Calls / mutations | Cost | Run time |
| --- | --- | --- | --- | --- |
| N1 | No / NOT_RUN / NOT_RUN | 11 / 2 | $1.176096 | 552.74 s |
| N2 | Yes / PASS / PASS | 8 / 1 | $0.678853 | 359.20 s |

N1 ended `COST_CAP_REACHED`; N2 ended `EVALUATOR_PASS`. Total recorded usage was
$1.854949 of $2.40, with $0.545051 closed unused. Billing was known and there were
no infrastructure stops. Three of four model-authored probes completed with usable
behavior output. One failed its model-authored setup assertion, not dependency
loading or a timeout. Eight owned check/probe containers were confirmed absent.

N2's final diff passed lifecycle 7/7 and upstream 32 tests, with three deselected,
before submission. Its submitted patch hash is
`sha256:0f9dbed48d374fee45a8a92df548b2ec090201fb8a25113b0249f01b90de21f7`.
The isolated evaluator supplied the aggregate acceptance/safety result; its private
details were not used in the public behavior analysis or sent back to the model.

## N1: useful observations, failed repairs, budget-limited recovery

1. Calls 1-2 searched and read the plugin, asyncio runner, Trio runner and interface.
   Call 3 (seq 56) probed the unmodified runner: KeyboardInterrupt propagated, the
   shared task remained alive, and later fixture teardown executed `post_interrupt`.
2. Call 4 (seq 70) changed cancellation handling. Its stated hypothesis added that
   the awaiting `_call_in_runner_task` task was cancelled when `run_until_complete`
   was interrupted. The probe had not measured that caller's cancellation state.
   The edit cancelled the shared runner only if that caller had `cancelling() > 0`.
   Call 5's lifecycle check passed 4/7; all three interrupt cases still resumed.
3. Call 6 (seq 100) tried to measure caller cancellation with an instrumented probe,
   but asserted `wrapped.__name__ == '_call_in_runner_task'`; the actual name was
   `wrapped`. It stopped before installing the wrapper, with no behavior stdout.
   That intended discriminator therefore provided no cancellation-path observation.
4. Calls 7-8 inspected cancellation code and `Runner._on_sigint`. Call 9 (seq 148)
   stored, cancelled and drained the per-call task on KeyboardInterrupt. Automatic
   recheck still passed 4/7, now also reporting incomplete cleanup and task/context
   mismatches in interrupt cases. The SIGINT analogy did not establish this ordering.
5. Call 10 (seq 166) produced useful observations on the second patch: the test
   resumed, the runner ended cancelled, and teardown raised `ClosedResourceError`.
   Call 11 reached its reduced 4,081-token output ceiling with only a reasoning
   item and no tool call (`incomplete`, `max_output_tokens`). The next count could
   not admit another response within the cost cap. No further repair or submission
   occurred. This is resource-limited NOT_RUN, not a submitted wrong answer.

The visible gap is between what the first probe measured and what the repair
hypothesis claimed it confirmed. Failed recovery, a malformed diagnostic and final
resource exhaustion are separately observed. This trace does not prove that any
single one alone caused the terminal outcome, or that more budget would solve it.

## N2: source and observation lead to a successful first repair

Calls 1-3 followed the plugin's leased runner to asyncio TestRunner. Call 4 (seq 63)
independently probed the baseline, including a manual loop re-entry before teardown;
`post_interrupt` appeared on that re-entry with the shared runner still alive.

Call 5 (seq 77) changed `run_test` to retain its call task, cancel the shared runner
when the call remained incomplete on a BaseException, and drain the call. It also
kept the shared runner loop alive after per-call cancellation. Unlike N1's first
edit, cancellation did not depend on the caller task already being cancelled.
The public plan still labeled preservation of fixture behavior as untested.

Calls 6-7 passed both registered checks on the same diff. Call 8 (seq 123) submitted,
explicitly limiting its public verification claim to executed checks. The original
probe was not rerun on the final patch, and the ordinary-cancellation plain-fixture
same-task assertion gap remains a limit of that visible check. Do not substitute
the earlier operator replay of different candidates for evidence on this patch.

## Implication and remaining question

The corrected environment supported independently chosen, relevant observations
in both full solves. One completed within the original cap; one did not. Probe
availability and successful reproduction were insufficient to ensure a correct
repair. These two selected runs are not a general success-rate estimate, a paired
environment-effect result or proof of a planning/memory mechanism.

The next useful causal question concerns unsupported premises in repair decisions
and execution ordering during cancellation. Before selecting a harness ablation,
isolate a concrete distinction from N1's public trace. Additional generic warnings,
mandatory probes or larger budgets are not established fixes. Step 3 was not run.

## Evidence and validation

Packet: `C:\pt\analyses\anyio-fresh-solve-20260927-v1`; live immutable state:
`C:\pt\anyiofresh0927a`. The packet contains protocol, frozen controls, pricing,
preflight, metrics, per-run public timelines, actual-input/action links and closure.
All 19 dispatched inputs matched saved segmented state; 20 input-count requests
and their dispatch bindings verified, as did continuation records and the three
live journal chains. Both initial inputs matched after excluding only model-field
normalization and measured/derived start identities; both requests use the same model.
The separate four-event audit journal verified, and 103 protected input/history
files plus runtime were unchanged before documentation updates.

The [official pricing page](https://developers.openai.com/api/docs/pricing) was
fetched: Standard short-context GPT-5.4 input/cached input/output rates were
$2.50/$0.25/$15 per million tokens. Cache-neutral accounting is diagnostic only;
the per-run cap uses recorded settled usage, not hypothetical uncached cost.

Wrapper/analysis Ruff passed. Seventeen focused checks passed in 66.63 seconds,
including collector stop/cap controls and mock solves reaching isolated evaluation.
Five documentation layout/link tests and Git whitespace validation passed.
No PatchLoop runtime code changed; its full regression suite was not rerun.
