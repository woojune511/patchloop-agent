# Clean-start observation-opportunity follow-up: preparation

## Material Passport

- Date: 2026-10-28. ARS experiment-agent, code experiment preparation.
- Status: PREPARED_NOT_EXECUTED; new exact execution/cap confirmation pending.
- Runtime implementation: `113efa3c4ce1d51dcb6ed79ec64900b8525fa104`.
- official=false, claim_eligible=false; one development task, not a causal estimate.

## Question and reason

The [implementation](2026-10-28-observation-opportunity.md) passed short offline
checks and restored observation choices under the saved failure state's budget.
That does not show whether a live model selects the option, learns anything useful
from it, revises its hypothesis or completes a correct repair.

Run the same clean-source Astroid-1333 task once with the same full model and
resource limits as the [closed baseline](2026-10-28-autonomous-fresh-results.md).
The intervention combines ruleless original-call selection, consistent minimum
observation/read admission and typed pre-target construction evidence. No separate
component effect or generalization claim can be inferred from this one follow-up.

Starting clean is intentional. A saved checkpoint would inherit old v9 UNKNOWN
receipts and a trajectory produced while observation was unavailable. It would
not exercise fresh v10 classification or autonomous initial exploration. Do not
inject the former patch, operator diagnosis or known successful repair.

## Fixed invocation

- Task: Astroid-1333, `tasks/dev-train/current-dev20/13/public.yaml`.
- Model: `gpt-5.4-2026-03-05`, xhigh; repeat1.
- Credential file: `C:/Users/geonj/Documents/PatchLoop/.env`.
- Proposed new invocation-wide cap: **USD4.50**. Previous allocations stay CLOSED.
- Twenty responses including at most one protocol correction,40 tool actions,
  three accepted edits, input60K, output40K/correction25K.
- Total2400 seconds including390 reserved for isolated evaluation; solver starts
  with2010 seconds. Existing per-operation deadlines remain in force.
- Thin policy, segmented context, protected inspection, bounded original
  acquisition, repair recheck and completion-recovery admission stay selected.
- Same verified original source, pinned public dependencies and explicit read-only
  `dependency:pylint` source access. Cross-run history and supplemental operator
  counterexamples are absent.

The serialized request equals the baseline request except for the new result root.
The intended difference is the runtime implementation. Registered pricing reserves
USD0.75 for60K uncached input/40K output and USD0.525 for60K/25K. Twenty responses are
a count ceiling, not a promise that all can reach maximum output within USD4.50.
Normal count-before-dispatch admission can lower output or stop.

## Measurements and decision rules

Record actual dispatched tool schemas and resource reasons after reproduction.
An option not offered is not counted as model avoidance. When the option is offered,
record caller/test inspection versus observation selection, selected call identity,
public repair hypothesis, trace completeness and identity, and linkage to an edit.
Record protected-reserve release separately from billed use and terminal exhaustion.

For fresh helper settings failures, distinguish typed rejection with zero captured
target entries from uncertain execution and from actual acquired original failure.
If no such failure occurs, classification uptake is NOT_EXERCISED; do not cause an
error or repeat a run just to obtain that trajectory.

Keep separate outcomes for baseline F0010 reproduction, candidate original replay,
error absence and positive processing of the intended fixture, current-diff public
regression, natural failed-repair feedback/revision, normal finish, delivered patch,
isolated task acceptance and safety, cost and elapsed time. Review whether the
model's processing predicate identifies the actual file; a name in an error message
is not automatically processing evidence. This operator assessment is not an extra
solver hint or a changed benchmark oracle.

Success requires the original and public checks on the submitted candidate plus
normal delivery and separate isolated acceptance/safety PASS. Observation uptake
alone is not success. If repair succeeds without a failed edit, revision uptake is
NOT_EXERCISED. If it fails, localize the first unsupported transition instead of
prescribing a larger cap merely because some resource remained unused.

## Preparation and boundaries

The ordinary runner constructed its first request with a synthetic count/stop
adapter while network, credentials and target execution were blocked. Counted and
dispatched input/tool payloads agree. Diff is empty, only base-regression is
registered at NOT_RUN, previous source/results are absent, and read/search offer
the public pylint scope. This is structural validation; real provider token fit
remains NOT_MEASURED until an authorized counted request.

Read-only preflight passed in10.723 seconds: manifest/runtime/task identities,
tracked source cleanliness, prepared source and dependencies/caller binding, local
pinned image identities and credential-file existence. It performed zero provider,
real token-count, credential-file-read or target calls. Docker was not started;
no image was pulled or built. Prior focused79/quick792/Ruff evidence is bound by
artifact hashes; runtime was unchanged during this preparation.

A shared-context independent read-only audit verified all14 bound files, unchanged
request conditions except result root, clean initial model state and the one-shot
approval boundary. `independent-audit.json` has hash
`sha256:6dd9b540a51b3cc7a322ac6883b3b5d153793aedd567b559498510c1f279e581`.
All five documentation checks passed; runtime tests were not repeated unchanged.

The command revalidates bound bytes and requires an exact approval receipt before
dispatch. Fresh result-root and journal locking permit one invocation only. Zero
SDK retries and stop-all on count/transport/billing/execution/cleanup uncertainty
remain unchanged. Do not restart a started trial or silently reuse unused funds.
No private evaluation content, reference patch or operator counterexamples enter
model context. The usual isolated evaluation remains outside the agent's context.

## Prepared command and artifacts

Command: `& 'C:/pt/observation-opportunity-fresh-plan-v1/run.ps1'`.

- Plan root: `C:/pt/observation-opportunity-fresh-plan-v1`.
- New result root: `C:/pt/observation-opportunity-fresh-run-v1` (not created).
- Approval manifest hash:
  `sha256:02215df8317e669b40e1e973cbe12fa73c73d25df7e161804487b4130b74c21f`.
- Runtime hash:
  `sha256:9e7db80fdb6a33082ecf7103c65ec4c117e17c3de3da3e22d62c8cb847093b9b`.
- `manifest.json`, `request.json`, `execute.py`, `run.ps1`, `monitor.py`,
  `collect-result.py`, `first-request.json`, `first-request-audit.json`,
  `preflight.json` and the hash-chained preparation journal retain the evidence.

Execution is pending the user's new one-run/cap confirmation. The standalone
preparation does not renew historical execution approval.
