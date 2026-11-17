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


def process_search(rfqs: Iterable[RfqEntry], mode: str) -> list[dict]:
    # Run gao searches and return results, numbered from 1

    roundup = mode == "roundup"
    raw_results = []
    yday = (datetime.now() - timedelta(days=1)).strftime("%b %-d, %Y")
    log.info(f"Yesterday: {yday}")

    for rfq in rfqs:
        log.info("Processing rfq number search")

        protest_details, url = gao.search(rfq.rfq_no, yday, roundup=roundup)

        if roundup or protest_details:
            raw_results.append(
                {
                    "rfq_no": rfq.rfq_no,
                    "rfq_nm": rfq.name,
                    "protest_details": protest_details,
                    "url": url,
                }
            )

    # Inject index into results
    n = 1

    for result in raw_results:
        result["index"] = n
        n += 1

    return raw_results


def main(settings: Settings) -> None:
    # Primary processing function

    log.info("Start processing")

    results = process_search(settings.rfqs, settings.mode)
    post_results(settings, results)


def post_results(settings: Settings, results: list[dict]) -> None:
    # Post to every configured chat channel. A failure on one channel doesn't
    # stop the others, but the run still fails afterwards.
    channels = [
        (teams, settings.ms_webhook_url),
        (slack, settings.slack_webhook_url),
    ]
    failed = []
    posted = False

    for channel, webhook_url in channels:
        if not webhook_url:
            continue

        items = channel.format_results(results, settings.mode)

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

    if failed:
        raise RuntimeError(f"Posting failed for: {', '.join(failed)}")

    if not posted:
        log.info("No protest updates found")
