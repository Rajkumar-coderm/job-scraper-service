from typing import Optional

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote

from app.core.config import HEADLESS
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


async def scrape_indeed(
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool = False,
    enrich_hr_limit: int = 5,
    headless: Optional[bool] = None,
):
    jobs = []

    days = DATE_FILTER_MAP.get(date_filter, "1")

    url = (
        f"{INDEED_BASE}/jobs?"
        f"q={quote(keyword)}"
        f"&l={quote(location)}"
        f"&fromage={days}"
    )

    print("\n======================")
    print("INDEED SCRAPER START")
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

            print("Indeed Page Loaded")

            await page.wait_for_selector(
                "a.jcs-JobTitle",
                timeout=20000,
            )

            await page.wait_for_timeout(2000)

            for _ in range(2):
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(1000)

            print("PAGE TITLE:")
            print(await page.title())

            html = await page.content()

            with open("indeed_debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.job_seen_beacon")

            if not cards:
                cards = soup.select("div.cardOutline")

            print(f"Indeed Cards Found: {len(cards)}")

            for card in cards:

                title_tag = card.select_one("a.jcs-JobTitle")
                if not title_tag:
                    title_tag = card.select_one("h3.jobTitle a")

                company_tag = card.select_one("[data-testid='company-name']")
                location_tag = card.select_one("[data-testid='text-location']")
                posted_tag = card.select_one("span.date")

                salary_tags = card.select(
                    "[data-testid='attribute_snippet_testid']"
                )
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

            if enrich_details and jobs:
                jobs = await enrich_jobs_with_details(
                    page,
                    jobs,
                    "indeed",
                    INDEED_BASE,
                    max_fetch=enrich_hr_limit,
                )

        except Exception as e:
            print("Indeed Error:", e)

        await browser.close()

    print(f"Indeed Jobs Found: {len(jobs)}")

    return jobs
