"""
Build Slack Block Kit messages and post them to a Slack incoming webhook.

Each chat destination gets its own module with the same interface:
format_results(results, mode) -> payload items, and post(webhook_url, items).
"""

import re
import time

import certifi
import urllib3

from protest_alerts import results

# Slack limits per message: 50 blocks, 12,000 characters across all markdown
# blocks, and 10,000 characters across all table cells. Tables also allow at
# most 100 rows.
MAX_BLOCKS = 50
MAX_MARKDOWN_CHARS = 12_000
MAX_TABLE_CHARS = 10_000
MAX_TABLE_ROWS = 100

# One table per message is always accepted. Raise this to group several
# tables into one message if your workspace allows it.
MAX_TABLES_PER_MESSAGE = 1

# **bold** or [text](url) in the shared Markdown text
MARKDOWN_TOKEN = re.compile(r"\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)")


class SlackPostError(Exception):
    pass


def build_markdown(text: str) -> dict:
    # Build a markdown block, which renders standard Markdown (**bold**,
    # [text](url), - lists)
    if len(text) > MAX_MARKDOWN_CHARS:
        text = text[: MAX_MARKDOWN_CHARS - 1] + "…"

    return {"type": "markdown", "text": text}


def build_cell(markdown: str) -> dict:
    # Build a rich text table cell from Markdown, keeping **bold** and
    # [text](url) links
    elements: list[dict] = []
    position = 0

    for match in MARKDOWN_TOKEN.finditer(markdown):
        if match.start() > position:
            elements.append(
                {"type": "text", "text": markdown[position : match.start()]}
            )

        bold, link_text, url = match.groups()

        if bold is not None:
            elements.append({"type": "text", "text": bold, "style": {"bold": True}})
        else:
            elements.append({"type": "link", "text": link_text, "url": url})

        position = match.end()

    if position < len(markdown) or not elements:
        elements.append({"type": "text", "text": markdown[position:] or " "})

    return {
        "type": "rich_text",
        "elements": [{"type": "rich_text_section", "elements": elements}],
    }


def cell_chars(cell: dict) -> int:
    # Characters a cell counts toward Slack's table limit. Link URLs are
    # included to stay on the safe side.
    return sum(
        len(element.get("text", "")) + len(element.get("url", ""))
        for section in cell["elements"]
        for element in section["elements"]
    )


def table_chars(table: dict) -> int:
    return sum(cell_chars(cell) for row in table["rows"] for cell in row)


def build_tables(columns: list[str], rows: list[list[str]]) -> list[dict]:
    # Build a table with a bold header row, the same layout as the Teams card.
    # Splits into more tables, each repeating the header row, to stay within
    # Slack's table limits.
    header = [build_cell(f"**{column}**") for column in columns]
    header_chars = sum(cell_chars(cell) for cell in header)
    tables: list[list[list[dict]]] = []
    current = [header]
    chars = header_chars

    for values in rows:
        row = [build_cell(value) for value in values]
        size = sum(cell_chars(cell) for cell in row)

        if len(current) > 1 and (
            len(current) >= MAX_TABLE_ROWS or chars + size > MAX_TABLE_CHARS
        ):
            tables.append(current)
            current, chars = [header], header_chars

        current.append(row)
        chars += size

    tables.append(current)

    return [
        {"type": "table", "column_settings": [{"is_wrapped": True}], "rows": rows}
        for rows in tables
    ]


def format_daily(raw_results: list[dict]) -> list:
    # Format daily protest updates: the header, then one block per solicitation
    if not raw_results:
        return []

    return [build_markdown(results.daily_header())] + [
        build_markdown(results.daily_content(result)) for result in raw_results
    ]


def format_roundup(raw_results: list[dict]) -> list:
    # Format weekly roundup: a bid line above a table of open protests for
    # each solicitation, then the solicitations with no open protests
    blocks = [build_markdown(results.roundup_header())]
    no_protest_results = []

    for result in raw_results:
        if not result["protest_details"]:
            no_protest_results.append(result)
            continue

        blocks.append(build_markdown(results.roundup_bid(result)))
        blocks += build_tables(
            results.ROUNDUP_COLUMNS,
            [results.roundup_row(detail) for detail in result["protest_details"]],
        )

    if not any(block["type"] == "table" for block in blocks):
        blocks.append(build_markdown(results.NO_PROTESTS))

    if no_protest_results:
        blocks.append(build_markdown(results.no_protest_summary(no_protest_results)))

    return blocks


def format_results(raw_results: list[dict], mode: str) -> list:
    # Format results for the run mode: "roundup" or "daily"
    return (
        format_roundup(raw_results) if mode == "roundup" else format_daily(raw_results)
    )


def block_size(block: dict) -> int:
    return table_chars(block) if block["type"] == "table" else len(block["text"])


def split_messages(blocks: list[dict]) -> list[list[dict]]:
    # Group blocks into messages that stay within Slack's per-message limits.
    # A bid line stays in the same message as the table that follows it.
    messages: list[list[dict]] = []
    current: list[dict] = []

    def totals(message: list[dict]) -> tuple[int, int, int]:
        tables = [b for b in message if b["type"] == "table"]
        markdown = [b for b in message if b["type"] != "table"]
        return (
            len(tables),
            sum(block_size(b) for b in tables),
            sum(block_size(b) for b in markdown),
        )

    for block in blocks:
        is_table = block["type"] == "table"
        tables, table_chars_total, markdown_chars = totals(current)
        size = block_size(block)

        if current and (
            len(current) >= MAX_BLOCKS
            or (is_table and tables >= MAX_TABLES_PER_MESSAGE)
            or (is_table and table_chars_total + size > MAX_TABLE_CHARS)
            or (not is_table and markdown_chars + size > MAX_MARKDOWN_CHARS)
        ):
            carry = []

            if is_table and len(current) > 1 and current[-1]["type"] != "table":
                # Move the bid line down with its table
                carry = [current.pop()]

            messages.append(current)
            current = carry

        current.append(block)

    if current:
        messages.append(current)

    return messages


def block_text(block: dict) -> str:
    # Plain text of a markdown block, or of a table's first cell
    if block["type"] == "table":
        section = block["rows"][0][0]["elements"][0]
        return "".join(element["text"] for element in section["elements"])

    return block["text"].replace("**", "")


def fallback_text(blocks: list[dict]) -> str:
    # Plain text used in notifications, from the message's first block
    return block_text(blocks[0])[:150]


def post(webhook_url: str, items: list[dict]) -> None:
    # Execute Slack post, splitting into several messages when needed
    http = urllib3.PoolManager(ca_certs=certifi.where())

    for n, blocks in enumerate(split_messages(items)):
        if n:
            # Incoming webhooks allow about one message per second
            time.sleep(1)

        response = http.request(
            "POST",
            webhook_url,
            json={"text": fallback_text(blocks), "blocks": blocks},
            timeout=30,
        )

        if response.status != 200:
            body = response.data.decode(errors="replace")
            raise SlackPostError(
                f"Slack webhook returned HTTP {response.status}: {body}"
            )
