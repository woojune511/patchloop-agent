# Evidence and limitations

## Current local evidence

Following the Rapid Dev Reset, local checkpoints recorded:

- `uv run ruff check patchloop tests` passed.
- The locked fast suite passed 26 tests in 10.46 seconds after documentation consolidation.
- Mock end-to-end reached `EVALUATOR_PASS` after parallel inspection, one mutation,
  a visible check, automatic diff projection, finish, and isolated evaluation.
- Task-loader identity hashes remained stable for representative smoke,
  `dev-train`, and held-out task packages.
- Active legacy Rapid/import references were absent.
- The visible-doc allowlist, hidden agent guide, and current local Markdown links
  are enforced by the fast suite.
- After the first-live diagnosis, the context-projection checkpoint passed Ruff,
  29 tests in 16.45 seconds, and mock `EVALUATOR_PASS`. This is local evidence only.
- The resume checkpoint adds provider-free fault injection across decision, mutation,
  check, and batch boundaries; it verifies exact mismatch rejection, terminal
  idempotency, durable cost/counter restoration, and no repeated mocked provider
  dispatch. Ruff passed, 39 tests passed in 35.15 seconds, and mock smoke reached
  `EVALUATOR_PASS`. This remains local contract evidence, not provider acceptance.
- The provenance/safety checkpoint passed Ruff and 54 tests in 50.43 seconds.
  Provider-free evaluator tests reject task, image, and patch mismatches before
  workspace creation; map synthetic Docker policy match, violation, and missing
  evidence to PASS, FAIL, and ERROR; and preserve policy hashes after an injected
  evaluator error. Mock smoke reports task acceptance PASS, safety NOT_RUN, and
  `claim_eligible=false`.
- After the second-live mutation-format diagnosis, the focused mutation/resume set
  passed 29 tests in 44.52 seconds. Full Ruff and 56 tests passed in 50.92 seconds,
  and mock smoke reached isolated `EVALUATOR_PASS` through one accepted
  `apply_git_diff` mutation. This verifies the local tool/recovery wiring only; it
  did not by itself show that a provider would emit the new wire format.
- The failed-mutation continuation checkpoint passed Ruff and 59 tests in 50.51 seconds.
  Focused tests retain a bounded failed mutation across four later read cards and a
  gateway restart, replace it with a later mutation, clear it only on success, and
  keep tool failure separate from protocol correction. Mock smoke still reaches
  isolated `EVALUATOR_PASS` with task acceptance PASS and safety NOT_RUN. A read-only
  hydration of the third live journal recovered its failed diff hash, hypothesis,
  public anchor, and patch line 27 without changing that immutable run.
- The hunk-recount checkpoint passed Ruff and all 62 tests in 55.10 seconds.
  Focused tests verify that incorrect hunk totals are accepted while invalid
  source context is rejected, scope rollback restores the exact HEAD blob, and crash
  reconciliation recognizes an already-applied recounted patch. Recount is shared by
  check, apply, rollback, and reverse-check paths; it does not bypass the existing
  tracked-path, anchor, scope, or final-diff contracts. Mock run
  `run_dev_8ba03a7965a048c5` reached `EVALUATOR_PASS` through one accepted mutation with
  task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero model cost.
- Provider-free retrospective run `run_dev_replay_d1d2519dbd9644f9` replayed the
  fourth live row's first exact raw diff through the current gateway in external
  state root `C:\patchloop-replay-880c0a55`. The mutation was accepted, all three
  version-1 visible checks passed, and `finish_task` submitted canonical diff
  `sha256:317ac609a2a9e555d0c38a5bf489c1dc68edd9c81457f598dbbf81fe3570d8c7`.
  The isolated evaluator applied the same hash and completed with task acceptance
  FAIL, failure class `PRIVATE_EVALUATION_FAILED`, and safety PASS. The source run
  remained byte-identical. There were zero provider calls and no image pull/build.
- The original `loguru-invalid-format-feedback` package remains version 1. A separate
  `-v2` package adds one public black-box check for the issue's missing-key feedback,
  available-key guidance, canonical `logger.bind()` / `{extra[key]}` usage, and
  `catch=True` / `catch=False` behavior. Its task content hash is
  `sha256:61704553b8ba733bad7350561eec397a7a6c04365a56ef61854a9e12cefe259d`.
  Provider-free run `run_dev_v2check_7084999308874e66` showed that the clean base and
  retrospectively replayed patch fail this new check, while an independently derived
  temporary public correction passes all four visible checks and reaches
  `finish_task`. It ran no hidden evaluator and makes no acceptance claim. Ruff
  and all 63 tests passed in 54.28 seconds; mock run
  `run_dev_99bbb59c944d4c37` reached `EVALUATOR_PASS` with task acceptance PASS,
  safety NOT_RUN, `claim_eligible=false`, and zero model cost.
- After the fifth-row diagnosis, the tool-alignment checkpoint passed focused
  context/tool/runner tests, Ruff, and all 69 tests in 69.15 seconds. The tests
  cover required tool choice in both generation and input counting, content-free
  output-shape provenance, complete four-check projection, correct PASS guidance,
  registered check enums, a non-empty submission gate, consecutive correction
  reset including resume reconstruction, and structured unsuccessful stop. Mock
  run `run_dev_6374b31034c44427` reached isolated `EVALUATOR_PASS` through one
  accepted mutation with task acceptance PASS, safety NOT_RUN,
  `claim_eligible=false`, and zero model cost.
