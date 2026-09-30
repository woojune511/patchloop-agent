# PDM repair preparation

Status: COMPLETE; approved single run finished; USD 3 allocation CLOSED at
USD 0.3550415. official=false and claim-ineligible. See the
[result](../docs/history/2026-10-01-pdm-repair-observation.md).
The preparation and originally proposed scope below are retained for provenance,
not permission for another execution.

## Question and scope

Observe one repair under the restored baseline on PDM's active-environment
selection issue. This is an exposed dev-train task, not unseen-task evaluation
or a comparison of prompts. The previous panel's unresolved failure does not
establish its cause. Do not provide earlier patches, trajectories or suspected
causes as hints to the agent.

- Task: `tasks/dev-train/pdm-ignore-active-venv-resolution-v2/public.yaml`.
- Source: PDM commit `881cd4e38d31663ae67bdae227ec1ccdfd5e2c77`.
- Change scope: `src/pdm/project/core.py`, one file, at most 60 diff lines.
- Observe handling of false-like settings, active versus descendant/sibling
  environments, and creation fallback through public evidence.
- Record actual repairs, registered checks and optional probes separately.
  Probe usage or successful submission alone does not establish improvement.

## Prepared environment

Source manifest:
`C:\pt\preparations\pdm-next-repair-20261001-v1\prepared-source.json`.
Admission hash:
`sha256:f52734730059484b1dd7fe4c3be4946385594e7abf6cd44394cb06c6730dc1b5`.

Existing pinned evaluator and public probe images were inspected without starting
Docker Desktop or acquiring images. Optional probes retain the previous
stdlib-only environment; PDM direct-import dependency readiness is not claimed.
Registered checks use their existing evaluator environment. No runtime, task,
prompt or dependency-profile change is included.

Provider-free verification journal:
`C:\pt\preparations\pdm-next-repair-20261001-v1\verification\runs\run_dev_b77819fcdcbe4174.jsonl`.
On unchanged source, the public active-venv contract produced 4 PASS / 20 FAIL,
including false-like settings, exclusion and fallback cases. This is an observed
task failure, not an environment setup failure. Container cleanup succeeded.
The upstream project regression passed all 36 tests (26.18 seconds reported by
pytest), also with confirmed cleanup. The five-event journal hash chain was
read back successfully. Provider calls: zero; isolated evaluation: NOT_RUN.

## Original proposed live scope, now completed

One fresh run, model `gpt-5.4-2026-03-05`, xhigh, 25,000 output tokens;
credential file `C:\Users\geonj\Documents\PatchLoop\.env`; repeat=1;
positive invocation-wide cap USD 3. Use the selected current-status policies
and limits (40 model calls, 100 actions, four accepted edits, 1,800 seconds).
Revalidate exact runtime/task/source/image identities before dispatch and record
the request in a fresh external journal. No previous allocation carries forward.

Count immediately before dispatch, zero SDK retries; stop on count, transport,
billing or cleanup uncertainty. No retry, resume, replacement row, second arm or
automatic paid follow-up. Preserve all evidence. Review the submitted diff and
public verification behavior before choosing any next intervention; report
isolated acceptance/safety separately from public checks and generalization.
