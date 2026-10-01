# Pydantic empty field boundary: rejected before serialization

## Question and result

The [contract audit](2026-10-01-pydantic-evaluator-contract-audit.md) identified no
explicit empty configured field-name case in the hidden matrix. This follow-up
checks the public construction path on the clean base, reference repair and
saved PA1 patch before treating that absence as a runtime coverage defect.

All three reject field mode with an empty thinking-field name using UserError.
This holds both for a plain OpenAIModelProfile and a provider-derived profile
copied with dataclasses.replace. The error type/message match across all six
observations. Public profile construction calls __post_init__, whose field-mode
guard rejects false-like configured field names. This validation exists in the
base and is preserved by both repairs.

The initial proposed four-case serialization check stopped at the first profile
construction. That failed diagnostic is preserved; it did not execute serialization
or demonstrate a candidate defect. A separate frozen admission diagnostic then
tested both constructors on all three source variants. It did not bypass validation
through object mutation or manufacture an unreachable valid-profile scenario.

## Decision

Close this boundary without modifying the task, evaluator or agent. The earlier
audit's untested boundary is now qualified: ordinary public construction rejects
the configuration before serialization. No serialization PASS is claimed for it.
Deliberately mutating a profile after validation is outside this bounded check.
PA1's known overbroad behavior on valid profiles remains a separate demonstrated
failure; its correct rejection here does not rehabilitate the saved repair.

No new runtime fix or paid experiment follows from this result. Keep the original
audit and all historical verdicts intact; this follow-up supplies the correction
to the earlier suggestion that a normal empty-field serialization case was missing.

## Evidence and validation

External root: C:\pt\analyses\pydantic-empty-field-20261001-v1.
Journal: runs/run_dev_pydanticemptyfield.jsonl. Both diagnostic programs, frozen
questions/script hashes, initial rejection, six subsequent observations, Docker
commands and confirmed cleanup are retained. Source-only copies came from the
three prior calibrated workspaces; no private evaluator or reference patch was
mounted into the containers. The reference-labelled source is already patched.

Existing pinned image, network none, read-only root/source, 2 CPUs, 2 GiB,
256 PIDs, 60-second timeout. All admission runs exited 0; no image pull/build,
Docker startup, credentials or provider requests. No task/runtime code changed.
Documentation layout/link/size and whitespace checks validate the closeout;
runtime tests and mock smoke were not repeated for this documentation change.
