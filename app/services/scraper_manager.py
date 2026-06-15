import asyncio
from typing import Optional

from app.core.config import ENRICH_HR_LIMIT, HEADLESS, SCRAPE_SEQUENTIAL
from app.scrapers.linkedin import scrape_linkedin
from app.scrapers.indeed import scrape_indeed
from app.scrapers.naukri import scrape_naukri

from app.services.cache_service import (
    load_cache,
    save_cache,
)

SCRAPER_MAP = {
    "linkedin": scrape_linkedin,
    "indeed": scrape_indeed,
    "naukri": scrape_naukri,
}


def _dedupe_jobs(jobs: list) -> list:
    unique_jobs = []
    seen = set()

    for job in jobs:
        key = (
            job.get("title", "") +
            job.get("company", "") +
            job.get("source", "")
        ).lower()

        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs


async def scrape_jobs_by_source(
    source: str,
    keyword: str,
    location: str,
    date_filter: str,
    enrich_details: bool = False,
    enrich_hr_limit: int = ENRICH_HR_LIMIT,
    headless: Optional[bool] = None,
):
    scraper = SCRAPER_MAP.get(source.lower())

    if not scraper:
        raise ValueError(f"Unsupported source: {source}")

    jobs = await scraper(
        keyword,
        location,
        date_filter,
        enrich_details=enrich_details,
        enrich_hr_limit=enrich_hr_limit,
        headless=headless,
    )

    return _dedupe_jobs(jobs)


async def scrape_all_jobs(
    keyword,
    location,
    date_filter,
    force_refresh=False,
    enrich_details=False,
    enrich_hr_limit=ENRICH_HR_LIMIT,
    headless=None,
    use_cache=False,
):

    if use_cache and not force_refresh:
        cached_jobs = load_cache(keyword, location, date_filter)

        if cached_jobs:
            print("Returning Cached Jobs")
            return cached_jobs

    print("Fetching Fresh Jobs")

    browser_headless = HEADLESS if headless is None else headless

    scraper_calls = [
        scrape_linkedin(
            keyword,
            location,
            date_filter,
            enrich_details=enrich_details,
            enrich_hr_limit=enrich_hr_limit,
            headless=browser_headless,
        ),
        scrape_indeed(
            keyword,
            location,
            date_filter,
            enrich_details=enrich_details,
            enrich_hr_limit=enrich_hr_limit,
            headless=browser_headless,
        ),
        scrape_naukri(
            keyword,
            location,
            date_filter,
            enrich_details=enrich_details,
            enrich_hr_limit=enrich_hr_limit,
            headless=browser_headless,
        ),
    ]

    if SCRAPE_SEQUENTIAL:
        results = []
        for scraper_call in scraper_calls:
            try:
                results.append(await scraper_call)
            except Exception as error:
                results.append(error)
    else:
        results = await asyncio.gather(
            *scraper_calls,
            return_exceptions=True,
        )

    all_jobs = []

    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)
        elif isinstance(result, Exception):
            print("Scraper Error:", result)

    unique_jobs = _dedupe_jobs(all_jobs)

    if use_cache:
        save_cache(unique_jobs, keyword, location, date_filter)

    print(f"Total Unique Jobs: {len(unique_jobs)}")

    return unique_jobs
