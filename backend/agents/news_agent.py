import asyncio
import httpx
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone

from .base_agent import BaseAgent


class NewsAgent(BaseAgent):
    """Fetches news from Google News RSS. Runs non-blocking, results
    injected into the main conversation on the next Gemini turn.
    """

    def __init__(self):
        super().__init__(
            name="agent_news",
            description="Fetch latest news for any topic. Returns articles with title, description, URL, source, and published date. Use when the user asks about news, current events, what's happening in the world or a specific topic."
        )

    @property
    def tool_definitions(self) -> list:
        return [{
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": "Topic or search term for news. Leave empty for top headlines."
                    },
                    "max_results": {
                        "type": "INTEGER",
                        "description": "Maximum articles to fetch (default 5, max 15)."
                    }
                },
                "required": []
            }
        }]

    def _parse_pubdate(self, pub: str):
        try:
            return datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def _strip_html(self, text: str):
        return re.sub(r"<[^>]+>", "", text).strip()

    async def _fetch_rss(self, query: str, max_results: int) -> list:
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                root = ET.fromstring(resp.text)
                results = []
                now = datetime.now(timezone.utc)
                for item in root.findall('.//item')[:max_results * 2]:
                    pub = item.findtext('pubDate', '')
                    dt = self._parse_pubdate(pub)
                    if dt:
                        days_old = (now - dt).total_seconds() / 86400
                        if days_old > 7:
                            continue
                    raw_desc = item.findtext('description', '')
                    results.append({
                        "title": item.findtext('title', ''),
                        "description": self._strip_html(raw_desc),
                        "url": item.findtext('link', ''),
                        "published": pub,
                        "source": item.findtext('source', 'Google News'),
                    })
                    if len(results) >= max_results:
                        break
                return results
        except Exception as e:
            print(f"[NewsAgent] RSS failed: {e}")
            return []

    async def execute(self, query: str = "", max_results: int = 5, **kwargs) -> dict:
        q = query if query else "latest news"
        articles = await self._fetch_rss(q, min(max_results, 15))
        return {
            "success": True,
            "query": query or "top headlines",
            "articles": articles,
            "result_count": len(articles),
        }
