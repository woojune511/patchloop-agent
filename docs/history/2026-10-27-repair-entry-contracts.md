# Repair entry contracts and public context continuation

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation and focused local validation
- Origin Date: 2026-10-27
- Verification Status: IMPLEMENTED / LOCALLY TESTED; live NOT_RUN
- Version Label: feedback-source-pair-v3
- Starting source: `8f4da439`; follows the closed v2 pilot, without rerunning it

The user authorized implementation of the proposed entry-point fixes. This change
does not execute a provider, read credentials, run the target in Docker, or prepare
a new paid allocation. Production defaults and the legacy one-edit profiles remain
unchanged. All generated local-test receipts live outside the repository.

## Problem and decision

The [v2 live pilot](2026-10-27-repair-cycle-results.md) never reached an edit.
R0 repeatedly inspected partial ranges before locating the function. R1 requested
a probe with null source, then requested two reads when the host allowed one.
The request still advertised `parallel_tool_calls=true`. Its undispatched
correction counted 68,124 input tokens against 60K. The last response introduced
an opaque reasoning item of 148,033 JSON characters; no new source output explains
that request growth. Those are byte observations, not a token decomposition or an
interpretation of the opaque content.

The selected problem is a mismatch between the host's actual capabilities and the
requests it asks the model to construct. It blocks diagnosis and a first repair,
so the existing post-edit feedback loop remains untested live. Fix these specific
contracts before buying more context or making a new model-capability claim.
Poor diagnosis, unnecessary exploration and ineffective edits remain plausible
causes after these fixes; a valid request is not evidence of a correct repair.

## Implemented contracts

1. The provider parallel flag now derives from the same opportunity policy that
   validates the returned read batch. A one-read opportunity advertises false;
   a multi-read opportunity advertises true. The host still validates every batch.
2. `recheck_original({})` selects the already registered public caller. Its frozen
   program, arguments and comparison come from the host. A new `run_probe` helper
   instead requires a non-null question and executable Python source, with no
   replay/purpose union. This diagnostic-only selector is not added to the general
   production registry. Its result distinguishes successful observation from
   supported/failed original behavior and from independent acceptance.
3. The saved-candidate gateway exposes the existing whole-file/page read API.
   Null bounds request a whole file when it fits or a bounded page with a
   continuation line. Explicit ranges remain available. Search remains a location
   tool; this change does not turn every search result into an entire file.
4. When a counted request exceeds 60K after history exists, the diagnostic builds
   a fresh public context and recounts it before cost admission and dispatch.
   It retains the exact current diff, bounded current observed source, current
   original-call result, last successful mutation, active correction, all action
   outcome identities, and global counters. The last complete/rejected tool batch
   and last successful mutation batch are quoted public observations. Prior native
   reasoning is not copied into the fresh request. Exact parent request/history
   and source/diff artifacts remain in content-addressed local storage.

The fresh context intentionally omits older tool-output bodies and opaque model
continuation; it is not a lossless conversational continuation. Omitted batch
counts and retained action identities are explicit. Source projection uses only
already observed current lines. The original feedback must match the current
diff, and an edited candidate cannot cross a boundary without that evidence.
Dangling tool calls cannot cross. Host/operator repair advice and private
evaluation do not enter the packet.

Each pending request may rebuild once. The new payload receives a distinct count
identity and a fresh cost admission. If it still exceeds the limit, it stops;
count/transport/billing uncertainty never triggers a fallback or retry. Prepared
and committed handoffs are separate journal events. Neither rebuilding nor an edit
renews normal responses, the single correction, tools, probes, edits, time or money.

## Resource and recovery consequences

Normal/correction responses remain 16/1, model tools 24, helper programs 2, edits 3,
output 40K/25K and input 60K. The optional original selection is limited to one
request and consumes one of the same 24 model-tool slots. It does not spend a
helper-program slot. Host original-call actions increase from at most four to five:
one clean baseline, one optional seed observation and three edited candidates.
Identical completed caller/diff receipts are reused; stale or unfinished actions
are rejected under the existing action-ID/input-hash contract.

Before dispatch, time reservation covers the required original-call execution;
the opportunity policy keeps a later edit and result-consumption response funded.
The model/intermediate-check 600-second deadline, final public/isolated 390-second
deadlines, row $1.20 and pair $2.40 ceilings remain configured as before. These
defaults are not fresh execution authorization. New runtime bindings include the
request-contract and context modules, and the preparation schema changes to v3.

## Local validation and limits

- Focused owner and legacy checks: **121 PASS in 63.49 seconds**, below two minutes.
  They cover whole/page reads, helper validation before execution, original
  selection before an edit and receipt reuse, matching parallel policy, ordinary
  and correction context boundaries, a second edit after failed original feedback,
  global counters, over-limit fresh context, uncertain count, stale original
  evidence, incomplete exchanges and legacy one-edit behavior.
- Ruff passed for `patchloop`, `tests` and `diagnostics`; `git diff --check` passed.
- Fast suite: **472 PASS in 106.60 seconds**, including isolated mock evaluation.
  This is not a full-suite result; earlier broader-suite failures remain outside
  this change and unresolved.
- Read-only implementation review found no additional defects. The initial
  integration check found that the custom original selector had been passed to
  the production schema registry; the final implementation excludes it there and
  appends its diagnostic schema locally. Final focused validation passed afterward.
- Receipts: `C:/pt/tmp/entryfocused27.xml`, `C:/pt/tmp/entryquick27.xml` and
  `C:/pt/tmp/entrydocs27.xml`. Scripted calls and synthetic count boundaries test
  host control flow. They do not measure live tokenization, provider acceptance,
  model reasoning or F0010 repair. External provider calls: zero.

The next live question remains whether the model reaches a justified first edit
and uses original-call failure feedback to revise it. A separately prepared,
bounded full-source trial can test uptake of these contracts. Several mechanisms
change together, so such a trial would not identify the isolated effect of a
larger source view, a smaller tool schema or a context boundary. No live quality,
acceptance or generalization gain is established by this implementation.
