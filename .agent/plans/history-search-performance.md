# Does optional evidence search improve repairs?

Status: **OFFLINE PREPARED; PAID NOT AUTHORIZED** (2026-10-20). The proposed allocation
is new; old approvals and unused balances do not transfer. Every run is
`official=false`, claim-ineligible. Runtime baseline: `1ce3a18`.
Preparation and the bounded execution wrapper live at `C:/pt/historyperf25/`.
`manifest.json` binds the final commit, source/runtime and local receipts; only a
successful `execute.py validate` confirms that its identities still match.

## Question and comparison

Does offering the current run-local evidence-search tool improve actual repair
success under the same resource limits? The
[saved-input replay](../../docs/history/2026-10-20-history-full-input.md) found
better original/caller delivery but additional size handoffs and lost counterchecks.
It did not measure model-selected queries, interpretation or completed repairs.
Do this comparison before another retrieval/context change.

| Arm | Sole assigned difference |
| --- | --- |
| A | `history_search_policy=none` |
| B | `history_search_policy=public-v1`: current tool, instructions and ordinary retention support |

Use the **same current runtime and fresh task starts** in both arms. Both receive
the same Pylint 2.12.2 prepared environment and ordinary caller disclosure. Neither
receives a saved observation, query, plan, checkpoint, patch or operator hint.
Do not use the old failed runs as A: runtime and starting conditions have changed.
The model chooses whether, when and what to search. A still has normal source
reads/searches and probes. B searches only public evidence previously delivered
within that particular fresh execution; no old experiment logs enter its corpus.

This estimates the effect of offering the complete feature, including its prompt,
attention, action, token and transition costs. It does not isolate ranking from
rendering, or force equal actual transition counts. Use rates among search users
are descriptive: users and non-users are not randomized subgroups.

## Exact proposed scope

