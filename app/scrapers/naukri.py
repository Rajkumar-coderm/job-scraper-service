from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.core.config import HEADLESS
from app.scrapers.naukri_api import scrape_naukri_api
from app.utils.browser import (
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
    default_hr_contact,
    enrich_jobs_with_details,
    normalize_job_url,
)

DATE_FILTER_MAP = {
    "24h": "1",
    "1m": "30",
    "3m": "90",
}

NAUKRI_BASE = "https://www.naukri.com"

JOB_SELECTORS = [
    "div.cust-job-tuple",
    "article.jobTuple",
    "div.srp-jobtuple-wrapper",
]


def _extract_skills(card) -> list:
    skills = []
    for tag in card.select("ul.tags-gt li"):
        skill = clean_text(tag.get_text(strip=True))
        if skill and skill not in skills:
            skills.append(skill)
    return skills[:8]


def _parse_naukri_cards(soup: BeautifulSoup) -> list:
    jobs = []

    cards = soup.select("div.cust-job-tuple")
    if not cards:
        cards = soup.select("article.jobTuple")

    for card in cards:
        title_tag = card.select_one("a.title")
        company_tag = card.select_one("a.comp-name")
        location_tag = card.select_one("span.locWdth")
        exp_tag = card.select_one("span.expwdth")
        posted_tag = card.select_one(".job-post-day")

        title = clean_text(
            title_tag.get_text(strip=True) if title_tag else "N/A"
        )
        company = clean_text(
            company_tag.get_text(strip=True) if company_tag else "N/A"
        )
        location_name = clean_text(
            location_tag.get_text(strip=True) if location_tag else "N/A"
        )
        experience = clean_text(
            exp_tag.get_text(strip=True) if exp_tag else "N/A"
        )
        posted = clean_text(
            posted_tag.get_text(strip=True) if posted_tag else "N/A"
        )

        job_link = "N/A"
        if title_tag and title_tag.get("href"):
            job_link = normalize_job_url(
                title_tag.get("href"),
                NAUKRI_BASE,
            )

        if title == "N/A":
            continue

        jobs.append({
            "title": title,
            "company": company,
            "location": location_name,
            "salary": "N/A",
            "experience": experience,
            "skills": _extract_skills(card),
            "posted": posted,
            "source": "naukri",
            "job_link": job_link,
            "hr_contact": default_hr_contact(),
        })

    return jobs


async def _scrape_naukri_browser(
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool,
    enrich_hr_limit: int,
    headless: bool,
) -> list:
    jobs = []

    days = DATE_FILTER_MAP.get(date_filter, "1")
    keyword_slug = keyword.strip().replace(" ", "-")
    location_slug = location.strip().replace(" ", "-")

    url = (
        f"{NAUKRI_BASE}/"
        f"{keyword_slug}-jobs-in-{location_slug}"
        f"?jobAge={days}"
    )

    async with async_playwright() as playwright:
        browser = await launch_browser(playwright, headless)
        context = await new_stealth_context(browser)
        page = await prepare_page(context)

        try:
            await warm_up_domain(page, NAUKRI_BASE)

            await page.goto(
                url,
                timeout=navigation_timeout(),
                wait_until="domcontentloaded",
            )

            await dismiss_overlays(page)

            found = await wait_for_any_selector(
                page,
                JOB_SELECTORS,
                timeout_ms=selector_timeout(),
            )

            if not found:
                print("Naukri selector timeout — parsing available HTML")

            await page.wait_for_timeout(2000)

            for _ in range(2):
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(800)

            title = await page.title()
            html = await page.content()
            log_block_status("Naukri", html, title)

            soup = BeautifulSoup(html, "html.parser")
            jobs = _parse_naukri_cards(soup)
            print(f"Naukri Cards Found: {len(jobs)}")

            if enrich_details and jobs:
                jobs = await enrich_jobs_with_details(
                    page,
                    jobs,
                    "naukri",
                    NAUKRI_BASE,
                    max_fetch=enrich_hr_limit,
                )

        except Exception as error:
            print("Naukri browser error:", error)

        await browser.close()

    return jobs


async def scrape_naukri(
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool = False,
    enrich_hr_limit: int = 5,
    headless: Optional[bool] = None,
):
    print("\n======================")
    print("NAUKRI SCRAPER START")
    print("======================")

    browser_headless = HEADLESS if headless is None else headless

    jobs = await _scrape_naukri_browser(
        keyword,
        location,
        date_filter,
        enrich_details,
        enrich_hr_limit,
        browser_headless,
    )

    if not jobs:
        print("Naukri browser returned 0 jobs — trying API fallback")
        jobs = await scrape_naukri_api(keyword, location, date_filter)

    print(f"Naukri Jobs Found: {len(jobs)}")
    return jobs
