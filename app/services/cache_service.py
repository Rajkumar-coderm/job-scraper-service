import hashlib
import json
import os
import time

CACHE_DIR = "app/cache"
CACHE_FILE = f"{CACHE_DIR}/jobs_cache.json"

CACHE_EXPIRY = 1800  # 30 mins


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def make_cache_key(keyword: str, location: str, date_filter: str) -> str:
    raw = f"{keyword.strip().lower()}|{location.strip().lower()}|{date_filter.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


def load_cache(keyword: str, location: str, date_filter: str):

    ensure_cache_dir()

    if not os.path.exists(CACHE_FILE):
        return None

    try:

        with open(CACHE_FILE, "r") as f:
            data = json.load(f)

        cache_key = make_cache_key(keyword, location, date_filter)
        entry = data.get("entries", {}).get(cache_key)

        if not entry:
            return None

        timestamp = entry.get("timestamp", 0)

        if time.time() - timestamp > CACHE_EXPIRY:
            return None

        return entry.get("jobs", [])

    except Exception as e:
        print("Cache Load Error:", e)
        return None


def save_cache(jobs, keyword: str, location: str, date_filter: str):

    ensure_cache_dir()

    try:

        cache_key = make_cache_key(keyword, location, date_filter)

        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"entries": {}}

        if "entries" not in data:
            data = {"entries": {}}

        data["entries"][cache_key] = {
            "timestamp": time.time(),
            "keyword": keyword,
            "location": location,
            "date_filter": date_filter,
            "jobs": jobs,
        }

        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)

        print("Cache Saved")

    except Exception as e:
        print("Cache Save Error:", e)
