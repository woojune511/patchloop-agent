# Task audit: csv-final-record-flush

- Split: `dev-train`
- Failure pattern: buffered parser state is not finalized when input reaches EOF
- Expected source change: `mini_data_utils/chunkcsv.py`
- Base visible behavior: terminated records, chunk splits and quoted commas remain valid
- Private acceptance: one or more chunks ending with a valid record but no final newline
- Leakage control: hidden values and reference patch are evaluator-only and must not enter memory text
- Independence rule: this task does not reuse the multiline-CSV smoke API or its stream-based fix

Admission requires the no-op baseline to pass visible checks and fail hidden acceptance, the reference
patch to pass SCRR, and every known-bad patch to fail its predeclared boundary.
