import re
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright

from app.core.config import IS_CLOUD, PROXY_SERVER

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--window-size=1366,768",
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en', 'en-US'] });
window.chrome = { runtime: {} };
"""

BLOCK_MARKERS = (
    "captcha",
    "verify you are human",
    "access denied",
    "blocked",
    "cloudflare",
    "unusual traffic",
    "press & hold",
    "robot",
    "enable cookies",
)

OVERLAY_SELECTORS = (
    "#onetrust-accept-btn-handler",
    "button:has-text('Accept all')",
    "button:has-text('Accept All')",
    "button:has-text('Accept')",
    "button:has-text('I agree')",
    "button:has-text('Got it')",
    "[data-testid='cookie-policy-banner-accept']",
    ".crossIcon",
    "span.crossIcon",
    "#closeModal",
)


def selector_timeout(base_ms: int = 20000) -> int:
    return int(base_ms * 2.5) if IS_CLOUD else base_ms


def navigation_timeout(base_ms: int = 45000) -> int:
    return int(base_ms * 1.5) if IS_CLOUD else base_ms


async def launch_browser(playwright: Playwright, headless: bool) -> Browser:
    launch_kwargs = {
        "headless": headless,
        "args": BROWSER_ARGS,
    }

    if PROXY_SERVER:
        launch_kwargs["proxy"] = {"server": PROXY_SERVER}
        print(f"Using proxy for browser: {PROXY_SERVER.split('@')[-1]}")

    return await playwright.chromium.launch(**launch_kwargs)


async def new_stealth_context(browser: Browser) -> BrowserContext:
    return await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 768},
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        geolocation={"latitude": 19.0760, "longitude": 72.8777},
        permissions=["geolocation"],
        extra_http_headers={
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
    )


async def prepare_page(context: BrowserContext) -> Page:
    page = await context.new_page()
    await page.add_init_script(STEALTH_INIT_SCRIPT)
    return page


async def dismiss_overlays(page: Page):
    for selector in OVERLAY_SELECTORS:
        try:
            button = page.locator(selector).first
            if await button.is_visible(timeout=1200):
                await button.click(timeout=2000)
                await page.wait_for_timeout(400)
        except Exception:
            continue


async def warm_up_domain(page: Page, base_url: str):
    try:
        await page.goto(
            base_url,
            timeout=navigation_timeout(30000),
            wait_until="domcontentloaded",
        )
        await dismiss_overlays(page)
        await page.wait_for_timeout(1500)
    except Exception as error:
        print(f"Warm-up skipped for {base_url}: {error}")


async def wait_for_any_selector(
    page: Page,
    selectors: list,
    timeout_ms: Optional[int] = None,
) -> bool:
    timeout_ms = timeout_ms or selector_timeout()

    for selector in selectors:
        try:
            await page.wait_for_selector(
                selector,
                timeout=timeout_ms,
                state="visible",
            )
            return True
        except Exception:
            continue

    return False


def detect_block_page(html: str) -> Optional[str]:
    lowered = html.lower()
    for marker in BLOCK_MARKERS:
        if marker in lowered:
            return marker
    return None


def log_block_status(source: str, html: str, title: str = ""):
    block = detect_block_page(html)
    if block:
        print(f"{source.title()} may be blocked (detected: {block})")
    if title:
        print(f"{source.title()} page title: {title}")
