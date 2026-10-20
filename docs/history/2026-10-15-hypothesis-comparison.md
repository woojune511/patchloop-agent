# SQLFluff and Pydicom hypothesis decisions

Date: 2026-10-15. Offline investigation of two completed public traces.
Decision: **KEEP_RUNTIME_BASELINE**. No runtime change, new model call, task
execution or private evaluation was performed for this investigation.

SQLFluff changed its implementation in response to a real regression, but did not
establish that the replacement explanation still solved the original task.
Pydicom followed the value from its failing consumer to the code that produced
the wrong type before editing. Both then treated registered regression PASS as
sufficient to finish; Pydicom's successful acceptance does not validate that
verification practice. The comparison narrows the decision failure, not the
causal benefit of a model, planning policy, memory feature or tool restriction.

## Question, selection and evidence boundary

These runs were selected to distinguish missing evidence, failure to use available
evidence, and resource/tool constraints. SQLFluff is informative because its own
full-behavior test passed on an intermediate patch and failed on the submitted
patch. Pydicom is informative because its public plans record an upstream change
of explanation. This is a purposive contrast, not a controlled success-rate A/B.

| Condition | SQLFluff-1733 | Pydicom-1413 |
| --- | --- | --- |
| Saved run | `run_dev_c6cdf266d5a34ded` | `run_dev_a7dea36034bb4e9b` |
| Evidence root | `C:/pt/thlive01/08-task18-B-rep1` | `C:/pt/cd20live06c/8` |
| Selection | Thin comparison row 8, task 18, repetition 1 | Corrected dev20 task 8 |
| Model | `gpt-5.4-2026-03-05`, xhigh | `gpt-5.4-mini-2026-03-17`, xhigh |
| Agent / planning | thin / none | current / brief-v1 |
| Harness commit | `6da629ee57acbbcc46d533333af8549fc2b5aee9` | `e3aa70804005f110c9f6ed32b0ba792958a56aa3` |
| Invocation cap / settled USD | 4.00 / 1.764421 | 1.20 / 0.2085237 |
| Model calls / accepted edits | 28 / 4 | 12 / 1 |
| Registered regression / original evaluation | 506 PASS / FAIL | 212 PASS / PASS |

Both used segmented-v1, result-or-size segment boundaries, repair-recheck, and
probe policy none; probes were available. Limits were 40 model calls, 100 actions,
four accepted edits and 1,800 seconds including a 330-second evaluation reserve.
Task, model, policy, runtime and cost differ. Neither the outcome nor the cost
difference identifies a feature effect or supports general performance claims.

The audit verified both original journal chains and all 40 dispatched model
inputs against content-addressed bytes, canonical input hashes, prepared requests,
counted/dispatch request hashes and exact offered tool names. It resolved public
source from both native/quoted results and the current-source catalog; a compact
catalog alone can omit code still present in native results. No ambiguous source
reference was found. Only public task/source/action/check information and public
model-authored plans, hypotheses and decisions were interpreted. Encrypted
reasoning and private evaluator contents were not inspected. Delivery establishes
availability, not model attention, comprehension or an internal motive.

## SQLFluff: a changed patch with an untested replacement premise

The public task requests correct indentation under the default configuration.
At input 250, before the first edit, all three baseline probe records remained
visible. The default `sqlfluff.fix(sql)` produced nine leading spaces instead of
eight. Running only L036, then L003, produced eight. The other probe failed on an
incorrect `.paths` attribute access; that exception is an experiment error, not
evidence against a repair. The useful contrast leaves the complete rule
interaction unexplained: correctness of the restricted sequence does not explain
the default pipeline's different output.

| Input -> decision sequence | Available evidence and observed next action |
| --- | --- |
| 250 -> 253 | Baseline default output differs from restricted L036-then-L003 output. Edit L036 to copy indentation from an existing target. |
| 262 -> 265; 275 -> 278 | Add a test asserting the full default `sqlfluff.fix(sql)` result, then run its file: 4 PASS at result 281. |
| 288 -> 291; 301 -> 305 | Registered regression returns 1 FAIL / 505 PASS at 294. Search the generated failing ID literally; it returns no source. |
| 315 -> 318 | Repeat the same generated-ID search; the empty result is cached. Subsequent reads investigate L003. |
| 351 -> 354 | Change L003's indentation helper to remove additional whitespace segments. Automatic required-check recheck still returns 1 FAIL / 505 PASS at 362. |
| 367 -> 370 | Revert the L036 indentation-copy change, assuming the L003 helper now preserves the CTE behavior. Automatic required-check recheck returns 506 PASS at 378. |
| 384 -> 388 | Finish without rerunning the added test or full default example on the submitted diff. |

The final edit's public explanation makes the unsupported step explicit:

> With L003 now normalizing multi-segment indents exactly, L036 can go back to only inserting a newline and let indentation be handled separately.

