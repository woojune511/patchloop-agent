# HF environment ownership: public contract successor

Version 5 retains all 196 v4 public cases and adds 96 environment cases.

The addition follows the public reproduction at
C:\pt\analyses\hf-origin-public-diagnostic-20260917-v1: with the explicit request
endpoint fixed, a custom HF_ENDPOINT changes the submitted parser's ownership
classification. Cases cover missed default-origin rebasing and preservation of
relative, already-custom, foreign and no-explicit-endpoint routes through existing
metadata and download APIs. No new parser or direct metadata signature is required.

Two fresh Python workers import the library with the configured environment.
A small launcher passes the public program as one source argument, so its children
run identical source without a second embedded copy. Each worker has a 20-second
timeout inside the existing 60-second registered check. Real imported configuration
is part of the public observations; missing or failed workers cannot yield a pass.

Issue, scope, source SHA, image, check IDs/order/timeouts and upstream command remain
unchanged. Private material is copied opaquely; only private.yaml's task version
changes. Earlier packages and submitted patches are immutable.

Validation: 30 focused tests and 168 related tests pass, with Ruff PASS. On separate
prepared-source clones, BASE passes 220/292 and the unchanged v4 submission 252/292;
upstream passes 15/15 for both. Four reproduced failure groups fit in 1335 characters
and reach both append-v1 and segmented-v1 actual inputs unchanged. Failure blocks
finish; action replay executes no new check; a synthetic edit permits recheck/finish.
Separate public-fixture mock runs reach isolated fixture acceptance under both policies.

No new HF repair, provider/count call or HF private evaluation is performed.
No live success, generalization or line-coverage claim is made. Subprocess cases
are outside launch-thread changed-line observation.
Records: C:\pt\analyses\hf-env-public-contract-20260917-v1.
