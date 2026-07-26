from __future__ import annotations

import inspect
from pathlib import Path

from sqlglot import exp, parse_one
from sqlglot.dialects.duckdb import DuckDB
from sqlglot.generator import Generator
from sqlglot.parser import Parser

WORKSPACE = Path("/workspace")


def _assert_duckdb_round_trip(sql: str) -> None:
    parsed = parse_one(sql, dialect="duckdb")
    rendered = parsed.sql(dialect="duckdb")
    assert rendered == sql
    assert parse_one(rendered, dialect="duckdb") == parsed


def test_submitted_parser_generator_and_dialect_are_imported() -> None:
    sources = (
        inspect.getsourcefile(Parser._parse_lambda),
        inspect.getsourcefile(Generator._embed_ignore_nulls),
        inspect.getsourcefile(DuckDB.Generator),
    )
    for source in sources:
        resolved = Path(source or "").resolve()
        assert resolved.is_relative_to(WORKSPACE), (
            f"production symbol was imported from {resolved}, not {WORKSPACE}"
        )


def test_trailing_ignore_nulls_round_trips_for_ordered_first_value() -> None:
    _assert_duckdb_round_trip(
        "SELECT FIRST_VALUE(score ORDER BY sequence_id DESC IGNORE NULLS) "
        "OVER (PARTITION BY account_id ORDER BY sequence_id) FROM events"
    )


def test_trailing_respect_nulls_round_trips_for_ordered_last_value() -> None:
    _assert_duckdb_round_trip(
        "SELECT LAST_VALUE(price ORDER BY captured_at RESPECT NULLS) "
        "OVER (PARTITION BY symbol ORDER BY captured_at) FROM ticks"
    )


def test_multiple_order_terms_stay_inside_the_window_function_argument() -> None:
    sql = (
        "SELECT FIRST_VALUE(metric ORDER BY priority DESC, event_id IGNORE NULLS) "
        "OVER (PARTITION BY tenant_id ORDER BY event_id) FROM measurements"
    )
    parsed = parse_one(sql, dialect="duckdb")
    rendered = parsed.sql(dialect="duckdb")

    assert rendered == sql
    assert rendered.index("IGNORE NULLS") < rendered.index("OVER")
    assert "priority DESC, event_id IGNORE NULLS" in rendered


def test_prefix_ignore_nulls_is_canonicalized_after_argument_order_by() -> None:
    parsed = parse_one(
        "SELECT LAST_VALUE(price IGNORE NULLS ORDER BY captured_at DESC) "
        "OVER (ORDER BY captured_at) FROM ticks",
        dialect="duckdb",
    )
    assert parsed.sql(dialect="duckdb") == (
        "SELECT LAST_VALUE(price ORDER BY captured_at DESC IGNORE NULLS) "
        "OVER (ORDER BY captured_at) FROM ticks"
    )


def test_prefix_respect_nulls_is_canonicalized_after_argument_order_by() -> None:
    parsed = parse_one(
        "SELECT FIRST_VALUE(score RESPECT NULLS ORDER BY sequence_id) "
        "OVER (ORDER BY sequence_id) FROM events",
        dialect="duckdb",
    )
    assert parsed.sql(dialect="duckdb") == (
        "SELECT FIRST_VALUE(score ORDER BY sequence_id RESPECT NULLS) "
        "OVER (ORDER BY sequence_id) FROM events"
    )


def test_trailing_modifier_is_bound_to_the_function_not_the_window_order() -> None:
    parsed = parse_one(
        "SELECT LAST_VALUE(amount ORDER BY priority IGNORE NULLS) "
        "OVER (PARTITION BY customer_id ORDER BY observed_at) FROM payments",
        dialect="duckdb",
    )
    window = parsed.find(exp.Window)
    assert window is not None
    modifier = window.this.find(exp.IgnoreNulls)
    assert modifier is not None
    assert window.args["order"].find(exp.IgnoreNulls) is None


def test_nth_value_keeps_offset_and_trailing_ignore_nulls() -> None:
    _assert_duckdb_round_trip(
        "SELECT NTH_VALUE(score, 2 ORDER BY sequence_id IGNORE NULLS) "
        "OVER (PARTITION BY account_id ORDER BY sequence_id) FROM events"
    )


def test_lag_keeps_offset_default_and_trailing_ignore_nulls() -> None:
    _assert_duckdb_round_trip(
        "SELECT LAG(score, 2, 0 ORDER BY sequence_id IGNORE NULLS) "
        "OVER (PARTITION BY account_id ORDER BY sequence_id) FROM events"
    )


def test_lead_respect_nulls_round_trips_with_named_window() -> None:
    _assert_duckdb_round_trip(
        "SELECT LEAD(score ORDER BY sequence_id RESPECT NULLS) "
        "OVER account_window FROM events "
        "WINDOW account_window AS (PARTITION BY account_id ORDER BY sequence_id)"
    )


def test_complex_argument_order_and_outer_frame_remain_distinct() -> None:
    _assert_duckdb_round_trip(
        "SELECT FIRST_VALUE(score ORDER BY priority DESC, "
        "sequence_id ASC NULLS FIRST IGNORE NULLS) "
        "OVER (PARTITION BY account_id ORDER BY sequence_id "
        "ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) FROM events"
    )


def test_existing_unordered_ignore_nulls_form_is_unchanged() -> None:
    _assert_duckdb_round_trip(
        "SELECT LAST_VALUE(status IGNORE NULLS) "
        "OVER (PARTITION BY device_id ORDER BY observed_at) FROM readings"
    )


def test_ordered_window_function_without_null_modifier_is_unchanged() -> None:
    _assert_duckdb_round_trip(
        "SELECT FIRST_VALUE(score ORDER BY sequence_id DESC) "
        "OVER (PARTITION BY account_id ORDER BY sequence_id) FROM events"
    )


def test_bigquery_keeps_ignore_nulls_before_order_and_limit() -> None:
    sql = "SELECT ARRAY_AGG(score IGNORE NULLS ORDER BY rank DESC LIMIT 3) FROM results"
    parsed = parse_one(sql, dialect="bigquery")
    assert parsed.sql(dialect="bigquery") == sql


def test_bigquery_respect_nulls_order_is_not_changed_by_duckdb_policy() -> None:
    sql = "SELECT ARRAY_AGG(score RESPECT NULLS ORDER BY rank LIMIT 2) FROM results"
    parsed = parse_one(sql, dialect="bigquery")
    assert parsed.sql(dialect="bigquery") == sql
