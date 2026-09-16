# HF endpoint paths: public contract successor

Version 4 retains all 100 version-3 cases exactly and adds 96 endpoint-path cases
to the existing `xet-endpoint-contract`. Check IDs/count/order, timeout, environment,
upstream regression, issue, scope, repository and pinned image remain unchanged.
Private files are copied opaquely with only the task-version marker updated.

## Public basis and coverage

The public issue requires preserving endpoint context and rebasing default-origin
refresh routes onto that endpoint. The pinned `hf_hub_url` and token URL builder
both preserve the complete endpoint before the resource path. Public execution of
the unchanged v3 submission reproduced loss of `/hub` and `/team%2Falpha/hub` in
the shared refresh-route builder. This does not reveal the private failure's cause.

New cases cross those two prefixes, header/link carriers and default, relative,
foreign and already-custom routes. Entry paths are no-explicit-endpoint metadata,
HfApi metadata, top-level cache/local downloads and HfApi cache/local downloads.
They use APIs present in the base repository. The diagnostic's new direct metadata
and parser parameters are not required. Passing controls remain verdict obligations.

The command checks every row's route, file hash, exact HEAD target and transfer
count. It reports a literal representative mismatch and count for each failing
class, plus the total. Controlled HEAD responses and a replaced transfer boundary
exercise real metadata propagation and destination handling; live servers,
redirects, authentication and transfers are outside this check's coverage.

## Validation

Both exact registered commands run on independent prepared-source clones. BASE
passes endpoint 144/196, the unchanged v3 submission 176/196; both pass upstream
15/15. The submission fails ten cases for each prefix class. Its complete 685-character
failure output reaches both append-v1 and segmented-v1 actual inputs, blocks finish,
replays without rerunning the check, and allows recheck after a synthetic edit.

Focused tests 23 PASS/8.322s, related regression 145 PASS/33.114s (JUnit timings),
Ruff PASS. Separate public-fixture mock smoke reaches edit/check/submit/isolated
fixture acceptance PASS under both policies, four audited inputs each; safety
NOT_RUN. These validate task coverage and workflow delivery, not a new HF repair.
Runtime is unchanged, so full runtime regression is not repeated. No provider/count
call, new repair candidate, private HF evaluation, source fetch or image start/pull/build.

Diagnostic: `C:\pt\analyses\hf-url-public-diagnostic-20260917-v1\result.md`.
Registration: `C:\pt\analyses\hf-path-public-contract-20260917-v1\result.md`.
All results are `official=false`.
