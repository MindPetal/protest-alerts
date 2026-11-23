"""
Run the GAO search for each tracked solicitation and post the results to the
configured chat channels (MS Teams and/or Slack).
"""

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from protest_alerts import gao, slack, teams
from protest_alerts.config import RfqEntry, Settings

log = logging.getLogger(__name__)


def process_search(
    rfqs: Iterable[RfqEntry], mode: str, days: int = 1
) -> tuple[list[dict], list[dict]]:
    # Run gao searches and return results and any GAO HTTP errors. An error
    # on one solicitation doesn't stop the others. Daily mode matches the
    # single date `days` ago; roundup ignores the date.

    roundup = mode == "roundup"
    raw_results = []
    errors = []
    yday = (datetime.now() - timedelta(days=days)).strftime("%b %-d, %Y")
    log.info(f"Searching for date: {yday}")

    for rfq in rfqs:
        log.info("Processing rfq number search")

        try:
            protest_details, url = gao.search(rfq.rfq_no, yday, roundup=roundup)
        except gao.GaoHttpError as e:
            log.error(f"GAO error: {e}")
            errors.append(
                {
                    "status": e.status,
                    "message": e.message,
                    "url": gao.search_url(rfq.rfq_no),
                }
            )
            continue

        if roundup or protest_details:
            raw_results.append(
                {
                    "rfq_no": rfq.rfq_no,
                    "rfq_nm": rfq.name,
                    "protest_details": protest_details,
                    "url": url,
                }
            )

    return raw_results, errors


def main(settings: Settings) -> None:
    # Primary processing function

    log.info("Start processing")

    results, errors = process_search(settings.rfqs, settings.mode, settings.days)
    post_results(settings, results, errors)


def post_results(
    settings: Settings, results: list[dict], errors: list[dict] | None = None
) -> None:
    # Post to every configured chat channel. A failure on one channel doesn't
    # stop the others, but the run still fails afterwards. GAO errors are
    # included in the post and also fail the run.
    errors = errors or []
    channels = [
        (teams, settings.ms_webhook_url),
        (slack, settings.slack_webhook_url),
    ]
    failed = []
    posted = False

    for channel, webhook_url in channels:
        if not webhook_url:
            continue

        items = channel.format_results(results, settings.mode, errors)

        if not items:
            continue

        name = channel.__name__.rsplit(".", 1)[-1]
        log.info("Posting results to %s", name)

        try:
            channel.post(webhook_url, items)
            posted = True
        except Exception:
            log.exception("Posting results to %s failed", name)
            failed.append(name)

    problems = []

    if failed:
        problems.append(f"Posting failed for: {', '.join(failed)}")

    if errors:
        problems.append(
            "GAO returned HTTP errors: " + ", ".join(str(e["status"]) for e in errors)
        )

    if problems:
        raise RuntimeError("; ".join(problems))

    if not posted:
        log.info("No protest updates found")
