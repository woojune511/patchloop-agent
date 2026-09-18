# Fixed-candidate counterexample discovery

## Question and boundary

Can the same model construct and execute a requirement-refuting input when explicitly
asked to review a fixed candidate? P11 supplied a useful public check at the outset;
that observation does not answer independent discovery. This diagnostic isolates that
question from patch repair and from voluntary verification during a solve.

`diagnostics.counterexample_discovery` implements `prepare`, `validate` and an offline
`rehearse`. `diagnostics.counterexample_discovery_rollout` now implements the bounded
collector, executable packet and read-only interrupted inspection. The sole live sample
is now **CLOSED / INFRASTRUCTURE_STOP**; the original design packet remains unchanged.
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
total cap $1.20. The executable packet binds the exact repository `.env`, pricing reviewed
on its execution date, implementation/runtime identity and invocation cap. Preparation
does not consume a sample. Execution exclusively creates its bound result directory;
once created, that directory cannot be retried, resumed or replaced by this packet.

History starts fresh. Subsequent calls append only this diagnostic's native results and
opaque continuation; there is no inherited segmented handoff. This is a separately
elicited discovery task, not an unchanged-policy A/B arm. The candidate remains fixed;
only read/search/probe and the report terminal are offered. No mutation, registered-check
execution, patch submission or hidden evaluation occurs in the discovery loop.

## Collector and recovery

The collector reuses `fresh_state_rollout.dispatch`, `episode_requests.DiagnosticClient`,
`DevToolGateway`, `DevCostLedger`, and the active native exchange builder. It does not
restore a source solve. The exact frozen two-message request starts a new history;
only this run's tool calls, public results and encrypted continuation are appended.
Provider reasoning summaries are excluded. Each counted request is stored in CAS.

Count immediately before dispatch; zero SDK retries. Admission reserves the full
25,000 output ceiling and rejects input above 60,000 tokens. Count/response/client
cleanup waits are bounded by the existing 30/300/5-second transport contract and the
remaining run deadline. Preflight has a separate 180-second bound. Source and dependency
identities, fixed patch, tool grammar and probe image/profile are checked before use.
The candidate is cloned locally and each probe uses the prepared public source/dependency
snapshot. The collector does not start Docker or pull/build an image.

Usage, cleanup, continuation and action uncertainty stop the sole sample. Known usage
survives a late response, and no late tool action is admitted. `inspect` verifies the
journal chain, execution identity, CAS artifacts and any published result without a
client, credential, workspace creation or another action. Interrupted results remain
interrupted; inspection never resumes or repairs them. Action receipts retain the
existing `action_id + input_hash` replay contract.

`report_discovery` binds its cited probe to the recorded program, candidate and receipt,
and records whether the requirement excerpt occurs in the public issue. A complete
receipt or zero exit does not prove a behavioral mismatch. `discovery_outcome` remains
null and `PUBLIC_REVIEW_REQUIRED` until the separate public-evidence review below.
Mock accounting is explicitly labeled simulated and reports zero live provider calls.

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

Executable evidence is `C:\pt\analyses\counterexample-discovery-executable-20260918-v1`.
`packet/plan.json` binds the untouched initial request and one fresh result directory.
The module's `prepare`/`validate` commands prepare and inspect that packet; `run` requires
both `--plan-root` and the exact `--plan-hash`. `inspect --root <result>` is read-only.
The frozen price review must match the UTC execution date. The live result directory was
consumed by the 2026-09-18 observation below; it cannot be reused.

Collector tests: 45 PASS/85.79s, covering native public feedback, terminal reporting,
full output reservation, call/tool/time/input bounds, invalid tools, source/packet/CAS
identity, uncertainty, cleanup and interrupted inspection. Shared regressions: 56 PASS/
75.72s, including the real response parser and both mock isolated evaluations. A durable
toy smoke records read -> simulated probe -> report with actual follow-up request bytes.
It proves collector plumbing only; it is not live discovery or real probe evidence.

## Closed live observation: 2026-09-18

User continuation authorized the exact one-sample/$1.20 packet. The original input and
all150 executable evidence files were verified before dispatch. Existing Docker/image
only; no startup, pull or build. Execution at runtime/collector commit `1dfa42e7` ends
with `REPORT_RECORDED` after 7 model/count calls, 11 reads/searches, 1 probe, 1 report.
The model reports `blocked`; public review records `INFRASTRUCTURE_STOP`, not a successful
discovery or a completed negative capability result. Task acceptance stays NOT_ASSESSED.

The first probe follows five inspection responses. It prints current `/workspace` module
paths and directly calls `_map_model_response`, then runs a deferred capability scenario
using `httpx.MockTransport`. SDK2.29.0 calls `asyncify(get_platform)` before transport;
the asyncio implementation uses `asyncio.to_thread`. Traceback reaches thread creation
and reports `RuntimeError: can't start new thread`. Probe code denies clone/clone3 and
uses pids_limit=2; the trace does not isolate which kernel restriction failed first.
The traceback exceeds 12,000 captured bytes (13,008 observed), yielding output_limit,
truncated=true and exit=null. Cleanup is confirmed; elapsed/container timeout flags are
false. The changed-line report is unavailable. None of this establishes a task defect.

Independently, the model's expected behavior is too broad. Its program creates a fresh
ordinary `OpenAIModelProfile` in field mode with `alt_reasoning`, without a supplied
DeepSeek profile, and expects an empty field. The original public task preserves ordinary
profiles unless given the requiring provider profile. The supplied patch itself shows
this unconditional field-mode insertion was newly added. The direct output matches the
model's unsupported expectation; its final report calls that behavior correct. Public
review records this expectation error without importing P11's check or rerunning a case.
The partial direct output cannot satisfy the frozen complete-receipt discovery criteria.

Recorded generation cost $0.2577015; cache-neutral $0.4425975; maximum input33355;
active loop183.065s/wall289.636s. Count/billing known for all7 responses; invoice/count
endpoint billing remains unverified. No global cost/input/call/time limit exit. Native
history is fresh append-only with no segment transitions. All7 actual requests and prior
public results pass the read-only delivery audit; exact candidate remains fixed, no
untracked files, no owned probe containers. No hidden evaluator read or execution.

Observation/public review: `C:\pt\analyses\counterexample-discovery-observation-20260918-v1`.
Raw execution: `C:\pt\analyses\counterexample-discovery-live-20260918-v1`.
The one sample and all unused funds are closed. Next work is provider-free
characterization and correction of SDK local initialization versus probe isolation;
retain the expectation error separately. This observation permits no automatic extra
candidate, paid judge, retry, resume, new prompt policy or runtime default adoption.

The report schema follows [OpenAI Docs strict function schemas](https://developers.openai.com/api/docs/guides/function-calling#strict-mode):
object properties are required, optional values are nullable, and extra properties are
forbidden. Schema preparation is not proof of live provider admission.
