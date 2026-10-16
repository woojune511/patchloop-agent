# Why D's astroid plans still closed without the promised verification

Date: 2026-10-16. Offline follow-up to the closed
[C/D comparison](2026-10-16-plan-grounds.md). No provider call, solver probe/check,
candidate replay or evaluator execution was added. Runtime and historical experiment
artifacts remain unchanged. This is a public-log diagnosis, not hidden-test analysis.

## Question and finding

Both D astroid runs retained the previous plan and a revision reason, yet omitted
their promised targeted regression. The question is whether delivery, resource limits
or the agent's recorded evidence judgment explains that omission. It matters because
recording why a check was dropped can leave the same unsupported completion decision.

The new fields and instructions reached both final decisions, including the actual
unfinished predecessor plan. Both runs changed the verification purpose **before**
the first public PASS: D1 substituted an already-successful neighboring path plus the
existing suite for verification of the repaired path; D2 made the targeted test
conditional on the existing suite failing. After PASS, they kept that revised plan
and declared the remaining evidence sufficient. The observed failure is in connecting
evidence to the original purpose, not loss of the retained plan or forced submission.

There was real late-run budget pressure, but probes/tests reopened after PASS with
five calls remaining in each D run. It is therefore insufficient to explain the exit
as a tool prohibition or exhausted budget. The logs show public decisions and actions;
they do not reveal internal deliberation or isolate the causal effect of one sentence.

## Exact comparison and integrity

C here is the **fresh C control in the C/D panel**, not C from the earlier B/C panel.
Both use task 13, `pylint-dev__astroid-1333`, two independent solves per version.
C is `b34e911d88acab74e431120c8e39760cc2656c25`; D is
`fcfa496dfb57f7e0d79616e5389fac034cfbc6b2`. Artifact A1-13/A2-13 map to report C1/C2,
and B1-13/B2-13 map to D1/D2. Same repetition numbers do not mean matched randomness
or replay of the same completion decision. The whole runtime intervention was exposed
from the start; this audit cannot isolate a single field's effect.

All four original journal chains and 155 prepared request artifact/canonical hashes
were verified. Of those preparations, 146 have a matching provider dispatch; the
other nine are not additional calls. Each final request has exactly one dispatch.
The re-extracted public state, system text and tool schema equal the prior public
evidence packet. This audit binds 173 source files, including the original requests,
journals, frozen manifest, public audit and closed result records.

The public issue describes `src/__init__.py`, absent `src/project/__init__.py`, and
`src/project/file.py`, with `pylint src/project` producing F0010. Public tests under
`tests/**` may be added; the registered suite runs `tests`. No hidden test, reference
patch or private evaluator detail was used to assess verification relevance.

## What was actually delivered

The C and D final `completion_guidance` message, finish description and assessment
schema are identical. They already say current PASS establishes eligibility rather than
correctness, ask the agent to revisit unfinished verification, and permit more work.
There is no automatic finish action and `next_action` is null.

D's actual system additionally says:

> Match claimed verification to executed input/assertion/result on this diff, or label it source inference.

Its actual planning instruction says:

> Name any unfinished verification being removed or closed, its purpose, and the already observed evidence that meets that purpose, or why it no longer matters.

It also requires accounting for unfinished purposes at finish even with a null plan
update. Both D final requests contain `last_change.previous_plan`, the revision reason,
`review_request.requested=true` with `check_result` and `first_ready_to_submit`, and
the new `plan_update_reason` schema. The check receipt says
`requirement_verification=not_assessed` and explicitly limits claims from PASS.

Both pre-edit probes remain in the final input with their actual output,
`historical=true`, the empty-diff hash and `behavior_verdict=not_assessed`. D1's
directory-loading exception is still present. The relevant evidence was not erased
by the post-check context handoff. The check selector parser reports
`selection_kind=unresolved` for the Python wrapper in both versions; that is unknown
coverage, not proof that a particular case did or did not execute.

## D1: success on the neighboring path replaced the promised repair check

Original B1-13 journal sequences provide this chain:

