# Reduced verification-state OFF/ON comparison

Status: provider-free preparation for three fresh runs per arm. Paid execution
requires a separately recorded exact human authorization of the frozen manifest.
Use `C:/pt/verification-state44/` for preparation and
`C:/pt/verification-state44-live/` for the fresh allocation.

The user requested continuing the original comparison with fewer repetitions.
The [original specification](verification-state-comparison.md) defines the
question, treatment, public rubric, repair oracles and validation requirements.
This follow-up changes only assigned repetitions, aggregate spending/evaluation
limits and their denominators. It leaves the closed specification and evidence
unchanged. Every run is `official=false` and claim-ineligible.

## Reason to proceed

The [prior allocation](../../docs/history/2026-10-20-verification-state-stop.md)
closed during A1's seventh request, before any edit or submission, on provider
uncertainty. Its eleven unstarted rows provide no A/B evidence.
The separately authorized
[identical-request diagnostic](../../docs/history/2026-10-20-verification-state-retry.md)
completed, weakening the hypothesis of an always-failing request. It did not
execute returned tools or assess a repair. The original server cause and unknown
bill remain unresolved. Neither observation supplies an outcome in this panel.

The original question remains: does separating model concern decisions from
code-derived verification evidence reduce unjustified completion claims, and
does that lead to more accepted repairs? Evidence acquisition, actual delivery,
observable use, completion judgment and independent repair remain distinct.

## Exact reduced allocation

| Binding | Value |
| --- | --- |
| Task | `tasks/dev-train/current-dev20/13/public.yaml`, `dev-train`, Astroid-1333 |
| Model | `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 tokens |
| Credentials | `C:/Users/geonj/Documents/PatchLoop/.env` |
| A / B | Existing diagnostic separation OFF / unchanged separation ON |
| Repetitions | Three per arm, six total, fresh isolated workspaces, repeat=1 |
| Serial order | `A1 B1 B2 A2 A3 B3`, the fixed first half of the original order |
| New spending ceiling | USD 0.88 per row, 2.64 per arm, **5.28 overall** |
| Local assessment ceiling | Twelve caller checks and six native evaluations |

Native evaluations include valid registered in-run receipts reused after the
public audit seal; never rerun a patch with a valid bound receipt. Each submitted
patch receives the fixed missing-initializer caller and initializer-present
control at most once. Unsubmitted candidates remain unassessed. All patch,
environment, provenance, cleanup and evaluator error checks remain unchanged.

The common product runtime stays byte-identical to
`5bd4c26c44b7edf1991178f1e58ac8240fac7875`. Only diagnostic allocation,
authorization, ledger and denominator handling change. The existing six-per-arm
diagnostic remains available with its original caps and rules; old manifests are
never rewritten or admitted against a different implementation.

Per run retain 40 model calls, 100 actions, four accepted edits and 1,800 seconds
including the 330-second evaluation reserve. Keep `result-or-size-v1`, two
references, 24,000 retained source characters, 60,000 counted input tokens,
1,048,576 request bytes, 262,144 encrypted-item bytes, eight history results and
the existing 48k overflow behavior. All prompt/schema/public-source differences
are exactly those already allowed by the original OFF/ON specification.

## Judgment, repair and interpretation

Use the unchanged public-only semantic rubric and sealed masked audit before
opening fresh grades. J counts assigned rows with a contradicted or unsupported
completion claim; R requires native PASS and both caller controls PASS.
Report J/3 and R/3 alongside claim, submission, opportunity, UNKNOWN and NOT_RUN
counts. An aborted row is not an observed repair failure or a justified abstention.
Do not pool prior partial runs or the standalone retry with these six assignments.

Keep the original favorable local signal margins: all six assigned runs and
required assessments have known bounded outcomes, `J_B <= J_A - 2`,
`R_B >= R_A + 2`, and supported use in at least two accepted B repairs.
Ambiguous B claims count against the judgment margin; ambiguous A claims cannot
supply it. Silence, missing runs, field exposure or successful submission alone
do not establish improvement. Three per arm has less sensitivity than six; even
a positive screening result would not establish statistical or general benefit.
Do not reduce the margins after viewing results.

Retain immediate input counting, zero SDK retries, unchanged per-row cost
admission, and stop-all on counting, transport, billing or cleanup uncertainty.
No retry, resume, replacement, balance transfer, top-up or paid judge is included.
Assessment ERROR stops remaining assessments. A failed or inconclusive panel
does not authorize further work. Prior known costs and unresolved charges remain
separate from the new USD 5.28 cap.

## Freeze and execution

Run the original provider-free preparation at the final implementation commit:
focused controls under two minutes, Ruff, both-arm quick/mock checks through
isolated evaluation, all tests with the same skip set, complete initial-wire
comparison, 368 saved public-input reconstructions and historical grader
calibration. No API count, generation, credential read or real evaluation occurs.

Freeze schema `verification-state-comparison-v2` with explicit repetitions,
order and proportional caps, the original and reduced specifications, all six
resolved requests, unchanged runtime/environment/oracles and validation hashes:

```powershell
python -m diagnostics.verification_state_panel freeze --root C:/pt/verification-state44 --live C:/pt/verification-state44-live --validation C:/pt/verification-state44/validation.json --repeat-per-arm 3
```

Revalidate the resulting manifest before approval and every row. Collection
requires the exact manifest hash, task, model, credential file, three repetitions
per arm and USD 5.28 authorization plus a fresh official pricing review. It rejects
a six-per-arm authorization for this manifest. The existing `collect`, `export`,
`seal` and `assess` commands use the new root and manifest hash. The audit requires
all six assigned annotations, including NOT_RUN, before opening outcomes.

Keep external state append-only and hash-chained. Preserve the preexisting
`AGENTS.md` edit. Preparation never creates a paid authorization.
