"""Build or validate the immutable R11 campaign correction index."""

from __future__ import annotations

import json

from patchloop.evals.heldout_ac_r11_campaign_evidence import (
    run_heldout_ac_r11_campaign_evidence,
)

if __name__ == "__main__":
    print(json.dumps(run_heldout_ac_r11_campaign_evidence(), indent=2))