- Version 3 preserves version 2 and replaces only its private literal-phrase oracle
  with semantic `logger.bind(...)` then `{extra[...]}` recognition. Task validation
  reports content hash
  `sha256:21f5f668c4f6ef85a2c1a45f4371cbd050de0e73dfcf8605a3c398413374c15b`.
  The focused contract set passed 13 tests, Ruff passed, and the final full suite
  passed 70 tests in 73.38 seconds. Mock run `run_dev_db9548d402084112` reached isolated
  `EVALUATOR_PASS` with task acceptance PASS, safety NOT_RUN, and zero model cost.
- The import-contract checkpoint made the `patchloop.dev` and `patchloop.verifier`
  package exports lazy while preserving their public names. Fresh-process tests cover
  lightweight package imports and both formerly failing submodule orders. Ruff and
  all 73 tests passed in 70.71 seconds; mock run `run_dev_d309590128764086` reached
  isolated `EVALUATOR_PASS` with zero recorded cost.
- `pyfakefs-makedirs-parent-traversal` version 2 preserves the version-1 task and adds
  one public black-box parent-traversal check. Task validation reports content hash
  `sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87`.
  The provider-free Docker matrix accepted the reference only and rejected the clean
  base plus all nine known-bad cases. A manifest-bound reference evaluation reported
  every task and safety axis PASS. Ruff and all 74 tests passed in 73.40 seconds;
  mock run `run_dev_55d5e74e1bd743d1` reached isolated `EVALUATOR_PASS` with zero cost.
- The post-eighth action-coupling checkpoint passed Ruff and all 78 tests in 114.69
  seconds using an external short temp root. Mock run `run_dev_198843ed55274f09`
  reached isolated `EVALUATOR_PASS` in four model turns and five tool actions through
  one accepted mutation, with task acceptance PASS, safety NOT_RUN,
  `claim_eligible=false`, and zero cost. This is provider-free contract evidence only.
- The ninth live row exposed a cross-call contract mismatch before the new action
  horizon could be exercised. Its provider responses and the subsequent provider-free
  correction are recorded below. Ruff and all 79 tests pass in 113.24 seconds with a
  short external temp root. Mock run `run_dev_a7724af70efb4984` reaches isolated
  `EVALUATOR_PASS` through one accepted mutation with task acceptance PASS, safety
  NOT_RUN, `claim_eligible=false`, and zero cost. This is provider-free contract
  evidence, not task-acceptance evidence for the ninth row.
- The reset changed no tracked bytes under `reports/`, `experiments/`, or
  `docs/archive/` relative to checkpoint `b71ddeee`.

These are local observations, not provider or claim results.

## First live development observation

On 2026-09-02, one separately approved row used:

- task `loguru-invalid-format-feedback` from the checked-in `dev-train` split
- model `gpt-5.4-mini-2026-03-17` with medium reasoning
- one repetition under a $1.20 invocation-wide cap
- external state root `C:\patchloop-live-20260902-loguru-r1`

Run `run_dev_e89e940c0715474e` wrote a valid 455-event hash chain ending at
`sha256:36a3e266f769197203f04870d49e92411a62bbcf7cc7daf43bc97af250167f9a`.
It reached `LIMIT_REACHED` (`tool-action limit reached`) in 141.147 seconds.
All 39 provider calls completed with the requested model and no unmatched call
start. Recorded usage was 91,907 input tokens, including 17,408 cached tokens,
and 4,866 output tokens, including 1,384 reasoning tokens. Recorded cost was
$0.07907685.

The agent made 76 searches and 23 reads, all successful, but used only 26 distinct
action input hashes. One successful `KeyError` search repeated 33 times and one
successful `format(` search repeated 18 times. No plan, edit, check, mutation,
submission, artifact, or evaluator result was produced. This is live development
evidence of a context-projection failure expressed as duplicate inspection, not
task correctness or quality evidence.

## Second live development observation

After the local context, resume, provenance, and safety changes, a separately
approved row repeated the first row's task, model, reasoning, repetition, and $1.20
cap with external state root `C:\patchloop-state`. Run
`run_dev_9939bd27c5d04819` wrote a valid 597-event hash chain ending at
`sha256:2b19997707abab44bcd1f3795c5e73a7975a2e245569ec0e6722f583fd132916`.
It reached `LIMIT_REACHED` (`model-call limit reached`) after 209.250 active seconds
and 214 seconds of run age. All 40 provider dispatches recorded durable completions;
one incomplete response used the single protocol correction. Recorded usage was
215,705 input tokens, including 3,584 cached tokens, and 22,116 output tokens,
including 16,172 reasoning tokens. Recorded cost was $0.25888155.

The run made 69 searches, 21 reads, and two mutation attempts. Across all 39
turn-to-turn transitions, every action ID from the prior parallel batch appeared in
the next canonical context artifact. Thirty-nine repeated exact requests were cache
hits and only soft stagnation signals were emitted. The mutation attempts on turns
36 and 39 both supplied Codex-style `*** Begin Patch` wrappers; the fail-closed tool
rejected them because it accepted only a raw Git diff. No mutation was admitted, so
no visible check, submission, or evaluator followed. This is live evidence that the
latest-batch projection defect was not the direct terminal cause in this row; it is
not evidence of task acceptance, safety, or general coding quality.

## Third live development observation

