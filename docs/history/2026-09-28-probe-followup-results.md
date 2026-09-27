# Selected failed-probe continuation: repair passed, verification closure incomplete

Date: 2026-09-28 KST. `official=false`; selected dev-train trajectory, not a fresh
solve or a matched comparison. Follows [funded preparation](2026-09-28-probe-funded-continuation.md).

## Execution and result

The user approved one toqito-1538 B2 continuation, gpt-5.4-2026-03-05 xhigh,
25,000 output ceiling, existing PatchLoop `.env`, new invocation cap $3.
The frozen manifest hash was
`sha256:f31d53616797b8f27d172380309ee288e5082016bcbfa3b2049cf17629707ff4`.
The first actual count and dispatch matched its funded request hash exactly.
Work counters and the 3,567-second active allowance were preserved. No historical
probe was replayed by the solver; no automatic retry or resume occurred.

Five new provider calls and five tool actions took approximately 226 seconds
including preparation/evaluation. Known new cost: **$0.685091**. The unused
**$2.314909 is closed**. Earlier unknown source billing remains separate and unknown;
the inherited bookkeeping total is not a complete historical invoice.

The final benchmark result is **EVALUATOR_PASS**, task acceptance PASS, safety PASS,
claim_eligible=false. Registered base-regression selected 14 tests, all passing.
Submitted patch:
`sha256:051bc0ad8f0cc4aeca528cc0ad8a681d81b79abe2fa357e391fea5b4613de34d`.

## Public evidence to action

1. The delivered failed classical-state probe changed the agent's submission plan.
   It read `_renyi_utils.py` to examine PSD matrix-power handling (turn sequence 485).
2. It used the last accepted mutation to re-Hermitianize the sandwiched operator
   and replace `float(np.real_if_close(trace_term))` with the real powered trace
   in `sandwiched_renyi_conditional_entropy.py` (action finished 507).
3. Its follow-up probe attempted the same classical expectation, but a mismatched
   parenthesis caused SyntaxError before repository behavior ran (finished 522).
4. The agent explicitly recognized this probe as invalid, then ran base-regression
   (finished 537) and submitted (finished 553), leaving the targeted post-fix
   behavior unverified within its own trajectory.

The failed probe's result was not mistaken for an implementation failure. Instead,
the agent substituted submission eligibility for resolving an acknowledged open
question. At the following inputs, `run_probe` was still exposed. Before submission,
the model saw 8 remaining calls, 56 tool actions, 3,378 seconds and $2.407754.
No accepted mutations remained, but that did not prohibit probe correction/rerun.
The model cited the absence of further mutations and optionality of experiments.
This is public decision evidence, not an inference about hidden reasoning.

## Separate operator verification

After the paid run ended, the original valid B2 program ran unchanged against an
isolated copy of the submitted patch in the same prepared probe environment.
It passed: uparrow 0.4568933936727783 versus expected 0.45689339367277615; downarrow
0.41503749927884404. Exit 0, no timeout, cleanup confirmed. No solver feedback or
additional paid call occurred; this does not retroactively repair its invalid probe.

The unchanged [15-case public matrix](2026-09-28-remaining-public-requirements.md)
was also rerun in the existing evaluator image as an operator public diagnostic:
**14 pass / 1 fail**, versus the prior **8 pass / 7 fail**. This is a selected case
set, not a benchmark score or a general success estimate. The remaining failure
is pure Schmidt probabilities (0.8, 0.2), alpha=0.50001: actual -0.556398021222833,
stable expected -0.3219409722687054, error about -0.234457 bits. The previously
identified underflow/clamp issue remains despite benchmark acceptance.

## Evidence and next question

- Live result: `C:/pt/probefollowup0928a/result.json`; branch `B2`, journal
  `run_dev_33068b6e257f423a`. Original journals and prepared boundary remain immutable.
- Frozen plan: `C:/pt/analyses/probe-funded-live-plan-20260928-v1/manifest.json`.
- Operator verification, public action/input trace and closed-funds receipt:
  `C:/pt/analyses/probe-followup-results-20260928-v1/report.json`.
- Review script: `C:/pt/audit_probe_followup_0928.py`; zero new provider calls.

The selected failed observation led to a real repair and benchmark acceptance.
It does not establish that removing the two system sentences generally improves
the harness: this is one selected branch with a separately funded continuation.
Next investigate why an invalid verification program permits closure of its still
unanswered question, distinguishing advisory policy from available actions. Do not
adopt a new default or tune to private evaluator details from this single result.
