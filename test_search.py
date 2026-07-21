"""
Tests for search.py
"""

from datetime import date

import pytest

import client
import search


@pytest.fixture
def api_client():
    api_config = search.client.Configuration()
    api_config.host = "https://www.example.com"

    return client.ApiClient(api_config)


def test_build_textblock():
    assert {
        "type": "TextBlock",
        "text": "Test",
        "wrap": True,
    } == search.build_textblock("Test")


def test_format_results():
    raw_results = [
        {
            "index": 1,
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
            "index": 2,
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
            "text": "**1. Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Sustained | Decided Feb 2, 2024 | [View decision](https://www.gao.gov/products/b-422681.5)\n\n- Test Company2 | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**2. Test RFQ Name2** - 987654321 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    assert items == search.format_results(raw_results)


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

    mocker.patch("search.search", return_value=(protest_details, "https://example.com"))
    assert items == search.process_search(rfq_list, "daily")


def test_process_search_zero(mocker):
    rfq_list = "123456789:Test RFQ Name,098765432: Test RFQ Name 2"
    protest_details = []

    mocker.patch("search.search", return_value=(protest_details, "https://example.com"))
    assert [] == search.process_search(rfq_list, "daily")


def test_format_results_closed_no_decision_url():
    """Closed protest with no published decision should not include a View decision link."""
    raw_results = [
        {
            "index": 1,
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

    items = search.format_results(raw_results)
    content = items[2]["text"]

    assert "View decision" not in content
    assert "Test Company | Bid Protest Dismissed | Decided Feb 2, 2024" in content


def test_format_results_decision_url_not_shared_across_protests():
    """When only the second of two closed protests has a decision URL,
    the first protest's output must not include any decision link."""
    raw_results = [
        {
            "index": 1,
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
            "index": 2,
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

    items = search.format_results(raw_results)
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


def test_teams_post(mocker):
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
            "text": "**1. Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Sustained | Decided Feb 2, 2024 | [View decision](https://example.com)\n\n- Test Company2 | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**2. Test RFQ Name2** - 987654321 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
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
    mock_teams_post = mocker.patch("search.client.MsApi.teams_post")
    search.teams_post(api_client, items)
    mock_teams_post.assert_called_once_with(body=body)


def test_format_roundup():
    """Roundup lists open protests per solicitation and shows a placeholder
    for solicitations with no open protests."""
    raw_results = [
        {
            "index": 1,
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
            "index": 2,
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
            "text": "**1. Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company, filed Feb 2, 2024, due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**2. Test RFQ Name2** - 987654321 - No open protests.",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    assert items == search.format_roundup(raw_results)


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
            "text": "**1. Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company, filed Feb 2, 2024, due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**2. Test RFQ Name2** - 987654321 - No open protests.",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    mocker.patch("search.search", side_effect=fake_search)
    assert items == search.process_search(rfq_list, "roundup")
