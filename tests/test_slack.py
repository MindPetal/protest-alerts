"""
Tests for slack.py
"""

from datetime import date

import pytest

from protest_alerts import results, slack

TODAY = date.today().strftime("%A, %m/%d/%Y")

OPENED = {
    "company": "Acme Federal LLC",
    "status": "Opened",
    "type": "Bid Protest",
    "filed_dt": "Feb 2, 2024",
    "due_dt": "May 2, 2024",
}
CLOSED = {
    "company": "Beta Corp",
    "status": "Denied",
    "type": "Bid Protest",
    "decided_dt": "Feb 2, 2024",
    "decision_url": "/products/b-000001.1",
}


def test_format_daily():
    raw_results = [
        {
            "index": 1,
            "rfq_no": "123456789",
            "rfq_nm": "Test RFQ",
            "protest_details": [CLOSED, OPENED],
            "url": "https://example.com",
        }
    ]

    blocks = slack.format_results(raw_results, "daily")

    assert all(block["type"] == "markdown" for block in blocks)
    assert [block["text"] for block in blocks] == [
        f"**{TODAY}.** Protest updates.",
        "**1. Test RFQ** - 123456789 - [View on GAO](https://example.com)"
        "\n\n- Beta Corp | Bid Protest Denied | Decided Feb 2, 2024"
        " | [View decision](https://www.gao.gov/products/b-000001.1)"
        "\n\n- Acme Federal LLC | Bid Protest Opened | Filed Feb 2, 2024"
        " | Due May 2, 2024",
    ]


def test_format_daily_empty():
    assert slack.format_results([], "daily") == []


def test_format_roundup():
    raw_results = [
        {
            "index": 1,
            "rfq_no": "123",
            "rfq_nm": "RFQ One",
            "protest_details": [OPENED, {**OPENED, "company": "A | B Inc"}],
            "url": "https://example.com/1",
        },
        {
            "index": 2,
            "rfq_no": "456",
            "rfq_nm": "RFQ Two",
            "protest_details": [],
            "url": "https://example.com/2",
        },
    ]

    blocks = slack.format_results(raw_results, "roundup")

    assert [block["type"] for block in blocks] == [
        "markdown",
        "markdown",
        "table",
        "markdown",
    ]
    assert blocks[0]["text"] == (
        f"**{TODAY}.** Weekly roundup of open GAO protests for tracked bids."
    )
    assert blocks[1]["text"] == "**RFQ One** - [View on GAO](https://example.com/1)"
    assert table_texts(blocks[2]) == [
        ["Company", "Filed", "Due"],
        ["Acme Federal LLC", "02/02/2024", "05/02/2024"],
        ["A | B Inc", "02/02/2024", "05/02/2024"],
    ]
    # Header row is bold, like the Teams table
    assert blocks[2]["rows"][0][0]["elements"][0]["elements"] == [
        {"type": "text", "text": "Company", "style": {"bold": True}}
    ]
    assert blocks[3]["text"] == "**Tracked bids with no open protests:** RFQ Two"


def cell_text(cell: dict) -> str:
    return "".join(e["text"] for e in cell["elements"][0]["elements"])


def table_texts(table: dict) -> list[list[str]]:
    return [[cell_text(cell) for cell in row] for row in table["rows"]]


def test_build_tables_splits_and_repeats_header():
    rows = [["x" * 1_000, "02/02/2024", "05/02/2024"]] * 25

    tables = slack.build_tables(results.ROUNDUP_COLUMNS, rows)

    assert [len(t["rows"]) for t in tables] == [10, 10, 8]
    assert all(table_texts(t)[0] == ["Company", "Filed", "Due"] for t in tables)
    assert all(slack.table_chars(t) <= slack.MAX_TABLE_CHARS for t in tables)


def test_build_cell_empty_value():
    assert cell_text(slack.build_cell("")) == " "


def test_split_messages_keeps_bid_line_with_table():
    raw_results = [
        {
            "index": n,
            "rfq_no": str(n),
            "rfq_nm": f"RFQ {n}",
            "protest_details": [OPENED],
            "url": f"https://example.com/{n}",
        }
        for n in (1, 2, 3)
    ]

    messages = slack.split_messages(slack.format_results(raw_results, "roundup"))

    assert [[b["type"] for b in m] for m in messages] == [
        ["markdown", "markdown", "table"],
        ["markdown", "table"],
        ["markdown", "table"],
    ]
    assert [m[-2]["text"] for m in messages] == [
        f"**RFQ {n}** - [View on GAO](https://example.com/{n})" for n in (1, 2, 3)
    ]


def test_fallback_text_from_table():
    table = slack.build_tables(results.ROUNDUP_COLUMNS, [["Acme", "", ""]])[0]

    assert slack.fallback_text([table]) == "Company"


def test_format_roundup_no_open_protests():
    blocks = slack.format_results([], "roundup")

    assert [block["text"] for block in blocks] == [
        f"**{TODAY}.** Weekly roundup of open GAO protests for tracked bids.",
        results.NO_PROTESTS,
    ]


def block(text: str) -> dict:
    return {"type": "markdown", "text": text}


def test_split_messages():
    assert [len(m) for m in slack.split_messages([block("x")] * 60)] == [50, 10]
    assert [len(m) for m in slack.split_messages([block("x" * 7_000)] * 2)] == [1, 1]


class FakeResponse:
    def __init__(self, status: int, data: bytes = b"ok"):
        self.status = status
        self.data = data


def test_post(mocker):
    mock_request = mocker.patch(
        "urllib3.PoolManager.request", return_value=FakeResponse(200)
    )
    blocks = [block("**Monday, 11/16/2026.** Protest updates."), block("x")]

    slack.post("https://hooks.slack.com/services/T/B/X", blocks)

    args, kwargs = mock_request.call_args
    assert args == ("POST", "https://hooks.slack.com/services/T/B/X")
    assert kwargs["json"] == {
        "text": "Monday, 11/16/2026. Protest updates.",
        "blocks": blocks,
    }


def test_post_raises_on_error(mocker):
    mocker.patch(
        "urllib3.PoolManager.request",
        return_value=FakeResponse(410, b"channel_is_archived"),
    )

    with pytest.raises(slack.SlackPostError, match="410: channel_is_archived"):
        slack.post("https://hooks.slack.com/services/T/B/X", [block("x")])
