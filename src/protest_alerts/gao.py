"""
Scrape bid protest dockets from the GAO website with Playwright.
"""

import logging
from http import HTTPStatus

from playwright.sync_api import BrowserContext, Page, sync_playwright

log = logging.getLogger(__name__)


class GaoHttpError(Exception):
    # GAO returned a non-200 status for a search or details page
    def __init__(self, status: int):
        self.status = status
        # GAO serves HTTP/2, which sends no status text, so use the standard
        # reason phrase
        try:
            self.message = HTTPStatus(status).phrase
        except ValueError:
            self.message = "Unknown error"

        super().__init__(f"HTTP {status} received: {self.message}")


def get_details_page(href: str, context: BrowserContext) -> Page:
    # Go to details page

    details_url = f"https://www.gao.gov{href}"
    new_tab = context.new_page()
    response = new_tab.goto(details_url)

    if response is not None and response.status != 200:
        new_tab.close()
        raise GaoHttpError(response.status)

    return new_tab


def search_url(rfq_no: str) -> str:
    # GAO bid protest search for a solicitation number
    return f"https://www.gao.gov/legal/bid-protests/search?processed=1&solicitation={rfq_no}&outcome=all#s-skipLinkTargetForMainSearchResults"


def search(rfq_no: str, yday: str, roundup: bool = False) -> tuple[list[dict], str]:
    # Execute gao search
    # roundup=False (daily): report protests from yesterday
    # roundup=True (weekly): report open protests, not date bound

    url = search_url(rfq_no)
    protest_details = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            screen={"width": 1920, "height": 1080},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            color_scheme="light",
            reduced_motion="no-preference",
            forced_colors="none",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "DNT": "1",
                "Connection": "keep-alive",
            },
        )
        page = context.new_page()
        response = page.goto(url)

        if response is None:
            browser.close()
            raise Exception("No response received from page")

        if response.status != 200:
            browser.close()
            raise GaoHttpError(response.status)

        cards = page.locator("article.node--type-bid-protest-docket")
        protest_count = cards.count()
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

            # Iterate each protest card and scope all lookups to that card so
            # open/closed status, headings and details always refer to the same
            # protest, regardless of how open and closed protests are interleaved.
            for i in range(protest_count):
                card = cards.nth(i)
                protest_info = {}

                heading_href = card.locator(
                    "div.teaser-search--heading h3.heading a"
                ).get_attribute("href")
                is_open = (
                    card.locator("div.teaser-search--status .field__item").count() > 0
                )

                if is_open:
                    # Open protest

                    # Go to details page
                    details_page = get_details_page(heading_href, context)

                    filed_dt = (
                        details_page.locator(
                            "div.field--name-field-filed-date .field__item"
                        )
                        .inner_text()
                        .strip()
                    )

                    if roundup or filed_dt == yday:
                        log.info("Opened protest")
                        protest_info["company"] = (
                            card.locator("div.teaser-search--heading h3.heading")
                            .inner_text()
                            .split(" (")[0]
                            .strip()
                        )
                        protest_info["status"] = (
                            card.locator("div.teaser-search--status .field__item")
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

                    details_page.close()

                elif not roundup:
                    # Closed protest (skipped entirely in roundup mode)

                    decided_dt = (
                        card.locator("div.teaser-search--decision_date .field__item")
                        .inner_text()
                        .strip()
                    )

                    log.info(f"Decided date: {decided_dt}")

                    if decided_dt == yday:
                        log.info("Protest updated")
                        protest_info["company"] = (
                            card.locator("div.teaser-search--heading h3.heading")
                            .inner_text()
                            .split(" (")[0]
                            .strip()
                        )
                        protest_info["status"] = (
                            card.locator("div.teaser-search--outcome .field__item")
                            .inner_text()
                            .strip()
                        )
                        protest_info["decided_dt"] = decided_dt

                        decision_link = card.locator("div.teaser-search-decision a")
                        if decision_link.count() > 0:
                            href = decision_link.first.get_attribute("href")
                            if href:
                                # Decision report published
                                protest_info["decision_url"] = href.strip()

                        # Go to details page
                        details_page = get_details_page(heading_href, context)

                        protest_info["type"] = (
                            details_page.locator(
                                "div.field--name-field-case-type .field__item"
                            )
                            .inner_text()
                            .strip()
                        )

                        details_page.close()

                        protest_details.append(protest_info)

        browser.close()

        return protest_details, url
