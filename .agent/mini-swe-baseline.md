# mini-SWE-agent baseline on dev20

## Question and decision

The user requested an external agent baseline and selected all 20 existing
SWE-bench Lite development tasks on 2026-10-16. Repeated PatchLoop prompt changes
have not established better acceptance. An independently designed simple agent can
show which of these tasks the same model solves under another harness. This is a
descriptive baseline, not a single-feature ablation, held-out accuracy, or a claim.

Use mini-SWE-agent v2.4.6, commit
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`, from
<https://github.com/SWE-agent/mini-swe-agent>. Its upstream DefaultAgent, SWE-bench
system/instance prompts, Responses action parser, and observation/error templates
are retained. No task-specific hints, PatchLoop notes, reference patches, previous
trajectories, or hidden results enter its inputs.

The operator adapter is `diagnostics/mini_swe_runtime.py`; the panel driver is
`diagnostics/mini_swe_dev20.py`. They do not change the PatchLoop agent/runtime.
Direct OpenAI transport replaces LiteLLM retry/post-spend accounting with existing
exact input counting, pre-dispatch reservation, zero retries and usage settlement.
All response items are replayed in linear history, including encrypted reasoning.

## Closed fresh rerun scope

The [fresh panel](../docs/history/2026-10-16-mini-swe-dev20-results.md) completed all
20 attempts: 10 native PASS, 5 native FAIL, 5 unsubmitted at the 40-call limit.
Fifteen submitted patches passed scope checks. Cumulative recorded cost including
the first stopped attempt was USD 3.2171004; allocation CLOSED. The exact packet
and outcomes remain frozen in `C:/pt/mini20prep05` and `C:/pt/mini20live02`;
`C:/pt/mini20rerun01` contains the audit and historical comparison. No further
live invocation is authorized by this closed scope.

- Same immutable 20-instance roster as `portfolio_dev20.baseline()`, using the
  public issues and current packages under `tasks/dev-train/current-dev20/1..20`.
- Model `gpt-5.4-mini-2026-03-17`, xhigh, desired output ceiling 25,000;
  standard/default service tier, global endpoint; credential file repository `.env`.
- One fresh attempt per task, one worker, at most 40 generations and 100 bash
  actions each. No resume, transport retry, replacement, repetition or cap transfer.
- The user reauthorized all 20 fresh attempts, the isolated bash exception and a
  cumulative USD 24 cap after the first attempt's count failure. Its settled
  generation cost, USD 0.002403, remains included. The new cap is USD 23.997597,
  divided equally into USD 1.19987985 per task; no transfer. The prior audit and
  original evidence hashes are validated before dispatch. No new paid PatchLoop run,
  SWE-agent run, test300 evaluation, or automatic follow-up.
- Solver preparation/counting/generation/actions share 1,470 seconds. Native
  evaluation has a 330-second process allowance, with a 300-second test timeout.
  Record cleanup/host overhead separately; do not equate this staged timeout with
  the historical PatchLoop invocation-wide deadline.
- Keep mini's native unlimited edit count, source-only submission and linear
  history. These differ from PatchLoop's four accepted edits, additive-test support,
  segmented context, registered tools, and automatic rechecks. Upstream's 250-step
  and USD 3 defaults are intentionally replaced by the stated matched budgets.
- Final scope/dependency/test-integrity checks run in a fresh checkout. Correctness
  uses the unchanged pinned native SWE-bench grader and exact instance images.
  Registered PatchLoop runtime/safety evaluation is NOT_RUN for this comparator;
  report its container isolation receipts separately, without claiming equivalent
  PatchLoop tool-admission safety. Base tests are never replaced by model tests.

## Public environment and authorization

Use only existing digest-pinned local images, with `--pull=never`, network disabled,
read-only root, dropped capabilities, no new privileges, CPU/memory/PID bounds, and
no host mounts. Mask `/testbed` with a fresh tmpfs populated solely by a verified
base-commit source archive. Create a synthetic one-commit Git repository without
remotes. If the public module import fails because masking the original checkout
removed editable metadata, regenerate it with public `setup.py egg_info`, without
installing dependencies or changing tracked source. The agent sees no host credential file,
PatchLoop task package, historical
run, private specification, or evaluator payload. Destroy its container before
private grading. Record actions and accounting in external hash-chained dev-run-v1
journals with content-addressed artifacts; no automatic action recovery/reexecution.

The repository AGENTS.md hard gate 2 says: "Expose only registered reads, searches,
mutations, visible checks, and finish; never provide unrestricted shell access to
the coding agent." Native mini needs bash inside its isolated container. The user
explicitly approved this benchmark-only exception and the USD 24 packet on
2026-10-16; `C:/pt/mini20prep04/authorization.json` records that approval. The
[attempt stopped](../docs/history/2026-10-16-mini-swe-count-stop.md) on its second
input-count request after one settled generation. All 20 native verdicts are
NOT_RUN. Preserve that closed packet and live evidence. The user's subsequent
explicit approval authorizes one fresh corrected panel, including prior cost in
the same USD 24 ceiling. Record it in the new packet's authorization receipt;
the old approval and failed attempt are never rewritten.

Before live execution, save the human approval against the exact packet hash with
`live_authorized=true` and `isolated_bash_exception=true`. A JSON authorization
file records human approval; it is never a substitute for receiving it.

The corrected operator adapter omits null optional SDK item fields when replaying
history, while retaining raw responses and every non-null item field. Saved-request
schema replay and an upstream/SDK mock passed. A count-only check of the saved
corrected request may verify transport before starting the fresh solves; it must
not generate a response or supply previous history to a fresh solver. Stop on
another count failure. The corrected count-only check and fresh 20-task panel
completed without count/transport/billing uncertainty. The saved-request check
made zero generations; the fresh panel made 524, all settled. This validates the
adapter on the recorded run, not a general agent-quality improvement.

## Reporting and stop rules

Report all 20 tasks, separating native PASS/FAIL, scope failure, unsubmitted runs,
NOT_RUN, infrastructure errors, known cost, uncertain billing and cleanup. Compare
individual native verdicts with each historical panel separately; retain the
corrected panel's original two NOT_RUN rows and its separately recorded supplement.
Do not pool old and new PatchLoop runs into one newly measured accuracy.

Count/transport/billing uncertainty, failed private grading or unconfirmed cleanup
stops admission for the entire panel. A settled row cost/call limit leaves that row
unsuccessful; other rows retain their own caps. Preserve the first result, even when
an environment or setup problem is found. No tuning or rerun follows automatically.

If mini solves tasks PatchLoop misses, inspect public traces for actionable harness
differences; this alone does not identify a causal mechanism. If both fail, inspect
shared difficulties before adding PatchLoop complexity; it does not prove a model
ceiling. If PatchLoop wins, preserve that descriptive result without a general claim.

## Recorded commands

Keep the pinned upstream checkout in `<prep>/upstream`; isolated support packages
in `<prep>/python-libs` are Jinja2 3.1.6, MarkupSafe 3.0.4, python-dotenv 1.2.1 and
platformdirs 4.9.4. PatchLoop's locked Python environment supplies other dependencies.
Preparation binds the actual source/dependency bytes, config, tasks, archives,
images, native harness and runtime into one manifest.

Use the attached `mini-swe-dev20` checkout so concurrent dev-head edits cannot change
the frozen runtime. The interpreter comes from the existing project environment.

```powershell
Set-Location C:/Users/geonj/.codex/worktrees/mini-swe-dev20/PatchLoop
$miniPython = 'C:/Users/geonj/Documents/PatchLoop/.venv/Scripts/python.exe'
& $miniPython -m diagnostics.mini_swe_dev20 prepare --root C:/pt/mini20prep05 --live-root C:/pt/mini20live02 --env-file C:/Users/geonj/Documents/PatchLoop/.env
& $miniPython -m diagnostics.mini_swe_dev20 preflight --root C:/pt/mini20prep05 --packet-hash <hash>
# Only after exact human approval, including the isolated bash exception:
& $miniPython -m diagnostics.mini_swe_dev20 run --root C:/pt/mini20prep05 --packet-hash <hash>
```
