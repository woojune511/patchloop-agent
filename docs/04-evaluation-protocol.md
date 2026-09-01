# Evaluation protocol

## Development lane

All runs are `official=false`. Mock accepts smoke tasks; live OpenAI accepts only
checked-in `tasks/dev-train/<task>/public.yaml` packages. Development validation
and held-out tasks are not accepted for live tuning.

Before live work, PatchLoop validates the task package, credential file, pricing,
external state root, Docker availability, and exact local evaluator image digest.
It neither pulls nor builds an image.

## Visible checks

The agent may execute only checks registered in `public.yaml`. A visible PASS is
bound to the current diff hash. Any subsequent mutation invalidates it.

## Submission and private evaluation

After all visible checks pass, `finish_task` captures the full patch in the
content-addressed artifact store. The evaluator creates a separate clean
workspace, applies that exact artifact, then copies hidden material into only the
evaluator workspace. It runs visible regression checks, private hidden checks, and
static scope/dependency/test/public-API policies.

The agent never receives evaluator details. The user-visible run record contains
only PASS/FAIL and a public-safe failure class. Artifacts retain hashes and
provenance outside the repository.

## Cost and uncertainty

OpenAI pricing is code-owned per exact model ID; unknown IDs fail before a call.
The current GPT-5.4 mini rates and supported reasoning efforts were verified on
2026-09-01 against the official [API pricing](https://developers.openai.com/api/docs/pricing)
and [model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
Immediately before generation, the adapter uses the official
[input-token count endpoint](https://developers.openai.com/api/docs/guides/token-counting)
on the actual request. The ledger reserves that input plus a conservative output
ceiling, shrinking the ceiling when needed. If a minimum 128-token output cannot
fit, the row terminates `COST_CAP_REACHED` without generation.

The cost cap covers all repetitions in the invocation. SDK transport retry is
zero. Count timeout, provider timeout, missing durable usage, or billing uncertainty
stops every remaining repetition. Ordinary agent/task failure may start a new run
ID only while declared repetitions and cap remain.
