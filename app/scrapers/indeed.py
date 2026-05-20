from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from app.utils.helpers import clean_text, make_search_keyword
from urllib.parse import quote


DATE_FILTER_MAP = {
    "24h": "1",
    "1m": "30",
    "3m": "90"
}

async def scrape_indeed(keyword: str, location: str,date_filter: str):
    jobs = []


    days = DATE_FILTER_MAP.get(date_filter, "1")

    url = (
    f"https://in.indeed.com/jobs?"
    f"q={quote(keyword)}"
    f"&l={quote(location)}"
    f"&fromage={days}"
)

    print("\n======================")
    print("INDEED SCRAPER START")
    print(url)
    print("======================")

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
             args=[
        "--no-sandbox",
        "--disable-setuid-sandbox"
    ]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            locale="en-US",
        )

        page = await context.new_page()

        # Hide automation
        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """)

        try:

            await page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            print("Indeed Page Loaded")

            await page.wait_for_timeout(10000)

            # Scroll page
            await page.mouse.wheel(0, 5000)

            await page.wait_for_timeout(5000)

            print("PAGE TITLE:")
            print(await page.title())

            html = await page.content()

            with open(
                "indeed_debug.html",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(html)

            print("HTML SAVED")

            soup = BeautifulSoup(html, "html.parser")

            cards = soup.select("div.cardOutline")

            print(f"Indeed Cards Found: {len(cards)}")

            for card in cards:

                title_tag = card.select_one("h2.jobTitle a")

                company_tag = card.select_one(
                    "[data-testid='company-name']"
                )

                location_tag = card.select_one(
                    "[data-testid='text-location']"
                )

                posted_tag = card.select_one("span.date")

                title = clean_text(
                    title_tag.get_text(strip=True)
                    if title_tag
                    else "N/A"
                )

                company = clean_text(
                    company_tag.get_text(strip=True)
                    if company_tag
                    else "N/A"
                )

                location_name = clean_text(
                    location_tag.get_text(strip=True)
                    if location_tag
                    else "N/A"
                )

                posted = clean_text(
                    posted_tag.get_text(strip=True)
                    if posted_tag
                    else "N/A"
                )

                job_link = "N/A"

                if title_tag and title_tag.get("href"):

                    href = title_tag.get("href")

                    if href.startswith("/"):
                        job_link = "https://in.indeed.com" + href
                    else:
                        job_link = href

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
                })

        except Exception as e:
            print("Indeed Error:", e)

        await browser.close()

    print(f"Indeed Jobs Found: {len(jobs)}")

    return jobs