# Cost-cap continuation

CLOSED: both continuations submitted and failed registered/native/public checks;
additional USD 0.21352020. See the [results](../docs/history/2026-10-06-cost-cap-continuation-results.md).
No further paid continuation is queued.

`diagnostics/cost_cap_continuation.py` prepares an unhinted continuation from the
last unexecuted prepared request of a settled `COST_CAP_REACHED` run. Ordinary
resume and closed experiment results remain unchanged. This is supplementary
execution, not another fresh solve or a replacement comparison score.

`prepare(sources, env_file, result_root, new_row_cap_usd, output)` copies each
completed prefix into a fresh external state, verifies inherited CAS/native
continuations, restores accepted edits, and rehearses one synthetic stop. It
loads no credentials and makes no real provider calls. A manifest binds parents,
first rebuilt inputs, model, task, credential path, implementation, runtime,
commit, and the proposed positive allowance. Read-only environment admission
uses existing images; there is no pull, build, or Docker start.

The parent model, reasoning effort, output ceiling, 24k/48k retention, evaluation
reserve and probe settings are retained. Calls, actions, mutations and active
time are not reset; elapsed time includes the final failed cost admission.
Only cost allowance is renewed. Historical spend remains separate from new
usage. Observation arm B is the identity projection: it adds no hints or cues.
Historical probe receipts remain provenance, not newly executed evidence.

`collect(manifest_path, approved_hash, approved_cap_usd)` requires the exact new
allocation. It uses one fresh branch per parent, serially, with a shared new-cost
cap and zero SDK retries. Stop remaining rows on count, transport, usage, cleanup
or identity uncertainty. A settled row-local cost stop does not reopen funds.
No automatic second continuation is allowed. Registered evaluation follows an
actual finish; native and operator-public assessments remain separate afterward.

Executed scope: the two 48k SQLFluff rows 3/5 under `C:/pt/sretlive01`, each once,
same `tasks/dev-train/current-dev20/18/public.yaml`, gpt-5.4-mini-2026-03-17/xhigh,
25,000 output ceiling, repository `.env`. Approved USD 1.20 additional per row,
USD 2.40 total. Preserve their remaining 4/7 model calls and approximately
430/367 solver seconds, with 330 evaluation seconds each. At the registered
60k-input/25k-output maxima, seven mini calls reserve at most USD 1.1025;
therefore USD 1.20 covers those calls without increasing any other limit.
Preparation alone does not authorize paid execution. The user approved this
allocation afterward; both failures remain separate from the original eight rows.
