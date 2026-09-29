# Frozen model-selected probes: registered-path execution

Following the [response-only selection result](2026-09-29-discriminating-case-selection-results.md),
the user authorized execution of the eight frozen probe programs. This stage made
zero model calls and cost USD 0 in provider charges. Each program ran once, without
changing its code, question, expected values or tool decision. The sixteen selected
run_check actions were outside this follow-up and were not executed.

## Execution and observations

| Program | Exit | Observation | Interpretation |
| --- | --- | --- | --- |
| P B1 | 0 | Fresh plain OpenAI field-mode profile emits empty custom_reasoning | Unsupported model expectation passes; not correct requirement behavior. |
| H B1 | 1 | Ambient-only HfApi rebases the default-owned route | Public counterexample reproduced. |
| F B1 | 0 | Orphan chain removed; ROOT-referenced child and leaf retained | Selected preservation control holds. |
| L B1 | 0 | Top-level and nested missing-key errors receive the same diagnostic | Scope observation; not an established task failure. |
| G B1 | 1 | Import fails: pandas missing | Setup/availability failure; skeleton behavior unobserved. |
| H B2 | 1 | Direct call preserves route; ambient and explicit clients both rebase | Public counterexample reproduced with controls. |
| F B2 | 0 | Surviving-parent case retained; converging queued-parent case removed | Selected lifecycle behavior holds. |
| G B2 | 1 | pgmpy import fails on missing numpy | Setup/availability failure; DummyData does not eliminate transitive imports. |

All eight actions passed gateway admission and produced durable tool receipts.
The gateway status was succeeded for all eight: it successfully executed the tool,
even when the program returned exit 1. Probe status was passed for four and failed
for four. Six reached their selected target behavior and passed their supplied
setup comparisons; the two import failures never reached setup checks or the
changed skeleton lines. There were no timeouts, truncated outputs or cleanup failures.
These are distinct counts, not an agent success rate.

H's model-selected programs independently reach the same endpoint-provenance
boundary as the earlier operator replay, now through the registered probe path.
B2 shows the controlled distinction directly: equal effective endpoints do not
justify equal rebasing when only one constructor received an explicit endpoint.
Actual ambient-client output violates the public preserve-without-explicit-endpoint
requirement. No operator correction was needed to reproduce this failure.

P is the opposite: the new serializer emits exactly the unsupported empty field
that the model expected. Its program exits successfully and its mode/name setup
checks pass. The public issue requires provider-profile provenance, which this
fresh plain profile lacks. This demonstrates why more probes, setup checks or
passing assertions alone cannot correct an erroneous expected outcome.

L can import its workspace package in the stdlib-only environment; a project
import alone was not proof of unavailable dependencies. Its nested lookup reports
that 'name' is unavailable in the record while the displayed top-level record keys
include 'name'. This exposes an ambiguous diagnosis of nested versus top-level
lookup, but the selected response did not establish a requirement for a different
nested-key diagnostic. Preserve that scope question; do not turn it into a new
benchmark failure or silently regrade the frozen selection experiment.

G had useful requirement-derived examples but neither generated program could
execute them in the available environment. The model had received the stdlib-only
dependency limitation. Thus there are two separable observations: the harness
does not supply the dependencies needed for these direct project probes, and the
selected actions do not accommodate that delivered restriction. This does not
establish whether a prepared dependency bundle or a model strategy change would
improve end-to-end task solving.

## Method and evidence integrity

Restored the exact P/H/F/L/G A1 candidate diffs at the pre-first-check seam from
prepared public sources in fresh external workspaces. Diff hashes match the actual
selection inputs. Original probe image digest, profile hash and prepared dependency
identity were revalidated for each case. No evaluator image, private task file,
reference patch or hidden test was used. No Docker startup, image pull/build or
dependency installation occurred.

Saved raw calls were parsed through the ordinary model-call parser, validated as
single run_probe actions, and executed by DevToolGateway and DockerProbeSandbox.
Action IDs, executable arguments, turn decisions and input hashes were preserved.
Each action has one started/finished pair in a separate dev-run-v1 hash chain.
This is a diagnostic tool replay, not a resumed agent trajectory: no next model
input was dispatched and no repair followed the observation.

All programs and source bindings were frozen before any execution. The registered
30-second per-program limit and a 600-second overall limit applied. Program exit 1
was retained as an observation, not retried; uncertain cleanup would stop the stage.
Both repeats of H/F/G used the same corresponding candidate snapshot hash. Candidate
diffs and original source journal/envelope bytes remained unchanged. No owned
containers remained after the run.

The initial v1 wrapper stopped before environment preparation or any probe when
its artifact writer rejected a plan path outside the writer's root. Its zero-run
failure record is retained. A new v2 directory corrected only that operator wrapper
storage root. No model program was edited or retried.

Evidence:

- Zero-execution preparation failure: C:/pt/analyses/selected-probe-execution-20260929-v1
- Execution script, frozen plan, eight receipts, summary, audit, content-addressed
  artifacts and hash-chained journals: C:/pt/analyses/selected-probe-execution-20260929-v2
- Prior immutable programs/grades: C:/pt/analyses/selection-execution-20260929-v1

Post-run audit verified all eight raw-call identities, source hashes, single-action
receipts, unchanged candidate hashes, cleanup confirmations and artifact/hash-chain
integrity. Documentation checks passed. Production runtime was unchanged; the full
runtime suite and mock solve were not rerun for this documentation-only change.
Isolated task acceptance and safety evaluation remain NOT_RUN; official=false.

## Current implication

Keep the baseline unchanged. Selection, execution readiness and expected-outcome
validity are different failure mechanisms: H now has usable failing evidence, G
is blocked before behavior, and P can pass a test that encodes its original mistake.
The five discriminating B selections from the prior review yielded two reproduced
counterexamples, one passing F control and two unexecuted G behaviors; this does
not revise their frozen selection grades or establish a repair advantage.

The next question is whether an agent uses valid failing observations to revise
its requirement-to-code mapping, versus merely making its chosen assertion pass.
Any repair comparison needs a separate fixed observation/input and funded model
authorization. Do not automatically install dependencies, retune the instruction,
or launch another panel from this diagnostic.
