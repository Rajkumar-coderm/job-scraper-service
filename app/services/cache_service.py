import json
import os
import time

CACHE_DIR = "app/cache"
CACHE_FILE = f"{CACHE_DIR}/jobs_cache.json"

CACHE_EXPIRY = 1800  # 30 mins


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_cache():

    ensure_cache_dir()

    if not os.path.exists(CACHE_FILE):
        return None

    try:

        with open(CACHE_FILE, "r") as f:
            data = json.load(f)

        timestamp = data.get("timestamp", 0)

        # cache expired
        if time.time() - timestamp > CACHE_EXPIRY:
            return None

        return data.get("jobs", [])

    except Exception as e:
        print("Cache Load Error:", e)
        return None


def save_cache(jobs):

    ensure_cache_dir()

    try:

        with open(CACHE_FILE, "w") as f:
            json.dump(
                {
                    "timestamp": time.time(),
                    "jobs": jobs
                },
                f,
                indent=2
            )

        print("Cache Saved")

    except Exception as e:
        print("Cache Save Error:", e)