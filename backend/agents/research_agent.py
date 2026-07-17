import asyncio

from .base_agent import BaseAgent
from .web_search_agent import WebSearchAgent
from .webpage_agent import WebpageAgent
from .news_agent import NewsAgent


class ResearchAgent(BaseAgent):
    """Deep research agent that combines web search, webpage reading, and news
    to produce a comprehensive answer. Runs all sources in parallel.
    """

    def __init__(self):
        super().__init__(
            name="agent_research",
            description="Deep research on a topic. Searches the web, reads top results, and compiles a comprehensive summary. Use when the user wants thorough, multi-source information on a topic. Runs in the background and delivers results when complete."
        )
        self._search_agent = WebSearchAgent()
        self._webpage_agent = WebpageAgent()
        self._news_agent = NewsAgent()

    @property
    def tool_definitions(self) -> list:
        return [{
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "topic": {
                        "type": "STRING",
                        "description": "The topic or question to research"
                    },
                    "depth": {
                        "type": "STRING",
                        "description": "Research depth: 'quick' (just search results), 'normal' (search + top pages), 'deep' (search + pages + news + synthesis). Default 'normal'."
                    }
                },
                "required": ["topic"]
            }
        }]

    async def execute(self, topic: str = "", depth: str = "normal", **kwargs) -> dict:
        if not topic:
            return {"success": False, "error": "No topic provided"}

        results = {"topic": topic, "depth": depth, "sources": []}

        if depth == "quick":
            search_result = await self._search_agent.execute(query=topic, num_results=5)
            results["search_results"] = search_result.get("results", [])
            results["summary"] = f"Found {search_result.get('result_count', 0)} search results for '{topic}'."
            results["success"] = search_result.get("success", False)
            return results

        tasks = [
            self._search_agent.execute(query=topic, num_results=5),
            self._news_agent.execute(query=topic, max_results=3),
        ]
        search_result, news_result = await asyncio.gather(*tasks)

        results["search_results"] = search_result.get("results", [])
        results["news"] = news_result.get("articles", [])

        if depth == "deep" and search_result.get("results"):
            urls = [r["url"] for r in search_result["results"][:3] if r.get("url")]
            page_tasks = [self._webpage_agent.execute(url=u) for u in urls]
            page_results = await asyncio.gather(*page_tasks)
            results["pages"] = [
                {"url": urls[i], "content": pr.get("content", "")[:2000]}
                for i, pr in enumerate(page_results) if pr.get("success")
            ]

        synthesis_prompt = (
            f"Research topic: {topic}\n"
            f"Search results found: {len(results.get('search_results', []))}\n"
            f"News articles: {len(results.get('news', []))}\n"
            f"Pages read: {len(results.get('pages', []))}\n\n"
            f"Provide a concise, well-structured summary of findings."
        )
        synthesis = await self.call_gemini(
            "You are a research assistant. Synthesize information clearly and objectively.",
            synthesis_prompt,
            timeout=20,
        )
        results["synthesis"] = synthesis.get("content", "")
        results["success"] = True
        return results
