"""
    Script executes via github actions to scrape protest updates
    from GAO and post results to MS Teams. 
"""

import logging
import sys
from datetime import date, datetime, timedelta

from playwright.sync_api import BrowserContext, Page, sync_playwright
import client
from client.rest import ApiException


log = logging.getLogger("search")
logging.basicConfig(level=logging.INFO)


def get_details_page(i: int, page: Page, context: BrowserContext) -> Page:
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


def search(rfq_no: str, yday: str) -> tuple[list[dict], str]:
    # Execute gao search

    url = f"https://www.gao.gov/legal/bid-protests/search?processed=1&solicitation={rfq_no}&outcome=all#s-skipLinkTargetForMainSearchResults"
    protest_details = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            screen={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            color_scheme='light',
            reduced_motion='no-preference',
            forced_colors='none',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Linux"',
                'DNT': '1',
                'Connection': 'keep-alive'
            }
        )
        page = context.new_page()
        response = page.goto(url)
        
        if response.status != 200:
            browser.close()
            raise Exception(f"Received HTTP {response.status}")
    
        protest_count = page.locator("div.teaser-search--bookmark").count()
        log.info(f"{protest_count} protests found")

        if protest_count > 0:

            closed_protest_count = page.locator(
                "div.teaser-search--outcome .field__item"
            ).count()
            open_protest_count = page.locator(
                "div.teaser-search--status .field__item"
            ).count()
            log.info(
                f"{closed_protest_count} closed protests, {open_protest_count} open protests"
            )

            for i in range(closed_protest_count):

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

            for i in range(open_protest_count):

                protest_info = {}

                if (
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


def build_textblock(content: str) -> dict:
    # Build TextBlock for MS Teams
    return {"type": "TextBlock", "text": content, "wrap": True}


def format_results(raw_results: list[dict]) -> list:
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


def process_search(rfq_list: str) -> list:
    # Prepare gao search and format results
    rfq_pairs = []
    raw_results = []
    yday = (datetime.now() - timedelta(days=1)).strftime("%b %d, %Y")
    log.info(f"Yesterday: {yday}")

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


def teams_post(api_client: client.ApiClient, items: list[dict]) -> None:
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


def main(rfq_list: str, ms_webhook_url: str) -> None:
    # Primary processing fuction

    log.info("Start processing")
    protest_results = process_search(rfq_list)

    if protest_results:
        log.info("Process Teams posts")
        api_config = client.Configuration()
        api_config.host = ms_webhook_url
        api_client = client.ApiClient(api_config)
        teams_post(api_client, protest_results)


""" Read in rfq_list, ms_webhook_url
"""
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
