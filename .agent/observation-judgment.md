# Captured diagnostic judgments and one baseline correction

Fresh diagnostic-presence originals declare `purpose.diagnostic_rules`: one to
four `{field, call_id, contains}` rules. `field` is a flat JSON key (1-64 chars),
`call_id` is call-1 through call-4, and `contains` is a literal (1-160 chars).
Expected/failure JSON must be strict boolean objects with exactly those distinct
keys. The host searches both complete per-call Python streams separately; it
never concatenates channels, pools calls, parses whole-probe logs, runs arbitrary
extractors or hardcodes a task-specific error. Literal choice and public-task
mapping remain model-authored, not semantic coverage certificates.

`probe_judgment.py` derives the canonical host JSON and bounded witnesses with
call, channel and character offset. `record_observation` still records the
authored JSON. Agreement is `consistent`; disagreement is `conflict` with reason
`observation_conflict`, and both comparisons become `not_compared`. Execution,
setup, malformed observation, missing/truncated capture or unexpected exception
produces `unknown`, never an inferred false/no-error value. The receipt preserves
both authored and host values. Rules null/absent retain legacy arbitrary-value
semantics; that path does not receive a diagnostic-consistency guarantee.

The provider schema requires explicit nullable `diagnostic_rules` and
`corrects_action_id`; local legacy requests may omit them. Absent/null fields do
not change old bindings or observer programs. Fresh wire identity is v55; exact
runtime recovery still forbids switching an existing run to new code.

## Correction before source repair

`observation_correction.py` derives one run-wide correction opportunity from a
completed fresh original baseline conflict. Pending conflicts precede acquisition
attempt/action release: the runner offers only `run_probe` and `stop_task`, and
the gateway independently blocks exploration, edits, checks and finish. Current
state includes the target judgment, witnesses and bounded original request/program
even after a context transition, so correction does not require fresh exploration.
Candidate conflicts remain unverified and cannot masquerade as baseline correction.

Send a fresh changed observation program with `purpose.corrects_action_id` pointing
to the conflicting original action. Keep all other declaration fields, diagnostic
rules, failure/desired JSON, caller, fixture and environment unchanged. The host
reruns on the unchanged base. Correction requires complete healthy execution,
host/authored agreement, the declared original failure and identical v4 actual
conditions. Changing the input or weakening the expected outcome cannot correct
the old judgment. The program hash and case identity are new; no receipt is edited.

An explicit correction action start consumes the sole opportunity, including a
preflight rejection. An in-flight action owns its slot; recovery checks its exact
binding, and completed action_id/input_hash recovery returns the receipt without
redispatch. Repeated action IDs, new IDs, cached results or restart never renew it.
Replay of a successfully corrected binding remains ordinary exact-program replay,
not a second correction. Unknown dispatch/billing/cleanup retains existing stop rules.

## Evidence versions and notes

A verified correction links previous/current action and case IDs. Only the proved
conflicting case is superseded in active completion/replay accounting; historical
receipts and superseded-case metadata remain. Valid acquired failures cannot be
retired through this route. Independent setup-failed or otherwise unrelated cases
remain unverified; this is not a general case-retirement mechanism.

Findings and questions referencing a conflicted/superseded action require
revalidation; statements remain unchanged and source-only findings are unaffected.
Action-level provenance cannot prove that every linked sentence was false.
Conflicted/unknown diagnostic judgments cannot resolve verification concerns;
existing decisions referencing superseded evidence reopen in the current view.
Model prose cannot close the original obligation.

## Completion resources

A pending correction adds one real model call and one probe action. Its successful
successor reserves the corrected case's later candidate replay as well as source
repair, fresh checks and finish. The probe does not double-reserve its own model
call in successor cost accounting. It may use the minimum successful path rather
than speculative recovery; failure recovery is not guaranteed.

This is separate from protocol-response correction and its output allowance. No
new fixed 25K monetary reserve, cap increase or unlimited retry is added. Failed,
spent or unaffordable observation correction returns `VERIFICATION_INCOMPLETE`;
known physical/output limit stops retain their original cause in the terminal
horizon. Count/transport/billing uncertainty retains its original terminal.

Run the bounded owner selection with
`uv run --locked --offline pytest @tests/judgment-correction.txt --basetemp C:/pt/<unique>`.
It uses pure receipts and trusted local adapters. Run quick separately; its
existing smoke reaches isolated mock acceptance, with safety NOT_RUN. Neither
local path establishes actual-model repair gain or Astroid acceptance.
