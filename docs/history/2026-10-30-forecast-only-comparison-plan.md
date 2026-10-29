# Forecast-only checkpoint comparison

Prepared: 2026-10-30 KST. Status: prepared, exact paid allocation pending.
The user requested an experiment after the source-delivery correction. This plan
fixes its concrete scope; it does not reopen any previous allocation.

## Question and selected checkpoint

Does the action-specific budget forecast change the next action and repair outcome
at a public failure boundary where one extra probe consumes the remaining
edit/check/finish response route? The preceding
[source-delivery investigation](2026-10-29-public-alternative-and-budget-readiness.md)
found that the relevant current source was selected but omitted from completion
input. That implementation defect is fixed in `5e22e882`; both arms now receive
the same naturally selected source. No operator patch or extra source is supplied.

Use Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml` (dev-train),
public hash `sha256:bd47d10d4eb19d9db18dcccf04e27019f6307139b4d8841ec505b439135c4412`.
Restore the B checkpoint at cut258 from
`C:/pt/completion-guidance-run-v1/B/runs/run_dev_aecd56b8decc47ff.jsonl`.
Both forks use observation arm B, preserving all original public observations.
This is a continuation diagnostic on a previously inspected development task,
not a fresh solve or held-out evaluation.

OFF removes only `action_horizon.action_budget` before each request is assembled
and counted. ON retains it. Tool admission, source selection, public evidence,
system prompt, accepted patch and other limits remain identical. Execution order
is OFF1 then ON1; each variant runs once. No replacement or extra repetition.

## Exact proposed live allocation

| Field | Fixed value |
|---|---|
| Model | `gpt-5.4-2026-03-05`, xhigh, standard tier |
| Credential file | `C:/Users/geonj/Documents/PatchLoop/.env` |
| Repetitions | OFF1 + ON1, two continuation branches total |
| New allowance per branch | USD3.3184995 |
| New invocation-wide maximum | **USD6.636999**, approximately USD6.64 |
| Ordinary output ceiling | 40,000 tokens, subject to ordinary cost admission |
| Correction output ceiling | 25,000 tokens |
| Remaining resources | 4 model calls including 1 correction reservation; 12 actions; 2 accepted edits |
| Time | Preserve inherited deadline; approximately 1,617 solver seconds at the checkpoint and 390-second evaluation reserve |
| Policies | segmented-v1, thin, public-checks-v1, completion-recovery-v1 |
| Source retention | Existing 24,000-character bound; selected content22,155 characters |
| Execution identity | `official=false`; claim-ineligible |

This comparison preserves the historical total edit cap3, with one edit already
accepted, to avoid changing two variables. The product's selected 12-edit default
is unchanged. A quota comparison is a separate question.

Historical spend remains recorded but is excluded from new usage. Each row and
the group have separate admission checks. Unspent row allowance is not transferred.
The [official pricing page](https://developers.openai.com/api/docs/pricing), fetched
2026-10-29 UTC, lists standard GPT-5.4 prices per million tokens of USD2.50 input,
USD0.25 cached input and USD15 output, matching the existing ledger below its
60K input bound. The [official model page](https://developers.openai.com/api/docs/models/gpt-5.4)
confirms the selected snapshot and xhigh support. Actual account access remains
unverified until the authorized call.

## Execution and evidence

Runtime hash: `sha256:45e1bfe96a20897102c6903cc14a19e261f82bb5d4a0887a8f63e579707acb7c`.
Runtime, diagnostic implementation, launcher, exact HEAD, public task, parent
prefix and first normalized request hashes are bound in the manifest. A docs-only
commit also changes HEAD and requires fresh preparation; no guard is relaxed.

- External launcher: `C:/pt/forecast_live_comparison.py`.
- Final preparation: `C:/pt/forecast-live-preparation-20261030-v1/manifest.json`.
- Fresh result root: `C:/pt/forecast-live-20261030-v1`.
- The final manifest is generated after this plan's commit. Its hash is supplied
  in the approval and collector command, avoiding a document/hash dependency cycle.
- Preparation uses the actual existing live collector with a scripted provider
  and network disabled. It does not load credentials or run targets/containers.
- Live execution uses the ordinary monotonic deadline. Only elapsed-time fields
  and transport timeout are normalized for first-request identity comparison;
  runtime budgets and count/dispatch contents are not modified by normalization.
- Every actual dispatch requires its immediately preceding successful count.
  SDK retries are zero. Public tools and independent terminal evaluation use
  existing local images; no image pull/build is permitted.

Read-only environment checks passed: Docker already running, required evaluator
and Python3.10 probe image digests present, prepared source clean and hash-matched,
788 dependency files verified, credential path present and untracked. No credential
contents were printed. Ordinary live admission rechecks the task and images.

## Outcomes, decision criteria and stop conditions

Record the first selected action and whether it spends the remaining repair route;
then accepted mutations, current-diff required public checks, exact submitted
patch, independent acceptance/safety, new cost and elapsed time. Do not use private
evaluation material to score public reasoning or to construct model input. Inspect
public actions and evidence only; encrypted reasoning remains opaque.

A forecast-consistent action without a correct repair is a behavior observation,
not a repair improvement. An ON repair with successful public and independent
checks would justify another bounded diagnostic; one pair cannot establish a
causal effect or general quality. A tie or failed repair does not justify more
repetitions merely because money remains. No policy adoption is precommitted.

Stop all remaining rows on count, transport, usage, billing, continuation, target
execution or cleanup uncertainty, failed preflight, collector exception or process
interruption. Preserve completed effects and unknown billing; do not retry, resume,
extend resources or substitute a row automatically. Fresh output roots are single-use.

The experiment can begin after the user confirms this exact new allocation.