1. Plan 15 promises a focused missing-init regression. Probe 322/323 constructs the
   public directory shape and prints two outcomes: `ast_from_file(directory)` raises
   `AstroidBuildingError` wrapping `IsADirectoryError`; explicit
   `ast_from_module_name('src.project')` succeeds. These are pre-edit observations.
2. Plan 349 correctly narrows the suspect path and explicitly keeps the regression
   requirement unchanged. Its reason says the successful module-name call settled
   that question, while the file-resolution repair and its test remain.
3. Mutation 468 changes `get_source_file` from `os.path.exists(base)` to
   `os.path.isfile(base)`. No test is added and the failing call is not rerun.
4. Plan 485, before check 486/487, replaces the remaining test with base-regression.
   The reason states: "The probe closed the module-name fallback question" and
   "The only remaining verification purpose is the public regression check on the
   patched file-resolution branch." The plan now says "If the check passes, submit".
5. Final request 491, dispatched at 496, still includes the predecessor's explicit
   regression promise and both probe outcomes. The next action is finish 502/503.
   Assessment claims the suite "confirms the reported scenario no longer fails in
   the visible check", without naming an executed current-diff input/assertion for it.

The successful explicit module-name call did not establish that the repaired
file-entry path derives the correct module name and reaches that fallback. The probe
also did not reproduce the complete pylint command. The patch's plausibility and
the suite's 1231 PASS therefore cannot be promoted to the claimed verification
without the missing evidence connection. This does not prove the suite contains
zero relevant coverage; it shows that the claimed connection was not established.

D1 also retained unresolved concern `v1`: a package directory without init should
no longer trigger a load error when analyzed from its parent tree. At finish it
resolved v1 using base-regression's action ID and the same branch-based rationale;
note receipt 500 accepts that update. This is valid current-diff provenance, not a
semantic determination that the suite addresses v1. The concern mechanism explicitly
labels such decisions model-authored and unverified.

An earlier attempt to link the probe as an unsuccessful execution was rejected:
the diagnostic caught/printed the exception and exited zero. That did not erase v1,
the failure output or the plan, all of which remained at finish. It is a separate
observation-catalog boundary, not evidence that D lacked the failing observation.

## D2: testing became conditional on a regression failure

Original B2-13 shows a different way to reach the same stopping condition:

1. Plan 16 promises a regression. Probe 221/222 checks directory-to-module mapping,
   `file_info_from_modpath` and `file_from_module_name`; namespace metadata succeeds.
   It neither calls `ast_from_file` nor creates the issue's `file.py` child. This is
   evidence about metadata lookup, not repaired entry-point behavior.
2. Plan 237 keeps the regression requirement and states the remaining uncertainty
   is the manager/build entry point. Mutation 491 then changes
   `source = True` to `source = not os.path.isdir(filepath)` in `ast_from_file`.
3. Plan 504, before check 505/506, declares the repair complete and makes a focused
   `unittest_manager.py` test conditional: add it **if** the existing suite fails.
   Its recorded reason says "targeted test addition is only needed if the visible
   suite exposes a gap". The preceding unconditional test promise remains visible.
4. The unchanged suite passes 1231 tests. Final request 510, dispatched at 515,
   contains that predecessor and reason. Finish 521/522 says no blocking verification
   remains; it neither adds/runs the promised case nor accounts for its omission.

Here an accepted mutation plus a successful pre-edit lookup is treated as enough
to finish the investigation. The test is then recast as a response to an existing
regression failure. A suite's failure can reveal a defect; its success does not by
itself establish that the originally planned case ran. That conditional rule removes
the very check intended to reveal a gap that existing regressions might miss.

## What C and the resource evidence distinguish

| Run | Observed trajectory | Verification at closure |
| --- | --- | --- |
| C1 | No probe; one source guard; 1231 PASS; immediate finish | Same unsupported substitution; final patch is byte-identical to D1 |
| D1 | Pre-edit failing/successful entry points; same guard; 1231 PASS; immediate finish | More diagnosis and retained reasons, but no repaired-path recheck or new test |
| C2 | Pre-edit module-path failure; source edit plus new assertion; public FAIL; repair; 1232 PASS | Executed support for the chosen plan purpose, all before first PASS |
| D2 | Pre-edit successful metadata lookup; manager guard; 1231 PASS; immediate finish | Targeted test weakened to "only if suite fails" |

