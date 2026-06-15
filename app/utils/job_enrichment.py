import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from app.utils.helpers import clean_text

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)
PHONE_RE = re.compile(
    r"(?:\+91[\s-]?)?[6-9]\d{9}"
)

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "from",
    "fromage",
    "vjk",
    "advn",
    "adid",
    "xkcb",
    "fccid",
    "bb",
    "jcid",
    "trk",
    "trkInfo",
    "refId",
    "trackingId",
    "position",
    "pageNum",
}

JUNK_EMAIL_DOMAINS = {
    "example.com",
    "sentry.io",
    "w3.org",
    "schema.org",
    "naukri.com",
    "linkedin.com",
    "indeed.com",
    "ambitionbox.com",
    "google.com",
    "facebook.com",
}

GENERIC_EMAIL_PREFIXES = {
    "noreply",
    "no-reply",
    "donotreply",
    "support",
    "help",
    "info",
    "admin",
    "contact",
    "careers",
    "jobs",
    "hr",
    "recruitment",
}

# LinkedIn/Indeed guest pages mix sidebar jobs into the DOM — skip HR there
HR_ENRICH_SOURCES = {"naukri"}

NAUKRI_SCOPE_SELECTORS = [
    ".jd-container",
    ".styles_jd-container",
    ".job-details",
    ".recruiter-info",
    ".emplyr-details",
    "[class*='recruiter']",
    "[class*='contact']",
]

NAUKRI_NAME_SELECTORS = [
    ".emplyr-name",
    ".recruiterName",
    "span.emplyr",
    ".hiring-manager",
    "[class*='recruiter'] .name",
]

POSTED_SELECTORS = {
    "indeed": [
        "[data-testid='job-date']",
        ".jobsearch-JobMetadataFooter",
        "span.date",
    ],
    "naukri": [
        ".job-post-day",
        ".tuple-posted",
    ],
    "linkedin": [
        "time",
        ".posted-time-ago__text",
    ],
}


def normalize_job_url(url: str, base: str = "") -> str:
    if not url or url == "N/A":
        return "N/A"

    if url.startswith("/"):
        url = urljoin(base, url)

    parsed = urlparse(url)

    if not parsed.scheme:
        return "N/A"

    clean_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_PARAMS
    ]

    clean_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/") or parsed.path,
            parsed.params,
            urlencode(clean_params),
            "",
        )
    )

    return clean_url


def build_indeed_job_url(href: str, base: str) -> str:
    if not href:
        return "N/A"

    jk_match = re.search(r"jk=([a-f0-9]+)", href)
    if jk_match:
        return f"{base}/viewjob?jk={jk_match.group(1)}"

    return normalize_job_url(href, base)


def default_hr_contact() -> dict:
    return {
        "name": "N/A",
        "email": "N/A",
        "phone": "N/A",
    }


def _company_tokens(company: str) -> set:
    if not company or company == "N/A":
        return set()

    tokens = re.findall(r"[a-z0-9]+", company.lower())
    return {token for token in tokens if len(token) > 2}


def _is_valid_hr_name(name: str, company: str) -> bool:
    if not name or name == "N/A":
        return False

    if len(name) < 2 or len(name) > 50:
        return False

    lowered = name.lower()

    if any(
        marker in lowered
        for marker in (
            "@",
            "http",
            "|",
            ".ai",
            ".com",
            ".io",
            ".co",
            "pvt",
            "ltd",
            "llp",
            "inc",
            "technologies",
            "solutions",
            "software",
            "specializing",
            "recruitment",
            "community",
            "reviews",
            "hiring",
            "talent acquisition",
            "manager -",
            "senior manager",
            "agency",
            "consulting",
        )
    ):
        return False

    if sum(char.isdigit() for char in name) > 2:
        return False

    if name.count(" ") > 5:
        return False

    company_tokens = _company_tokens(company)
    name_tokens = _company_tokens(name)

    if company_tokens and name_tokens:
        overlap = company_tokens & name_tokens
        if len(overlap) >= 2 or (
            len(overlap) == 1 and len(name_tokens) <= 2
        ):
            return False

    return True


def _pick_email(text: str, company: str = "") -> str:
    company_tokens = _company_tokens(company)
    candidates = []

    for email in EMAIL_RE.findall(text):
        local, domain = email.lower().split("@", 1)
        if domain in JUNK_EMAIL_DOMAINS:
            continue
        if any(local.startswith(prefix) for prefix in GENERIC_EMAIL_PREFIXES):
            continue

        score = 0
        if company_tokens:
            if any(token in domain for token in company_tokens):
                score += 2
            if any(token in local for token in company_tokens):
                score += 1

        if "." in local:
            score += 1

        candidates.append((score, email))

    if not candidates:
        return "N/A"

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _pick_phone(text: str) -> str:
    for match in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", match)
        if len(digits) == 10:
            return digits
    return "N/A"


