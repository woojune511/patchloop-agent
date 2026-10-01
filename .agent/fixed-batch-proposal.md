# Fixed baseline batch proposal

Status: selection frozen 2026-10-01; preparation incomplete; paid execution NOT_RUN
and not authorized. This proposal does not extend any previous allocation.

## Question and decision

Where does the unchanged working baseline fail across three repositories selected
before preparation or outcome inspection? Recent individual task diagnoses do not
establish which failures recur across repositories. This batch collects comparable
failure evidence before choosing another intervention; it is not a causal comparison
or a general success-rate estimate. No prompt, memory or tool change is proposed.

## Frozen selection

Use `diagnostics/original_baseline_select.py` unchanged: public issue and image
present, pytest parser, exclude repositories in the candidate ledger and existing
public task packages, rank SHA256(seed + newline + instance ID), then take the first
three distinct repositories. Seed: `patchloop-original-input-pilot-v1`.
Selection used only public columns, without image-availability or outcome filtering.
Do not replace a selected task when preparation or evaluation fails.

Dataset: `nebius/SWE-rebench-leaderboard`, `2026_03`, revision
`ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`; parquet SHA256
`18e198ac18b3c25b307c0aa5d9b6e20d338886e186bf7c12addb759ad4165a61`.
There were 81 eligible rows out of 110. Frozen order:

| Instance | Base commit | Public problem |
| --- | --- | --- |
| `alibaba__opensandbox-816` | `fb78091f947f62ae2c71a372af42425a764aacee` | Host-volume path validation permits symbolic links |
| `pyinfra-dev__pyinfra-1679_interface` | `185f7dbec96f8e1d5f7cfefe0f325f99ab73927a` | ProxyJump connection ignores timeout |
| `pycqa__isort-2491` | `ae91dadf34951e316d5a81ffe7ac086952f1da65` | Alias import moves a trailing comment |

External evidence: `C:\pt\preparations\fixed-batch-20261001-v1`.
`runs/run_dev_fixedbatchselection.jsonl` records protocol before selection,
exclusion-input hashes, selector/driver hashes, and content-addressed public rows.
`selection.json` provides exact issue hashes and artifact paths. The driver is
`C:\pt\fixed_batch_select_20261001.py`. Private columns were not decoded.

## Preparation gate

All three dataset image tags were absent in local `docker image inspect` checks.
No image was pulled or built; Docker was not started. Image tags are discovery
references, not execution identities. Do not automatically pull/build images.

Before requesting paid approval, prepare exact `dev-train` task IDs/versions and
hashes, source checkouts at the commits above, immutable image identities and probe
dependencies. Preserve original public issues without diagnostic hints. Keep
original benchmark F2P/P2P tests and reference patches private. Calibrate baseline
failure and reference success with complete test accounting; distinguish test
collection/setup failure from a completed wrong-answer result. Verify public checks,
probe environment parity and isolated evaluator operation. Record scope/safety
contracts separately. A conflicting or incomplete oracle blocks that row rather
than silently changing its requirements or substituting another task.

No runnable packages, image digests, calibration or execution command are claimed
by this proposal. Record preparation failures against the same three selected rows.

## Proposed execution scope

Freeze the runtime commit and prepared identities before approval. Use the current
baseline unchanged: `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens;
`segmented-v1`, `result-or-size-v1`, `brief-v1`, probes enabled with policy `none`,
`repair-recheck`, `protected-v1`, `per-call-v1`. Per task: one fresh run, 40 model
calls, 100 actions, four accepted edits, 1,800 seconds, positive invocation cap
USD 3. Proposed aggregate maximum: USD 9 across three sequential invocations.
Credential-file proposal: `C:\Users\geonj\Documents\PatchLoop\.env`; do not read
credentials during preparation. Exact task/model/credential/repeat/cap approval
remains required once the scope is executable.

No retries, rescue runs, replacements or transfer of unused budget. Count before
dispatch, zero SDK retries, and stop the entire batch on count, transport or billing
uncertainty. A normal task failure remains evidence; it does not authorize tuning
before subsequent rows. Preserve external append-only hash-chained journals and
historical evidence. Every run is `official=false`; cross-run memory, held-out
tuning and claim execution remain disabled. Never return hidden feedback to the
coding agent.

## Readout and stopping decision

For every selected row report preparation and execution state, public checks,
original hidden F2P/P2P results, patch scope, safety, counted cost and elapsed time.
Keep PREPARATION, INFRASTRUCTURE, RESOURCE and REPAIR failures distinct and retain
their underlying evidence. Unexecuted axes are NOT_RUN, not failures or successes;
unknown usage is not zero. Report both the fixed selection denominator of three
and the number admitted/executed/evaluated, without dropping blocked rows.

After the batch, select a mechanism only if public trace/source evidence supports
it and the impact warrants investigation. Competing possibilities include setup
limitations, exhausted resources, task misunderstanding and incomplete repair;
successful repairs or unrelated failures would weaken a shared-mechanism claim.
Use the smallest discriminating diagnostic next. If no actionable mechanism is
supported, preserve the baseline and stop. No next batch is automatic. Three
development tasks neither establish general accuracy nor prove no contamination.
