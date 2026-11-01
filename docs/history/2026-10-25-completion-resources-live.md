# Completion resource pilot: oracle mismatch before repair

Date: 2026-10-25. Status: completed, allocation closed. `official=false`,
`claim_eligible=false`. Material passport: academic-research-suite /
experiment-agent / run; verification status ANALYZED, not independently rerun;
version `completion25-live-v1`.

## Question and frozen design

The [40K diagnosis](2026-10-25-output40-diagnosis.md) identified a completion
forecast that reserved an unreachable failed-finish step after reusable early
replay, coupled normal/correction output allowances, and no diagnostic opportunity
after a failed candidate near the protected horizon. These mattered because the
previous run received three comparable F0010 failures but never repaired them.
The [local follow-up](2026-10-25-completion-resources.md) implemented all three.

This run asked whether those changes enabled useful diagnosis and repair within
the same USD1.20 cap. It was one fresh solve, compared descriptively with the one
historical exposed-task trajectory. The three interventions are bundled; neither
causal attribution nor generalization is identified. Alternatives recorded before
dispatch included unused/unhelpful diagnosis, an incorrect repair hypothesis,
insufficient money, correction output exhaustion and stochastic trajectory change.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; credential file `.env` (contents not
  printed). Normal output 40,000, independent correction allowance 25,000.
- One repetition, USD1.20 invocation-wide cap; 40 model calls, 100 actions,
  four accepted edits, 1,800 active seconds, 1,920 seconds outer supervision.
- Same `run_probe` recommendation, segmented-v1 / result-or-size-v1 / brief-v1,
  probe policy none, bounded-v1 acquisition, repair-recheck, protected-v1,
  completion-recovery-v1 and prior prepared source/dependencies/images.
- At most two frozen post-submission public checks shared 120 seconds, conditional
  on a settled eligible submission. Count/billing/transport/cleanup uncertainty,
  input drift and resource limits stopped work. No retry, resume or cap increase.
- Runtime commit `cf17c24815c039cbe11ec40a87ea8b8c45758919`;
  runtime hash `sha256:5cd77b68f855dfe592a5f498552ffe0af2f54866edb40f2670df1ce565259327`.
- Baseline commit `fbc7f42edd8adf72e677e6dda988ae573051de22` and run
  `run_dev_fd87d80110a643b5`; its correction allowance remained coupled at 40K.

The preregistered decision rule required original acquisition, comparable candidate
success, required checks, full submission, frozen public checks and independent
acceptance for repair. Delivery, extra actions or submission alone were insufficient.
If no failed candidate occurred, failure-feedback uptake was NOT_OBSERVED.

## Result

Run `run_dev_1947ccb8339d4f9c` lasted 871.532 seconds (14m32s) and ended
`INCOMPLETE_RESPONSE`. Billing/counting were known; USD1.080337500 was settled,
leaving USD0.119662500 unused. There was no submitted patch.

| Measure | Historical 40K run | Current 40K / correction25K run |
| --- | --- | --- |
| Model calls / tool actions | 31 / 34 | 30 / 28 |
| Cost | USD0.869725350 | USD1.080337500 |
| Accepted edits | 3 | 0 |
| Original acquisition | acquired | not_reproduced |
| Candidate original replay | three comparable F0010 failures | NOT_RUN |
| Public regression / submission / acceptance | NOT_RUN | NOT_RUN |
| Terminal | COST_CAP_REACHED | INCOMPLETE_RESPONSE |

The current actions were two authored probes, 12 searches and 14 reads. Mutation
was offered from model call 4; no mutation was requested. Formal completion remained
`unverified`. Independent acceptance, safety and the two post-submission public
checks were NOT_RUN. This is a failed solve, not evidence of a successful repair.

## Failure path in public evidence

1. The first response produced a probe after 18,843 output tokens. Its program used
   `reproduction_workspace()` as a Path even though the helper returns a string.
   `root / "bug"` raised TypeError before the target caller ran. Gateway receipt
   success did not mean probe execution or original acquisition succeeded.
2. The second probe wrapped that string in `Path` and actually called
   `pylint.lint.Run(["src/project"], do_exit=False)` in both fixture trees.
   Missing `__init__.py`: complete per-call stdout contained F0010 and
   `Unable to load file src/project/__init__.py`; stderr was empty. The control
   produced C0114/W0611 on stdout and no F0010.
