# Verification selection, source retention and completion reservations

The user requested diagnosis of all three mechanisms after the
[SQLFluff-1733 patch comparison](2026-10-06-sqlfluff-1733-patch-comparison.md).
The question is why the agent could submit an untested repair, lose previously
read calculation code, and temporarily lose inspection tools. These mechanisms
matter at different decisions; they must not be collapsed into one causal claim.

This investigation used saved public inputs/actions from rows 06 and 08, current
source, deterministic offline replays and existing local tests. No new provider,
probe or evaluator was called. Original traces, patches and closed records were
preserved. Analysis HEAD was `11290043bdc3dad6e7d3a07b2c7d45bbb5e92fde`, runtime
`sha256:52bd5ca036bc876556b29e6f949fbfc67b7222445b3228015d0bb54b806a3c0e`.
The relevant runner, prompt, selector, conversation and segment code is unchanged
from the original `29ff6e4f86895a89df2301f0294c6d99dae125de` run. Later interface
fixes are separate from those live results. Every result is `official=false` and
claim-ineligible. No runtime code or selected policy changed here.

## 1. Verification selection and unsupported claims

Observed failure: neither row ran the reproduction after its edit. Both passed
the broad registered regression check, containing 506 tests. The earlier public
operator comparison established that row 08 still emitted the wrong nine-space
indent, while row 06 emitted the expected eight spaces.

The exact final model inputs retained historical probe results and open questions.
Row 06 explicitly asked whether the adjusted under-indent branch now produced
the expected CTE indentation without disturbing plain SELECT. Row 08 retained
the unresolved question about which L003 branch produced the moved indentation.
Both had read/probe/test tools available, with 16 and six model calls remaining,
respectively. Required-check PASS did not erase their notes or questions.

All eight original probe programs contained no Python `assert` statements and
printed behavior rather than asserting the expected formatting. Setup checks
were separate. Thus row 06's three bug-showing, exit-zero executions created no
entry in the unsuccessful-execution observation catalog. Row 08's catalog held
the unsupported-API TypeError. The useful formatting outputs still appeared in
`recent_probes`; absence from that catalog did not mean source evidence vanished
or the behavior passed.

The alternative that runtime labels falsely certified the probes is contradicted:
the actual public projection removed raw `status=passed` and exposed
`execution_status=completed`, `behavior_verdict=not_assessed`, diagnostic scope
and baseline diff identities. Row 06's statement that a probe confirmed its
current repair came from the model-authored finish decision/note. The citation
was to the pre-edit baseline. Current note projection keeps it historical and
unverified, and typed concern resolution rejects that baseline evidence.

`runner._completion_guidance` uses required-check readiness and available tools,
not the content of open questions or behavioral coverage. Paired deterministic
checks with and without unresolved notes/probe evidence produced identical
`next_action=finish_task` guidance. The message also says untested behavior is not
proved and offers a probe for uncertainty that could change the edit. This is a
real design tension between submission eligibility and behavioral verification,
not a discovered provenance or status-label contract violation.

The [earlier advice-removal comparison](2026-09-26-completion-status-comparison.md)
had no acceptance gain on its two seeded tasks. It does not settle this case,
but prevents treating another wording-only change as an established solution.
The concrete behavioral target is a discriminating expected-versus-actual check
on the edited candidate, followed by repair when it fails. Existing tools can
express it. Neither an additional warning nor a mandatory gate is justified by
this diagnosis alone.

Source: `patchloop/dev/probe_observation.py`, `verification_observations.py`,
`tools.py`, `working_notes.py`, and `runner.py:555-620`.

## 2. Source omission at the repair decision

Both agents had read all 799 original L003 lines without read-result truncation.
Six exact saved snapshots were reconstructed with the current source selector:
row 06 sequence 336 and row 08 sequences 393, 409, 449, 462 and 491. Selected
source spans and delivered-source hashes matched in every case.

At row 08 sequence 409, the retained-source budget was 23,993 of 24,000 characters.
Three newer observations occupied 20,825 characters: L036 code 1-337 (13,967), its
fixture 1-214 (3,861), and a parser helper 680-760 (2,997). Most L003 calculation
code was older and lost the priority/recency competition. The retained L003
body was only lines 401-405 plus its first line. No arithmetic range was protected
by a source citation in the model's notes.

The calculation still reached request 393 through old public function-output
history. The `major_result_reviewed` handoff at 408 removed that history, so it
disappeared from request 409. This was normal bounded selection and handoff,
not deletion of the underlying journal, stale-hash reuse, or unseen source
fabrication. Selection merges overlapping lines and subtracts overlap with the
latest native tool results; those mechanisms did not explain the lost calculation.

The final read before closure requested 330-430. It included the call to
`_process_current_line` at 424 and only that function's signature at 430; its
body starts at 431 and the relevant arithmetic is at 706. A 430-799 read would
fit the 400-line tool limit. Four parallel reads were also still available on
that last inspection turn. The chosen read therefore missed the actual fix
construction after an explicit last-opportunity warning.

Two offline alternatives clarify the tradeoff without claiming agent improvement:

- Protecting the already-read L003 401-799 range retained line 706 at both 409 and
  462 within the same 24,000-character retained-source budget, with latest native
  deliveries held fixed. At 409 it displaced most L036 code and
  the parser helper; at 462 it displaced L036 code, its fixture and some L003
  helpers. This is a retrospective range choice, not a general selection rule.
- Applying recency to entire files retained only L003 1-674 at 08/462 and 1-585
  at successful 06/336: both lost line 706. A simple file-priority change is not
  sufficient. Delaying handoff would preserve extra history, but is not a fixed
  retained-budget alternative: public source bodies were 42,859 unique characters
  before handoff and 24,124 afterward, including native and quoted deliveries.

