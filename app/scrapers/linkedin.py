from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from app.utils.helpers import clean_text, make_search_keyword

DATE_FILTER_MAP = {
    "24h": "r86400",
    "1m": "r2592000",
    "3m": "r7776000"
}


async def scrape_linkedin(keyword: str, location: str,date_filter: str):
    jobs = []

    time_filter = DATE_FILTER_MAP.get(date_filter, "r86400")

    url = (
    f"https://www.linkedin.com/jobs/search/"
    f"?keywords={keyword}"
    f"&location={location}"
    f"&f_TPR={time_filter}"
)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled"
    ])
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(5000)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            cards = soup.select("div.base-card")

            for card in cards:
                title = clean_text(
                    card.select_one("h3").text if card.select_one("h3") else "N/A"
                )

                company = clean_text(
                    card.select_one("h4").text if card.select_one("h4") else "N/A"
                )

                location_name = clean_text(
                    card.select_one("span.job-search-card__location").text
                    if card.select_one("span.job-search-card__location")
                    else "N/A"
                )

                posted = clean_text(
                    card.select_one("time").text
                    if card.select_one("time")
                    else "N/A"
                )

                link_tag = card.select_one("a.base-card__full-link")

                job_link = link_tag.get("href") if link_tag else "N/A"

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_name,
                    "salary": "N/A",
                    "experience": "N/A",
                    "skills": [],
                    "posted": posted,
                    "source": "linkedin",
                    "job_link": job_link,
                })

        except Exception as e:
            print("LinkedIn Error:", e)

        await browser.close()

    print(f"LinkedIn Jobs Found: {len(jobs)}")
    return jobs