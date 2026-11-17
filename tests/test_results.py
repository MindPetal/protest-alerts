"""
Tests for results.py
"""

from protest_alerts import results


def test_fmt_date():
    assert results.fmt_date("Feb 2, 2024") == "02/02/2024"


def test_fmt_date_passes_through_unparseable_values():
    assert results.fmt_date("TBD") == "TBD"
    assert results.fmt_date("") == ""


def test_roundup_row():
    detail = {"company": "Acme Federal LLC", "filed_dt": "Feb 2, 2024", "due_dt": ""}

    assert results.roundup_row(detail) == ["Acme Federal LLC", "02/02/2024", ""]


def test_no_protest_summary():
    no_protest_results = [{"rfq_nm": "RFQ One"}, {"rfq_nm": "RFQ Two"}]

    assert (
        results.no_protest_summary(no_protest_results)
        == "**Tracked bids with no open protests:** RFQ One, RFQ Two"
    )
