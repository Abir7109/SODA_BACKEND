import httpx
import re

from .base_agent import BaseAgent


class WebpageAgent(BaseAgent):
    """Fetches and extracts clean text from webpages using trafilatura.
    Non-blocking — results injected on the next Gemini turn.
    """

    def __init__(self):
        super().__init__(
            name="agent_browse",
            description="Fetch and read the content of a specific webpage. Returns clean text content with image URLs. Use after the user picks a URL or result to read. Extracts the page content for summarization."
        )

    @property
    def tool_definitions(self) -> list:
        return [{
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "url": {
                        "type": "STRING",
                        "description": "The full URL of the webpage to fetch"
                    }
                },
                "required": ["url"]
            }
        }]

    async def execute(self, url: str = "", **kwargs) -> dict:
        if not url:
            return {"success": False, "error": "No URL provided"}
        try:
            import trafilatura
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                html = resp.text

            text = trafilatura.extract(html, include_links=False, include_images=False)

            images = []
            img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
            base_url = url.split('/')[0] + '//' + url.split('/')[2]
            for match in img_pattern.finditer(html):
                img_url = match.group(1)
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = base_url + img_url
                elif not img_url.startswith('http'):
                    continue
                if any(skip in img_url.lower() for skip in ['pixel', 'tracking', 'analytics', 'beacon', '1x1', 'spacer', 'blank', 'logo.ico', 'favicon']):
                    continue
                if img_url not in images:
                    images.append(img_url)
                if len(images) >= 8:
                    break

            if not text:
                return {"success": False, "error": "Could not extract content from this page", "url": url}

            return {
                "success": True,
                "content": text[:8000],
                "url": url,
                "images": images,
                "content_length": len(text),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}
