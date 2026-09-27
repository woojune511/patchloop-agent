# Bounded live checkpoint comparison

`diagnostics/checkpoint_comparison.py` adds an explicitly funded, single-use live
collector to the frozen mutation-advice pair and shared checkpoint restoration.
The production runtime is unchanged. A keeps the saved first request; B removes
only the current message's mutation advice. Prior exposure and other cues remain.
After the first decision both arms use the ordinary runtime. This is a local
checkpoint diagnostic, not a comparison of general solver quality.

The separate [caller-information intervention](caller-information.md) reuses this
collector with `--caller-evidence` plus its hash. That mode keeps the original advice
in both arms and supplies verified later operator observations to B's first input.
Its manifest binds the different request hashes and evidence; old manifests do not
authorize it. Ordinary collection without these arguments retains advice removal.

## Preparation and admission

The [cleanup-information packet](cleanup-information.md) uses the same collector
with its evidence and first-input hashes already frozen in the packet. Do not
pass `--caller-evidence` for that schema. It restores the first failed-check
candidate instead of the original pre-edit workspace.

`prepare` binds the exact public dev-train task, model/settings, credential path,
source packet, first request identities, runtime, collector files and Git HEAD.
It freezes A1/B1/B2/A2 and a fresh external result root. Each row retains its
original remaining allowance; the invocation cap is four times that allowance.
Unused historical funds are closed. No credential contents are read in preparation.
The recorded manifest is not paid authorization. `collect` requires its approved
hash and exact positive new cap after explicit user approval of all live controls.

Read-only preflight validates tracked runtime/task inputs, prepared source and
dependency identities and already-local evaluator/probe images. It never starts
Docker, pulls/builds images, runs containers, counts tokens or calls a model.
READY is environment admission only; provider acceptance and task solving remain
NOT_RUN. Collection repeats admission immediately before execution.

## Cost, execution and stopping

An atomic fresh result directory makes a plan single-use, including interrupted or
failed attempts. There is no resume or retry command. Rows run serially because
restoration hooks are process-local. Every row gets a fresh base workspace, exact
completed source prefix and copied public CAS; no old action/probe is replayed.
Setup materialization is outside the inherited active deadline; runner preflight
and model/tool work consume the remaining active time. The saved first input's
displayed time is unchanged. Historical event/envelope identities remain source-bound;
the new group journal records the executing implementation and current Git HEAD.

The ordinary row ledger includes inherited usage for budget/context fidelity.
The shared invocation ledger includes only new settlements. Each count precedes
dispatch; row and group admission must both fit conservative input/output cost.
First count and dispatch must match the frozen request exactly, including output
ceiling. Recorded usage is provisional until the runtime confirms billing evidence.
An over-reservation response stops all rows; unexpected provider usage cannot be
undone and is not described as proof that actual billing stayed within the cap.

Zero SDK retries and the standard global Responses endpoint are inherited from
the existing adapter. Count, transport, usage, continuation or cleanup uncertainty
stops the group. Known ordinary row cost exhaustion can advance to the next fixed
row, without transferring unused allowance. Missing evaluation remains NOT_RUN;
unexecuted rows are NOT_RUN rather than incorrect solutions. On process interruption,
the durable journal is the evidence; do not resume to fill missing rows.

All generated plans, request artifacts and append-only dev-run-v1 group/branch
journals live outside the repository. No raw requests or isolated evaluator results
are projected into model context. New usage, inherited usage, infrastructure status,
public checks, submission and isolated acceptance/safety must be reported separately.
Local scripted tests do not establish live provider acceptance or an advice effect.