3. Its authored predicate checked only stderr:

   ```python
   has_parse_error = ("F0010" in stderr) or ("Unable to load file" in stderr)
   ```

   Thus `observed_json` was false/false, matched the desired JSON and mismatched
   the declared failure JSON. The raw original symptom was observed, but the
   authored observation did not establish a qualifying original failure.
4. The exact next dispatched model input contained those complete per-call
   captures, unchanged. In the following public annotations the model stated that
   the fixture had not emitted the reported parse error and shifted to source
   inspection. This contradicts its delivered stdout. This finding uses public
   tool annotations, not private reasoning. The later 26 inspections never
   corrected the probe or produced a mutation.
5. The acquisition projection released after two original attempts, including one
   setup failure. It retained `not_reproduced` and did not treat desired JSON
   matching as repair. No acquired failed candidate existed to trigger the newly
   reserved diagnostic opportunity.
6. At call 29, the physical protected horizon left only `replace_text` and
   `stop_task`. Monetary admission reduced the normal ceiling to 15,154 tokens,
   preserving USD0.248652 for two minimum successors plus the one correction.
   All 15,154 output tokens were reported as reasoning output; no tool call arrived.
7. Call 30 consumed the reserved correction with an admitted 25,000-token ceiling,
   retaining USD0.091152 for two minimum successors. It also ended at its output
   ceiling without a tool call. The one correction credit was exhausted, so the
   run stopped even though USD0.119662500 remained. This was not a denied
   correction dispatch or an unknown billing failure.

Offline classification of the already-recorded stdout plus stderr changes the
two flags to true/false. That is a text audit, not an executed corrected probe,
retroactive acquisition, repair or acceptance. It was not fed back to the solver.

## Mechanisms and decision

- **Independent correction budget was exercised.** Initial correction reservation
  was USD0.1575 instead of the historical USD0.225. The actual recovery used the
  separate 25K ceiling, but did not produce a valid action. Reservation mechanics
  worked; adequacy for this response did not.
- **Reuse-aware savings were not exercised.** All dispatched states retained
  `early_replay_reusable=false`; there were no candidate edits or automatic
  original replays. Local validation remains the evidence for that positive path.
- **Bounded failure diagnosis was not exercised.** No dispatched diagnostic
  opportunity, selected diagnostic or subsequent repair uptake occurred. Its
  prerequisite was missing, rather than its allowance being observed too small.

The decision is to retain the local mechanism evidence without claiming live
repair gain or treating this single worse trajectory as a causal regression. The
next concrete bottleneck is the relationship between actual diagnostic output and
the authored observation: a baseline oracle that calls the reported failure
"absent" should be checked against its captured evidence before source repair
planning inherits that interpretation. A small offline channel/predicate check
would distinguish that issue from capture loss; this record does not implement it
or authorize another paid run. Merely raising output cannot correct the already
observed channel error. Whether a stronger/bigger response would choose a useful
repair remains unresolved.

## Evidence and integrity

External ready root: `C:/pt/completion25-live-ready-v1`; result root:
`C:/pt/completion25-live-v1`. Request, authorization, preflight, source inventory,
exact command and supervisor were sealed before dispatch. Existing images were
used; Docker was not started and no images were pulled or built.

- Request: `sha256:3a239ed91c70bed8171fa4d635545f911a316a3806a9a8fe10e36c5ed4df88b1`.
- Collection: `sha256:042202203cc0c74318a4c76182dd88a6f6e378bc848231a6b84040e9b5443118`.
- Public analysis: `sha256:300192d93fcd5585ef9780c15bdc6e574c87b1c275eff45f2255aa58598285e5`.
- Mechanism analysis: `sha256:7f600bf0db709629e694c6bbb89c844aa23102cc6f2b30b6ad6e1260bfb3a268`.
- Predicate/delivery audit: `sha256:ee5eb789d50d829067bfe4d3348e0d70507602570be1d463d264ca285c89a3c4`.

All 111 sealed repository inputs remained unchanged during execution. The collector
checked 157 content-addressed objects, hash-chained journals, matching completed
provider calls and all action_id/input_hash pairs. No cleanup failure or timeout
was recorded. Private evaluator/continuation objects were only hashed; their
contents were not used. Total token metadata: 1,293,432 input (625,280 cached),
118,295 output including 108,790 reasoning tokens. Reasoning tokens are not added
again to output. Post-run analysis executed no model, probe or evaluator.

The operator and preparation journals close the one authorized allocation; unused
budget is not transferred. Documentation validation and the final docs commit are
bound in the external closeout receipt. No runtime changes were made in this run.
