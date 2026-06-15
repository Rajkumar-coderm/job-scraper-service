from typing import Optional

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from app.core.config import HEADLESS
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


def _extract_skills(card) -> list:
    skills = []
    for tag in card.select("ul.tags-gt li"):
        skill = clean_text(tag.get_text(strip=True))
        if skill and skill not in skills:
            skills.append(skill)
    return skills[:8]


async def scrape_naukri(
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool = False,
    enrich_hr_limit: int = 5,
    headless: Optional[bool] = None,
):
    jobs = []

    days = DATE_FILTER_MAP.get(date_filter, "1")
    keyword_slug = keyword.strip().replace(" ", "-")
    location_slug = location.strip().replace(" ", "-")

    url = (
        f"{NAUKRI_BASE}/"
        f"{keyword_slug}-jobs-in-{location_slug}"
        f"?jobAge={days}"
    )

    print("\n======================")
    print("NAUKRI SCRAPER START")
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

        try:

            await page.goto(
                url,
                timeout=45000,
                wait_until="domcontentloaded",
            )

            await page.wait_for_selector(
                "div.cust-job-tuple",
                timeout=20000,
            )

            await page.wait_for_timeout(2500)

            for _ in range(2):
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(1000)

            print("PAGE TITLE:")
            print(await page.title())

            html = await page.content()

            with open("naukri_debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.cust-job-tuple")

            if not cards:
                cards = soup.select("article.jobTuple")

            print(f"Naukri Cards Found: {len(cards)}")

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

            if enrich_details and jobs:
                jobs = await enrich_jobs_with_details(
                    page,
                    jobs,
                    "naukri",
                    NAUKRI_BASE,
                    max_fetch=enrich_hr_limit,
                )

        except Exception as e:
            print("Naukri Error:", e)

        await browser.close()

    print(f"Naukri Jobs Found: {len(jobs)}")

    return jobs
