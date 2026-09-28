# Pre-edit issue focus results

## Question and execution

Would repeating the original public issue before a mutation improve the condition
chosen for the repair? The [preregistered design](2026-09-28-pre-edit-issue-focus-design.md)
was committed as a62b4b2 before collection. A kept the historical input; B appended
the complete original issue without highlights, answers or new evidence. Native
encrypted continuation, plans, tools and observations remained unchanged and opaque.
Pydantic v1 PA1 call 5, HF Hub v5 HA1 call 9, Fromager v1 FA1 call 2; all dev-train.
The HF checkpoint follows earlier edits and public rechecks, unlike the first-edit
Pydantic/Fromager checkpoints. Cross-task differences therefore are not effect sizes.

Collected all 12 independent next responses, two per arm per task, with
gpt-5.4-2026-03-05 xhigh and 25K output. Twelve count calls preceded twelve
generations, zero retries or sampled tool executions. Cost $1.079303, active time
601.047 seconds, all billing known. The unused $6.920697 of the new $8 allocation
is closed; no continuation or replacement calls. official=false; acceptance and
safety evaluation NOT_RUN. No Docker, private evaluator, hidden tests or reference
patches were used.

## Arm-masked review

Anonymous public actions were graded and hash-journaled before reading the arm map.
Same investigator, not independent blind assessment; content can reveal treatment.
Counts below are response descriptions, not task success rates.

| Task | A: original input | B: original issue repeated |
| --- | --- | --- |
| Pydantic | 2 overbroad edits | 1 overbroad edit; 1 relevant profile inspection |
| HF Hub | 1 overbroad edit; 1 call-site search | 1 overbroad edit; 1 call-site search |
| Fromager | 2 scope-preserving proposed edits | 2 scope-preserving proposed edits |

Pydantic B repetition 2 explicitly distinguished a provider-carried opt-in from
generic field mode and requested profile definitions/validation to implement it.
That is a relevant change of investigation, not a completed repair. All three
Pydantic edits conditioned insertion on tool calls, absent thinking and field mode,
without the provider-carried opt-in required to preserve other profiles.

Both HF edits passed self.endpoint unconditionally. The public constructor resolves
an omitted endpoint to constants.ENDPOINT, so forwarding that value does not retain
the explicit-versus-omitted distinction. Both other responses searched additional
metadata call sites, still treating self.endpoint as explicit context. They explored
coverage, not the relevant endpoint-provenance condition. Merely mentioning that
endpoint-less callers should remain unchanged did not implement that constraint.

All four Fromager proposals queued children only after removal of backreferences
left no parents; surviving-parent references and exact-key/no-op behavior remained
in the proposed code. No global orphan sweep was introduced. This is static scope
review, not proof of behavioral correctness or benchmark acceptance.

All nine proposed replacements had one matching anchor in source whose bytes
matched the checkpoint hash, and the resulting full files parsed as Python.
Windows CRLF accounted for baseline Git-byte differences. Source was read only;
replacement and parsing occurred in memory. No generated code was executed, and
full tool admission/runtime safety was not evaluated. No output errors were reported.

## Interpretation and next decision

The original requirement was demonstrably delivered at all checkpoints. Repeating
it produced one relevant Pydantic investigation, no correct Pydantic/HF edit, and
no observed static control regression. This small selected sample does not justify
adopting issue repetition as a general harness improvement or claiming no effect.

The failure can be located behaviorally at requirement-to-edit-condition mapping:
generic field mode was substituted for provider opt-in, and a resolved endpoint
value for explicit endpoint provenance. It is not explained by a malformed edit
anchor or syntax in these responses. Environmental readiness and later execution
are outside this experiment. Existing plans, notes, earlier feedback and native
continuation were retained, so this does not isolate a model-only cause or assign
causal blame to a particular harness component.

Keep the baseline unchanged. If continuing causal diagnosis, distinguish inherited
plan commitment from condition derivation, changing one context component at a time
and retaining successful controls. First inspect whether the implicated condition
already appears in the active plan; do not automatically repeat this paid panel or
add task-specific repair hints. A subsequent behavioral experiment needs its own
fixed scope and allocation.

## Evidence and validation

- Live C:/pt/preeditfocus0928a, run_dev_sample_372226690cd5452d.
- Frozen packet C:/pt/analyses/pre-edit-focus-plan-20260928-v1/packet.json;
  sha256:f366f5377b427edd24c64ea22df7dcdca9d25da73cc6e8f90e8cce9f84daddca.
- External review C:/pt/analyses/pre-edit-focus-results-20260928-v1:
  anonymous-public.json, static-checks.json, pre-mapping-grades.json, report.json,
  and hash-chained run_dev_preeditfocusreview journal.
- Revalidated source/native projections after collection; all twelve actual request
  artifacts exactly matched the frozen requests and schedule. Prior source bytes
  remained unchanged. Review and unused allowance closure were journaled.
- Focused/shared collector tests: 43 passed. Ruff passed. Twelve fake dispatches
  matched the same fixed requests with no tools executed. No production runtime
  changes; full runtime suite and evaluator smoke not rerun for this diagnostic.
