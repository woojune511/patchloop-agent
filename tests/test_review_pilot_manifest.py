import copy

import pytest

from diagnostics.review_pilot_manifest import score_isort, score_opensandbox
from patchloop.errors import ContractError


def test_backend_gap_and_missing_matrix_are_distinct():
    names = ["helper_clean", "helper_symlink", "backend_clean_no_subpath",
             "backend_symlink_no_subpath", "sequence_symlink_no_subpath",
             "sequence_symlink_subpath_allowlist", "sequence_symlink_subpath_no_allowlist",
             "backend_after_interstage_swap"]
    rows = [{"case": n, "outcome": "ACCEPT" if "clean" in n else "REJECT"} for n in names]
    assert all(score_opensandbox(rows).values())
    rows[-1]["outcome"] = "ACCEPT"
    assert not score_opensandbox(rows)["backend_after_interstage_swap"]
    with pytest.raises(ContractError, match="incomplete"):
        score_opensandbox(rows[:-1])
    rows[-1]["outcome"] = "ERROR"
    with pytest.raises(ContractError, match="unclassified"):
        score_opensandbox(rows)


def test_comment_owner_and_idempotence_are_both_required():
    rows = []
    for profile in ("default", "black"):
        for comment in ("type: ignore[attr-defined]", "explanation"):
            for placement in ("opening", "member"):
                rows.append({"profile": profile, "comment": comment, "placement": placement,
                    "idempotent": True, "comment_lines": [0 if placement == "opening" else 1],
                    "output": (f"from x import (  # {comment}\n renamed_random_attribute,\n)"
                               if placement == "opening" else
                               f"from x import (\n renamed_random_attribute,  # {comment}\n)")})
    assert all(score_isort({"cases": rows}).values())
    damaged = copy.deepcopy(rows)
    damaged[-1]["output"] = "from x import (  # explanation\n renamed_random_attribute,\n)"
    damaged[-1]["comment_lines"] = [0]
    assert not all(score_isort({"cases": damaged}).values())
    rows[0]["idempotent"] = False
    assert not all(score_isort({"cases": rows}).values())
    with pytest.raises(ContractError, match="incomplete"):
        score_isort({"cases": rows[:-1]})
