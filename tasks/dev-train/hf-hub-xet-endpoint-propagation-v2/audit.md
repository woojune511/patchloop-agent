# HF endpoint propagation: public contract successor

Version 2 adds `xet-endpoint-contract` before the unchanged upstream regression.
The issue, source SHA, scope and image are unchanged. Version 1 stays immutable.
Private files are copied byte-for-byte, except the private version marker.

The new command uses only the public issue and pinned public project APIs.
Twenty-four cases cover direct metadata without an explicit endpoint, HfApi
configured for a custom endpoint with custom/default file URLs, and the download
metadata path. Both header/link carriers exercise default-origin, relative and
foreign-origin refresh routes; URL query/fragment and file hash must survive.

HTTP HEAD responses and the file-transfer boundary are controlled collaborators;
real metadata functions and the download metadata/cache path run in the pinned
image with no network. This does not test live servers, redirects or transfer.
No parser signature or particular repair implementation is required.

The exact command was executed once on the prepared base and once on the existing
H1 submission: BASE 18/24, SUBMITTED 20/24. The submission incorrectly rebases two
no-endpoint calls and misses two configured-client endpoint cases. Both versions
pass the unchanged upstream 15/15 regression. No new HF repair or private
evaluation is part of this validation; all results are official=false.

Evidence: `C:\pt\analyses\hf-endpoint-public-contract-20260916-v1`.
The original source, experiment and task bytes remain immutable. This version
improves development feedback, not a held-out or general quality result.