Its expected behavior says the CTE remains fixed because L003 can normalize
combined-fix indentation. The observed regression supports removing L036's
overcorrection; it does **not** establish that the remaining L003 change handles
the original default-pipeline case. Thus this is not simply refusal to revise a
hypothesis. The agent revised the patch and its explanation, but accepted the
second half of that explanation without a corresponding observation.

At input 367, the actual request contains the current L003 file, including its
helper and separate indentation-creation paths, L036, and the added 62-line test
file. The old selected-test PASS is explicitly `evidence_currency=historical`.
The baseline probes are retained as historical observations too. At input 384 the
old test PASS is still historical, while only registered regression PASS is current.
This is not a stale PASS incorrectly promoted by the runtime.

There is an investigation gap as well: no L039 source occurs in any of the 28
delivered source views. The agent never acquired that additional rule's behavior;
this is different from pruning a previously read L039 body. Its failed literal-ID
searches also missed the underlying fixture key without the `L036_` prefix.
These observations identify narrow exploration choices, not a broken search tool
or evidence that unrestricted shell access was needed.

The existing [final-test diagnostic](2026-10-07-thin-followup.md) binds the submitted
diff to failure of the agent's own added assertion: five spaces instead of eight.
That failure was discovered after the solve and was **not delivered to this
solver**. The registered directory check did not collect that existing file under
the repository's `*_test.py` collection pattern; the agent had selected it explicitly
for its earlier run. Do not describe this trace as ignoring a delivered final-patch
failure. The [seeded counterexample run](2026-10-07-counterexample-results.md) is
different evidence and is not substituted for this run.

The [intermediate diagnostic](2026-10-07-intermediate-test.md) also matters: the
selected file still passes after edit three. Automatically rerunning it there
would not yet reveal the final defect. The failure appears after the fourth edit.
At input 367, one edit, 14 model calls, 57 actions and 704 solver seconds remained;
at input 384, no edits but 13 calls, 55 actions and 650 solver seconds remained.
Verification was available, while another repair was no longer allowed. Final
revalidation could expose the defect or avoid submission; these records do not
show that it would produce a successful repair. Raising the edit limit is likewise
an untested intervention, not a demonstrated remedy.

## Pydicom: follow the producer of the wrong value

The public issue reports that OL fails with a bytes-versus-MultiValue error while
OB and OF work. It supplies an incomplete sample rather than an executable
reproduction. The agent's narrowing is source-based; it did not run the proposed
OL-specific experiment.

| Input -> decision sequence | Available evidence and observed next action |
| --- | --- |
| 75 -> 78 | `filewriter.py` shows OL dispatching to `write_OWvalue`, which writes the stored bytes directly. Move upstream to `DataElement` conversion. |
| 105 -> 108 | `_convert_value` wraps lists in MultiValue, while ordinary bytes do not take that branch. Read the setter; retain writer dispatch as an alternative if the setter preserves bytes. |
| 118 -> 121 | The setter's backslash-splitting exclusion list omits OL. Splitting bytes creates a list that the already-read conversion code wraps in MultiValue. Search for the predicate and existing backslash tests. |
| 133 -> 136; 146 -> 149 | Read the existing textual-backslash test, then edit the setter. Public `causal_revision` replaces the writer explanation with upstream splitting. |
| 164 -> 167 | Run registered regression. The still-delivered plan to add an OL round-trip test is replaced with a plan to submit after regression PASS. |
| 178 -> 182 | After 212 PASS, finish. No added test, selected-test run or probe occurred. Original isolated evaluation is PASS. |

The actual source establishes a connected mechanism: `filewriter.py:1157` routes
OL to `write_OWvalue`; lines 278-284 write the stored value. In `dataelem.py`, lines
439-448 permit splitting OL bytes on `0x5c`, and lines 509-515 convert the resulting
list to MultiValue. Input 118 contains these setter/conversion lines. Input 146
also contains the existing textual-backslash test, a preservation constraint.
The one edit adds OD, OL, OV, SV and UV to the exclusion list. This accounts for
the reported type mismatch without changing the consumer. Its broader VR scope
was not individually validated by an agent-authored test.

The successful pivot predates its only working-note creation. That note is then
expired with `source_changed` after the edit, as the lifecycle records disclose.
At input 164, the explicit plan to test OL bytes through add_new and round-trip
write/read is still delivered, although bound to the previous diff. The next
model-authored plan instead says:

> If it passes, submit without further edits

This is an observed plan replacement, not evidence that compaction erased the
testing intention. Three edit slots and 1,267 solver seconds remained before the
regression check; at finish, three slots and 1,249 seconds remained. Resource
exhaustion does not explain this omission. The check receipt reports output
truncation with 207 warnings and a visible 212-PASS summary; it supplies no
agent-authored OL round-trip observation. Acceptance PASS remains useful outcome
evidence, but does not retroactively create that missing verification.

