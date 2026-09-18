# Fixed-candidate counterexample discovery

## Question and boundary

Can the same model construct and execute a requirement-refuting input when explicitly
asked to review a fixed candidate? P11 supplied a useful public check at the outset;
that observation does not answer independent discovery. This diagnostic isolates that
question from patch repair and from voluntary verification during a solve.

`diagnostics.counterexample_discovery` implements `prepare`, `validate` and an offline
`rehearse`. The model collector is **not implemented** and paid execution is **NOT_RUN**.
Preparation never instantiates a provider client or reads credentials. All records are
external, immutable files with a `dev-run-v1` preparation/rehearsal journal; `official=false`.
The published packet is the final write. An incomplete directory cannot be reused.

## Frozen input

The exact input consists of:

- The original `pydantic-ai-synthetic-tool-reasoning` public task, including its two
  existing check definitions. No historical check verdicts are supplied.
- The exact P10 public patch, hash
  `sha256:9e7a8e144e1bf385aef59bb916461748bf9c4bfa46a8a8efa94fa54d6bd233f9`.
- A generic discovery instruction, original read/search/probe schemas with `brief-v1`
  annotations, prepared public dependency capability, and `report_discovery`.

The builder accepts no historical context argument. P10 plans, reasoning, trace,
outcomes, P11 task/check/case/patch, evaluator material and operator diagnoses are absent.
Local artifact paths and preparation identifiers are kept in the operator packet.
The model sees the neutral candidate name and public source/task identity only.

The same `gpt-5.4-2026-03-05` / `medium` model and 25,000 output ceiling are proposed.
One fresh sample, up to 40 model calls, 100 tools, 1,800 seconds and 60,000 input tokens;
proposed total cap $1.20. This proposal is not a consumed execution grant or frozen price
review. A subsequent collector must bind the exact credential file, reviewed pricing,
its implementation identity and invocation cap before any count/generation call.

History starts fresh. Subsequent calls append only this diagnostic's native results and
opaque continuation; there is no inherited segmented handoff. This is a separately
elicited discovery task, not an unchanged-policy A/B arm. The candidate remains fixed;
only read/search/probe and the report terminal are offered. No mutation, registered-check
execution, patch submission or hidden evaluation occurs in the proposed discovery loop.

## Judgment

`report_discovery` can report a counterexample, no discovery, or a blockage. Reports are
claims to inspect, not an automatic verdict. A reproduced mismatch requires all of:

1. A literal public requirement and a justified expectation for the precise input.
2. A model-authored program bound to its recorded action, source and candidate hashes.
3. Execution of the current workspace implementation, with observations derived from
   that execution. Imports, printed assertions and line-entry hits alone are insufficient.
4. Complete actual/expected evidence of a behavioral contradiction. An import error,
   setup failure or nonzero exit alone is insufficient.
5. Complete receipts and confirmed cleanup, without unresolved execution uncertainty.

The public review checks those facts from recorded code and execution output. It does
not read hidden evaluator details, consult P11's case, run another candidate, or pay for
a judge. It records `REPRODUCED`, `NO_REPRODUCTION`, `CENSORED`, or `INFRASTRUCTURE_STOP`.
Call/probe counts and concise plans are secondary behavior evidence. Limits and setup
failures remain separate from a completed search without reproduction.

Success would justify inspecting why verification was not selected during earlier solves.
It would not prove that action selection is the unique cause: explicit instructions and
a fixed-candidate review change the task. Failure would leave requirement interpretation,
case design and execution obstacles to distinguish from the public trace. Neither result
changes runtime defaults or establishes general model capability from one selected patch.

## Preparation and validation

The external record is `C:\pt\analyses\counterexample-discovery-20260918-v1`.
`packet/request.json` contains the actual initial request bytes. `packet/protocol.json`
contains the predeclared judgment and stopping rules; `packet/packet.json` binds both.
Use `python -B -m diagnostics.counterexample_discovery validate --root <packet>` for
read-only reconstruction. `rehearse --root <packet> --output <fresh-external-root>` checks
dependency contents, clones prepared source independently, applies the exact candidate,
reads its hunk through `DevToolGateway`, and verifies idempotent read recovery. This does
not execute a model-authored probe or establish model capability.

Focused tests prohibit network/provider/Docker access and private sibling reads. They
cover input provenance, tampering, interrupted publication, exact independent workspaces,
dependency corruption and read recovery. Existing probe/dependency tests exercise mocked
execution, action identity, current-source delivery and isolated evaluation separately.
Runtime/default/task bytes stay unchanged; full-suite evidence belongs to that unchanged
runtime and is not a newly executed full regression.

The report schema follows [OpenAI Docs strict function schemas](https://developers.openai.com/api/docs/guides/function-calling#strict-mode):
object properties are required, optional values are nullable, and extra properties are
forbidden. Schema preparation is not proof of live provider admission.