After the raw-diff tool contract was made explicit, a third separately approved row
again used `loguru-invalid-format-feedback`, `gpt-5.4-mini-2026-03-17`, medium
reasoning, one repetition, the $1.20 cap, and external state root
`C:\patchloop-state`. Run `run_dev_ef58e14b40834f0b` wrote a valid 604-event hash
chain ending at
`sha256:ed9915e6dbbb48aa4fc6cdeccd45e479df1aa1e3c92fd441110c8fba69efe7cf`.
It reached `LIMIT_REACHED` (`model-call limit reached`) after 172.780 active seconds
and 174 seconds of run age. All 40 provider dispatches recorded durable completions.
Recorded usage was 249,211 input tokens, 12,666 output tokens including 8,325
reasoning tokens, and $0.24390525 of cost.

The run made 74 searches, 19 reads, and one `apply_git_diff` call. On turn 3 the
provider emitted a raw Git diff beginning with the required `diff --git` header. Its
first hunk declared 20 post-image lines while containing 21, so fail-closed
`git apply --check` rejected it with `corrupt patch at <stdin>:27` before applying
anything. The next context artifact contained that exact tool result and remained at
the `needs_mutation` gate. The following 37 turns nevertheless used only read/search
actions. Of 93 read/search actions, 31 were cache hits, 59 returned no new span, and
three emitted a soft stagnation signal. No signal blocked execution. No mutation was
accepted, no visible check or submission occurred, and no evaluator ran.

This row is bounded live evidence that the renamed schema and raw-diff prefix are
provider-compatible. It also isolates a later failure boundary: a malformed mutation
was reported correctly for one turn, but the unresolved repair target was displaced
by subsequent bounded attempt cards. It does not justify a hard repeated-evidence
terminal or establish task acceptance, safety, or general coding quality.

## Fourth live development observation

After failed-mutation continuation was implemented, a fourth separately approved row
again used `loguru-invalid-format-feedback`, `gpt-5.4-mini-2026-03-17`, medium
reasoning, one repetition, the $1.20 cap, and external state root
`C:\\patchloop-state`. Run `run_dev_dd7c981c6d024bcf` wrote a valid 537-event hash
chain ending at
`sha256:3e6674cbcaa7491bff9715926f64fff7e5c9a4c4f5b4ddc8ffe6cb097b96e91d`.
It reached `LIMIT_REACHED` (`model-call limit reached`) after 293.264 active seconds
and 298 seconds of run age. All 40 provider dispatches recorded durable completions;
one incomplete response used the single protocol correction. Recorded usage was
262,346 input tokens including 12,800 cached tokens and 34,439 output tokens including
16,473 reasoning tokens. Recorded cost was $0.343095.

The run made 44 searches, 15 reads, and 13 `apply_git_diff` calls; 21 read/search
actions were cache hits. Every failed mutation's exact action and error appeared in
the immediately following context, and `last_failed_mutation` was present in all 23
turn contexts after the first failure. The agent repeatedly repaired or replaced the
diff instead of abandoning mutation for the rest of the row. This confirms the
bounded continuation behavior in a live loop.

None of the 13 mutation attempts applied. Every diff contained at least one hunk whose
declared pre- or post-image total differed from its body; strict Git reported 12
`corrupt patch` failures and one `patch fragment without header` failure. A read-only
`git apply --check --recount` against the retained isolated workspace accepted all 13
exact diffs without modifying it. This isolates hunk-total arithmetic as the current
wire boundary, but does not show that any patch is semantically correct. No mutation,
visible check, submission, evaluator, task acceptance, or safety result was produced.

## Fifth live development observation

After deterministic hunk recount and the version-2 public contract were implemented,
a fifth separately approved row used task version 2,
`gpt-5.4-mini-2026-03-17`, medium reasoning, one repetition, the $1.20 cap, and
external state root `C:\patchloop-state`. Run `run_dev_329131da9a4940c3` wrote a
valid 396-event hash chain ending at
`sha256:1044b780d95813be4fd927c8c4ec95a10f6a2ffd1838c0993ffd7c8b499b4261`.
It reached `PROTOCOL_VIOLATION` (`model response must request at least one tool`)
after 140.703 active seconds and 142 seconds of run age. All 29 provider dispatches
recorded durable completions. Usage was 177,028 input tokens including 7,168 cached
tokens and 10,320 output tokens including 7,088 reasoning tokens. Recorded cost was
$0.1743726.

The run made 37 searches, 14 reads, one accepted `apply_git_diff`, and three passing
checks: `invalid-format-feedback-contract`, `basic-format-regression`, and
`patcher-field-regression`. It thereby establishes a post-recount live mutation and
public-check execution, but not submission or acceptance. On turns 27 and 29 the
provider responses completed with 303/149 and 228/83 output/reasoning tokens
respectively, but their recorded tool-call lists were empty. The old adapter did not
retain output item types, so the journal cannot establish whether the discarded
items were messages, reasoning, or another non-function shape.

Both corresponding contexts had gate `needs_visible_checks` and listed all four
public checks in the task. However, bounded `recent_checks` contained only the two
then three completed checks, did not name the remaining
`upstream-format-regression`, and every PASS attempt card incorrectly asked what the
public “failure” had falsified. The request itself did not require a tool even though
the application rejected an empty tool batch. The terminal is therefore evidence of
an application-level request/context mismatch, not proof of a malformed provider
response or failed task patch.

After the run, one provider-free Docker invocation used the retained exact diff,
the already-local pinned image, `--pull never`, a read-only workspace mount, and the
registered `upstream-format-regression` command. It passed all 20 tests in 0.26
seconds. This result was intentionally not appended to the immutable live journal;
it proves only that the missing public check passes on the retained diff. No hidden
evaluator ran.

## Sixth live development observation

