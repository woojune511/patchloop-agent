# Full-source trial: context recovered, no first repair

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: authorized execution and settled public-evidence audit
- Origin Date: 2026-10-27
- Verification Status: LIVE EXECUTED / BILLING SETTLED; repair not demonstrated
- Runtime mechanism: `48e62b64`; selected-arm collector: `47ba713c`
- Execution checkout: `007e2ec8` (preflight documentation follow-up)

## Question and authorized execution

The [prepared single trial](2026-10-27-repair-entry-single-plan.md) asked whether
the new request contracts allow the model to reach a first edit and then use
original-call feedback to revise. The user approved R1 once, $1.20 total, for
Astroid-1333 (`dev-train/current-dev20/13`), `gpt-5.4-mini-2026-03-17` xhigh and the
repository `.env`. The exact command was the prepared `run.ps1`; its manifest hash
was `sha256:711dc6277d512a76bc93c00f8ca9da3eb896606f76a0d0f32ba9cbd92bc478be`.
The approval is preserved in `approval.json` and the preparation journal. The
process exited zero, all generation calls settled, and the allocation is closed.
There was no retry, second arm, extra model call or post-run target replay.

This is a development-exposed saved-candidate continuation, official=false, with
no concurrent control. It is not a fresh benchmark solve or an estimate of any
single mechanism's causal effect. The known operator repair remained excluded
from model inputs. No private result was delivered to the model.

## Observed result

| Measure | Observed |
| --- | --- |
| Terminal | `AGENT_STOPPED`, `insufficient_public_evidence` |
| Normal responses / corrections | 15 / 0 |
| Model actions | 19: seven reads, eleven searches, one stop |
| Additional edits | 0; imported seed diff unchanged |
| Helper programs / original selections / host original executions | 0 / 0 / 0 |
| Model whole/page reads | 0; all seven requested explicit ranges |
| Input counts / generation calls | 16 / 15, all settled |
| Context boundaries | One committed public handoff |
| Maximum counted / dispatched input | 60,734 / 56,585 tokens |
| Largest response / total generated output | 5,154 / 17,209 tokens |
| Model phase | 111.006 seconds of the shared 600-second ceiling |
| Settled cost | $0.22311930 of $1.20; $0.97688070 unspent |
| Final original/public/isolated verification | NOT_RUN |
| Task acceptance | NOT_RUN |

The two initial host source reads are excluded from the 19 model actions. All
676 selected source lines were supplied. The model's first response requested
one read and one search. No action receipt failed and no protocol correction was
needed. The existing seed remained
`sha256:93b024b3f11ef89311d9cbf5a06a56328b14f7b7d7687746e6d24a8b9fb8e3e5`.
Because no original execution or edit occurred, this run does not newly establish
that F0010 persisted or disappeared; it produced no new repair or verification.

## What the context boundary established

After response 13, the next input counted 60,734 tokens. The host rebuilt a public
context, recounted 48,301 tokens, admitted it and dispatched response 14. It carried
normal-call count 13, model-action count 17 and settled cost $0.16312035. The model
then read `astroid/modutils.py:250-290`; the subsequent response stopped. No native
reasoning or function-call items were copied into the fresh context; public
exchanges were quoted as historical observations. Opaque content was not interpreted.

This proves that this ordinary input-limit boundary resumed within 60K without
resetting allowances. It does not test a live correction boundary, post-edit
failure retention, original selection, helper construction or repair effectiveness:
those paths were not selected here.

## Why this was not a monetary or output cutoff

Immediately before the final response, normal responses=2, tools=6, edits=3 and
funds=$1.01539320 remained. The request offered `replace_text` and `stop_task`, with
40K output. Additional inspection/helper/original selection had closed because the
opportunity policy reserves a response to consume an edit result. One response
earlier, normal responses=3 and tools=7 remained, and all those diagnostic tools
were still offered; the model chose another source read.

Thus the response-count reservation affected the final action menu, but cost,
time and output ceilings did not force termination. Raising the context ceiling
is not supported as a sufficient remedy: the boundary recovered successfully and
the model still stopped. More response opportunities could change behavior, but
this run does not show whether they would produce useful observations or more
searching. A new run needs an evidence-based reason, not unused funds.

## Public action evidence and next unresolved question

The model repeatedly sought Pylint's directory/module-expansion path. Three
Pylint-specific path searches scanned **zero files**. Two broader searches for
`def expand_modules` and `expand_modules(` scanned 205 files each and returned no
spans. The model also inspected Astroid builder/manager code and public tests.
Six of eleven searches returned no spans; the final broad namespace search was
truncated after twenty spans. These are search-scope observations, not proof that
the sought dependency code does not exist.

The explicit stop summary said the prefix change was already present, that failure
appeared later in directory-target module selection, and that the available source
did not justify a safe edit. This is the model's stated, unverified interpretation.
It did not use either executable helper opportunity or the registered-original
selector to test that interpretation. Merely exposing a smaller valid request did
not cause its use, and supplying a complete selected file did not guarantee access
to every relevant caller.

The next diagnostic question is whether useful caller evidence was inaccessible
through the chosen search surface, insufficiently discoverable through the existing
tools, or deliberately avoided because replay looked redundant with supplied
failure feedback. Audit that evidence path before adding a compulsory gate or
raising budgets. The present run cannot distinguish those explanations, and no
follow-up execution is authorized by its remaining funds.

## Integrity and evidence locations

The public audit checked matching IDs for 16 count starts/completions, 15 generation
starts/completions and 21 action starts/completions (two host, nineteen model).
Count/request hashes, dispatched versus counted input, output admission and the
sum of settled costs agree. A separate read-only review reached the same conclusion.
No count/transport/billing uncertainty or failed action receipt was observed.

- Preparation/approval/command: `C:/pt/repair-entry-single-plan-v1/`.
- Immutable collector result: `C:/pt/repair-entry-single-run-v1/result.json`.
- Public metadata and action audit: `C:/pt/repair-entry-single-run-v1/public-analysis.json`.
- Source execution journal: `C:/pt/repair-entry-single-run-v1/R1/runs/run_dev_feedbacksourcemodel.jsonl`.
- Analysis receipt: `C:/pt/repair-entry-single-run-v1/analysis/runs/run_dev_entryanalysis.jsonl`.

Implementation validation remains the separate 44-focused/472-quick local result
in the preparation record. This execution supplies no accepted solution, isolated
acceptance gain or generalization claim. No runtime code was changed during the run.
