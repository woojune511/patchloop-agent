# Selected probe continuation boundary preparation

Date: 2026-09-28. `official=false`; no new provider calls or billed cost.
Follows [selected probe validation](2026-09-28-selected-closure-probe.md).
Implementation contract: [saved-response boundary](../../.agent/selected-probe-continuation.md).

## Preparation and result

Reused the actual settled B2 response, including encrypted continuation order,
public action ID/arguments and recorded usage. Restored the earlier completed
checkpoint into a new external branch, excluding the original later finish and
evaluation. The replayed count/dispatch/usage events are historical bookkeeping,
explicitly marked as such; no SDK network call or fresh reasoning generation ran.

The ordinary runner/gateway then executed the selected probe once. It reproduced
the objective TypeError at line 174, with matching program and snapshot hashes from
the separate operator replay. The tool completed with exit 1, no timeout, and
confirmed cleanup. No code changed and no evaluation ran.

Preparation stopped after constructing the next input but before counting it.
Delivery verification rebuilt the projected public state and checked native input
binding. The TypeError text, offending conversion and B2's open question are present.
No count or provider operation is pending and the branch has no terminal event.

Ordinary major-result segment rotation occurred. The actual encrypted B2 response
is preserved in the journal, but is not included in the next fresh segment. This is
the runtime's normal public-state handoff, not a claim of uninterrupted private
reasoning. The next input restores ordinary system wording: this was a first-input
ablation, not a persistent policy change.

Remaining inherited counters are 12 model calls, 60 tool actions and 1 mutation;
displayed active time is 3,567 seconds. Displayed cost is inherited/replayed
bookkeeping and authorizes no new spending. All earlier paid caps remain closed.

## Validation and preparation failures

The first preparation stopped before replay because the adapter lacked the ordinary
request builder. The second correctly rejected the changed system message against
the immutable inherited seed binding. The third uses the normal builder and a
scoped exact-deletion binding check; all later inputs use normal validation.
Failed roots v1/v2 are preserved and are not continuation candidates.

Five focused saved-response tests cover encrypted ordering/usage, wrong selected
action, unsettled billing, ciphertext corruption and pre-count capture signaling.
Together with 13 collector tests and 5 documentation checks, 23 tests passed under
two minutes. Ruff passed. Actual checkpoint replay plus public-state verification
provides integration evidence. No production runtime change was made; the prior
mock smoke and incomplete full-suite status are unchanged, not new test claims.

## Evidence and remaining work

- Prepared root: `C:/pt/analyses/selected-probe-continuation-20260928-v3`.
- `prepared-boundary.json` binds source response, boundary artifact and next request;
  `delivery-audit.json` records observed failure, counters and projection verification.
- Branch journal: `run_dev_33068b6e257f423a`; selected probe action sequence 471,
  prepared boundary sequence 475, before the next count.
- Next request: `sha256:a5227ee2f91c353a12cd30a5c099763e33d6c285eb0476d3e532fce1104bb36f`.
- Probe source: `sha256:36c28444dfbf8540f043a4743f9b49ca9fc3b5c78940f85cf6f4615eb596f319`.
- Probe snapshot: `sha256:93dacc1337c5281bf6ea2326842e4196b375fd5933bc7b8735c36d4a897fcaa3`.

The boundary is ready for a separately implemented/admitted funded fork, not a live
execution-ready manifest. That fork must preserve this failed tool result and
ordinary state, assign fresh cost authority without resetting work counters, and
measure repair, same-case recheck and submission separately. Agent repair and
benchmark acceptance remain NOT_RUN. No further paid invocation is authorized.