After required tool choice, complete check-status projection, output-shape metadata,
and structured stop were implemented, a sixth separately approved row used task
version 2, `gpt-5.4-mini-2026-03-17`, medium reasoning, one repetition, the $1.20 cap,
and external state root `C:\\patchloop-state`. Run `run_dev_f1bb02f3e3154bb8` wrote a
valid 513-event hash chain ending at
`sha256:503a30a884ec0257bb35a12b454aab2da8c9dd8ba4b6ad5be23a30f4eea0bcc6`.
It reached `EVALUATOR_FAIL` after 227.735 active seconds and 229 seconds of run age.
Usage was 269,693 input tokens including 9,856 cached tokens and 15,535 output tokens
including 8,183 reasoning tokens. Recorded cost was $0.26552445.

All 38 provider responses contained at least one function call; the recorded shapes
comprised 38 reasoning items and 68 function calls. The agent made 45 searches, 13
reads, five mutation attempts, four visible checks, and one finish call. Twenty exact
read/search requests were cache hits. Four mutation actions failed before one was
accepted; the run then passed all four registered visible checks. The visible-check
diff, submitted artifact, and evaluator-applied patch were identical at
`sha256:e55b934c407a36807344f2f9e378c54c10283e407b063033972183ea0f43254f`.
This is live evidence that the aligned tool requirement, complete check projection,
mutation recovery, submission identity, and evaluator handoff can complete together.

Evaluation completed with regression PASS, scope PASS, typed Docker safety PASS,
and task acceptance FAIL (`PRIVATE_EVALUATION_FAILED`). The failure was caused by a
private literal-phrase assertion stricter than the public version-2 contract, which
explicitly allowed semantically equivalent guidance rather than one exact sentence.
The private wording and test body remain outside coding-agent context. This mismatch
invalidates the result as a negative coding-agent verdict; it does not turn the row
into task acceptance or a quality claim. Version 2 remains immutable evidence, and
any oracle correction must use a versioned successor.

## Version-3 provider-free oracle validation

The successor package `loguru-invalid-format-feedback-v3` changes the task version,
private semantic assertion, and task audit while preserving the version-2 public
behavior and all reference/known-bad/environment fixture bytes. Versions 1 and 2
remain unchanged. Its identities are:

- public spec: `sha256:40039f93b0955260a1942808adcae72b14d813db6c791feed686e5d0f5125a9a`
- private spec: `sha256:eafeb4fd0355972cd9da67983dfacf20bbe854bdf3da9501dc6f5752705f29ee`
- task content: `sha256:21f5f668c4f6ef85a2c1a45f4371cbd050de0e73dfcf8605a3c398413374c15b`

Provider-free evaluator run `run_dev_v3candidate_f1bb` used the already-local pinned
image and the sixth live row's exact submitted patch
`sha256:e55b934c407a36807344f2f9e378c54c10283e407b063033972183ea0f43254f`.
The manifest, submitted artifact, applied patch, and resulting diff remained bound to
that identity. All four visible checks, the semantic hidden check, four scope/policy
checks, and all four typed safety controls passed. The result, manifest, and
provenance are retained under external root `C:\patchloop-v3-eval-f1bb`; the run is
`official=false`, used no provider, and cannot retroactively alter the sixth row.

Provider-free evaluator run `run_dev_v3reference` separately bound and applied the
byte-identical reference patch
`sha256:bed37a0dbf76a572a68853db61e6ae24dc74a0791457f2f96fece1b75ec8de3a`.
Hidden, regression, scope, and safety all passed; its artifacts remain under
`C:\patchloop-v3-eval-reference`.

A separate Docker matrix cloned the same exact base locally and used `--pull never`.
The clean base failed both public and private missing-key behavior checks and had no
submission. The reference patch passed visible, hidden, and scope acceptance. All six
declared known-bad patches were rejected: four failed behavior checks, the forbidden
path also failed scope, and the no-op had no submission. This guards against fixing
the version-2 false negative by making the oracle vacuous.

The first matrix harness attempt also exposed a separate, reproducible import edge.
That local defect is now fixed: both package roots resolve their public exports lazily,
the runner imports the concrete evaluator module, and fresh-process regressions cover
both import orders. The production evaluator result above was unaffected.

## Pyfakefs version-2 provider-free contract validation

The original `pyfakefs-makedirs-parent-traversal` package remains version 1. The
separate `-v2` successor changes only the public/private task versions and adds one
visible check derived from the public issue. The check calls repository APIs without
inspecting source shape and exercises ordered traversal in POSIX and Windows modes,
bytes paths, and separation of intermediate-directory mode from the requested leaf
mode. Environment, hidden evaluator, reference patch, nine known-bad patches, and
task audit bytes remain identical to version 1. Its identities are:

- public spec: `sha256:1b9865bf7cfbd6937ebc17ef9257112b7d63868431f38eeac62a603a68a0db6a`
- private spec: `sha256:540ea69225bd3410626f7db27933396220562f6743bd9f39df9ed233c6f5253f`
- task content: `sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87`

The already-local digest-pinned image was used with `--pull never`, network disabled,
and a read-only workspace mount. In the successful 11-case matrix under
`C:\pl-pyf-v2-matrix-99fac9de`, the clean base failed the new public behavior check
and private acceptance, the reference passed every visible/private/policy axis, and
all nine declared known-bad cases were rejected. The new visible check itself rejects
the normalization, parent-mode propagation, string-only, early-return, and uncaught
parent variants; other partials are rejected by upstream or private behavior checks,
and the forbidden-path case also fails scope and test-tampering policy.

