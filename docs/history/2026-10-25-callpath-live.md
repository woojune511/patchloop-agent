# Call-path pilot stops before the first repair

Date: 2026-10-25. Status: completed; allocation closed. `official=false`,
`claim_eligible=false`.

## Material Passport

- Origin skill/mode: academic-research-suite / experiment-agent / run.
- Verification: ANALYZED from saved public execution and dispatch evidence;
  no independent model rerun or repair-quality claim.
- Version: `callpath-live-v1`.

## Question and fixed conditions

The [previous investigation](2026-10-25-judgment-callpath-analysis.md) found four
ineffective mutations whose changed branches missed the failing call. The
[implementation](2026-10-25-callpath-repair.md) added conditional call-path
observation, diagnosis-to-revision linkage, selected-test comparison and resource
accounting. This pilot asked whether the model would use those observations to
repair the original F0010 failure. Diagnosis delivery, original behavior, checks,
submission and independent acceptance remained separate observations.

The user's new actual-model experiment request authorized one fresh solve within
the continuing thread's task/model/credential/repeat/cap conditions. The exact scope
was restated and sealed before dispatch. Old allocations remained closed; operator
diagnoses and patches were not supplied to the model.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`, contents not printed.
- One repetition; USD1.20 invocation cap; normal output 40,000, independent
  protocol correction 25,000. Limits: 40 model calls, 100 tool actions, four
  accepted mutations, 1,800 active seconds and 1,920-second supervision.
- Same run_probe recommendation, segmented-v1 / result-or-size-v1 / brief-v1,
  bounded-v1 acquisition, probes with policy none, repair-recheck, protected-v1,
  completion-recovery-v1, prepared source/dependencies and existing images.
- Runtime commit `ab1fc8ef4e92ec515dec22e275dd319cbc0494ff`; runtime hash
  `sha256:18076f25f247f3fca8deef6b09a6064d07eb7edaf85da3fe2dcad0e183557c96`.
  The request changed only its state root. The collector/wrapper changed the
  trusted probe profile to
  `sha256:a087c235e807dd4de6434599769655e921ff493548221941e36117127dee66c6`;
  image, dependencies and limits were unchanged.
- Count/transport/billing/cleanup uncertainty or source drift stops work. No
  automatic repeat, resume, model change, cap increase or image acquisition.
  Two frozen post-submission public checks had a conditional shared 120-second bound.

The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
confirmed the snapshot, xhigh and USD0.75 / USD0.075 / USD4.50 per million input /
cached input / output tokens. Same-commit local validation receipts were verified;
unchanged runtime tests were not repeated for this live run.

This is one stochastic solve on an exposed dev-train task. The historical judgment
pilot is descriptive context, not a paired causal estimate. Model-authored
reproductions can differ across fresh solves. Preregistered alternatives included
repair before the diagnosis trigger, failed acquisition, invalid/incomplete
diagnosis, ineffective evidence use, weak selected tests and resource/output
exhaustion. Untriggered mechanisms count as NOT_EXERCISED.

## Observed result

Run `run_dev_b727d95fec6b4f93` ended `INCOMPLETE_RESPONSE` after 650.323 seconds
(10m50s). Cost settled at USD1.050511650; USD0.149488350 remained unused. There were
31 model calls, 33 input counts and 29 tool actions. Billing and counting are known;
no timeout, cleanup failure or frozen-source drift occurred.

| Stage | Observation |
| --- | --- |
| Unchanged-base original failure | Acquired on first model call; host/authored judgment consistent |
| Source exploration | 13 searches and 14 reads |
| Additional helper probe | One execution, exit 1 with NameError; no resolver observations |
| Mutations / candidate replay | 0 / NOT_RUN; workspace diff remains empty |
| New call-path requests / executions | 0 / 0; trigger never reached |
| Diagnosis-linked revision / paired selected tests | NOT_EXERCISED / NOT_EXERCISED |
| Required checks / submission | NOT_RUN / NOT_RUN |
| Post-submission checks / independent acceptance / safety | NOT_RUN / NOT_RUN / NOT_RUN |

1. Call 1 ran `pylint.lint.Run` on `src/project` and its normal file control.
   Complete per-call captures contained F0010 on the directory invocation. Literal
   `Unable to load file` rules yielded
   `{"bug_has_error":true,"control_has_error":false}` in both host and authored
   judgments. Baseline conditions hash:
   `sha256:291d367f8255f623b4544d978d8233fbf08f9ab2a82ead3d49bf857626f7bdc1`.
   No candidate was created to compare against it.
2. `replace_text` was offered from call 3. The model continued source exploration.
   At call 25 it attempted a helper probe of resolver behavior, but the unbound
   helper used `reproduction_workspace()`, available only through original-case
   injection. It failed before resolver outputs with
   `NameError: name 'reproduction_workspace' is not defined`. Tool status
   `succeeded` records a returned execution; exit 1 is not diagnostic success.
3. The helper error reached call 26's public developer archive. The model made
   four more source inspections without correcting the helper. The original
   baseline remained present in dispatched states, including calls 30 and 31.
   Missing failure delivery is not the explanation supported by this audit.
4. Before call 30, USD0.711600450 had settled. Exploration closed under
   `completion_horizon`, leaving `replace_text` and `stop_task`. The response used
   all 40,000 output tokens without a tool call, costing USD0.209435250. The one
   reserved correction at call 31 received all 25,000 tokens, also emitted no tool
   call, and cost USD0.129475950. Both ended `max_output_tokens`; the provider
   classified all 65,000 tokens as reasoning. Reasoning content was not inspected.

Token totals: 1,252,703 input, including 694,912 cached; 128,900 output, including
113,410 reasoning. Reasoning is included in output, not added twice. The terminal
was output exhaustion, not exhaustion of the dollar cap or four-edit limit.

## Interpretation and next question

The experiment failed to repair the task. It never exercised the new diagnosis,
whose trigger requires a comparable failed mutation and measured unobserved
changed lines. This supports neither a repair benefit nor rejection of that
mechanism; absence of diagnosis here is consistent with its activation condition.

The intervention addressed repeated ineffective edits, while this trajectory
stalled earlier: valid original baseline, source exploration, invalid helper and
no first repair. Correction funding worked: it delivered the complete 25K allowance.
That did not guarantee an action. Remaining budget alone does not support raising
the normal ceiling beyond 40K.

Keep the original-failure gate and conditional diagnosis implementation, separating
local verification from live uptake. The next question is how to reach a valid
bounded diagnostic and first repair before exploration closes. The current evidence
does not distinguish inadequate helper guidance, difficulty forming a repair and
stochastic response failure; inspect that transition before replacing a mechanism
that this run never reached.

A separate static check found another limitation: this task registers pytest via
a Python `-c` wrapper, while the paired-test adapter accepts only direct registered
Python `-m pytest` commands. It cannot exercise the comparison without another
implementation change. No selected test was requested, so that limitation did not
cause this terminal; it matters for a future end-to-end comparison on this task.

## Integrity and records

Preparation/scripts: `C:/pt/callpath-live-ready-v1`. Run/analysis artifacts:
`C:/pt/callpath-live-v1`. The collector verified 116 sealed repository inputs,
hash-chained journals, 161 content-addressed objects at collection, settled
dispatch identities and action_id/input_hash pairs. Private evaluator/continuation
artifacts were only hashed; private tests, reference patches and provider reasoning
were not inspected or supplied to the model. State was fresh, without cross-run memory.

- Request: `sha256:1f79fb13125ce32d6cde540056dea900b93a3f1e8ad2b8b3c4a8407f2b1d00bd`.
- Collection: `sha256:0e24f6e15799c429e4423f37d5ba69010c22abc67ccca21fba58d9ef6e4fbffc`.
- Public analysis: `sha256:4c1d1edc950476461922917020a8421060bd0186283f2f17b069fd32da5299e2`.
- Path/dispatch audit: `sha256:87879ce895f1f27655316cac2d813627b610ec591ab0552ffff1750859b48afe`.
- Feedback/capability audit: `sha256:561cd485595478919aab40e6eebeb9c2a4680cd75905f8d333cec55ce112a577`.

The first offline feedback audit omitted public developer archives, so its
helper-delivery assertion failed. The preserved follow-up included that delivered
archive and verified the error without any new target/model call. Documentation
validation and the closing commit are in the external closeout receipt. The paid
allocation is closed; unused budget does not authorize a continuation.
