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

## Not executed

- no fourth repetition, transport retry, or follow-up paid run after the third row
- no image pull, image build, or automatic Docker Desktop start
- no accepted mutation, visible check, submission, private evaluator, or evaluator
  container in any live row
- no claim, qualification, activation, adoption, or held-out evaluation

The under-two-minute validation target is locally supported. A durable live terminal
was observed within 30 minutes, but the full operational target remains unverified
because no evaluator summary was reached.

## Known limitations

- The price registry accepts only reviewed model IDs; unknown models fail closed.
- Input counting and generation are separate provider operations. Timeout after
  either boundary can make billing uncertain, so the invocation stops.
- Digest and requested sandbox policy are content-bound, but they are not host-level
  attestation.
- Mock fixtures do not prove remote checkout, provider schema acceptance, model
  behavior, or production billing.
- Local/mock evaluation intentionally reports Docker safety as NOT_RUN. The typed
  Docker safety path is locally simulated but has not been live-executed here.
- Long-horizon memory is disabled; only bounded current-run public evidence is projected.
- Deleted historical executables require Git history to replay.
- Only runs with the new immutable envelope can resume; older journals remain
  read-only evidence.
- One live row shows that the provider can emit the `apply_git_diff` raw-diff shape,
  but its single malformed patch does not establish reliable mutation or submission.

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
