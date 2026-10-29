# File transactions

Source: `patchloop/dev/file_edits.py`, `file_transaction.py`; tests: `test_file_edits.py`,
`test_file_transaction.py`, `test_file_edit_boundaries.py`.

`edit_files` is a singleton alternative to `replace_text`, sharing its admission,
completion forecast and accepted-edit quota. Supply either 1–16 distinct `edits`
or `undo_action_id`, with the other null, plus hypothesis and expected_behavior.
Existing files retain exact observed anchors; old_text=null creates an absent file
with the complete UTF-8 new_text and occurrence=1. Each text is bounded at 20k
characters; the task's full-diff/file/path limits still apply. New regular files
join Git intent-to-add so reads, searches and submitted patches include them.
Task API constraints remain authoritative, including restrictions on new Python modules.

One accepted transaction or undo spends one edit and needs checks on its resulting
diff. Undo uses this run's successful mutation receipt and exact saved file images;
later unrelated edits survive, but changed target files cause rejection. Original
tests cannot be deleted or weakened. New additive test modules require declared
test roots; original-test isolated grading removes those modules temporarily.
No arbitrary delete/rename or unrestricted shell is exposed.

Atomic here means one logical action under the execution lock: ordinary write
failure rolls back the whole batch; a crash may leave mixed before/after files.
Durable CAS images and baseline/candidate hashes permit only those known states
on replay. Unconfirmed rollback remains pending, never a settled failed action.
Legacy receipts without saved file images cannot be undone with this new tool.
