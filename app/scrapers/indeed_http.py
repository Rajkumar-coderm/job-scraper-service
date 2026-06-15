import asyncio
from urllib.parse import quote

from bs4 import BeautifulSoup

from app.core.config import PROXY_SERVER
from app.utils.browser import USER_AGENT, detect_block_page
from app.utils.helpers import clean_text
from app.utils.job_enrichment import build_indeed_job_url, default_hr_contact

INDEED_BASE = "https://in.indeed.com"


def _parse_indeed_html(html: str) -> list:
    jobs = []
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.job_seen_beacon")
    if not cards:
        cards = soup.select("div.cardOutline")

    for card in cards:
        title_tag = card.select_one("a.jcs-JobTitle")
        if not title_tag:
            title_tag = card.select_one("h3.jobTitle a")

        company_tag = card.select_one("[data-testid='company-name']")
        location_tag = card.select_one("[data-testid='text-location']")
        posted_tag = card.select_one("span.date")

        title = clean_text(
            title_tag.get_text(strip=True) if title_tag else "N/A"
        )
        company = clean_text(
            company_tag.get_text(strip=True) if company_tag else "N/A"
        )
        location_name = clean_text(
            location_tag.get_text(strip=True) if location_tag else "N/A"
        )
        posted = clean_text(
            posted_tag.get_text(strip=True) if posted_tag else "N/A"
        )

        job_link = "N/A"
        if title_tag and title_tag.get("href"):
            job_link = build_indeed_job_url(
                title_tag.get("href"),
                INDEED_BASE,
            )

        if title == "N/A":
            continue

        jobs.append({
            "title": title,
            "company": company,
            "location": location_name,
            "salary": "N/A",
            "experience": "N/A",
            "skills": [],
            "posted": posted,
            "source": "indeed",
            "job_link": job_link,
            "hr_contact": default_hr_contact(),
        })

    return jobs


def _fetch_indeed_html(keyword: str, location: str, days: str) -> str:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        print("curl_cffi not installed — skipping Indeed HTTP fallback")
        return ""

    url = (
        f"{INDEED_BASE}/jobs?"
        f"q={quote(keyword)}"
        f"&l={quote(location)}"
        f"&fromage={days}"
    )

    print("Indeed HTTP fallback:", url)

    proxies = None
    if PROXY_SERVER:
        proxies = {"http": PROXY_SERVER, "https": PROXY_SERVER}

    session = curl_requests.Session(impersonate="chrome131")

    session.get(
        INDEED_BASE,
        timeout=30,
        proxies=proxies,
        headers={"Accept-Language": "en-IN,en;q=0.9"},
    )

    response = session.get(
        url,
        timeout=45,
        proxies=proxies,
        headers={
            "Accept-Language": "en-IN,en;q=0.9",
            "Referer": f"{INDEED_BASE}/",
        },
    )

    print(f"Indeed HTTP status: {response.status_code}")

    if response.status_code != 200:
        return ""

    return response.text


async def scrape_indeed_http(
    keyword: str,
    location: str,
    date_filter: str,
) -> list:
    days_map = {"24h": "1", "1m": "30", "3m": "90"}
    days = days_map.get(date_filter, "1")

    try:
        html = await asyncio.to_thread(
            _fetch_indeed_html,
            keyword,
            location,
            days,
        )

        if not html:
            return []

        block = detect_block_page(html)
        if block:
            print(f"Indeed HTTP blocked (detected: {block})")
            if not PROXY_SERVER:
                print(
                    "Tip: set PROXY_SERVER env var with a residential proxy "
                    "for Indeed on cloud hosts like Render"
                )
            return []

        jobs = _parse_indeed_html(html)
        print(f"Indeed HTTP jobs: {len(jobs)}")
        return jobs

    except Exception as error:
        print("Indeed HTTP error:", error)
        return []
