from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Job Scraper API")
DEBUG = os.getenv("DEBUG", "False") == "True"

HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")

SCRAPE_ON_STARTUP = os.getenv("SCRAPE_ON_STARTUP", "false").lower() in (
    "true",
    "1",
    "yes",
)

# Only Naukri detail pages reliably expose recruiter contact info
ENRICH_HR_LIMIT = int(os.getenv("ENRICH_HR_LIMIT", "5"))

# Run scrapers sequentially on low-memory hosts (e.g. Render)
SCRAPE_SEQUENTIAL = os.getenv("SCRAPE_SEQUENTIAL", "false").lower() in (
    "true",
    "1",
    "yes",
)
