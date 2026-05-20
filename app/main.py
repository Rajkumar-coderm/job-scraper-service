from fastapi import FastAPI

from app.api.routes import router
from app.services.scheduler_service import (
    start_scheduler,
    refresh_jobs
)

app = FastAPI(
    title="Job Scraper API"
)

app.include_router(router)


@app.on_event("startup")
async def startup_event():

    print("Starting App...")
    start_scheduler()
    await refresh_jobs()

    print("App Started Successfully")