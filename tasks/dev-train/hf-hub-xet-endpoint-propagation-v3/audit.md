# HF endpoint origin: public contract successor

Version 3 expands the existing `xet-endpoint-contract` to 100 cases. All 24 v2
cases retain their original inputs and expected outputs. The upstream regression,
issue, source SHA, scope, image, tool IDs and check count remain unchanged.
Versions 1 and 2 are immutable. Private files are copied opaquely, with only the
private task-version marker changed from 2 to 3.

The added cases cover host/scheme case and explicit HTTPS port 443 as equivalent
default-origin spellings, plus foreign port/scheme, lookalike host, network-relative
routes and the local-directory download path. This applies the issue's origin
requirement using [RFC 6454 sections 4-5](https://www.rfc-editor.org/rfc/rfc6454.html#section-4).
Both header and link carriers retain file hash and exact route/query/fragment.
Only preexisting metadata/HfApi/download entry points are exercised; no new parser
or direct metadata signature or particular repair algorithm is required.

The verdict checks every observation. Failure output gives one literal mismatch
and occurrence count per route class so all three reproduced classes fit bounded
agent feedback. The complete case definitions remain in the public command.

The exact registered commands ran on independent prepared-source clones:
BASE 68/100, unchanged v2 SUBMITTED 76/100; upstream 15/15 on both. Submitted
failures are eight each for host-case, scheme-case and default-port. HTTP HEAD
responses and file transfer are controlled boundaries around real project code;
there is no live-server, redirect or transfer claim.

Focused tests cover preserved cases/bytes, controls, incomplete observations and
fail/edit/recheck/finish. Actual Docker failure bytes reach both append-v1 and
segmented-v1 inputs. Separate public-fixture mock smoke reaches isolated fixture
acceptance; this does not establish HF acceptance or successful live repair.
No new provider/count call, repair candidate or private HF evaluation occurred.

Evidence: `C:\pt\analyses\hf-origin-public-contract-20260917-v1`.
All results are `official=false`; no held-out or general quality claim follows.
