import httpx
from urllib.parse import quote

from .base_agent import BaseAgent


class WikipediaAgent(BaseAgent):
    """Fetches Wikipedia summaries for topics. Non-blocking sub-agent."""

    def __init__(self):
        super().__init__(
            name="agent_wikipedia",
            description="Get a Wikipedia summary for any topic. Returns title, description, extract, and URL. Use when the user asks for factual information, explanations of concepts, or background knowledge on a subject."
        )

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
                        "description": "The topic to look up on Wikipedia"
                    }
                },
                "required": ["topic"]
            }
        }]

    async def execute(self, topic: str = "", **kwargs) -> dict:
        if not topic:
            return {"success": False, "error": "No topic provided"}
        encoded = quote(topic)
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        try:
            headers = {"User-Agent": "SODA-Agent/1.0 (https://github.com/Abir7109/SODA_BACKEND; abircod157@gmail.com)"}
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return {"success": False, "error": f"Topic not found: {topic}", "topic": topic}
                resp.raise_for_status()
                data = resp.json()
                return {
                    "success": True,
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "extract": data.get("extract"),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
                }
        except Exception as e:
            return {"success": False, "error": str(e), "topic": topic}
