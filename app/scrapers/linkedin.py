from typing import Optional

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote

from app.core.config import HEADLESS
from app.utils.helpers import clean_text
from app.utils.job_enrichment import (
    default_hr_contact,
    enrich_jobs_with_details,
    normalize_job_url,
)

DATE_FILTER_MAP = {
    "24h": "r86400",
    "1m": "r2592000",
    "3m": "r7776000",
}

LINKEDIN_BASE = "https://www.linkedin.com"


async def scrape_linkedin(
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool = False,
    enrich_hr_limit: int = 5,
    headless: Optional[bool] = None,
):
    jobs = []

    time_filter = DATE_FILTER_MAP.get(date_filter, "r86400")

    url = (
        f"{LINKEDIN_BASE}/jobs/search/"
        f"?keywords={quote(keyword)}"
        f"&location={quote(location)}"
        f"&f_TPR={time_filter}"
    )

    print("\n======================")
    print("LINKEDIN SCRAPER START")
    print(url)
    print("======================")

    browser_headless = HEADLESS if headless is None else headless

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=browser_headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """)

        try:
            await page.goto(
                url,
                timeout=45000,
                wait_until="domcontentloaded",
            )

            await page.wait_for_timeout(3000)

            for _ in range(3):
                await page.mouse.wheel(0, 2500)
                await page.wait_for_timeout(1200)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            cards = soup.select("div.base-card")

            if not cards:
                cards = soup.select("li.jobs-search-results__list-item")

            print(f"LinkedIn Cards Found: {len(cards)}")

            for card in cards:
                title_el = (
                    card.select_one("h3.base-search-card__title")
                    or card.select_one("h3")
                )
                company_el = (
                    card.select_one("h4.base-search-card__subtitle")
                    or card.select_one("h4")
                )
                location_el = card.select_one(
                    "span.job-search-card__location"
                )
                posted_el = card.select_one("time")

                title = clean_text(
                    title_el.get_text(strip=True) if title_el else "N/A"
                )
                company = clean_text(
                    company_el.get_text(strip=True) if company_el else "N/A"
                )
                location_name = clean_text(
                    location_el.get_text(strip=True) if location_el else "N/A"
                )
                posted = clean_text(
                    posted_el.get_text(strip=True) if posted_el else "N/A"
                )

                link_tag = (
                    card.select_one("a.base-card__full-link")
                    or card.select_one("a[href*='/jobs/view/']")
                )

                job_link = "N/A"
                if link_tag and link_tag.get("href"):
                    job_link = normalize_job_url(
                        link_tag.get("href"),
                        LINKEDIN_BASE,
                    )

                if title == "N/A":
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_name,
                    "salary": "N/A",
                    "experience": "N/A",
                    "skills": [],
                    "posted": posted,
                    "source": "linkedin",
                    "job_link": job_link,
                    "hr_contact": default_hr_contact(),
                })

            if enrich_details and jobs:
                jobs = await enrich_jobs_with_details(
                    page,
                    jobs,
                    "linkedin",
                    LINKEDIN_BASE,
                    max_fetch=enrich_hr_limit,
                )

        except Exception as e:
            print("LinkedIn Error:", e)

        await browser.close()

    print(f"LinkedIn Jobs Found: {len(jobs)}")
    return jobs