C2's probe 400/401 observes `modpath_from_file` failure. It adds
`test_modpath_from_file_namespace_package` at 483, expecting
`['src', 'project', 'file']`. Check 499 fails in that new test. Mutation 558 corrects
the `spec.find_spec` lookup relative to the parent path; check 564 then passes.
This is a concrete falsification-and-repair loop already possible in C. Its scoped
test does not prove complete public-task correctness: **all four independent grades
remain FAIL**. No historical grade or public closure category is revised by this audit.

Both D runs spent 33 model calls before their first edit; at seven calls remaining,
the completion-horizon policy temporarily limited tools to mutation/stop. At six
remaining, mutation/check/stop were available; this is when the plans were narrowed.
The restriction can plausibly contribute to a short completion strategy. It did
not force finish after PASS:

| Final delivered state | D1 | D2 |
| --- | ---: | ---: |
| Remaining model calls, including this decision | 5 | 5 |
| Remaining accepted edits | 3 | 3 |
| Remaining solver seconds, excluding evaluation reserve | 986 | 1000 |
| Remaining recorded cost capacity USD | 0.50411640 | 0.56244015 |
| `run_probe`, `run_tests`, `replace_text` available | Yes | Yes |
| Extra actions after first PASS before finish | 0 | 0 |

Both states mark exploration open and predict four exploratory turns after reserving
finish. A successful edit/check/finish fits the minimum horizon, while the full
failure-recovery reserve does not. Availability does not guarantee a new repair
would succeed or that every future request would fit. It does establish that the
observed choice was not mechanically restricted to finish. Neither finish basis
cites exhausted resources; both claim the current evidence is sufficient.

## Decision and remaining uncertainty

The strongest supported explanation is an unsupported reduction in verification
purpose: a neighboring path's success and a plausible small edit are taken to settle
the original behavioral question, leaving generic regression as the only exit test.
D makes that substitution auditable; it does not establish its validity. C1's same
patch/exit pattern and C2's actual failing assertion help distinguish this from a
new field-delivery defect or the absence of optional verification tools.

The contract intentionally validates reason presence/length, keeps the predecessor,
and binds `plan_review` to the submitted diff. It does not certify a free-text reason's
logical sufficiency or mark the plan's purposes verified. This audit found those
implemented boundaries operating as specified; it adds no semantic validator,
mandatory check, runtime fix, prompt tuning or paid follow-up.

Remaining uncertainties are how strongly the late budget restriction influenced the
choice and whether another task-independent intervention would improve that judgment.
These four independent trajectories cannot decide either question. The failure of
both independent D evaluations does not identify which hidden requirement failed,
and it is not used to retroactively define the omitted public verification.

## Evidence and validation

Fresh provider-free evidence root: `C:/pt/planastroidaudit01/`.

- `extraction.json`: counts, row mapping, final budgets, plans and assessments.
- `actual-system-C-D.diff`: exact delivered system-text difference.
- `C1/`, `C2/`, `D1/`, `D2/`: readable public timelines, all prepared public
  request projections, final request/schema and original event sequence references.
- `source-bindings.json`: the 173 original file hashes checked before and after.
- `runs/run_dev_astroidclosureaudit.jsonl`: append-only hash-chained audit record.
- `validation.json`: helper lint, documentation checks, source preservation and
  zero provider/solver/evaluator execution.

Only this new report and mutable status/index links are changed in the repository.
The initial extractor assumed an optional delivery field existed in early requests;
it was corrected to retain only present fields before completing the extraction.
No evidence value was filled in, no original artifact was rewritten, and no solver
or provider was invoked. Runtime tests and evaluator replays are NOT_RUN because
this is a read-only diagnosis plus documentation.