- Task: `tasks/dev-train/current-dev20/13/public.yaml`,
  `swebench-lite-dev-pylint-dev-astroid-1333`, base
  `d2a5b3c7b1e203fec3c7ca73c30eb1785d3d4d0a`.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000,
  standard/global Responses, `store=false`, zero SDK retries.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`. Offline preparation
  must intercept credential loading and provider construction, count and generation.
- Six fresh rows per arm, twelve total. Serial alternating blocks:
  `A1 B1 B2 A2 A3 B3 B4 A4 A5 B5 B6 A6`. These are order blocks, not matched seeds.
- USD **0.88 per row**, **5.28 per arm**, **10.56 invocation-wide**. Each row has
  `repeat=1`, an independent workspace/state root and its own fixed allocation.
  No transfer, top-up, retry, replacement, continuation or paid judge.
- Per row: 40 model calls, 100 tool actions, four accepted mutations, 1,800 active
  seconds including a 330-second evaluation reserve. Keep other `DevLimits`.
- Same `segmented-v1`, `result-or-size-v1`, `brief-v1`, current agent policy,
  probes on / policy `none` / recheck `none`, repair recheck on,
  `protected-v1` inspection and `per-call-v1` cost admission.
- Two open-question references; 24,000 retained source characters; 60,000 counted
  input tokens; 1,048,576 request bytes; 262,144 bytes per encrypted item.
  B keeps eight results, whole originals first, current 48k overflow/page behavior.
  No boundary, ranking, rendering, reference or budget changes during collection.
- Prepared source: `C:/pt/ld20p01/s/13/prepared-source.json`. Both arms use exactly
  `C:/pt/calleruptake18/preparation-v2/B/prepared-probe-dependencies.json`.
  Verify complete dependency/source identities and existing probe/evaluator images;
  do not start Docker Desktop or pull/build an image.

The selected task has demonstrated evidence loss and supports a small mechanism
screen, but it is heavily development-exposed. Six repetitions estimate local
variability only; they cannot establish cross-task or held-out improvement.
Historical pricing is a preparation reference, not a current quote. Review current
rates before dispatch; any mismatch stops admission without changing the cap.

## Outcomes and causal interpretation

Primary result: number of independently accepted repairs in each assigned set of
six. A repair requires the **exact submitted patch** to pass native acceptance and
the original public caller failure case plus its initializer-present preservation
control. Report registered evaluation, native evaluation and each public control
separately; a helper/test PASS or submission alone is not success. Seal public
mechanism annotations before opening the fresh outcome grades. No grades or
post-run programs/results are fed back into a solver.

Track each axis separately, using YES / NO_OBSERVED / UNKNOWN / NOT_RUN:

| Axis | Required evidence |
| --- | --- |
| Acquisition | Relevant caller/source/program/setup/result first enters an actually dispatched input through ordinary actions. Search cannot recover an observation never acquired. |
| Opportunity | Previously delivered relevant evidence is absent from the current input before a model-selected search. Record this in both arms, including cases with no loss. |
| Search exposure/use | Actual tool schema delivery and model-selected search/fetch/page calls; distinguish offering, attempting and obtaining useful results. |
| Recovery/delivery | Returned original record/hash/range reaches a subsequent dispatched input; identify what was restored and what context was displaced at that input. A stored tool result alone is insufficient. |
| Interpretation/use | Subsequent explicit decision, probe or edit uses the recovered caller, environment, input and countercondition correctly. A citation or repeated name alone is insufficient; silence is not proof of non-use. |
| Repair | Frozen independent outcomes on the exact final submitted patch, as above. |

Record original/returned/current diff identities, setup, known counterconditions,
staleness, source re-reads, repeated checks, search counts, handoffs by cause,
actual input/cached/output/reasoning token usage, total settled cost, elapsed time,
and output-ceiling reductions. Do not decrypt or interpret opaque reasoning.
Record whole originals versus reduced fields/pages and new evidence losses.

Report success counts with all six assigned rows as the denominator, accompanied
by submitted / FAIL / ERROR / NOT_RUN counts; do not silently treat unknown grades
as task failures or drop unfinished rows. Report arm-total and per-row cost/time;
cost per accepted repair is undefined for an arm with zero accepted repairs.
Do not claim causal mediation merely because a successful B row used search.

Competing explanations: relevant evidence was never acquired; it was available
without search; the model did not search; the query/ranking missed it; delivery
displaced another necessary fact; the model misapplied accurate evidence; or the
remaining repair/budget problem persisted despite correct use. Assign a failure
location only when public traces support it; otherwise retain UNKNOWN.

## Decision and execution discipline

Complete the fixed panel without result-dependent stopping or retuning, except
the existing hard stops. A local follow-up signal requires at least two more
accepted repairs in B than A, with useful recovery and supported application
observed in at least two successful B rows. This is a screening threshold, not
statistical proof, a runtime adoption rule or authorization for another panel.
Report smaller differences as inconclusive. If both arms rarely need history,
the mechanism is not exercised; if B recovers evidence but repairs do not improve,
do not describe recovery as a repair-quality gain. Keep the default off pending
the result and a separate decision. No automatic task expansion or extra repeats.

Before collection, bind the final commit/runtime, this specification, all twelve
resolved requests, complete source/dependency/image identities, actual initial A/B
inputs and their exact allowed differences, validation receipts and execution code
in an external immutable packet. Generated state uses append-only `dev-run-v1`.
Compare complete initial requests, normalizing only derived segment IDs and the
declared search tool, exact instructions and available-tool entry. Unexpected
differences stop preparation. Preparation is not a solve or an outcome observation.

Reuse the existing serial one-row `parallel_dev_batch.run_parallel_rows` execution,
`caller_uptake_execution.Allocation` and `due_receipts` contracts for the same
twelve-row/cap layout. Revalidate the bound packet before each row. Settle usage
and owned cleanup before advancing. Count/transport/billing/cleanup uncertainty
stops the remaining rows; known row-level budget exhaustion is recorded unchanged.
No model dispatch until exact task/model/credential/repeats/cap authorization.

After the public audit is sealed, allow at most two caller controls and one native
assessment per submitted patch: at most 24 caller checks and 12 native evaluations,
no paid calls. Use the existing pinned oracle, complete submitted patch for native
acceptance, source projection for the external caller controls, and preserve their
distinct patch hashes. Each patch shares the existing 600-second post-run deadline
with native tests bounded to 300 seconds. ERROR or uncertain cleanup stops the
remaining assessments; preserve partial results without retrying them.

The first-input comparison used the real runtime and local images with an adapter
that stops before counting/generation. The only state difference was the search
availability entry. A bare-schema/suffix assumption in the initial comparison
script was corrected against the registered ordinary decision wrapper and segment
instructions; saved captures were reused without rerunning a solver. These are
preparation checks, not retrieval-use or repair outcomes.

Routine preparation uses focused contracts, the quick suite and included isolated
mock evaluation, not the 5,000-test suite. The prior four full-suite failures remain
disclosed; do not describe this as a full-suite pass. Any failure affecting this
experiment's current execution path must be resolved before paid admission.
