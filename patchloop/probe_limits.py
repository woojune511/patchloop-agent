"""Separate authored input, trusted observer and serialized execution budgets."""

SOURCE_LIMIT_CHARS = 8_000
SOURCE_LIMIT_BYTES = 4 * SOURCE_LIMIT_CHARS
OBSERVER_LIMIT_CHARS = 8_000
OBSERVER_LIMIT_BYTES = 4 * OBSERVER_LIMIT_CHARS

# repr(source) can use ten ASCII characters per Unicode code point (\Uxxxxxxxx),
# plus two quotes. The host prefix/suffix have their own UTF-8 allowance.
EXECUTION_LIMIT_CHARS = 10 * SOURCE_LIMIT_CHARS + 2 + OBSERVER_LIMIT_CHARS
EXECUTION_LIMIT_BYTES = 10 * SOURCE_LIMIT_CHARS + 2 + OBSERVER_LIMIT_BYTES
