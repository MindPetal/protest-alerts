"""
    Script executes via github actions to scrape protest updates
    from GAO and post results to MS Teams. 
"""

import logging
import sys
from datetime import date, datetime, timedelta

from playwright.sync_api import sync_playwright
import client
from client.rest import ApiException


log = logging.getLogger("search")
logging.basicConfig(level=logging.INFO)


def get_details_page(i, page, context):
    # Go to details page

    details_link = (
        page.locator("div.teaser-search--heading h4.heading a")
        .nth(i)
        .get_attribute("href")
    )
    details_url = f"https://www.gao.gov{details_link}"
    new_tab = context.new_page()
    new_tab.goto(details_url)
    return new_tab


def search(rfq_no, yday):
    # Execute gao search

    url = f"https://www.gao.gov/legal/bid-protests/search?processed=1&solicitation={rfq_no}&outcome=all#s-skipLinkTargetForMainSearchResults"
    protest_details = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url)

        protest_count = page.locator("div.teaser-search--bookmark").count()
        log.info(f"{protest_count} protests found")

        if protest_count > 0:

            for i in range(protest_count):

                protest_info = {}

                if (
                    page.locator("div.teaser-search--outcome .field__item")
                    .nth(i)
                    .is_visible()
                ):
                    # Closed protest
                    decided_dt = (
                        page.locator("div.teaser-search--decision_date .field__item")
                        .nth(i)
                        .inner_text()
                        .strip()
                    )

                    if decided_dt == yday:
                        log.info("Protest updated")
                        protest_info["company"] = (
                            page.locator("div.teaser-search--heading h4.heading")
                            .nth(i)
                            .inner_text()
                            .split(" (")[0]
                            .strip()
                        )
                        protest_info["status"] = (
                            page.locator("div.teaser-search--outcome .field__item")
                            .nth(i)
                            .inner_text()
                            .strip()
                        )
                        protest_info["decided_dt"] = (
                            page.locator(
                                "div.teaser-search--decision_date .field__item"
                            )
                            .nth(i)
                            .inner_text()
                            .strip()
                        )

                        if (
                            page.locator("div.teaser-search-decision")
                            .nth(i)
                            .is_visible()
                        ):
                            # Decision report published
                            protest_info["decision_url"] = (
                                page.locator("div.teaser-search-decision a")
                                .nth(i)
                                .get_attribute("href")
                                .strip()
                            )

                        # Go to details page
                        details_page = get_details_page(i, page, context)

                        protest_info["type"] = (
                            details_page.locator(
                                "div.field--name-field-case-type .field__item"
                            )
                            .inner_text()
                            .strip()
                        )

                        protest_details.append(protest_info)

                elif (
                    page.locator("div.teaser-search--status .field__item")
                    .nth(i)
                    .is_visible()
                ):
                    # Open protest

                    # Go to details page
                    details_page = get_details_page(i, page, context)

                    filed_dt = (
                        details_page.locator(
                            "div.field--name-field-filed-date .field__item"
                        )
                        .inner_text()
                        .strip()
                    )

                    if filed_dt == yday:
                        log.info("Opened protest")
                        protest_info["company"] = (
                            page.locator("div.teaser-search--heading h4.heading")
                            .nth(i)
                            .inner_text()
                            .split(" (")[0]
                            .strip()
                        )
                        protest_info["status"] = (
                            page.locator("div.teaser-search--status .field__item")
                            .nth(i)
                            .inner_text()
                            .strip()
                        )
                        protest_info["type"] = (
                            details_page.locator(
                                "div.field--name-field-case-type .field__item"
                            )
                            .inner_text()
                            .strip()
                        )

                        if protest_info["status"] == "Case Currently Open":
                            protest_info["status"] = "Opened"

                        protest_info["filed_dt"] = filed_dt
                        protest_info["due_dt"] = (
                            details_page.locator(
                                "div.field--name-field-due-date .field__item"
                            )
                            .inner_text()
                            .strip()
                        )

                        protest_details.append(protest_info)

        browser.close()

        return protest_details, url


def build_textblock(content):
    # Build TextBlock for MS Teams
    return {"type": "TextBlock", "text": content, "wrap": True}


def format_results(raw_results):
    # Format results strings

    items = []

    if raw_results:
        header = f'**{date.today().strftime("%A, %m/%d/%Y")}.** Protest updates.'
        items += [build_textblock(header), build_textblock("")]

        for result in raw_results:

            content = f'**{result["index"]}. {result["rfq_nm"]} - Solicitation {result["rfq_no"]} - [View updates]({result["url"]})**'

            for detail in result["protest_details"]:

                if "decided_dt" in detail:
                    # Case closed
                    content += f'\n\n- {detail["company"]} **|** {detail["type"]} {detail["status"]} **|** Decided {detail["decided_dt"]}'

                    if "decision_url" in detail:
                        # Decision report published
                        content += f' **|** [View decision](https://www.gao.gov{detail["decision_url"]})'

                elif "filed_dt" in detail:
                    # Case opened
                    content += f'\n\n- {detail["company"]} **|** {detail["type"]} Opened **|** Filed {detail["filed_dt"]} **|** Due {detail["due_dt"]}'

            items += [build_textblock(content), build_textblock("")]

    return items


def process_search(rfq_list):
    # Prepare gao search and format results
    rfq_pairs = []
    raw_results = []
    yday = (datetime.now() - timedelta(days=1)).strftime("%b %d, %Y")

    if rfq_list:
        rfq_pairs = rfq_list.split(",")

    for pair in rfq_pairs:
        log.info("Processing rfq number search")

        rfq_no, rfq_nm = pair.split(":", 1)
        rfq_no = rfq_no.strip()
        rfq_nm = rfq_nm.strip()
        protest_details, url = search(rfq_no, yday)

        if protest_details:
            raw_results.append(
                {
                    "rfq_no": rfq_no,
                    "rfq_nm": rfq_nm,
                    "protest_details": protest_details,
                    "url": url,
                }
            )

    if raw_results:
        # Inject index into results
        n = 1

        for result in raw_results:
            result["index"] = n
            n += 1

    return format_results(raw_results)


def teams_post(api_client, items):
    # Execute MS Teams post
    api_instance = client.MsApi(api_client)

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


def main(rfq_list, ms_webhook_url):
    # Primary processing fuction

    log.info("Start processing")
    protest_results = process_search(rfq_list)

    if protest_results:
        log.info(protest_results)
        log.info("Process Teams posts")
        api_config = client.Configuration()
        api_config.host = ms_webhook_url
        api_client = client.ApiClient(api_config)
        teams_post(api_client, protest_results)


""" Read in rfq_list, ms_webhook_url
"""
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
