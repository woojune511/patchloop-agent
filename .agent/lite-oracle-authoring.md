# Public-output predicate authoring diagnostic

Status: CLOSED after one approved response. The verbatim quote was invalid;
report NOT_ASSESSABLE, generated-predicate evaluation NOT_RUN. See the
[outcome](../docs/history/2026-10-03-public-predicate-result.md).
The scope below records the frozen plan and authorizes no further dispatch.

## Question and evidence

The [SQLFluff final-verification audit](../docs/history/2026-10-02-lite-final-verification-audit.md)
found that 1733's public probe rejected the original nine-space symptom but accepted
a five-space final output, although the public issue explicitly expects eight spaces.
The final model had the public requirement, probe tool and remaining resources. No
runtime recheck defect was established. The earlier frozen-expectation diagnostic
also showed that freezing a model expectation does not make it semantically correct.

Can the selected mini model translate this explicit public requirement into a useful
output predicate when asked directly, before seeing any implementation output?
This separates a narrow authoring capability from choosing when to verify during a
repair. Failure may reflect interpretation or predicate construction; success would
leave autonomous selection, real formatter invocation and repair ability unresolved.
There is no causal comparison or prompt/default adoption decision in this allocation.

## Frozen scope

- Registered task: `swebench-lite-dev-sqlfluff-sqlfluff-1733`, `dev-train`.
- One independent response, `gpt-5.4-mini-2026-03-17`, `xhigh`, 25,000 output ceiling.
- Project only the complete public issue and task ID, plus a generic request for
  `accepts(actual: str) -> bool`, a verbatim requirement quote and limitations.
- Do not supply old trajectories, candidate outputs, diagnoses, grading controls,
  reference patches, hidden tests or private evaluator details to the model.
- No repository tool execution or patch generation. The function call is a response
  artifact, frozen before operator grading; it is not executed by the model adapter.
- Credential: `C:/Users/geonj/Documents/PatchLoop/.env`. Invocation cap USD 0.20.
  Maximum one input count and one generation; input ceiling 10,000 tokens. At the
  [reviewed standard price](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
  the full input/output reservation is at most USD 0.12; the cap is not expected spend.
- Both Ubuntu and Windows `fast-dev-head` jobs must succeed at the frozen PR #21 head.
  Local head, runtime/task/request/driver hashes and existing sandbox image must match.
- Zero retries, corrections, continuation or resume. Count/transport/billing uncertainty
  stops the allocation. A malformed response is NOT_ASSESSABLE, not an extra call.
- No image downloads/builds, fresh solves, benchmark reruns, hidden evaluation or merge.

## Operator grading

The fixed panel is withheld from model input: public expected output must be accepted;
the original nine-space output, five-space output and output missing `one_more` must
be rejected. These are operator-authored public-behavior controls, not benchmark
hidden tests. No corrected predicate is fed back to the model.

Execute the authored code only with the existing Docker probe sandbox on a neutral
public workspace. No host execution, task checkout, credential mount or network.
Require four Boolean results; exceptions, invalid output, timeout, truncation or
cleanup failure remain explicit and do not count as rejection of incorrect behavior.
All four classifications plus a manual review against the public requirement are
necessary for a useful narrow result. A constant answer or panel-aware shortcut does
not establish a valid predicate. Four examples cannot establish exhaustive coverage.

Calibration uses three operator-written predicates: exact comparison distinguishes
all four outputs; the old symptom-only comparison misses the five-space and missing
field cases; constant true misses every negative. This is grading-tool evidence,
not evidence that an agent can author the predicate.

## Execution and evidence

External evidence: `C:/pt/analyses/lite-oracle-authoring-20261002-v1`.
`driver.py prepare` freezes `request.json`, `packet.json`, implementation hashes and
an append-only journal. `driver.py validate` is provider-free. Following a new exact
human grant and both CI successes, `driver.py collect` exclusively claims
`C:/pt/loa1live01` and uses the existing one-response `decision_sampler` engine.
`judge.py grade` evaluates the settled valid artifact once and requires the frozen
packet, collection identity and sandbox profile. Interrupted operations are inspect-only.

Provider-free preparation covers real isolated calibration, request/control tamper,
input limits, one-call mocks, no approval, no restart, malformed output and uncertainty
stops. The runtime and task contracts are unchanged. Keep the SQL3 original 0/3 and
dev20 10/20 records unchanged. Report model authorship, control discrimination,
semantic review, cost/time and unexecuted work separately. Every result is
`official=false`, development-exposed and claim-ineligible; no automatic paid follow-up.