The first ad hoc matrix attempt copied hidden files into the workspace before taking
the submitted diff summary. That made `.patchloop-hidden` appear as an untracked scope
violation and falsely marked every case, including the reference, as scope FAIL. The
attempt was interrupted and supports no task conclusion. The corrected harness first
freezes the submission diff and policy inputs, then injects hidden files, matching the
ordering in `EvaluationEngine`.

Manifest-bound evaluator run `run_dev_pyfakefsv2reference` under external root
`C:\pl-pyf-v2-eval-47e71bf5` applied canonical reference artifact
`sha256:ffc4b0fa6a3c83b76d3778172cbcccb922ba081cabde141484fe85eab75a27be`.
Hidden, regression, scope, and typed Docker safety all reported PASS. The run is
`official=false`, used no provider, and is task-contract evidence rather than a live
coding-agent observation.

## Seventh live development observation

After the repository-root `.env` was restored from the exact external path to which
it had previously been moved, its format was validated without exposing the value.
One separately approved invocation then used
`pyfakefs-makedirs-parent-traversal` version 2,
`gpt-5.4-mini-2026-03-17`, medium reasoning, one repetition, the $1.20 invocation cap,
and external state root `C:\patchloop-state`. No image was pulled or built, Docker
Desktop was not started by PatchLoop, and no retry followed.

Run `run_dev_42d9c3c06c6a4be9` wrote a valid 580-event hash chain ending at
`sha256:fe975460f70726dc59be36b7c5c54153ab81d355df8154495137d50d0fdcedfb`.
It reached `LIMIT_REACHED` (`model-call limit reached`) after 198.531 active seconds
and 203 seconds of run age. Usage was 287,487 input tokens, 12,156 output tokens
including 8,800 reasoning tokens, and $0.27031725 of recorded cost. All 40 provider
responses completed and recorded a reasoning item plus at least one function call.

The 86 successful actions comprised 44 reads and 42 searches. Twenty-five exact
requests were cache hits, 34 results added no source span, and no tool action failed.
The `makedirs` source appeared in every canonical context from turn 2 through turn
40. The final context artifact was
`sha256:003f43c75f10af0283222e45e31da34006c4c146a1c88309c94320e49c78ee7d`;
it projected the latest three results plus eight working spans, gate
`needs_mutation`, both visible checks as `NOT_RUN`, and one remaining model call.
Despite that evidence, the last decision repeated a cached search for
`def makedirs(`. No mutation, check, submission, or evaluator occurred. The row is
therefore evidence of an action-selection/commitment failure after sufficient public
source visibility, not task acceptance, safety evidence, or a hidden/public contract
mismatch.

The diagnostic stagnation flag was false for every action. Its current counter is
global-resetting: whenever any interleaved read discovers a new span, it clears every
fingerprint repetition count. Overlapping reads can also receive distinct span IDs.
That explains why the soft card missed this repeated exploration. It did not cause
the terminal or block mutation, because the flag has no execution-gate effect. This
single row does not justify a repeated-read hard terminal or removal of read tools;
the observability and action-selection seams should be characterized provider-free
before another live invocation.

## Post-seventh working-state checkpoint

The provider-free correction gives each read/search call a strict bounded public
`working_state`: `working_hypothesis` is limited to 800 characters, `evidence_gap` to
500, and `decision_after_result` to 800. The provider adapter separates that state
from executable path/query arguments. Durable action identity hashes both, while a
separate operational read hash keys evidence caching by tool, executable arguments,
and current diff. The result then receives the current call's state after cache lookup.
This prevents an earlier cached hypothesis from replacing a revised one.

Focused tests cover required/strict schemas, bounds, non-read rejection, cache reuse
across revised state, successful and failed result projection, process hydration, and
provider-decision resume without another provider call. Attempt cards prefer the
recorded `decision_after_result`; the existing stagnation value remains visible only
as a diagnostic result field. No tool was removed and no transition or terminal was
added. Invalid or over-length provider state becomes a bounded protocol error while
the completed response's token fields remain available for durable usage settlement.
Ruff and all 78 tests pass in 83.55 seconds.

Provider-free mock run `run_dev_6c167fa301ac40c3` under external root
`C:\pl-working-state-smoke-commit-20260903` reached `EVALUATOR_PASS` in four model
turns and five tool actions with one accepted mutation and zero cost. Its second
canonical context contained both first-turn working states; neither private-test
identity nor a reference-patch field appeared. Task acceptance was PASS, Docker
safety was NOT_RUN, and `claim_eligible=false`. This proves only local contract and
context continuity. It does not show that a provider model will follow the recorded
decision or improve live task completion.

The follow-up no-call preflight used the proposed eighth-row parameters without
dispatching them. `patchloop doctor` found Python, uv, Git, the Docker CLI, and the
Docker server available. The version-2 task validated at content hash
`sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87`;
the runtime and selected task paths matched HEAD; model pricing was registered; and
the required local image matched
`sha256:6de3b39018eec22728567f44dfbdc3cbd31322c384f6ee3d7f328ef38165d57c`.
The repository-root `.env` was both ignored and untracked, and its exact one-key
format validated without printing the credential. This is readiness evidence only,
not authorization or a live result.

## Eighth live development observation

One separately approved invocation used external state root `C:\patchloop-state`,
`pyfakefs-makedirs-parent-traversal` version 2,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and the $1.20 invocation cap. PatchLoop did not start Docker Desktop or pull/build an
image, and no retry followed.

