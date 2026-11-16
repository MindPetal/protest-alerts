"""
Build MS Teams Adaptive Card content and post it to a Teams webhook.

Each chat destination gets its own module with the same interface:
format_results(results, mode) -> payload items, and post(webhook_url, items).
Another destination, such as Slack, would be a sibling module (slack.py).
"""

import logging
from datetime import date

import client
from client.rest import ApiException
from protest_alerts import results

log = logging.getLogger(__name__)


def build_textblock(content: str) -> dict:
    # Build TextBlock for MS Teams
    return {"type": "TextBlock", "text": content, "wrap": True}


def build_cell(content: str) -> dict:
    # Build a single TableCell
    return {"type": "TableCell", "items": [build_textblock(content)]}


def build_header_row(labels: list[str]) -> dict:
    # Build the styled header TableRow
    return {
        "type": "TableRow",
        "style": "accent",
        "cells": [build_cell(f"**{label}**") for label in labels],
    }


def build_row(values: list[str], stripe_index: int) -> dict:
    # Build a striped multi-cell TableRow
    return {
        "type": "TableRow",
        "style": "emphasis" if stripe_index % 2 else "default",
        "cells": [build_cell(value) for value in values],
    }


def format_daily(raw_results: list[dict]) -> list:
    # Format daily protest updates

    items = []

    if raw_results:
        header = f"**{date.today().strftime('%A, %m/%d/%Y')}.** Protest updates."
        items += [build_textblock(header), build_textblock("")]

        for result in raw_results:
            content = f"**{result['index']}. {result['rfq_nm']}** - {result['rfq_no']} - [View on GAO]({result['url']})"

            for detail in result["protest_details"]:
                if "decided_dt" in detail:
                    # Case closed
                    content += f"\n\n- {detail['company']} | {detail['type']} {detail['status']} | Decided {detail['decided_dt']}"

                    if "decision_url" in detail:
                        # Decision report published
                        content += f" | [View decision](https://www.gao.gov{detail['decision_url']})"

                elif "filed_dt" in detail:
                    # Case opened
                    content += f"\n\n- {detail['company']} | {detail['type']} Opened | Filed {detail['filed_dt']} | Due {detail['due_dt']}"

            items += [build_textblock(content), build_textblock("")]

    return items


def format_roundup(raw_results: list[dict]) -> list:
    # Format weekly roundup as a full-width bid header above a compact table

    header = f"**{date.today().strftime('%A, %m/%d/%Y')}.** Weekly roundup of open GAO protests for tracked bids."

    items = [build_textblock(header), build_textblock("")]
    no_protest_results = []
    has_open_protests = False

    for result in raw_results:
        if not result["protest_details"]:
            no_protest_results.append(result)
            continue

        has_open_protests = True

        bid = f"**{result['rfq_nm']}** - [View on GAO]({result['url']})"
        rows = [build_header_row(["Company", "Filed", "Due"])]

        for stripe_index, detail in enumerate(result["protest_details"]):
            rows.append(
                build_row(
                    [
                        detail["company"],
                        results.fmt_date(detail["filed_dt"]),
                        results.fmt_date(detail["due_dt"]),
                    ],
                    stripe_index,
                )
            )

        table = {
            "type": "Table",
            "columns": [{"width": 2}, {"width": 1}, {"width": 1}],
            "firstRowAsHeaders": True,
            "gridStyle": "default",
            "rows": rows,
        }

        items += [build_textblock(bid), table, build_textblock("")]

    if not has_open_protests:
        items.append(build_textblock("No protests."))

    if no_protest_results:
        names = ", ".join(result["rfq_nm"] for result in no_protest_results)
        items += [
            build_textblock(""),
            build_textblock(f"**Tracked bids with no open protests:** {names}"),
        ]

    return items


def format_results(raw_results: list[dict], mode: str) -> list:
    # Format results for the run mode: "roundup" or "daily"
    return (
        format_roundup(raw_results) if mode == "roundup" else format_daily(raw_results)
    )


def post(webhook_url: str, items: list[dict]) -> None:
    # Execute MS Teams post
    api_config = client.Configuration()
    api_config.host = webhook_url
    api_instance = client.MsApi(client.ApiClient(api_config))

    try:
        api_instance.teams_post(
            body={
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
        )

    except ApiException as e:
        log.exception("Exception when calling MsApi->teams_post: %s\n" % e)
        raise
