# Caller/completion repair follow-up: public PASS, isolated FAIL

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved code experiment and public outcome audit
- Origin Date: 2026-10-28, Asia/Seoul
- Verification Status: LIVE_EXECUTED; public cases/checks PASS; task acceptance FAIL
- Version Label: caller_completion_repair_results_v1
- Scope: one dev-train checkpoint continuation, official=false, claim-ineligible

## Question, authority and fixed conditions

The [plan](2026-10-28-caller-completion-repair-plan.md) asked whether caller-source
access and a coherent completion reserve let the model investigate and repair
within the previous budget. The preceding run exhausted its three edits while
the original remained unresolved; source access and early reservation constraints
were observed bottlenecks. The intervention registered prepared pylint source in
ordinary reads/searches and used shared completion-path reservations. It did not
inject caller bodies, an operator diagnosis or a successful patch.

The human explicitly approved one execution at a new USD4.13241570 cap, bound to
manifest `sha256:527fb7ddb8a55baa2738edb38ad9c6a99c4bf9f1cf0ae052ab265ccd22421902`.
The exact approved script `C:/pt/caller-completion-repair-plan-v1/run.ps1` ran once
and exited zero. Its exit status means the experiment completed, not task success.
The approved scope is recorded in that directory's `authorization.json` and the
append-only preparation journal. No second run or continuation is authorized.

Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml`, resumed public cut84
of `run_dev_3e21775752a54cae` from `C:/pt/argument-first-reproduction-run-v1/B`.
Model `gpt-5.4-2026-03-05`, xhigh, used the repository `.env` path. The original
15 remaining responses, 33 tools, three edits, context60K, output40K/correction25K,
about1727.678s solver time and390s evaluation reserve were retained. Caller roots
were `{"pylint":"pylint"}`, backed by the prepared pylint2.12.2 snapshot.
Twenty-six fixed manifest fields matched the previous checkpoint trial.

Implementation commits: `2a7acd5dab48e78089922148899f32621902516b` and checkpoint
bridge `6f5786ee`; execution HEAD `563b896c`. Runtime stayed frozen throughout the
run. The source checkpoint prefix and original hashes remain unchanged.

## Observed behavior and outcomes

| Evidence | Result |
| --- | --- |
| Caller access | Two successful dependency searches and a read of `pylint/lint/expand_modules.py` lines1-139; one earlier malformed dependency path was rejected |
| Caller delivery | Results appeared in canonical contexts linked to subsequent dispatches |
| Candidate | One accepted `replace_text` edit to `astroid/modutils.py` |
| Original public fixture | F0010 absent; actual `file.py` W0611 present |
| Normal-package control | F0010 absent; actual `file.py` W0611 present |
| Verification feedback | Exact replay observation and action ID in next dispatched turn |
| Public `base-regression` | 1,231 passed, 69 skipped, 15 xfailed; no timeout or truncation |
| Normal finish/submission | `cases_verified_delivery` / `cases_verified` |
| Isolated task acceptance | FAIL, `PRIVATE_EVALUATION_FAILED`, terminal `EVALUATOR_FAIL` |
| Safety | PASS, independently reported from task acceptance |

Branch journal sequence186 records the edit; seq193 records automatic original
replay. Seq200's canonical context contains the exact result under
`state.reproduction_review.completion.cases[0].current.observed_json`, linked to
dispatch202. The model then selected the public check (seq208), followed by normal
finish223 and submission228. Isolated summary230 and terminal231 close the run.
The isolated result was not fed back to the model.

The post-run audit independently recalculated F0010/W0611 from both complete
captured calls. They agree with the authored verdict, both entered the target, and
both produced a diagnostic for the actual file. This was not a no-op success.
Baseline and candidate conditions hashes are identical:
`sha256:cb3216d53240fd49a12b2e6fd03bacdbc0f8aa27b9bc7107a360ca0faf78a063`;
environment identity also agrees. The selected public fixture passed, while the
issue-to-caller mapping remains `model_authored_unverified`.

There were no additional model-selected probes. The single new probe was the
automatic post-edit replay, so this run does not establish model uptake of the
choice to observe a call path before editing. No failed intermediate repair or
public check occurred, so feedback-driven re-repair was not exercised either.

## Resource accounting and allocation closure

- Eight new count/dispatch/usage groups settled; 20 new tool actions, one edit,
  zero protocol corrections. Total inherited-plus-new responses13/tools27.
- New cost USD0.81392900; historical settled cost USD0.36758430; branch total
  USD1.18151330. The new allocation's unspent USD3.31848670 is CLOSED.
- New active elapsed379.780s including evaluation. Summed new usage:
  input243,974 tokens, cached input52,096, output21,414. These are cumulative,
  not per-request context or output sizes.
- No output/context exhaustion, counting, transport, billing or cleanup
  uncertainty was recorded. No retry occurred. Both journals' hash chains,
  count-to-dispatch linkage, pricing, caps and source-prefix preservation passed
  independent read-only audit.

The progress monitor initially selected an older nested fork marker and counted
one inherited USD0.28173750 call as new. This affected interim display only;
collector accounting remained correct. Final attribution uses current fork85,
not the first funded marker. The result, collector ledger and independent audit
all agree on eight calls and USD0.81392900. The original monitor is retained as
evidence and must not be reused unchanged for nested forks.

## Interpretation and next question

This run demonstrates caller-source access being used, public verification
reaching the next response, and completion within the approved bounds. It differs
from the preceding three-edit failure, but access and reservation policy changed
together and each condition has only one sample. Their individual causal effects,
clean-start efficacy and generalization remain unestablished.

The submitted public patch adds an ImportError fallback in `modutils.py` that
constructs a namespace spec from an explicit path entry. Statically, that fallback
iterates only `path or ()`, requires a directory without an initializer, and
requires its trailing components to equal the entire module path. It adds no
tests. These are visible branch constraints, not an explanation extracted from
the isolated evaluator.

The result preserves the access/reservation implementation but changes the next
question from reaching submission to public verification coverage and resolver
semantics. Review the public path/return-value contract and compare relevant
explicit/implicit path forms on base versus candidate before another paid trial.
Such diagnostics were NOT_RUN here. No private test, reference patch, detailed
evaluator failure or opaque reasoning was opened to explain acceptance FAIL.
The exact private failure cause remains unknown; public PASS must not be promoted
to a claim of successful task repair.

## Evidence locations and validation

- Plan and approval: `C:/pt/caller-completion-repair-plan-v1`
- Result: `C:/pt/caller-completion-repair-run-v1/result.json`
- Collector: `runs/run_dev_postreproductionrepair.jsonl`, final allocation closure
  seq36, hash `sha256:1c25fef44b30b0311b8b45b2a6878fc3b242686fe3773a2ec6d3517cce2737d3`
- Branch: `repair/runs/run_dev_3e21775752a54cae.jsonl`, hash
  `sha256:ec8de9ea05dbc3beff7ffc4574c9c931b345eeb77639369f5740f3c950a2825d`
- Submitted public patch:
  `sha256:141dc0f8e373a23b7379661de8c08b3b0f07c6fa010f2d7bbb8b18b0ed74967f`
- Audit: `C:/pt/caller-completion-audit-v1/audit-result-1.json`, hash
  `sha256:6369127cb475568f19842deb176bd3c0861e6c353cad1b91c44a53e7fa635f85`
- Public outcome: `C:/pt/caller-completion-audit-v1/public-outcome-1.json`, hash
  `sha256:0615ba5683372fea78c34cd6bdca44188ee3cefe53146c6fc54ddcd5ac863908`

Preparation bridge controls passed17+5 tests; docs passed5 before execution.
Post-run documentation controls passed5 and `git diff --check` passed.
Post-run changes are documentation only. No runtime change, extra target
execution, model request or private inspection was used during closeout.
