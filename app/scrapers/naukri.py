from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from app.utils.helpers import clean_text

DATE_FILTER_MAP = {
    "24h": "1",
    "1m": "30",
    "3m": "90"
}


async def scrape_naukri(keyword: str, location: str,date_filter:str):

    jobs = []

    keyword_slug = keyword.replace(" ", "-")

    days = DATE_FILTER_MAP.get(date_filter, "1")

    url = (
    f"https://www.naukri.com/"
    f"{keyword.replace(' ', '-')}-jobs-in-{location}"
    f"?jobAge={days}"
    )

    print("\n======================")
    print("NAUKRI SCRAPER START")
    print(url)
    print("======================")

    async with async_playwright() as p:

        browser = await p.firefox.launch(
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

        try:

            await page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            await page.wait_for_timeout(12000)

            # Scroll slowly
            await page.mouse.wheel(0, 3000)

            await page.wait_for_timeout(5000)

            print("PAGE TITLE:")
            print(await page.title())

            html = await page.content()

            with open(
                "naukri_debug.html",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(html)

            soup = BeautifulSoup(html, "html.parser")

            cards = soup.select("article.jobTuple")

            print(f"Naukri Cards Found: {len(cards)}")

            for card in cards:

                title_tag = card.select_one("a.title")

                company_tag = card.select_one("a.comp-name")

                location_tag = card.select_one("span.locWdth")

                exp_tag = card.select_one("span.expwdth")

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

                experience = clean_text(
                    exp_tag.get_text(strip=True)
                    if exp_tag
                    else "N/A"
                )

                job_link = (
                    title_tag.get("href")
                    if title_tag
                    else "N/A"
                )

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_name,
                    "salary": "N/A",
                    "experience": experience,
                    "skills": [],
                    "posted": "N/A",
                    "source": "naukri",
                    "job_link": job_link,
                })

        except Exception as e:
            print("Naukri Error:", e)

        await browser.close()

    print(f"Naukri Jobs Found: {len(jobs)}")

    return jobs