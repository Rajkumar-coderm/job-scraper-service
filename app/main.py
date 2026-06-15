from fastapi import FastAPI

from app.api.routes import router
from app.core.config import APP_NAME, HEADLESS, SCRAPE_ON_STARTUP
from app.services.scheduler_service import (
    start_scheduler,
    refresh_jobs,
)

app = FastAPI(
    title=APP_NAME,
    description="Scrape jobs from LinkedIn, Indeed, and Naukri with dynamic search.",
    version="1.0.0",
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Job Scraper API is running",
        "docs": "/docs",
        "health": "/api/v1/health",
        "browser_headless": HEADLESS,
        "endpoints": {
            "search_all": (
                "/api/v1/jobs?keyword=flutter developer"
                "&location=Bangalore&date_filter=24h"
            ),
            "search_source": (
                "/api/v1/jobs/source/indeed?keyword=python developer"
                "&location=India&date_filter=1m"
            ),
            "legacy_search": (
                "/jobs?keyword=flutter developer&location=India"
            ),
        },
        "query_params": {
            "keyword": "required - job title or skill",
            "location": "optional - defaults to India",
            "date_filter": "optional - 24h, 1m, or 3m",
            "force_refresh": "optional - live scrape (default true)",
            "enrich_details": (
                "optional - fetch HR contacts from Naukri only "
                "(default false, faster)"
            ),
            "enrich_hr_limit": (
                "optional - max Naukri jobs to enrich (default 5)"
            ),
            "use_cache": "optional - return cached results (default false)",
        },
    }


@app.on_event("startup")
async def startup_event():

    print("Starting App...")
    print(f"Browser headless mode: {HEADLESS}")

    start_scheduler()

    if SCRAPE_ON_STARTUP:
        await refresh_jobs()

    print("App Started Successfully")
