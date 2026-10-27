# Processing evidence and canonical diagnostic codes

Fresh diagnostic-presence originals declare `purpose.diagnostic_rules`: one to
four `{field, call_id, code, role}` rules. `field` is a flat JSON key (1-64 chars),
`call_id` is call-1 through call-4, and `code` is a stable diagnostic identifier
(2-32 characters, uppercase letters then digits, optional uppercase/digit/_/- suffix).
Use a public diagnostic code, not its explanatory message. No task-specific code
is injected. The selected code and caller/requirement mapping remain model-authored.

Each selected call must pair `role=failure` expected false with `role=processing`
expected true. Pick positive evidence from the intended fixture's public behavior;
an unrelated warning cannot establish intended processing. The same call/code
cannot serve both roles. Expected/failure JSON must be strict boolean objects with
exactly those distinct keys. The v7/v8 invocation reports per-call captures; the host searches code
tokens in each stdout/stderr independently, with ASCII identifier boundaries.
Longer identifiers such as XF0010, F00100 and F0010_EXTRA do not match F0010.
This is token extraction, not semantic parsing of diagnostic records.

The helper executes target calls and does not write a second Boolean extractor or
call `record_observation`. `probe_judgment.py` computes `captured-diagnostic-v2`,
status `computed`, source `host`, canonical JSON and bounded code witnesses. The
same rule runs before and after mutation: changed message text with the same code
remains a current-diff mismatch. Complete empty output also mismatches because
the processing code is absent. Both failures reach the next response and prevent
finish. Existing repair/check/finish limits and exact-diff replay reuse apply.
An incidental authored observation is retained only as information and cannot
override captures. It does not create an observation-correction obligation.

Missing/truncated captures, unexpected exceptions, setup failure and unhealthy
execution remain `unknown`/`not_compared`; absence of a Boolean extractor does not
erase execution failures. The actual API status is `capture_status='complete'`.
The shared `is_usable` contract connects computed values to first-call observation,
path diagnosis, repair prediction and concerns. Independent replay recomputation
still requires equality with the stored observed JSON.

For a silent target or without a stable processing code, use null rules and
`record_observation` with actual processed items, returned data or observable
effects alongside failure evidence. Do not invent target output. This path does not gain the code
contract's extraction guarantee. Neither path proves the selected observation
covers the public task, intended-file identity or semantic correctness.

## Fixture identity and target entry

Fresh v8 helpers retain v7's `reproduction_workspace()` for fixture inputs and
`reproduction_outputs()` for generated files and HOME/cache children. These are
separate stable sibling roots under the original sandbox cwd. Select actual
fixture paths in `observed_target(input_paths=...)`; generated output paths and
ancestors containing them are rejected as selected inputs. A deliberately read
warm cache is an input fixture, not an ignored output. There is no cache-name
filter or blanket HOME exclusion. Fixture changes remain identity differences.

The call row sets `target_started` immediately before invoking the declared
callable. Resolution, snapshot and signature-binding errors remain false with
incomplete outcome/captures. `completion_reproduction` excludes only completed,
bound v7/v8 cases whose every related call proves no target entry and whose host
receipts settle execution/cleanup. It retains action/input/program/case identities
in bounded `request_attempts`, full counts and the immutable journal. Attempts
still consume existing acquisition/action/cost limits; they grant no reproduction
credit. No established failure means the task obligation stays unverified.

Missing/malformed markers, legacy rows, pending related actions, any target entry,
timeout/truncation or cleanup uncertainty remain unverified case obligations.
This is not general case retirement. Corrected requests acquire a new case; only
its healthy baseline and comparable current replay can support verified delivery.
Null-rules observations and model-selected code witnesses remain coverage-limited.

## Expected exceptions

Fresh v8 `observed_target` accepts a tuple of at most four Exception or SystemExit
subclasses in `expected_exceptions`. Ordinary Exception observations require an
exact listed class: listing Exception does not match ValueError. SystemExit and
its subclasses are always captured with their actual `exit_code`, whether listed
or omitted. Listing them is redundant but valid. BaseException, KeyboardInterrupt
and GeneratorExit are not allowed in the tuple. Unexpected exceptions, incomplete
capture and target-entry uncertainty retain their existing verification limits.
An exit code or expected exception is an observation, not task success.

The generic and first-original descriptions share this contract. The v8 observer
only widens the configuration predicate for the already-supported SystemExit
family; it preserves output, exception and exit-code capture. Stored v1-v7 observer
bytes and replay behavior remain unchanged. A saved v7 request that explicitly
lists SystemExit therefore still has its historical configuration error.

## Frozen v1 diagnostic judgments

Saved v1-v7 invocations retain their exact observer programs and verdict semantics.
V6 code-only rules keep their prior host computation without new role requirements.
Their `{field, call_id, contains}` rules use a literal (1-160 chars).
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
not change old bindings or observer programs. Fresh wire identity is v67; exact
runtime recovery still forbids switching an existing run to new code.

## Legacy correction before source repair

`observation_correction.py` derives one run-wide correction opportunity from a
completed legacy original baseline conflict. Pending conflicts precede acquisition
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
The owner checks are `tests/test_canonical_diagnostic.py`,
`tests/test_behavior_diagnostic.py`, `tests/test_pre_target_obligations.py`,
`tests/test_processing_observer.py` and `tests/test_normal_diagnostic_continuation.py`,
included in quick. Normal-runner tests exercise changed wording and missing
processing through actual prepared requests and a second edit.
It uses pure receipts and trusted local adapters. Run quick separately; its
existing smoke reaches isolated mock acceptance, with safety NOT_RUN. Neither
local path establishes actual-model repair gain or Astroid acceptance.
