import httpx
import os

from .base_agent import BaseAgent, SUB_AGENT_KEY

BRAVE_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "")


class WebSearchAgent(BaseAgent):
    """Searches the web using Brave Search API or DuckDuckGo fallback.
    Runs independently — does not block the main voice loop.
    """

    def __init__(self):
        super().__init__(
            name="agent_search",
            description="Search the internet for real-time information. Returns structured results with titles, URLs, and snippets. Use for any web search query."
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
                        "description": "The search query string"
                    },
                    "num_results": {
                        "type": "INTEGER",
                        "description": "Number of results to return (1-10). Default 5."
                    }
                },
                "required": ["query"]
            }
        }]

    async def _brave_search(self, query: str, num_results: int) -> list:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_KEY}
        params = {"q": query, "count": num_results}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers, params=params)
                data = resp.json()
                results = data.get("web", {}).get("results", [])
                return [
                    {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("description", "")}
                    for r in results
                ]
        except Exception as e:
            print(f"[WebSearchAgent] Brave failed: {e}")
            return []

    async def _duckduckgo_search(self, query: str, num_results: int) -> list:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query, "kl": ""},
                    headers=headers,
                )
                html = resp.text
                results = self._parse_ddg_html(html, num_results)
                if results:
                    return results
        except Exception as e:
            print(f"[WebSearchAgent] DDG HTML failed: {e}")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                )
                data = resp.json()
                results = []
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data.get("AbstractText", ""),
                    })
                for r in data.get("RelatedTopics", [])[:num_results]:
                    if isinstance(r, dict) and "Text" in r:
                        results.append({
                            "title": r.get("Text", "")[:60],
                            "url": r.get("FirstURL", ""),
                            "snippet": r.get("Text", ""),
                        })
                return results
        except Exception as e:
            print(f"[WebSearchAgent] DDG instant-answer failed: {e}")
        return []

    def _parse_ddg_html(self, html: str, num_results: int) -> list:
        import re
        results = []
        pattern = re.compile(
            r'<div[^>]*class="[^"]*result__body[^"]*"[^>]*>'
            r'.*?result__a[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
            r'.*?result__snippet[^>]*>(?P<snippet>.*?)</a>',
            re.DOTALL,
        )
        for m in pattern.finditer(html):
            url = m.group("url")
            title = re.sub(r"<[^>]+>", "", m.group("title")).strip()
            snippet = re.sub(r"<[^>]+>", "", m.group("snippet")).strip()
            if title and url and "duckduckgo.com" not in url:
                results.append({"title": title, "url": url, "snippet": snippet})
                if len(results) >= num_results:
                    break
        return results

    async def execute(self, query: str = "", num_results: int = 5, **kwargs) -> dict:
        if not query:
            return {"success": False, "error": "No query provided", "results": []}
        if BRAVE_KEY:
            results = await self._brave_search(query, num_results)
        else:
            results = await self._duckduckgo_search(query, num_results)
        return {
            "success": True,
            "query": query,
            "results": results,
            "result_count": len(results),
        }
