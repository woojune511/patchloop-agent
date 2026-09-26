# Separate current guidance from accumulated history

Date: 2026-09-26. Documentation change only; no runtime or experiment change.

## Problem and hypothesis

Current status and the internal guide had accumulated 885,996 and 539,319 bytes.
They mixed current priorities/contracts with old results and superseded next steps.
Reading those documents wholesale exposed much more material than current work
needed and made the authority of historical instructions ambiguous. Actual token
use or an agent decision failure caused by this structure was not measured.

The intervention is a short replaceable current snapshot, current contract/operation
guidance, and historical records retrieved only for a specific evidence question.

## Change and preservation

Five originals were copied byte-for-byte into
[the pre-split snapshot directory](2026-09-26-context-split/manifest.json) before editing.
SHA-256, byte counts, and original paths are retained. Local Git attributes disable
text normalization for those snapshots so checkout line endings cannot change hashes.
Existing `reports/`, `experiments/`, and `docs/archive/` were unchanged.

| Active document | Before bytes | After bytes |
| --- | ---: | ---: |
| Current status | 885,996 | 4,762 |
| Internal guide | 539,319 | 10,875 |
| Evidence | 81,972 | 3,891 |
| Operations | 137,656 | 10,856 |
| Product | 30,566 | 7,002 |

AGENTS and the docs index now distinguish current authority from historical lookup.
Current status is updated by replacement; completed investigations are recorded once
in history. Reading or searching all historical material is not a default startup step.
Current-document byte limits prevent unchecked growth, and snapshot hash checks guard
the migration's retained bytes. These are documentation checks, not runtime gates.

## Validation and limits

Documentation tests: 5 PASS in 0.12 seconds, covering current layout/discovery, byte
limits, active file links, and snapshot integrity. Ruff PASS; active-document
`git diff --check` PASS. Current contracts were cross-checked against relevant public
source by focused review. The full runtime suite, mock smoke, live provider and
Docker execution were NOT_RUN because runtime behavior did not change.

This establishes a smaller current reading surface and retained original records.
It does not establish billed-token savings, model latency, or improved task accuracy.
If context problems persist, inspect the actual documents and passages being read
before attributing them to memory or adding another mechanism.
