"""
Tests for search.py
"""

from datetime import date

from protest_alerts import search, teams
from protest_alerts.config import RfqEntry, Settings, parse_rfq_list

GAO_SEARCH = "protest_alerts.gao.search"


def test_process_search_protest_results(mocker):
    rfq_list = "123456789:Test RFQ Name"
    protest_details = [
        {
            "company": "Test Company",
            "status": "Sustained",
            "decided_dt": "Feb 2, 2024",
            "decision_url": "/products/b-422681.5",
            "type": "Bid Protest",
        },
        {
            "company": "Test Company2",
            "status": "Opened",
            "type": "Bid Protest",
            "filed_dt": "Feb 2, 2024",
            "due_dt": "May 2, 2024",
        },
    ]

    items = [
        {
            "type": "TextBlock",
            "text": f"**{date.today().strftime('%A, %m/%d/%Y')}.** Protest updates.",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**1. Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Sustained | Decided Feb 2, 2024 | [View decision](https://www.gao.gov/products/b-422681.5)\n\n- Test Company2 | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    mocker.patch(GAO_SEARCH, return_value=(protest_details, "https://example.com"))
    assert items == teams.format_results(
        search.process_search(parse_rfq_list(rfq_list), "daily"), "daily"
    )


def test_process_search_zero(mocker):
    rfq_list = "123456789:Test RFQ Name,098765432: Test RFQ Name 2"
    protest_details = []

    mocker.patch(GAO_SEARCH, return_value=(protest_details, "https://example.com"))
    assert [] == teams.format_results(
        search.process_search(parse_rfq_list(rfq_list), "daily"), "daily"
    )


def test_process_roundup(mocker):
    """Every tracked solicitation is included, even with no open protests."""
    rfq_list = "123456789:Test RFQ Name,987654321:Test RFQ Name2"

    def fake_search(rfq_no, yday, roundup=False):
        if rfq_no == "123456789":
            return (
                [
                    {
                        "company": "Test Company",
                        "status": "Opened",
                        "type": "Bid Protest",
                        "filed_dt": "Feb 2, 2024",
                        "due_dt": "May 2, 2024",
                    }
                ],
                "https://example.com",
            )
        return ([], "https://example.com")

    items = [
        {
            "type": "TextBlock",
            "text": f"**{date.today().strftime('%A, %m/%d/%Y')}.** Weekly roundup of open GAO protests for tracked bids.",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**Test RFQ Name** - [View on GAO](https://example.com)",
            "wrap": True,
        },
        {
            "type": "Table",
            "columns": [{"width": 2}, {"width": 1}, {"width": 1}],
            "firstRowAsHeaders": True,
            "gridStyle": "default",
            "rows": [
                {
                    "type": "TableRow",
                    "style": "accent",
                    "cells": [
                        {
                            "type": "TableCell",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "**Company**",
                                    "wrap": True,
                                }
                            ],
                        },
                        {
                            "type": "TableCell",
                            "items": [
                                {"type": "TextBlock", "text": "**Filed**", "wrap": True}
                            ],
                        },
                        {
                            "type": "TableCell",
                            "items": [
                                {"type": "TextBlock", "text": "**Due**", "wrap": True}
                            ],
                        },
                    ],
                },
                {
                    "type": "TableRow",
                    "style": "default",
                    "cells": [
                        {
                            "type": "TableCell",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "Test Company",
                                    "wrap": True,
                                }
                            ],
                        },
                        {
                            "type": "TableCell",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "02/02/2024",
                                    "wrap": True,
                                }
                            ],
                        },
                        {
                            "type": "TableCell",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "05/02/2024",
                                    "wrap": True,
                                }
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**Tracked bids with no open protests:** Test RFQ Name2",
            "wrap": True,
        },
    ]

    mocker.patch(GAO_SEARCH, side_effect=fake_search)
    assert items == teams.format_results(
        search.process_search(parse_rfq_list(rfq_list), "roundup"), "roundup"
    )


def test_process_search_returns_numbered_results(mocker):
    protest = {
        "company": "Test Company",
        "status": "Opened",
        "type": "Bid Protest",
        "filed_dt": "Feb 2, 2024",
        "due_dt": "May 2, 2024",
    }
    mock_search = mocker.patch(
        GAO_SEARCH,
        side_effect=[
            ([protest], "https://example.com/1"),
            ([], "https://example.com/2"),
        ],
    )

    results = search.process_search(
        [RfqEntry("111", "RFQ One"), RfqEntry("222", "RFQ Two")], "daily"
    )

    assert [c.args[0] for c in mock_search.call_args_list] == ["111", "222"]
    assert all(c.kwargs == {"roundup": False} for c in mock_search.call_args_list)
    # Daily mode drops solicitations without protest updates
    assert results == [
        {
            "rfq_no": "111",
            "rfq_nm": "RFQ One",
            "protest_details": [protest],
            "url": "https://example.com/1",
            "index": 1,
        }
    ]


def settings(mode: str, rfqs: tuple[RfqEntry, ...] = ()) -> Settings:
    return Settings(rfqs=rfqs, ms_webhook_url="https://webhook.example.com", mode=mode)


def test_main_posts_results(mocker):
    results = [{"index": 1}]
    mock_process = mocker.patch(
        "protest_alerts.search.process_search", return_value=results
    )
    mock_format = mocker.patch(
        "protest_alerts.teams.format_results", return_value=["items"]
    )
    mock_post = mocker.patch("protest_alerts.teams.post")
    rfqs = (RfqEntry("111", "RFQ One"),)

    search.main(settings("daily", rfqs))

    mock_process.assert_called_once_with(rfqs, "daily")
    mock_format.assert_called_once_with(results, "daily")
    mock_post.assert_called_once_with("https://webhook.example.com", ["items"])


def test_main_daily_no_updates(mocker):
    mocker.patch("protest_alerts.search.process_search", return_value=[])
    mock_post = mocker.patch("protest_alerts.teams.post")

    search.main(settings("daily"))

    mock_post.assert_not_called()


def test_main_roundup_posts_even_without_solicitations(mocker):
    # The roundup always posts its header and "No protests." summary
    mocker.patch("protest_alerts.search.process_search", return_value=[])
    mock_post = mocker.patch("protest_alerts.teams.post")

    search.main(settings("roundup"))

    mock_post.assert_called_once()
    assert "No protests." in [item["text"] for item in mock_post.call_args.args[1]]
