import asyncio

from app.scrapers.linkedin import scrape_linkedin
# from app.scrapers.indeed import scrape_indeed
# from app.scrapers.naukri import scrape_naukri

from app.services.cache_service import (
    load_cache,
    save_cache
)


async def scrape_all_jobs(
    keyword,
    location,
    date_filter,
    force_refresh=False
):

    # RETURN CACHE
    if not force_refresh:

        cached_jobs = load_cache()

        if cached_jobs:
            print("Returning Cached Jobs")
            return cached_jobs

    print("Fetching Fresh Jobs")

    results = await asyncio.gather(
        scrape_linkedin(keyword, location, date_filter),
        # scrape_indeed(keyword, location, date_filter),
        # scrape_naukri(keyword, location, date_filter),
        return_exceptions=True
    )

    all_jobs = []

    for result in results:

        if isinstance(result, list):
            all_jobs.extend(result)

    # REMOVE DUPLICATES
    unique_jobs = []
    seen = set()

    for job in all_jobs:

        key = (
            job.get("title", "") +
            job.get("company", "")
        ).lower()

        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    # SAVE CACHE
    save_cache(unique_jobs)

    print(f"Total Unique Jobs: {len(unique_jobs)}")

    return unique_jobs