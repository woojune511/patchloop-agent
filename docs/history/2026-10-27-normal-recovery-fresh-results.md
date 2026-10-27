# Clean-start result: first repair reached, diagnostic predicates disagree

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved live execution and public-evidence analysis
- Origin Date: 2026-10-27
- Verification Status: LIVE_EXECUTED; terminal VERIFICATION_INCOMPLETE
- Runtime implementation: `dc3c2b2c`; plan docs: `e6c21f9f`
- Official: false; claim-ineligible; allocation closed

## Question and decision

The [sealed pilot](2026-10-27-normal-recovery-fresh-plan.md) tested whether the normal
runner can acquire, repair, verify and finish from clean Astroid-1333 source after
the saved-evidence diagnostic succeeded. One exact USD 4.50 invocation was approved
and executed. No old patch, source excerpt, helper result or history was injected.

The model reached original-call observation and its first accepted repair, but
normal completion failed before public regression or isolated evaluation. The
decisive problem was two different diagnostic predicates: helper code recognized
F0010 even after its wording changed, while the host rule recognized only the old
message text. The resulting conflict could not enter the baseline-only correction
path. This stopped the loop before another response received the failed repair.

Do not increase token or money limits on this evidence. The next useful local
change is one consistent executable diagnostic definition, separating a baseline
failure signature from the desired behavior. Preserve F0010 detection when wording
changes, and verify that a current-diff failure reaches a subsequent repair response.
Do not simply discard the conflict or treat absence of an old phrase as success.

## Observed sequence

Journal `run_dev_79754e0769044891`, external result root
`C:/pt/normal-recovery-fresh-run-v1`:

1. First original probe, action request seq48/result51: both Pylint calls returned.
   The bug call captured F0010 / `Unable to load file`; the control lacked F0010.
   Helper code expected capture status `captured` or `completed`, but actual status
   was `complete`. Its authored observation was therefore null/null. Host judgment
   was true/false and correctly detected an initial observation conflict.
2. Corrected probe, request64/result67: the model removed the incorrect status
   guard. It calculated the booleans from captured stdout/stderr using
   `"Unable to load file" in text or "F0010" in text`. The host rules still used
   only `contains="Unable to load file"`. On unchanged base, both produced
   true/false and the correction was accepted. No observation was hardcoded.
3. `observe_original`, result84, reran the frozen call before repair and linked
   that observation to the edit. Additional source reads/searches followed.
4. First edit, request157/result158, changed `astroid/manager.py`:
   on `NoSourceFile`, a missing `__init__.py` now sets `source=False` instead of
   doing nothing. Its public hypothesis was to use module resolution instead of
   opening the synthesized missing initializer.
5. Host replay, result165, still captured F0010. The message changed to
   `Failed to import module project` / `No module named project`. Both calls
   returned and capture was complete. This disproves resolution of the observed
   failure; it does not establish any regression behavior.
6. The helper's broader predicate correctly stayed true/false. The host's narrower
   rule calculated false/false, declared `observation_conflict`, and left repair
   comparison unassessed. Correction status became failed with
   `target_not_baseline_conflict`, because this was a candidate replay. Terminal
   seq167 occurred before the next model request.

Thus neither a constant helper observation nor output exhaustion explains this
run. The initial API-status mismatch was fixed, but baseline agreement did not
establish equivalent predicates after a repair changes the diagnostic wording.
The stop prevented false success; its failure mode was withholding useful failure
feedback despite a still-visible F0010 and sufficient remaining resources.

## Resources and verification boundaries

| Measure | Observed |
| --- | --- |
| Model responses / input counts | 10 / 10 |
| Tool actions / accepted edits | 15 / 1 |
| Protocol corrections / observation corrections | 0 / 1 |
| Source search / read | 7 / 3 |
| run_probe / observe_original | 3 / 1; includes one host replay |
| Max actual input / output tokens | 49,059 / 21,068 |
| Context segments | 4; no over-60K input count |
| Cost / invocation cap | USD 0.40596195 / 4.50 |
| Active elapsed | 457,987ms, approximately 7m38s |
| Remaining model / tool slots | 10 / 25 |
| Remaining solver time | about 1,552 seconds |
| Public registered checks / finish / isolated evaluation | 0 / 0 / 0 |

The terminal has no blocking resource. All ten dispatched model calls have settled
usage, all input counts returned, and all fifteen actions have completed receipts.
No retry, operator patch, later target execution or synthetic submission occurred.
The local 500-test mechanism validation remains valid, but does not prove this
live predicate interaction was covered.

The policy's 1,470-to-830-second reserve reduction followed action availability:
the earlier broad request offered paired selected tests as well as a later repair;
the final request offered edit/stop. The paired tests account for 610 seconds and
one response accounts for 30. This is not the terminal cause. The new reservations
were exercised, but repair gain and end-to-end completion remain unproven.

An initial progress message incorrectly described F0010 as disappearing after
reading the host booleans. Direct captured-output inspection corrected that claim
immediately: only the old phrase disappeared. Raw public captures, not derived
booleans alone, support the interpretation above.

## Evidence and follow-up

- Approval manifest:
  `sha256:be198c8809a84191b558292147743c90ca036d09515b61de6bac86b1a8493d92`.
- `collection.json`:
  `sha256:e2b9018d1307484a1774fc6ef3ea9929b02d355856e8704e3aa53119c2655ce3`.
- Terminal event:
  `sha256:6ff5bdebd63c56a1645bbb3926c8227e8c8536ccc744411c56b6331a53aa4291`.
- `analysis.json` preserves bounded public captures and scalar outcomes.
- Plan journal `run_dev_normalfreshpreparation` records approval, execution return
  and allocation closure; no authorized repetitions remain.

A focused local fixture should cover baseline F0010 wording A, failed candidate
F0010 wording B, and genuinely resolved output. One registered predicate must
produce failure/failure/success across those cases. Verify API capture status
handling and next-response delivery of the candidate failure without renewing
correction or repair budgets. Only after that should a separately authorized
saved-candidate continuation or fresh trial assess live revision. No additional
paid run is authorized by this record.
