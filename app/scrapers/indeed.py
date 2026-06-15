from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import quote

from app.core.config import HEADLESS
from app.scrapers.indeed_http import scrape_indeed_http
from app.utils.browser import (
    detect_block_page,
    dismiss_overlays,
    launch_browser,
    log_block_status,
    navigation_timeout,
    new_stealth_context,
    prepare_page,
    selector_timeout,
    wait_for_any_selector,
    warm_up_domain,
)
from app.utils.helpers import clean_text
from app.utils.job_enrichment import (
    build_indeed_job_url,
    default_hr_contact,
    enrich_jobs_with_details,
)

DATE_FILTER_MAP = {
    "24h": "1",
    "1m": "30",
    "3m": "90",
}

INDEED_BASE = "https://in.indeed.com"

JOB_SELECTORS = [
    "a.jcs-JobTitle",
    "div.job_seen_beacon",
    "div.cardOutline",
]


def _parse_indeed_cards(soup: BeautifulSoup) -> list:
    jobs = []

    cards = soup.select("div.job_seen_beacon")
    if not cards:
        cards = soup.select("div.cardOutline")

    for card in cards:
        title_tag = card.select_one("a.jcs-JobTitle")
        if not title_tag:
            title_tag = card.select_one("h3.jobTitle a")

        company_tag = card.select_one("[data-testid='company-name']")
        location_tag = card.select_one("[data-testid='text-location']")
        posted_tag = card.select_one("span.date")

        salary_tags = card.select("[data-testid='attribute_snippet_testid']")
        salary = "N/A"
        for tag in salary_tags:
            text = clean_text(tag.get_text(strip=True))
            if (
                "₹" in text
                or "year" in text.lower()
                or "month" in text.lower()
            ):
                salary = text
                break

        title = clean_text(
            title_tag.get_text(strip=True) if title_tag else "N/A"
        )
        company = clean_text(
            company_tag.get_text(strip=True) if company_tag else "N/A"
        )
        location_name = clean_text(
            location_tag.get_text(strip=True) if location_tag else "N/A"
        )
        posted = clean_text(
            posted_tag.get_text(strip=True) if posted_tag else "N/A"
        )

        job_link = "N/A"
        if title_tag and title_tag.get("href"):
            job_link = build_indeed_job_url(
                title_tag.get("href"),
                INDEED_BASE,
            )

        if title == "N/A":
            continue

        jobs.append({
            "title": title,
            "company": company,
            "location": location_name,
            "salary": salary,
            "experience": "N/A",
            "skills": [],
            "posted": posted,
            "source": "indeed",
            "job_link": job_link,
            "hr_contact": default_hr_contact(),
        })

    return jobs


async def _scrape_indeed_browser(
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool,
    enrich_hr_limit: int,
    headless: bool,
) -> list:
    jobs = []
    days = DATE_FILTER_MAP.get(date_filter, "1")

    url = (
        f"{INDEED_BASE}/jobs?"
        f"q={quote(keyword)}"
        f"&l={quote(location)}"
        f"&fromage={days}"
    )

    async with async_playwright() as playwright:
        browser = await launch_browser(playwright, headless)
        context = await new_stealth_context(browser)
        page = await prepare_page(context)

        try:
            await warm_up_domain(page, INDEED_BASE)

            await page.goto(
                url,
                timeout=navigation_timeout(),
                wait_until="domcontentloaded",
            )

            print("Indeed Page Loaded")
            await dismiss_overlays(page)

            found = await wait_for_any_selector(
                page,
                JOB_SELECTORS,
                timeout_ms=selector_timeout(),
            )

            if not found:
                print("Indeed selector timeout — parsing available HTML")

            await page.wait_for_timeout(2000)

            for _ in range(2):
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(800)

            title = await page.title()
            html = await page.content()
            log_block_status("Indeed", html, title)

            soup = BeautifulSoup(html, "html.parser")
            jobs = _parse_indeed_cards(soup)
            print(f"Indeed Cards Found: {len(jobs)}")

            if enrich_details and jobs:
                jobs = await enrich_jobs_with_details(
                    page,
                    jobs,
                    "indeed",
                    INDEED_BASE,
                    max_fetch=enrich_hr_limit,
                )

        except Exception as error:
            print("Indeed browser error:", error)

        await browser.close()

    return jobs


async def scrape_indeed(
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool = False,
    enrich_hr_limit: int = 5,
    headless: Optional[bool] = None,
):
    print("\n======================")
    print("INDEED SCRAPER START")
    print("======================")

    browser_headless = HEADLESS if headless is None else headless

    jobs = await _scrape_indeed_browser(
        keyword,
        location,
        date_filter,
        enrich_details,
        enrich_hr_limit,
        browser_headless,
    )

    if not jobs:
        print("Indeed browser returned 0 jobs — trying HTTP fallback")
        jobs = await scrape_indeed_http(keyword, location, date_filter)

    print(f"Indeed Jobs Found: {len(jobs)}")
    return jobs
