# B first response: one entrypoint-pattern removal

Status: local preparation only; no new paid authorization or provider call.
This is a fresh one-request diagnostic, not a continuation of a closed allocation.

The [schema-family pair](../../docs/history/2026-10-20-b-schema-results.md) succeeded
without the new reproduction schema and failed with it. The
[field audit](../../docs/history/2026-10-20-b-schema-fields.md) found no contradictory
constraint or malformed structure. The entrypoint regex adds constructs absent
from the successful OFF schema and is the next discriminating candidate.

Use the same saved B first request, changing exactly one JSON path:
`/tools/4/parameters/properties/reproduction/anyOf/0/properties/entrypoint/pattern`.
Delete that keyword, leaving the reproduction object, fields, required list,
length bounds, B prose and every other input/request control unchanged. The host
`Intent` validator stays unchanged. The original pattern is
`^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$`.

- Task: `tasks/dev-train/current-dev20/13/public.yaml`, Astroid-1333, dev-train.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh; project credential file
  `C:/Users/geonj/Documents/PatchLoop/.env`.
- One `pattern-off` response; at most **one input count and one generation**.
- New cap **USD 0.15750000**, using the existing 60,000 input-token and 25,000
  output-token ceilings with uncached input admission. Review the same official
  USD 0.75 / 0.075 / 4.50 per-million rates on execution day. No output reduction.
- Reuse the frozen collector loop from `C:/pt/b-schema34/execute.py` with only its
  process-local order set to one condition and cap set to USD 0.1575. Its file and
  the original packet remain unchanged. Use the same pinned B runtime, zero SDK
  retries, request wait limits, 1,800-second deadline, usage validation and stops.
- No retries, alternate fields, additional conditions, continuation, tool action,
  Docker operation, evaluation or repair-quality claim. Transition rules, two
  references and the agent's other limits stay unchanged and are not exercised.

Compare with the saved ON response from allocation 34; do not spend another call
repeating its already observed UNKNOWN-billing failure. This is a historical
control, so time/routing effects remain unseparated. If pattern-off is healthy,
the pattern keyword or its interaction with the remaining schema is implicated;
the particular regex feature and provider internals are still unknown. If it
fails, pattern removal is insufficient; report its failure class and stop.
Never turn this one-call approval into an adaptive search through more variants.

Packet: `C:/pt/b-pattern36/`; fresh state: `C:/pt/b-pattern36-live/`.
Candidate hash: `sha256:e6875fc12fe6c8a859a71413b2921c868a008e30a67528ef26c02e358da774aa`.
The manifest binds the committed plan, source request/result, original frozen
collector and manifest, one-field change, new wrapper and five passing no-network
controls. A new exact human approval must bind this manifest and allocation before
the wrapper reads credentials. Closed allocations and their UNKNOWN bills remain
separate. All work is `official=false`, `claim_eligible=false`.
