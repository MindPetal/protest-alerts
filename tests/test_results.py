"""
Tests for results.py
"""

from protest_alerts import results


def test_fmt_date():
    assert results.fmt_date("Feb 2, 2024") == "02/02/2024"


def test_fmt_date_passes_through_unparseable_values():
    assert results.fmt_date("TBD") == "TBD"
    assert results.fmt_date("") == ""
