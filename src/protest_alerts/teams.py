"""
Build MS Teams Adaptive Card content and post it to a Teams webhook.

Each chat destination gets its own module with the same interface:
format_results(results, mode) -> payload items, and post(webhook_url, items).
"""

import logging

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


def format_daily(raw_results: list[dict], errors: list[dict] | None = None) -> list:
    # Format daily protest updates, then any GAO errors

    items = []

    if raw_results or errors:
        items += [build_textblock(results.daily_header()), build_textblock("")]

        for result in raw_results:
            content = results.daily_content(result)
            items += [build_textblock(content), build_textblock("")]

    if errors:
        items.append(build_textblock(results.gao_errors(errors)))

    return items


def format_roundup(raw_results: list[dict], errors: list[dict] | None = None) -> list:
    # Format weekly roundup as a full-width bid header above a compact table

    items = [build_textblock(results.roundup_header()), build_textblock("")]
    no_protest_results = []
    has_open_protests = False

    for result in raw_results:
        if not result["protest_details"]:
            no_protest_results.append(result)
            continue

        has_open_protests = True

        bid = results.roundup_bid(result)
        rows = [build_header_row(results.ROUNDUP_COLUMNS)]

        for stripe_index, detail in enumerate(result["protest_details"]):
            rows.append(build_row(results.roundup_row(detail), stripe_index))

        table = {
            "type": "Table",
            "columns": [{"width": 2}, {"width": 1}, {"width": 1}],
            "firstRowAsHeaders": True,
            "gridStyle": "default",
            "rows": rows,
        }

        items += [build_textblock(bid), table, build_textblock("")]

    if not has_open_protests:
        items.append(build_textblock(results.NO_PROTESTS))

    if no_protest_results:
        items += [
            build_textblock(""),
            build_textblock(results.no_protest_summary(no_protest_results)),
        ]

    if errors:
        items += [build_textblock(""), build_textblock(results.gao_errors(errors))]

    return items


def format_results(
    raw_results: list[dict], mode: str, errors: list[dict] | None = None
) -> list:
    # Format results for the run mode: "roundup" or "daily"
    return (
        format_roundup(raw_results, errors)
        if mode == "roundup"
        else format_daily(raw_results, errors)
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
