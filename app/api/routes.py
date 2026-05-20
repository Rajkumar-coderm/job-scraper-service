from fastapi import APIRouter, Query

from app.services.scraper_manager import scrape_all_jobs

router = APIRouter()


@router.get("/jobs")
async def get_jobs(
    keyword: str = Query(...),
    location: str = Query("India"),
    date_filter: str = Query("24h")
):

    jobs = await scrape_all_jobs(
        keyword=keyword,
        location=location,
        date_filter=date_filter
    )

    return {
        "success": True,
        "total_jobs": len(jobs),
        "jobs": jobs
    }