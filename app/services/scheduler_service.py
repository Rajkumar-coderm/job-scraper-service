from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.scraper_manager import scrape_all_jobs

scheduler = AsyncIOScheduler()


async def refresh_jobs():

    print("Refreshing Jobs Cache...")

    try:

        await scrape_all_jobs(
            keyword="Flutter Developer",
            location="India",
            date_filter="24h",
            force_refresh=True
        )

        print("Jobs Cache Updated")

    except Exception as e:
        print("Scheduler Error:", e)


def start_scheduler():

    scheduler.add_job(
        refresh_jobs,
        "interval",
        minutes=30
    )

    scheduler.start()

    print("Scheduler Started")