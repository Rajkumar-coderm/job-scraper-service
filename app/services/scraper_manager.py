import asyncio
from typing import Optional

from app.core.config import (
    ENRICH_HR_LIMIT,
    HEADLESS,
    SCRAPE_SEQUENTIAL,
    SCRAPER_TIMEOUT_SECONDS,
)
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


async def _run_scraper(source: str, scraper_call) -> list:
    try:
        if SCRAPER_TIMEOUT_SECONDS > 0:
            jobs = await asyncio.wait_for(
                scraper_call,
                timeout=SCRAPER_TIMEOUT_SECONDS,
            )
        else:
            jobs = await scraper_call

        if not isinstance(jobs, list):
            return []

        return jobs

    except asyncio.TimeoutError:
        print(
            f"{source.title()} timed out after "
            f"{SCRAPER_TIMEOUT_SECONDS}s — skipping"
        )
        return []

    except Exception as error:
        print(f"{source.title()} error:", error)
        return []


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

    jobs = await _run_scraper(
        source.lower(),
        scraper(
            keyword,
            location,
            date_filter,
            enrich_details=enrich_details,
            enrich_hr_limit=enrich_hr_limit,
            headless=headless,
        ),
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

    if SCRAPER_TIMEOUT_SECONDS > 0:
        print(f"Per-source timeout: {SCRAPER_TIMEOUT_SECONDS}s")

    browser_headless = HEADLESS if headless is None else headless

    scraper_tasks = [
        (
            "linkedin",
            scrape_linkedin(
                keyword,
                location,
                date_filter,
                enrich_details=enrich_details,
                enrich_hr_limit=enrich_hr_limit,
                headless=browser_headless,
            ),
        ),
        (
            "indeed",
            scrape_indeed(
                keyword,
                location,
                date_filter,
                enrich_details=enrich_details,
                enrich_hr_limit=enrich_hr_limit,
                headless=browser_headless,
            ),
        ),
        (
            "naukri",
            scrape_naukri(
                keyword,
                location,
                date_filter,
                enrich_details=enrich_details,
                enrich_hr_limit=enrich_hr_limit,
                headless=browser_headless,
            ),
        ),
    ]

    if SCRAPE_SEQUENTIAL:
        results = []
        for source, scraper_call in scraper_tasks:
            results.append(await _run_scraper(source, scraper_call))
    else:
        results = await asyncio.gather(
            *[
                _run_scraper(source, scraper_call)
                for source, scraper_call in scraper_tasks
            ]
        )

    all_jobs = []

    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)

    unique_jobs = _dedupe_jobs(all_jobs)

    if use_cache:
        save_cache(unique_jobs, keyword, location, date_filter)

    print(f"Total Unique Jobs: {len(unique_jobs)}")

    return unique_jobs
