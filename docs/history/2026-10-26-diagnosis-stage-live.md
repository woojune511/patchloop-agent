# Live diagnosis-stage pilot: no first mutation, diagnosis not exercised

Date: 2026-10-26. Follow-up to the [local implementation](2026-10-26-diagnosis-stage.md).

## Material Passport and question

- Origin: academic-research-suite / experiment-agent, mode run;
  version `diagnosis-stage-live-v1`.
- Evidence: live-executed and saved public receipts analyzed; `official=false`,
  `claim_eligible=false`. No independent reproducibility rerun.
- Runtime commit: `9e8c953feb4b638018c3f2e4202943fe8a14e4c3`.
- Runtime hash: `sha256:f37a81117ad7fe0cd87005aa062f2d994ce213cbac9661b745ad9188b77967ac`.
- Run: `run_dev_65272138acea4650`.

The [previous live pilot](2026-10-26-diagnosis-mode-live.md) left F0010 unchanged
after a late first mutation and generated no diagnostic action. The compact
diagnosis stage moves watch construction to the host and leaves the model a small
focus-only request, with dedicated public context and typed correction. The question
was whether this permits actual caller-path observation and a repair that removes
F0010 while preserving the control behavior.

The predeclared criteria separate stage entry, valid focus selection, host construction,
actual tracing, use of that evidence, original replay, checks, submission and isolated
acceptance. No qualifying missed mutation, no action, irrelevant focus, incomplete
trace and ineffective repair were possible outcomes. A run that never reaches diagnosis
does not test its effectiveness; no mutation or diagnosis was forced by the operator.

## Frozen scope and authorization

The immediately preceding exact plan was approved by the current user message
"실행해줘". A separate immutable authorization receipt binds its request hash;
the prepared request retains its original awaiting-approval state. Revision 2 had
updated the analysis classifier to recognize focus-only requests before approval,
without changing solve conditions. Earlier paid allocations remain closed.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, exposed dev-train Astroid-1333.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- Normal output ceiling 40,000; one protocol-correction allowance 25,000;
  repeat 1; total invocation cap $1.20.
- Limits: 40 model calls, 100 actions, four accepted mutations, 1,800 active seconds;
  operator hard timeout 1,920 seconds.
- Segmented-v1, result-or-size-v1, brief-v1, probe policy none, repair-recheck,
  protected-v1 inspection, bounded-v1 reproduction and completion-recovery-v1.
  The run_probe recommendation and input-context limits were unchanged.
- Same prepared source, dependencies, existing images and profile. Two frozen public
  checks share 120 seconds and require a submitted patch; they are separate from
  registered isolated evaluation. No image acquisition or Docker Desktop launch.
- Zero SDK retries; stop on count, transport, billing, cleanup or source uncertainty.
  No retry, resume, replacement, limit increase or operator feedback to the solver.

Preflight verified the frozen commit, 120 source files, runtime/task hashes,
prepared inputs and existing image identities. Existing local validation was reused:
quick 369 PASS in 81.14 seconds, focused owner checks, Ruff PASS and isolated mock
acceptance. These establish local mechanisms, not live repair effectiveness.

## Observed sequence

| Stage | Observation |
| --- | --- |
| Model call 1 | Original probe executed on unchanged base; bug call emitted F0010, control did not; host and authored judgments agreed |
| Calls 2-27 | 26 successful search/read actions, no mutation |
| Call 28 | Helper queried modpath_from_file for directory and file paths; both returned caught ImportError |
| Call 29 | One further read, still no mutation |
| Call 30 | Completion horizon closed inspection; replace_text and stop_task offered; 30,704 output tokens, all reported as reasoning, no action |
| Call 31 | Reserved correction received full 25,000 tokens; all reported as reasoning, no action |
| Terminal | INCOMPLETE_RESPONSE after the allowed correction; unchanged diff, no submission |

The captured original call was `pylint.lint.Run(['src/project'], exit=False)` from
a fixture with `src/__init__.py` and no `src/project/__init__.py`. Its F0010 reported
the missing `src/project/__init__.py`. The control was `Run(['src'], exit=False)`.
The two captures were complete and the host computed
`bug_has_error=true, control_has_error=false`. Public issue-to-caller mapping remains
model-authored/unverified; a matching selected case is not independent acceptance.