Run `run_dev_07ad1af07d22489c` wrote a valid 500-event hash chain ending at durable
`LIMIT_REACHED` after 299.562 active seconds. All 40 provider calls and input counts
completed; durable provider costs sum exactly to the terminal's $0.34786650. Two
4096-output-token incomplete responses at turns 9 and 22 received the allowed
non-consecutive corrections and were followed by valid tool batches. They were not
the terminal cause.

All 60 tool actions succeeded: 30 `read_file` and 30 `search_files`. No mutation,
visible check, submission, evaluator, or safety execution occurred. Every canonical
context from turn 2 through turn 40 projected working state on every latest result.
Thirty-five of the 60 `decision_after_result` values explicitly used mutation,
editing, patching, or applying language, but each later tool selection remained a
read/search. The final context still reported `needs_mutation`, carried both latest
working states, and showed one model call remaining.

There were nine evidence-cache hits and 21 results with no new span, but no stagnation
signal. This preserves the earlier conclusion: projection and the model-authored
decision text are present, while the decision is non-binding and does not control the
next tool choice. The result does not justify a repeated-read hard terminal, a ninth
paid row, or any quality claim.

## Post-eighth action-coupling checkpoint

The provider-free correction retires per-read `working_state` from the active tool
contract. Every current tool call instead carries one typed public `turn_decision`.
Its mode must match the actual tool family. The initial version also required every
call in a parallel read batch to repeat the complete decision exactly. Attempt cards
became batch-level so one observation batch could not project several conflicting
future actions.

The OpenAI request remains `store=false`, but it is no longer represented solely as a
fresh system-plus-user snapshot. From the second turn onward, a bounded journal-derived
input sequence contains the immediately preceding structured function calls, their
matching exact public outputs, and the current derived state. Call IDs and ordering are
preserved. Raw reasoning, message content, private specs, hidden paths, evaluator
details, and reference patches are not persisted or replayed. Both the canonical
context and exact model-input sequence are content-addressed at the turn boundary.

At that checkpoint, tool exposure derived from workflow evidence and remaining
capacity. The runner
reserves the calls and tool actions needed for mutation, all checks on the resulting
diff, and finish; a current failed check correctly includes another mutation and full
check rerun in that horizon. The default inspection lease is 24 turns per unchanged
diff. After a failed mutation, at most three repair-specific inspection turns are
available before another mutation or explicit stop. Failed checks cannot be rerun on
the same diff. `stop_task` is always available. This is deterministic resource
allocation, not a semantic judgment that evidence is repetitive; the stagnation signal
remains diagnostic-only and creates no terminal. Its count is now retained per
fingerprint for the unchanged diff, so an unrelated newly discovered span or visible
check no longer erases evidence that an exact read was repeated.

This checkpoint is implementation and provider-free contract evidence only. It does
not show that a provider will change tool selection. At that checkpoint it did not
authorize a ninth row.
Read-only replay characterization found 23 inspection batches before the first mutation
in both the fifth and sixth rows. The sixth row used at most three repair reads between
failed mutations before its accepted mutation on turn 33 and completed finish on turn
38. The 24-turn general lease and three-turn repair lease therefore preserve both
observed successful trajectories. Applied to the eighth row's unchanged-diff counters,
the policy removes read/search after its 24th completed inspection batch; this is a
deterministic policy simulation, not another provider execution.

## Ninth live development observation

One separately approved invocation used external state root `C:\patchloop-state`,
`pyfakefs-makedirs-parent-traversal` version 2,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and the $1.20 invocation cap. No retry followed, and PatchLoop did not start Docker or
pull/build an image.

Run `run_dev_b79d22f70ae44854` ended at durable `PROTOCOL_VIOLATION` after 14.234
active seconds, three completed provider calls and input counts, one successful search,
no accepted mutation, and $0.0077223. No visible check, submission, evaluator, or safety
execution occurred.

The first search located `fake_os.makedirs`. The next request contained that exact
function call and public output with matching call ID, establishing that native result
continuation operated in the live request. The second response returned one
`read_file` and one `search_files`, both structurally valid and both in `inspect` mode.
Their call-specific `basis` and `evidence_goal` text differed, so the application's
cross-call equality validator rejected the complete batch. The correction appeared in
the next public attempt card. The third response again returned two valid inspect calls
with distinct concrete rationales, and the consecutive-correction limit closed the row.

This is a harness contract terminal, not evidence that the agent rejected mutation or
exhausted the inspection lease. Tool JSON Schemas constrain each call independently and
cannot express equality between arbitrary free-text fields in sibling calls. The local
tests had proved the application validator and used one reused decision object in mock
success paths; they did not establish that this relational constraint was a stable
provider interface.

## Post-ninth parallel-decision correction

That post-ninth contract required only the enforceable common property: every call in a
parallel read/search batch has `mode=inspect`. Each call may carry the distinct bounded
`basis` and `evidence_goal` appropriate to its query or range. The batch attempt card
stores every action's corresponding decision instead of projecting only the first.
The exact two-call shape from the ninth row is a provider-free regression case. Mixed
tool families, wrong decision modes, missing decisions, duplicate action IDs, and
oversized batches still fail closed. The native continuation, completion horizon,
24/3 inspection leases, and diagnostic-only stagnation policy are unchanged.
Ruff passes, the complete 79-test suite passes in 113.24 seconds using a short external
temp root, and mock run `run_dev_a7724af70efb4984` reaches isolated `EVALUATOR_PASS`
through one accepted mutation. Its task acceptance is PASS, safety is NOT_RUN,
`claim_eligible=false`, and provider cost is zero. No tenth-row authority follows.

## Tenth live development observation