def _scope_soup(soup: BeautifulSoup, source: str) -> BeautifulSoup:
    if source != "naukri":
        return soup

    for selector in NAUKRI_SCOPE_SELECTORS:
        section = soup.select_one(selector)
        if section:
            return section

    return soup


def _extract_posted(soup: BeautifulSoup, source: str) -> str:
    for selector in POSTED_SELECTORS.get(source, []):
        element = soup.select_one(selector)
        if element:
            posted = clean_text(element.get_text(strip=True))
            if posted and posted != "N/A":
                return posted
    return "N/A"


def extract_hr_from_soup(
    soup: BeautifulSoup,
    source: str,
    company: str = "",
) -> dict:
    contact = default_hr_contact()

    if source not in HR_ENRICH_SOURCES:
        return contact

    scoped = _scope_soup(soup, source)

    for selector in NAUKRI_NAME_SELECTORS:
        element = scoped.select_one(selector)
        if element:
            name = clean_text(element.get_text(strip=True))
            if _is_valid_hr_name(name, company):
                contact["name"] = name
                break

    mailto = scoped.select_one("a[href^='mailto:']")
    if mailto and mailto.get("href"):
        email = mailto["href"].replace("mailto:", "").split("?")[0].strip()
        if email and "@" in email:
            contact["email"] = email

    tel = scoped.select_one("a[href^='tel:']")
    if tel and tel.get("href"):
        phone = _pick_phone(tel["href"])
        if phone != "N/A":
            contact["phone"] = phone

    section_text = scoped.get_text(" ", strip=True)

    if contact["email"] == "N/A":
        contact["email"] = _pick_email(section_text, company)

    if contact["phone"] == "N/A":
        contact["phone"] = _pick_phone(section_text)

    if contact["name"] != "N/A" and not _is_valid_hr_name(
        contact["name"],
        company,
    ):
        contact["name"] = "N/A"

    return contact


def sanitize_hr_contact(contact: dict, company: str) -> dict:
    cleaned = default_hr_contact()

    name = contact.get("name", "N/A")
    if _is_valid_hr_name(name, company):
        cleaned["name"] = name

    email = contact.get("email", "N/A")
    if email and email != "N/A" and "@" in email:
        domain = email.split("@")[-1].lower()
        if domain not in JUNK_EMAIL_DOMAINS:
            cleaned["email"] = email

    phone = contact.get("phone", "N/A")
    if phone and phone != "N/A" and len(re.sub(r"\D", "", phone)) == 10:
        cleaned["phone"] = re.sub(r"\D", "", phone)[-10:]

    return cleaned


async def enrich_jobs_with_details(
    page,
    jobs: list,
    source: str,
    base_url: str,
    max_fetch: int = 5,
):
    if source not in HR_ENRICH_SOURCES:
        for job in jobs:
            job["hr_contact"] = sanitize_hr_contact(
                job.get("hr_contact", default_hr_contact()),
                job.get("company", ""),
            )
            job["job_link"] = normalize_job_url(
                job.get("job_link", "N/A"),
                base_url,
            )
        return jobs

    for job in jobs[:max_fetch]:
        job_link = job.get("job_link", "N/A")
        company = job.get("company", "")

        if not job_link or job_link == "N/A":
            job["hr_contact"] = default_hr_contact()
            continue

        try:
            await page.goto(
                job_link,
                timeout=30000,
                wait_until="domcontentloaded",
            )
            await page.wait_for_timeout(1200)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            canonical = soup.select_one('link[rel="canonical"]')
            if canonical and canonical.get("href"):
                job["job_link"] = normalize_job_url(
                    canonical["href"],
                    base_url,
                )
            else:
                job["job_link"] = normalize_job_url(page.url, base_url)

            if job.get("posted", "N/A") == "N/A":
                posted = _extract_posted(soup, source)
                if posted != "N/A":
                    job["posted"] = posted

            job["hr_contact"] = sanitize_hr_contact(
                extract_hr_from_soup(soup, source, company),
                company,
            )

        except Exception as error:
            print(f"{source.title()} enrichment error:", error)
            job["hr_contact"] = default_hr_contact()

    for job in jobs:
        if "hr_contact" not in job:
            job["hr_contact"] = sanitize_hr_contact(
                default_hr_contact(),
                job.get("company", ""),
            )

        job["job_link"] = normalize_job_url(
            job.get("job_link", "N/A"),
            base_url,
        )

    return jobs