The helper used a new temporary directory and directly called `modpath_from_file`.
Both the directory and the file produced "Unable to find module" ImportError,
which its program caught and printed. Process PASS therefore did not establish a
successful contrasting condition or an observed original caller path. There was no
helper program NameError or helper correction in this run.

All 31 dispatched states lacked diagnosis_stage. Focus requests, host watch
construction, diagnosis execution, typed diagnosis correction, linked mutations and
before/after selected-test comparisons were all zero. These mechanisms are
**NOT_EXERCISED**. The ordinary successful helper probe is not a diagnosis-stage run.

## Resources and result

- Settled cost: **$1.078465800 of $1.20**; unused $0.121534200. Allocation closed.
- Wall time: **865.870 seconds** (about 14 minutes 26 seconds), no hard timeout.
- 31 model dispatches, 33 input-count calls, 29 tool actions; zero mutation requests
  and zero accepted mutations.
- Tools: 17 searches, 10 reads, two run_probe executions; no request rejection.
- Tokens: 1,301,644 input including 761,984 cached; 137,016 output including 128,064
  reasoning tokens. Reasoning is included in output, not an additional total.
- Checks, selected tests, finish, frozen post-submission public checks, isolated
  acceptance and safety: **NOT_RUN**. The conditional assessor recorded no_submission.

Before call 30, $0.793772250 was already settled. The future reserve was $0.248652000,
including $0.157500000 for correction, and the admitted ordinary output was 30,704.
The actual input was 25,877 tokens; this was not a 60,000-token input-limit failure.
Call 31 received the full 25,000 correction output with 25,596 input tokens and
$0.091152000 reserved for successors. Both calls used fresh ordinary context
segments; neither was a compact diagnosis segment.

The final two calls cost $0.284693550 without producing an action. Termination was
caused by the second incomplete response, not by exhausting the total dollar, call
or time cap. Reserving correction worked as funding; it did not ensure useful output.
The unused balance does not establish that another call or a higher ceiling would
have succeeded. Reported reasoning counts do not reveal why generation stalled;
provider reasoning content was not inspected.

## Decision and limits

Retain the locally validated diagnosis implementation without claiming live benefit
or rejection. This trajectory failed upstream, during the transition from inspection
to first mutation. It shifts the next investigation toward whether the public
evidence supported an actionable repair hypothesis, whether the helper distinguished
the intended cases, and what the first-mutation contract required the model to emit.
Inspect those saved public inputs before adding another rule or increasing limits.

This is one stochastic fresh solve on an exposed task. The earlier pilot used a
file-path control, while this model authored the `src` directory control. Although
configuration and prepared inputs were held fixed, generated probes, hypotheses and
trajectories differ. No paired causal gain, regression, optimal budget or held-out
generalization follows. No additional run or continuation is authorized here.

## Evidence and validation

Preparation: `C:/pt/diagnosis-stage-live-ready-v1`.
Execution and append-only hash-chained dev-run-v1 journals:
`C:/pt/diagnosis-stage-live-v1`.

| Artifact | SHA-256 |
| --- | --- |
| request.json | `cad2b772ae41a110391706f6a7595f6e3a53f7c094521146b42cd2a599a37a1a` |
| authorization.json | `34673d1f5b3749958ba15ef491c2d0f39644fd56df449814ffb38bdd83e8090b` |
| collection.json | `467d1d6606b2a53a731612db75d5187eccf47989c26ecad52663c0338d22ed71` |
| public-analysis.json | `57c62d0b77ec89cbc0a5138301a579f70cfd6f9b77a9177db802ff13ab279e76` |
| execution-findings.json | `0dbcb3f61eb72f2e82d413edd855bce8412239e7b191a93af119d0cee78ff65c` |
| Unchanged diff | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

All provider starts settled with known billing/counting, and CLI totals agreed with
the journal. Action_id/input_hash pairs, journal chains, sealed inputs and runtime
were verified; initial collection checked 162 content-addressed objects. Post-run
analysis made zero provider calls and zero target executions. No private evaluator
content, reference patch or provider reasoning content was read.

Final documentation validation, commit and provenance are in closeout.json. Runtime
code was unchanged; closed history and the pre-existing unrelated working-tree
changes were preserved. Full/quick runtime suites were not repeated for this docs-only
closeout; the original short local validation remains separate evidence.
