# Reproduction recovery: one live pilot

Material Passport: academic-research-suite / experiment-agent run; 2026-10-23.
Verification status: UNVERIFIED. Execution, accounting and saved artifact integrity
were checked; there was no successful repair or repeated-run validation.
All evidence is official=false, development-exposed and claim-ineligible.

## Question and decision

Can the [recovery and funding changes](2026-10-23-repro-recovery.md) obtain a faithful
original failure and reach checked delivery within the same USD 0.88 cap? The
[previous diagnosis](2026-10-23-repro-budget.md) motivated this question: two malformed
requests consumed acquisition opportunities, annotation errors competed with primary
feedback, and an unchecked edit remained when funding ended.

This pilot observed correction of a request-length error despite a simultaneous
annotation rejection. One actual original-caller execution returned. The model
nevertheless froze the existing bug as its expected result, then made 27 source
inspections without an edit. The cost policy closed inspection and retained successor
money, but the final response exhausted its output allowance without a tool call.
The run ended COST_CAP_REACHED with zero edits, checks or submissions.

Keep the implementation and opt-in defaults unchanged. Do not claim improved repair
or successful completion funding. The result separates transport/request recovery,
correct expectation binding, and progress under financial reservation. A further paid
comparison is not authorized by this report; this allocation is closed.

## Frozen design and authorization

The user explicitly approved the prepared scope with “승인할게” on 2026-10-23.
The proposal remains immutable, including its original unapproved status. A separate
`authorization.json` and `live_pilot_authorized` journal event bind the approval to it.

