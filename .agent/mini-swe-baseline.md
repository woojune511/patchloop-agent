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

## Proposed exact scope

- Same immutable 20-instance roster as `portfolio_dev20.baseline()`, using the
  public issues and current packages under `tasks/dev-train/current-dev20/1..20`.
- Model `gpt-5.4-mini-2026-03-17`, xhigh, desired output ceiling 25,000;
  standard/default service tier, global endpoint; credential file repository `.env`.
- One fresh attempt per task, one worker, at most 40 generations and 100 bash
  actions each. No resume, transport retry, replacement, repetition or cap transfer.
- USD 1.20 per task, USD 24 total in model-token costs. No new paid PatchLoop run,
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

## Public environment and pending permission

Use only existing digest-pinned local images, with `--pull=never`, network disabled,
read-only root, dropped capabilities, no new privileges, CPU/memory/PID bounds, and
no host mounts. Mask `/testbed` with a fresh tmpfs populated solely by a verified
base-commit source archive. Create a synthetic one-commit Git repository without
remotes. If masking the original checkout removes editable package metadata,
regenerate that metadata with public `setup.py egg_info`, without installing
dependencies or changing tracked source. The agent sees no host credential file,
PatchLoop task package, historical
run, private specification, or evaluator payload. Destroy its container before
private grading. Record actions and accounting in external hash-chained dev-run-v1
journals with content-addressed artifacts; no automatic action recovery/reexecution.

The repository AGENTS.md hard gate 2 says: "Expose only registered reads, searches,
mutations, visible checks, and finish; never provide unrestricted shell access to
the coding agent." Native mini needs bash inside its isolated container. **That
benchmark-only exception remains pending explicit human approval**, together with
the exact manifest/cost scope required by hard gate 5. Preparation, operator-only
environment canaries, and tests do not authorize model execution. Do not adapt mini
to PatchLoop tools to silently evade this difference or silently waive the rule.

Before live execution, save the human approval against the exact packet hash with
`live_authorized=true` and `isolated_bash_exception=true`. A JSON authorization
file records human approval; it is never a substitute for receiving it.

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

## Commands

Keep the pinned upstream checkout in `<prep>/upstream`; isolated support packages
in `<prep>/python-libs` are Jinja2 3.1.6, MarkupSafe 3.0.4, python-dotenv 1.2.1 and
platformdirs 4.9.4. PatchLoop's locked Python environment supplies other dependencies.
Preparation binds the actual source/dependency bytes, config, tasks, archives,
images, native harness and runtime into one manifest.

```powershell
.venv/Scripts/python.exe -m diagnostics.mini_swe_dev20 prepare --root C:/pt/mini20prep02 --live-root C:/pt/mini20live01 --env-file C:/Users/geonj/Documents/PatchLoop/.env
.venv/Scripts/python.exe -m diagnostics.mini_swe_dev20 preflight --root C:/pt/mini20prep02 --packet-hash <hash>
# Only after exact human approval, including the isolated bash exception:
.venv/Scripts/python.exe -m diagnostics.mini_swe_dev20 run --root C:/pt/mini20prep02 --packet-hash <hash>
```
