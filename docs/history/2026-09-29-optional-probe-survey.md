# Independent saved optional-probe candidates

Date: 2026-09-29. Read-only evidence survey; no provider calls, task/tool execution,
Docker operation or private evaluation. Follow-up to the narrower
[exposure design](2026-09-29-observation-exposure-design.md); its original packet is unchanged.

## Question and scope

The first 45-run inventory contained optional probe failures only on toqito. Search
independent saved journals for agent-requested probe failures on other public tasks,
without generating counterexamples or selecting by private acceptance.

Enumerated 19,525 run_dev_*.jsonl paths under C:/pt, excluding tmp, workspaces, .git,
artifacts, prepared and evaluations directories. This is not a whole-machine census.
First-event filtering found 443 journals headed by OpenAI/dev-train run_started.
Eleven malformed first records were under test_preflight/test_mismatched fixture
paths; they are listed in headers.json and excluded. Journals beginning with episode
or diagnostic events are outside this filter, so the search is not exhaustive.

394 journal files (287 distinct recorded run IDs) contain positive recorded cost
and response-ID evidence for model-requested tools. This is recorded provenance,
not an external billing audit or 394 independent experiments. Counted 357 probe
occurrences and 120 unsuccessful occurrences. Deduplicating task/action/input/diff/
output identity yields 56 unsuccessful probe outcomes: AnyIO 44, toqito 7, pyfakefs 3,
tox 2. Six outcomes match the original inventory; 50 are outside it. Copies are not
independent episodes. Unsuccessful outcomes include execution/setup/inspection
failures; the number does not mean 56 product bugs or supported repair cases.

## Reviewed candidates

Each selected action matches an earlier recorded paid model run_probe request.
Source journal hash chains, input artifact hashes and candidate diff identity pass.
All five have a later model-input checkpoint and run_probe remains callable.
Paired public-context fixtures differ only in the automatic observations field;
operator classifications are not inserted into either arm. These are still context
fixtures, not restored runnable environments or parity-checked provider requests.

| Cut | Public observation | Remaining edits/calls | Appropriate diagnostic |
| --- | --- | --- | --- |
| N1 AnyIO | check_setup expects wrapped.__name__ to be _call_in_runner_task although the function is named wrapped | 3 / 34 | Correct experiment prerequisite; original behavior not yet answered |
| T1 tox | tox.version import fails before substitution cases | 3 / 37 | Execution readiness, not candidate behavior |
| T2 tox | Factor-filtered value is empty, but missing-key fallback also returns empty and assertion fails | 3 / 36 | Candidate behavioral failure pending real-public-path applicability review |
| P1 pyfakefs | FakeFilesystem.symlink is absent; AttributeError occurs before errno cases | 1 / 12 | Correct probe API usage; avoid claiming a product bug |
| P2 pyfakefs | inspect.getsource(os.makedirs) cannot obtain source | 4 / 29 | Revise investigation method without inferring behavior from failed inspection |

N1: run_dev_49efb33fc65a49a2, call_2JGcBMcg2C5fCncp3neASL4Q.
T1/T2: run_dev_a70238e212334718, call_zpxMz31ZAieaMrHoxlJIvr8a /
call_CndFh03WtWoKdz1ra3Bdy9EP. They are successive cuts of one trajectory, not two
independent successes/failures. P1: run_dev_83afa4772611467a,
call_R0a7qpWA5r82iRTEguW5wKyL. P2: run_dev_241839df8d524755,
call_gsC8ELPwtgDo1Fh87fk8nV3J. Five cuts span four runs and three tasks.

T2 uses LoaderStub/ConfStub and package import bypasses. Its assertion alone does
not establish supported behavior or a product defect. N1 also wraps runner behavior;
fixing its name assertion does not validate the wrapper as an equivalent public path.
Past runtime/model/guidance differences must not be treated as current-baseline
performance; future A/B arms must share the same restored state and current schema.
Historical probes/questions remain exposed examples, not held-out evidence.

## Decision

The diversity gap in the first inventory is narrowed: agent-run optional failures
exist beyond toqito. A multi-task interpretation/verification-recovery diagnostic
now has candidate material. Do not silently redefine that as demonstrated repair
improvement. Multi-task supported behavioral-repair applicability is still unproven.

Prefer N1/T1/P1 as one initial interpretation candidate per task, with P2 as an
inspection alternative and T2 separately pending applicability. Do not count T1 and
T2 as independent task replicates. Before any paid comparison, verify public-path
applicability, restore equal candidate/history/tool state, inspect available existing
environments, and establish full-request exposure parity. Preserve the earlier
judging rules: relevant investigation, valid verification, false bug claims, redundant
work and resource use; linking alone is secondary. No new paid allocation is opened.

## Artifacts and verification

Packet: C:/pt/analyses/optional-probe-survey-20260929-v1.
journal-paths.txt and headers.json preserve discovery scope/errors; survey.py and
survey.json record matching/deduplication/provenance; shortlist.py and shortlist.json
freeze source references, checkpoints, budgets and paired fixture hashes.
An external dev-run-v1 hash chain records survey and shortlist completion.
Selected source bytes remained unchanged. Five source chains and five context pairs
passed verification. Restoration, environment readiness, actual provider-request
parity and behavioral effect remain NOT_RUN. Runtime implementation is unchanged.
Five documentation layout/link tests and git diff --check passed after keeping the
current summary within its existing size cap; no runtime suite/mock rerun was needed.
