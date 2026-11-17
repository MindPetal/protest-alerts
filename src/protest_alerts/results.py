"""
Display helpers and the Markdown text for protest details, shared by every
chat channel.
"""

from datetime import date, datetime

ROUNDUP_COLUMNS = ["Company", "Filed", "Due"]
NO_PROTESTS = "No protests."


def fmt_date(value: str) -> str:
    # Normalize a date string like "Feb 2, 2024" to mm/dd/yyyy
    try:
        return datetime.strptime(value, "%b %d, %Y").strftime("%m/%d/%Y")
    except (ValueError, TypeError):
        return value


def daily_header() -> str:
    # Header for the daily protest updates message
    return f"**{date.today().strftime('%A, %m/%d/%Y')}.** Protest updates."


def daily_content(result: dict) -> str:
    # Markdown for one solicitation's protest updates: a heading line, then one
    # bullet per opened or closed protest
    content = f"**{result['index']}. {result['rfq_nm']}** - {result['rfq_no']} - [View on GAO]({result['url']})"

    for detail in result["protest_details"]:
        if "decided_dt" in detail:
            # Case closed
            content += f"\n\n- {detail['company']} | {detail['type']} {detail['status']} | Decided {detail['decided_dt']}"

            if "decision_url" in detail:
                # Decision report published
                content += (
                    f" | [View decision](https://www.gao.gov{detail['decision_url']})"
                )

        elif "filed_dt" in detail:
            # Case opened
            content += f"\n\n- {detail['company']} | {detail['type']} Opened | Filed {detail['filed_dt']} | Due {detail['due_dt']}"

    return content


def roundup_header() -> str:
    # Header for the weekly roundup message
    return f"**{date.today().strftime('%A, %m/%d/%Y')}.** Weekly roundup of open GAO protests for tracked bids."


def roundup_bid(result: dict) -> str:
    # Bid line shown above a solicitation's table of open protests
    return f"**{result['rfq_nm']}** - [View on GAO]({result['url']})"


def roundup_row(detail: dict) -> list[str]:
    # Table cells for one open protest, matching ROUNDUP_COLUMNS
    return [
        detail["company"],
        fmt_date(detail["filed_dt"]),
        fmt_date(detail["due_dt"]),
    ]


def no_protest_summary(no_protest_results: list[dict]) -> str:
    # Lists tracked solicitations that have no open protests
    names = ", ".join(result["rfq_nm"] for result in no_protest_results)
    return f"**Tracked bids with no open protests:** {names}"