| Setting | Frozen value |
| --- | --- |
| Task | Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml` |
| Runtime commit | `6a102ec5713505fe2a2b8b46f26c03e2427ec68c` |
| Runtime SHA256 | `2426912820c5a3d7aef7fed80041e8371e3c566970ac2ba3782d6f979dc05261` |
| Model | `gpt-5.4-mini-2026-03-17`, xhigh, 25,000 desired output tokens |
| Scope | One fresh solve, no seeded case, old solver context or operator hints |
| Cap and limits | USD 0.88 total; 40 model calls, 100 actions, four accepted edits, 1,800 active seconds |
| Policies | segmented-v1; result-or-size-v1; brief-v1; probes enabled, policy none; repair-recheck; protected-v1; completion-minimum-v1; bounded-v1 acquisition |
| Credential | Repository `.env`, supplied directly to the runtime; contents not inspected or logged by the operator |
| Public assessment | At most two frozen post-submission caller/control checks, shared 120 seconds, zero model calls |
| Stops | No repeat, resume, replacement, model switch, cap increase or image acquisition; stop on identity/count/transport/billing/cleanup uncertainty |

The exact argv and working directory are preserved in
`C:/pt/repro-recovery23-live-ready-v2/request.json` and `command.ps1`.
Request SHA256: `8eb8fa8a4805d65032170b07f10135566c9babdc981aa795675c520f2f59d92a`.
Command SHA256: `cdb8da3cfaffdb366516854ae856338da9a5f79cfbefa66cbe3e266da38eaf4f`.
The operator executed that argv once, using `subprocess.Popen` without shell
interpolation. The outer process limit was 1,920 seconds including collection allowance.

Fresh read-only preflight verified 106 bound files, the exact task/source/dependency
identities, the existing local images and untracked credential presence. No image was
pulled or built. The prepared source and dependencies remained those in the proposal.
The SDK retry count was zero. Runtime/task source stayed frozen during execution.

The predeclared positive signal required faithful original-base failure, comparable
final replay, required checks/finish, both public controls and independent acceptance.
Submission alone was insufficient. The historical run was a diagnostic reference,
not a concurrent matched control. Three bundled changes, one stochastic sample and
development exposure prevent causal attribution, solve-rate or generalization claims.

## Executed result

Run: `run_dev_851bcf3ff691486d`. State: `C:/pt/repro-recovery23-live`.
Execution: 2026-10-23 02:09:34–02:19:59 UTC, or 11:09:34–11:19:59 KST.
The supervisor returned exit 0 after 625.072 seconds; runtime active time was
623.370 seconds. Exit 0 means the CLI returned its result, not successful repair.

| Measurement | Observation |
| --- | --- |
| Terminal | COST_CAP_REACHED; invocation stop_remaining=true |
| Settled cost | USD 0.788845950 of 0.88; USD 0.091154050 remained |
| Model / input counting / tools | 30 / 32 / 29; all started provider/count requests settled |
| Requests / actual dispatches / actual returns | Two original requests: one rejected, one accepted; one dispatch, one return |
| Request correction | Observed for combined program/observer length; historical quote-error correction NOT_TESTED |
| Setup / cleanup | Executed probe setup passed; zero setup failures; cleanup confirmed |
| Source investigation | 15 searches and 12 reads; 23/27 reported marginal coverage gain, 1,044 newly covered lines |
| Accepted edits / visible checks / submission | 0 / 0 / 0; solver worktree remained clean |
| Original obligation | unverified; not_reproduced under the desired-expectation contract |
| Independent acceptance / safety | NOT_RUN / NOT_RUN |
| Frozen post-submission public checks | 0/2 executed; both NOT_RUN because there was no submission |

Total usage metadata: 1,256,757 input tokens, including 739,456 cached tokens;
76,758 output tokens, including 66,015 reasoning tokens. Only counts and status
metadata were inspected; provider reasoning content was not read.

The frozen public assessor was not invoked: there was no submitted patch and its
settled-success precondition rejected stop_remaining=true. Its bytes were preserved.
No saved patch, alternate candidate or extra probe substituted for the missing
submission. A separate NOT_RUN receipt records this decision.

## Request recovery and the remaining semantic error

The first action, `call_RHSMHA8Vi9rIlr2y82wj1TZq`, had two distinct results:

- Primary result: CONTRACT_ERROR, combined probe plus observer exceeded 8,000 characters.
- Optional note: rejected citation to an unobserved `pending` tool result.

The next prepared native tool output contained the primary error and no note/plan
update wrapper. The note rejection remained in `working_notes.last_update_result`.
The next model request shortened its program from 2,108 to 1,083 characters. Action
`call_R6N6RjWFPzmJNgzY3fUwOTVY` passed admission and executed once. This is an observed
recovery sequence, not a controlled demonstration that feedback separation caused it.
One rejected request left the actual execution slots intact.

The successful dispatch invoked `pylint.lint.Run` with `args=[['src/project']]` and
`do_exit=False`, while `sys.argv` was `['pylint', 'src/project']`. It ran from the
temporary fixture root with `src/__init__.py`, `src/project/file.py`, and no
`src/project/__init__.py`. The receipt bound the prepared Linux/Python 3.9.25 profile,
fixture and call. It observed F0010 and “Unable to load file”. This is a real
observation of the reported symptom in the selected environment; it is not a claim
of equivalence to every environment in the original issue.

However, both requests set `has_f0010=true` and `has_unable_to_load=true` in
`expected_json`, despite quoting the public desired behavior “Does not fail with
error.” The actual bug therefore matched the frozen expectation. The case was
SUPPORTED relative to that expectation, with zero baseline failure case IDs. The
original obligation correctly remained unverified. The model later dismissed its
advisory baseline-confirmation concern, but that did not remove the obligation.

The dedicated acquisition phase released after six investigation actions. Release
did not verify the issue or prohibit ordinary later investigation. Only one of the
two original dispatch opportunities was used; the model did not repair the oracle.
The first rejected binding also remained a separate unestablished case after the
shortened request created a second binding. Its possible effect on later verified
delivery was not exercised here because the run never edited or finished.

This polarity error is separate from the terminal funding failure. With no candidate
or replay, this run cannot establish whether it would block a correct repair or
support an incorrect one at finish. It does establish that observing the symptom
and defining the desired post-repair result were conflated.

## What the money reserve did and did not achieve

Before call 30, settled spending was USD 0.675533700. The policy removed inspection
and check tools, offering only `replace_text` and `stop_task`. It reserved two
successful successor calls at USD 0.045576 each: USD 0.091152 total. Financial units
used the frozen 60K uncached input / 128 output minimum. This retained money for the
successor path; it did not guarantee a successful mutation response.

| Final provider call | Observed value |
| --- | ---: |
| Counted and billed input tokens | 28,443 |
| Admitted output ceiling | 20,440 |
| Actual output / reasoning output tokens | 20,440 / 20,440 |
| Returned tool calls | 0 |
| Response status / reason | incomplete / max_output_tokens |
| Settled call cost | USD 0.113312250 |

The current allowance was 20,440 tokens, not the 128-token future floor. An increased
allowance or different reasoning setting was not tested. No claim is made that
either would have produced a valid edit.

After that response, the candidate still required mutation, check and finish: three
minimum model calls. Remaining USD 0.091154050 funded two units, not three. The
runtime recorded a protocol correction but admitted no further provider call and
returned COST_CAP_REACHED. The stop occurred with ten physical model calls and 71
tool actions unused. Billing/counting were known; transport and cleanup uncertainty
were not the reason for the stop.

Thus the observed limitation is failure recovery after a non-progress response. The
reserved money remained available, but the assumed successful current action did
not happen. The financial mechanism was exercised; checked completion was not.
The 27 source inspections consumed USD 0.556265850 after the two reproduction
requests. Most added source coverage, so this evidence does not justify describing
all of them as duplicates or blindly tightening a read counter.

## Integrity, limits and next question

The collection verified both journal chains, five preparation CAS objects, 137 live
CAS objects present before collection, all 106 bound source files, the clean solver
worktree, known counting/billing and the one probe's confirmed cleanup. Stderr was
empty. Collection and skip receipts were then added to CAS and the operator journal.
The original proposal, failed preparatory directory and previous run artifacts were
not replaced. Unrelated user changes in AGENTS.md and the existing pytest directory
were preserved. No evaluator-private material or reasoning text was used in analysis.

This follow-up changes documentation only. Documentation layout: 5 PASS; Ruff on
patchloop/tests/diagnostics: PASS; diff whitespace check: PASS. The already recorded
runtime suites and mock smoke were not repeated because runtime source did not change.

Important evidence:

- `C:/pt/repro-recovery23-live/collection.json`, SHA256
  `64de90f28bd5b66dc509d8e05d54334e331262214d4ce5b16d3e7e452baf9d8c`.
- `C:/pt/repro-recovery23-live/public-assessment.json`, SHA256
  `447f92a89484f7a7853c4dbf22b7c60969076680af7afed65f79c85421dd5be4`.
- `C:/pt/repro-recovery23-live/runs/run_dev_851bcf3ff691486d.jsonl` and
  `run_dev_reprorecoveryliveoperator.jsonl` preserve execution, collection and closure.
- `C:/pt/repro-recovery23-live-ready-v2/runs/run_dev_reprorecoveryliveprepare.jsonl`
  preserves proposal, explicit authorization and fresh preflight.

The result supports retaining separate request/dispatch/result accounting and
primary/annotation feedback. It does not meet the predeclared positive-mechanism
criterion. It does not exercise live replay, rejection of an acquired original case,
unverified delivery at finish, required checks, independent acceptance or safety.
Prior local validation remains separate from these unexecuted live paths.

The next diagnostic should first distinguish an observed failure predicate from the
desired post-repair oracle and check when a request becomes a durable case. A second
local control should preserve the observed incomplete-response metadata and ask
whether a non-progress current call leaves a useful recovery path under the same
cap. Correct arithmetic alone would not establish that the model uses such a path.
Earlier commitment, a bounded recovery reserve, and response-generation settings are
alternatives to compare only when a specific control distinguishes their effects.
No new implementation, provider comparison or automatic policy adoption is included
in this allocation.
