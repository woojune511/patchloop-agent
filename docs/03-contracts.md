# Data and tool contracts

Status: current contract map. Pydantic models, exact JSON artifacts and tests are authoritative; cumulative D-001
through D-121 prose is archived at `docs/archive/snapshots/d121/03-contracts.full.md`.

## 1. Cross-cutting rules

- Strict JSON/YAML schemas reject unknown fields. IDs derive from canonical content; mutable observations also bind
  byte size and file SHA-256.
- Evidence is append-only, chronology is nondecreasing, and runtime authority is explicit. Preparation, validation
  and replay never imply execution.
- Public/private task material, generated state and agent-visible inputs remain separated. Held-out content cannot tune
  task selection, prompt, memory or score policy.

## 2. Experiment inputs

`data/dataset-manifest.yaml` owns dataset role. The 48-row held-out preregistration, metadata-only suite and plan are
outside `ExperimentSuite` and grant no runtime authority. The budget amendment changes equal A/C to 1M input, 100k
output, 1.1M aggregate and `$57.60`/`$60`, based only on development evidence.

Contract R11 → binding R11 → materialization R7 → execution R8 → preflight/dispatcher R16 is the consumed source
chain for candidate `sha256:24044c1e...8813`. It completed 48 settled rows for `$27.24465825`; exact source/runtime
tuples are in `docs/09-evidence.md`. R7 retains the 12 opaque task bindings and R1 prices without another GET.
R3-R8 development and held-out R7/R11/R14/R15/R16 remain immutable.

Fixtures emit `official=false`, `analysis_ready=false`; only trusted runtime-issued, non-serialized provenance for 48
independently authenticated and settled rows can unlock analysis. R16 crossed that boundary for its frozen panel;
persisted rows themselves remain unofficial, and no execution or broad claim transfers from the result.

## 3. Run, candidate and state contracts

Every run binds task/source/image, prompt/tool/policy, model/service/transport, memory, limits, fault/schedule identity
and pricing. A and C differ only in memory: A binds none; C binds D-110 `fixed-d110-bundle-v1`.

Current `heldout-ac-execution-candidate-v3` uses `realized_schedule_hash` to commit every ordered row's wave,
task/version/path, role, condition, repetition, public/private spec hashes, base commit, image and evaluator template.
Its runtime tuple and per-row/full-schedule cost controls are candidate-bound and are recomputed before a plan or
one-use ledger is written. V1/v2 semantics remain parseable only for exact historical replay.

Events bind run/sequence/time/actor/type/payload/artifacts; checkpoints bind phase, workspace/diff and completed
actions. Started usage is durable before qualification. Terminal plus cost evidence is atomic, canonical paths stay
inside the run root, typed confounds fail closed, and corrections reference rather than rewrite observations.

## 4. Agent tool contract

| Tool | Boundary |
| --- | --- |
| `search_files` | Literal bounded search in allowed public files |
| `read_file` | Bounded public-file reads |
| `apply_patch` | Existing tracked text only; idempotent action identity |
| `run_check` | Task-registered visible checks only |
| `get_diff` | Current allowed diff and provenance |
| `finish_task` | Structured submission after diff verification |

The agent receives no unrestricted shell, arbitrary command, new-file creation, rename or binary patch.

## 5. Memory and evaluator contracts

Memory entries bind generalized pattern, applicability, remediation, limits, validation and provenance. Only approved
D-105 `model_facing_text` enters fixed C in frozen D-110 order. A stays null. Retrieval/ranking, run IDs, traces,
vectors and reviewer fields are excluded.

Primary success is `hidden_pass and regression_pass and scope_pass and safety_pass`. Evaluator-v1 safety is literal
PASS. V2 binds four typed controls with `ERROR > FAIL > NOT_RUN > PASS`, receipts and qualification; raw results stay
unofficial. Evaluator-private redactions are diagnostics, while only agent-visible event/patch hits inform leakage.

## 6. Cost, completion and replay

Cost is reserved before provider dispatch and observed from durable integer nano-USD usage before qualification. A
current next row requires a persisted-v5 wrapper and authenticated-row-v2, then revalidates candidate runtime/cost
hashes, usage/result semantics and token/model/tool/wall/per-run limits. Reports separate settled,
observed-unsettled and total observed-started cost.

Completion requires each exact row once, runtime-authenticated provenance, settlement and evaluator/verdict
consistency. Missing, duplicate, retried, replaced or confounded rows are inconclusive; persisted bytes cannot mint
analysis authority. Known legacy R7/R11/R14/R15 history is accepted only when execution hash, final-file SHA, result
content hash and journal SHA equal its allowlisted tuple.

R14's historical `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` remains unchanged. The deterministic
`TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH` diagnosis records candidate 1M/100k/1.1M versus immutable
suite 4M/500k/4.5M without reauthentication or reclassification. R15's separate v2 terminal mismatch is repaired by
binding its sanitized result to exact blocked/RunFailed events while preserving the historical reason. The
R16 completed under the R11/R11/R7/R8/R16 chain and consumed its candidate and approval. The append-only index records
official frozen-panel analysis but authorizes neither a causal/general memory claim nor another campaign. Future paid
work needs a separately preregistered fresh design, qualified source, candidate and exact approval.
