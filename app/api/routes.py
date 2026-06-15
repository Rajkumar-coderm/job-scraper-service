from fastapi import APIRouter, HTTPException, Query

from app.core.config import ENRICH_HR_LIMIT, HEADLESS
from app.models.job import JobSearchResponse
from app.services.scraper_manager import (
    SCRAPER_MAP,
    scrape_all_jobs,
    scrape_jobs_by_source,
)

router = APIRouter()
api_v1 = APIRouter(prefix="/api/v1", tags=["jobs"])

VALID_DATE_FILTERS = {"24h", "1m", "3m"}
VALID_SOURCES = set(SCRAPER_MAP.keys())


def _validate_date_filter(date_filter: str):
    if date_filter not in VALID_DATE_FILTERS:
        raise HTTPException(
            status_code=400,
            detail=f"date_filter must be one of: {', '.join(sorted(VALID_DATE_FILTERS))}",
        )


async def _search_jobs(
    keyword: str,
    location: str,
    date_filter: str,
    force_refresh: bool,
    enrich_details: bool,
    enrich_hr_limit: int,
    use_cache: bool,
):
    _validate_date_filter(date_filter)

    jobs = await scrape_all_jobs(
        keyword=keyword,
        location=location,
        date_filter=date_filter,
        force_refresh=force_refresh,
        enrich_details=enrich_details,
        enrich_hr_limit=enrich_hr_limit,
        headless=HEADLESS,
        use_cache=use_cache,
    )

    return JobSearchResponse(
        success=True,
        keyword=keyword,
        location=location,
        date_filter=date_filter,
        total_jobs=len(jobs),
        jobs=jobs,
    )


@api_v1.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Job Scraper API",
        "sources": sorted(VALID_SOURCES),
        "date_filters": sorted(VALID_DATE_FILTERS),
        "browser_headless": HEADLESS,
        "enrich_hr_limit_default": ENRICH_HR_LIMIT,
        "hr_enrichment_sources": ["naukri"],
    }


@api_v1.get("/jobs", response_model=JobSearchResponse)
async def get_jobs_v1(
    keyword: str = Query(..., description="Job title or skill to search"),
    location: str = Query("India", description="City or country"),
    date_filter: str = Query("24h", description="24h, 1m, or 3m"),
    force_refresh: bool = Query(
        True,
        description="Always scrape live (default true)",
    ),
    enrich_details: bool = Query(
        False,
        description="Fetch HR contacts from Naukri job pages (slower)",
    ),
    enrich_hr_limit: int = Query(
        ENRICH_HR_LIMIT,
        ge=1,
        le=10,
        description="Max Naukri jobs to enrich for HR contacts",
    ),
    use_cache: bool = Query(
        False,
        description="Return cached results when available",
    ),
):
    return await _search_jobs(
        keyword=keyword,
        location=location,
        date_filter=date_filter,
        force_refresh=force_refresh,
        enrich_details=enrich_details,
        enrich_hr_limit=enrich_hr_limit,
        use_cache=use_cache,
    )


@api_v1.get("/jobs/source/{source}", response_model=JobSearchResponse)
async def get_jobs_by_source(
    source: str,
    keyword: str = Query(...),
    location: str = Query("India"),
    date_filter: str = Query("24h"),
    enrich_details: bool = Query(False),
    enrich_hr_limit: int = Query(ENRICH_HR_LIMIT, ge=1, le=10),
):
    _validate_date_filter(date_filter)

    if source.lower() not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"source must be one of: {', '.join(sorted(VALID_SOURCES))}",
        )

    jobs = await scrape_jobs_by_source(
        source=source.lower(),
        keyword=keyword,
        location=location,
        date_filter=date_filter,
        enrich_details=enrich_details,
        enrich_hr_limit=enrich_hr_limit,
        headless=HEADLESS,
    )

    return JobSearchResponse(
        success=True,
        keyword=keyword,
        location=location,
        date_filter=date_filter,
        total_jobs=len(jobs),
        jobs=jobs,
    )


@router.get("/jobs")
async def get_jobs(
    keyword: str = Query(...),
    location: str = Query("India"),
    date_filter: str = Query("24h"),
    force_refresh: bool = Query(True),
    enrich_details: bool = Query(False),
    enrich_hr_limit: int = Query(ENRICH_HR_LIMIT, ge=1, le=10),
    use_cache: bool = Query(False),
):
    response = await _search_jobs(
        keyword=keyword,
        location=location,
        date_filter=date_filter,
        force_refresh=force_refresh,
        enrich_details=enrich_details,
        enrich_hr_limit=enrich_hr_limit,
        use_cache=use_cache,
    )
    return response.model_dump()


router.include_router(api_v1)
