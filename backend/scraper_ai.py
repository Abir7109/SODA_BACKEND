import os
import re
import json
import httpx
import logging

logger = logging.getLogger("scraper_ai")

GEMINI_MODEL = "gemini-2.5-flash"
MAX_CHARS = 80000

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": CHROME_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

EXTRACTION_PROMPT = (
    "You are a data extraction assistant. Extract structured data from the "
    "following webpage content based on the user's request. "
    "Return ONLY valid JSON — no markdown, no explanation, no code fences. "
    "If the content is a list of items, return a JSON array of objects. "
    "If it's a single entity, return a JSON object with relevant fields. "
    "Use descriptive keys. Infer structure naturally from the content."
)


async def extract(url: str, prompt: str) -> dict:
    """Extract structured data from a URL using two-tier fetch + Gemini API."""
    result = await _fetch_with_hints(url)
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "Failed to fetch page content"),
            "error_type": result.get("error_type", "fetch_failed"),
            "url": url,
            "prompt": prompt,
        }

    page_text = result.get("content", "")
    if not page_text.strip():
        return {
            "success": False,
            "error": "Fetched page is empty",
            "error_type": "empty_content",
            "url": url,
            "prompt": prompt,
        }

    try:
        data = await _ask_gemini(page_text, prompt)
        return {
            "success": True,
            "data": data,
            "url": url,
            "prompt": prompt,
        }
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
        return {
            "success": False,
            "error": f"AI extraction failed: {e}",
            "error_type": "extraction_failed",
            "url": url,
            "prompt": prompt,
        }


async def _fetch_with_hints(url: str) -> dict:
    """Two-tier fetch: httpx first, Playwright+stealth fallback."""
    result = await _fetch_via_httpx(url)
    if result.get("success"):
        text = result.get("content", "").strip()
        if len(text) > 200:
            return result
        logger.info(f"httpx returned only {len(text)} chars — trying Playwright")

    pw_result = await _fetch_via_playwright(url)
    if pw_result.get("success"):
        return pw_result

    msg = pw_result.get("error", "Unknown error")
    logger.error(f"Both fetch tiers failed for {url}: {msg}")
    return {
        "success": False,
        "error": msg,
        "error_type": "blocked",
    }


async def _fetch_via_httpx(url: str) -> dict:
    """Fetch page text using httpx with real browser headers."""
    try:
        async with httpx.AsyncClient(
            headers=BROWSER_HEADERS,
            follow_redirects=True,
            timeout=25,
        ) as client:
            r = await client.get(url)

        if r.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {r.status_code} from server",
                "error_type": "http_error",
            }

        text = _extract_readable(r.text)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        cleaned = "\n".join(lines)

        return {
            "success": True,
            "content": cleaned[:MAX_CHARS],
            "method": "httpx",
        }

    except httpx.TimeoutException:
        return {"success": False, "error": "Connection timed out", "error_type": "timeout"}
    except httpx.ConnectError:
        return {"success": False, "error": "Could not connect to server", "error_type": "connect_error"}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": "httpx_error"}


async def _fetch_via_playwright(url: str) -> dict:
    """Fetch page text using Playwright with undetected-playwright stealth."""
    try:
        from playwright.async_api import async_playwright
        from undetected_playwright import stealth_async
    except ImportError:
        return {"success": False, "error": "Playwright/stealth not installed", "error_type": "missing_dep"}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(
                user_agent=CHROME_UA,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                device_scale_factor=1,
                ignore_https_errors=True,
            )

            await stealth_async(context)

            page = await context.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            })

            await page.goto(url, wait_until="networkidle", timeout=35000)
            await page.wait_for_timeout(1500)

            text = await page.inner_text("body")
            await browser.close()

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        cleaned = "\n".join(lines)

        if not cleaned.strip():
            return {"success": False, "error": "Page loaded but body is empty", "error_type": "empty_content"}
        return {"success": True, "content": cleaned[:MAX_CHARS], "method": "playwright"}

    except Exception as e:
        return {"success": False, "error": str(e), "error_type": "playwright_error"}


def _extract_readable(html: str) -> str:
    """Strip HTML tags and return readable text."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "noscript", "iframe", "svg", "form", "button"]):
            tag.decompose()

        for tag in soup.find_all(True):
            if tag.name in ("br", "p", "h1", "h2", "h3", "h4", "h5", "h6",
                            "li", "div", "section", "article", "blockquote",
                            "tr", "th", "td", "pre", "dd", "dt"):
                tag.append("\n")

        text = soup.get_text(separator=" ", strip=False)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    except ImportError:
        import html as _html
        text = re.sub(r"<[^>]+>", " ", html)
        text = _html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def _get_api_key() -> str:
    key = (os.getenv("SCRAPER_GEMINI_KEY") or os.getenv("SUB_AGENT_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"))
    if key:
        return key
    raise ValueError("No Gemini API key found (set SCRAPER_GEMINI_KEY, SUB_AGENT_GEMINI_API_KEY, or GEMINI_API_KEY)")


async def _ask_gemini(page_text: str, user_prompt: str) -> dict:
    """Send page text + prompt to Gemini and return parsed JSON."""
    key = _get_api_key()
    url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent"

    system = (
        f"{EXTRACTION_PROMPT}\n\n"
        f"User request: {user_prompt}\n\n"
        f"Webpage content:\n{page_text}"
    )

    body = {
        "contents": [
            {
                "parts": [{"text": system}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        }
    }

    import asyncio
    max_retries = 3
    retry_delay = 2
    last_err = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(f"{url}?key={key}", json=body)

            if r.status_code == 503:
                last_err = RuntimeError(f"Gemini API error (503): Service unavailable")
                logger.warning(f"Gemini 503 on attempt {attempt + 1}/{max_retries}, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 10)
                continue

            if r.status_code != 200:
                err = r.json().get("error", {}).get("message", r.text[:200])
                raise RuntimeError(f"Gemini API error ({r.status_code}): {err}")

            break
        except RuntimeError:
            raise
        except Exception as e:
            last_err = e
            logger.warning(f"Gemini request failed on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 10)
            else:
                raise
    else:
        if last_err:
            raise RuntimeError(f"Gemini request failed after {max_retries} retries: {last_err}")

    raw = r.json()
    text = raw.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {"raw": text}


async def to_markdown(url: str) -> dict:
    """Fetch a URL as plain readable text."""
    result = await _fetch_with_hints(url)
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "Failed to fetch page content"),
            "error_type": result.get("error_type", "fetch_failed"),
            "url": url,
        }
    return {"success": True, "content": result.get("content", ""), "url": url}


def check_available() -> bool:
    try:
        _get_api_key()
        return True
    except ValueError:
        return False
