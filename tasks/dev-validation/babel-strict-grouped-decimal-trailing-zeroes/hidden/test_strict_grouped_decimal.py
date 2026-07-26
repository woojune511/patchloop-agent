from __future__ import annotations

import inspect
from decimal import Decimal
from pathlib import Path

import pytest
from babel import numbers


def test_submitted_parse_decimal_is_imported() -> None:
    expected = Path("/workspace/babel/numbers.py").resolve()
    actual = Path(inspect.getsourcefile(numbers.parse_decimal) or "").resolve()
    assert actual == expected


def test_english_grouped_mixed_fraction_preserves_padding() -> None:
    parsed = numbers.parse_decimal("12,345.6700", locale="en_US", strict=True)
    assert parsed == Decimal("12345.6700")
    assert str(parsed) == "12345.6700"


def test_single_insignificant_zero_is_accepted() -> None:
    parsed = numbers.parse_decimal("54,321.870", locale="en_US", strict=True)
    assert parsed == Decimal("54321.870")
    assert str(parsed) == "54321.870"


def test_significant_zero_inside_fraction_is_not_removed() -> None:
    parsed = numbers.parse_decimal("12,345.6070", locale="en_US", strict=True)
    assert parsed == Decimal("12345.6070")
    assert str(parsed) == "12345.6070"


def test_negative_grouped_decimal_preserves_padding() -> None:
    parsed = numbers.parse_decimal("-12,345.6700", locale="en_US", strict=True)
    assert parsed == Decimal("-12345.6700")
    assert str(parsed) == "-12345.6700"


def test_comma_decimal_locale_accepts_insignificant_padding() -> None:
    parsed = numbers.parse_decimal("12.345,6700", locale="de_DE", strict=True)
    assert parsed == Decimal("12345.6700")
    assert str(parsed) == "12345.6700"


def test_indian_grouping_accepts_insignificant_padding() -> None:
    parsed = numbers.parse_decimal("12,34,567.8900", locale="en_IN", strict=True)
    assert parsed == Decimal("1234567.8900")
    assert str(parsed) == "1234567.8900"


def test_narrow_space_grouping_accepts_insignificant_padding() -> None:
    parsed = numbers.parse_decimal("12\u202f345,6700", locale="fr_FR", strict=True)
    assert parsed == Decimal("12345.6700")
    assert str(parsed) == "12345.6700"


def test_default_arabic_number_symbols_are_supported() -> None:
    parsed = numbers.parse_decimal(
        "7\u066c654\u066b3200",
        locale="ar_EG",
        strict=True,
        numbering_system="default",
    )
    assert parsed == Decimal("7654.3200")
    assert str(parsed) == "7654.3200"


def test_long_trailing_zero_run_preserves_scale() -> None:
    parsed = numbers.parse_decimal("19,876.54000", locale="en_US", strict=True)
    assert parsed == Decimal("19876.54000")
    assert str(parsed) == "19876.54000"


def test_all_zero_fraction_remains_accepted_with_scale() -> None:
    parsed = numbers.parse_decimal("12,345.0000", locale="en_US", strict=True)
    assert parsed == Decimal("12345.0000")
    assert str(parsed) == "12345.0000"


def test_ungrouped_decimal_behavior_is_unchanged() -> None:
    parsed = numbers.parse_decimal("12345.6700", locale="en_US", strict=True)
    assert parsed == Decimal("12345.6700")
    assert str(parsed) == "12345.6700"


def test_malformed_single_group_is_still_rejected_when_padded() -> None:
    with pytest.raises(numbers.NumberFormatError):
        numbers.parse_decimal("123,45.6700", locale="en_US", strict=True)


def test_wrong_locale_separators_are_still_rejected() -> None:
    with pytest.raises(numbers.NumberFormatError):
        numbers.parse_decimal("12.345,6700", locale="en_US", strict=True)


def test_multiple_decimal_symbols_are_still_rejected() -> None:
    with pytest.raises(numbers.NumberFormatError):
        numbers.parse_decimal("12,345.67.00", locale="en_US", strict=True)


def test_non_strict_malformed_grouping_remains_permissive() -> None:
    parsed = numbers.parse_decimal("1,23,45.6700", locale="en_US", strict=False)
    assert parsed == Decimal("12345.6700")
    assert str(parsed) == "12345.6700"
