"""
Run the GAO search for each tracked solicitation and post the results to the
chat channel.
"""

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from protest_alerts import gao, teams
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
    items = teams.format_results(results, settings.mode)

    if items:
        log.info("Posting results")
        teams.post(settings.ms_webhook_url, items)
    else:
        log.info("No protest updates found")
