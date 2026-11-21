"""
Tests for teams.py
"""

from datetime import date

import client
from protest_alerts import teams


def test_build_textblock():
    assert {
        "type": "TextBlock",
        "text": "Test",
        "wrap": True,
    } == teams.build_textblock("Test")


def test_format_daily():
    raw_results = [
        {
            "rfq_no": "123456789",
            "rfq_nm": "Test RFQ Name",
            "protest_details": [
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
            ],
            "url": "https://example.com",
        },
        {
            "rfq_no": "987654321",
            "rfq_nm": "Test RFQ Name2",
            "protest_details": [
                {
                    "company": "Test Company",
                    "status": "Opened",
                    "type": "Bid Protest",
                    "filed_dt": "Feb 2, 2024",
                    "due_dt": "May 2, 2024",
                }
            ],
            "url": "https://example.com",
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
            "text": "**Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Sustained | Decided Feb 2, 2024 | [View decision](https://www.gao.gov/products/b-422681.5)\n\n- Test Company2 | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**Test RFQ Name2** - 987654321 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    assert items == teams.format_daily(raw_results)


def test_format_daily_closed_no_decision_url():
    """Closed protest with no published decision should not include a View decision link."""
    raw_results = [
        {
            "rfq_no": "123456789",
            "rfq_nm": "Test RFQ Name",
            "protest_details": [
                {
                    "company": "Test Company",
                    "status": "Dismissed",
                    "decided_dt": "Feb 2, 2024",
                    "type": "Bid Protest",
                    # no decision_url
                },
            ],
            "url": "https://example.com",
        },
    ]

    items = teams.format_daily(raw_results)
    content = items[2]["text"]

    assert "View decision" not in content
    assert "Test Company | Bid Protest Dismissed | Decided Feb 2, 2024" in content


def test_format_daily_decision_url_not_shared_across_protests():
    """When only the second of two closed protests has a decision URL,
    the first protest's output must not include any decision link."""
    raw_results = [
        {
            "rfq_no": "111111111",
            "rfq_nm": "RFQ No Decision",
            "protest_details": [
                {
                    "company": "Company A",
                    "status": "Dismissed",
                    "decided_dt": "Feb 2, 2024",
                    "type": "Bid Protest",
                    # no decision_url — the bug caused this to get Company B's link
                },
            ],
            "url": "https://example.com/1",
        },
        {
            "rfq_no": "222222222",
            "rfq_nm": "RFQ With Decision",
            "protest_details": [
                {
                    "company": "Company B",
                    "status": "Sustained",
                    "decided_dt": "Feb 2, 2024",
                    "decision_url": "/products/b-999999.1",
                    "type": "Bid Protest",
                },
            ],
            "url": "https://example.com/2",
        },
    ]

    items = teams.format_daily(raw_results)
    # items layout: header, blank, rfq1_content, blank, rfq2_content, blank
    rfq1_content = items[2]["text"]
    rfq2_content = items[4]["text"]

    assert "View decision" not in rfq1_content, (
        "First protest (no decision) must not include a View decision link"
    )
    assert "View decision" in rfq2_content, (
        "Second protest (with decision) must include a View decision link"
    )
    assert "https://www.gao.gov/products/b-999999.1" in rfq2_content


def test_format_roundup():
    """Roundup lists open protests per solicitation and shows a placeholder
    for solicitations with no open protests."""
    raw_results = [
        {
            "rfq_no": "123456789",
            "rfq_nm": "Test RFQ Name",
            "protest_details": [
                {
                    "company": "Test Company",
                    "status": "Opened",
                    "type": "Bid Protest",
                    "filed_dt": "Feb 2, 2024",
                    "due_dt": "May 2, 2024",
                }
            ],
            "url": "https://example.com",
        },
        {
            "rfq_no": "987654321",
            "rfq_nm": "Test RFQ Name2",
            "protest_details": [],
            "url": "https://example.com",
        },
    ]

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

    assert items == teams.format_roundup(raw_results)


def test_format_roundup_multiple_protests_blank_bid():
    """A solicitation with multiple open protests renders one full-width bid
    header above a single table containing a row per protest."""
    raw_results = [
        {
            "rfq_no": "123456789",
            "rfq_nm": "Test RFQ Name",
            "protest_details": [
                {
                    "company": "Company A",
                    "status": "Opened",
                    "type": "Bid Protest",
                    "filed_dt": "Feb 2, 2024",
                    "due_dt": "May 2, 2024",
                },
                {
                    "company": "Company B",
                    "status": "Opened",
                    "type": "Bid Protest",
                    "filed_dt": "Feb 3, 2024",
                    "due_dt": "May 3, 2024",
                },
            ],
            "url": "https://example.com",
        },
    ]

    items = teams.format_roundup(raw_results)
    bid_header = next(
        item
        for item in items
        if item["type"] == "TextBlock" and item["text"].startswith("**Test RFQ Name**")
    )
    table = next(item for item in items if item["type"] == "Table")

    # Bid appears once as a full-width header, not inside the table.
    assert bid_header["text"] == (
        "**Test RFQ Name** - [View on GAO](https://example.com)"
    )

    # Header row plus one striped row per protest.
    assert table["rows"][1]["style"] == "default"
    assert table["rows"][2]["style"] == "emphasis"
    assert table["rows"][1]["cells"][0]["items"][0]["text"] == "Company A"
    assert table["rows"][2]["cells"][0]["items"][0]["text"] == "Company B"
    assert table["rows"][1]["cells"][1]["items"][0]["text"] == "02/02/2024"
    assert table["rows"][2]["cells"][2]["items"][0]["text"] == "05/03/2024"


def test_format_roundup_no_open_protests():
    """When no tracked bid has an open protest, a 'No protests.' line appears
    below the header, above the no-open-protests list."""
    raw_results = [
        {
            "rfq_no": "123456789",
            "rfq_nm": "Test RFQ Name",
            "protest_details": [],
            "url": "https://example.com",
        },
        {
            "rfq_no": "987654321",
            "rfq_nm": "Test RFQ Name2",
            "protest_details": [],
            "url": "https://example.com",
        },
    ]

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
            "text": "No protests.",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**Tracked bids with no open protests:** Test RFQ Name, Test RFQ Name2",
            "wrap": True,
        },
    ]

    assert items == teams.format_roundup(raw_results)


def test_post(mocker):
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
            "text": "**Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Sustained | Decided Feb 2, 2024 | [View decision](https://example.com)\n\n- Test Company2 | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**Test RFQ Name2** - 987654321 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    body = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.0",
                    "body": [{"type": "Container", "items": items}],
                    "msteams": {"width": "Full"},
                },
            }
        ],
    }
    mock_teams_post = mocker.patch.object(client.MsApi, "teams_post", autospec=True)
    teams.post("https://webhook.example.com", items)
    mock_teams_post.assert_called_once()
    api_instance = mock_teams_post.call_args.args[0]
    assert api_instance.api_client.configuration.host == "https://webhook.example.com"
    assert mock_teams_post.call_args.kwargs == {"body": body}


def test_format_results_dispatches_on_mode():
    raw_results = [
        {
            "rfq_no": "123456789",
            "rfq_nm": "Test RFQ Name",
            "protest_details": [],
            "url": "https://example.com",
        },
    ]

    assert teams.format_results(raw_results, "daily") == teams.format_daily(raw_results)
    assert teams.format_results(raw_results, "roundup") == teams.format_roundup(
        raw_results
    )
