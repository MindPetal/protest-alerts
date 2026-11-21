"""
Tests for search.py
"""

from datetime import date

import pytest

from protest_alerts import gao, search, slack, teams
from protest_alerts.config import RfqEntry, Settings, parse_rfq_list
from protest_alerts.results import gao_errors

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
            "text": "**Test RFQ Name** - 123456789 - [View on GAO](https://example.com)\n\n- Test Company | Bid Protest Sustained | Decided Feb 2, 2024 | [View decision](https://www.gao.gov/products/b-422681.5)\n\n- Test Company2 | Bid Protest Opened | Filed Feb 2, 2024 | Due May 2, 2024",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": "",
            "wrap": True,
        },
    ]

    mocker.patch(GAO_SEARCH, return_value=(protest_details, "https://example.com"))
    results, errors = search.process_search(parse_rfq_list(rfq_list), "daily")
    assert items == teams.format_results(results, "daily", errors)


def test_process_search_zero(mocker):
    rfq_list = "123456789:Test RFQ Name,098765432: Test RFQ Name 2"
    protest_details = []

    mocker.patch(GAO_SEARCH, return_value=(protest_details, "https://example.com"))
    results, errors = search.process_search(parse_rfq_list(rfq_list), "daily")
    assert [] == teams.format_results(results, "daily", errors)


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
    results, errors = search.process_search(parse_rfq_list(rfq_list), "roundup")
    assert items == teams.format_results(results, "roundup", errors)


def test_process_search_returns_results(mocker):
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

    results, errors = search.process_search(
        [RfqEntry("111", "RFQ One"), RfqEntry("222", "RFQ Two")], "daily"
    )

    assert errors == []
    assert [c.args[0] for c in mock_search.call_args_list] == ["111", "222"]
    assert all(c.kwargs == {"roundup": False} for c in mock_search.call_args_list)
    # Daily mode drops solicitations without protest updates
    assert results == [
        {
            "rfq_no": "111",
            "rfq_nm": "RFQ One",
            "protest_details": [protest],
            "url": "https://example.com/1",
        }
    ]


def settings(
    mode: str,
    rfqs: tuple[RfqEntry, ...] = (),
    ms_webhook_url: str = "https://webhook.example.com",
    slack_webhook_url: str = "",
) -> Settings:
    return Settings(
        rfqs=rfqs,
        ms_webhook_url=ms_webhook_url,
        mode=mode,
        slack_webhook_url=slack_webhook_url,
    )


def test_main_posts_results(mocker):
    results = [{"rfq_no": "111"}]
    mock_process = mocker.patch(
        "protest_alerts.search.process_search", return_value=(results, [])
    )
    mock_format = mocker.patch(
        "protest_alerts.teams.format_results", return_value=["items"]
    )
    mock_post = mocker.patch("protest_alerts.teams.post")
    rfqs = (RfqEntry("111", "RFQ One"),)

    search.main(settings("daily", rfqs))

    mock_process.assert_called_once_with(rfqs, "daily")
    mock_format.assert_called_once_with(results, "daily", [])
    mock_post.assert_called_once_with("https://webhook.example.com", ["items"])


def test_main_daily_no_updates(mocker):
    mocker.patch("protest_alerts.search.process_search", return_value=([], []))
    mock_post = mocker.patch("protest_alerts.teams.post")

    search.main(settings("daily"))

    mock_post.assert_not_called()


def test_main_roundup_posts_even_without_solicitations(mocker):
    # The roundup always posts its header and "No protests." summary
    mocker.patch("protest_alerts.search.process_search", return_value=([], []))
    mock_post = mocker.patch("protest_alerts.teams.post")

    search.main(settings("roundup"))

    mock_post.assert_called_once()
    assert "No protests." in [item["text"] for item in mock_post.call_args.args[1]]


SLACK_URL = "https://hooks.slack.com/services/T/B/X"


def test_main_posts_to_slack_only(mocker):
    results = [{"rfq_no": "111"}]
    mocker.patch("protest_alerts.search.process_search", return_value=(results, []))
    mock_teams_post = mocker.patch("protest_alerts.teams.post")
    mock_slack_format = mocker.patch(
        "protest_alerts.slack.format_results", return_value=["blocks"]
    )
    mock_slack_post = mocker.patch("protest_alerts.slack.post")

    search.main(settings("daily", ms_webhook_url="", slack_webhook_url=SLACK_URL))

    mock_teams_post.assert_not_called()
    mock_slack_format.assert_called_once_with(results, "daily", [])
    mock_slack_post.assert_called_once_with(SLACK_URL, ["blocks"])


