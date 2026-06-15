from urllib.parse import quote

import httpx

from app.utils.browser import USER_AGENT
from app.utils.helpers import clean_text
from app.utils.job_enrichment import default_hr_contact, normalize_job_url

NAUKRI_BASE = "https://www.naukri.com"

HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Language": "en-IN,en;q=0.9",
    "appid": "109",
    "systemid": "Naukri",
    "Referer": f"{NAUKRI_BASE}/",
}


def _extract_skills(job: dict) -> list:
    skills = []
    raw = job.get("keywords") or job.get("tagsAndSkills") or ""
    for tag in str(raw).split(","):
        skill = clean_text(tag)
        if skill and skill not in skills:
            skills.append(skill)
    return skills[:8]


def _format_experience(job: dict) -> str:
    min_exp = job.get("minExp")
    max_exp = job.get("maxExp")

    if min_exp is not None and max_exp is not None:
        return f"{min_exp}-{max_exp} Yrs"

    return clean_text(
        job.get("experienceText")
        or job.get("experience")
        or "N/A"
    )


def _format_location(job: dict) -> str:
    placeholders = job.get("placeholders") or []
    if placeholders:
        return clean_text(placeholders[0].get("label", "N/A"))

    cityfield = clean_text(job.get("cityfield", ""))
    if cityfield:
        parts = [part.strip() for part in cityfield.split("-") if part.strip()]
        if parts:
            return parts[0].title()

    return "N/A"


async def scrape_naukri_api(
    keyword: str,
    location: str,
    date_filter: str,
) -> list:
    jobs = []

    keyword_slug = keyword.strip().replace(" ", "-").lower()
    location_slug = location.strip().replace(" ", "-").lower()
    seo_key = f"{keyword_slug}-jobs-in-{location_slug}"

    days_map = {"24h": 1, "1m": 30, "3m": 90}
    job_age = days_map.get(date_filter, 1)

    query = (
        f"noOfResults=20"
        f"&keyword={quote(keyword)}"
        f"&location={quote(location)}"
        f"&pageNo=1"
        f"&jobAge={job_age}"
        f"&url=/{seo_key}"
        f"&seoKey={seo_key}"
    )

    url = f"{NAUKRI_BASE}/jobapi/v2/search?{query}"

    print("Naukri API fallback:", url)

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers=HTTP_HEADERS,
        ) as client:
            response = await client.get(url)

        if response.status_code != 200:
            print(f"Naukri API failed: HTTP {response.status_code}")
            return jobs

        data = response.json()
        items = data.get("list", [])

        for item in items:
            title = clean_text(item.get("post") or item.get("title", "N/A"))
            company = clean_text(
                item.get("companyName")
                or item.get("CONTCOM")
                or "N/A"
            )

            job_link = "N/A"
            if item.get("urlStr"):
                job_link = normalize_job_url(item["urlStr"], NAUKRI_BASE)

            posted = clean_text(item.get("addDate", "N/A"))

            if title == "N/A":
                continue

            jobs.append({
                "title": title,
                "company": company,
                "location": _format_location(item),
                "salary": "N/A",
                "experience": _format_experience(item),
                "skills": _extract_skills(item),
                "posted": posted,
                "source": "naukri",
                "job_link": job_link,
                "hr_contact": default_hr_contact(),
            })

        print(f"Naukri API jobs: {len(jobs)} (total available: {data.get('totaljobs', 0)})")

    except Exception as error:
        print("Naukri API error:", error)

    return jobs