One separately approved invocation used external state root `C:\patchloop-state`,
`pyfakefs-makedirs-parent-traversal` version 2,
`gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one repetition,
and the $1.20 invocation cap. No retry followed, and PatchLoop did not start Docker or
pull/build an image.

Run `run_dev_8efe75f7c8c14cbd` wrote a valid 363-event hash chain ending at durable
`INCOMPLETE_RESPONSE` after 271.046 active seconds. All 28 provider calls and input
counts completed, and durable provider costs sum exactly to the terminal's
$0.27773415. It completed 23 `read_file` and 34 `search_files` actions, then one
`parent-traversal-contract` check on the empty diff. That check failed as the public
contract requires; no mutation, submission, evaluator, or safety execution followed.

The first 24 unchanged-diff inspection turns completed normally. Starting with turn
25, the public tool surface contained only mutation, check, and stop actions, so the
completion horizon and 24-turn inspection lease operated as designed. Turn 25 returned
an incomplete reasoning-only response after using its full 4,096-token output ceiling.
The next turn issued the valid public check, whose completed batch reset the consecutive
correction allowance. Turns 27 and 28 again returned incomplete reasoning-only
responses using exactly 4,096 output and 4,096 reasoning tokens; the second consecutive
one produced the terminal.

The immutable event stream preserved response status, ceiling, token usage, item shape,
and the generic `incomplete_response` code, but omitted the adapter's parsed
`incomplete_details.reason`. Equal ceiling, output, and reasoning counts on all three
events make output-ceiling exhaustion the supported explanation, but it remains an
inference rather than an exact historical provider field. This row therefore validates
the action horizon and inspection lease while exposing a distinct output-budget and
provenance boundary.

## First post-tenth output-budget correction

The desired dev-head output ceiling is now 25,000 tokens. This is an internal,
previously exercised project setting, not an API recommendation. Per-dispatch cost
admission still lowers it when the remaining invocation-wide cap cannot reserve the
full amount, and refuses a call that cannot reserve the minimum. The configured ceiling
is included in model identity and the submission manifest; every actual admitted
ceiling remains in `provider_call_started`.

Future provider `incomplete_details.reason` metadata is retained in
`provider_call_finished` and `turn_decision_recorded`, copied by decision recovery,
named in the next bounded correction, and included in terminal provenance. At that
first correction, response text and reasoning remained unstored. Provider-free tests
cover full-ceiling admission, cap-driven reduction, typed adapter extraction, durable
propagation, terminal wording,
and recovery without another provider dispatch. Ruff passes, and all 83 tests pass in
about 85.5 seconds with a short external temp root. Mock run
`run_dev_5e032eaf91ec4177` reaches isolated `EVALUATOR_PASS` through one accepted
mutation with task acceptance PASS, safety NOT_RUN, `claim_eligible=false`, and zero
provider cost. No eleventh-row authority follows.

## Encrypted-continuation and completion-slack correction

The current provider-free successor keeps the 25,000-token ceiling while changing the
two mechanisms implicated by the tenth row. OpenAI requests remain stateless with
`store=false`, but now request `reasoning.encrypted_content`. The immediately preceding
encrypted reasoning items and their original ordering with function calls are stored
in the external content-addressed artifact store. Journal events retain only artifact
metadata and hashes. The next input replays that encrypted state, matching calls and
public results before the latest public context. This includes reasoning-only
incomplete responses and bounded public rejection results for function calls rejected
by the local protocol. Tests verify that plaintext reasoning and summaries do not enter
the continuation artifact or journal. Missing, corrupt, reordered, or action-mismatched
continuation evidence reaches `PROVIDER_CONTINUATION_ERROR` without another provider
or tool call.

The 24 unchanged-diff and three repair-read fields remain parseable and recoverable,
but are now telemetry only. Inspection is available while both remaining model calls
and tool actions exceed the minimum mutation/check/finish path. One remaining optional
turn is announced as `last_opportunity`; zero closes `read_file` and `search_files`.
A required first anchor read is part of the minimum path. Every close or reopen records
`tool_policy_transition`, and the next context projects it once. Corrections are built
from the actual allowed-tool set, so they cannot recommend a removed tool; a diagnostic
`run_check` is explicitly not presented as satisfying `needs_mutation`.

At this checkpoint the evidence was provider-free only. It did not yet show that the
live provider accepted the wire representation, that continuation improved model
behavior, or that the agent mutated, checked, and submitted. No provider call, Docker
startup, image pull/build, or eleventh live row occurred in that change.

Ruff and all 86 tests pass. The complete suite used a short external temp root and
finished in 111.40 seconds (112.09 seconds invocation wall time), below the two-minute
target. To keep that bound without dropping recovery evidence, terminal-resume reused
the terminal produced by the existing mock E2E test, and two redundant persistent Git
identity commands became one commit-local configuration. Provider-free mock run
`run_dev_e961ed4d987e43b1` reached isolated `EVALUATOR_PASS` in four model turns and
five tool actions through one accepted mutation. Task acceptance was PASS, safety was
NOT_RUN, `claim_eligible=false`, and provider cost was zero.

## Eleventh live development observation

The separately authorized eleventh row used `pyfakefs-makedirs-parent-traversal`
version 2, `gpt-5.4-mini-2026-03-17`, medium reasoning, repository-root `.env`, one
repetition, a $1.20 invocation cap, and external state root `C:\patchloop-state`.
Run `run_dev_36d200ed199d4377` wrote a durable `LIMIT_REACHED` terminal after
412.811 active seconds and 419 seconds of run age. It completed 40 provider calls and
input counts, 94 tool actions, one accepted mutation, and $0.449133 of provider cost.

Every provider response stored a continuation reference containing one encrypted
reasoning item. Read-only artifact comparison found zero semantic replay mismatches
across all 39 next-turn edges: reasoning IDs and ciphertext, function-call ordering,
and matching public function outputs were preserved. Neither the journal nor any
canonical public context contained `encrypted_content`. No response was incomplete.
Turns 37 and 38 completed with 12,128 and 7,469 output tokens, including 11,235 and
6,402 reasoning tokens, and both emitted one `apply_git_diff` call. This confirms live
wire acceptance and removes the tenth row's 4,096-token response boundary; it does not
by itself attribute better problem solving to continuation.

The run made 32 reads and 58 searches. Turn 36 projected `last_opportunity` with both
inspection tools still available. Turn 37 recorded a `completion_horizon` transition
from `inspection_open` to `execution_only` and exposed only mutation and stop. The
first mutation used an invalid bare `@@` separator, so `git apply --check --recount`
rejected it at patch line 8. The next context retained the exact failed diff, hypothesis,
anchor, and error; turn 38 emitted a complete replacement diff, changing only
`pyfakefs/fake_os.py`. `parent-traversal-contract` and
`upstream-fake-os-regression` both passed on diff
`sha256:cd233801193f75f169f7e0ce5bc24c5ada2cb81f8c821499a67eb7a15a36d4a3`.
Calls 39 and 40 ran those checks, leaving no call for `finish_task`. Nothing was
submitted and no evaluator or safety check ran.

## Post-eleventh repair-reserve correction

The live trace showed that completion slack protected only the best-case four-call
mutation/check/check/finish path. One rejected first mutation consumed the finish call.
It also showed that `completion_possible` meant only that mutation capacity remained;
it stayed true even when three model calls remained for a four-call minimum path.

The provider-free successor keeps the 40-model/100-tool limits. It adds one explicit
first-mutation repair call to the completion budget and consumes that reserve after a
mutation failure. The best-case minimum remains separately visible, while
`completion_possible` now also requires both remaining budgets to cover it. The
scheduler regression reconstructs the live shape at calls 35–40: final inspection,
failed mutation, repaired mutation, two checks, and finish. Invalid bare `@@` syntax
remains fail-closed rather than being guessed or normalized.

Ruff and all 87 tests pass. The complete suite used a short external temp root and
finished in 88.79 seconds. Provider-free mock run `run_dev_22a91101f0224925` reached
isolated `EVALUATOR_PASS` in four model turns and five tool actions through one accepted
mutation. Task acceptance was PASS, safety was NOT_RUN, `claim_eligible=false`, and
provider cost was zero. This validates the local contract, not another live row.

## Not executed

- no transport retry or follow-up paid run after the eleventh row
- no image pull, image build, or automatic Docker Desktop start
- no contract-valid paid/live task acceptance, claim, qualification, activation,
  adoption, or held-out evaluation; the version-3 PASS is provider-free only
- no mutation, submission, or evaluator execution in the seventh through tenth
  pyfakefs version-2 live rows; the eleventh mutated and passed both visible checks but
  did not submit or invoke the evaluator
- no hidden evaluation of the temporary Loguru version-2 public correction

The under-two-minute focused-validation target remains locally supported. The sixth
row reached a durable evaluator summary within 30 minutes, verifying the operational
path but exposing an invalid acceptance oracle rather than producing task acceptance.

## Known limitations

- The price registry accepts only reviewed model IDs; unknown models fail closed.
- Input counting and generation are separate provider operations. Timeout after
  either boundary can make billing uncertain, so the invocation stops.
- Digest and requested sandbox policy are content-bound, but they are not host-level
  attestation.
- Mock fixtures do not prove remote checkout, provider schema acceptance, model
  behavior, or production billing.
- Local/mock evaluation intentionally reports Docker safety as NOT_RUN. The
  provider-free retrospective and sixth paid live row executed the pinned Docker
  policy path and reported safety PASS.
- Long-horizon memory is disabled; only bounded current-run public evidence is projected.
- Deleted historical executables require Git history to replay.
- Only runs with the new immutable envelope can resume; older journals remain
  read-only evidence.
- The third through sixth live rows show that the provider can emit the
  `apply_git_diff` raw-diff shape, and the fourth and sixth show failed-mutation
  continuation through later attempts. The sixth establishes live submission and
  evaluator handoff, but version 2's stricter private literal assertion prevents a
  contract-valid live task-acceptance conclusion. Version 3 corrects that oracle and
  passes provider-free evaluation only. The seventh and eighth rows exercised only
  read/search and therefore add no mutation, check, submission, evaluator, or safety
  evidence. The eighth additionally proves live working-state projection, not
  compliance with the projected decision. The ninth proves native continuation for one
  completed search, then exposes a cross-call free-text equality mismatch before the
  action horizon or inspection lease is exercised. The tenth proves that horizon and
  lease operate live, then ends on three reasoning-only responses at the old 4,096-token
  ceiling. Its exact incomplete reason was not durably recorded and is inferred from
  the preserved status and token counts.

A development PASS does not establish comparative quality, generalization,
causality, or memory benefit. A future confirmatory lane needs separate frozen
contracts and authority.

## Historical audit

Checkpoint `b71ddeee` preserves the secret-scanned pre-reset tree. Historical
results remain under `reports/` and `experiments/`; historical narrative remains
under `docs/archive/`. Verify their tracked bytes with:

```powershell
git diff --name-only b71ddeee -- reports experiments docs/archive
```

Expected output is empty.
