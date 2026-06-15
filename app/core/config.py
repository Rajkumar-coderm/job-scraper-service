from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Job Scraper API")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


# Render sets RENDER=true automatically; other PaaS flags included
IS_CLOUD = bool(
    os.getenv("RENDER")
    or os.getenv("DYNO")
    or os.getenv("RAILWAY_ENVIRONMENT_NAME")
    or os.getenv("FLY_APP_NAME")
)

DEBUG = _env_bool("DEBUG", False)

# Cloud servers have no display — Playwright must run headless
if IS_CLOUD:
    HEADLESS = True
else:
    HEADLESS = _env_bool("HEADLESS", False)

SCRAPE_ON_STARTUP = _env_bool("SCRAPE_ON_STARTUP", False)

ENRICH_HR_LIMIT = int(os.getenv("ENRICH_HR_LIMIT", "5"))

# Sequential scraping saves RAM on Render/small instances
SCRAPE_SEQUENTIAL = _env_bool("SCRAPE_SEQUENTIAL", IS_CLOUD)

# Optional residential proxy for Indeed on cloud (e.g. http://user:pass@host:port)
PROXY_SERVER = os.getenv("PROXY_SERVER", "").strip()

# Per-source timeout; 0 = no limit. Default 120s on cloud (skip slow/blocked sources)
SCRAPER_TIMEOUT_SECONDS = int(
    os.getenv(
        "SCRAPER_TIMEOUT_SECONDS",
        "120" if IS_CLOUD else "0",
    )
)
