from types import SimpleNamespace

import pytest

from diagnostics import review_integrated_execution as integrated
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError


@pytest.mark.parametrize("tampered", [False, True])
def test_inherited_probe_receipts_are_not_current_execution(tmp_path, monkeypatch, tampered):
    journal = DevJournal(tmp_path, "run_dev_lineagefixture")
    journal.append("old_probe", {})
    journal.append("diagnostic_checkpoint_fork", {"source_journal_hash": "parent"})
    journal.append("new_probe", {})
    branch = SimpleNamespace(journal=journal, inherited_events=1,
                             parent_journal_hash="changed" if tampered else "parent")
    observed = []

    def receipts(view, store, run_id):
        kinds = [e["event_type"] for e in view.events()]
        observed.append(kinds)
        return []

    monkeypatch.setattr(integrated.runner, "_probe_evidence", receipts)
    with integrated.current_receipts(branch):
        if tampered:
            with pytest.raises(ContractError, match="lineage changed"):
                integrated.runner._probe_evidence(journal, None, journal.run_id)
            assert not observed
        else:
            integrated.runner._probe_evidence(journal, None, journal.run_id)
            assert observed == [["old_probe"], ["diagnostic_checkpoint_fork", "new_probe"]]
            lineage = journal.events()[-1]["payload"]
            assert lineage["historical_receipts_are_current_execution"] is False