The demonstrated issue is loss of a relevant earlier observation under a
semantic-agnostic retention policy. Its effect on patch choice remains uncertain:
the agent had earlier access, chose an insufficient last read, and regained the
calculation after the public check. No general larger-context or pin-everything
change follows from this pair.

Source: `patchloop/dev/context.py`, `native_sources.py`, `conversation.py`,
`segments.py`, and `model_state.py`.

## 3. Reservation arithmetic and a resource mismatch

Five saved states passed 40 exact replay assertions; two independent path
assertions checked the reservation arithmetic. Under the current common-call
forecast, eight is internally consistent:

| Component | Reserved calls |
| --- | ---: |
| Accepted edit, one required check, finish | 3 |
| Extra rejected attempt and anchor read; accepted retry counted above | 2 |
| One future required-check failure: inspect, repair, recheck | 3 |
| Total protected path | 8 |

At nine remaining model calls, one inspection fits while preserving eight. At
eight, it does not. After the required check passes, the remaining baseline path
is just finish, so six remaining calls expose five optional inspection turns.
Time, dollar and tool-action slack do not override the model-call cap. Neither
run had protocol corrections, provider errors, duplicate action replay or model
compaction calls; the displayed correction allowance of one was not consumed use.

There is nevertheless a concrete conservative mismatch to enabled execution.
Both runs had `repair_recheck=true`. After an accepted repair of a healthy,
current failed registered check, the runner executes the recheck before the next
inference. That child consumes one tool action and zero model calls. The forecast
has no automatic-recheck input and uses one protected count for both resources.

An independent bounded path has seven model calls and eight tool actions:
rejected edit, inspection, accepted edit, required-check failure, inspection,
accepted repair, automatic recheck, finish. Only the automatic recheck is zero
model calls. Existing tests verify its counter behavior, exact recovery identity,
selection boundaries, action capacity and deadline handling. Automatic recheck
disabled still requires eight/eight under the same assumptions.

Consequently, a resource-specific forecast could preserve this same bounded
recovery path with a seven-model/eight-tool reservation. At 08/462, call-count
admission would then have room for one further inspection. This is not a global
cap reduction or permission to consume reserved tool actions. Any correction
must remain consistent across successor states and unavailable/disabled automatic
recheck paths; subtracting one only at the initial gate is insufficient. Existing
deadline, cleanup, cost-admission and uncertainty boundaries still apply.

The precise original intent of the conservative common forecast is not established.
This is a verified resource-accounting mismatch, not an off-by-one or proof that
one more read would produce the correct patch. It also does not explain skipping
the later reopened verification opportunity.

Source: `patchloop/dev/completion_budget.py:37-73`, `runner.py:779-867`,
`runner.py:3288-3341`, `runner.py:4249`, and `repair_recheck.py:37-88`.

## Decision and validation

The observed sequence combines source loss, an insufficient last read, a
conservative inspection floor, a wrong edit and a later choice to submit without
testing its effect. Temporal order alone does not establish each causal arrow.
Verification selection/interpretation is the clearest behavioral failure; the
automatic-recheck resource mismatch is the narrowest concrete code correction
candidate. Source selection requires a principled way to retain relevant earlier
evidence; the tested file-recency shortcut did not work.

Keep the current runtime baseline for this diagnostic. No paid continuation,
new prompt comparison, automatic probe replay or mandatory verification workflow
was launched. A future accounting correction can be tested locally; its effect
on actual repair success would remain a separate empirical question.

- Verification: 125 evidence/contract checks; 35 focused tests passed in 25.86s.
- Reservation: 42 replay/path assertions; 73 focused tests passed in 21.89s plus
  two additional existing boundary tests in 18.59s.
- Context: six exact selector/delivery replays and same-budget alternatives;
  17 focused tests passed in 8.390s wall time.
- Root closeout verified 127 distinct focused test nodes plus five documentation
  tests, the corrected evidence linkage, four journal chains and unchanged runtime.
- One initial external verification fixture lacked a lifecycle accessor; the
  error was preserved and the corrected operator/results were versioned. Context
  v2 corrected quoted-source volume accounting; selector results were unchanged.
- Final audit caught an external verification-operator hash-linkage error: its
  saved evidence held 122 checks, but a shared list later gained three closeout
  checks before the result hash was computed. The original journal correctly
  bound the saved file. A separate provenance follow-up reconstructs the mismatch,
  binds the unchanged file, and records those three checks separately. Originals
  were preserved; no test or live call was repeated. This was not a runtime defect.
- No production source changed; full suite and Docker smoke were not rerun.

External immutable evidence root:
`C:/pt/analyses/1733-three-mechanisms-20261006-v1`.

- `closeout.json` binds the final records and test reports, including the separate
  verification provenance correction.
- `verification/findings.md`, `verification/attempt2/{packet,evidence,result}.json`,
  focused logs/XML and `runs/run_dev_1733verificationdiagnostic.jsonl`.
- `verification/provenance-followup-v1/{correction,result-provenance-corrected}.json`
  corrects the original verification result's evidence-hash linkage.
- `context/evidence-v2.json`, `focused-tests.json`, `focused-tests.xml`, and
  `runs/run_dev_1733contextmechanism.jsonl`.
- `reservation/{result,validation}.json`, `analysis.md`, focused and boundary
  logs/XML, and `runs/run_dev_1733reservation.jsonl`.

The machine records bind exact historical inputs, source versions, commands and
hashes. Public outputs and failed operator attempts are retained separately;
none of these offline results is a fresh solve or acceptance-rate measurement.
