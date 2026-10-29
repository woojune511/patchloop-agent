# Integrated test-selection follow-up

Date: 2026-10-30 KST. Status: prepared; new paid allocation awaiting confirmation.

## Question and frozen conditions

The user requested a fresh integrated experiment after the
[selection and host-latency changes](2026-10-30-test-execution-visibility-and-latency.md).
Check whether the current agent actually executes added/changed tests, preserves
task correctness and regressions, and changes total time, host time or API cost.
The previous [three-task result](2026-10-30-integrated-dev3-results.md) is the
observed development baseline, not a causal control or a general success rate.

Tasks 3 (pvlib1154), 13 (Astroid1333) and 18 (SQLFluff1733) each start fresh once.
The first and third exposed omitted new tests; Astroid also exercises recovery
from public regression failures. Model: `gpt-5.4-2026-03-05`, xhigh, 25,000 desired
output tokens. Current/brief-v1, segmented-v1/result-or-size-v1, public-checks-v1,
ordinary probes, repair recheck, protected inspection and per-call cost admission
remain fixed. Limits: 40 model calls, 100 actions, 12 accepted edits and 1,800
seconds per task, including a 330-second evaluation reserve. No old patch, agent
state or operator solution is seeded.

Proposed new allocation: USD4 per task, USD12 total, maximum two workers;
credential file `C:/Users/geonj/Documents/PatchLoop/.env`. No cap transfer or
automatic retry; count, transport, billing, continuation or cleanup uncertainty
stops new batch admissions while already admitted calls settle. Earlier
allocations are closed and do not authorize this run.

Implementation: `ce3f8391`. The existing batch scheduler and registered isolated
evaluator are reused. The external launcher differs from the preceding run only
in fresh result paths and reading its directly frozen `manifest.json`.
All source/dependency/image and credential-shape preflights passed without a model
call. Seven synthetic assessment controls passed. No image was pulled or built.
The [official pricing page](https://developers.openai.com/api/docs/pricing) was
checked: standard GPT-5.4 input/cached-input/output USD2.50/0.25/15 per million,
under the runtime's 60K input limit. The client pins the default service tier and
zero SDK retries; actual input is counted immediately before each dispatch.

Preparation: `C:/pt/integrated3-selection-20261030-v1/manifest.json`.
Manifest hash: `sha256:099ffe2bb2ca22a864dda0a791a049de0895514de193f0789cbdbe33bf0cf6d5`.
Separate new result root: `C:/pt/integrated3-selection-run-20261030-v1`.
Requests, preparation receipts and the frozen runtime identity are bound there;
the preparation journal is append-only, hash-chained `dev-run-v1`.

## Assessment

For every added/changed public test file, distinguish explicit selection, partial
node selection, directory discovery and actual execution evidence. A command PASS
or visible advisory field alone is insufficient. If a run adds no test file, do
not count that as proof that new-file omissions were fixed. Inspect only public
actions, delivered context and public outputs; do not inspect hidden checks,
reference patches or private evaluator details.

Record independent acceptance and safety, public regression outcomes, submitted
diff, test choices, model calls, settled cost and whole-task/batch time. Separate
provider wait from tool/host work and record any remaining unclassified interval.
Keep operator follow-up checks separate from the agent's own decisions.

Keep the changes if useful selection behavior appears without a concrete
correctness/reliability regression; investigate specific failures if omissions
persist. Three exposed tasks with one run each do not establish causal speed gain,
test-selection probability or generalization. No further run is automatic.

## Execution

No live provider calls have been made for this new allocation yet.
