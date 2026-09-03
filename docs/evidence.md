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

The first matrix harness attempt also exposed a separate, reproducible import edge:
a fresh interpreter importing `patchloop.verifier.policy` first enters a circular
import through the eager `patchloop.verifier` and `patchloop.dev` package exports.
Importing through the production runner order succeeds, and the production evaluator
run above is unaffected. This is a local module-import contract defect to fix
separately, not task-acceptance evidence.

## Not executed

- no seventh repetition, transport retry, or follow-up paid run after the sixth row
- no image pull, image build, or automatic Docker Desktop start
- no contract-valid paid/live task acceptance, claim, qualification, activation,
  adoption, or held-out evaluation; the version-3 PASS is provider-free only
- no hidden evaluation of the temporary version-2 validation candidate

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
- Standalone `patchloop.verifier.policy` import currently depends on import order
  because the `patchloop.dev` and `patchloop.verifier` packages eagerly re-export
  runtime objects; the production runner path is covered and passes.
- The third through sixth live rows show that the provider can emit the
  `apply_git_diff` raw-diff shape, and the fourth and sixth show failed-mutation
  continuation through later attempts. The sixth establishes live submission and
  evaluator handoff, but version 2's stricter private literal assertion prevents a
  contract-valid live task-acceptance conclusion. Version 3 corrects that oracle and
  passes provider-free evaluation only.

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
