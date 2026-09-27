# Original-input pilot: three fresh attempts

Executed 2026-09-28 KST. `official=false`, `claim_eligible=false`.

## Question and fixed boundary

After separating source/image/dependency preparation from solving, can the selected
agent finish three original-input tasks within the fixed per-task allowance?
User authorized the exact proposal with "진행해줘": toqito, MontePy, darts, one
fresh attempt each, `gpt-5.4-2026-03-05`, xhigh, desired output 25,000, $1.20 each,
$3.60 aggregate, credential `C:/Users/geonj/Documents/PatchLoop/.env`.
No budget transfer, fresh retry, continuation, hint injection or sample replacement.
The existing bounded in-run protocol correction remains part of the frozen runtime.

Runtime commit `616a60f9f8db2b587c587ef34be7b7668364cc04`; runtime hash
`sha256:850942479181d7ce55199c21f08aa0221edd9bbaaa71098ca13ce6521b51b1de`.
Baseline policies, task hashes, prepared sources and dependency profiles match
[the pilot protocol](../../.agent/original-input-pilot.md) and the frozen draft:
`C:/pt/analyses/installed-limit-probes-20260927-v1/execution-draft.json`, raw hash
`sha256:4a63178abbb1f237b5cdb3fa56cfa07d85798839161e2d7501cfbfc381ababfb`.

## Results

| Task | Terminal / correctness | Submitted | Model calls / tools / edits | Active seconds | USD |
| --- | --- | --- | --- | --- | --- |
| toqito-1538 | COST_CAP_REACHED / NOT_RUN | No | 9 / 15 / 1 | 598.731 | 1.1853010 |
| MontePy-933_interface | EVALUATOR_PASS | Yes | 10 / 16 / 1 | 215.302 | 0.6193025 |
| darts-3065 | EVALUATOR_PASS | Yes | 5 / 5 / 1 | 177.214 | 0.2845970 |

Total recorded model-rate cost: **$2.0892005 / $3.60**. The unused $1.5107995 is
closed, not a future allocation. All provider calls and input counts have settled
journal outcomes; no unresolved transport/billing/cleanup state was found. No owned
PatchLoop container remained at the final check. These are usage-derived costs,
not an independently reconciled provider invoice.

Resolved/submitted: **2/2**. Resolved/planned: **2/3**. Submission: **2/3**.
Both submitted tasks have task acceptance PASS and safety PASS. Toqito has no
submitted patch or isolated correctness evaluation; its unsubmitted edit is not
an evaluated wrong answer. All three passed runtime environment preparation.
The selected sample is a development pilot, not a general success-rate estimate.

Original issue descriptions were verified verbatim in all three saved first model
requests. Original private evaluation ran only after submission and was not returned
to the solver. Scores use the pinned original test patches/F2P/P2P and selected
upstream parser/grading functions; this is not full upstream CLI execution.

## Public information to action

### Toqito

The agent located the existing conditional entropy API and tests, inspected related
entropy helpers and optimization usage, then wrote two diagnostic probes itself.
These were not operator-added registered checks or preparation canaries.

Probe 1 exited zero but contradicted the proposed local BFGS method at alpha=0.5:
the numerical value differed from the agent's proposed pure-state target by about
-0.32525. Probe 2 changed to derivative-free optimization: its pure-state difference
was about 3.8e-15, while its classical-quantum result still differed from the agent's
proposed target by about 0.08725. Neither target formula is established merely by
this self-authored probe. Successful process exit did not prove mathematical validity.

The agent then read shared helpers and made one large in-place extension with special
cases and a Powell fallback. The edit-producing eighth call cost $0.3555395 and used
19,560 output tokens, including 14,349 reasoning tokens. Recorded prior spend was
$0.7357595; after that call only $0.108701 remained. The next counted input was
42,012 tokens, so per-call admission reduced output from 25,000 to **244 tokens**.
That response used all 244 as reasoning, returned no tool call and cost $0.094002.
The existing protocol correction prepared another request, but cost admission stopped
it before dispatch. There were zero registered checks and no finish action.

Observed failure: exploration and edit production left insufficient budget for checks
and submission. This supports a completion-budget investigation; it does not prove
that more funds, fewer probes, another policy, or the untested edit would solve the task.

### MontePy

Reads/searches traced `Cell.universe` through `UniverseInput` and the property factory,
including default-universe bookkeeping. The agent added 17 lines in `montepy/cell.py`
to handle None and deletion, with linked-problem universe-0 handling and truncation
reset. One existing base-regression check passed, then the agent submitted the same
diff; original isolated evaluation passed. No custom probe or extra test was added.
The public changed-line report was unavailable/unknown, not coverage evidence.

### Darts

Two source reads connected the failing static-covariate mapping to categorical
output-column construction. The agent changed 12 added / 4 removed lines to respect
the fitted encoder's actual output columns. Eight existing public tests passed; the
same diff was submitted and passed original isolated evaluation. No custom probe or
extra test was added. This five-call path finished within its own allowance.

## Execution and evidence

Operator drivers live outside the repository. Their pre-dispatch checks initially
misinterpreted the source descriptor hash as its content hash (v1), then supplied a
task directory where run_dev requires public.yaml (v2). Both failed before any count,
provider call or task run was created. Those artifacts remain preserved. V3 corrected
only those operator bindings, used unchanged runtime/task bytes, and executed the
three authorized fresh attempts. It was not a retry of a started agent attempt.

The sequential driver bound the three $1.20 requests (sum $3.60), prohibited existing
state roots, verified identities, and checked terminal/accounting/cleanup evidence
before advancing. Each run_dev invocation enforced its own cap; funds were never
transferred. No runtime implementation or agent policy changed during the pilot.

Evidence root: `C:/pt/analyses/original-pilot-live-20260928-v3`.
Hash-chained journal: `runs/run_dev_originalpilot0928.jsonl`.
Public action/cost audit: `public-process-audit.json` (also content-addressed and journal-bound).
Driver: `C:/pt/original_pilot_live_0928_v3.py` (hash recorded in authorization event).

Run state roots are `C:/pt/runs/original-pilot-<task-name>-proposed-v1`:

- toqito: `run_dev_33068b6e257f423a`.
- MontePy: `run_dev_2af5f8fa68d34a28`.
- darts: `run_dev_3b3bf6a8bfc148a8`.

## Next question

Investigate how completion-cost admission can preserve a feasible check/submit path
before an expensive edit call consumes the remainder. First audit the existing
completion-reserve policy against this saved trace, without a new paid run or private
feedback. Treat it as a hypothesis; no default policy adoption or efficacy claim follows
from this pilot. Additional solving or continuation requires a new bounded allocation.

## Record validation

Documentation layout: 5 passed after compressing current summaries to their byte
limits. Ruff (`patchloop tests diagnostics`) and `git diff --check` passed. Run journals
and artifact identities were checked during the public audit; all original descriptions
were located in saved initial requests. No runtime/task code changed in this turn, so
no new full-suite or mock rerun was performed. The three actual executions above are
the live evidence; previous preparation tests are separate historical evidence.