def test_main_roundup_posts_to_both(mocker):
    mocker.patch("protest_alerts.search.process_search", return_value=([], []))
    mock_teams_post = mocker.patch("protest_alerts.teams.post")
    mock_slack_post = mocker.patch("protest_alerts.slack.post")

    search.main(settings("roundup", slack_webhook_url=SLACK_URL))

    mock_teams_post.assert_called_once()
    slack_texts = [block["text"] for block in mock_slack_post.call_args.args[1]]
    assert "No protests." in slack_texts


def test_main_daily_no_updates_skips_both(mocker):
    mocker.patch("protest_alerts.search.process_search", return_value=([], []))
    mock_teams_post = mocker.patch("protest_alerts.teams.post")
    mock_slack_post = mocker.patch("protest_alerts.slack.post")

    search.main(settings("daily", slack_webhook_url=SLACK_URL))

    mock_teams_post.assert_not_called()
    mock_slack_post.assert_not_called()


def test_main_teams_failure_still_posts_slack(mocker):
    mocker.patch(
        "protest_alerts.search.process_search", return_value=([{"rfq_no": "111"}], [])
    )
    mocker.patch("protest_alerts.teams.format_results", return_value=["items"])
    mocker.patch("protest_alerts.teams.post", side_effect=Exception("boom"))
    mocker.patch("protest_alerts.slack.format_results", return_value=["blocks"])
    mock_slack_post = mocker.patch("protest_alerts.slack.post")

    with pytest.raises(RuntimeError, match="Posting failed for: teams"):
        search.main(settings("daily", slack_webhook_url=SLACK_URL))

    mock_slack_post.assert_called_once_with(SLACK_URL, ["blocks"])


SEARCH_URL = gao.search_url("123456789")

GAO_ERROR = {
    "status": 404,
    "message": "Not Found",
    "url": SEARCH_URL,
}

GAO_ERROR_TEXT = (
    "⚠️ There was an error on GAO's website during the workflow run."
    f" HTTP 404 received: Not Found. [View on GAO]({SEARCH_URL})"
)


def test_process_search_continues_after_gao_error(mocker, caplog):
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
            gao.GaoHttpError(404),
            ([protest], "https://example.com/2"),
        ],
    )

    results, errors = search.process_search(
        [RfqEntry("123456789", "Test RFQ Name"), RfqEntry("222", "RFQ Two")],
        "daily",
    )

    assert mock_search.call_count == 2
    # View on GAO links to the failed search, even when a details page failed
    assert errors == [GAO_ERROR]
    assert [r["rfq_no"] for r in results] == ["222"]
    # Solicitation numbers are secrets, so never log them
    assert "HTTP 404 received: Not Found" in caplog.text
    assert "123456789" not in caplog.text


def test_main_posts_gao_error_then_fails(mocker):
    # A daily run with only a GAO error still posts, then fails the run
    mocker.patch("protest_alerts.search.process_search", return_value=([], [GAO_ERROR]))
    mock_teams_post = mocker.patch("protest_alerts.teams.post")
    mock_slack_post = mocker.patch("protest_alerts.slack.post")

    with pytest.raises(RuntimeError, match=r"^GAO returned HTTP errors: 404$"):
        search.main(settings("daily", slack_webhook_url=SLACK_URL))

    teams_texts = [item["text"] for item in mock_teams_post.call_args.args[1]]
    slack_texts = [block["text"] for block in mock_slack_post.call_args.args[1]]
    assert teams_texts[-1] == GAO_ERROR_TEXT
    assert slack_texts[-1] == GAO_ERROR_TEXT
    assert "Protest updates." in teams_texts[0]


def test_roundup_includes_gao_error(mocker):
    items = teams.format_results([], "roundup", [GAO_ERROR])
    blocks = slack.format_results([], "roundup", [GAO_ERROR])

    assert items[-1]["text"] == GAO_ERROR_TEXT
    assert blocks[-1]["text"] == GAO_ERROR_TEXT


def test_gao_errors_one_note_per_error():
    errors = [
        GAO_ERROR,
        {**GAO_ERROR, "status": 500, "message": "Internal Server Error"},
    ]

    assert gao_errors(errors) == (
        "⚠️ There was an error on GAO's website during the workflow run."
        f" HTTP 404 received: Not Found. [View on GAO]({SEARCH_URL})"
        "\n\n⚠️ There was an error on GAO's website during the workflow run."
        f" HTTP 500 received: Internal Server Error. [View on GAO]({SEARCH_URL})"
    )


def test_gao_http_error_message():
    error = gao.GaoHttpError(404)

    assert error.message == "Not Found"
    assert str(error) == "HTTP 404 received: Not Found"
    assert gao.GaoHttpError(599).message == "Unknown error"