## Decision implications and limits

- **Maintain the current runtime and bounded tool set.** Neither run demonstrates
  a projection, source-identity, note-storage or tool-admission defect requiring
  a correction. This is a bounded finding, not certification of the entire design.
  SQLFluff's unacquired L039 behavior and its last-edit capacity remain real limits.
- **Do not attribute this contrast to memory or context size.** SQLFluff made no
  non-null memory updates; Pydicom's upstream pivot occurred before its one note.
  Relevant observed evidence and the abandoned test plan survived at decisive
  inputs. Larger context cannot by itself supply an explanation the agent never
  investigated. These cases do not establish that pruning is harmless everywhere.
- **Treat original-task behavior and regression preservation as a joint repair
  question on the same final diff.** SQLFluff answered them on different patches.
  Pydicom never executed its proposed direct task check. A useful verification
  should distinguish the replacement hypothesis, not merely repeat a passing suite.
  SQLFluff already had such an assertion; new test-generation infrastructure was
  not necessary to expose its final error.
- **Do not adopt another generic prompt, mandatory plan/probe, automatic selected
  recheck or larger budget from this pair.** Current source already instructs
  ownership reasoning, untested assumptions and current-diff checks. SQLFluff's
  thin input 384 has no `next_action=finish_task` instruction, so that specific
  wording is not necessary for premature closure. Pydicom's current-policy input
  does offer finish with a qualification about untested behavior. This is not a
  controlled test of either policy's effect.

The decision changed by this audit is explanatory: prioritize whether a revised
causal claim actually covers the complete public behavior, rather than assuming
the failure is lost context or inability to change hypotheses. Preserve the
implementation until an intervention demonstrates better repairs and regressions,
with independent acceptance assessed separately. More tests, note use, failure
detection or blocked submissions alone are not repair-quality improvement.

The existing [L039 ownership control](2026-10-08-rule-ownership.md) shows the tested
requirements are compatible: its operator patch changed 2 FAIL / 5 PASS to 7 PASS
and kept 506 regressions passing. It is not a fresh agent solve, unique-root-cause
proof, or private acceptance result. It supplies a public counterexample to the
idea that the task inherently required sacrificing one behavior. The remaining
agent-level question is how to select that distinguishing rule-interaction
investigation before committing the last repair. This report queues no additional
experiment and does not activate the separately prepared revision comparison.

## Reproduction and validation

Investigation root: `C:/pt/hypcmp01`. Frozen `plan.json` records the question,
alternatives, selected runs, zero-call/execution limits and stop conditions.
`runs/run_dev_hypothesiscomparison.jsonl` is append-only, hash-chained dev-run-v1.

- `analyze.py` and `{sql,pyd}-public-turns.json`: original task, actual inputs,
  public tool decisions and action results, with original input artifact refs.
- `resolve_views.py`, `visible_sources.py`, and `{sql,pyd}-visible-sources.json`:
  source resolution with file hashes, exact lines and native action provenance.
  Historical and current versions are separate; source was not filled from a
  later checkout. Catalog and native source resolution found no ambiguity.
- `verify_decisions.py`, `request-verification.json`, `decision-evidence.json`:
  all 40 prepared/dispatched requests verified and 14 decisive inputs extracted.
- `prior-public-diagnostics.json`: hash-verified receipts for the existing final
  and intermediate selected tests, plus the prior ownership-control summary.
  These prior executions were not rerun or delivered to either solver here.
- `input-bindings.json` and `verification-bindings.json`: consumed-file hashes;
  all 55 initial input bindings were unchanged at verification.

Source journal heads are
`sha256:8e0d6bff0f4b1017988e9b37e1d7b4a2f376712d5d2b6e448001bb6cce3edfa5`
(SQLFluff, 398 events) and
`sha256:d5eb4605a6ab4b8497a90e6e994b7ebbb82e06bf3eaae0cbe0985c2887738ada`
(Pydicom, 193 events). Relevant SQLFluff diff identities are `945e1aaf...f7014e6`
(selected 4 PASS), `59679012...6d2987` (third edit), and `94b0aeeb...efff25f3`
(submitted); Pydicom submitted `6493047b...676897`. Full hashes and action IDs
remain in the decision and diagnostic artifacts.

Only this report, current status and the history index are changed. Validation
receipts are recorded in `C:/pt/hypcmp01/closeout.json`: documentation layout/link
checks, new-report links, whitespace and preserved input/runtime/user-edit bytes.
An initial current-status byte-budget failure was corrected by shortening that
page; its failed validation receipt remains alongside the subsequent check.
The broad runtime suite, mock smoke, Docker and new provider/private evaluations
are NOT_RUN for this documentation-only investigation. Prior historical outcomes
retain their original scope; no performance or generalization claim is produced.
