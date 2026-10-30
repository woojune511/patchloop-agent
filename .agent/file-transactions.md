# File transactions

Source: `patchloop/dev/file_edits.py`, `file_transaction.py`; tests: `test_file_edits.py`,
`test_file_transaction.py`, `test_file_edit_boundaries.py`, `test_test_restoration.py`,
`test_file_edit_source_rebinding.py`.

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

After a transaction, exact admitted before/after images define a conservative
changed interval per file. Previously observed unchanged prefix/suffix lines are
rebound to the current file hash; a bounded post-image targets the changed interval.
Retain at most eight rebound fragments for the whole batch, alongside each file's
existing bounded post-image. Normal source-output and retained-context limits still
apply, so durable observations may exceed what one model request can carry. Unread
unchanged ranges outside the post-image gain no source authority. Undo and pending
recovery use the same images and mapping; completed replay reuses its saved receipt.

Both mutation tools use the shared test validator. Restoring an existing test file
to its exact original HEAD bytes is permitted, including removing a run-added test
while moving it into a new module in the same batch. This does not require undoing
the source repair. The current source observation, path/scope, quota and transaction
checks still apply. Equivalent AST or whitespace-only changes are not exact restoration;
deleting an original test file remains forbidden.

Atomic here means one logical action under the execution lock: ordinary write
failure rolls back the whole batch; a crash may leave mixed before/after files.
Durable CAS images and baseline/candidate hashes permit only those known states
on replay. Unconfirmed rollback remains pending, never a settled failed action.
Legacy receipts without saved file images cannot be undone with this new tool.
