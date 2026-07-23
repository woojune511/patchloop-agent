# Offline smoke replays

These JSONL files are recorded, deterministic model turns for exercising PatchLoop without a provider or
network. They contain public repository paths and submitted patch text, but no private task spec, hidden
assertion, reference-patch locator, or credential.

Replay sources are repository-relative and their SHA-256 hashes are frozen in each run manifest. They are
test fixtures only: memory construction and live model runs must not read them.
