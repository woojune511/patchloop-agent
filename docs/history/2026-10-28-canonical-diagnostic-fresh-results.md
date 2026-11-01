# Canonical diagnostic pilot: normal submission, acceptance failure

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: approved one-run execution and public-evidence audit
- Origin Date: 2026-10-28 KST (started 2026-10-27)
- Verification Status: LIVE_EXECUTED / EVALUATOR_FAIL
- Runtime commit: `c9efc5c4`; preparation docs commit: `6b2eec6b`
- official=false; claim-ineligible; allocation CLOSED

## Question, intervention and scope

The [sealed plan](2026-10-27-canonical-diagnostic-fresh-plan.md) followed a
[clean-start failure](2026-10-27-normal-recovery-fresh-results.md) where changed F0010
wording split the helper and host verdicts and prevented another response.
Fresh invocation v6 computes diagnostic-code values once on the host. This pilot
tested actual model use and ordinary completion under the same task, model and limits.

The user approved manifest
`sha256:346cfa8cfc2a4100634bdd908c6237a2a79fc614b2296479427453774b256225`
for Astroid-1333 (`dev-train/current-dev20/13`), mini snapshot
`gpt-5.4-mini-2026-03-17`, xhigh, repository `.env`, once, USD 4.50.
Limits remained 20 total responses including one correction, 40 tools, three edits,
60K input, 40K/25K output and 2,400 seconds including 390 for evaluation.
No previous patch, observations or private evaluator information entered model context.
No retry, operator patch, synthetic submission or extra target replay was performed.

## Observed result

| Component | Evidence |
|---|---|
| Fresh code judgment | Model chose two F0010 rules; host policy captured-diagnostic-v2 |
| First probe | Invalid `option=False` failed argument binding; host correctly returned unknown |
| Corrected baseline | Complete captures: problem F0010 present, control absent; host true/false |
| Original path observation | Entered modpath_from_file and file_build; missing initializer raised errors |
| Accepted edits | One: synthesize an empty package module for a missing initializer under an existing directory |
| Post-edit code observation | Complete captures: F0010 absent in both calls; host false/false |
| Actual next requests | Received code-match result, current patch and unverified comparability state |
| Public regression | 1,231 passed, 69 skipped, 15 xfailed; exit 0, 10.29 seconds |
| Normal finish_task | Succeeded; submitted the exact model patch |
| Delivery verification | unverified_delivery; original replay comparability changed |
| Isolated task acceptance | FAIL / PRIVATE_EVALUATION_FAILED |
| Isolated safety | PASS, separate from task correctness |
| Changed-wording failure feedback and revision | NOT_EXERCISED: the first edit removed the selected code |

This run reached ordinary finish and isolated evaluation, but did not repair the
task successfully. Host code computation was used correctly on the observed
captures. That does not establish a success-rate improvement or validate the
changed-wording repair loop with a live model.

## Public evidence sequence and limitations

The first helper declared F0010 without a second Boolean extractor, but passed
`option=False` to pylint.lint.Run. Binding failed before the target executed.
The next helper removed the invalid argument, reproduced F0010 on the unchanged
source and captured both calls completely. No protocol correction was used.

The first edit changed `AstroidBuilder.file_build`: when a nonexistent
`__init__.py` belongs to an existing directory, it returns
`self.string_build("", modname, path=path)` instead of raising AstroidBuildingError.
The next automatic replay captured empty output for the problem call and ordinary
diagnostics for the control. F0010 was absent. This is a narrow output observation,
not proof that the intended files were correctly discovered or analyzed.

The replay was not fully comparable. Baseline and replay call-1 root inventories
both had 14 entries and the same fingerprint. Before call-2, the replay inventory
had 16 entries and a different hash. Those are the only normalized-condition
differences: `/calls/1/inputs/0/entries` and `/calls/1/inputs/0/hash`. The helper
fingerprinted its entire reproduction root, including work/cache directories.
The saved receipt does not enumerate the two extra entries, so their identity and
cause remain unverified. Do not label the whole original case PASS or bypass this
check based on an assumed cache explanation.

Independent audit checked actual prepared request hashes at sequences 153, 168
and 184 against subsequent dispatch. The first received the matched code result;
all three retained the UNKNOWN evidence / observed_call_or_setup_changed state,
early_replay_reusable=false, and the complete 924-character current patch. The
latter two also received current-diff base-regression PASS. The failure here was
not lost post-edit feedback or stale source in those requests.

The retained malformed first case also remains unverified, but the corrected case
independently fails comparability. Normal finish produced unverified_delivery.
Only scalar evaluator outcomes were used; private test details were neither
inspected for diagnosis nor fed back to the agent.

## Resources and integrity

- Run: `run_dev_9733c1d801864fcf`.
- Cost: USD 0.59931540 / 4.50; all 12 provider usages settled.
- Active duration: 818,048 ms, approximately 13m38s.
- Counts: 12 input counts, 12 model responses, 16 actions, one accepted edit.
- Four probe executions: initial helper, corrected helper, original-path
  observation and candidate replay. One public regression; one normal finish.
- Maximum input/output: 38,374 / 35,518 tokens; eight context segments.
- No protocol correction or configured-resource exhaustion. The ninth response,
  which produced the edit, used 35,518 output tokens and about 280 seconds.
- Provider, input-count, action and probe started/finished identities pair exactly;
  hash-chained journal, total cost and terminal runtime identity verify.

The result root is `C:/pt/canonical-diagnostic-fresh-run-v1`.
Collection hash:
`sha256:2e60ceaa69c6ea08ccc3d5339981595e1c04b891e3c6047884d6ec3009513a1a`.
Bounded public analysis is `analysis.json`, hash:
`sha256:e6b6fae821b4972d95790bdd19c83a62abf3fb9f4590a2efc1f2ad9dc4a3e121`.
Patch hash:
`sha256:5b4284f3c4445e7d13b28ed8e76e41f1d5c33e2f8520d937fb2d53a8a5aa2d1d`.
The plan journal records approval, one dispatch, returned collection and closure.
Unused funds do not authorize another invocation.

## Decision and next question

Keep the canonical host judgment: this run used it without the earlier duplicate
predicate conflict. The local changed-wording tests still provide that mechanism's
evidence; the live run did not exercise a remaining-code failure after an edit.
Do not raise context or cost limits on this result: the agent submitted within them.

The next useful diagnosis is whether the empty-module repair merely suppresses
the error while changing which public files are analyzed, and which generated
entries alter call-2 identity. Public, discriminating behavior and explicit fixture
boundaries can test those hypotheses without consulting private expected patches.
Neither hypothesis is established solely by this evaluator FAIL. No follow-up paid
experiment or implementation is included in this completed allocation.
