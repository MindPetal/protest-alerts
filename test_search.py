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
            "text": f'**{date.today().strftime("%A, %m/%d/%Y")}.** Protest updates.',
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**1. Test RFQ Name - Solicitation 123456789 - [View updates](https://example.com)**\n\n- Test Company **|** Bid Protest Sustained **|** Decided Feb 2, 2024 **|** [View decision](https://www.gao.gov/products/b-422681.5)\n\n- Test Company2 **|** Bid Protest Opened **|** Filed Feb 2, 2024 **|** Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**2. Test RFQ Name2 - Solicitation 987654321 - [View updates](https://example.com)**\n\n- Test Company **|** Bid Protest Opened **|** Filed Feb 2, 2024 **|** Due May 2, 2024",
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
            "text": f'**{date.today().strftime("%A, %m/%d/%Y")}.** Protest updates.',
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**1. Test RFQ Name - Solicitation 123456789 - [View updates](https://example.com)**\n\n- Test Company **|** Bid Protest Sustained **|** Decided Feb 2, 2024 **|** [View decision](https://www.gao.gov/products/b-422681.5)\n\n- Test Company2 **|** Bid Protest Opened **|** Filed Feb 2, 2024 **|** Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    mocker.patch("search.search", return_value=(protest_details, "https://example.com"))
    assert items == search.process_search(rfq_list)


def test_process_search_zero(mocker):
    rfq_list = "123456789:Test RFQ Name,098765432: Test RFQ Name 2"
    protest_details = []

    mocker.patch("search.search", return_value=(protest_details, "https://example.com"))
    assert [] == search.process_search(rfq_list)


def test_teams_post(mocker):
    items = [
        {
            "type": "TextBlock",
            "text": f'**{date.today().strftime("%A, %m/%d/%Y")}.** Protest updates.',
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**1. Test RFQ Name - Solicitation 123456789 - [View updates](https://example.com)**\n\n- Test Company **|** Bid Protest Sustained **|** Decided Feb 2, 2024 **|** [View decision](https://example.com)\n\n- Test Company2 **|** Bid Protest Opened **|** Filed Feb 2, 2024 **|** Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "**2. Test RFQ Name2 - Solicitation 987654321 - [View updates](https://example.com)**\n\n- Test Company **|** Bid Protest Opened **|** Filed Feb 2, 2024 **|** Due May 2, 2024",
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
